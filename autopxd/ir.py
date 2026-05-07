"""IR module - re-exported from headerkit.

All IR classes are now maintained in the headerkit package.
This module provides backward-compatible imports.
"""

from headerkit.ir import (
    Array,
    Constant,
    CType,
    Declaration,
    Enum,
    EnumValue,
    Field,
    Function,
    FunctionPointer,
    Header,
    Parameter,
    ParserBackend,
    Pointer,
    SourceLocation,
    Struct,
    Typedef,
    TypeExpr,
    Variable,
)

__all__ = [
    "Array",
    "Constant",
    "CType",
    "Declaration",
    "Enum",
    "EnumValue",
    "Field",
    "Function",
    "FunctionPointer",
    "Header",
    "Parameter",
    "ParserBackend",
    "Pointer",
    "SourceLocation",
    "Struct",
    "Typedef",
    "TypeExpr",
    "Variable",
]
