"""C++ specific tests that only run with libclang backend."""

import pytest

from autopxd.backends import get_backend
from autopxd.ir import (
    Function,
    Struct,
)
from test.assertions import assert_pxd_equals

# These tests require libclang - exclude with: pytest -m "not libclang"
pytestmark = pytest.mark.libclang


@pytest.fixture
def libclang_backend():
    """Provide libclang backend for C++ tests."""
    return get_backend("libclang")


class TestCppClasses:
    """Test C++ class parsing."""

    def test_cpp_class_is_cppclass(self, libclang_backend):
        """C++ classes should have is_cppclass=True."""
        code = """
        class Widget {
        public:
            int width;
            int height;
        };
        """
        header = libclang_backend.parse(code, "test.hpp", extra_args=["-x", "c++"])
        assert len(header.declarations) == 1
        struct = header.declarations[0]
        assert isinstance(struct, Struct)
        assert struct.name == "Widget"
        assert struct.is_cppclass is True
        assert struct.is_union is False

    def test_cpp_class_with_methods(self, libclang_backend):
        """C++ class methods should be extracted."""
        code = """
        class Widget {
        public:
            int width;
            int height;
            void resize(int w, int h);
        };
        """
        header = libclang_backend.parse(code, "test.hpp", extra_args=["-x", "c++"])
        assert len(header.declarations) == 1
        struct = header.declarations[0]
        assert isinstance(struct, Struct)
        assert struct.is_cppclass is True
        assert len(struct.fields) == 2
        assert len(struct.methods) == 1
        method = struct.methods[0]
        assert method.name == "resize"
        assert len(method.parameters) == 2

    def test_cpp_class_generates_cppclass_pxd(self, libclang_backend, tmp_path):
        """Generated pxd should use 'cppclass' for C++ classes."""
        assert_pxd_equals(
            """
            class Widget {
            public:
                int width;
                int height;
                void resize(int w, int h);
            };
            """,
            """cdef extern from "test.hpp":

    cdef cppclass Widget:
        int width
        int height
        void resize(int w, int h)
""",
            tmp_path,
            backend="libclang",
            filename="test.hpp",
            cplus=True,
            extra_args=["-x", "c++"],
        )

    def test_cpp_struct_is_not_cppclass(self, libclang_backend):
        """C++ structs should NOT have is_cppclass=True (they're just structs)."""
        code = """
        struct Point {
            int x;
            int y;
        };
        """
        header = libclang_backend.parse(code, "test.hpp", extra_args=["-x", "c++"])
        assert len(header.declarations) == 1
        struct = header.declarations[0]
        assert isinstance(struct, Struct)
        assert struct.name == "Point"
        assert struct.is_cppclass is False
        assert struct.is_union is False

    def test_cpp_namespace_function(self, libclang_backend):
        """Top-level C++ functions should be parsed."""
        code = """
        int global_func(int x);
        """
        header = libclang_backend.parse(code, "test.hpp", extra_args=["-x", "c++"])
        assert len(header.declarations) == 1
        func = header.declarations[0]
        assert isinstance(func, Function)
        assert func.name == "global_func"
