# python-autopxd2
A friendly fork of autopxd https://github.com/tarruda/python-autopxd

It allows to generate `.pxd` files automatically from `.h` files.

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
- Adding tests for the command line
- Uploading to PyPi
- Check that the generated code is correct by comparing it to the libc in Cython
- More tests
- Merge it into Cython so that the `.pxd` files aren't necessary anymore? Maybe.


#### Please raise an issue if the generated code isn't correct.

It's difficult to catch all the corner cases.


