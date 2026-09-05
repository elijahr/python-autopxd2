# pylint: disable=attribute-defined-outside-init,import-outside-toplevel,wrong-import-order
"""Tests using realistic header fixtures.

These tests verify that the libclang parser backend can handle patterns
commonly found in real C/C++ libraries.
"""

import os

import pytest

from test.assertions import assert_pxd_file_equals
from test.fixtures.realistic_headers import (
    C_FIXTURES,
    CPP_FIXTURES,
)

EXPECTED_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "realistic_headers")


@pytest.mark.libclang
class TestRealisticCHeaders:
    """Test libclang backend with realistic C headers."""

    @pytest.mark.parametrize("fixture_name", list(C_FIXTURES.keys()))
    def test_parse_c_fixture(self, backend, fixture_name):
        """Test that backend can parse realistic C headers."""
        code = C_FIXTURES[fixture_name]
        header = backend.parse(code, f"{fixture_name}.h")

        assert len(header.declarations) > 0
        decl_types = {type(d).__name__ for d in header.declarations}
        assert decl_types & {"Function", "Struct", "Typedef", "Enum"}

    @pytest.mark.parametrize("fixture_name", list(C_FIXTURES.keys()))
    def test_generate_pxd_c_fixture(self, fixture_name, tmp_path):
        """Test pxd generation from realistic C headers matches expected and compiles."""
        code = C_FIXTURES[fixture_name]
        expected_path = os.path.join(EXPECTED_DIR, f"{fixture_name}.expected.pxd")

        assert_pxd_file_equals(
            code,
            expected_path,
            tmp_path,
            backend="libclang",
            filename=f"{fixture_name}.h",
        )

    @pytest.mark.parametrize("fixture_name", list(C_FIXTURES.keys()))
    def test_generate_pxd_c_fixture_treesitter_compiles(self, fixture_name, tmp_path):
        """Test pxd generation from realistic C headers using tree-sitter compiles with Cython."""
        from headerkit.backends import is_backend_available

        if not is_backend_available("tree-sitter"):
            pytest.skip("tree-sitter optional dependency not installed")

        import autopxd
        from test.cython_utils import validate_cython_compiles

        code = C_FIXTURES[fixture_name]
        pxd = autopxd.translate(code.strip(), f"{fixture_name}.h", backend="tree-sitter")
        assert len(pxd) > 0

        header_file = tmp_path / f"{fixture_name}.h"
        header_file.write_text(code.strip())
        validate_cython_compiles(pxd, tmp_path, cplus=False, include_dirs=[str(tmp_path)])


@pytest.mark.libclang
class TestRealisticCppHeaders:
    """Test C++ headers (libclang only)."""

    @pytest.fixture
    def libclang_backend(self):
        """Provide libclang backend for C++ tests."""
        from headerkit.backends import get_backend

        return get_backend("libclang")

    @pytest.mark.parametrize("fixture_name", list(CPP_FIXTURES.keys()))
    def test_parse_cpp_fixture(self, backend, fixture_name):
        """Test that backend can parse C++ headers."""
        code = CPP_FIXTURES[fixture_name]
        header = backend.parse(code, f"{fixture_name}.hpp", extra_args=["-x", "c++"])

        assert len(header.declarations) > 0

    @pytest.mark.parametrize("fixture_name", list(CPP_FIXTURES.keys()))
    def test_generate_pxd_cpp_fixture(self, fixture_name, tmp_path):
        """Test pxd generation from C++ headers matches expected and compiles."""
        code = CPP_FIXTURES[fixture_name]
        expected_path = os.path.join(EXPECTED_DIR, f"{fixture_name}.expected.pxd")

        assert_pxd_file_equals(
            code,
            expected_path,
            tmp_path,
            backend="libclang",
            filename=f"{fixture_name}.hpp",
            cplus=True,
            extra_args=["-x", "c++"],
        )

    @pytest.mark.parametrize("fixture_name", list(CPP_FIXTURES.keys()))
    def test_generate_pxd_cpp_fixture_treesitter_compiles(self, fixture_name, tmp_path):
        """Test pxd generation from C++ headers using tree-sitter compiles with Cython."""
        from headerkit.backends import is_backend_available

        if not is_backend_available("tree-sitter"):
            pytest.skip("tree-sitter optional dependency not installed")

        import autopxd
        from test.cython_utils import validate_cython_compiles

        code = CPP_FIXTURES[fixture_name]
        pxd = autopxd.translate(
            code.strip(),
            f"{fixture_name}.hpp",
            backend="tree-sitter",
            extra_args=["-x", "c++"],
        )
        assert len(pxd) > 0

        header_file = tmp_path / f"{fixture_name}.hpp"
        header_file.write_text(code.strip())
        validate_cython_compiles(pxd, tmp_path, cplus=True, include_dirs=[str(tmp_path)])
