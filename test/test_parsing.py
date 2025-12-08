"""Core parsing tests that run on both backends."""

from autopxd.ir import (
    CType,
    Enum,
    Function,
    FunctionPointer,
    Pointer,
    Struct,
    Typedef,
    Variable,
)


class TestFunctionParsing:
    """Test function declaration parsing."""

    def test_simple_function(self, backend):
        code = "int foo(void);"
        header = backend.parse(code, "test.h")
        assert len(header.declarations) == 1
        func = header.declarations[0]
        assert isinstance(func, Function)
        assert func.name == "foo"
        assert isinstance(func.return_type, CType)
        assert func.return_type.name == "int"
        assert func.parameters == []
        assert func.is_variadic is False

    def test_function_with_params(self, backend):
        code = "int add(int a, int b);"
        header = backend.parse(code, "test.h")
        func = header.declarations[0]
        assert isinstance(func, Function)
        assert func.name == "add"
        assert len(func.parameters) == 2
        assert func.parameters[0].name == "a"
        assert func.parameters[1].name == "b"

    def test_variadic_function(self, backend):
        code = "int printf(const char* fmt, ...);"
        header = backend.parse(code, "test.h")
        func = header.declarations[0]
        assert isinstance(func, Function)
        assert func.name == "printf"
        assert func.is_variadic is True
        assert len(func.parameters) == 1


class TestVariableParsing:
    """Test variable declaration parsing."""

    def test_global_variable(self, backend):
        code = "int count;"
        header = backend.parse(code, "test.h")
        assert len(header.declarations) == 1
        var = header.declarations[0]
        assert isinstance(var, Variable)
        assert var.name == "count"


class TestStructParsing:
    """Test struct parsing."""

    def test_simple_struct(self, backend):
        code = """
        struct Point {
            int x;
            int y;
        };
        """
        header = backend.parse(code, "test.h")
        assert len(header.declarations) == 1
        struct = header.declarations[0]
        assert isinstance(struct, Struct)
        assert struct.name == "Point"
        assert struct.is_union is False
        assert len(struct.fields) == 2
        assert struct.fields[0].name == "x"
        assert struct.fields[1].name == "y"

    def test_union(self, backend):
        code = """
        union Data {
            int i;
            float f;
        };
        """
        header = backend.parse(code, "test.h")
        struct = header.declarations[0]
        assert isinstance(struct, Struct)
        assert struct.name == "Data"
        assert struct.is_union is True

    def test_struct_with_pointers(self, backend):
        code = """
        struct Node {
            int value;
            struct Node* next;
        };
        """
        header = backend.parse(code, "test.h")
        struct = header.declarations[0]
        assert len(struct.fields) == 2
        next_field = struct.fields[1]
        assert next_field.name == "next"
        assert isinstance(next_field.type, Pointer)

    def test_empty_struct(self, backend):
        code = "struct Empty {};"
        header = backend.parse(code, "test.h")
        struct = header.declarations[0]
        assert struct.name == "Empty"
        assert len(struct.fields) == 0


class TestEnumParsing:
    """Test enum parsing."""

    def test_simple_enum(self, backend):
        code = """
        enum Color {
            RED,
            GREEN,
            BLUE
        };
        """
        header = backend.parse(code, "test.h")
        assert len(header.declarations) == 1
        enum = header.declarations[0]
        assert isinstance(enum, Enum)
        assert enum.name == "Color"
        assert len(enum.values) == 3
        assert enum.values[0].name == "RED"
        assert enum.values[0].value == 0
        assert enum.values[1].value == 1
        assert enum.values[2].value == 2

    def test_enum_with_explicit_values(self, backend):
        code = """
        enum Flags {
            FLAG_A = 1,
            FLAG_B = 2,
            FLAG_C = 4
        };
        """
        header = backend.parse(code, "test.h")
        enum = header.declarations[0]
        assert enum.values[0].value == 1
        assert enum.values[1].value == 2
        assert enum.values[2].value == 4


class TestTypedefParsing:
    """Test typedef parsing."""

    def test_simple_typedef(self, backend):
        code = "typedef int myint;"
        header = backend.parse(code, "test.h")
        assert len(header.declarations) == 1
        typedef = header.declarations[0]
        assert isinstance(typedef, Typedef)
        assert typedef.name == "myint"

    def test_pointer_typedef(self, backend):
        code = "typedef char* string;"
        header = backend.parse(code, "test.h")
        typedef = header.declarations[0]
        assert isinstance(typedef, Typedef)
        assert typedef.name == "string"
        assert isinstance(typedef.underlying_type, Pointer)

    def test_function_pointer_typedef(self, backend):
        code = "typedef int (*callback)(int, int);"
        header = backend.parse(code, "test.h")
        typedef = header.declarations[0]
        assert isinstance(typedef, Typedef)
        assert typedef.name == "callback"
        assert isinstance(typedef.underlying_type, Pointer)
        pointee = typedef.underlying_type.pointee
        assert isinstance(pointee, FunctionPointer)
        assert len(pointee.parameters) == 2
