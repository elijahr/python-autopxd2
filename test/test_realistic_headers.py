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


@pytest.mark.libclang
class TestRealisticCppHeaders:
    """Test C++ headers (libclang only)."""

    @pytest.fixture
    def libclang_backend(self):
        """Provide libclang backend for C++ tests."""
        from autopxd.backends import get_backend

        return get_backend("libclang")

    @pytest.mark.parametrize("fixture_name", list(CPP_FIXTURES.keys()))
    def test_parse_cpp_fixture(self, libclang_backend, fixture_name):
        """Test that backend can parse C++ headers."""
        code = CPP_FIXTURES[fixture_name]
        header = libclang_backend.parse(code, f"{fixture_name}.hpp", extra_args=["-x", "c++"])

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
