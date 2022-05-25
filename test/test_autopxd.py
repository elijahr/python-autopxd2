import glob
import os
import re

import pytest

import autopxd

FILES_DIR = os.path.join(os.path.dirname(__file__), "test_files")


@pytest.mark.parametrize("file_path", glob.iglob(os.path.abspath(os.path.join(FILES_DIR, "*.test"))))
def test_cython_vs_header(file_path):
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


if __name__ == "__main__":
    pytest.main([__file__])
