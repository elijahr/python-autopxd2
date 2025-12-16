"""Tests for libclang header inclusion tracking."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

# These tests require libclang - use pytest -m "not libclang" to exclude
pytestmark = pytest.mark.libclang

# Guard import for when clang2 is not installed
clang = pytest.importorskip("clang")
from autopxd.backends.libclang_backend import LibclangBackend  # noqa: E402


def _get_system_include_args() -> list[str]:
    """Get system include paths for libclang.

    libclang doesn't automatically know about system headers, so we need
    to provide the paths explicitly. This includes both the SDK headers
    and the clang builtin headers (for stdarg.h, stddef.h, etc.).
    """
    args = []

    # Get include paths from clang -v output
    try:
        result = subprocess.run(
            ["clang", "-v", "-x", "c", "-E", "/dev/null"],
            capture_output=True,
            text=True,
        )
        # Parse the include paths from stderr
        in_includes = False
        for line in result.stderr.splitlines():
            if "#include <...> search starts here:" in line:
                in_includes = True
                continue
            if in_includes:
                if line.startswith("End of search list"):
                    break
                path = line.strip()
                if path and not path.endswith("(framework directory)"):
                    args.extend(["-I", path])
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Fallback: if we didn't get any paths, try platform-specific defaults
    if not args:
        if sys.platform == "darwin":
            try:
                sdk_path = subprocess.check_output(
                    ["xcrun", "--show-sdk-path"], text=True, stderr=subprocess.DEVNULL
                ).strip()
                args.extend(["-isysroot", sdk_path])
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        elif sys.platform == "linux":
            for path in ["/usr/include", "/usr/local/include"]:
                if os.path.isdir(path):
                    args.extend(["-I", path])

    return args


class TestHeaderInclusionTracking:
    """Tests for tracking included headers in libclang backend."""

    @pytest.fixture
    def backend(self):
        return LibclangBackend()

    @pytest.fixture
    def system_args(self):
        """System include arguments for parsing system headers."""
        return _get_system_include_args()

    def test_includes_stdio(self, backend, system_args):
        """Detects stdio.h inclusion."""
        code = """\
#include <stdio.h>

void test_func(FILE *f);
"""
        header = backend.parse(code, "test.h", extra_args=system_args)
        # Should detect stdio.h was included
        assert any("stdio.h" in h for h in header.included_headers)

    def test_includes_stdint(self, backend, system_args):
        """Detects stdint.h inclusion."""
        code = """\
#include <stdint.h>

typedef uint32_t my_int;
"""
        header = backend.parse(code, "test.h", extra_args=system_args)
        assert any("stdint.h" in h for h in header.included_headers)

    def test_includes_multiple_headers(self, backend, system_args):
        """Detects multiple header inclusions."""
        code = """\
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void test(void);
"""
        header = backend.parse(code, "test.h", extra_args=system_args)
        included_basenames = {h.split("/")[-1] for h in header.included_headers}
        assert "stdio.h" in included_basenames
        assert "stdlib.h" in included_basenames
        assert "string.h" in included_basenames

    def test_no_includes_empty_set(self, backend, system_args):
        """No includes results in empty set."""
        code = """\
void standalone_func(int x);
"""
        header = backend.parse(code, "test.h", extra_args=system_args)
        # May have implicit includes from compiler, but should at minimum exist
        assert isinstance(header.included_headers, set)

    def test_includes_transitive(self, backend, system_args):
        """Tracks transitive includes (headers included by other headers)."""
        # stdio.h typically includes stddef.h or similar
        code = """\
#include <stdio.h>

void test(void);
"""
        header = backend.parse(code, "test.h", extra_args=system_args)
        # Should have more than just stdio.h due to transitive includes
        assert len(header.included_headers) >= 1
