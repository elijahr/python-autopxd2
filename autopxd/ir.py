"""Intermediate Representation (IR) for C/C++ declarations.

This module defines the IR that all parser backends produce. The writer
consumes this IR to generate Cython ``.pxd`` files.

Design Principles
-----------------
* **Parser-agnostic**: Works with pycparser, libclang, tree-sitter, etc.
* **Intuitive composition**: Types compose naturally
  (e.g., ``const char*`` becomes ``Pointer(CType("char", ["const"]))``)
* **Complete coverage**: Represents everything Cython ``.pxd`` files can express

Type Hierarchy
--------------
Type expressions form a recursive structure:

* :class:`CType` - Base C type (``int``, ``unsigned long``, etc.)
* :class:`Pointer` - Pointer to another type (``int*``, ``char**``)
* :class:`Array` - Fixed or flexible array (``int[10]``, ``char[]``)
* :class:`FunctionPointer` - Function pointer type

Declaration Types
-----------------
* :class:`Enum` - Enumeration with named constants
* :class:`Struct` - Struct or union with fields
* :class:`Function` - Function declaration
* :class:`Typedef` - Type alias
* :class:`Variable` - Global variable
* :class:`Constant` - Compile-time constant or macro

Example
-------
Parse a header and inspect declarations::

    from autopxd.backends import get_backend
    from autopxd.ir import Struct, Function

    backend = get_backend()
    header = backend.parse("struct Point { int x; int y; };", "test.h")

    for decl in header.declarations:
        if isinstance(decl, Struct):
            print(f"Found struct: {decl.name}")
"""

from __future__ import (
    annotations,
)

from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Optional,
    Protocol,
    Union,
)

# =============================================================================
# Source Location
# =============================================================================


@dataclass
class SourceLocation:
    """Location in source file for error reporting and filtering.

    Used to track where declarations originated, enabling:

    * Better error messages during parsing
    * Filtering declarations by file (e.g., exclude system headers)
    * Source mapping for debugging

    :param file: Path to the source file.
    :param line: Line number (1-indexed).
    :param column: Column number (1-indexed), or None if unknown.

    Example
    -------
    ::

        loc = SourceLocation("myheader.h", 42, 5)
        print(f"Declaration at {loc.file}:{loc.line}")
    """

    file: str
    line: int
    column: Optional[int] = None


# =============================================================================
# Type Representations
# =============================================================================


@dataclass
class CType:
    """A C type expression representing a base type with optional qualifiers.

    This is the fundamental building block for all type representations.
    Qualifiers like ``const``, ``volatile``, ``unsigned`` are stored separately
    from the type name for easier manipulation.

    :param name: The base type name (e.g., ``"int"``, ``"long"``, ``"char"``).
    :param qualifiers: Type qualifiers (e.g., ``["const"]``, ``["unsigned"]``).

    Examples
    --------
    Simple types::

        int_type = CType("int")
        unsigned_long = CType("long", ["unsigned"])
        const_int = CType("int", ["const"])

    Composite types with pointers::

        from autopxd.ir import Pointer

        # const char*
        const_char_ptr = Pointer(CType("char", ["const"]))
    """

    name: str
    qualifiers: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        if self.qualifiers:
            return f"{' '.join(self.qualifiers)} {self.name}"
        return self.name


@dataclass
class Pointer:
    """Pointer to another type.

    Represents pointer types with optional qualifiers. Pointers can be
    nested to represent multi-level indirection (e.g., ``char**``).

    :param pointee: The type being pointed to.
    :param qualifiers: Qualifiers on the pointer itself (e.g., ``["const"]``
        for a const pointer, not a pointer to const).

    Examples
    --------
    Basic pointer::

        int_ptr = Pointer(CType("int"))  # int*

    Pointer to const::

        const_char_ptr = Pointer(CType("char", ["const"]))  # const char*

    Double pointer::

        char_ptr_ptr = Pointer(Pointer(CType("char")))  # char**

    Const pointer (pointer itself is const)::

        const_ptr = Pointer(CType("int"), ["const"])  # int* const
    """

    pointee: Union[CType, Pointer, Array, FunctionPointer]
    qualifiers: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        quals = f"{' '.join(self.qualifiers)} " if self.qualifiers else ""
        return f"{quals}{self.pointee}*"


@dataclass
class Array:
    """Fixed-size or flexible array type.

    Represents C array types, which can have a fixed numeric size,
    a symbolic size (macro or constant), or be flexible (incomplete).

    :param element_type: The type of array elements.
    :param size: Array size - an integer for fixed size, a string for
        symbolic/expression size (e.g., ``"MAX_SIZE"``), or None for
        flexible/incomplete arrays.

    Examples
    --------
    Fixed-size array::

        int_arr = Array(CType("int"), 10)

    Flexible array (incomplete)::

        flex_arr = Array(CType("char"), None)

    Symbolic size::

        buf = Array(CType("char"), "BUFFER_SIZE")

    Multi-dimensional array::

        matrix = Array(Array(CType("int"), 3), 3)
    """

    element_type: Union[CType, Pointer, Array, FunctionPointer]
    size: Optional[Union[int, str]] = None  # None = flexible, str = expression

    def __str__(self) -> str:
        size_str = str(self.size) if self.size is not None else ""
        return f"{self.element_type}[{size_str}]"


@dataclass
class Parameter:
    """Function parameter declaration.

    Represents a single parameter in a function signature. Parameters
    may be named or anonymous (common in prototypes).

    :param name: Parameter name, or None for anonymous parameters.
    :param type: The parameter's type expression.

    Examples
    --------
    Named parameter::

        x_param = Parameter("x", CType("int"))  # int x

    Anonymous parameter::

        anon = Parameter(None, Pointer(CType("void")))  # void*

    Complex type::

        callback = Parameter("fn", FunctionPointer(CType("void"), []))
    """

    name: Optional[str]
    type: Union[CType, Pointer, Array, FunctionPointer]

    def __str__(self) -> str:
        if self.name:
            return f"{self.type} {self.name}"
        return str(self.type)


@dataclass
class FunctionPointer:
    """Function pointer type.

    Represents a pointer to a function with a specific signature.
    Used for callbacks, vtables, and function tables.

    :param return_type: The function's return type.
    :param parameters: List of function parameters.
    :param is_variadic: True if the function accepts variable arguments
        (ends with ``...``).

    Examples
    --------
    Simple function pointer::

        void_fn = FunctionPointer(CType("int"), [])  # int (*)(void)

    With parameters::

        callback = FunctionPointer(
            CType("void"),
            [Parameter("data", Pointer(CType("void")))]
        )  # void (*)(void* data)

    Variadic function pointer::

        printf_fn = FunctionPointer(
            CType("int"),
            [Parameter("fmt", Pointer(CType("char", ["const"])))],
            is_variadic=True
        )  # int (*)(const char* fmt, ...)
    """

    return_type: Union[CType, Pointer, Array, FunctionPointer]
    parameters: list[Parameter] = field(default_factory=list)
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
    """Struct or union field declaration.

    Represents a single field within a struct or union definition.

    :param name: The field name.
    :param type: The field's type expression.

    Examples
    --------
    Simple field::

        x_field = Field("x", CType("int"))  # int x

    Pointer field::

        data = Field("data", Pointer(CType("void")))  # void* data

    Array field::

        buffer = Field("buffer", Array(CType("char"), 256))  # char buffer[256]
    """

    name: str
    type: TypeExpr

    def __str__(self) -> str:
        return f"{self.type} {self.name}"


@dataclass
class EnumValue:
    """Single enumeration constant.

    Represents one named constant within an enum definition.

    :param name: The constant name.
    :param value: The constant's value - an integer for explicit values,
        a string for expressions (e.g., ``"FOO | BAR"``), or None
        for auto-incremented values.

    Examples
    --------
    Explicit value::

        red = EnumValue("RED", 0)

    Auto-increment (implicit value)::

        green = EnumValue("GREEN", None)  # follows previous value

    Expression value::

        mask = EnumValue("MASK", "FLAG_A | FLAG_B")
    """

    name: str
    value: Optional[Union[int, str]] = None  # None = auto, str = expression

    def __str__(self) -> str:
        if self.value is not None:
            return f"{self.name} = {self.value}"
        return self.name


@dataclass
class Enum:
    """Enumeration declaration.

    Represents a C enum type with named constants. Enums may be
    named or anonymous (used in typedefs or inline).

    :param name: The enum tag name, or None for anonymous enums.
    :param values: List of enumeration constants.
    :param is_typedef: True if this enum came from a typedef declaration.
    :param location: Source location for error reporting.

    Examples
    --------
    Named enum::

        color = Enum("Color", [
            EnumValue("RED", 0),
            EnumValue("GREEN", 1),
            EnumValue("BLUE", 2),
        ])

    Anonymous enum (typically used with typedef)::

        anon = Enum(None, [EnumValue("FLAG_A", 1), EnumValue("FLAG_B", 2)])
    """

    name: Optional[str]
    values: list[EnumValue] = field(default_factory=list)
    is_typedef: bool = False
    location: Optional[SourceLocation] = None

    def __str__(self) -> str:
        name_str = self.name or "(anonymous)"
        return f"enum {name_str}"


@dataclass
class Struct:
    """Struct or union declaration.

    Represents a C struct or union type definition. Both use the same
    IR class with ``is_union`` distinguishing between them.

    :param name: The struct/union tag name, or None for anonymous types.
    :param fields: List of member fields.
    :param methods: List of methods (for C++ classes only).
    :param is_union: True for unions, False for structs.
    :param is_cppclass: True for C++ classes (uses ``cppclass`` in Cython).
    :param is_typedef: True if this came from a typedef declaration.
    :param location: Source location for error reporting.

    Examples
    --------
    Simple struct::

        point = Struct("Point", [
            Field("x", CType("int")),
            Field("y", CType("int")),
        ])

    Union::

        data = Struct("Data", [
            Field("i", CType("int")),
            Field("f", CType("float")),
        ], is_union=True)

    C++ class with method::

        widget = Struct("Widget", [
            Field("width", CType("int")),
        ], methods=[
            Function("resize", CType("void"), [
                Parameter("w", CType("int")),
                Parameter("h", CType("int")),
            ])
        ], is_cppclass=True)

    Anonymous struct::

        anon = Struct(None, [Field("value", CType("int"))])
    """

    name: Optional[str]
    fields: list[Field] = field(default_factory=list)
    methods: list[Function] = field(default_factory=list)
    is_union: bool = False
    is_cppclass: bool = False
    is_typedef: bool = False
    namespace: Optional[str] = None
    template_params: list[str] = field(default_factory=list)
    cpp_name: Optional[str] = None
    notes: list[str] = field(default_factory=list)
    inner_typedefs: dict[str, str] = field(default_factory=dict)  # name -> underlying_type
    location: Optional[SourceLocation] = None

    def __str__(self) -> str:
        if self.is_cppclass:
            kind = "cppclass"
        elif self.is_union:
            kind = "union"
        else:
            kind = "struct"
        name_str = self.name or "(anonymous)"
        return f"{kind} {name_str}"


@dataclass
class Function:
    """Function declaration.

    Represents a C function prototype or declaration. Does not include
    the function body (declarations only).

    :param name: The function name.
    :param return_type: The function's return type.
    :param parameters: List of function parameters.
    :param is_variadic: True if the function accepts variable arguments.
    :param location: Source location for error reporting.

    Examples
    --------
    Simple function::

        exit_fn = Function("exit", CType("void"), [
            Parameter("status", CType("int"))
        ])

    With return value::

        strlen_fn = Function("strlen", CType("size_t"), [
            Parameter("s", Pointer(CType("char", ["const"])))
        ])

    Variadic function::

        printf_fn = Function(
            "printf",
            CType("int"),
            [Parameter("fmt", Pointer(CType("char", ["const"])))],
            is_variadic=True
        )
    """

    name: str
    return_type: TypeExpr
    parameters: list[Parameter] = field(default_factory=list)
    is_variadic: bool = False
    namespace: Optional[str] = None
    location: Optional[SourceLocation] = None

    def __str__(self) -> str:
        params = ", ".join(str(p) for p in self.parameters)
        if self.is_variadic:
            params = f"{params}, ..." if params else "..."
        return f"{self.return_type} {self.name}({params})"


@dataclass
class Typedef:
    """Type alias declaration.

    Represents a C typedef that creates an alias for another type.
    Common patterns include aliasing primitives, struct tags, and
    function pointer types.

    :param name: The new type name being defined.
    :param underlying_type: The type being aliased.
    :param location: Source location for error reporting.

    Examples
    --------
    Simple alias::

        size_t = Typedef("size_t", CType("long", ["unsigned"]))

    Struct typedef::

        point_t = Typedef("Point", CType("struct Point"))

    Function pointer typedef::

        callback_t = Typedef("Callback", FunctionPointer(
            CType("void"),
            [Parameter("data", Pointer(CType("void")))]
        ))
    """

    name: str
    underlying_type: TypeExpr
    location: Optional[SourceLocation] = None

    def __str__(self) -> str:
        return f"typedef {self.underlying_type} {self.name}"


@dataclass
class Variable:
    """Global variable declaration.

    Represents a global or extern variable declaration. Does not
    include local variables (which are not exposed in header files).

    :param name: The variable name.
    :param type: The variable's type.
    :param location: Source location for error reporting.

    Examples
    --------
    Extern variable::

        errno_var = Variable("errno", CType("int"))

    Const string::

        version = Variable("version", Pointer(CType("char", ["const"])))

    Array variable::

        lookup_table = Variable("table", Array(CType("int"), 256))
    """

    name: str
    type: TypeExpr
    location: Optional[SourceLocation] = None

    def __str__(self) -> str:
        return f"{self.type} {self.name}"


@dataclass
class Constant:
    """Compile-time constant declaration.

    Represents ``#define`` macros with constant values or ``const``
    variable declarations. Only backends that support macro extraction
    (e.g., libclang) can populate macro constants.

    :param name: The constant name.
    :param value: The constant's value - an integer, float, or string
        expression. None if the value cannot be determined.
    :param type: For typed constants (``const int``), the C type.
        None for macros.
    :param is_macro: True if this is a ``#define`` macro, False for
        ``const`` declarations.
    :param location: Source location for error reporting.

    Examples
    --------
    Numeric macro::

        size = Constant("SIZE", 100, is_macro=True)

    Expression macro::

        mask = Constant("MASK", "1 << 4", is_macro=True)

    Typed const::

        max_val = Constant("MAX_VALUE", 255, type=CType("int"))

    String macro::

        version = Constant("VERSION", '"1.0.0"', is_macro=True)
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
    """Container for a parsed C/C++ header file.

    This is the top-level result returned by all parser backends.
    It contains the file path and all extracted declarations.

    :param path: Path to the original header file.
    :param declarations: List of extracted declarations (structs, functions, etc.).
    :param included_headers: Set of header file basenames included by this header
                             (populated by libclang backend only).

    Example
    -------
    ::

        from autopxd.backends import get_backend
        from autopxd.ir import Struct, Function

        backend = get_backend()
        header = backend.parse(code, "myheader.h")

        print(f"Parsed {len(header.declarations)} declarations from {header.path}")

        for decl in header.declarations:
            if isinstance(decl, Function):
                print(f"  Function: {decl.name}")
    """

    path: str
    declarations: list[Declaration] = field(default_factory=list)
    included_headers: set[str] = field(default_factory=set)

    def __str__(self) -> str:
        return f"Header({self.path}, {len(self.declarations)} declarations)"


# =============================================================================
# Parser Backend Protocol
# =============================================================================


class ParserBackend(Protocol):  # pylint: disable=too-few-public-methods
    """Protocol defining the interface for parser backends.

    All parser backends must implement this protocol to be usable with autopxd2.
    Backends are responsible for translating from their native AST format
    (pycparser, libclang, etc.) to the common :class:`Header` IR format.

    Available Backends
    ------------------
    * ``pycparser`` - Pure Python C99 parser (default)
    * ``libclang`` - LLVM clang-based parser with C++ support

    Example
    -------
    ::

        from autopxd.backends import get_backend

        # Get default backend
        backend = get_backend()

        # Get specific backend
        libclang = get_backend("libclang")

        # Parse code
        header = backend.parse("int foo(void);", "test.h")
    """

    # pylint: disable=unnecessary-ellipsis

    def parse(
        self,
        code: str,
        filename: str,
        include_dirs: Optional[list[str]] = None,
        extra_args: Optional[list[str]] = None,
    ) -> Header:
        """Parse C/C++ code and return the IR representation.

        :param code: Source code to parse.
        :param filename: Name of the source file. Used for error messages
            and ``#line`` directives. Does not need to exist on disk.
        :param include_dirs: Directories to search for ``#include`` files.
            Only used by backends that handle preprocessing.
        :param extra_args: Additional arguments for the preprocessor/compiler.
            Format is backend-specific.
        :returns: Parsed header containing all extracted declarations.
        :raises RuntimeError: If parsing fails due to syntax errors.
        """
        ...

    @property
    def name(self) -> str:
        """Human-readable name of this backend (e.g., ``"pycparser"``)."""
        ...

    @property
    def supports_macros(self) -> bool:
        """Whether this backend can extract ``#define`` constants."""
        ...

    @property
    def supports_cpp(self) -> bool:
        """Whether this backend can parse C++ code."""
        ...
