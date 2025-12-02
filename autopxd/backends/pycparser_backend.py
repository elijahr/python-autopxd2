# pylint: disable=cyclic-import
# Cyclic import is intentional - backends register themselves when loaded
"""pycparser-based parser backend.

This backend uses pycparser (pure Python C99 parser) to parse C header files.
It's the default backend since it has no external dependencies.

Limitations:
- C99 only (no C++ support)
- Cannot extract #define macro values (they're processed by cpp before parsing)
- Requires a C preprocessor (cpp or cl.exe on Windows)
"""

from typing import (
    List,
    Optional,
)

from autopxd.backends import (
    register_backend,
)
from autopxd.ir import (
    Header,
)


class PycparserBackend:
    """Parser backend using pycparser."""

    @property
    def name(self) -> str:
        return "pycparser"

    @property
    def supports_macros(self) -> bool:
        return False

    @property
    def supports_cpp(self) -> bool:
        return False

    def parse(
        self,
        code: str,
        filename: str,
        include_dirs: Optional[List[str]] = None,
        extra_args: Optional[List[str]] = None,
    ) -> Header:
        """Parse C code using pycparser.

        This will:
        1. Run the C preprocessor on the code
        2. Parse the preprocessed output with pycparser
        3. Convert pycparser's AST to our IR

        Args:
            code: C source code to parse
            filename: Source filename for error messages
            include_dirs: Additional include directories for preprocessor
            extra_args: Additional preprocessor arguments

        Returns:
            Header containing parsed declarations
        """
        # pylint: disable-next=fixme
        # TODO: Implement actual parsing  # noqa: TD002, TD003, FIX002
        # The implementation will be moved from the existing code
        raise NotImplementedError(
            "pycparser backend not yet implemented. "
            "This is a placeholder - the actual implementation will be migrated from existing code."
        )


# Register this backend as the default
register_backend("pycparser", PycparserBackend, is_default=True)
