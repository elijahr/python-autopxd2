"""Tests for CLI functionality."""

from autopxd.backends import get_backend_info, is_backend_available


class TestBackendAvailability:
    """Tests for backend availability checking."""

    def test_pycparser_always_available(self) -> None:
        """pycparser should always be available."""
        assert is_backend_available("pycparser") is True

    def test_unknown_backend_not_available(self) -> None:
        """Unknown backends should not be available."""
        assert is_backend_available("nonexistent") is False


class TestBackendInfo:
    """Tests for backend info retrieval."""

    def test_get_backend_info_returns_list(self) -> None:
        """get_backend_info should return a list of backend info dicts."""
        info = get_backend_info()
        assert isinstance(info, list)
        assert len(info) >= 1  # At least pycparser

    def test_backend_info_has_required_fields(self) -> None:
        """Each backend info should have name, available, default, description."""
        info = get_backend_info()
        for backend in info:
            assert "name" in backend
            assert "available" in backend
            assert "default" in backend
            assert "description" in backend

    def test_exactly_one_default_backend(self) -> None:
        """Exactly one backend should be marked as default."""
        info = get_backend_info()
        defaults = [b for b in info if b["default"]]
        assert len(defaults) == 1
