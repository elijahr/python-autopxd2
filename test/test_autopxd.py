import glob
import os
import re

import pytest
from Cython.Build.Dependencies import (
    cythonize_one,
)
from Cython.Compiler.Main import (
    CompilationOptions,
)

import autopxd

FILES_DIR = os.path.join(os.path.dirname(__file__), "test_files")


def do_one_cython_vs_header_test(
    file_path: str, backend: str = "pycparser", extra_args: list[str] | None = None
) -> str:
    with open(file_path, encoding="utf-8") as f:
        data = f.read()
    c, cython = re.split("^-+$", data, maxsplit=1, flags=re.MULTILINE)
    c = c.strip()
    cython = cython.strip() + "\n"

    whitelist: list[str] | None = None
    args: list[str] = list(extra_args) if extra_args else []

    # Special handling of whitelist.test
    if file_path.endswith("whitelist.test"):
        whitelist = [os.path.join(FILES_DIR, "tux_foo.h")]
        args.append(f"-I{FILES_DIR}")

    # Special handling of whitelist2.test
    if file_path.endswith("whitelist2.test"):
        whitelist = ["<stdin>"]  # Only whitelist declarations in this file, ignore includes
        args.append(f"-I{FILES_DIR}")

    # xnvme_opts.test includes system headers, only whitelist main file
    if file_path.endswith("xnvme_opts.test"):
        whitelist = ["<stdin>"]

    actual = autopxd.translate(
        code=c,
        hdrname=os.path.basename(file_path),
        backend=backend,
        extra_args=args if args else None,
        whitelist=whitelist,
    )
    assert cython == actual, f"\nCYTHON:\n{cython}\n\n\nACTUAL:\n{actual}"

    return actual


@pytest.mark.pycparser
@pytest.mark.parametrize("file_path", glob.glob(os.path.abspath(os.path.join(FILES_DIR, "*.test"))))
def test_cython_vs_header(file_path, tmp_path):
    actual = do_one_cython_vs_header_test(file_path, backend="pycparser")

    # Finally ensure the translation is valid Cython !
    src = tmp_path / "x.pyx"
    src.write_text(actual)
    dst = tmp_path / "x.c"
    options = CompilationOptions(
        language_level=3,
    )
    # Will raise `Cython.Compiler.Errors.CompileError` if the .pyx is invalid
    cythonize_one(str(src), str(dst), None, False, options=options)


@pytest.mark.libclang
@pytest.mark.parametrize("file_path", glob.glob(os.path.abspath(os.path.join(FILES_DIR, "*.cpptest"))))
def test_cython_vs_cpp_header(file_path, tmp_path):
    """Test C++ header files with libclang backend."""
    actual = do_one_cython_vs_header_test(file_path, backend="libclang", extra_args=["-x", "c++", "-std=c++11"])

    # Ensure the translation is valid Cython
    src = tmp_path / "x.pyx"
    src.write_text(actual)
    dst = tmp_path / "x.cpp"
    options = CompilationOptions(
        language_level=3,
        cplus=True,
    )
    # Will raise `Cython.Compiler.Errors.CompileError` if the .pyx is invalid
    cythonize_one(str(src), str(dst), None, False, options=options)


if __name__ == "__main__":
    pytest.main([__file__])
