"""Test assertion helpers for pxd output validation.

All tests that generate pxd output MUST use these helpers to ensure:
1. Full text comparison (not partial `in` checks)
2. Cython compilation validation (when possible)
"""

import os

import autopxd
from autopxd.ir import Header
from autopxd.ir_writer import write_pxd
from test.cython_utils import validate_cython_compiles


def assert_pxd_equals(
    code: str,
    expected: str,
    tmp_path,
    backend: str = "pycparser",
    filename: str = "test.h",
    cplus: bool = False,
    extra_args: list[str] | None = None,
    whitelist: list[str] | None = None,
):
    """Assert pxd output matches expected exactly and compiles with Cython.

    Args:
        code: C/C++ input code
        expected: Expected pxd output (full text, must match exactly)
        tmp_path: pytest tmp_path fixture for Cython compilation
        backend: Parser backend to use ("pycparser" or "libclang")
        filename: Filename for the header
        cplus: If True, validate as C++ with Cython
        extra_args: Extra args for the parser
        whitelist: Whitelist for filtering declarations
    """
    actual = autopxd.translate(
        code.strip(),
        filename,
        backend=backend,
        extra_args=extra_args,
        whitelist=whitelist,
    )

    assert actual == expected, (
        f"\n{'='*60}\nEXPECTED:\n{'='*60}\n{repr(expected)}\n" f"{'='*60}\nACTUAL:\n{'='*60}\n{repr(actual)}\n{'='*60}"
    )

    validate_cython_compiles(actual, tmp_path, cplus=cplus)


def assert_ir_to_pxd_equals(
    header: Header,
    expected: str,
    tmp_path,
    cplus: bool = False,
):
    """Assert IR Header produces expected pxd and compiles with Cython.

    Args:
        header: IR Header object
        expected: Expected pxd output (full text, must match exactly)
        tmp_path: pytest tmp_path fixture
        cplus: If True, validate as C++
    """
    actual = write_pxd(header)

    assert actual == expected, (
        f"\n{'='*60}\nEXPECTED:\n{'='*60}\n{repr(expected)}\n" f"{'='*60}\nACTUAL:\n{'='*60}\n{repr(actual)}\n{'='*60}"
    )

    validate_cython_compiles(actual, tmp_path, cplus=cplus)


def assert_pxd_file_equals(
    code: str,
    expected_path: str,
    tmp_path,
    backend: str = "pycparser",
    filename: str = "test.h",
    cplus: bool = False,
    extra_args: list[str] | None = None,
):
    """Assert pxd output matches expected file and compiles with Cython.

    Use this for fixture-based tests where expected output is stored in files.

    Args:
        code: C/C++ input code
        expected_path: Path to .expected.pxd file
        tmp_path: pytest tmp_path fixture for Cython compilation
        backend: Parser backend to use
        filename: Filename for the header
        cplus: If True, validate as C++ with Cython
        extra_args: Extra args for the parser
    """
    with open(expected_path, encoding="utf-8") as f:
        expected = f.read()

    actual = autopxd.translate(
        code.strip(),
        filename,
        backend=backend,
        extra_args=extra_args,
    )

    assert actual == expected, (
        f"\n{'='*60}\nEXPECTED ({os.path.basename(expected_path)}):\n{'='*60}\n{repr(expected)}\n"
        f"{'='*60}\nACTUAL:\n{'='*60}\n{repr(actual)}\n{'='*60}"
    )

    validate_cython_compiles(actual, tmp_path, cplus=cplus)


def assert_header_pxd_equals(
    header: Header,
    expected_path: str,
    tmp_path,
    cplus: bool = False,
):
    """Assert IR Header produces expected pxd from file and compiles with Cython.

    Use this for tests that parse headers directly and compare against expected files.

    Args:
        header: IR Header object (already parsed)
        expected_path: Path to .expected.pxd file
        tmp_path: pytest tmp_path fixture for Cython compilation
        cplus: If True, validate as C++ with Cython
    """
    with open(expected_path, encoding="utf-8") as f:
        expected = f.read()

    actual = write_pxd(header)

    assert actual == expected, (
        f"\n{'='*60}\nEXPECTED ({os.path.basename(expected_path)}):\n{'='*60}\n{repr(expected)}\n"
        f"{'='*60}\nACTUAL:\n{'='*60}\n{repr(actual)}\n{'='*60}"
    )

    validate_cython_compiles(actual, tmp_path, cplus=cplus)


def assert_test_file_equals(
    test_file_path: str,
    tmp_path,
    backend: str = "pycparser",
    cplus: bool = False,
    extra_args: list[str] | None = None,
):
    """Assert a .test file (code + expected separated by ---) matches and compiles.

    Use this for regression tests where input and expected output are in a single file.

    Args:
        test_file_path: Path to .test file with format: header_code\\n---\\nexpected_pxd
        tmp_path: pytest tmp_path fixture for Cython compilation
        backend: Parser backend to use
        cplus: If True, validate as C++ with Cython
        extra_args: Extra args for the parser
    """
    with open(test_file_path, encoding="utf-8") as f:
        content = f.read()

    parts = content.split("\n---\n")
    if len(parts) != 2:
        raise ValueError(f"Invalid test file format: {test_file_path}")

    header_code, expected_pxd = parts
    expected_pxd = expected_pxd.strip() + "\n"
    filename = os.path.basename(test_file_path)

    actual_pxd = autopxd.translate(
        header_code.strip(),
        filename,
        backend=backend,
        extra_args=extra_args,
    )

    assert actual_pxd == expected_pxd, (
        f"\n{'='*60}\nEXPECTED ({filename}):\n{'='*60}\n{repr(expected_pxd)}\n"
        f"{'='*60}\nACTUAL:\n{'='*60}\n{repr(actual_pxd)}\n{'='*60}"
    )

    validate_cython_compiles(actual_pxd, tmp_path, cplus=cplus)
