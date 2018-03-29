import glob
import os
import re
import pytest
import autopxd


def test_all():
    files_dir = os.path.join(os.path.dirname(__file__), "test_files")
    list_to_test = list(glob.iglob(files_dir + '/*.test'))
    print(len(list_to_test), 'files to test')
    for file_path in list_to_test:
        with open(file_path) as f:
            data = f.read()
        c, cython = re.split('^-+$', data, maxsplit=1, flags=re.MULTILINE)
        c = c.strip()
        cython = cython.strip() + '\n'

        whitelist = None
        cpp_args = []
        if file_path == files_dir + '/whitelist.test':
            test_path = os.path.dirname(file_path)
            whitelist = [files_dir + '/tux_foo.h']
            cpp_args = ['-I', test_path]
        actual = autopxd.translate(c, os.path.basename(file_path), cpp_args, whitelist)
        assert cython == actual


if __name__ == '__main__':
    pytest.main([__file__])
