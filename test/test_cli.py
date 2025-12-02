"""Tests for CLI functionality."""

from autopxd.backends import is_backend_available


class TestBackendAvailability:
    """Tests for backend availability checking."""

    def test_pycparser_always_available(self) -> None:
        """pycparser should always be available."""
        assert is_backend_available("pycparser") is True

    def test_unknown_backend_not_available(self) -> None:
        """Unknown backends should not be available."""
        assert is_backend_available("nonexistent") is False
