"""Regression tests for specific GitHub issues.

Each .test file in cases/ contains:
- C/C++ header code (top section)
- Expected Cython output (bottom section, after ---)

Tests verify:
1. Output matches expected EXACTLY (full text assertion)
2. Output compiles with Cython
"""

import glob
import os

import pytest

from test.assertions import assert_test_file_equals

CASES_DIR = os.path.join(os.path.dirname(__file__), "cases")


def get_test_cases():
    """Get all regression test cases."""
    return glob.glob(os.path.join(CASES_DIR, "*.test"))


def get_cpp_test_cases():
    """Get C++ regression test cases."""
    return glob.glob(os.path.join(CASES_DIR, "*.cpptest"))


@pytest.mark.pycparser
@pytest.mark.parametrize("file_path", get_test_cases(), ids=lambda p: os.path.basename(p))
def test_regression_pycparser(file_path, tmp_path):
    """Test regression case with pycparser backend."""
    assert_test_file_equals(file_path, tmp_path, backend="pycparser")


@pytest.mark.libclang
@pytest.mark.parametrize("file_path", get_cpp_test_cases(), ids=lambda p: os.path.basename(p))
def test_regression_libclang_cpp(file_path, tmp_path):
    """Test C++ regression case with libclang backend."""
    assert_test_file_equals(
        file_path,
        tmp_path,
        backend="libclang",
        cplus=True,
        extra_args=["-x", "c++", "-std=c++11"],
    )
