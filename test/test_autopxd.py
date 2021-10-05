import glob
import os
import re

import pytest

import autopxd

FILES_DIR = os.path.join(os.path.dirname(__file__), "test_files")


def make_test(file_path):
    def test_func():
        with open(file_path) as f:
            data = f.read()
        c, cython = re.split("^-+$", data, maxsplit=1, flags=re.MULTILINE)
        c = c.strip()
        cython = cython.strip() + "\n"

        whitelist = []
        cpp_args = []
        if file_path == os.path.join(FILES_DIR, "whitelist.test"):
            test_path = os.path.dirname(file_path)
            whitelist.append(os.path.join(FILES_DIR, "tux_foo.h"))
            if test_path:
                cpp_args.append("-I%s" % test_path)
        actual = autopxd.translate(c, os.path.basename(file_path), cpp_args, whitelist)
        assert cython == actual

    test_func_name = "test_" + os.path.basename(file_path).replace(".test", "")
    test_func.__name__ = test_func_name
    globals()[test_func_name] = test_func


# Populate globals with one fixture for each test
for fp in glob.iglob(os.path.abspath(os.path.join(FILES_DIR, "*.test"))):
    make_test(fp)

if __name__ == "__main__":
    pytest.main([__file__])
