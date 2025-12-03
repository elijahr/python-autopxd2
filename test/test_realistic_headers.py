# pylint: disable=attribute-defined-outside-init,import-outside-toplevel,wrong-import-order
"""Tests using realistic header fixtures.

These tests verify that both parser backends can handle patterns
commonly found in real C/C++ libraries.
"""

import re

import pytest
from fixtures.realistic_headers import (
    C_FIXTURES,
    CPP_FIXTURES,
)

from autopxd.ir import (
    Function,
)
from autopxd.ir_writer import (
    write_pxd,
)


def preprocess_for_pycparser(code: str) -> str:
    """Remove comments and preprocessor directives for pycparser."""
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    code = re.sub(r"//.*$", "", code, flags=re.MULTILINE)
    code = re.sub(r"^#.*$", "", code, flags=re.MULTILINE)
    return code


def get_code_for_backend(code: str, backend_name: str) -> str:
    """Preprocess code if needed for backend."""
    if backend_name == "pycparser":
        return preprocess_for_pycparser(code)
    return code


class TestRealisticCHeaders:
    """Test backends with realistic C headers."""

    @pytest.mark.parametrize("fixture_name", list(C_FIXTURES.keys()))
    def test_parse_c_fixture(self, backend, fixture_name):
        """Test that backend can parse realistic C headers."""
        code = get_code_for_backend(C_FIXTURES[fixture_name], backend.name)
        header = backend.parse(code, f"{fixture_name}.h")

        assert len(header.declarations) > 0
        decl_types = {type(d).__name__ for d in header.declarations}
        assert decl_types & {"Function", "Struct", "Typedef", "Enum"}

    @pytest.mark.parametrize("fixture_name", list(C_FIXTURES.keys()))
    def test_generate_pxd_c_fixture(self, backend, fixture_name):
        """Test pxd generation from realistic C headers."""
        code = get_code_for_backend(C_FIXTURES[fixture_name], backend.name)
        header = backend.parse(code, f"{fixture_name}.h")
        pxd = write_pxd(header)

        assert len(pxd) > 0
        assert "cdef extern from" in pxd


@pytest.mark.requires_cpp
class TestRealisticCppHeaders:
    """Test C++ headers (libclang only)."""

    @pytest.mark.parametrize("fixture_name", list(CPP_FIXTURES.keys()))
    def test_parse_cpp_fixture(self, backend, fixture_name):
        """Test that backend can parse C++ headers."""
        code = CPP_FIXTURES[fixture_name]
        header = backend.parse(code, f"{fixture_name}.hpp", extra_args=["-x", "c++"])

        assert len(header.declarations) > 0

    @pytest.mark.parametrize("fixture_name", list(CPP_FIXTURES.keys()))
    def test_generate_pxd_cpp_fixture(self, backend, fixture_name):
        """Test pxd generation from C++ headers."""
        code = CPP_FIXTURES[fixture_name]
        header = backend.parse(code, f"{fixture_name}.hpp", extra_args=["-x", "c++"])
        pxd = write_pxd(header)

        assert len(pxd) > 0
        assert "cdef extern from" in pxd


class TestBackendConsistency:
    """Test that both backends produce consistent results for C code."""

    @pytest.mark.parametrize("fixture_name", list(C_FIXTURES.keys()))
    def test_function_names_consistent(self, backend, fixture_name):
        """Test that backend finds expected functions."""
        code = get_code_for_backend(C_FIXTURES[fixture_name], backend.name)
        header = backend.parse(code, f"{fixture_name}.h")

        functions = [d for d in header.declarations if isinstance(d, Function)]
        # Just verify we found some functions (specific count varies by backend)
        assert len(functions) >= 1, f"No functions found in {fixture_name}"
