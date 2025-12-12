"""Backend property tests."""

import pytest


class TestBackendProperties:
    """Test backend properties and capabilities."""

    def test_backend_has_name(self, backend):
        assert backend.name in ("pycparser", "libclang")

    def test_backend_has_supports_macros(self, backend):
        assert isinstance(backend.supports_macros, bool)

    def test_backend_has_supports_cpp(self, backend):
        assert isinstance(backend.supports_cpp, bool)

    def test_pycparser_properties(self, backend):
        if backend.name != "pycparser":
            pytest.skip("pycparser-specific test")
        assert backend.supports_macros is False
        assert backend.supports_cpp is False

    def test_libclang_properties(self, backend):
        if backend.name != "libclang":
            pytest.skip("libclang-specific test")
        assert backend.supports_macros is True  # Supports simple numeric macros
        assert backend.supports_cpp is True
