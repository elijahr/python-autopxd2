# pylint: disable=attribute-defined-outside-init
"""Tests for the pycparser backend."""

from autopxd.backends.pycparser_backend import (
    PycparserBackend,
)
from autopxd.ir import (
    Array,
    CType,
    Enum,
    Function,
    FunctionPointer,
    Pointer,
    Struct,
    Typedef,
    Variable,
)


class TestPycparserBackendBasic:
    """Test basic parsing functionality."""

    def setup_method(self):
        self.backend = PycparserBackend()

    def test_backend_properties(self):
        assert self.backend.name == "pycparser"
        assert self.backend.supports_macros is False
        assert self.backend.supports_cpp is False

    def test_simple_function(self):
        code = "int foo(void);"
        header = self.backend.parse(code, "test.h")
        assert len(header.declarations) == 1
        func = header.declarations[0]
        assert isinstance(func, Function)
        assert func.name == "foo"
        assert isinstance(func.return_type, CType)
        assert func.return_type.name == "int"
        assert func.parameters == []
        assert func.is_variadic is False

    def test_function_with_params(self):
        code = "int add(int a, int b);"
        header = self.backend.parse(code, "test.h")
        func = header.declarations[0]
        assert isinstance(func, Function)
        assert func.name == "add"
        assert len(func.parameters) == 2
        assert func.parameters[0].name == "a"
        assert func.parameters[0].type.name == "int"
        assert func.parameters[1].name == "b"

    def test_variadic_function(self):
        code = "int printf(const char* fmt, ...);"
        header = self.backend.parse(code, "test.h")
        func = header.declarations[0]
        assert isinstance(func, Function)
        assert func.name == "printf"
        assert func.is_variadic is True
        assert len(func.parameters) == 1
        param = func.parameters[0]
        assert isinstance(param.type, Pointer)

    def test_global_variable(self):
        code = "int count;"
        header = self.backend.parse(code, "test.h")
        assert len(header.declarations) == 1
        var = header.declarations[0]
        assert isinstance(var, Variable)
        assert var.name == "count"
        assert var.type.name == "int"


class TestTypeConversion:
    """Test type conversion."""

    def setup_method(self):
        self.backend = PycparserBackend()

    def test_pointer_type(self):
        code = "int* ptr;"
        header = self.backend.parse(code, "test.h")
        var = header.declarations[0]
        assert isinstance(var.type, Pointer)
        assert isinstance(var.type.pointee, CType)
        assert var.type.pointee.name == "int"

    def test_double_pointer(self):
        code = "char** argv;"
        header = self.backend.parse(code, "test.h")
        var = header.declarations[0]
        assert isinstance(var.type, Pointer)
        assert isinstance(var.type.pointee, Pointer)
        assert var.type.pointee.pointee.name == "char"

    def test_const_pointer(self):
        code = "const char* str;"
        header = self.backend.parse(code, "test.h")
        var = header.declarations[0]
        assert isinstance(var.type, Pointer)
        pointee = var.type.pointee
        assert isinstance(pointee, CType)
        assert pointee.name == "char"
        assert "const" in pointee.qualifiers

    def test_array_fixed_size(self):
        code = "int arr[10];"
        header = self.backend.parse(code, "test.h")
        var = header.declarations[0]
        assert isinstance(var.type, Array)
        assert var.type.size == 10
        assert var.type.element_type.name == "int"

    def test_array_flexible(self):
        code = "int arr[];"
        header = self.backend.parse(code, "test.h")
        var = header.declarations[0]
        assert isinstance(var.type, Array)
        assert var.type.size is None

    def test_qualified_type(self):
        code = "volatile int flag;"
        header = self.backend.parse(code, "test.h")
        var = header.declarations[0]
        assert isinstance(var.type, CType)
        assert "volatile" in var.type.qualifiers


class TestStructs:
    """Test struct parsing."""

    def setup_method(self):
        self.backend = PycparserBackend()

    def test_simple_struct(self):
        code = """
        struct Point {
            int x;
            int y;
        };
        """
        header = self.backend.parse(code, "test.h")
        assert len(header.declarations) == 1
        struct = header.declarations[0]
        assert isinstance(struct, Struct)
        assert struct.name == "Point"
        assert struct.is_union is False
        assert len(struct.fields) == 2
        assert struct.fields[0].name == "x"
        assert struct.fields[1].name == "y"

    def test_union(self):
        code = """
        union Data {
            int i;
            float f;
        };
        """
        header = self.backend.parse(code, "test.h")
        struct = header.declarations[0]
        assert isinstance(struct, Struct)
        assert struct.name == "Data"
        assert struct.is_union is True

    def test_struct_with_pointers(self):
        code = """
        struct Node {
            int value;
            struct Node* next;
        };
        """
        header = self.backend.parse(code, "test.h")
        struct = header.declarations[0]
        assert len(struct.fields) == 2
        next_field = struct.fields[1]
        assert next_field.name == "next"
        assert isinstance(next_field.type, Pointer)

    def test_typedef_struct(self):
        code = """
        typedef struct {
            int x;
            int y;
        } Point;
        """
        header = self.backend.parse(code, "test.h")
        # Should create a struct named Point
        assert len(header.declarations) == 1
        struct = header.declarations[0]
        assert isinstance(struct, Struct)
        assert struct.name == "Point"


class TestEnums:
    """Test enum parsing."""

    def setup_method(self):
        self.backend = PycparserBackend()

    def test_simple_enum(self):
        code = """
        enum Color {
            RED,
            GREEN,
            BLUE
        };
        """
        header = self.backend.parse(code, "test.h")
        assert len(header.declarations) == 1
        enum = header.declarations[0]
        assert isinstance(enum, Enum)
        assert enum.name == "Color"
        assert len(enum.values) == 3
        assert enum.values[0].name == "RED"
        assert enum.values[0].value == 0
        assert enum.values[1].value == 1
        assert enum.values[2].value == 2

    def test_enum_with_explicit_values(self):
        code = """
        enum Flags {
            FLAG_A = 1,
            FLAG_B = 2,
            FLAG_C = 4
        };
        """
        header = self.backend.parse(code, "test.h")
        enum = header.declarations[0]
        assert enum.values[0].value == 1
        assert enum.values[1].value == 2
        assert enum.values[2].value == 4

    def test_enum_with_expression(self):
        code = """
        enum Shifts {
            SHIFT_0 = 1,
            SHIFT_1 = 1 << 1,
            SHIFT_2 = 1 << 2
        };
        """
        header = self.backend.parse(code, "test.h")
        enum = header.declarations[0]
        assert enum.values[0].value == 1
        assert enum.values[1].value == 2
        assert enum.values[2].value == 4

    def test_enum_referencing_other(self):
        code = """
        enum Related {
            BASE = 10,
            DERIVED = BASE
        };
        """
        header = self.backend.parse(code, "test.h")
        enum = header.declarations[0]
        assert enum.values[0].value == 10
        # DERIVED references BASE, so value is string expression
        assert enum.values[1].value == "10"

    def test_array_with_enum_dimension(self):
        code = """
        enum Sizes { SIZE = 5 };
        int arr[SIZE];
        """
        header = self.backend.parse(code, "test.h")
        assert len(header.declarations) == 2
        arr = header.declarations[1]
        assert isinstance(arr, Variable)
        assert isinstance(arr.type, Array)
        assert arr.type.size == 5


class TestTypedefs:
    """Test typedef parsing."""

    def setup_method(self):
        self.backend = PycparserBackend()

    def test_simple_typedef(self):
        code = "typedef int myint;"
        header = self.backend.parse(code, "test.h")
        assert len(header.declarations) == 1
        typedef = header.declarations[0]
        assert isinstance(typedef, Typedef)
        assert typedef.name == "myint"
        assert typedef.underlying_type.name == "int"

    def test_pointer_typedef(self):
        code = "typedef char* string;"
        header = self.backend.parse(code, "test.h")
        typedef = header.declarations[0]
        assert isinstance(typedef, Typedef)
        assert typedef.name == "string"
        assert isinstance(typedef.underlying_type, Pointer)

    def test_function_pointer_typedef(self):
        code = "typedef int (*callback)(int, int);"
        header = self.backend.parse(code, "test.h")
        typedef = header.declarations[0]
        assert isinstance(typedef, Typedef)
        assert typedef.name == "callback"
        assert isinstance(typedef.underlying_type, Pointer)
        pointee = typedef.underlying_type.pointee
        assert isinstance(pointee, FunctionPointer)
        assert len(pointee.parameters) == 2


class TestFunctionPointers:
    """Test function pointer parsing."""

    def setup_method(self):
        self.backend = PycparserBackend()

    def test_function_pointer_param(self):
        code = "void process(int (*handler)(int));"
        header = self.backend.parse(code, "test.h")
        func = header.declarations[0]
        assert isinstance(func, Function)
        assert len(func.parameters) == 1
        param = func.parameters[0]
        assert isinstance(param.type, Pointer)
        assert isinstance(param.type.pointee, FunctionPointer)

    def test_function_returning_function_pointer(self):
        code = "int (*get_handler(void))(int);"
        header = self.backend.parse(code, "test.h")
        func = header.declarations[0]
        assert isinstance(func, Function)
        assert func.name == "get_handler"
        assert isinstance(func.return_type, Pointer)


class TestComplexCases:
    """Test complex parsing cases."""

    def setup_method(self):
        self.backend = PycparserBackend()

    def test_multiple_declarations(self):
        code = """
        struct Point { int x; int y; };
        typedef struct Point Point;
        Point origin;
        int distance(Point a, Point b);
        """
        header = self.backend.parse(code, "test.h")
        assert len(header.declarations) == 4

    def test_nested_structs(self):
        code = """
        struct Outer {
            struct Inner {
                int value;
            } inner;
        };
        """
        header = self.backend.parse(code, "test.h")
        outer = header.declarations[0]
        assert isinstance(outer, Struct)
        assert len(outer.fields) == 1
        inner_field = outer.fields[0]
        assert inner_field.name == "inner"

    def test_array_of_pointers(self):
        code = "char* argv[10];"
        header = self.backend.parse(code, "test.h")
        var = header.declarations[0]
        assert isinstance(var.type, Array)
        assert var.type.size == 10
        assert isinstance(var.type.element_type, Pointer)

    def test_pointer_to_array(self):
        code = "int (*ptr)[10];"
        header = self.backend.parse(code, "test.h")
        var = header.declarations[0]
        assert isinstance(var.type, Pointer)
        assert isinstance(var.type.pointee, Array)
        assert var.type.pointee.size == 10


class TestEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        self.backend = PycparserBackend()

    def test_empty_struct(self):
        code = "struct Empty {};"
        header = self.backend.parse(code, "test.h")
        struct = header.declarations[0]
        assert struct.name == "Empty"
        assert len(struct.fields) == 0

    def test_unsigned_types(self):
        code = "unsigned long count;"
        header = self.backend.parse(code, "test.h")
        var = header.declarations[0]
        assert var.type.name == "unsigned long"

    def test_long_long(self):
        code = "long long value;"
        header = self.backend.parse(code, "test.h")
        var = header.declarations[0]
        assert var.type.name == "long long"

    def test_function_definition_extracts_decl(self):
        code = """
        int foo(int x) {
            return x * 2;
        }
        """
        header = self.backend.parse(code, "test.h")
        assert len(header.declarations) == 1
        func = header.declarations[0]
        assert isinstance(func, Function)
        assert func.name == "foo"
