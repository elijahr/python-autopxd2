"""Tests for the IR module."""

from autopxd.ir import (
    Array,
    Constant,
    CType,
    Enum,
    EnumValue,
    Field,
    Function,
    FunctionPointer,
    Header,
    Parameter,
    Pointer,
    SourceLocation,
    Struct,
    Typedef,
    Variable,
)


class TestCType:
    def test_simple_type(self):
        t = CType("int")
        assert t.name == "int"
        assert t.qualifiers == []
        assert str(t) == "int"

    def test_qualified_type(self):
        t = CType("int", ["const"])
        assert str(t) == "const int"

    def test_multiple_qualifiers(self):
        t = CType("int", ["const", "volatile"])
        assert str(t) == "const volatile int"


class TestPointer:
    def test_simple_pointer(self):
        p = Pointer(CType("int"))
        assert str(p) == "int*"

    def test_const_pointer(self):
        p = Pointer(CType("char", ["const"]))
        assert str(p) == "const char*"

    def test_pointer_to_pointer(self):
        p = Pointer(Pointer(CType("int")))
        assert str(p) == "int**"


class TestArray:
    def test_fixed_size_array(self):
        a = Array(CType("int"), 10)
        assert str(a) == "int[10]"

    def test_flexible_array(self):
        a = Array(CType("char"), None)
        assert str(a) == "char[]"

    def test_expression_size(self):
        a = Array(CType("int"), "SIZE")
        assert str(a) == "int[SIZE]"


class TestFunctionPointer:
    def test_simple_function_pointer(self):
        fp = FunctionPointer(CType("int"), [])
        assert str(fp) == "int (*)()"

    def test_function_pointer_with_params(self):
        fp = FunctionPointer(
            CType("void"),
            [Parameter("x", CType("int")), Parameter("y", CType("int"))],
        )
        assert str(fp) == "void (*)(int x, int y)"

    def test_variadic_function_pointer(self):
        fp = FunctionPointer(
            CType("int"),
            [Parameter("fmt", Pointer(CType("char", ["const"])))],
            is_variadic=True,
        )
        assert str(fp) == "int (*)(const char* fmt, ...)"


class TestEnum:
    def test_simple_enum(self):
        e = Enum("Color", [EnumValue("RED"), EnumValue("GREEN"), EnumValue("BLUE")])
        assert e.name == "Color"
        assert len(e.values) == 3
        assert str(e) == "enum Color"

    def test_enum_with_values(self):
        e = Enum(
            "Flags",
            [EnumValue("FLAG_A", 1), EnumValue("FLAG_B", 2), EnumValue("FLAG_C", "FLAG_A | FLAG_B")],
        )
        assert str(e.values[0]) == "FLAG_A = 1"
        assert str(e.values[2]) == "FLAG_C = FLAG_A | FLAG_B"

    def test_anonymous_enum(self):
        e = Enum(None, [EnumValue("VALUE", 42)])
        assert str(e) == "enum (anonymous)"


class TestStruct:
    def test_simple_struct(self):
        s = Struct("Point", [Field("x", CType("int")), Field("y", CType("int"))])
        assert s.name == "Point"
        assert not s.is_union
        assert str(s) == "struct Point"

    def test_union(self):
        u = Struct("Data", [Field("i", CType("int")), Field("f", CType("float"))], is_union=True)
        assert u.is_union
        assert str(u) == "union Data"


class TestFunction:
    def test_simple_function(self):
        f = Function("main", CType("int"), [])
        assert str(f) == "int main()"

    def test_function_with_params(self):
        f = Function(
            "add",
            CType("int"),
            [Parameter("a", CType("int")), Parameter("b", CType("int"))],
        )
        assert str(f) == "int add(int a, int b)"

    def test_variadic_function(self):
        f = Function(
            "printf",
            CType("int"),
            [Parameter("fmt", Pointer(CType("char", ["const"])))],
            is_variadic=True,
        )
        assert str(f) == "int printf(const char* fmt, ...)"


class TestTypedef:
    def test_simple_typedef(self):
        t = Typedef("myint", CType("int"))
        assert str(t) == "typedef int myint"


class TestVariable:
    def test_simple_variable(self):
        v = Variable("count", CType("int"))
        assert str(v) == "int count"


class TestConstant:
    def test_macro_constant(self):
        c = Constant("SIZE", 100, is_macro=True)
        assert str(c) == "#define SIZE 100"

    def test_const_variable(self):
        c = Constant("MAX", 255, type=CType("int"))
        assert str(c) == "const int MAX = 255"


class TestHeader:
    def test_header(self):
        h = Header(
            "test.h",
            [
                Struct("Point", [Field("x", CType("int"))]),
                Function("get_point", CType("Point")),
            ],
        )
        assert h.path == "test.h"
        assert len(h.declarations) == 2
        assert str(h) == "Header(test.h, 2 declarations)"


class TestSourceLocation:
    def test_location(self):
        loc = SourceLocation("test.h", 42, 10)
        assert loc.file == "test.h"
        assert loc.line == 42
        assert loc.column == 10

    def test_location_without_column(self):
        loc = SourceLocation("test.h", 42)
        assert loc.column is None


class TestHeaderIncludedHeaders:
    """Tests for Header.included_headers attribute."""

    def test_header_has_included_headers_attribute(self):
        """Header should have included_headers attribute."""
        header = Header(path="test.h", declarations=[])
        assert hasattr(header, "included_headers")

    def test_included_headers_defaults_to_empty_set(self):
        """included_headers defaults to empty set."""
        header = Header(path="test.h", declarations=[])
        assert header.included_headers == set()

    def test_included_headers_can_be_set(self):
        """included_headers can be populated."""
        header = Header(path="test.h", declarations=[])
        header.included_headers = {"stdio.h", "stdlib.h", "stdint.h"}
        assert "stdio.h" in header.included_headers
        assert "stdlib.h" in header.included_headers
        assert len(header.included_headers) == 3

    def test_header_constructor_accepts_included_headers(self):
        """Header constructor should accept included_headers parameter."""
        included = {"stdio.h", "string.h"}
        header = Header(path="test.h", declarations=[], included_headers=included)
        assert header.included_headers == included
