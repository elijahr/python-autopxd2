"""Intermediate Representation (IR) for C/C++ declarations.

This module defines the IR that all parser backends produce. The writer
consumes this IR to generate Cython .pxd files.

The IR is designed to be:
- Parser-agnostic: works with pycparser, libclang, tree-sitter, etc.
- Intuitive: types compose naturally (e.g., const char* is Pointer(CType("char", ["const"])))
- Complete: covers everything Cython .pxd files can express
"""

from __future__ import (
    annotations,
)

from dataclasses import (
    dataclass,
    field,
)
from typing import (
    List,
    Optional,
    Protocol,
    Union,
)

# =============================================================================
# Source Location
# =============================================================================


@dataclass
class SourceLocation:
    """Location in source file for error reporting and filtering."""

    file: str
    line: int
    column: Optional[int] = None


# =============================================================================
# Type Representations
# =============================================================================


@dataclass
class CType:
    """A C type expression.

    Examples:
        int -> CType("int")
        unsigned long -> CType("long", ["unsigned"])
        const int -> CType("int", ["const"])
    """

    name: str
    qualifiers: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        if self.qualifiers:
            return f"{' '.join(self.qualifiers)} {self.name}"
        return self.name


@dataclass
class Pointer:
    """Pointer to another type.

    Examples:
        int* -> Pointer(CType("int"))
        const char* -> Pointer(CType("char", ["const"]))
        int** -> Pointer(Pointer(CType("int")))
    """

    pointee: Union[CType, "Pointer", "Array", "FunctionPointer"]
    qualifiers: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        quals = f"{' '.join(self.qualifiers)} " if self.qualifiers else ""
        return f"{quals}{self.pointee}*"


@dataclass
class Array:
    """Fixed-size or flexible array.

    Examples:
        int[10] -> Array(CType("int"), 10)
        char[] -> Array(CType("char"), None)
        int[SIZE] -> Array(CType("int"), "SIZE")
    """

    element_type: Union[CType, "Pointer", "Array", "FunctionPointer"]
    size: Optional[Union[int, str]] = None  # None = flexible, str = expression

    def __str__(self) -> str:
        size_str = str(self.size) if self.size is not None else ""
        return f"{self.element_type}[{size_str}]"


@dataclass
class Parameter:
    """Function parameter.

    Examples:
        int x -> Parameter("x", CType("int"))
        void* -> Parameter(None, Pointer(CType("void")))
    """

    name: Optional[str]
    type: Union[CType, Pointer, Array, "FunctionPointer"]

    def __str__(self) -> str:
        if self.name:
            return f"{self.type} {self.name}"
        return str(self.type)


@dataclass
class FunctionPointer:
    """Function pointer type.

    Examples:
        int (*)(void) -> FunctionPointer(CType("int"), [])
        void (*)(int, char*) -> FunctionPointer(CType("void"), [Parameter(...), Parameter(...)])
    """

    return_type: Union[CType, Pointer, Array, "FunctionPointer"]
    parameters: List[Parameter] = field(default_factory=list)
    is_variadic: bool = False

    def __str__(self) -> str:
        params = ", ".join(str(p) for p in self.parameters)
        if self.is_variadic:
            params = f"{params}, ..." if params else "..."
        return f"{self.return_type} (*)({params})"


# Type alias for any type expression
TypeExpr = Union[CType, Pointer, Array, FunctionPointer]


# =============================================================================
# Declarations
# =============================================================================


@dataclass
class Field:
    """Struct or union field."""

    name: str
    type: TypeExpr

    def __str__(self) -> str:
        return f"{self.type} {self.name}"


@dataclass
class EnumValue:
    """Single enum constant.

    Examples:
        FOO = 1 -> EnumValue("FOO", 1)
        BAR -> EnumValue("BAR", None)  # auto-increment
        BAZ = FOO + 1 -> EnumValue("BAZ", "FOO + 1")
    """

    name: str
    value: Optional[Union[int, str]] = None  # None = auto, str = expression

    def __str__(self) -> str:
        if self.value is not None:
            return f"{self.name} = {self.value}"
        return self.name


@dataclass
class Enum:
    """Enum declaration.

    Examples:
        enum Color { RED, GREEN, BLUE }
        enum { ANONYMOUS_VALUE = 42 }  # name is None
    """

    name: Optional[str]
    values: List[EnumValue] = field(default_factory=list)
    location: Optional[SourceLocation] = None

    def __str__(self) -> str:
        name_str = self.name or "(anonymous)"
        return f"enum {name_str}"


@dataclass
class Struct:
    """Struct or union declaration.

    Examples:
        struct Point { int x; int y; }
        union Data { int i; float f; }
    """

    name: Optional[str]
    fields: List[Field] = field(default_factory=list)
    is_union: bool = False
    location: Optional[SourceLocation] = None

    def __str__(self) -> str:
        kind = "union" if self.is_union else "struct"
        name_str = self.name or "(anonymous)"
        return f"{kind} {name_str}"


@dataclass
class Function:
    """Function declaration.

    Examples:
        int main(int argc, char** argv)
        void exit(int status)
    """

    name: str
    return_type: TypeExpr
    parameters: List[Parameter] = field(default_factory=list)
    is_variadic: bool = False
    location: Optional[SourceLocation] = None

    def __str__(self) -> str:
        params = ", ".join(str(p) for p in self.parameters)
        if self.is_variadic:
            params = f"{params}, ..." if params else "..."
        return f"{self.return_type} {self.name}({params})"


@dataclass
class Typedef:
    """Type alias.

    Examples:
        typedef int myint -> Typedef("myint", CType("int"))
        typedef struct Point Point -> Typedef("Point", CType("struct Point"))
    """

    name: str
    underlying_type: TypeExpr
    location: Optional[SourceLocation] = None

    def __str__(self) -> str:
        return f"typedef {self.underlying_type} {self.name}"


@dataclass
class Variable:
    """Global variable declaration.

    Examples:
        extern int errno
        const char* version
    """

    name: str
    type: TypeExpr
    location: Optional[SourceLocation] = None

    def __str__(self) -> str:
        return f"{self.type} {self.name}"


@dataclass
class Constant:
    """Compile-time constant (#define or const).

    Examples:
        #define SIZE 100 -> Constant("SIZE", 100, is_macro=True)
        #define MASK (1 << 4) -> Constant("MASK", "1 << 4", is_macro=True)
        const int X = 10 -> Constant("X", 10, type=CType("int"))
    """

    name: str
    value: Optional[Union[int, float, str]] = None  # None if complex/unknown
    type: Optional[CType] = None
    is_macro: bool = False
    location: Optional[SourceLocation] = None

    def __str__(self) -> str:
        if self.is_macro:
            return f"#define {self.name} {self.value}"
        return f"const {self.type} {self.name} = {self.value}"


# Type alias for any declaration
Declaration = Union[Enum, Struct, Function, Typedef, Variable, Constant]


# =============================================================================
# Header Container
# =============================================================================


@dataclass
class Header:
    """Parsed C/C++ header file."""

    path: str
    declarations: List[Declaration] = field(default_factory=list)

    def __str__(self) -> str:
        return f"Header({self.path}, {len(self.declarations)} declarations)"


# =============================================================================
# Parser Backend Protocol
# =============================================================================


class ParserBackend(Protocol):  # pylint: disable=too-few-public-methods
    """Interface that all parser backends must implement.

    Backends translate from their native AST format to our IR.
    """

    # pylint: disable=unnecessary-ellipsis

    def parse(
        self,
        code: str,
        filename: str,
        include_dirs: Optional[List[str]] = None,
        extra_args: Optional[List[str]] = None,
    ) -> Header:
        """Parse C/C++ code and return IR.

        Args:
            code: Source code to parse
            filename: Name of the source file (for error messages and #line directives)
            include_dirs: Directories to search for #include files
            extra_args: Additional arguments for the preprocessor/compiler

        Returns:
            Header containing all parsed declarations
        """
        ...

    @property
    def name(self) -> str:
        """Human-readable name of this backend."""
        ...

    @property
    def supports_macros(self) -> bool:
        """Whether this backend can extract #define constants."""
        ...

    @property
    def supports_cpp(self) -> bool:
        """Whether this backend can parse C++ code."""
        ...
