"""C++ specific tests that only run on backends with C++ support."""

import pytest

from autopxd.ir import (
    Function,
    Struct,
)

pytestmark = pytest.mark.requires_cpp


class TestCppClasses:
    """Test C++ class parsing."""

    def test_cpp_class(self, backend):
        code = """
        class Widget {
        public:
            int width;
            int height;
        };
        """
        header = backend.parse(code, "test.hpp", extra_args=["-x", "c++"])
        # Classes are treated as structs
        assert len(header.declarations) == 1
        struct = header.declarations[0]
        assert isinstance(struct, Struct)
        assert struct.name == "Widget"

    def test_cpp_namespace_function(self, backend):
        # For now, we only handle top-level declarations
        code = """
        int global_func(int x);
        """
        header = backend.parse(code, "test.hpp", extra_args=["-x", "c++"])
        assert len(header.declarations) == 1
        func = header.declarations[0]
        assert isinstance(func, Function)
        assert func.name == "global_func"
