import os
import sys

import pytest
from headerkit.backends import get_backend, is_backend_available


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add CLI options for autopxd test runner."""
    parser.addoption(
        "--require-all-libraries",
        action="store_true",
        default=False,
        help="Fail if any system test library in test_real_headers is not installed (default: skip)",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Ensure standard system and Homebrew pkg-config paths are set on macOS."""
    if sys.platform == "darwin":
        brew_pkgconfig_dirs = [
            "/opt/homebrew/lib/pkgconfig",
            "/opt/homebrew/share/pkgconfig",
            "/usr/local/lib/pkgconfig",
            "/usr/local/share/pkgconfig",
        ]
        current_path = os.environ.get("PKG_CONFIG_PATH", "")
        paths = [p for p in current_path.split(os.pathsep) if p]
        for d in brew_pkgconfig_dirs:
            if os.path.isdir(d) and d not in paths:
                paths.append(d)
        if paths:
            os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(paths)


@pytest.fixture(
    params=[
        pytest.param("libclang", marks=pytest.mark.libclang),
        pytest.param(
            "tree-sitter",
            marks=pytest.mark.skipif(
                not is_backend_available("tree-sitter"),
                reason="tree-sitter optional dependency not installed",
            ),
        ),
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
