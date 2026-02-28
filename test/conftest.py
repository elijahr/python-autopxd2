"""Shared pytest fixtures for autopxd tests."""

import pytest

from autopxd.backends import get_backend, is_backend_available


@pytest.fixture(
    params=[
        pytest.param("libclang", marks=pytest.mark.libclang),
    ]
)
def backend(request: pytest.FixtureRequest):
    """Parameterized fixture providing the libclang backend.

    Each parameter is marked with its backend name, so you can filter:
        pytest -m "not libclang"      # exclude libclang parameterizations

    Fails if the backend is not available.
    """
    name: str = request.param

    if not is_backend_available(name):
        pytest.fail(f"{name} backend not available - use pytest -m 'not {name}' to exclude")

    return get_backend(name)
