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
        c, cython = re.split('^-+$', data, maxsplit=1, flags=re.MULTILINE)
        c = c.strip()
        cython = cython.strip() + '\n'

        whitelist = None
        cpp_args = []
        if file_path == FILES_DIR + '/whitelist.test':
            test_path = os.path.dirname(file_path)
            whitelist = [FILES_DIR + '/tux_foo.h']
            cpp_args = ['-I', test_path]
        actual = autopxd.translate(c, os.path.basename(file_path), cpp_args, whitelist)
        assert cython == actual

    test_func_name = 'test_' + os.path.basename(file_path).replace('.test', '')
    test_func.__name__ = test_func_name
    globals()[test_func_name] = test_func


# Populate globals with one fixture for each test
for file_path in glob.iglob(FILES_DIR + '/*.test'):
    make_test(file_path)

if __name__ == '__main__':
    pytest.main([__file__])
