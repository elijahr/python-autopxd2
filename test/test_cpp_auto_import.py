"""Tests for C++ STL auto-import."""

import pytest

from autopxd import translate

# Mark entire module as requiring libclang
pytestmark = pytest.mark.libclang

libclang = pytest.importorskip("clang.cindex")


class TestCppAutoImport:
    """Tests for C++ standard library auto-import."""

    @pytest.fixture
    def backend(self):
        return "libclang"

    def test_vector_auto_import(self, backend):
        """std::vector generates libcpp.vector cimport."""
        code = """\
namespace std {
    template<typename T> class vector {};
}

class Container {
public:
    std::vector<int> get_items();
};
"""
        result = translate(code, "test.hpp", backend=backend, extra_args=["-x", "c++"])

        assert "from libcpp.vector cimport vector" in result

    def test_string_auto_import(self, backend):
        """std::string generates libcpp.string cimport."""
        code = """\
namespace std {
    class string {};
}

std::string get_name();
"""
        result = translate(code, "test.hpp", backend=backend, extra_args=["-x", "c++"])

        assert "from libcpp.string cimport string" in result

    def test_smart_pointers_auto_import(self, backend):
        """Smart pointers generate libcpp.memory cimport."""
        code = """\
namespace std {
    template<typename T> class shared_ptr {};
    template<typename T> class unique_ptr {};
}

class Widget;
std::shared_ptr<Widget> create_widget();
std::unique_ptr<Widget> take_widget();
"""
        result = translate(code, "test.hpp", backend=backend, extra_args=["-x", "c++"])

        assert "from libcpp.memory cimport" in result
        assert "shared_ptr" in result
        assert "unique_ptr" in result

    def test_multiple_stl_types(self, backend):
        """Multiple STL types generate multiple cimports."""
        code = """\
namespace std {
    template<typename T> class vector {};
    template<typename K, typename V> class map {};
    class string {};
}

std::map<std::string, std::vector<int>> get_data();
"""
        result = translate(code, "test.hpp", backend=backend, extra_args=["-x", "c++"])

        assert "from libcpp.vector cimport vector" in result
        assert "from libcpp.map cimport map" in result
        assert "from libcpp.string cimport string" in result
