"""Shared pytest fixtures for autopxd tests."""

import pytest

from autopxd.backends import get_backend, is_backend_available


def _was_backend_explicitly_requested(request: pytest.FixtureRequest, backend_name: str) -> bool:
    """Check if user ran pytest -m libclang or similar."""
    markers = request.config.option.markexpr
    return backend_name in (markers or "")


@pytest.fixture(params=["pycparser", "libclang"])
def backend(request: pytest.FixtureRequest):
    """Parameterized fixture providing each available backend.

    Behavior:
    - Auto-skips backends that aren't available (graceful degradation)
    - Fails loudly if a backend is explicitly requested but unavailable
    - Skips tests marked requires_cpp if backend doesn't support C++
    - Skips tests marked requires_macros if backend doesn't support macros
    """
    name: str = request.param
    available = is_backend_available(name)
    explicitly_requested = _was_backend_explicitly_requested(request, name)

    if not available:
        if explicitly_requested:
            pytest.fail(f"{name} backend explicitly requested but not available")
        else:
            pytest.skip(f"{name} backend not available")

    instance = get_backend(name)

    # Skip if test requires C++ but backend doesn't support it
    if request.node.get_closest_marker("requires_cpp"):
        if not instance.supports_cpp:
            pytest.skip(f"{name} does not support C++")

    # Skip if test requires macros but backend doesn't support it
    if request.node.get_closest_marker("requires_macros"):
        if not instance.supports_macros:
            pytest.skip(f"{name} does not support macros")

    return instance
