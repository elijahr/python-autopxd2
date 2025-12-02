# pylint: disable=cyclic-import
# Cyclic import is intentional - backends register themselves when loaded
"""libclang-based parser backend.

This backend uses libclang (LLVM's C/C++ parser) to parse header files.
It provides full C/C++ support and can extract #define macro values.

Requirements:
- libclang must be installed (e.g., via `pip install libclang` or system package)
- On some systems, you may need to set LIBCLANG_PATH environment variable

Advantages over pycparser:
- Full C++ support
- Can extract #define macro values
- Handles complex preprocessor constructs
- Uses the same parser as actual compilers
"""

from typing import (
    List,
    Optional,
)

# Try to import clang - this may fail if not installed
try:
    import clang.cindex  # noqa: F401

    CLANG_AVAILABLE = True
except ImportError:
    CLANG_AVAILABLE = False

from autopxd.ir import (
    Header,
)

if CLANG_AVAILABLE:
    from autopxd.backends import (
        register_backend,
    )

    class LibclangBackend:
        """Parser backend using libclang."""

        @property
        def name(self) -> str:
            return "libclang"

        @property
        def supports_macros(self) -> bool:
            return True

        @property
        def supports_cpp(self) -> bool:
            return True

        def parse(
            self,
            code: str,
            filename: str,
            include_dirs: Optional[List[str]] = None,
            extra_args: Optional[List[str]] = None,
        ) -> Header:
            """Parse C/C++ code using libclang.

            Args:
                code: C/C++ source code to parse
                filename: Source filename for error messages
                include_dirs: Additional include directories
                extra_args: Additional compiler arguments

            Returns:
                Header containing parsed declarations
            """
            # pylint: disable-next=fixme
            # TODO: Implement actual parsing using clang.cindex  # noqa: TD002, TD003
            raise NotImplementedError(
                "libclang backend not yet implemented. Install libclang with: pip install libclang"
            )

    # Register this backend (not as default since it requires external dependency)
    register_backend("libclang", LibclangBackend)
