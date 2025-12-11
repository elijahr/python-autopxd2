"""Cython compilation validation utilities for tests."""

from Cython.Build.Dependencies import cythonize_one
from Cython.Compiler.Main import CompilationOptions


def validate_cython_compiles(pxd_content: str, tmp_path, cplus: bool = False) -> None:
    """Validate that pxd content compiles with Cython.

    Args:
        pxd_content: The pxd content to validate
        tmp_path: pytest tmp_path fixture
        cplus: If True, compile as C++

    Raises:
        Cython.Compiler.Errors.CompileError: If compilation fails
    """
    src = tmp_path / "test.pyx"
    src.write_text(pxd_content)
    dst = tmp_path / ("test.cpp" if cplus else "test.c")
    options = CompilationOptions(
        language_level=3,
        cplus=cplus,
    )
    cythonize_one(str(src), str(dst), None, False, options=options)
