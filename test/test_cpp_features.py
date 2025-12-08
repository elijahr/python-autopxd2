"""C++ specific tests that only run with libclang backend."""

import pytest

from autopxd.backends import get_backend
from autopxd.ir import (
    Function,
    Struct,
)

# These tests require libclang - exclude with: pytest -m "not libclang"
pytestmark = pytest.mark.libclang


@pytest.fixture
def libclang_backend():
    """Provide libclang backend for C++ tests."""
    return get_backend("libclang")


class TestCppClasses:
    """Test C++ class parsing."""

    def test_cpp_class(self, libclang_backend):
        code = """
        class Widget {
        public:
            int width;
            int height;
        };
        """
        header = libclang_backend.parse(code, "test.hpp", extra_args=["-x", "c++"])
        # Classes are treated as structs
        assert len(header.declarations) == 1
        struct = header.declarations[0]
        assert isinstance(struct, Struct)
        assert struct.name == "Widget"

    def test_cpp_namespace_function(self, libclang_backend):
        # For now, we only handle top-level declarations
        code = """
        int global_func(int x);
        """
        header = libclang_backend.parse(code, "test.hpp", extra_args=["-x", "c++"])
        assert len(header.declarations) == 1
        func = header.declarations[0]
        assert isinstance(func, Function)
        assert func.name == "global_func"
