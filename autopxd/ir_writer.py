"""IR to Cython .pxd writer.

This module converts our IR (Intermediate Representation) to Cython .pxd files.
It handles:
- Keyword escaping (Python keywords get _ suffix)
- stdint type imports
- Proper Cython syntax for all declaration types
"""

from typing import (
    List,
    Optional,
    Set,
    Union,
)

from autopxd.declarations import (
    STDINT_DECLARATIONS,
)
from autopxd.ir import (
    Array,
    CType,
    Enum,
    Field,
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
    """Writes IR to Cython .pxd format."""

    INDENT = "    "

    def __init__(self, header: Header) -> None:
        self.header = header
        self.stdint_types: Set[str] = set()

    def write(self) -> str:
        """Convert IR Header to Cython .pxd string."""
        lines: List[str] = []

        # Collect stdint types used
        self._collect_stdint_types()

        # Add stdint imports if needed
        if self.stdint_types:
            cimports = ", ".join(sorted(self.stdint_types))
            lines.append(f"from libc.stdint cimport {cimports}")
            lines.append("")

        # Add extern block
        lines.append(f'cdef extern from "{self.header.path}":')
        lines.append("")

        # Add declarations
        if not self.header.declarations:
            lines.append(f"{self.INDENT}pass")
            lines.append("")
        else:
            for decl in self.header.declarations:
                decl_lines = self._write_declaration(decl)
                for line in decl_lines:
                    lines.append(f"{self.INDENT}{line}" if line else "")
                lines.append("")

        return "\n".join(lines)

    def _collect_stdint_types(self) -> None:
        """Collect all stdint types used in declarations."""
        for decl in self.header.declarations:
            self._collect_stdint_from_decl(decl)

    def _collect_stdint_from_decl(self, decl: Union[Enum, Struct, Function, Typedef, Variable]) -> None:
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

    def _write_declaration(self, decl: Union[Enum, Struct, Function, Typedef, Variable]) -> List[str]:
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
        return []

    def _write_struct(self, struct: Struct) -> List[str]:
        """Write a struct or union declaration."""
        kind = "union" if struct.is_union else "struct"
        name = self._escape_name(struct.name, include_c_name=True)

        lines = [f"cdef {kind} {name}:"]

        if struct.fields:
            for field in struct.fields:
                field_type = self._format_type(field.type)
                field_name = self._escape_name(field.name)
                # Add array dimensions to name if this is an array type
                if isinstance(field.type, Array):
                    dims = self._format_array_dims(field.type)
                    field_name = f"{field_name}{dims}"
                lines.append(f"{self.INDENT}{field_type} {field_name}")
        else:
            lines.append(f"{self.INDENT}pass")

        return lines

    def _write_enum(self, enum: Enum) -> List[str]:
        """Write an enum declaration."""
        name = self._escape_name(enum.name, include_c_name=True)

        # Use cpdef for named enums (makes them accessible from Python)
        if enum.name:
            lines = [f"cpdef enum {name}:"]
        else:
            lines = ["cpdef enum:"]

        if enum.values:
            for val in enum.values:
                val_name = self._escape_name(val.name, include_c_name=True)
                lines.append(f"{self.INDENT}{val_name}")
        else:
            lines.append(f"{self.INDENT}pass")

        return lines

    def _write_function(self, func: Function) -> List[str]:
        """Write a function declaration."""
        return_type = self._format_type(func.return_type)
        name = self._escape_name(func.name)
        params = self._format_params(func.parameters, func.is_variadic)

        return [f"{return_type} {name}({params})"]

    def _write_typedef(self, typedef: Typedef) -> List[str]:
        """Write a typedef declaration."""
        underlying = self._format_type(typedef.underlying_type)
        name = self._escape_name(typedef.name)

        return [f"ctypedef {underlying} {name}"]

    def _write_variable(self, var: Variable) -> List[str]:
        """Write a variable declaration."""
        var_type = self._format_type(var.type)
        name = self._escape_name(var.name)

        # Add array dimensions to name if this is an array type
        if isinstance(var.type, Array):
            dims = self._format_array_dims(var.type)
            name = f"{name}{dims}"

        return [f"{var_type} {name}"]

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
        """Format a CType."""
        # Escape keywords in type names
        parts = ctype.name.split()
        escaped_parts = [self._escape_name(p) for p in parts]
        name = " ".join(escaped_parts)

        if ctype.qualifiers:
            quals = " ".join(ctype.qualifiers)
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

    def _format_func_ptr_as_ptr(self, fp: FunctionPointer, ptr_quals: List[str]) -> str:
        """Format a pointer to function pointer."""
        return_type = self._format_type(fp.return_type)
        params = self._format_params(fp.parameters, fp.is_variadic)
        result = f"{return_type} (*)({params})"

        if ptr_quals:
            quals = " ".join(ptr_quals)
            result = f"{result} {quals}"

        return result

    def _format_params(self, params: List[Parameter], is_variadic: bool) -> str:
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

    def _escape_name(self, name: Optional[str], include_c_name: bool = False) -> str:
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
    """Convert an IR Header to Cython .pxd string.

    Args:
        header: Parsed header in IR format

    Returns:
        Cython .pxd file content as string
    """
    writer = PxdWriter(header)
    return writer.write()
