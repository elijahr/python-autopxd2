"""Macro extraction tests for libclang backend.

These tests verify that various #define macro types are correctly extracted
as constants with appropriate types.
"""

import pytest

from autopxd.backends import get_backend
from autopxd.ir import Constant, CType
from test.assertions import assert_pxd_equals

# These tests require libclang - exclude with: pytest -m "not libclang"
pytestmark = pytest.mark.libclang


@pytest.fixture
def libclang_backend():
    """Provide libclang backend for macro tests."""
    return get_backend("libclang")


class TestSimpleNumericMacros:
    """Test extraction of simple numeric macros."""

    def test_decimal_macro(self, libclang_backend):
        """Simple decimal macros should be extracted as int."""
        code = """
        #define SIZE 100
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 1
        assert constants[0].name == "SIZE"
        assert constants[0].value == 100
        assert constants[0].is_macro is True
        assert constants[0].type == CType("int")

    def test_hex_macro(self, libclang_backend):
        """Hexadecimal macros should be extracted as int."""
        code = """
        #define MASK 0xFF
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 1
        assert constants[0].name == "MASK"
        assert constants[0].value == 0xFF
        assert constants[0].type == CType("int")

    def test_octal_macro(self, libclang_backend):
        """Octal macros should be extracted as int."""
        code = """
        #define MODE 0755
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 1
        assert constants[0].name == "MODE"
        assert constants[0].value == 0o755
        assert constants[0].type == CType("int")

    def test_binary_macro(self, libclang_backend):
        """Binary macros should be extracted as int."""
        code = """
        #define FLAGS 0b1010
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 1
        assert constants[0].name == "FLAGS"
        assert constants[0].value == 0b1010
        assert constants[0].type == CType("int")

    def test_multiple_macros(self, libclang_backend):
        """Multiple macros should all be extracted."""
        code = """
        #define A 1
        #define B 2
        #define C 3
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 3
        names = {c.name for c in constants}
        assert names == {"A", "B", "C"}

    def test_macro_generates_int_declaration(self, tmp_path):
        """Integer macros should generate 'int NAME' in pxd output."""
        assert_pxd_equals(
            """
            #define SIZE 100
            #define COUNT 50
            void use_values(void);
            """,
            """cdef extern from "test.h":

    int SIZE

    int COUNT

    void use_values()
""",
            tmp_path,
            backend="libclang",
        )


class TestMacrosWithSuffixes:
    """Test extraction of macros with type suffixes."""

    def test_macro_with_ull_suffix(self, libclang_backend):
        """Macros with ULL suffix should be extracted as int."""
        code = """
        #define SIZE_ULL 100ULL
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 1
        assert constants[0].name == "SIZE_ULL"
        assert constants[0].value == 100
        assert constants[0].type == CType("int")

    def test_macro_with_l_suffix(self, libclang_backend):
        """Macros with L suffix should be extracted as int."""
        code = """
        #define SIZE_L 100L
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 1
        assert constants[0].name == "SIZE_L"
        assert constants[0].value == 100

    def test_macro_with_u_suffix(self, libclang_backend):
        """Macros with U suffix should be extracted as int."""
        code = """
        #define SIZE_U 100U
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 1
        assert constants[0].name == "SIZE_U"
        assert constants[0].value == 100

    def test_hex_with_suffix(self, libclang_backend):
        """Hex macros with suffixes should be extracted."""
        code = """
        #define HEX_UL 0xFFUL
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 1
        assert constants[0].name == "HEX_UL"
        assert constants[0].value == 0xFF


class TestFloatMacros:
    """Test extraction of floating-point macros."""

    def test_float_macro(self, libclang_backend):
        """Float macros should be extracted as double."""
        code = """
        #define PI 3.14159
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 1
        assert constants[0].name == "PI"
        assert abs(constants[0].value - 3.14159) < 0.00001
        assert constants[0].type == CType("double")

    def test_float_with_f_suffix(self, libclang_backend):
        """Float macros with f suffix should be extracted as double."""
        code = """
        #define PI_F 3.14f
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 1
        assert constants[0].name == "PI_F"
        assert abs(constants[0].value - 3.14) < 0.01

    def test_scientific_notation(self, libclang_backend):
        """Scientific notation macros should be extracted as double."""
        code = """
        #define LARGE 1e10
        #define SMALL 1.5e-5
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 2
        names = {c.name: c for c in constants}
        assert abs(names["LARGE"].value - 1e10) < 1e5
        assert abs(names["SMALL"].value - 1.5e-5) < 1e-10

    def test_float_generates_double_declaration(self, tmp_path):
        """Float macros should generate 'double NAME' in pxd output."""
        assert_pxd_equals(
            """
            #define PI 3.14159
            void use_pi(void);
            """,
            """cdef extern from "test.h":

    double PI

    void use_pi()
""",
            tmp_path,
            backend="libclang",
        )


class TestStringMacros:
    """Test extraction of string literal macros."""

    def test_string_macro(self, libclang_backend):
        """String macros should be extracted with const char type."""
        code = """
        #define VERSION "1.0.0"
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 1
        assert constants[0].name == "VERSION"
        assert constants[0].value == '"1.0.0"'
        assert constants[0].type == CType("char", ["const"])

    def test_empty_string_macro(self, libclang_backend):
        """Empty string macros should be extracted."""
        code = """
        #define EMPTY ""
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 1
        assert constants[0].name == "EMPTY"
        assert constants[0].value == '""'

    def test_string_generates_const_char_ptr(self, tmp_path):
        """String macros should generate 'const char* NAME' in pxd output."""
        assert_pxd_equals(
            """
            #define VERSION "1.0.0"
            void get_version(void);
            """,
            """cdef extern from "test.h":

    const char* VERSION

    void get_version()
""",
            tmp_path,
            backend="libclang",
        )


class TestExpressionMacros:
    """Test extraction of expression macros."""

    def test_parenthesized_expression(self, libclang_backend):
        """Parenthesized expressions should be extracted as int."""
        code = """
        #define TOTAL (10 + 20)
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 1
        assert constants[0].name == "TOTAL"
        assert constants[0].type == CType("int")
        # Value is None for expressions (we don't evaluate)
        assert constants[0].value is None

    def test_bitwise_expression(self, libclang_backend):
        """Bitwise expressions should be extracted as int."""
        code = """
        #define FLAGS (0x01 | 0x02 | 0x04)
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 1
        assert constants[0].name == "FLAGS"
        assert constants[0].type == CType("int")

    def test_shift_expression(self, libclang_backend):
        """Shift expressions should be extracted as int."""
        code = """
        #define SHIFTED (1 << 4)
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 1
        assert constants[0].name == "SHIFTED"
        assert constants[0].type == CType("int")

    def test_macro_referencing_other_macro(self, libclang_backend):
        """Macros referencing other macros should be extracted."""
        code = """
        #define BASE 10
        #define DOUBLE_BASE (BASE * 2)
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 2
        names = {c.name for c in constants}
        assert names == {"BASE", "DOUBLE_BASE"}

    def test_negative_number_expression(self, libclang_backend):
        """Negative numbers (expressions) should be extracted as int."""
        code = """
        #define NEGATIVE -1
        #define ALSO_NEGATIVE (-100)
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 2
        names = {c.name for c in constants}
        assert names == {"NEGATIVE", "ALSO_NEGATIVE"}

    def test_expression_generates_int_declaration(self, tmp_path):
        """Expression macros should generate 'int NAME' in pxd output."""
        assert_pxd_equals(
            """
            #define A 10
            #define B 20
            #define TOTAL (A + B)
            void use_total(void);
            """,
            """cdef extern from "test.h":

    int A

    int B

    int TOTAL

    void use_total()
""",
            tmp_path,
            backend="libclang",
        )


class TestUnsupportedMacros:
    """Test macros that should NOT be extracted."""

    def test_function_like_macro_ignored(self, libclang_backend):
        """Function-like macros should be ignored."""
        code = """
        #define MAX(a, b) ((a) > (b) ? (a) : (b))
        #define MIN(a, b) ((a) < (b) ? (a) : (b))
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 0

    def test_empty_macro_ignored(self, libclang_backend):
        """Empty macros (no value) should be ignored."""
        code = """
        #define EMPTY
        #define ALSO_EMPTY
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 0

    def test_string_concatenation_ignored(self, libclang_backend):
        """String concatenation macros should be ignored."""
        code = """
        #define CONCAT "hello" "world"
        void f(void);
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        # String concat is multiple tokens including strings - should be ignored
        assert len(constants) == 0


class TestMacroWithOtherDeclarations:
    """Test macros alongside other declarations."""

    def test_macros_ordered_before_functions(self, tmp_path):
        """Macros should appear before functions in output."""
        assert_pxd_equals(
            """
            void first_func(void);
            #define MIDDLE 50
            void last_func(void);
            """,
            """cdef extern from "test.h":

    int MIDDLE

    void first_func()

    void last_func()
""",
            tmp_path,
            backend="libclang",
        )

    def test_macros_with_structs(self, libclang_backend):
        """Macros should work alongside struct declarations."""
        code = """
        #define SIZE 10
        struct Data {
            int values[SIZE];
        };
        """
        header = libclang_backend.parse(code, "test.h")
        constants = [d for d in header.declarations if isinstance(d, Constant)]
        assert len(constants) == 1
        assert constants[0].name == "SIZE"

    def test_mixed_macro_types(self, tmp_path):
        """Mixed macro types should generate appropriate declarations."""
        assert_pxd_equals(
            """
            #define INT_VAL 42
            #define FLOAT_VAL 3.14
            #define STR_VAL "hello"
            #define EXPR_VAL (1 + 2)
            void f(void);
            """,
            """cdef extern from "test.h":

    int INT_VAL

    double FLOAT_VAL

    const char* STR_VAL

    int EXPR_VAL

    void f()
""",
            tmp_path,
            backend="libclang",
        )
