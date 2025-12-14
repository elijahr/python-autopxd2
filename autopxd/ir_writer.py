"""IR to Cython ``.pxd`` writer.

This module converts the autopxd IR (Intermediate Representation) to
Cython ``.pxd`` declaration files.

Features
--------
* Keyword escaping - Python keywords get ``_`` suffix with C name alias
* stdint type imports - Automatically adds ``cimport`` for ``libc.stdint`` types
* Full Cython syntax - Supports all declaration types (structs, enums, functions, etc.)

Example
-------
::

    from autopxd.ir_writer import write_pxd
    from autopxd.backends import get_backend

    backend = get_backend()
    header = backend.parse(code, "myheader.h")
    pxd_content = write_pxd(header)

    with open("myheader.pxd", "w") as f:
        f.write(pxd_content)
"""

import re
from collections import defaultdict

from autopxd.cython_types import (
    get_cython_module_for_type,
    get_libcpp_module_for_type,
    get_stub_module_for_type,
)
from autopxd.ir import (
    Array,
    Constant,
    CType,
    Declaration,
    Enum,
    Function,
    FunctionPointer,
    Header,
    Parameter,
    Pointer,
    Struct,
    Typedef,
    TypeExpr,
    Variable,
)
from autopxd.keywords import (
    keywords,
)

# Type qualifiers that Cython doesn't support - strip from output
UNSUPPORTED_TYPE_QUALIFIERS = {"_Atomic", "__restrict", "_Noreturn", "__restrict__"}

# C type names that need to be converted to Cython equivalents
C_TO_CYTHON_TYPE_MAP = {
    "_Bool": "bint",  # C99 boolean type -> Cython boolean integer
}


class PxdWriter:
    """Writes IR to Cython ``.pxd`` format.

    Converts an :class:`~autopxd.ir.Header` containing parsed C/C++ declarations
    into valid Cython ``.pxd`` syntax. Handles keyword escaping, stdint imports,
    and proper formatting for all declaration types.

    :param header: The parsed header to convert.

    Attributes
    ----------
    INDENT : str
        Indentation string (4 spaces).

    Example
    -------
    ::

        from autopxd.ir_writer import PxdWriter
        from autopxd.ir import Header, Function, CType, Parameter

        header = Header("test.h", [
            Function("strlen", CType("size_t"), [
                Parameter("s", Pointer(CType("char", ["const"])))
            ])
        ])

        writer = PxdWriter(header)
        pxd_content = writer.write()
    """

    INDENT = "    "

    def __init__(self, header: Header) -> None:
        self.header = header
        # Track declared struct/union/enum names for type reference cleanup
        self.known_structs: set[str] = set()
        self.known_unions: set[str] = set()
        self.known_enums: set[str] = set()
        self._collect_known_types()

        # Track used-but-undeclared struct/union types (need forward declarations)
        self.undeclared_structs: set[str] = set()
        self.undeclared_unions: set[str] = set()

        # Track incomplete structs (forward declarations with no fields)
        # Fields using these as value types must be skipped
        self.incomplete_structs: set[str] = set()
        self._collect_incomplete_types()

        # New cimport tracking using registries
        self.cython_cimports: dict[str, set[str]] = {}  # module -> types
        self.stub_cimports: dict[str, set[str]] = {}  # stub_module -> types
        self.libcpp_cimports: dict[str, set[str]] = {}  # module -> types

        # Current struct's inner typedefs for method return type resolution
        self._current_inner_typedefs: dict[str, str] = {}

        # Inner typedefs that cannot be represented in Cython (nested template types)
        self._unsupported_inner_typedefs: set[str] = set()

        # Collect types from all declarations
        self._collect_cimport_types()

    def _sort_declarations(self, decls: list[Declaration]) -> tuple[list[Declaration], set[int]]:
        """Sort declarations topologically to resolve forward references.

        This ensures typedefs that reference structs come after the struct
        definitions, and structs that use typedef types have the typedefs
        defined first.

        Args:
            decls: List of declarations to sort.

        Returns:
            Tuple of (sorted declarations, set of indices that are in cycles).
        """
        # Build dependency graph: decl -> list of decls it depends on
        dependencies: dict[int, set[int]] = defaultdict(set)
        decl_names: dict[str, list[int]] = defaultdict(list)  # name -> indices in decls

        # First pass: build name index for all declarations
        # Note: We need to track ALL occurrences, not just the last one
        for i, decl in enumerate(decls):
            if isinstance(decl, (Struct, Typedef, Enum)) and decl.name:
                decl_names[decl.name].append(i)

        # Build typedef→underlying_struct map for resolving indirect dependencies
        # E.g., uv_signal_t -> uv_signal_s
        typedef_to_struct: dict[str, str] = {}
        for decl in decls:
            if isinstance(decl, Typedef) and decl.name:
                underlying_names = self._extract_type_names(decl.underlying_type)
                for uname in underlying_names:
                    if uname in decl_names:
                        # Check if the underlying type is a struct
                        for idx in decl_names[uname]:
                            if isinstance(decls[idx], Struct):
                                typedef_to_struct[decl.name] = uname
                                break

        # Second pass: build dependency edges
        # Key insight: if struct S uses typedef T in a field, then T must be defined before S
        # Similarly, if typedef T aliases struct S, then S must be defined before T
        for i, decl in enumerate(decls):
            if isinstance(decl, Typedef):
                # Typedef depends on the underlying type (struct/union/enum)
                # E.g., "ctypedef uv_signal_s uv_signal_t" depends on uv_signal_s
                # Also, function pointer typedefs depend on types used in parameters/return
                deps = self._extract_type_names(decl.underlying_type)
                for dep_name in deps:
                    if dep_name in decl_names:
                        # Add dependency on ALL occurrences of this name
                        for dep_idx in decl_names[dep_name]:
                            dep_decl = decls[dep_idx]
                            # Depend on struct/union/enum/typedef definitions
                            if isinstance(dep_decl, (Struct, Enum, Typedef)):
                                dependencies[i].add(dep_idx)

            elif isinstance(decl, Struct):
                # Struct depends on types used in its fields
                # E.g., struct with field "uv_signal_t child" depends on uv_signal_t typedef
                #
                # Key insight about pointer types:
                # - Pointers to structs DON'T need the struct to be defined first
                #   (forward declaration is sufficient)
                # - BUT typedefs MUST be defined before use, even through pointers,
                #   because the typedef NAME must be known to the compiler
                for field in decl.fields:
                    # Skip pointer types for struct body dependencies (forward decl is enough)
                    is_pointer = isinstance(field.type, Pointer)

                    deps = self._extract_type_names(field.type)
                    for dep_name in deps:
                        if dep_name in decl_names:
                            for dep_idx in decl_names[dep_name]:
                                dep_decl = decls[dep_idx]
                                # Typedefs must be defined before use (even through pointers)
                                if isinstance(dep_decl, Typedef):
                                    dependencies[i].add(dep_idx)
                                    # For VALUE types, also depend on underlying struct
                                    if not is_pointer and dep_name in typedef_to_struct:
                                        struct_name = typedef_to_struct[dep_name]
                                        if struct_name in decl_names:
                                            for struct_idx in decl_names[struct_name]:
                                                if isinstance(decls[struct_idx], Struct):
                                                    dependencies[i].add(struct_idx)
                                # Struct/enum dependencies only for VALUE types (not pointers)
                                elif isinstance(dep_decl, (Struct, Enum)):
                                    if not is_pointer:
                                        if self._is_value_type_usage(field.type, dep_name):
                                            dependencies[i].add(dep_idx)

            elif isinstance(decl, Function):
                # Functions depend on types used in return type and parameters
                # This ensures typedefs are defined before functions use them
                all_types: set[str] = set()

                # Collect return type dependencies
                all_types.update(self._extract_type_names(decl.return_type))

                # Collect parameter type dependencies
                for param in decl.parameters:
                    all_types.update(self._extract_type_names(param.type))

                for dep_name in all_types:
                    if dep_name in decl_names:
                        for dep_idx in decl_names[dep_name]:
                            dep_decl = decls[dep_idx]
                            # Depend on typedefs (functions use typedef names in signatures)
                            if isinstance(dep_decl, Typedef):
                                dependencies[i].add(dep_idx)

        # Topological sort using Kahn's algorithm
        # in_degree[i] = number of nodes that i depends on
        in_degree = {i: len(dependencies[i]) for i in range(len(decls))}

        # Start with declarations that have no dependencies
        queue = [i for i in range(len(decls)) if in_degree[i] == 0]
        sorted_indices = []

        while queue:
            # Process in stable order (preserve original order when possible)
            queue.sort()
            idx = queue.pop(0)
            sorted_indices.append(idx)

            # For each node that depends on idx, reduce its in-degree
            for dependent in range(len(decls)):
                if idx in dependencies[dependent]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        # If we couldn't sort everything, there's a cycle
        # Track which declarations are in cycles
        cycle_indices = set()
        if len(sorted_indices) != len(decls):
            # Find unsorted indices - these are in cycles
            sorted_set = set(sorted_indices)
            unsorted_indices = [i for i in range(len(decls)) if i not in sorted_set]
            cycle_indices = set(unsorted_indices)
            # Append unsorted declarations in original order
            sorted_indices.extend(unsorted_indices)

        return ([decls[i] for i in sorted_indices], cycle_indices)

    def _extract_type_names(self, typ: TypeExpr) -> set[str]:
        """Extract all type names referenced by a type expression.

        Args:
            typ: Type expression to analyze.

        Returns:
            Set of type names (struct tags, typedefs, etc.) referenced.
        """
        names = set()

        if isinstance(typ, CType):
            # Extract the base name, stripping struct/union/enum prefixes
            name = typ.name
            if name.startswith("struct "):
                names.add(name[7:])
            elif name.startswith("union "):
                names.add(name[6:])
            elif name.startswith("enum "):
                names.add(name[5:])
            else:
                names.add(name)

        elif isinstance(typ, Pointer):
            names.update(self._extract_type_names(typ.pointee))

        elif isinstance(typ, Array):
            names.update(self._extract_type_names(typ.element_type))

        elif isinstance(typ, FunctionPointer):
            names.update(self._extract_type_names(typ.return_type))
            for param in typ.parameters:
                names.update(self._extract_type_names(param.type))

        return names

    def _is_value_type_usage(self, typ: TypeExpr, type_name: str) -> bool:
        """Check if a type is used as a value type (not through a pointer).

        Args:
            typ: Type expression to check.
            type_name: Name of the type we're looking for.

        Returns:
            True if type_name appears as a value type (not pointer/array element).
        """
        if isinstance(typ, CType):
            # Direct usage as value type
            name = typ.name
            if name.startswith("struct "):
                return name[7:] == type_name
            elif name.startswith("union "):
                return name[6:] == type_name
            elif name.startswith("enum "):
                return name[5:] == type_name
            else:
                return name == type_name

        # Pointers and arrays don't require complete types
        return False

    def write(self) -> str:
        """Convert IR Header to Cython ``.pxd`` string.

        :returns: Complete ``.pxd`` file content as a string.
        """
        lines: list[str] = []

        # 1. Cython stdlib cimports (sorted for determinism)
        for module in sorted(self.cython_cimports.keys()):
            types = sorted(self.cython_cimports[module])
            lines.append(f"from {module} cimport {', '.join(types)}")

        # 2. C++ STL cimports
        for module in sorted(self.libcpp_cimports.keys()):
            types = sorted(self.libcpp_cimports[module])
            lines.append(f"from {module} cimport {', '.join(types)}")

        # 3. Autopxd stub cimports
        for stub_module in sorted(self.stub_cimports.keys()):
            types = sorted(self.stub_cimports[stub_module])
            lines.append(f"from autopxd.stubs.{stub_module} cimport {', '.join(types)}")

        # Blank line before extern blocks if we had cimports
        if lines:
            lines.append("")

        # Group declarations by namespace
        by_namespace: dict[str | None, list[Declaration]] = defaultdict(list)
        for decl in self.header.declarations:
            ns = getattr(decl, "namespace", None)
            by_namespace[ns].append(decl)

        # If no declarations at all, still output empty extern block
        if not by_namespace:
            by_namespace[None] = []

        # Sort declarations within each namespace to resolve forward references
        # Also track which declarations are in cycles
        sorted_by_namespace: dict[str | None, list[Declaration]] = {}
        cycle_indices_by_namespace: dict[str | None, set[int]] = {}

        for ns in by_namespace:
            sorted_decls, cycle_indices = self._sort_declarations(by_namespace[ns])
            sorted_by_namespace[ns] = sorted_decls
            # Track which declarations are in cycles (for that namespace)
            cycle_indices_by_namespace[ns] = cycle_indices

        # Output non-namespaced declarations first, then namespaced (sorted)
        namespace_order = sorted(by_namespace.keys(), key=lambda x: (x is not None, x or ""))

        for namespace in namespace_order:
            decls = sorted_by_namespace[namespace]
            cycle_indices = cycle_indices_by_namespace[namespace]

            # Add extern block with optional namespace
            if namespace:
                lines.append(f'cdef extern from "{self.header.path}" namespace "{namespace}":')
            else:
                lines.append(f'cdef extern from "{self.header.path}":')

            # Add forward declarations for undeclared struct/union types (only in global namespace)
            if namespace is None:
                forward_decls = []
                for struct_name in sorted(self.undeclared_structs):
                    forward_decls.append(f"{self.INDENT}cdef struct {struct_name}")
                for union_name in sorted(self.undeclared_unions):
                    forward_decls.append(f"{self.INDENT}cdef union {union_name}")
                if forward_decls:
                    lines.append("")
                    lines.extend(forward_decls)

            # For declarations with circular dependencies, use multi-phase output:
            # 1. Forward declarations for structs in cycles
            # 2a. Typedefs that DON'T reference structs in cycles (safe to use)
            # 2b. Typedefs that reference structs in cycles (but structs are forward-declared)
            # 3. Everything else except full struct bodies in cycles
            # 4. Full struct bodies for structs in cycles

            if cycle_indices:
                # When cycles exist, use strict ordering to break dependencies:
                # 1. Forward declarations for ALL structs with bodies
                # 2. ALL typedefs
                # 3. Enums and functions (non-struct, non-typedef)
                # 4. ALL struct bodies
                #
                # This ensures typedefs are defined before struct bodies use them.

                # First, collect names of typedef'd structs - we'll skip forward declarations
                # for these since the ctypedef struct syntax serves as both declaration and definition
                typedef_struct_names: set[str] = {
                    decl.name for decl in decls if isinstance(decl, Struct) and decl.is_typedef and decl.name
                }

                # Phase 1: Forward declarations for ALL structs with bodies
                # Skip:
                # - Structs that are imported from stubs
                # - typedef'd structs (they use ctypedef struct syntax, not cdef struct)
                forward_struct_decls = []
                for decl in decls:
                    if isinstance(decl, Struct) and (decl.fields or decl.methods):
                        # Skip if this type is available from a stub (we'll cimport it instead)
                        if decl.name and get_stub_module_for_type(decl.name):
                            continue
                        # Skip typedef'd structs - they're emitted as "ctypedef struct name:"
                        if decl.is_typedef:
                            continue
                        kind = "union" if decl.is_union else "struct"
                        name = self._escape_name(decl.name, include_c_name=False)
                        forward_struct_decls.append(f"{self.INDENT}cdef {kind} {name}")

                if forward_struct_decls:
                    lines.append("")
                    lines.extend(forward_struct_decls)

                # Phase 2: ALL typedefs
                typedef_decls = []
                for decl in decls:
                    if isinstance(decl, Typedef):
                        decl_lines = self._write_declaration(decl)
                        for line in decl_lines:
                            typedef_decls.append(f"{self.INDENT}{line}" if line else "")
                        typedef_decls.append("")

                if typedef_decls:
                    lines.append("")
                    lines.extend(typedef_decls)

                # Phase 3: Enums and forward-declaration-only structs (NOT functions)
                # Functions go after struct bodies to ensure all types are complete
                other_decls = []
                for decl in decls:
                    # Skip typedefs (already emitted)
                    if isinstance(decl, Typedef):
                        continue
                    # Skip struct bodies (emit in phase 4)
                    if isinstance(decl, Struct) and (decl.fields or decl.methods):
                        continue
                    # Skip forward-declaration-only structs that have a typedef'd version
                    # (ctypedef struct NAME: serves as both declaration and definition)
                    if isinstance(decl, Struct) and decl.name in typedef_struct_names:
                        continue
                    # Skip functions (emit after struct bodies in phase 5)
                    if isinstance(decl, Function):
                        continue
                    # Emit enums, variables, constants, forward-decl-only structs
                    decl_lines = self._write_declaration(decl)
                    for line in decl_lines:
                        other_decls.append(f"{self.INDENT}{line}" if line else "")
                    other_decls.append("")

                if other_decls:
                    lines.append("")
                    lines.extend(other_decls)

                # Phase 4: ALL struct bodies
                # Sort struct bodies by their VALUE type dependencies on other structs
                # (pointers don't need complete types, so ignore them)
                # Skip structs that are imported from stubs
                struct_decls = [
                    d
                    for d in decls
                    if isinstance(d, Struct)
                    and (d.fields or d.methods)
                    and not (d.name and get_stub_module_for_type(d.name))
                ]

                # Build struct name -> decl index map
                struct_name_to_idx: dict[str, int] = {}
                for idx, sd in enumerate(struct_decls):
                    if sd.name:
                        struct_name_to_idx[sd.name] = idx

                # Build typedef name -> underlying struct name map
                typedef_to_struct_name: dict[str, str] = {}
                for d in decls:
                    if isinstance(d, Typedef) and d.name:
                        underlying_names = self._extract_type_names(d.underlying_type)
                        for un in underlying_names:
                            if un in struct_name_to_idx:
                                typedef_to_struct_name[d.name] = un
                                break

                # Build dependency graph for struct bodies only
                struct_deps: dict[int, set[int]] = {i: set() for i in range(len(struct_decls))}
                for idx, sd in enumerate(struct_decls):
                    for field in sd.fields:
                        # Skip pointer types - they don't need complete definitions
                        if isinstance(field.type, Pointer):
                            continue
                        field_types = self._extract_type_names(field.type)
                        for ft in field_types:
                            # Direct struct dependency
                            if ft in struct_name_to_idx and ft != sd.name:
                                struct_deps[idx].add(struct_name_to_idx[ft])
                            # Indirect through typedef
                            if ft in typedef_to_struct_name:
                                target = typedef_to_struct_name[ft]
                                if target in struct_name_to_idx and target != sd.name:
                                    struct_deps[idx].add(struct_name_to_idx[target])

                # Topological sort of struct bodies
                in_degree = {i: len(struct_deps[i]) for i in range(len(struct_decls))}
                queue = [i for i in range(len(struct_decls)) if in_degree[i] == 0]
                sorted_struct_indices: list[int] = []

                while queue:
                    idx = queue.pop(0)
                    sorted_struct_indices.append(idx)
                    for dependent in range(len(struct_decls)):
                        if idx in struct_deps[dependent]:
                            in_degree[dependent] -= 1
                            if in_degree[dependent] == 0:
                                queue.append(dependent)

                # Append any remaining (cyclic) in original order
                if len(sorted_struct_indices) != len(struct_decls):
                    remaining = [i for i in range(len(struct_decls)) if i not in sorted_struct_indices]
                    sorted_struct_indices.extend(remaining)

                # Emit struct bodies in sorted order
                struct_bodies = []
                for idx in sorted_struct_indices:
                    decl = struct_decls[idx]
                    decl_lines = self._write_declaration(decl)
                    for line in decl_lines:
                        struct_bodies.append(f"{self.INDENT}{line}" if line else "")
                    struct_bodies.append("")

                if struct_bodies:
                    lines.append("")
                    lines.extend(struct_bodies)

                # Phase 5: Functions (after struct bodies so all types are complete)
                func_decls = []
                for decl in decls:
                    if isinstance(decl, Function):
                        decl_lines = self._write_declaration(decl)
                        for line in decl_lines:
                            func_decls.append(f"{self.INDENT}{line}" if line else "")
                        func_decls.append("")

                if func_decls:
                    lines.append("")
                    lines.extend(func_decls)

            else:
                # No cycles - use normal output
                # Add declarations
                if not decls and not (namespace is None and (self.undeclared_structs or self.undeclared_unions)):
                    lines.append(f"{self.INDENT}pass")
                    lines.append("")
                else:
                    lines.append("")
                    for decl in decls:
                        decl_lines = self._write_declaration(decl)
                        for line in decl_lines:
                            lines.append(f"{self.INDENT}{line}" if line else "")
                        lines.append("")

        return "\n".join(lines)

    def _collect_known_types(self) -> None:
        """Collect all declared struct/union/enum names for type resolution."""
        for decl in self.header.declarations:
            if isinstance(decl, Struct):
                if decl.name:
                    if decl.is_union:
                        self.known_unions.add(decl.name)
                    else:
                        self.known_structs.add(decl.name)
            elif isinstance(decl, Enum):
                if decl.name:
                    self.known_enums.add(decl.name)
            elif isinstance(decl, Typedef):
                # Typedefs also create type names
                if decl.name:
                    # Track typedef names - these can be used without prefix
                    self.known_structs.add(decl.name)

    def _collect_incomplete_types(self) -> None:
        """Collect structs that are forward declarations (no fields).

        Cython requires complete type definitions for struct value types.
        Fields using incomplete structs as value types must be skipped.
        """
        for decl in self.header.declarations:
            if isinstance(decl, Struct):
                if decl.name and not decl.fields and not decl.methods:
                    self.incomplete_structs.add(decl.name)

    def _collect_cimport_types(self) -> None:
        """Collect all types that need cimport statements."""
        for decl in self.header.declarations:
            self._collect_types_from_declaration(decl)

    def _collect_types_from_declaration(self, decl: Declaration) -> None:
        """Recursively collect types from a declaration."""
        if isinstance(decl, Function):
            self._check_type(decl.return_type)
            for param in decl.parameters:
                self._check_type(param.type)
        elif isinstance(decl, Struct):
            for field in decl.fields:
                self._check_type(field.type)
            # Also check methods (for cppclass)
            for method in decl.methods:
                self._check_type(method.return_type)
                for param in method.parameters:
                    self._check_type(param.type)
        elif isinstance(decl, Typedef):
            self._check_type(decl.underlying_type)
        elif isinstance(decl, Variable):
            self._check_type(decl.type)

    def _check_type(self, typ: TypeExpr) -> None:
        """Check if a type needs a cimport and record it."""
        if isinstance(typ, CType):
            self._check_type_name(typ.name)
        elif isinstance(typ, Pointer):
            self._check_type(typ.pointee)
        elif isinstance(typ, Array):
            self._check_type(typ.element_type)
        elif isinstance(typ, FunctionPointer):
            self._check_type(typ.return_type)
            for param in typ.parameters:
                self._check_type(param.type)

    def _check_type_name(self, name: str) -> None:
        """Check a type name against registries."""
        # Strip struct/class/union keywords (e.g., "struct string" -> "string")
        clean_name = name.removeprefix("struct ").removeprefix("class ").removeprefix("union ")

        # Check if this type is available in stubs BEFORE deciding to forward-declare
        stub_module = get_stub_module_for_type(name) or get_stub_module_for_type(clean_name)

        # Track undeclared struct/union types that need forward declarations
        # BUT only if they're not available in stubs
        if not stub_module:
            if name.startswith("struct "):
                struct_name = name[7:]  # len("struct ") = 7
                # Skip anonymous structs
                if "(unnamed at" not in struct_name and struct_name not in self.known_structs:
                    self.undeclared_structs.add(struct_name)
            elif name.startswith("union "):
                union_name = name[6:]  # len("union ") = 6
                if "(unnamed at" not in union_name and union_name not in self.known_unions:
                    self.undeclared_unions.add(union_name)

        # Strip std:: prefix for C++ types
        cpp_name = clean_name.removeprefix("std::")

        # For template types, extract the base type name (e.g., "vector<int>" -> "vector")
        base_name = cpp_name.split("<")[0] if "<" in cpp_name else cpp_name

        # Check Cython stdlib
        module = get_cython_module_for_type(name)
        if module:
            self.cython_cimports.setdefault(module, set()).add(name)
            return

        # Check C++ STL (use base name without template args)
        module = get_libcpp_module_for_type(base_name)
        if module:
            self.libcpp_cimports.setdefault(module, set()).add(base_name)

        # Also check template arguments recursively for C++ types
        if "<" in cpp_name:
            self._check_template_args(cpp_name)
            return

        # Check autopxd stubs - try both the full name and clean name
        stub_module = get_stub_module_for_type(name) or get_stub_module_for_type(clean_name)
        if stub_module:
            self.stub_cimports.setdefault(stub_module, set()).add(clean_name)

    def _check_template_args(self, type_str: str) -> None:
        """Recursively check template arguments for types that need cimports.

        Parses template arguments from type strings like ``map<string, vector<int>>``
        and registers any nested types that need cimports.

        Note:
            This parser handles common template patterns but has limitations:

            - Assumes well-formed template syntax (balanced angle brackets)
            - Does not handle ``operator<`` or ``operator>>`` in type names
            - Does not parse default template arguments with comparison operators
              (e.g., ``template<int N = (5>3)>``)

            These edge cases are rare in typical type names and the parser will
            silently skip malformed input rather than raising errors.

        Args:
            type_str: Type string potentially containing template args.
        """
        # Extract content between first < and last >
        start = type_str.find("<")
        if start == -1:
            return

        # Find matching closing >
        depth = 0
        end = -1
        for i in range(start, len(type_str)):
            if type_str[i] == "<":
                depth += 1
            elif type_str[i] == ">":
                depth -= 1
                if depth == 0:
                    end = i
                    break

        if end == -1:
            return

        # Get the template arguments
        args_str = type_str[start + 1 : end]

        # Split by commas, respecting nested templates
        args = []
        current_arg = ""
        depth = 0
        for char in args_str:
            if char == "<":
                depth += 1
                current_arg += char
            elif char == ">":
                depth -= 1
                current_arg += char
            elif char == "," and depth == 0:
                args.append(current_arg.strip())
                current_arg = ""
            else:
                current_arg += char

        if current_arg.strip():
            args.append(current_arg.strip())

        # Check each argument
        for arg in args:
            self._check_type_name(arg)

    def _write_declaration(self, decl: Declaration) -> list[str]:
        """Write a single declaration."""
        if isinstance(decl, Struct):
            return self._write_struct(decl)
        if isinstance(decl, Enum):
            return self._write_enum(decl)
        if isinstance(decl, Function):
            return self._write_function(decl)
        if isinstance(decl, Typedef):
            return self._write_typedef(decl)
        if isinstance(decl, Variable):
            return self._write_variable(decl)
        if isinstance(decl, Constant):
            return self._write_constant(decl)
        return []

    def _write_struct(self, struct: Struct) -> list[str]:
        """Write a struct, union, or cppclass declaration."""
        lines: list[str] = []

        # Store inner typedefs context for _format_ctype to resolve method return types
        # Inner typedefs like `typedef Iterator<T, PT> iterator;` need to be resolved
        # to their underlying type when used as return types
        self._current_inner_typedefs = struct.inner_typedefs if struct.is_cppclass else {}

        # Track inner template typedefs that we cannot properly handle
        # These will cause methods using them to be commented out with an explanation
        self._unsupported_inner_typedefs = set()
        if struct.is_cppclass and struct.inner_typedefs:
            for inner_name, inner_type in struct.inner_typedefs.items():
                if "<" in inner_type and ">" in inner_type:
                    # Extract base type name (e.g., "Iterator" from "Iterator<T, PT>")
                    base_type = inner_type.split("<")[0].strip()
                    # If the base type is already declared (likely as another class's inner type),
                    # we can't use it because Cython doesn't support C++ nested types properly
                    # and will crash when trying to specialize with different template params
                    if base_type and base_type in self.known_structs:
                        self._unsupported_inner_typedefs.add(inner_name)

        # Emit notes as comments before the struct declaration
        if struct.notes:
            for note in struct.notes:
                lines.append(f"# {note}")

        if struct.is_cppclass:
            kind = "cppclass"
        elif struct.is_union:
            kind = "union"
        else:
            kind = "struct"
        name = self._escape_name(struct.name, include_c_name=True)

        # Add template parameters if present
        if struct.template_params:
            params = ", ".join(struct.template_params)
            name = f"{name}[{params}]"

        # Add C++ name if different (for template specializations)
        if struct.cpp_name and struct.cpp_name != struct.name:
            name = f'{name} "{struct.cpp_name}"'

        # typedef'd structs/unions use ctypedef, plain declarations use cdef
        keyword = "ctypedef" if struct.is_typedef else "cdef"

        # If struct has no fields and no methods, it's a forward declaration
        if not struct.fields and not struct.methods:
            lines.append(f"{keyword} {kind} {name}")
            return lines

        lines.append(f"{keyword} {kind} {name}:")

        for field in struct.fields:
            # Skip anonymous struct/union fields - Cython can't represent them directly
            if isinstance(field.type, CType) and "(unnamed at" in field.type.name:
                continue

            # Skip fields using incomplete types as values (not pointers)
            # Cython requires complete type definitions for struct value types
            if self._is_incomplete_value_type(field.type):
                continue

            field_name = self._escape_name(field.name, include_c_name=True)
            # Handle function pointer fields specially
            # Cython requires: int (*callback)(void*, int)
            if isinstance(field.type, FunctionPointer):
                # Check if return type is also a function pointer - Cython doesn't support this
                if self._is_nested_func_ptr(field.type):
                    # Use void* as workaround for function pointer returning function pointer
                    lines.append(f"{self.INDENT}void* {field_name}")
                else:
                    lines.append(f"{self.INDENT}{self._format_func_ptr(field.type, field_name)}")
            # Handle pointer to function pointer
            elif isinstance(field.type, Pointer) and isinstance(field.type.pointee, FunctionPointer):
                # Check if it's nested (return type is also function pointer)
                if self._is_nested_func_ptr(field.type.pointee):
                    lines.append(f"{self.INDENT}void* {field_name}")
                else:
                    lines.append(f"{self.INDENT}{self._format_func_ptr(field.type.pointee, field_name)}")
            # Add array dimensions to name if this is an array type
            elif isinstance(field.type, Array):
                field_type = self._format_type(field.type)
                dims = self._format_array_dims(field.type)
                lines.append(f"{self.INDENT}{field_type} {field_name}{dims}")
            else:
                field_type = self._format_type(field.type)
                lines.append(f"{self.INDENT}{field_type} {field_name}")

        # Add methods for cppclass
        # Operators that need special handling
        # Map C++ operator names to Python-friendly aliases using Cython's string name feature
        operator_aliases = {
            "operator->": "deref",  # operator->() -> deref "operator->()"
            "operator()": "call",  # operator()() -> call "operator()()"
        }
        # operator, (comma) is genuinely unsupported - skip it
        unsupported_operators = {"operator,"}

        for method in struct.methods:
            # Skip operators that Cython doesn't support
            if method.name in unsupported_operators:
                continue

            # Check if return type uses an unsupported inner typedef
            # If so, emit as comment with explanation per user directive
            return_type_name = method.return_type.name if isinstance(method.return_type, CType) else None
            if return_type_name and return_type_name in self._unsupported_inner_typedefs:
                # Get the underlying type for the error message
                underlying = self._current_inner_typedefs.get(return_type_name, return_type_name)
                lines.append(
                    f"{self.INDENT}# UNSUPPORTED: {method.name}() returns C++ inner type "
                    f"'{return_type_name}' ({underlying})"
                )
                lines.append(
                    f"{self.INDENT}# Cython cannot represent nested template types. "
                    f"Use the C++ API directly if needed."
                )
                continue

            # Handle operator aliasing for unsupported operators
            if method.name in operator_aliases:
                # Use Cython's string name feature to alias the operator
                # e.g., T* deref "operator->()" ()
                alias = operator_aliases[method.name]
                return_type = self._format_type(method.return_type)
                params = self._format_params(method.parameters, method.is_variadic)
                method_line = f'{return_type} {alias} "{method.name}"({params})'
                lines.append(f"{self.INDENT}{method_line}")
            else:
                method_lines = self._write_function(method)
                for line in method_lines:
                    lines.append(f"{self.INDENT}{line}")

        # Clear inner typedef context after struct processing
        self._current_inner_typedefs = {}
        self._unsupported_inner_typedefs = set()

        return lines

    def _write_enum(self, enum: Enum) -> list[str]:
        """Write an enum declaration."""
        # Skip anonymous enums with clang's "(unnamed at ...)" names
        if enum.name and "(unnamed at" in enum.name:
            return []

        name = self._escape_name(enum.name, include_c_name=True)

        # typedef'd enums use ctypedef, plain enum declarations use cdef
        # Note: Using cpdef would make enums Python-accessible, but causes C compilation
        # issues when inside extern blocks because Cython generates conversion helpers
        # that forward-declare the enum type without including the header definition.
        keyword = "ctypedef" if enum.is_typedef else "cdef"
        if enum.name:
            lines = [f"{keyword} enum {name}:"]
        else:
            lines = [f"{keyword} enum:"]

        if enum.values:
            for val in enum.values:
                val_name = self._escape_name(val.name, include_c_name=True)
                lines.append(f"{self.INDENT}{val_name}")
        else:
            lines.append(f"{self.INDENT}pass")

        return lines

    def _write_function(self, func: Function) -> list[str]:
        """Write a function declaration."""
        return_type = self._format_type(func.return_type)
        name = self._escape_name(func.name, include_c_name=True)
        params = self._format_params(func.parameters, func.is_variadic)

        return [f"{return_type} {name}({params})"]

    def _write_typedef(self, typedef: Typedef) -> list[str]:
        """Write a typedef declaration."""
        name = self._escape_name(typedef.name, include_c_name=True)

        # Special handling for function pointer typedefs
        # Cython syntax: ctypedef return_type (*name)(params)
        if isinstance(typedef.underlying_type, Pointer):
            if isinstance(typedef.underlying_type.pointee, FunctionPointer):
                return self._write_func_ptr_typedef(name, typedef.underlying_type.pointee)
        if isinstance(typedef.underlying_type, FunctionPointer):
            return self._write_func_ptr_typedef(name, typedef.underlying_type)

        underlying = self._format_type(typedef.underlying_type)

        # Skip circular typedefs like "ctypedef foo foo" - these are invalid
        # This happens with anonymous structs: typedef struct { ... } foo;
        # The struct should be emitted separately as "ctypedef struct foo: ..."
        if (
            underlying == name
            or underlying == f"struct {name}"
            or underlying == f"union {name}"
            or underlying == f"enum {name}"
        ):
            return []

        return [f"ctypedef {underlying} {name}"]

    def _write_func_ptr_typedef(self, name: str, fp: FunctionPointer) -> list[str]:
        """Write a function pointer typedef.

        Cython syntax: ctypedef return_type (*name)(params)

        Note: Cython does not support function pointers that return function pointers.
        For such cases, we use void* as a workaround.
        """
        # Check if return type is a function pointer (or pointer to function pointer)
        # Cython doesn't support this, so we use void* instead
        is_func_ptr_return = isinstance(fp.return_type, FunctionPointer) or (
            isinstance(fp.return_type, Pointer) and isinstance(fp.return_type.pointee, FunctionPointer)
        )
        if is_func_ptr_return:
            return_type = "void*"
        else:
            return_type = self._format_type(fp.return_type)

        params = self._format_params(fp.parameters, fp.is_variadic)
        return [f"ctypedef {return_type} (*{name})({params})"]

    def _write_variable(self, var: Variable) -> list[str]:
        """Write a variable declaration."""
        var_type = self._format_type(var.type)
        name = self._escape_name(var.name, include_c_name=True)

        # Add array dimensions to name if this is an array type
        if isinstance(var.type, Array):
            dims = self._format_array_dims(var.type)
            name = f"{name}{dims}"

        return [f"{var_type} {name}"]

    def _write_constant(self, const: Constant) -> list[str]:
        """Write a constant declaration.

        Constants are written with their detected type (int, double, const char*)
        or as int if type is unknown.
        """
        name = self._escape_name(const.name, include_c_name=True)

        # Use detected type if available
        if const.type:
            type_str = self._format_ctype(const.type)
            # For string macros, need pointer
            if const.type.name == "char" and "const" in const.type.qualifiers:
                return [f"const char* {name}"]
            return [f"{type_str} {name}"]

        # Default to int for macros without detected type
        return [f"int {name}"]

    def _format_type(self, type_expr: TypeExpr) -> str:
        """Format a type expression as Cython string."""
        if isinstance(type_expr, CType):
            return self._format_ctype(type_expr)
        if isinstance(type_expr, Pointer):
            return self._format_pointer(type_expr)
        if isinstance(type_expr, Array):
            return self._format_array(type_expr)
        if isinstance(type_expr, FunctionPointer):
            return self._format_func_ptr(type_expr)
        return "void"

    def _format_ctype(self, ctype: CType) -> str:
        """Format a CType.

        Strips 'struct ', 'union ', 'enum ' prefixes when the type is already
        declared in the header, since Cython references them by name only.
        Also strips unsupported type qualifiers like _Atomic.
        Also de-duplicates qualifiers that may already be in the type name.
        Resolves inner typedefs to their hoisted or underlying types.
        Maps C types to Cython equivalents (e.g., _Bool -> bint).
        """
        name = ctype.name

        # Map C types to Cython equivalents (e.g., _Bool -> bint)
        if name in C_TO_CYTHON_TYPE_MAP:
            name = C_TO_CYTHON_TYPE_MAP[name]

        # Strip C++ namespace prefixes (std::, boost::, library-specific namespaces)
        # Cython uses bare names like "string" not "std::string"
        # This handles both leading prefixes and embedded ones (in templates)
        # Pattern: word characters followed by :: (the namespace prefix)
        # Apply repeatedly to handle nested namespaces like std::chrono::
        while "::" in name:
            name = re.sub(r"\b\w+::", "", name)

        # Resolve inner typedefs (e.g., `iterator` -> `Iterator<T, PT>`)
        # This handles cases like `typedef Iterator<T, PT> iterator;` inside a class
        if self._current_inner_typedefs and name in self._current_inner_typedefs:
            # Use the underlying type directly
            name = self._current_inner_typedefs[name]

        # Strip unsupported type qualifiers from type name
        for qual in UNSUPPORTED_TYPE_QUALIFIERS:
            name = name.replace(f"{qual} ", "")
            # Also handle case where qualifier is at the end
            if name.endswith(f" {qual}"):
                name = name[: -(len(qual) + 1)]
            # Handle qualifier(type) syntax (e.g., _Atomic(int)) - extract the inner type
            prefix = f"{qual}("
            if name.startswith(prefix) and name.endswith(")"):
                name = name[len(prefix) : -1]

        # Strip struct/union/enum prefix if the type is declared, forward-declared, or from stubs
        if name.startswith("struct "):
            struct_name = name[7:]  # len("struct ") = 7
            # Strip prefix if declared OR forward-declared OR available in stubs
            stub_available = get_stub_module_for_type(struct_name) is not None
            if struct_name in self.known_structs or struct_name in self.undeclared_structs or stub_available:
                name = struct_name
        elif name.startswith("union "):
            union_name = name[6:]  # len("union ") = 6
            stub_available = get_stub_module_for_type(union_name) is not None
            if union_name in self.known_unions or union_name in self.undeclared_unions or stub_available:
                name = union_name
        elif name.startswith("enum "):
            enum_name = name[5:]  # len("enum ") = 5
            # In Cython, enum types are referenced by name alone (no "enum" prefix)
            # This is especially important for C++ scoped enums (enum class)
            # We strip the prefix if:
            # 1. The enum is known (declared in this header), OR
            # 2. The name contains no spaces (it's a single identifier, likely from another header)
            # We keep the prefix only for anonymous enums with generated names
            if enum_name in self.known_enums or " " not in enum_name:
                name = enum_name

        # Convert C++ template syntax <> to Cython syntax []
        # This must be done before keyword escaping to handle template parameters correctly
        if "<" in name and ">" in name:
            name = self._convert_template_syntax(name)

        # Escape keywords in type names
        parts = name.split()
        escaped_parts = [self._escape_name(p) for p in parts]
        name = " ".join(escaped_parts)

        if ctype.qualifiers:
            # Filter out unsupported qualifiers
            filtered_quals = [q for q in ctype.qualifiers if q not in UNSUPPORTED_TYPE_QUALIFIERS]
            # De-duplicate qualifiers that are already in the type name
            new_quals = []
            for q in filtered_quals:
                if q not in parts:
                    new_quals.append(q)
            if new_quals:
                quals = " ".join(new_quals)
                return f"{quals} {name}"
        return name

    def _format_pointer(self, ptr: Pointer) -> str:
        """Format a Pointer type.

        Special cases:
        - Pointer to FunctionPointer: void (*)(int)
        - Pointer to Pointer to FunctionPointer: void (**)(int)
        """
        if isinstance(ptr.pointee, FunctionPointer):
            # Function pointer - handled specially
            return self._format_func_ptr_as_ptr(ptr.pointee, ptr.qualifiers)

        # Check for pointer to pointer to function pointer
        # This should be formatted as: void (**)(params) not void (*)(params)*
        if isinstance(ptr.pointee, Pointer) and isinstance(ptr.pointee.pointee, FunctionPointer):
            # Format as pointer to pointer to function
            fp = ptr.pointee.pointee
            return_type = self._format_type(fp.return_type)
            params = self._format_params(fp.parameters, fp.is_variadic)
            # Cython requires explicit void for empty parameter lists
            if not params:
                params = "void"
            result = f"{return_type} (**)({params})"

            if ptr.qualifiers:
                quals = " ".join(ptr.qualifiers)
                result = f"{result} {quals}"

            return result

        pointee = self._format_type(ptr.pointee)
        result = f"{pointee}*"

        if ptr.qualifiers:
            # const pointer, volatile pointer
            quals = " ".join(ptr.qualifiers)
            result = f"{result} {quals}"

        return result

    def _format_array(self, arr: Array) -> str:
        """Format an Array type.

        Note: In Cython, array declarations are written as:
            type name[size]
        So we just return the element type here, and the array dimension
        is added when formatting the variable/field name.
        """
        # For arrays, we just return the element type
        # The dimensions are added by the caller
        return self._format_type(arr.element_type)

    def _is_incomplete_value_type(self, typ: TypeExpr) -> bool:
        """Check if a type is an incomplete struct used as a value (not pointer).

        Cython requires complete type definitions when a struct is used as a
        value type. Pointers to incomplete types are allowed.
        """
        if isinstance(typ, CType):
            # Check if it's a struct type that's incomplete
            name = typ.name
            # Strip "struct " prefix if present
            if name.startswith("struct "):
                struct_name = name[7:]
            else:
                struct_name = name

            # Check if this struct is in our incomplete set
            if struct_name in self.incomplete_structs:
                return True

            # Also check for undeclared structs (forward-declared by us)
            if struct_name in self.undeclared_structs:
                return True

        # Pointers are OK even to incomplete types
        # Arrays and function pointers are also not affected
        return False

    def _is_nested_func_ptr(self, fp: FunctionPointer) -> bool:
        """Check if a function pointer has a nested function pointer (return type is also func ptr).

        Cython doesn't support function pointers that return function pointers.
        We detect this to use void* as a workaround.
        """
        # Direct function pointer return type
        if isinstance(fp.return_type, FunctionPointer):
            return True
        # Pointer to function pointer return type
        if isinstance(fp.return_type, Pointer) and isinstance(fp.return_type.pointee, FunctionPointer):
            return True
        return False

    def _format_func_ptr(self, fp: FunctionPointer, name: str | None = None) -> str:
        """Format a FunctionPointer type.

        Args:
            fp: The FunctionPointer to format
            name: Optional parameter name to include inside the (*name) part

        For Cython, function pointer parameters need the name inside:
            int (*callback)(void*, int)  # with name
            int (*)(void*, int)          # without name

        Note: Cython doesn't support function pointers that return function pointers.
        For such cases, this method returns void* as a workaround when called without
        a name argument. Callers handling struct fields should check _is_nested_func_ptr
        before calling this method.

        Note: For empty parameter lists in struct fields, Cython wants () not (void).
        But for ctypedef declarations, Cython wants (void). The caller should handle
        this distinction if needed.
        """
        # Regular function pointer
        return_type = self._format_type(fp.return_type)
        params = self._format_params(fp.parameters, fp.is_variadic)
        # Keep empty params as empty - let caller decide if void is needed
        if name:
            return f"{return_type} (*{name})({params})"
        return f"{return_type} (*)({params})"

    def _format_func_ptr_as_ptr(self, fp: FunctionPointer, ptr_quals: list[str]) -> str:
        """Format a pointer to function pointer."""
        return_type = self._format_type(fp.return_type)
        params = self._format_params(fp.parameters, fp.is_variadic)
        result = f"{return_type} (*)({params})"

        if ptr_quals:
            quals = " ".join(ptr_quals)
            result = f"{result} {quals}"

        return result

    def _format_params(self, params: list[Parameter], is_variadic: bool) -> str:
        """Format function parameters."""
        parts = []
        for param in params:
            if param.name:
                name = self._escape_name(param.name)
                # Handle function pointer parameters specially
                # Cython requires: int (*callback)(void*, int)
                # NOT: int (*)(void*, int) callback
                if isinstance(param.type, FunctionPointer):
                    parts.append(self._format_func_ptr(param.type, name))
                # Handle pointer to function pointer: int (*callback)(...)
                elif isinstance(param.type, Pointer) and isinstance(param.type.pointee, FunctionPointer):
                    parts.append(self._format_func_ptr(param.type.pointee, name))
                # Handle array parameters
                elif isinstance(param.type, Array):
                    param_type = self._format_type(param.type)
                    dims = self._format_array_dims(param.type)
                    parts.append(f"{param_type} {name}{dims}")
                else:
                    param_type = self._format_type(param.type)
                    parts.append(f"{param_type} {name}")
            else:
                param_type = self._format_type(param.type)
                parts.append(param_type)

        if is_variadic:
            parts.append("...")

        return ", ".join(parts)

    def _format_array_dims(self, arr: Array) -> str:
        """Format array dimensions for variable/field names."""
        dims = []
        current: TypeExpr = arr
        while isinstance(current, Array):
            if current.size is not None:
                dims.append(str(current.size))
            else:
                dims.append("")
            current = current.element_type
        return "".join(f"[{d}]" for d in dims)

    def _convert_template_syntax(self, name: str) -> str:
        """Convert C++ template syntax <> to Cython syntax [].

        This parser handles:
        - Nested templates: Container<Container<int>> -> Container[Container[int]]
        - Multiple parameters: Map<K, V> -> Map[K, V]
        - Non-type parameters: Array<int, 10> -> Array[int, 10]
        - Operators in expressions: Array<int, (16>>2)> -> Array[int, (16>>2)]
        - Templates inside function signatures: function<void (shared_ptr<T>)>

        The key insight is to convert < and > that follow identifiers (templates),
        not those that appear as operators (which usually have spaces around them
        or are inside numeric expressions).
        """
        result = []
        i = 0
        depth = 0  # Track template nesting depth

        while i < len(name):
            char = name[i]

            if char == "(" or char == ")":
                result.append(char)
                i += 1
            elif char == "<":
                # Check if this looks like a template (preceded by identifier/])
                # vs an operator (preceded by space or digit)
                is_template = False
                if i > 0:
                    prev = name[i - 1]
                    # Template if preceded by identifier char or closing bracket
                    if prev.isalnum() or prev == "_" or prev == "]":
                        is_template = True
                else:
                    # < at start of string - treat as template
                    is_template = True

                if is_template:
                    result.append("[")
                    depth += 1
                else:
                    result.append(char)
                i += 1
            elif char == ">":
                # Check if this is a template closing bracket
                if depth > 0:
                    result.append("]")
                    depth -= 1
                else:
                    result.append(char)
                i += 1
            else:
                result.append(char)
                i += 1

        return "".join(result)

    def _escape_name(self, name: str | None, include_c_name: bool = False) -> str:
        """Escape Python keywords by adding underscore suffix.

        If include_c_name is True, also add the original C name in quotes.
        """
        if name is None:
            return ""

        if name in keywords:
            if include_c_name:
                return f'{name}_ "{name}"'
            return f"{name}_"

        return name


def write_pxd(header: Header) -> str:
    """Convert an IR Header to Cython ``.pxd`` string.

    Convenience function that creates a :class:`PxdWriter` and calls
    :meth:`~PxdWriter.write`. This is the main entry point for converting
    parsed headers to Cython declarations.

    :param header: Parsed header in IR format.
    :returns: Complete ``.pxd`` file content as a string.

    Example
    -------
    ::

        from autopxd.backends import get_backend
        from autopxd.ir_writer import write_pxd

        backend = get_backend()
        header = backend.parse(code, "myheader.h")
        pxd = write_pxd(header)

        print(pxd)
    """
    writer = PxdWriter(header)
    return writer.write()
