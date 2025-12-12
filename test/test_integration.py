# pylint: disable=attribute-defined-outside-init,import-outside-toplevel
"""Integration tests for the backend → IR → writer pipeline.

These tests verify that the new architecture produces correct output
for various C constructs.
"""

import pytest

from test.assertions import assert_ir_to_pxd_equals, assert_pxd_equals


class TestIntegrationBasic:
    """Test basic C constructs through the full pipeline."""

    def test_simple_function(self, tmp_path):
        assert_pxd_equals(
            "int foo(void);",
            """cdef extern from "test.h":

    int foo()
""",
            tmp_path,
        )

    def test_function_with_params(self, tmp_path):
        assert_pxd_equals(
            "int add(int a, int b);",
            """cdef extern from "test.h":

    int add(int a, int b)
""",
            tmp_path,
        )

    def test_simple_struct(self, tmp_path):
        assert_pxd_equals(
            """
            struct Point {
                int x;
                int y;
            };
            """,
            """cdef extern from "test.h":

    cdef struct Point:
        int x
        int y
""",
            tmp_path,
        )

    def test_simple_enum(self, tmp_path):
        assert_pxd_equals(
            """
            enum Color {
                RED,
                GREEN,
                BLUE
            };
            """,
            """cdef extern from "test.h":

    cdef enum Color:
        RED
        GREEN
        BLUE
""",
            tmp_path,
        )

    def test_global_variable(self, tmp_path):
        assert_pxd_equals(
            "int count;",
            """cdef extern from "test.h":

    int count
""",
            tmp_path,
        )

    def test_typedef(self, tmp_path):
        assert_pxd_equals(
            "typedef int myint;",
            """cdef extern from "test.h":

    ctypedef int myint
""",
            tmp_path,
        )


class TestIntegrationPointers:
    """Test pointer handling through the pipeline."""

    def test_pointer_variable(self, tmp_path):
        assert_pxd_equals(
            "int* ptr;",
            """cdef extern from "test.h":

    int* ptr
""",
            tmp_path,
        )

    def test_const_char_pointer(self, tmp_path):
        assert_pxd_equals(
            "const char* str;",
            """cdef extern from "test.h":

    const char* str
""",
            tmp_path,
        )

    def test_double_pointer(self, tmp_path):
        assert_pxd_equals(
            "char** argv;",
            """cdef extern from "test.h":

    char** argv
""",
            tmp_path,
        )


class TestIntegrationArrays:
    """Test array handling through the pipeline."""

    def test_fixed_size_array(self, tmp_path):
        assert_pxd_equals(
            "int arr[10];",
            """cdef extern from "test.h":

    int arr[10]
""",
            tmp_path,
        )

    def test_array_in_struct(self, tmp_path):
        assert_pxd_equals(
            """
            struct Buffer {
                char data[256];
            };
            """,
            """cdef extern from "test.h":

    cdef struct Buffer:
        char data[256]
""",
            tmp_path,
        )


class TestIntegrationComplex:
    """Test complex C constructs through the pipeline."""

    def test_typedef_struct(self, tmp_path):
        assert_pxd_equals(
            """
            typedef struct {
                int x;
                int y;
            } Point;
            """,
            """cdef extern from "test.h":

    ctypedef struct Point:
        int x
        int y
""",
            tmp_path,
        )

    def test_variadic_function(self, tmp_path):
        assert_pxd_equals(
            "int printf(const char* fmt, ...);",
            """cdef extern from "test.h":

    int printf(const char* fmt, ...)
""",
            tmp_path,
        )

    def test_enum_with_values(self, tmp_path):
        assert_pxd_equals(
            """
            enum Flags {
                FLAG_A = 1,
                FLAG_B = 2,
                FLAG_C = 4
            };
            """,
            """cdef extern from "test.h":

    cdef enum Flags:
        FLAG_A
        FLAG_B
        FLAG_C
""",
            tmp_path,
        )

    def test_function_pointer_typedef(self, tmp_path):
        assert_pxd_equals(
            "typedef int (*callback)(int, int);",
            """cdef extern from "test.h":

    ctypedef int (*callback)(int, int)
""",
            tmp_path,
        )

    def test_union(self, tmp_path):
        assert_pxd_equals(
            """
            union Data {
                int i;
                float f;
            };
            """,
            """cdef extern from "test.h":

    cdef union Data:
        int i
        float f
""",
            tmp_path,
        )


class TestIntegrationKeywords:
    """Test Python keyword escaping through the pipeline."""

    def test_keyword_struct_name(self, tmp_path):
        assert_pxd_equals(
            """
            struct class {
                int value;
            };
            """,
            """cdef extern from "test.h":

    cdef struct class_ "class":
        int value
""",
            tmp_path,
        )

    def test_keyword_field_name(self, tmp_path):
        assert_pxd_equals(
            """
            struct Foo {
                int import;
            };
            """,
            """cdef extern from "test.h":

    cdef struct Foo:
        int import_ "import"
""",
            tmp_path,
        )


class TestIntegrationStdint:
    """Test stdint type handling through the pipeline.

    Note: pycparser doesn't know about stdint types without preprocessing.
    In the full autopxd pipeline, preprocessing defines these types.
    Here we test that the IR writer correctly identifies and imports them
    when they appear in the IR.
    """

    def test_stdint_import_from_ir(self, tmp_path):
        """Test that stdint types in IR are properly imported."""
        from autopxd.ir import (
            CType,
            Field,
            Header,
            Struct,
        )

        # Directly create IR with stdint types (simulating preprocessed code)
        header = Header(
            "test.h",
            [
                Struct(
                    "Data",
                    [
                        Field("a", CType("uint32_t")),
                        Field("b", CType("int64_t")),
                    ],
                )
            ],
        )
        assert_ir_to_pxd_equals(
            header,
            """from libc.stdint cimport int64_t, uint32_t

cdef extern from "test.h":

    cdef struct Data:
        uint32_t a
        int64_t b
""",
            tmp_path,
        )


# =============================================================================
# Libclang Backend Integration Tests
# =============================================================================


@pytest.mark.libclang
class TestLibclangIntegrationBasic:
    """Test basic C constructs through libclang → IR → writer pipeline."""

    def test_simple_function(self, tmp_path):
        assert_pxd_equals(
            "int foo(void);",
            """cdef extern from "test.h":

    int foo()
""",
            tmp_path,
            backend="libclang",
        )

    def test_function_with_params(self, tmp_path):
        assert_pxd_equals(
            "int add(int a, int b);",
            """cdef extern from "test.h":

    int add(int a, int b)
""",
            tmp_path,
            backend="libclang",
        )

    def test_simple_struct(self, tmp_path):
        assert_pxd_equals(
            """
            struct Point {
                int x;
                int y;
            };
            """,
            """cdef extern from "test.h":

    cdef struct Point:
        int x
        int y
""",
            tmp_path,
            backend="libclang",
        )

    def test_simple_enum(self, tmp_path):
        assert_pxd_equals(
            """
            enum Color {
                RED,
                GREEN,
                BLUE
            };
            """,
            """cdef extern from "test.h":

    cdef enum Color:
        RED
        GREEN
        BLUE
""",
            tmp_path,
            backend="libclang",
        )

    def test_global_variable(self, tmp_path):
        assert_pxd_equals(
            "int count;",
            """cdef extern from "test.h":

    int count
""",
            tmp_path,
            backend="libclang",
        )

    def test_typedef(self, tmp_path):
        assert_pxd_equals(
            "typedef int myint;",
            """cdef extern from "test.h":

    ctypedef int myint
""",
            tmp_path,
            backend="libclang",
        )


@pytest.mark.libclang
class TestLibclangIntegrationComplex:
    """Test complex C constructs through libclang pipeline."""

    def test_variadic_function(self, tmp_path):
        assert_pxd_equals(
            "int printf(const char* fmt, ...);",
            """cdef extern from "test.h":

    int printf(const char* fmt, ...)
""",
            tmp_path,
            backend="libclang",
        )

    def test_union(self, tmp_path):
        assert_pxd_equals(
            """
            union Data {
                int i;
                float f;
            };
            """,
            """cdef extern from "test.h":

    cdef union Data:
        int i
        float f
""",
            tmp_path,
            backend="libclang",
        )

    def test_pointer_variable(self, tmp_path):
        assert_pxd_equals(
            "int* ptr;",
            """cdef extern from "test.h":

    int* ptr
""",
            tmp_path,
            backend="libclang",
        )

    def test_array_variable(self, tmp_path):
        assert_pxd_equals(
            "int arr[10];",
            """cdef extern from "test.h":

    int arr[10]
""",
            tmp_path,
            backend="libclang",
        )


@pytest.mark.libclang
class TestLibclangIntegrationCpp:
    """Test C++ specific features through libclang pipeline."""

    def test_cpp_class(self, tmp_path):
        assert_pxd_equals(
            """
            class Widget {
            public:
                int width;
                int height;
            };
            """,
            """cdef extern from "test.hpp":

    cdef cppclass Widget:
        int width
        int height
""",
            tmp_path,
            backend="libclang",
            filename="test.hpp",
            cplus=True,
            extra_args=["-x", "c++"],
        )

    def test_cpp_function(self, tmp_path):
        assert_pxd_equals(
            "int compute(int x, int y);",
            """cdef extern from "test.hpp":

    int compute(int x, int y)
""",
            tmp_path,
            backend="libclang",
            filename="test.hpp",
            extra_args=["-x", "c++"],
        )


@pytest.mark.libclang
class TestBackendComparison:
    """Test that both backends produce similar output for the same input."""

    def test_simple_struct_both_backends(self, tmp_path):
        code = """
        struct Point {
            int x;
            int y;
        };
        """
        expected = """cdef extern from "test.h":

    cdef struct Point:
        int x
        int y
"""
        # Test pycparser
        assert_pxd_equals(code, expected, tmp_path, backend="pycparser")
        # Test libclang
        assert_pxd_equals(code, expected, tmp_path, backend="libclang")

    def test_simple_function_both_backends(self, tmp_path):
        code = "int add(int a, int b);"
        expected = """cdef extern from "test.h":

    int add(int a, int b)
"""
        # Test pycparser
        assert_pxd_equals(code, expected, tmp_path, backend="pycparser")
        # Test libclang
        assert_pxd_equals(code, expected, tmp_path, backend="libclang")

    def test_enum_both_backends(self, tmp_path):
        code = """
        enum Color { RED, GREEN, BLUE };
        """
        expected = """cdef extern from "test.h":

    cdef enum Color:
        RED
        GREEN
        BLUE
"""
        # Test pycparser
        assert_pxd_equals(code, expected, tmp_path, backend="pycparser")
        # Test libclang
        assert_pxd_equals(code, expected, tmp_path, backend="libclang")
