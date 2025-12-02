"""Parser backends for autopxd.

This package contains parser backend implementations that convert C/C++
source code into the autopxd IR (Intermediate Representation).

Available backends:
- pycparser: Pure Python C99 parser (default, no external dependencies)
- libclang: Clang-based parser (supports C++ and macros, requires clang)

Usage:
    from autopxd.backends import get_backend, list_backends

    # Get the default backend
    backend = get_backend()

    # Get a specific backend
    backend = get_backend("libclang")

    # List available backends
    for name in list_backends():
        print(name)
"""

from typing import (
    Dict,
    List,
    Optional,
    Type,
)

from autopxd.ir import (
    ParserBackend,
)

# Registry of available backends
# Backends are registered lazily to avoid import errors if dependencies are missing
_BACKEND_REGISTRY: Dict[str, Type[ParserBackend]] = {}
_DEFAULT_BACKEND: Optional[str] = None


def register_backend(name: str, backend_class: Type[ParserBackend], is_default: bool = False) -> None:
    """Register a parser backend.

    Args:
        name: Unique name for the backend (e.g., "pycparser", "libclang")
        backend_class: Class implementing ParserBackend protocol
        is_default: If True, this becomes the default backend
    """
    global _DEFAULT_BACKEND  # pylint: disable=global-statement
    _BACKEND_REGISTRY[name] = backend_class
    if is_default or _DEFAULT_BACKEND is None:
        _DEFAULT_BACKEND = name


def list_backends() -> List[str]:
    """List names of all registered backends."""
    _ensure_backends_loaded()
    return list(_BACKEND_REGISTRY.keys())


def get_backend(name: Optional[str] = None) -> ParserBackend:
    """Get a parser backend instance.

    Args:
        name: Backend name, or None for the default backend

    Returns:
        Instance of the requested backend

    Raises:
        ValueError: If the requested backend is not available
    """
    _ensure_backends_loaded()

    if name is None:
        if _DEFAULT_BACKEND is None:
            raise ValueError("No backends available")
        name = _DEFAULT_BACKEND

    if name not in _BACKEND_REGISTRY:
        available = ", ".join(_BACKEND_REGISTRY.keys()) or "(none)"
        raise ValueError(f"Unknown backend: {name!r}. Available: {available}")

    return _BACKEND_REGISTRY[name]()


def _ensure_backends_loaded() -> None:
    """Lazily load backend modules to populate the registry."""
    if _BACKEND_REGISTRY:
        return  # Already loaded

    # pylint: disable=import-outside-toplevel
    # Lazy imports are intentional to avoid import errors if dependencies are missing

    # Try to import pycparser backend (should always work)
    try:
        from autopxd.backends import (  # noqa: F401
            pycparser_backend,
        )
    except ImportError:
        pass

    # Try to import libclang backend (may fail if clang not installed)
    try:
        from autopxd.backends import (  # noqa: F401
            libclang_backend,
        )
    except ImportError:
        pass
