"""Test edge cases in template syntax conversion."""

import pytest

from autopxd.backends import get_backend
from autopxd.ir_writer import write_pxd

# These tests require libclang
pytestmark = pytest.mark.libclang


@pytest.fixture
def libclang_backend():
    """Provide the libclang backend."""
    return get_backend("libclang")


class TestTemplateEdgeCases:
    """Test edge cases in template formatting."""

    def test_nested_templates(self, libclang_backend):
        """Test nested templates like A<B<C>>."""
        code = """
        template<typename T>
        class Container {};

        template<typename T>
        class Wrapper {
        public:
            Container<T> inner;
        };

        // Nested instantiation
        Wrapper<Container<int>> nested;
        """
        header = libclang_backend.parse(code, "test.hpp", extra_args=["-x", "c++", "-std=c++17"])
        pxd = write_pxd(header)

        # Should convert A<B<C>> to A[B[C]]
        # NOT A<B<C]] or other broken combinations
        print("Generated PXD:")
        print(pxd)
        assert "[Container[int]]" in pxd or "Wrapper[Container[int]]" in pxd

    def test_non_type_template_params(self, libclang_backend):
        """Test non-type template parameters like std::array<int, 4>."""
        code = """
        template<typename T, int N>
        class FixedArray {
        public:
            T data[N];
            int size() { return N; }
        };
        """
        header = libclang_backend.parse(code, "test.hpp", extra_args=["-x", "c++", "-std=c++17"])
        pxd = write_pxd(header)

        print("Generated PXD:")
        print(pxd)
        # Should handle non-type parameter gracefully
        # The cppclass declaration should use [T] only, not [T, int]
        assert "cppclass FixedArray[T]" in pxd
        assert "NOTE:" in pxd  # Should have a note about non-type params

    def test_double_closing_angle_brackets(self, libclang_backend):
        """Test >> in nested templates (C++11 allows this)."""
        code = """
        template<typename T>
        class Outer {};

        template<typename T>
        class Inner {
        public:
            Outer<T> value;
        };

        // C++11 allows >> without space
        Inner<Outer<int>> nested;
        """
        header = libclang_backend.parse(code, "test.hpp", extra_args=["-x", "c++", "-std=c++17"])
        pxd = write_pxd(header)

        print("Generated PXD:")
        print(pxd)
        # Should correctly parse >> as two separate >
        assert "Inner[Outer[int]]" in pxd or "[Outer[int]]" in pxd

    def test_template_with_multiple_params(self, libclang_backend):
        """Test templates with multiple type parameters."""
        code = """
        template<typename K, typename V>
        class Map {
        public:
            V lookup(K key);
        };
        """
        header = libclang_backend.parse(code, "test.hpp", extra_args=["-x", "c++", "-std=c++17"])
        pxd = write_pxd(header)

        print("Generated PXD:")
        print(pxd)
        # Should convert Map<K, V> to Map[K, V]
        assert "cppclass Map[K, V]" in pxd

    def test_variadic_templates(self, libclang_backend):
        """Test variadic templates (Args...)."""
        code = """
        template<typename... Args>
        class Tuple {
        public:
            void accept(Args... args);
        };
        """
        header = libclang_backend.parse(code, "test.hpp", extra_args=["-x", "c++", "-std=c++17"])
        pxd = write_pxd(header)

        print("Generated PXD:")
        print(pxd)
        # Should handle variadic templates somehow
        # Cython doesn't support these, so might skip or note
        assert "Tuple" in pxd

    def test_template_specialization_name(self, libclang_backend):
        """Test template specialization gets distinct name."""
        code = """
        template<typename T>
        class Vector {
        public:
            T* data;
        };

        // Specialization for bool
        template<>
        class Vector<bool> {
        public:
            unsigned char* bits;
        };
        """
        header = libclang_backend.parse(code, "test.hpp", extra_args=["-x", "c++", "-std=c++17"])
        pxd = write_pxd(header)

        print("Generated PXD:")
        print(pxd)
        # Specialization should have a distinct name to avoid collision
        # Current code uses _mangle_specialization_name
        assert "Vector[T]" in pxd
        # Specialization might be Vector_bool or similar
        assert 'Vector_bool "Vector<bool>"' in pxd or "Vector<bool>" in pxd

    def test_typedef_with_templates(self, libclang_backend):
        """Test typedefs involving templates."""
        code = """
        template<typename T>
        class Ptr {};

        typedef Ptr<int> IntPtr;
        """
        header = libclang_backend.parse(code, "test.hpp", extra_args=["-x", "c++", "-std=c++17"])
        pxd = write_pxd(header)

        print("Generated PXD:")
        print(pxd)
        # Should convert Ptr<int> to Ptr[int] in typedef
        assert "ctypedef" in pxd
        assert "Ptr[int]" in pxd or "IntPtr" in pxd


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
