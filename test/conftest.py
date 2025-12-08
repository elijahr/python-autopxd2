"""Shared pytest fixtures for autopxd tests."""

import pytest

from autopxd.backends import get_backend, is_backend_available


@pytest.fixture(
    params=[
        pytest.param("pycparser", marks=pytest.mark.pycparser),
        pytest.param("libclang", marks=pytest.mark.libclang),
    ]
)
def backend(request: pytest.FixtureRequest):
    """Parameterized fixture providing each available backend.

    Each parameter is marked with its backend name, so you can filter:
        pytest -m "not libclang"      # exclude libclang parameterizations
        pytest -m "not pycparser"     # exclude pycparser parameterizations

    Fails if a backend is not available.
    """
    name: str = request.param

    if not is_backend_available(name):
        pytest.fail(f"{name} backend not available - use pytest -m 'not {name}' to exclude")

    return get_backend(name)
