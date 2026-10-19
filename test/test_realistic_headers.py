# pylint: disable=attribute-defined-outside-init,wrong-import-order
"""Tests using realistic header fixtures.

These tests verify that the parser backends can handle patterns commonly found
in real C/C++ libraries.
"""

import os

import pytest
from headerkit.backends import is_backend_available

import autopxd
from test.assertions import assert_pxd_file_equals
from test.cython_utils import validate_cython_compiles
from test.fixtures.realistic_headers import (
    C_FIXTURES,
    CPP_FIXTURES,
)

EXPECTED_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "realistic_headers")

requires_treesitter = pytest.mark.skipif(
    not is_backend_available("tree-sitter"),
    reason="tree-sitter optional dependency not installed",
)

# Symbols each fixture must contribute to generated pxd output. An extern block
# with zero declarations compiles cleanly, so a length check cannot detect a
# backend that emits nothing; these names make that failure visible.
C_FIXTURE_SYMBOLS = {
    "compression_lib": ("compress_stream", "compress_status", "COMPRESS_OK", "compress_init", "compress_bound"),
    "database_lib": ("db_callback", "db_open", "db_close", "db_prepare", "db_column_double"),
    "json_lib": ("json_type", "JSON_OBJECT", "json_error_t", "json_typeof", "json_array_append_new"),
    "network_protocol": ("msg_type_t", "MSG_CONNECT", "msg_header_t", "callbacks_t", "conn_create"),
}

CPP_FIXTURE_SYMBOLS = {
    "cpp_container": ("Point", "Vector2D", "Rectangle", "make_vector", "distance"),
}


class TestRealisticCHeaders:
    """Test parser backends with realistic C headers."""

    @pytest.mark.parametrize("fixture_name", list(C_FIXTURES.keys()))
    def test_parse_c_fixture(self, backend, fixture_name):
        """Test that backend can parse realistic C headers."""
        code = C_FIXTURES[fixture_name]
        header = backend.parse(code, f"{fixture_name}.h")

        assert len(header.declarations) > 0
        decl_types = {type(d).__name__ for d in header.declarations}
        assert decl_types & {"Function", "Struct", "Typedef", "Enum"}

    @pytest.mark.libclang
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

    @pytest.mark.treesitter
    @requires_treesitter
    @pytest.mark.parametrize("fixture_name", list(C_FIXTURES.keys()))
    def test_generate_pxd_c_fixture_treesitter_compiles(self, fixture_name, tmp_path):
        """Test pxd generation from realistic C headers using tree-sitter compiles with Cython."""
        code = C_FIXTURES[fixture_name]
        pxd = autopxd.translate(code.strip(), f"{fixture_name}.h", backend="tree-sitter")

        for symbol in C_FIXTURE_SYMBOLS[fixture_name]:
            assert symbol in pxd, f"{fixture_name}: tree-sitter output is missing {symbol!r}"

        header_file = tmp_path / f"{fixture_name}.h"
        header_file.write_text(code.strip())
        validate_cython_compiles(pxd, tmp_path, cplus=False, include_dirs=[str(tmp_path)])


class TestRealisticCppHeaders:
    """Test C++ headers."""

    @pytest.mark.parametrize("fixture_name", list(CPP_FIXTURES.keys()))
    def test_parse_cpp_fixture(self, backend, fixture_name):
        """Test that backend can parse C++ headers."""
        code = CPP_FIXTURES[fixture_name]
        header = backend.parse(code, f"{fixture_name}.hpp", extra_args=["-x", "c++"])

        assert len(header.declarations) > 0

    @pytest.mark.libclang
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

    @pytest.mark.treesitter
    @requires_treesitter
    @pytest.mark.parametrize("fixture_name", list(CPP_FIXTURES.keys()))
    def test_generate_pxd_cpp_fixture_treesitter_compiles(self, fixture_name, tmp_path):
        """Test pxd generation from C++ headers using tree-sitter compiles with Cython."""
        code = CPP_FIXTURES[fixture_name]
        pxd = autopxd.translate(
            code.strip(),
            f"{fixture_name}.hpp",
            backend="tree-sitter",
            extra_args=["-x", "c++"],
        )

        for symbol in CPP_FIXTURE_SYMBOLS[fixture_name]:
            assert symbol in pxd, f"{fixture_name}: tree-sitter output is missing {symbol!r}"

        header_file = tmp_path / f"{fixture_name}.hpp"
        header_file.write_text(code.strip())
        validate_cython_compiles(pxd, tmp_path, cplus=True, include_dirs=[str(tmp_path)])
