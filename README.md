# python-autopxd2
A friendly fork of autopxd https://github.com/tarruda/python-autopxd

It allows to generate `.pxd` files automatically from `.h` files.

Tested against:

- Python 2.7
- Python 3.4
- Python 3.6
- PEP8

[![Build Status](https://travis-ci.org/gabrieldemarmiesse/python-autopxd2.svg?branch=master)](https://travis-ci.org/gabrieldemarmiesse/python-autopxd2)

### installation:
```shell
git clone https://github.com/gabrieldemarmiesse/python-autopxd2.git
cd python-autopxd2
pip install -e .
```

### usage:
```shell
autopxd INPUT_PATH OUTPUT_PATH
```

Roadmap:

- Refactoring of the code __DONE__
- Adding tests for PEP8 __DONE__
- Uploading to PyPi
- Check that the generated code is correct by comparing it to the libc in Cython
- More tests
- Merge it into Cython so that the `.pxd` files aren't necessary anymore? Maybe.


#### Please raise an issue if the generated code isn't correct.

It's difficult to catch all the corner cases.


