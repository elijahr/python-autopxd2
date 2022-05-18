import glob
import os
import re

import pytest

import autopxd

FILES_DIR = os.path.join(os.path.dirname(__file__), "test_files")


@pytest.mark.parametrize("file_path", glob.iglob(os.path.abspath(os.path.join(FILES_DIR, "*.test"))))
def test_cython_vs_header(file_path):
    with open(file_path) as f:
        data = f.read()
    c, cython = re.split("^-+$", data, maxsplit=1, flags=re.MULTILINE)
    c = c.strip()
    cython = cython.strip() + "\n"

    # Special handling of whitelist.test
    whitelist = []
    cpp_args = []
    if file_path == os.path.join(FILES_DIR, "whitelist.test"):
        test_path = os.path.dirname(file_path)
        whitelist.append(os.path.join(FILES_DIR, "tux_foo.h"))
        if test_path:
            cpp_args.append("-I%s" % test_path)

    actual = autopxd.translate(c, os.path.basename(file_path), cpp_args, whitelist)
    assert cython == actual, f"\nCYTHON:\n{cython}\n\n\nACTUAL:\n{actual}"

if __name__ == "__main__":
    pytest.main([__file__])
