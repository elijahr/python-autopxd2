"""Tests for the IR writer."""

from autopxd.ir import (
    Array,
    CType,
    Enum,
    EnumValue,
    Field,
    Function,
    FunctionPointer,
    Header,
    Parameter,
    Pointer,
    Struct,
    Typedef,
    Variable,
)
from test.assertions import assert_ir_to_pxd_equals


class TestWriteFunction:
    """Test the write_pxd convenience function."""

    def test_empty_header(self, tmp_path):
        header = Header("test.h", [])
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":
    pass
""",
            tmp_path,
        )

    def test_simple_function(self, tmp_path):
        header = Header(
            "test.h",
            [Function("foo", CType("int"), [])],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    int foo()
""",
            tmp_path,
        )


class TestPxdWriterBasic:
    """Test basic PxdWriter functionality."""

    def test_struct(self, tmp_path):
        header = Header(
            "test.h",
            [
                Struct(
                    "Point",
                    [Field("x", CType("int")), Field("y", CType("int"))],
                )
            ],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    cdef struct Point:
        int x
        int y
""",
            tmp_path,
        )

    def test_union(self, tmp_path):
        header = Header(
            "test.h",
            [
                Struct(
                    "Data",
                    [Field("i", CType("int")), Field("f", CType("float"))],
                    is_union=True,
                )
            ],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    cdef union Data:
        int i
        float f
""",
            tmp_path,
        )

    def test_enum(self, tmp_path):
        header = Header(
            "test.h",
            [
                Enum(
                    "Color",
                    [
                        EnumValue("RED", 0),
                        EnumValue("GREEN", 1),
                        EnumValue("BLUE", 2),
                    ],
                )
            ],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    cdef enum Color:
        RED
        GREEN
        BLUE
""",
            tmp_path,
        )

    def test_function(self, tmp_path):
        header = Header(
            "test.h",
            [
                Function(
                    "add",
                    CType("int"),
                    [Parameter("a", CType("int")), Parameter("b", CType("int"))],
                )
            ],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    int add(int a, int b)
""",
            tmp_path,
        )

    def test_variadic_function(self, tmp_path):
        header = Header(
            "test.h",
            [
                Function(
                    "printf",
                    CType("int"),
                    [Parameter("fmt", Pointer(CType("char", ["const"])))],
                    is_variadic=True,
                )
            ],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    int printf(const char* fmt, ...)
""",
            tmp_path,
        )

    def test_typedef(self, tmp_path):
        header = Header(
            "test.h",
            [Typedef("myint", CType("int"))],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    ctypedef int myint
""",
            tmp_path,
        )

    def test_variable(self, tmp_path):
        header = Header(
            "test.h",
            [Variable("count", CType("int"))],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    int count
""",
            tmp_path,
        )


class TestPointerTypes:
    """Test pointer type formatting."""

    def test_simple_pointer(self, tmp_path):
        header = Header(
            "test.h",
            [Variable("ptr", Pointer(CType("int")))],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    int* ptr
""",
            tmp_path,
        )

    def test_double_pointer(self, tmp_path):
        header = Header(
            "test.h",
            [Variable("ptr", Pointer(Pointer(CType("char"))))],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    char** ptr
""",
            tmp_path,
        )

    def test_const_pointer(self, tmp_path):
        header = Header(
            "test.h",
            [Variable("str_", Pointer(CType("char", ["const"])))],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    const char* str_
""",
            tmp_path,
        )


class TestArrayTypes:
    """Test array type formatting."""

    def test_simple_array(self, tmp_path):
        header = Header(
            "test.h",
            [Variable("arr", Array(CType("int"), 10))],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    int arr[10]
""",
            tmp_path,
        )

    def test_flexible_array(self, tmp_path):
        header = Header(
            "test.h",
            [Variable("arr", Array(CType("int"), None))],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    int arr[]
""",
            tmp_path,
        )

    def test_array_of_pointers(self, tmp_path):
        header = Header(
            "test.h",
            [Variable("ptrs", Array(Pointer(CType("char")), 10))],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    char* ptrs[10]
""",
            tmp_path,
        )

    def test_array_in_struct(self, tmp_path):
        header = Header(
            "test.h",
            [
                Struct(
                    "Buffer",
                    [Field("data", Array(CType("char"), 256))],
                )
            ],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    cdef struct Buffer:
        char data[256]
""",
            tmp_path,
        )


class TestFunctionPointers:
    """Test function pointer formatting."""

    def test_function_pointer_typedef(self, tmp_path):
        header = Header(
            "test.h",
            [
                Typedef(
                    "callback",
                    Pointer(
                        FunctionPointer(
                            CType("int"),
                            [Parameter(None, CType("int"))],
                        )
                    ),
                )
            ],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    ctypedef int (*callback)(int)
""",
            tmp_path,
        )


class TestKeywordEscaping:
    """Test Python keyword escaping."""

    def test_escape_struct_name(self, tmp_path):
        header = Header(
            "test.h",
            [Struct("class", [Field("value", CType("int"))])],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    cdef struct class_ "class":
        int value
""",
            tmp_path,
        )

    def test_escape_function_name(self, tmp_path):
        header = Header(
            "test.h",
            [Function("import", CType("void"), [])],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    void import_ "import"()
""",
            tmp_path,
        )

    def test_escape_field_name(self, tmp_path):
        header = Header(
            "test.h",
            [Struct("Foo", [Field("class", CType("int"))])],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    cdef struct Foo:
        int class_ "class"
""",
            tmp_path,
        )

    def test_escape_param_name(self, tmp_path):
        header = Header(
            "test.h",
            [
                Function(
                    "foo",
                    CType("void"),
                    [Parameter("from", CType("int"))],
                )
            ],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    void foo(int from_)
""",
            tmp_path,
        )

    def test_escape_enum_value(self, tmp_path):
        header = Header(
            "test.h",
            [Enum("Keywords", [EnumValue("None", 0)])],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    cdef enum Keywords:
        None_ "None"
""",
            tmp_path,
        )


class TestStdintTypes:
    """Test stdint type handling."""

    def test_stdint_import(self, tmp_path):
        header = Header(
            "test.h",
            [Variable("val", CType("uint32_t"))],
        )
        assert_ir_to_pxd_equals(
            header,
            """from libc.stdint cimport uint32_t

cdef extern from "test.h":

    uint32_t val
""",
            tmp_path,
        )

    def test_multiple_stdint_imports(self, tmp_path):
        header = Header(
            "test.h",
            [
                Variable("a", CType("int8_t")),
                Variable("b", CType("uint64_t")),
            ],
        )
        assert_ir_to_pxd_equals(
            header,
            """from libc.stdint cimport int8_t, uint64_t

cdef extern from "test.h":

    int8_t a

    uint64_t b
""",
            tmp_path,
        )

    def test_stdint_in_struct(self, tmp_path):
        header = Header(
            "test.h",
            [Struct("Data", [Field("val", CType("size_t"))])],
        )
        # size_t is a Cython built-in, so no cimport needed
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    cdef struct Data:
        size_t val
""",
            tmp_path,
        )

    def test_stdint_in_function_param(self, tmp_path):
        header = Header(
            "test.h",
            [
                Function(
                    "foo",
                    CType("void"),
                    [Parameter("n", CType("uint16_t"))],
                )
            ],
        )
        assert_ir_to_pxd_equals(
            header,
            """from libc.stdint cimport uint16_t

cdef extern from "test.h":

    void foo(uint16_t n)
""",
            tmp_path,
        )


class TestQualifiedTypes:
    """Test type qualifiers."""

    def test_const_type(self, tmp_path):
        header = Header(
            "test.h",
            [Variable("val", CType("int", ["const"]))],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    const int val
""",
            tmp_path,
        )

    def test_volatile_type(self, tmp_path):
        header = Header(
            "test.h",
            [Variable("flag", CType("int", ["volatile"]))],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    volatile int flag
""",
            tmp_path,
        )


class TestComplexCases:
    """Test complex declaration cases."""

    def test_multiple_declarations(self, tmp_path):
        header = Header(
            "test.h",
            [
                Struct("Point", [Field("x", CType("int"))]),
                Function("get_point", CType("struct Point"), []),
            ],
        )
        # struct prefix is stripped because Point is a known type
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    cdef struct Point:
        int x

    Point get_point()
""",
            tmp_path,
        )

    def test_empty_struct(self, tmp_path):
        """Empty struct is a forward declaration (no colon, no pass)."""
        header = Header(
            "test.h",
            [Struct("Empty", [])],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    cdef struct Empty
""",
            tmp_path,
        )

    def test_anonymous_enum(self, tmp_path):
        header = Header(
            "test.h",
            [Enum(None, [EnumValue("VALUE", 42)])],
        )
        assert_ir_to_pxd_equals(
            header,
            """cdef extern from "test.h":

    cdef enum:
        VALUE
""",
            tmp_path,
        )
