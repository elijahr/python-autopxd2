"""Test handling of C type qualifiers that Cython doesn't support.

This module tests autopxd2's handling of type qualifiers like _Atomic,
__restrict, and _Noreturn. These qualifiers are not supported by Cython's
parser, so they must be stripped from .pxd output while preserving the
semantics through the included header file.

Design Decisions
----------------
After evaluating multiple approaches:

1. **CNAME String**: Doesn't work - Cython rejects CNAME syntax for function
   parameters (the primary use case for qualifiers).

2. **Libc Shim**: Limited scope - Only helps for _Atomic types, doesn't
   address __restrict or other qualifiers.

3. **Macro Magic**: Doesn't work - Even with #define macros in the pxd,
   Cython's parser rejects the qualifier syntax before the C preprocessor
   runs.

4. **Smart Stripping** (CURRENT): Works correctly - Qualifiers are stripped
   from .pxd declarations but preserved in the original header that's
   included via `cdef extern from`. The C compiler sees the correct types.

5. **Comment Annotation**: Possible enhancement but minimal value since:
   - The original header contains the qualifiers
   - The qualifiers don't affect Cython's type system
   - The C compiler still sees correct types via the header

6. **Typedef Workaround**: Overly complex and creates extra declarations
   for minimal benefit.

Conclusion: Smart Stripping (#4) is the optimal approach and is already
implemented. The qualifiers are only "stripped" from Cython's view of the
types; the actual C code still has full qualifier information.
"""

import pytest

from autopxd.backends import get_backend


def _libclang_available():
    """Check if libclang backend is available."""
    try:
        from autopxd.backends import list_backends

        return "libclang" in list_backends()
    except Exception:
        return False


class TestAtomicQualifier:
    """Test _Atomic type qualifier handling."""

    def test_atomic_space_syntax(self):
        """Test _Atomic int syntax (space-separated)."""
        code = "typedef _Atomic int atomic_int;"
        backend = get_backend()
        header = backend.parse(code, "test.h")

        from autopxd.ir_writer import write_pxd

        pxd = write_pxd(header)
        # _Atomic should be stripped, leaving just 'int'
        assert "ctypedef int atomic_int" in pxd
        assert "_Atomic" not in pxd

    def test_atomic_paren_syntax(self):
        """Test _Atomic(int) syntax (function-like)."""
        code = "typedef _Atomic(long) atomic_long;"
        backend = get_backend()
        header = backend.parse(code, "test.h")

        from autopxd.ir_writer import write_pxd

        pxd = write_pxd(header)
        # _Atomic should be stripped, extracting inner type
        assert "ctypedef long atomic_long" in pxd
        assert "_Atomic" not in pxd

    def test_atomic_in_struct(self):
        """Test _Atomic types in struct fields."""
        code = """
        typedef _Atomic int atomic_int;
        struct counter {
            atomic_int value;
        };
        """
        backend = get_backend()
        header = backend.parse(code, "test.h")

        from autopxd.ir_writer import write_pxd

        pxd = write_pxd(header)
        # Typedef should have _Atomic stripped
        assert "ctypedef int atomic_int" in pxd
        # Struct field uses the typedef name
        assert "atomic_int value" in pxd
        assert "_Atomic" not in pxd

    def test_atomic_in_function(self):
        """Test _Atomic in function signatures."""
        code = "void update(_Atomic int* counter);"
        backend = get_backend()
        header = backend.parse(code, "test.h")

        from autopxd.ir_writer import write_pxd

        pxd = write_pxd(header)
        # _Atomic should be stripped from parameter
        assert "void update(int* counter)" in pxd
        assert "_Atomic" not in pxd


class TestRestrictQualifier:
    """Test __restrict and __restrict__ qualifier handling."""

    @pytest.mark.skipif(not _libclang_available(), reason="__restrict is a GCC extension, not supported by pycparser")
    def test_restrict_in_function(self):
        """Test __restrict in function parameters."""
        code = """
        #include <stddef.h>
        void process(int* __restrict dst, const int* __restrict src, size_t n);
        """
        backend = get_backend("libclang")
        header = backend.parse(code, "test.h")

        from autopxd.ir_writer import write_pxd

        pxd = write_pxd(header)
        # __restrict should be stripped, const preserved
        assert "void process(int* dst, const int* src, size_t n)" in pxd
        assert "__restrict" not in pxd
        assert "const" in pxd  # const is supported by Cython

    @pytest.mark.skipif(not _libclang_available(), reason="__restrict__ is a GCC extension, not supported by pycparser")
    def test_restrict_double_underscore(self):
        """Test __restrict__ (double underscore variant)."""
        code = "void copy(char* __restrict__ dst, const char* __restrict__ src);"
        backend = get_backend("libclang")
        header = backend.parse(code, "test.h")

        from autopxd.ir_writer import write_pxd

        pxd = write_pxd(header)
        # __restrict__ should be stripped
        assert "void copy(char* dst, const char* src)" in pxd
        assert "__restrict" not in pxd


class TestNoreturnQualifier:
    """Test _Noreturn qualifier handling."""

    @pytest.mark.skipif(not _libclang_available(), reason="_Noreturn is a C11 keyword, not supported by pycparser")
    def test_noreturn_function(self):
        """Test _Noreturn in function declarations."""
        code = "_Noreturn void abort_program(void);"
        backend = get_backend("libclang")
        header = backend.parse(code, "test.h")

        from autopxd.ir_writer import write_pxd

        pxd = write_pxd(header)
        # _Noreturn should be stripped
        assert "void abort_program()" in pxd
        assert "_Noreturn" not in pxd


class TestMixedQualifiers:
    """Test combinations of supported and unsupported qualifiers."""

    @pytest.mark.skipif(not _libclang_available(), reason="__restrict is a GCC extension, not supported by pycparser")
    def test_const_volatile_atomic_mix(self):
        """Test const, volatile (supported) with _Atomic (unsupported)."""
        code = """
        void func(const _Atomic int* ptr, volatile int* __restrict vptr);
        """
        backend = get_backend("libclang")
        header = backend.parse(code, "test.h")

        from autopxd.ir_writer import write_pxd

        pxd = write_pxd(header)
        # const and volatile should be preserved, _Atomic and __restrict stripped
        assert "const int* ptr" in pxd
        assert "volatile int* vptr" in pxd
        assert "_Atomic" not in pxd
        assert "__restrict" not in pxd


class TestSemanticsPreservation:
    """Verify that stripping qualifiers doesn't break functionality."""

    def test_header_inclusion_preserves_qualifiers(self):
        """Verify that original header with qualifiers is still included.

        This is the key insight: autopxd2 strips qualifiers from the .pxd
        declarations (for Cython's parser), but the original header is
        included via `cdef extern from "header.h"`, so the C compiler
        still sees all the qualifiers.
        """
        code = "typedef _Atomic int atomic_int;"
        backend = get_backend()
        header = backend.parse(code, "test.h")

        from autopxd.ir_writer import write_pxd

        pxd = write_pxd(header)

        # The pxd should reference the original header
        assert 'cdef extern from "test.h"' in pxd
        # This means when Cython generates C code, it will #include "test.h"
        # which contains the full "_Atomic int" declaration

    def test_typedef_chain_with_qualifiers(self):
        """Test typedef chains involving stripped qualifiers."""
        code = """
        typedef _Atomic int atomic_int;
        typedef atomic_int counter_t;
        struct state {
            counter_t count;
        };
        """
        backend = get_backend()
        header = backend.parse(code, "test.h")

        from autopxd.ir_writer import write_pxd

        pxd = write_pxd(header)

        # First typedef: _Atomic stripped
        assert "ctypedef int atomic_int" in pxd
        # Second typedef: uses first typedef
        assert "ctypedef atomic_int counter_t" in pxd
        # Struct: uses second typedef
        assert "counter_t count" in pxd
        # No _Atomic in output
        assert "_Atomic" not in pxd
