# pylint: disable=cyclic-import
# Cyclic import is intentional - backends register themselves when loaded
"""libclang-based parser backend - re-exported from headerkit.

This backend uses headerkit's vendored libclang parser to parse header files.
It provides full C/C++ support with vendored LLVM 18-21 bindings.
"""

from headerkit.backends.libclang import (
    LibclangBackend,
    _is_umbrella_header,
    get_system_include_dirs,
)

from autopxd.backends import register_backend

__all__ = ["LibclangBackend", "get_system_include_dirs", "_is_umbrella_header"]

register_backend("libclang", LibclangBackend, is_default=True)
