"""Integration tests for auto-import functionality."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from autopxd import translate

# Mark entire module as requiring libclang
pytestmark = pytest.mark.libclang

# Only run with libclang for header tracking
libclang = pytest.importorskip("clang.cindex")


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


class TestAutoImportIntegration:
    """End-to-end tests for automatic cimport generation."""

    @pytest.fixture
    def backend(self):
        return "libclang"

    @pytest.fixture
    def system_args(self):
        """System include arguments for parsing system headers."""
        return _get_system_include_args()

    def test_stdio_auto_import(self, backend, system_args):
        """FILE pointer in function generates stdio cimport."""
        code = """\
#include <stdio.h>

int read_file(FILE *f);
"""
        result = translate(code, "test.h", backend=backend, extra_args=system_args)

        assert "from libc.stdio cimport FILE" in result
        assert 'cdef extern from "test.h"' in result
        assert "int read_file(FILE* f)" in result

    def test_stdint_auto_import(self, backend, system_args):
        """stdint types generate appropriate cimport."""
        code = """\
#include <stdint.h>

uint32_t hash_data(const uint8_t *data, int64_t len);
"""
        result = translate(code, "test.h", backend=backend, extra_args=system_args)

        assert "from libc.stdint cimport" in result
        assert "uint32_t" in result
        assert "uint8_t" in result
        assert "int64_t" in result

    def test_va_list_auto_import(self, backend, system_args):
        """va_list generates stub cimport."""
        code = """\
#include <stdarg.h>

void log_message(const char *fmt, va_list args);
"""
        result = translate(code, "test.h", backend=backend, extra_args=system_args)

        assert "from autopxd.stubs.stdarg cimport va_list" in result
        # Old inline declaration should NOT be present
        assert "ctypedef struct va_list:" not in result

    def test_mixed_types_ordered_cimports(self, backend, system_args):
        """Multiple type sources generate properly ordered cimports."""
        code = """\
#include <stdio.h>
#include <stdint.h>
#include <stdarg.h>

int process(FILE *f, uint32_t flags, va_list args);
"""
        result = translate(code, "test.h", backend=backend, extra_args=system_args)

        lines = result.split("\n")

        # Find positions of different cimport types
        stdio_line = next(i for i, line in enumerate(lines) if "libc.stdio" in line)
        stdint_line = next(i for i, line in enumerate(lines) if "libc.stdint" in line)
        stub_line = next(i for i, line in enumerate(lines) if "autopxd.stubs" in line)
        extern_line = next(i for i, line in enumerate(lines) if "cdef extern from" in line)

        # All cimports before extern
        assert stdio_line < extern_line
        assert stdint_line < extern_line
        assert stub_line < extern_line

    def test_cython_compiles(self, backend, system_args, tmp_path):
        """Generated pxd with cimports compiles with Cython."""
        code = """\
#include <stdio.h>
#include <stdint.h>

uint32_t read_data(FILE *f);
"""
        result = translate(code, "test.h", backend=backend, extra_args=system_args)

        # Write to temp file
        pxd_path = tmp_path / "test.pxd"
        pxd_path.write_text(result)

        # Try to compile with Cython
        proc = subprocess.run(
            [sys.executable, "-m", "cython", "-3", str(pxd_path)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"Cython failed: {proc.stderr}"
