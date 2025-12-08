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

from autopxd.declarations import (
    STDINT_DECLARATIONS,
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
        self.stdint_types: set[str] = set()
        # Track declared struct/union/enum names for type reference cleanup
        self.known_structs: set[str] = set()
        self.known_unions: set[str] = set()
        self.known_enums: set[str] = set()
        self._collect_known_types()

    def write(self) -> str:
        """Convert IR Header to Cython ``.pxd`` string.

        :returns: Complete ``.pxd`` file content as a string.
        """
        lines: list[str] = []

        # Collect stdint types used
        self._collect_stdint_types()

        # Add stdint imports if needed
        if self.stdint_types:
            cimports = ", ".join(sorted(self.stdint_types))
            lines.append(f"from libc.stdint cimport {cimports}")
            lines.append("")

        # Add extern block
        lines.append(f'cdef extern from "{self.header.path}":')

        # Add declarations
        if not self.header.declarations:
            lines.append(f"{self.INDENT}pass")
            lines.append("")
        else:
            lines.append("")
            for decl in self.header.declarations:
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

    def _collect_stdint_types(self) -> None:
        """Collect all stdint types used in declarations."""
        for decl in self.header.declarations:
            self._collect_stdint_from_decl(decl)

    def _collect_stdint_from_decl(self, decl: Declaration) -> None:
        """Collect stdint types from a declaration."""
        if isinstance(decl, Struct):
            for field in decl.fields:
                self._collect_stdint_from_type(field.type)
        elif isinstance(decl, Function):
            self._collect_stdint_from_type(decl.return_type)
            for param in decl.parameters:
                self._collect_stdint_from_type(param.type)
        elif isinstance(decl, Typedef):
            self._collect_stdint_from_type(decl.underlying_type)
        elif isinstance(decl, Variable):
            self._collect_stdint_from_type(decl.type)

    def _collect_stdint_from_type(self, type_expr: TypeExpr) -> None:
        """Collect stdint types from a type expression."""
        if isinstance(type_expr, CType):
            if type_expr.name in STDINT_DECLARATIONS:
                self.stdint_types.add(type_expr.name)
        elif isinstance(type_expr, Pointer):
            self._collect_stdint_from_type(type_expr.pointee)
        elif isinstance(type_expr, Array):
            self._collect_stdint_from_type(type_expr.element_type)
        elif isinstance(type_expr, FunctionPointer):
            self._collect_stdint_from_type(type_expr.return_type)
            for param in type_expr.parameters:
                self._collect_stdint_from_type(param.type)

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
        """Write a struct or union declaration."""
        kind = "union" if struct.is_union else "struct"
        name = self._escape_name(struct.name, include_c_name=True)

        # typedef'd structs/unions use ctypedef, plain declarations use cdef
        keyword = "ctypedef" if struct.is_typedef else "cdef"

        # If struct has no fields, it's a forward declaration
        if not struct.fields:
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

        Constants are written as Cython enum values for macros,
        or typed constants for const declarations.
        """
        name = self._escape_name(const.name, include_c_name=True)
        if const.is_macro:
            # Macros become anonymous enum values
            return [f"int {name}"]
        if const.type:
            type_str = self._format_ctype(const.type)
            return [f"{type_str} {name}"]
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
        Also de-duplicates qualifiers that may already be in the type name.
        """
        name = ctype.name

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
            # De-duplicate qualifiers that are already in the type name
            # e.g., if name is "const char" and qualifiers contains "const",
            # we don't want to produce "const const char"
            new_quals = []
            for q in ctype.qualifiers:
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
