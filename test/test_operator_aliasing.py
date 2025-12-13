"""Test operator aliasing for unsupported C++ operators."""

import pytest

from autopxd.backends import get_backend
from autopxd.ir_writer import write_pxd


@pytest.mark.libclang
class TestOperatorAliasing:
    """Test that unsupported operators are aliased with Python-friendly names."""

    @pytest.fixture
    def libclang_backend(self):
        """Provide the libclang backend."""
        return get_backend("libclang")

    def test_operator_arrow_aliased(self, libclang_backend):
        """Test that operator-> is aliased to 'deref'."""
        code = """
        template<typename T>
        class SmartPtr {
        public:
            T* operator->() const;
        };
        """

        header = libclang_backend.parse(code, "test.h", extra_args=["-x", "c++", "-std=c++11"])
        pxd = write_pxd(header)

        # Should contain the aliased operator with C name in quotes
        assert 'deref "operator->"()' in pxd
        # Verify it's a complete method declaration
        assert 'T* deref "operator->"()' in pxd
        # Original operator name should only appear in the quoted C name
        assert pxd.count("operator->") == 1  # Only in the quoted C name

    def test_operator_call_aliased(self, libclang_backend):
        """Test that operator() is aliased to 'call'."""
        code = """
        template<typename T>
        class Functor {
        public:
            T operator()(int x);
        };
        """

        header = libclang_backend.parse(code, "test.h", extra_args=["-x", "c++", "-std=c++11"])
        pxd = write_pxd(header)

        # Should contain the aliased operator
        assert 'call "operator()"(' in pxd
        # Verify it's a method declaration with parameter
        assert 'T call "operator()"(int x)' in pxd

    def test_operator_comma_skipped(self, libclang_backend):
        """Test that operator, is skipped entirely."""
        code = """
        class Foo {
        public:
            void operator,(const Foo& other);
        };
        """

        header = libclang_backend.parse(code, "test.h", extra_args=["-x", "c++", "-std=c++11"])
        pxd = write_pxd(header)

        # Should NOT contain operator, in any form
        assert "operator," not in pxd

    def test_supported_operators_unchanged(self, libclang_backend):
        """Test that supported operators are emitted normally."""
        code = """
        class Vector {
        public:
            int operator[](int index);
            Vector operator+(const Vector& other);
            bool operator==(const Vector& other);
        };
        """

        header = libclang_backend.parse(code, "test.h", extra_args=["-x", "c++", "-std=c++11"])
        pxd = write_pxd(header)

        # These operators should appear normally (not aliased)
        assert "operator[]" in pxd
        assert "operator+" in pxd
        assert "operator==" in pxd

    def test_cython_compilation(self, libclang_backend, tmp_path):
        """Test that the generated PXD with aliased operators compiles with Cython."""
        from test.cython_utils import validate_cython_compiles

        code = """
        template<typename T>
        class SmartPtr {
        public:
            T* ptr_;
            T* operator->() const { return ptr_; }
            T& operator()(int index) { return ptr_[index]; }
        };
        """

        header = libclang_backend.parse(code, "test.h", extra_args=["-x", "c++", "-std=c++11"])
        pxd = write_pxd(header)

        # Should have both aliased operators
        assert 'deref "operator->"()' in pxd
        assert 'call "operator()"(' in pxd

        # Validate it compiles with Cython (syntax check only, no C compilation)
        validate_cython_compiles(pxd, tmp_path, cplus=True, cython_only=True)
