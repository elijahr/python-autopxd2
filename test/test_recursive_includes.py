"""Tests for recursive include processing."""

from pathlib import Path

import pytest

from autopxd import translate
from autopxd.backends import is_backend_available


@pytest.fixture
def multi_header_project(tmp_path: Path) -> Path:
    """Create a simple multi-header project structure."""
    # Create directory structure
    (tmp_path / "include").mkdir()

    # Main meta-header that includes other headers
    (tmp_path / "include" / "all.h").write_text("""\
#ifndef ALL_H
#define ALL_H

#include "types.h"
#include "functions.h"

#endif
""")

    # Types header
    (tmp_path / "include" / "types.h").write_text("""\
#ifndef TYPES_H
#define TYPES_H

typedef struct {
    int x;
    int y;
} Point;

typedef struct {
    Point start;
    Point end;
} Line;

#endif
""")

    # Functions header
    (tmp_path / "include" / "functions.h").write_text("""\
#ifndef FUNCTIONS_H
#define FUNCTIONS_H

#include "types.h"

Point create_point(int x, int y);
Line create_line(Point start, Point end);
double line_length(Line* line);

#endif
""")

    return tmp_path


@pytest.mark.skipif(
    not is_backend_available("libclang"),
    reason="libclang backend not available",
)
class TestRecursiveIncludes:
    """Tests for recursive include processing."""

    def test_meta_header_includes_all_declarations(self, multi_header_project: Path) -> None:
        """Meta-header should include declarations from all included files."""
        header_path = multi_header_project / "include" / "all.h"
        code = header_path.read_text()

        pxd = translate(
            code,
            str(header_path),
            backend="libclang",
            extra_args=[f"-I{multi_header_project / 'include'}"],
            recursive_includes=True,
        )

        # Should have both struct types
        assert "Point" in pxd
        assert "Line" in pxd

        # Should have all functions
        assert "create_point" in pxd
        assert "create_line" in pxd
        assert "line_length" in pxd

    def test_no_recursive_excludes_included_files(self, multi_header_project: Path) -> None:
        """With recursive_includes=False, only main file declarations appear."""
        header_path = multi_header_project / "include" / "all.h"
        code = header_path.read_text()

        pxd = translate(
            code,
            str(header_path),
            backend="libclang",
            extra_args=[f"-I{multi_header_project / 'include'}"],
            recursive_includes=False,
        )

        # all.h has no declarations of its own, so pxd should be minimal
        # (just the cdef extern block with no declarations inside)
        assert "Point" not in pxd
        assert "Line" not in pxd
        assert "create_point" not in pxd

    def test_single_header_still_works(self, multi_header_project: Path) -> None:
        """A regular header (not meta) should still work with recursive=True."""
        header_path = multi_header_project / "include" / "types.h"
        code = header_path.read_text()

        pxd = translate(
            code,
            str(header_path),
            backend="libclang",
            extra_args=[f"-I{multi_header_project / 'include'}"],
            recursive_includes=True,
        )

        # types.h should have its own declarations
        assert "Point" in pxd
        assert "Line" in pxd
        # But not function declarations from functions.h
        assert "create_point" not in pxd

    def test_system_headers_excluded(self, multi_header_project: Path) -> None:
        """System headers should not be processed even with recursive=True."""
        from autopxd.backends.libclang_backend import get_system_include_dirs

        # Create a header that includes a system header
        (multi_header_project / "include" / "with_stdio.h").write_text("""\
#ifndef WITH_STDIO_H
#define WITH_STDIO_H

#include <stdio.h>

typedef struct {
    FILE* file;
    int count;
} FileCounter;

void count_lines(FileCounter* fc);

#endif
""")

        header_path = multi_header_project / "include" / "with_stdio.h"
        code = header_path.read_text()

        # Include system dirs explicitly since we're also using custom -I
        system_includes = get_system_include_dirs()
        extra_args = [f"-I{multi_header_project / 'include'}"] + system_includes

        pxd = translate(
            code,
            str(header_path),
            backend="libclang",
            extra_args=extra_args,
            recursive_includes=True,
        )

        # Should have our declaration
        assert "FileCounter" in pxd
        assert "count_lines" in pxd

        # Should NOT have tons of stdio.h declarations
        # (fopen, fread, etc. should not appear)
        assert "fopen" not in pxd
        assert "fread" not in pxd

    def test_recursive_includes_default_enabled(self, multi_header_project: Path) -> None:
        """Default behavior should have recursive_includes=True."""
        header_path = multi_header_project / "include" / "all.h"
        code = header_path.read_text()

        # Call without explicit recursive_includes argument
        pxd = translate(
            code,
            str(header_path),
            backend="libclang",
            extra_args=[f"-I{multi_header_project / 'include'}"],
        )

        # Should include declarations from included headers
        assert "Point" in pxd
        assert "Line" in pxd
