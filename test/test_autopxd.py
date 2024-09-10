import glob
import os
import re
import sys

import pytest
from Cython.Build.Dependencies import (
    cythonize_one,
)
from Cython.Compiler.Main import (
    CompilationOptions,
)

import autopxd

FILES_DIR = os.path.join(os.path.dirname(__file__), "test_files")


def do_one_cython_vs_header_test(file_path):
    with open(file_path, encoding="utf-8") as f:
        data = f.read()
    c, cython = re.split("^-+$", data, maxsplit=1, flags=re.MULTILINE)
    c = c.strip()
    cython = cython.strip() + "\n"

    whitelist = []
    cpp_args = []

    # Special handling of whitelist.test
    if file_path.endswith("whitelist.test"):
        whitelist.append(os.path.join(FILES_DIR, "tux_foo.h"))
        cpp_args.append(f"-I{FILES_DIR}")

    # Special handling of whitelist2.test
    if file_path.endswith("whitelist2.test"):
        whitelist.append("<stdin>")  # Only whitelist declarations in 'whitelist2.test' and ignore includes
        cpp_args.append(f"-I{FILES_DIR}")

    actual = autopxd.translate(c, os.path.basename(file_path), cpp_args, whitelist)
    assert cython == actual, f"\nCYTHON:\n{cython}\n\n\nACTUAL:\n{actual}"

    return actual


@pytest.mark.parametrize("file_path", glob.glob(os.path.abspath(os.path.join(FILES_DIR, "*.test"))))
def test_cython_vs_header(file_path, tmp_path):
    actual = do_one_cython_vs_header_test(file_path)

    # Finally ensure the translation is valid Cython !
    src = tmp_path / "x.pyx"
    src.write_text(actual)
    dst = tmp_path / "x.c"
    options = CompilationOptions(
        language_level=3,
    )
    # Will raise `Cython.Compiler.Errors.CompileError` if the .pyx is invalid
    cythonize_one(str(src), str(dst), None, False, options=options)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
@pytest.mark.parametrize("file_path", glob.glob(os.path.abspath(os.path.join(FILES_DIR, "*.test"))))
def test_cython_vs_header_with_msvc(file_path, monkeypatch):
    monkeypatch.setattr(autopxd, "preprocess", autopxd._preprocess_msvc)  # pylint: disable=protected-access
    do_one_cython_vs_header_test(file_path)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
def test_find_cl():
    # In failure cases, this will raise
    cl = autopxd._find_cl()  # pylint: disable=protected-access
    # In success cases, we should have a file path
    assert os.path.isfile(cl)


if __name__ == "__main__":
    pytest.main([__file__])
