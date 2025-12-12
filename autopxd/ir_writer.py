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

        # New cimport tracking using registries
        self.cython_cimports: dict[str, set[str]] = {}  # module -> types
        self.stub_cimports: dict[str, set[str]] = {}  # stub_module -> types
        self.libcpp_cimports: dict[str, set[str]] = {}  # module -> types

        # Collect types from all declarations
        self._collect_cimport_types()

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

        # Output non-namespaced declarations first, then namespaced (sorted)
        namespace_order = sorted(by_namespace.keys(), key=lambda x: (x is not None, x or ""))

        for namespace in namespace_order:
            decls = by_namespace[namespace]

            # Add extern block with optional namespace
            if namespace:
                lines.append(f'cdef extern from "{self.header.path}" namespace "{namespace}":')
            else:
                lines.append(f'cdef extern from "{self.header.path}":')

            # Add declarations
            if not decls:
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

        # Check autopxd stubs
        stub_module = get_stub_module_for_type(name)
        if stub_module:
            self.stub_cimports.setdefault(stub_module, set()).add(name)

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
        if struct.is_cppclass:
            kind = "cppclass"
        elif struct.is_union:
            kind = "union"
        else:
            kind = "struct"
        name = self._escape_name(struct.name, include_c_name=True)

        # typedef'd structs/unions use ctypedef, plain declarations use cdef
        keyword = "ctypedef" if struct.is_typedef else "cdef"

        # If struct has no fields and no methods, it's a forward declaration
        if not struct.fields and not struct.methods:
            return [f"{keyword} {kind} {name}"]

        lines = [f"{keyword} {kind} {name}:"]

        for field in struct.fields:
            field_type = self._format_type(field.type)
            field_name = self._escape_name(field.name, include_c_name=True)
            # Add array dimensions to name if this is an array type
            if isinstance(field.type, Array):
                dims = self._format_array_dims(field.type)
                field_name = f"{field_name}{dims}"
            lines.append(f"{self.INDENT}{field_type} {field_name}")

        # Add methods for cppclass
        for method in struct.methods:
            method_lines = self._write_function(method)
            for line in method_lines:
                lines.append(f"{self.INDENT}{line}")

        return lines

    def _write_enum(self, enum: Enum) -> list[str]:
        """Write an enum declaration."""
        name = self._escape_name(enum.name, include_c_name=True)

        # typedef'd enums use ctypedef, plain enum declarations use cpdef
        keyword = "ctypedef" if enum.is_typedef else "cpdef"
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
        return [f"ctypedef {underlying} {name}"]

    def _write_func_ptr_typedef(self, name: str, fp: FunctionPointer) -> list[str]:
        """Write a function pointer typedef.

        Cython syntax: ctypedef return_type (*name)(params)
        """
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
        """
        name = ctype.name

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

        # Strip struct/union/enum prefix if the type is already declared
        if name.startswith("struct "):
            struct_name = name[7:]  # len("struct ") = 7
            if struct_name in self.known_structs:
                name = struct_name
        elif name.startswith("union "):
            union_name = name[6:]  # len("union ") = 6
            if union_name in self.known_unions:
                name = union_name
        elif name.startswith("enum "):
            enum_name = name[5:]  # len("enum ") = 5
            if enum_name in self.known_enums:
                name = enum_name

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
        """Format a Pointer type."""
        if isinstance(ptr.pointee, FunctionPointer):
            # Function pointer - handled specially
            return self._format_func_ptr_as_ptr(ptr.pointee, ptr.qualifiers)

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

    def _format_func_ptr(self, fp: FunctionPointer) -> str:
        """Format a FunctionPointer type."""
        return_type = self._format_type(fp.return_type)
        params = self._format_params(fp.parameters, fp.is_variadic)
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
            param_type = self._format_type(param.type)
            if param.name:
                name = self._escape_name(param.name)
                # Handle array parameters
                if isinstance(param.type, Array):
                    dims = self._format_array_dims(param.type)
                    parts.append(f"{param_type} {name}{dims}")
                else:
                    parts.append(f"{param_type} {name}")
            else:
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
