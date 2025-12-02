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
from autopxd.ir_writer import (
    write_pxd,
)


class TestWriteFunction:
    """Test the write_pxd convenience function."""

    def test_empty_header(self):
        header = Header("test.h", [])
        result = write_pxd(header)
        assert 'cdef extern from "test.h":' in result
        assert "pass" in result

    def test_simple_function(self):
        header = Header(
            "test.h",
            [Function("foo", CType("int"), [])],
        )
        result = write_pxd(header)
        assert "int foo()" in result


class TestPxdWriterBasic:
    """Test basic PxdWriter functionality."""

    def test_struct(self):
        header = Header(
            "test.h",
            [
                Struct(
                    "Point",
                    [Field("x", CType("int")), Field("y", CType("int"))],
                )
            ],
        )
        result = write_pxd(header)
        assert "cdef struct Point:" in result
        assert "int x" in result
        assert "int y" in result

    def test_union(self):
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
        result = write_pxd(header)
        assert "cdef union Data:" in result

    def test_enum(self):
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
        result = write_pxd(header)
        assert "cpdef enum Color:" in result
        assert "RED" in result
        assert "GREEN" in result
        assert "BLUE" in result

    def test_function(self):
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
        result = write_pxd(header)
        assert "int add(int a, int b)" in result

    def test_variadic_function(self):
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
        result = write_pxd(header)
        assert "int printf(const char* fmt, ...)" in result

    def test_typedef(self):
        header = Header(
            "test.h",
            [Typedef("myint", CType("int"))],
        )
        result = write_pxd(header)
        assert "ctypedef int myint" in result

    def test_variable(self):
        header = Header(
            "test.h",
            [Variable("count", CType("int"))],
        )
        result = write_pxd(header)
        assert "int count" in result


class TestPointerTypes:
    """Test pointer type formatting."""

    def test_simple_pointer(self):
        header = Header(
            "test.h",
            [Variable("ptr", Pointer(CType("int")))],
        )
        result = write_pxd(header)
        assert "int* ptr" in result

    def test_double_pointer(self):
        header = Header(
            "test.h",
            [Variable("ptr", Pointer(Pointer(CType("char"))))],
        )
        result = write_pxd(header)
        assert "char** ptr" in result

    def test_const_pointer(self):
        header = Header(
            "test.h",
            [Variable("str", Pointer(CType("char", ["const"])))],
        )
        result = write_pxd(header)
        assert "const char* str" in result


class TestArrayTypes:
    """Test array type formatting."""

    def test_simple_array(self):
        header = Header(
            "test.h",
            [Variable("arr", Array(CType("int"), 10))],
        )
        result = write_pxd(header)
        assert "int arr[10]" in result

    def test_flexible_array(self):
        header = Header(
            "test.h",
            [Variable("arr", Array(CType("int"), None))],
        )
        result = write_pxd(header)
        assert "int arr[]" in result

    def test_array_of_pointers(self):
        header = Header(
            "test.h",
            [Variable("ptrs", Array(Pointer(CType("char")), 10))],
        )
        result = write_pxd(header)
        assert "char* ptrs[10]" in result

    def test_array_in_struct(self):
        header = Header(
            "test.h",
            [
                Struct(
                    "Buffer",
                    [Field("data", Array(CType("char"), 256))],
                )
            ],
        )
        result = write_pxd(header)
        assert "char data[256]" in result


class TestFunctionPointers:
    """Test function pointer formatting."""

    def test_function_pointer_typedef(self):
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
        result = write_pxd(header)
        assert "ctypedef int (*)(int) callback" in result


class TestKeywordEscaping:
    """Test Python keyword escaping."""

    def test_escape_struct_name(self):
        header = Header(
            "test.h",
            [Struct("class", [Field("value", CType("int"))])],
        )
        result = write_pxd(header)
        assert 'class_ "class"' in result

    def test_escape_function_name(self):
        header = Header(
            "test.h",
            [Function("import", CType("void"), [])],
        )
        result = write_pxd(header)
        assert "import_" in result

    def test_escape_field_name(self):
        header = Header(
            "test.h",
            [Struct("Foo", [Field("class", CType("int"))])],
        )
        result = write_pxd(header)
        assert "class_" in result

    def test_escape_param_name(self):
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
        result = write_pxd(header)
        assert "from_" in result

    def test_escape_enum_value(self):
        header = Header(
            "test.h",
            [Enum("Keywords", [EnumValue("None", 0)])],
        )
        result = write_pxd(header)
        assert 'None_ "None"' in result


class TestStdintTypes:
    """Test stdint type handling."""

    def test_stdint_import(self):
        header = Header(
            "test.h",
            [Variable("val", CType("uint32_t"))],
        )
        result = write_pxd(header)
        assert "from libc.stdint cimport uint32_t" in result

    def test_multiple_stdint_imports(self):
        header = Header(
            "test.h",
            [
                Variable("a", CType("int8_t")),
                Variable("b", CType("uint64_t")),
            ],
        )
        result = write_pxd(header)
        assert "from libc.stdint cimport" in result
        assert "int8_t" in result
        assert "uint64_t" in result

    def test_stdint_in_struct(self):
        header = Header(
            "test.h",
            [Struct("Data", [Field("val", CType("size_t"))])],
        )
        result = write_pxd(header)
        # size_t is not in STDINT_DECLARATIONS, so no import needed
        assert "from libc.stdint cimport" not in result
        assert "size_t val" in result

    def test_stdint_in_function_param(self):
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
        result = write_pxd(header)
        assert "from libc.stdint cimport uint16_t" in result


class TestQualifiedTypes:
    """Test type qualifiers."""

    def test_const_type(self):
        header = Header(
            "test.h",
            [Variable("val", CType("int", ["const"]))],
        )
        result = write_pxd(header)
        assert "const int val" in result

    def test_volatile_type(self):
        header = Header(
            "test.h",
            [Variable("flag", CType("int", ["volatile"]))],
        )
        result = write_pxd(header)
        assert "volatile int flag" in result


class TestComplexCases:
    """Test complex declaration cases."""

    def test_multiple_declarations(self):
        header = Header(
            "test.h",
            [
                Struct("Point", [Field("x", CType("int"))]),
                Function("get_point", CType("struct Point"), []),
            ],
        )
        result = write_pxd(header)
        assert "cdef struct Point:" in result
        assert "struct Point get_point()" in result

    def test_empty_struct(self):
        header = Header(
            "test.h",
            [Struct("Empty", [])],
        )
        result = write_pxd(header)
        assert "cdef struct Empty:" in result
        assert "pass" in result

    def test_anonymous_enum(self):
        header = Header(
            "test.h",
            [Enum(None, [EnumValue("VALUE", 42)])],
        )
        result = write_pxd(header)
        assert "cpdef enum:" in result
        assert "VALUE" in result
