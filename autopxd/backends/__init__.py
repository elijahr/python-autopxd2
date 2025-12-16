"""Parser backends for autopxd.

This package contains parser backend implementations that convert C/C++
source code into the autopxd IR (Intermediate Representation).

Available Backends
------------------
pycparser
    Pure Python C99 parser. Default backend with no external dependencies.
    Requires preprocessed input (CPP/clang -E output).

libclang
    LLVM clang-based parser with full C++ support. Requires system
    libclang library and matching ``clang2`` Python package.

Example
-------
::

    from autopxd.backends import get_backend, list_backends

    # Get the default backend
    backend = get_backend()

    # Get a specific backend
    backend = get_backend("libclang")

    # List available backends
    for name in list_backends():
        print(name)
"""

from autopxd.ir import (
    ParserBackend,
)

# Registry of available backends
# Backends are registered lazily to avoid import errors if dependencies are missing
_BACKEND_REGISTRY: dict[str, type[ParserBackend]] = {}
_DEFAULT_BACKEND: str | None = None
_BACKENDS_LOADED: bool = False  # Track if we've tried to load all backends
_LIBCLANG_IMPORT_ERROR: str | None = None  # Store libclang import error for better messages


def register_backend(name: str, backend_class: type[ParserBackend], is_default: bool = False) -> None:
    """Register a parser backend.

    Called by backend modules during import to add themselves to the registry.
    The first registered backend becomes the default unless ``is_default`` is
    explicitly set on a later registration.

    :param name: Unique name for the backend (e.g., ``"pycparser"``, ``"libclang"``).
    :param backend_class: Class implementing the :class:`~autopxd.ir.ParserBackend` protocol.
    :param is_default: If True, this becomes the default backend for :func:`get_backend`.
    """
    global _DEFAULT_BACKEND  # pylint: disable=global-statement
    _BACKEND_REGISTRY[name] = backend_class
    if is_default or _DEFAULT_BACKEND is None:
        _DEFAULT_BACKEND = name


def list_backends() -> list[str]:
    """List names of all registered backends.

    :returns: List of backend names that can be passed to :func:`get_backend`.

    Example
    -------
    ::

        from autopxd.backends import list_backends

        for name in list_backends():
            print(f"Available: {name}")
    """
    _ensure_backends_loaded()
    return list(_BACKEND_REGISTRY.keys())


def is_backend_available(name: str) -> bool:
    """Check if a backend is available for use.

    :param name: Backend name to check.
    :returns: True if the backend is registered and can be instantiated.
    """
    _ensure_backends_loaded()
    return name in _BACKEND_REGISTRY


def get_backend_info() -> list[dict[str, str | bool]]:
    """Get information about all known backends.

    :returns: List of dicts with name, available, default, and description.
    """
    _ensure_backends_loaded()

    descriptions = {
        "libclang": "Full C/C++ support via LLVM",
        "pycparser": "Legacy C99 parser",
    }

    result: list[dict[str, str | bool]] = []
    for name in ["libclang", "pycparser"]:  # Fixed order for display
        result.append(
            {
                "name": name,
                "available": name in _BACKEND_REGISTRY,
                "default": name == _DEFAULT_BACKEND,
                "description": descriptions.get(name, ""),
            }
        )
    return result


def get_backend(name: str | None = None) -> ParserBackend:
    """Get a parser backend instance.

    Returns a new instance of the requested backend. If no name is provided,
    returns the default backend (pycparser).

    :param name: Backend name (e.g., ``"pycparser"``, ``"libclang"``),
        or None for the default backend.
    :returns: New instance of the requested backend.
    :raises ValueError: If the requested backend is not available.

    Example
    -------
    ::

        from autopxd.backends import get_backend

        # Get default backend
        backend = get_backend()

        # Get libclang backend
        clang = get_backend("libclang")

        # Parse a header
        header = backend.parse(code, "myheader.h")
    """
    _ensure_backends_loaded()

    if name is None:
        if _DEFAULT_BACKEND is None:
            raise ValueError("No backends available")
        name = _DEFAULT_BACKEND

    if name not in _BACKEND_REGISTRY:
        # Provide helpful error for libclang if we know why it failed
        if name == "libclang" and _LIBCLANG_IMPORT_ERROR:
            raise ValueError(_LIBCLANG_IMPORT_ERROR)

        available = ", ".join(_BACKEND_REGISTRY.keys()) or "(none)"
        raise ValueError(f"Unknown backend: {name!r}. Available: {available}")

    return _BACKEND_REGISTRY[name]()


def get_default_backend() -> str:
    """Get the name of the default backend.

    Returns the name of the currently configured default backend.
    If libclang is available, it is preferred; otherwise pycparser is used.

    :returns: Backend name (e.g., "pycparser" or "libclang").
    :raises ValueError: If no backends are available.

    Example
    -------
    ::

        from autopxd.backends import get_default_backend

        default = get_default_backend()
        print(f"Default backend: {default}")
    """
    _ensure_backends_loaded()

    if _DEFAULT_BACKEND is None:
        raise ValueError("No backends available")
    return _DEFAULT_BACKEND


def _detect_system_clang_version() -> str | None:
    """Detect the system libclang/LLVM version.

    :returns: Version string like "18" or None if not detected.
    """
    import shutil
    import subprocess

    # Try llvm-config first (most reliable)
    llvm_config = shutil.which("llvm-config")
    if llvm_config:
        try:
            result = subprocess.run(
                [llvm_config, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                # Extract major version (e.g., "18.1.0" -> "18")
                major = version.split(".")[0]
                if major.isdigit():
                    return major
        except (subprocess.SubprocessError, OSError):
            pass

    # Try clang --version as fallback
    clang = shutil.which("clang")
    if clang:
        try:
            result = subprocess.run(
                [clang, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # Parse "clang version X.Y.Z" or "Apple clang version X.Y.Z"
                import re

                match = re.search(r"clang version (\d+)", result.stdout)
                if match:
                    return match.group(1)
        except (subprocess.SubprocessError, OSError):
            pass

    return None


def _ensure_backends_loaded() -> None:
    """Lazily load backend modules to populate the registry."""
    global _BACKENDS_LOADED, _LIBCLANG_IMPORT_ERROR  # pylint: disable=global-statement

    if _BACKENDS_LOADED:
        return  # Already tried to load all backends

    _BACKENDS_LOADED = True

    # pylint: disable=import-outside-toplevel
    # Lazy imports are intentional to avoid import errors if dependencies are missing

    # Try to import pycparser backend (should always work)
    try:
        from autopxd.backends import (  # noqa: F401
            pycparser_backend,
        )
    except ImportError:
        pass

    # Try to import libclang backend (may fail if clang2 not installed)
    try:
        from autopxd.backends import (  # noqa: F401
            libclang_backend,
        )
    except ImportError as e:
        # Store error details for helpful message later
        if "clang" in str(e).lower() or "No module named 'clang'" in str(e):
            version = _detect_system_clang_version()
            if version:
                _LIBCLANG_IMPORT_ERROR = (
                    f"libclang backend requires the clang2 package.\n"
                    f"Detected LLVM version {version} on your system.\n"
                    f"Install with: pip install 'clang2=={version}.*'"
                )
            else:
                _LIBCLANG_IMPORT_ERROR = (
                    "libclang backend requires the clang2 package.\n"
                    "Install with: pip install clang2\n"
                    "Note: clang2 version must match your system's LLVM version.\n"
                    "Example: pip install 'clang2==18.*' for LLVM 18"
                )
