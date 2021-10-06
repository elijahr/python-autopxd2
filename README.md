# python-autopxd2

A friendly fork of autopxd https://github.com/tarruda/python-autopxd

It generates `.pxd` files automatically from `.h` files.

Tested against:

- Python 3.6
- Python 3.7
- Python 3.8
- Python 3.9
- PEP8

[![Test](https://github.com/gabrieldemarmiesse/python-autopxd2/actions/workflows/test.yml/badge.svg)](https://github.com/gabrieldemarmiesse/python-autopxd2/actions/workflows/test.yml)
[![Lint](https://github.com/gabrieldemarmiesse/python-autopxd2/actions/workflows/lint.yml/badge.svg)](https://github.com/gabrieldemarmiesse/python-autopxd2/actions/workflows/lint.yml)

### installation:

```shell
pip install autopxd2
```

### usage:

```shell
Usage: autopxd [OPTIONS] [INFILE] [OUTFILE]

  Generate a Cython pxd file from a C header file.

Options:
  -v, --version                   Print program version and exit.
  -I, --include-dir <dir>         Allow the C preprocessor to search for files
                                  in <dir>.

  -D, --compiler-directive <directive>
                                  Additional directives for the C compiler.
  --debug / --no-debug            Dump preprocessor output to stderr.
  -h, --help                      Show this message and exit.
```

### release history:

#### v2.0.0 - 2021-10-06

- Add `--compiler-directive` option to pass along to the compiler
- Add some type annotations (`nodes.py`)
- Drop support for Python 2
- Add linting, format with black
- Migrate from Travis CI to Github Actions

#### v1.1.0 - 2020-01-03

- Support for OSX

### roadmap:

- Refactoring of the code **DONE**
- Adding tests for PEP8 **DONE**
- Uploading to PyPi **DONE**
- Check that the generated code is correct by comparing it to the libc in Cython
- More tests
- Merge it into Cython so that the `.pxd` files aren't necessary anymore? Maybe.

#### Please raise an issue if the generated code isn't correct.

It's difficult to catch all the corner cases.
