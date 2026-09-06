"""Tests for the ``--no-recursive`` and ``--max-depth`` umbrella recursion options.

These options are honored only by a backend that follows ``#include``
directives. The libclang backend does; the tree-sitter backend parses exactly
the text it is given. Passing ``max_depth`` to a backend that cannot act on it
must warn rather than be dropped silently.
"""

import textwrap
import warnings

import pytest

from autopxd import translate


@pytest.fixture
def umbrella_tree(tmp_path):
    """An umbrella header over three project headers, one of them nested.

    The umbrella detector requires at least three project includes, so a
    smaller tree would not exercise recursion at all.
    """
    (tmp_path / "deep1.h").write_text(
        textwrap.dedent("""
            #pragma once
            int fn_deep1(int x);
        """)
    )
    (tmp_path / "a1.h").write_text(
        textwrap.dedent("""
            #pragma once
            #include "deep1.h"
            int fn_a1(int x);
        """)
    )
    (tmp_path / "a2.h").write_text(
        textwrap.dedent("""
            #pragma once
            int fn_a2(int x);
        """)
    )
    (tmp_path / "a3.h").write_text(
        textwrap.dedent("""
            #pragma once
            int fn_a3(int x);
        """)
    )
    top = tmp_path / "top.h"
    top.write_text(
        textwrap.dedent("""
            #include "a1.h"
            #include "a2.h"
            #include "a3.h"
        """)
    )
    return top


def _functions(top, **kwargs):
    """Names of functions appearing in the generated pxd for ``top``."""
    pxd = translate(
        code=top.read_text(),
        hdrname=str(top),
        backend="libclang",
        extra_args=[f"-I{top.parent}"],
        **kwargs,
    )
    return {name for name in ("fn_a1", "fn_a2", "fn_a3", "fn_deep1") if name in pxd}


@pytest.mark.libclang
def test_recursion_enabled_by_default_expands_umbrella(umbrella_tree):
    assert _functions(umbrella_tree) == {"fn_a1", "fn_a2", "fn_a3", "fn_deep1"}


@pytest.mark.libclang
def test_no_recursive_suppresses_all_included_declarations(umbrella_tree):
    assert _functions(umbrella_tree, recursive_includes=False) == set()


@pytest.mark.libclang
def test_max_depth_zero_suppresses_all_included_declarations(umbrella_tree):
    assert _functions(umbrella_tree, max_depth=0) == set()


@pytest.mark.libclang
@pytest.mark.parametrize("depth", [1, 2, 10])
def test_max_depth_at_least_one_expands_the_whole_tree(umbrella_tree, depth):
    """Depth >= 1 yields the full transitive set.

    Each included header is parsed as its own translation unit, so clang has
    already flattened that header's own includes by the time the recursion
    loop would descend. ``max_depth`` therefore acts as an on/off switch
    rather than a per-level limit.
    """
    assert _functions(umbrella_tree, max_depth=depth) == {
        "fn_a1",
        "fn_a2",
        "fn_a3",
        "fn_deep1",
    }


@pytest.mark.treesitter
def test_max_depth_warns_on_backend_that_does_not_follow_includes(umbrella_tree):
    with pytest.warns(UserWarning, match="does not follow #include directives"):
        translate(
            code=umbrella_tree.read_text(),
            hdrname=str(umbrella_tree),
            backend="treesitter",
            max_depth=2,
        )


@pytest.mark.treesitter
def test_unspecified_max_depth_does_not_warn(umbrella_tree):
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        translate(
            code=umbrella_tree.read_text(),
            hdrname=str(umbrella_tree),
            backend="treesitter",
        )


@pytest.mark.treesitter
def test_no_recursive_does_not_warn_on_non_recursing_backend(umbrella_tree):
    """``recursive_includes=False`` asks for fewer symbols, which this backend
    already delivers, so the request is satisfied and must stay silent."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        translate(
            code=umbrella_tree.read_text(),
            hdrname=str(umbrella_tree),
            backend="treesitter",
            recursive_includes=False,
        )


@pytest.mark.libclang
def test_max_depth_does_not_warn_on_libclang(umbrella_tree):
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        translate(
            code=umbrella_tree.read_text(),
            hdrname=str(umbrella_tree),
            backend="libclang",
            extra_args=[f"-I{umbrella_tree.parent}"],
            max_depth=2,
        )
