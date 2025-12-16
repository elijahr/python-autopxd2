"""Test handling of compile-time expressions in typedefs (decltype, sizeof)."""

import pytest

# These tests require libclang
pytestmark = pytest.mark.libclang

# Guard import for when clang2 is not installed
clang = pytest.importorskip("clang")
from autopxd.backends.libclang_backend import LibclangBackend  # noqa: E402
from autopxd.ir import Typedef  # noqa: E402
from autopxd.ir_writer import write_pxd  # noqa: E402


@pytest.fixture
def backend():
    """Create a libclang backend instance."""
    return LibclangBackend()


class TestDecltypeTypedefs:
    """Test resolution of decltype() expressions in typedefs."""

    def test_decltype_nullptr_resolves_to_void_ptr(self, backend):
        """decltype(nullptr) should resolve to void*."""
        code = "typedef decltype(nullptr) nullptr_t;"
        header = backend.parse(code, "test.cpp", extra_args=["-std=c++11"])

        # Should have one typedef
        assert len(header.declarations) == 1
        typedef = header.declarations[0]
        assert isinstance(typedef, Typedef)
        assert typedef.name == "nullptr_t"

        # Should resolve to void* (not the raw "decltype(nullptr)")
        pxd = write_pxd(header)
        assert "ctypedef void* nullptr_t" in pxd
        assert "decltype" not in pxd

    def test_decltype_int_resolves_to_int(self, backend):
        """decltype(0) should resolve to int."""
        code = "typedef decltype(0) int_type;"
        header = backend.parse(code, "test.cpp", extra_args=["-std=c++11"])

        typedef = header.declarations[0]
        assert typedef.name == "int_type"

        pxd = write_pxd(header)
        assert "ctypedef int int_type" in pxd
        assert "decltype" not in pxd

    def test_decltype_in_function_signature(self, backend):
        """Typedef with decltype should be usable in function signatures."""
        code = """
        typedef decltype(nullptr) nullptr_t;
        int test_func(nullptr_t ptr);
        """
        header = backend.parse(code, "test.cpp", extra_args=["-std=c++11"])

        pxd = write_pxd(header)
        # Should have typedef and function using it
        assert "ctypedef void* nullptr_t" in pxd
        assert "int test_func(nullptr_t ptr)" in pxd


class TestSizeofTypedefs:
    """Test resolution of sizeof() expressions in typedefs."""

    def test_sizeof_int_resolves(self, backend):
        """sizeof(int) should resolve to size_t (unsigned long on most platforms)."""
        code = "typedef decltype(sizeof(int)) size_type;"
        header = backend.parse(code, "test.cpp", extra_args=["-std=c++11"])

        typedef = header.declarations[0]
        assert typedef.name == "size_type"

        pxd = write_pxd(header)
        # Should resolve to unsigned long (size_t's canonical type)
        assert "ctypedef unsigned long size_type" in pxd
        assert "sizeof" not in pxd
        assert "decltype" not in pxd

    def test_sizeof_pointer_resolves(self, backend):
        """sizeof(void*) should resolve to size_t."""
        code = "typedef decltype(sizeof(void*)) ptr_size_type;"
        header = backend.parse(code, "test.cpp", extra_args=["-std=c++11"])

        pxd = write_pxd(header)
        assert "ctypedef unsigned long ptr_size_type" in pxd
        assert "sizeof" not in pxd

    def test_sizeof_in_struct(self, backend):
        """Typedef with sizeof should work in struct fields."""
        code = """
        typedef decltype(sizeof(int)) size_type;
        struct MyStruct {
            size_type size;
        };
        """
        header = backend.parse(code, "test.cpp", extra_args=["-std=c++11"])

        pxd = write_pxd(header)
        assert "ctypedef unsigned long size_type" in pxd
        assert "cdef struct MyStruct:" in pxd
        assert "size_type size" in pxd


class TestMixedExpressions:
    """Test files with multiple compile-time expression typedefs."""

    def test_multiple_decltype_typedefs(self, backend):
        """Multiple decltype typedefs should all resolve correctly."""
        code = """
        typedef decltype(nullptr) nullptr_t;
        typedef decltype(0) int_type;
        typedef decltype(0L) long_type;
        """
        header = backend.parse(code, "test.cpp", extra_args=["-std=c++11"])

        assert len(header.declarations) == 3
        pxd = write_pxd(header)

        assert "ctypedef void* nullptr_t" in pxd
        assert "ctypedef int int_type" in pxd
        assert "ctypedef long long_type" in pxd
        assert "decltype" not in pxd

    def test_decltype_and_sizeof_together(self, backend):
        """Mix of decltype and sizeof should both resolve."""
        code = """
        typedef decltype(nullptr) nullptr_t;
        typedef decltype(sizeof(int)) size_type;

        struct Test {
            nullptr_t ptr;
            size_type size;
        };
        """
        header = backend.parse(code, "test.cpp", extra_args=["-std=c++11"])

        pxd = write_pxd(header)
        assert "ctypedef void* nullptr_t" in pxd
        assert "ctypedef unsigned long size_type" in pxd
        assert "nullptr_t ptr" in pxd
        assert "size_type size" in pxd
        assert "decltype" not in pxd
        assert "sizeof" not in pxd
