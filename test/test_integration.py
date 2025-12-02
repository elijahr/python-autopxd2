# pylint: disable=attribute-defined-outside-init,import-outside-toplevel
"""Integration tests for the backend → IR → writer pipeline.

These tests verify that the new architecture produces correct output
for various C constructs.
"""

from autopxd.backends.pycparser_backend import (
    PycparserBackend,
)
from autopxd.ir_writer import (
    write_pxd,
)


class TestIntegrationBasic:
    """Test basic C constructs through the full pipeline."""

    def setup_method(self):
        self.backend = PycparserBackend()

    def _translate(self, code: str, filename: str = "test.h") -> str:
        """Parse code and generate pxd output."""
        header = self.backend.parse(code, filename)
        return write_pxd(header)

    def test_simple_function(self):
        code = "int foo(void);"
        result = self._translate(code)
        assert 'cdef extern from "test.h":' in result
        assert "int foo()" in result

    def test_function_with_params(self):
        code = "int add(int a, int b);"
        result = self._translate(code)
        assert "int add(int a, int b)" in result

    def test_simple_struct(self):
        code = """
        struct Point {
            int x;
            int y;
        };
        """
        result = self._translate(code)
        assert "cdef struct Point:" in result
        assert "int x" in result
        assert "int y" in result

    def test_simple_enum(self):
        code = """
        enum Color {
            RED,
            GREEN,
            BLUE
        };
        """
        result = self._translate(code)
        assert "cpdef enum Color:" in result
        assert "RED" in result
        assert "GREEN" in result
        assert "BLUE" in result

    def test_global_variable(self):
        code = "int count;"
        result = self._translate(code)
        assert "int count" in result

    def test_typedef(self):
        code = "typedef int myint;"
        result = self._translate(code)
        assert "ctypedef int myint" in result


class TestIntegrationPointers:
    """Test pointer handling through the pipeline."""

    def setup_method(self):
        self.backend = PycparserBackend()

    def _translate(self, code: str, filename: str = "test.h") -> str:
        header = self.backend.parse(code, filename)
        return write_pxd(header)

    def test_pointer_variable(self):
        code = "int* ptr;"
        result = self._translate(code)
        assert "int* ptr" in result

    def test_const_char_pointer(self):
        code = "const char* str;"
        result = self._translate(code)
        assert "const char* str" in result

    def test_double_pointer(self):
        code = "char** argv;"
        result = self._translate(code)
        assert "char** argv" in result


class TestIntegrationArrays:
    """Test array handling through the pipeline."""

    def setup_method(self):
        self.backend = PycparserBackend()

    def _translate(self, code: str, filename: str = "test.h") -> str:
        header = self.backend.parse(code, filename)
        return write_pxd(header)

    def test_fixed_size_array(self):
        code = "int arr[10];"
        result = self._translate(code)
        assert "int arr[10]" in result

    def test_array_in_struct(self):
        code = """
        struct Buffer {
            char data[256];
        };
        """
        result = self._translate(code)
        assert "char data[256]" in result


class TestIntegrationComplex:
    """Test complex C constructs through the pipeline."""

    def setup_method(self):
        self.backend = PycparserBackend()

    def _translate(self, code: str, filename: str = "test.h") -> str:
        header = self.backend.parse(code, filename)
        return write_pxd(header)

    def test_typedef_struct(self):
        code = """
        typedef struct {
            int x;
            int y;
        } Point;
        """
        result = self._translate(code)
        # Should create a struct named Point
        assert "struct Point:" in result or "Point:" in result
        assert "int x" in result

    def test_variadic_function(self):
        code = "int printf(const char* fmt, ...);"
        result = self._translate(code)
        assert "printf" in result
        assert "..." in result

    def test_enum_with_values(self):
        code = """
        enum Flags {
            FLAG_A = 1,
            FLAG_B = 2,
            FLAG_C = 4
        };
        """
        result = self._translate(code)
        assert "cpdef enum Flags:" in result
        assert "FLAG_A" in result
        assert "FLAG_B" in result
        assert "FLAG_C" in result

    def test_function_pointer_typedef(self):
        code = "typedef int (*callback)(int, int);"
        result = self._translate(code)
        assert "ctypedef" in result
        assert "callback" in result

    def test_union(self):
        code = """
        union Data {
            int i;
            float f;
        };
        """
        result = self._translate(code)
        assert "cdef union Data:" in result
        assert "int i" in result
        assert "float f" in result


class TestIntegrationKeywords:
    """Test Python keyword escaping through the pipeline."""

    def setup_method(self):
        self.backend = PycparserBackend()

    def _translate(self, code: str, filename: str = "test.h") -> str:
        header = self.backend.parse(code, filename)
        return write_pxd(header)

    def test_keyword_struct_name(self):
        code = """
        struct class {
            int value;
        };
        """
        result = self._translate(code)
        # The struct name 'class' should be escaped
        assert 'class_ "class"' in result or "class_" in result

    def test_keyword_field_name(self):
        code = """
        struct Foo {
            int import;
        };
        """
        result = self._translate(code)
        assert "import_" in result


class TestIntegrationStdint:
    """Test stdint type handling through the pipeline.

    Note: pycparser doesn't know about stdint types without preprocessing.
    In the full autopxd pipeline, preprocessing defines these types.
    Here we test that the IR writer correctly identifies and imports them
    when they appear in the IR.
    """

    def test_stdint_import_from_ir(self):
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
        result = write_pxd(header)
        assert "from libc.stdint cimport" in result
        assert "uint32_t" in result
        assert "int64_t" in result
