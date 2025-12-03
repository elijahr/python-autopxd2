# pylint: disable=attribute-defined-outside-init
"""Tests for the libclang backend."""

import pytest

from autopxd.backends.libclang_backend import (
    LibclangBackend,
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

# Mark all tests in this module as requiring libclang
pytestmark = pytest.mark.libclang


class TestLibclangBackendBasic:
    """Test basic parsing functionality."""

    def setup_method(self):
        self.backend = LibclangBackend()

    def test_backend_properties(self):
        assert self.backend.name == "libclang"
        assert self.backend.supports_macros is False  # Limited by Python bindings
        assert self.backend.supports_cpp is True

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
        assert func.parameters[1].name == "b"

    def test_variadic_function(self):
        code = "int printf(const char* fmt, ...);"
        header = self.backend.parse(code, "test.h")
        func = header.declarations[0]
        assert isinstance(func, Function)
        assert func.name == "printf"
        assert func.is_variadic is True
        assert len(func.parameters) == 1

    def test_global_variable(self):
        code = "int count;"
        header = self.backend.parse(code, "test.h")
        assert len(header.declarations) == 1
        var = header.declarations[0]
        assert isinstance(var, Variable)
        assert var.name == "count"


class TestTypeConversion:
    """Test type conversion."""

    def setup_method(self):
        self.backend = LibclangBackend()

    def test_pointer_type(self):
        code = "int* ptr;"
        header = self.backend.parse(code, "test.h")
        var = header.declarations[0]
        assert isinstance(var.type, Pointer)
        assert isinstance(var.type.pointee, CType)

    def test_double_pointer(self):
        code = "char** argv;"
        header = self.backend.parse(code, "test.h")
        var = header.declarations[0]
        assert isinstance(var.type, Pointer)
        assert isinstance(var.type.pointee, Pointer)

    def test_const_pointer(self):
        code = "const char* str;"
        header = self.backend.parse(code, "test.h")
        var = header.declarations[0]
        assert isinstance(var.type, Pointer)
        pointee = var.type.pointee
        assert isinstance(pointee, CType)
        # libclang includes const in the type

    def test_array_fixed_size(self):
        code = "int arr[10];"
        header = self.backend.parse(code, "test.h")
        var = header.declarations[0]
        assert isinstance(var.type, Array)
        assert var.type.size == 10

    def test_array_flexible(self):
        code = "extern int arr[];"
        header = self.backend.parse(code, "test.h")
        var = header.declarations[0]
        assert isinstance(var.type, Array)
        assert var.type.size is None


class TestStructs:
    """Test struct parsing."""

    def setup_method(self):
        self.backend = LibclangBackend()

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


class TestEnums:
    """Test enum parsing."""

    def setup_method(self):
        self.backend = LibclangBackend()

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


class TestTypedefs:
    """Test typedef parsing."""

    def setup_method(self):
        self.backend = LibclangBackend()

    def test_simple_typedef(self):
        code = "typedef int myint;"
        header = self.backend.parse(code, "test.h")
        assert len(header.declarations) == 1
        typedef = header.declarations[0]
        assert isinstance(typedef, Typedef)
        assert typedef.name == "myint"

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


class TestCppSupport:
    """Test C++ specific features."""

    def setup_method(self):
        self.backend = LibclangBackend()

    def test_cpp_class(self):
        code = """
        class Widget {
        public:
            int width;
            int height;
        };
        """
        header = self.backend.parse(code, "test.hpp", extra_args=["-x", "c++"])
        # Classes are treated as structs
        assert len(header.declarations) == 1
        struct = header.declarations[0]
        assert isinstance(struct, Struct)
        assert struct.name == "Widget"

    def test_cpp_namespace_function(self):
        # For now, we only handle top-level declarations
        # Namespace support could be added later
        code = """
        int global_func(int x);
        """
        header = self.backend.parse(code, "test.hpp", extra_args=["-x", "c++"])
        assert len(header.declarations) == 1
        func = header.declarations[0]
        assert func.name == "global_func"


class TestComplexCases:
    """Test complex parsing cases."""

    def setup_method(self):
        self.backend = LibclangBackend()

    def test_multiple_declarations(self):
        code = """
        struct Point { int x; int y; };
        typedef struct Point Point;
        int distance(Point a, Point b);
        """
        header = self.backend.parse(code, "test.h")
        # Should have struct, typedef, and function
        assert len(header.declarations) >= 2

    def test_array_of_pointers(self):
        code = "char* argv[10];"
        header = self.backend.parse(code, "test.h")
        var = header.declarations[0]
        assert isinstance(var.type, Array)
        assert var.type.size == 10
        assert isinstance(var.type.element_type, Pointer)

    def test_empty_struct(self):
        code = "struct Empty {};"
        header = self.backend.parse(code, "test.h")
        struct = header.declarations[0]
        assert struct.name == "Empty"
        assert len(struct.fields) == 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        self.backend = LibclangBackend()

    def test_unsigned_types(self):
        code = "unsigned long count;"
        header = self.backend.parse(code, "test.h")
        var = header.declarations[0]
        assert "unsigned" in var.type.name or "unsigned" in var.type.qualifiers

    def test_long_long(self):
        code = "long long value;"
        header = self.backend.parse(code, "test.h")
        var = header.declarations[0]
        assert "long long" in var.type.name

    def test_forward_declaration_skipped(self):
        code = """
        struct Forward;
        struct Defined { int x; };
        """
        header = self.backend.parse(code, "test.h")
        # Only the defined struct should be included
        assert len(header.declarations) == 1
        assert header.declarations[0].name == "Defined"

    def test_parse_error(self):
        code = "this is not valid C"
        with pytest.raises(RuntimeError):
            self.backend.parse(code, "test.h")
