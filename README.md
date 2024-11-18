# python-autopxd2

A friendly fork of autopxd https://github.com/tarruda/python-autopxd

It generates `.pxd` files automatically from `.h` files.

#### Tested against:

- Python 3.10
- Python 3.11
- Python 3.12
- Python 3.13

[![Test](https://github.com/elijahr/python-autopxd2/actions/workflows/test.yml/badge.svg)](https://github.com/elijahr/python-autopxd2/actions/workflows/test.yml)
[![Lint](https://github.com/elijahr/python-autopxd2/actions/workflows/lint.yml/badge.svg)](https://github.com/elijahr/python-autopxd2/actions/workflows/lint.yml)

### Installation:

```shell
pip install autopxd2
```

### Usage:

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

### Contributing:

Contributions are welcome! Please ensure that your code includes unit tests. To install the package in development mode and run tests, use the following commands:

```shell
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

Additionally, we use pre-commit to ensure code quality. To install pre-commit and run it, use the following commands:

```shell
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

### Release History:

#### v2.4.1 - 2024-11-17

- Refactor installation to use only pyproject.toml.
- Update linting to use pre-commit.
- Add contribution guidelines.

#### v2.4.0 - 2024-09-10

- Add: Support for Python 3.12 from Michael Milton [#45](https://github.com/elijahr/python-autopxd2/pull/45)
- Add: Support for char and binary expression in enum from Poiuzy & Emmanuel Leblond [#47](https://github.com/elijahr/python-autopxd2/pull/47)
- Release now also provide a Wheel on Pypi from Emmanuel Leblond #[#46](https://github.com/elijahr/python-autopxd2/pull/46)

#### v2.3.0 - 2023-01-08

- Add: Support for const & volatile qualifiers from Emmanuel Leblond [#42](https://github.com/elijahr/python-autopxd2/pull/42)

#### v2.2.3 - 2022-10-04

- Move to https://github.com/elijahr/python-autopxd2

#### v2.2.0 - 2022-08-03

- Add: Microsoft Visual C++ support from Steve Dower [#40](https://github.com/elijahr/python-autopxd2/pull/40)

#### v2.1.1 - 2022-05-24

- Add: `--regex` for arbitrary conversions
- Fix: Various other fixes and improvements from Mads Ynddal in [#38](https://github.com/elijahr/python-autopxd2/pull/38)

#### v2.0.4 - 2021-11-23

- Fix: Windows CRLF issue ([#24](https://github.com/elijahr/python-autopxd2/pull/24))

#### v2.0.3 - 2021-10-08

- Fix: remove unnecessary `importlib_resources` from `install_requires`

#### v2.0.2 - 2021-10-07

- Migrate to [`setup.cfg`](https://docs.python.org/3/distutils/configfile.html)

#### v2.0.1 - 2021-10-06

- Add: `--compiler-directive` option to pass along to the compiler
- Add: some type annotations (`nodes.py`)
- Deprecation: Drop support for Python 2
- Add: linting, format with black
- Add: Migrate from Travis CI to Github Actions

#### v1.1.0 - 2020-01-03

- Add: Support for macOS

### Roadmap:

- Refactoring of the code **DONE**
- Adding tests for PEP8 **DONE**
- Uploading to PyPi **DONE**
- Check that the generated code is correct by comparing it to the libc in Cython
- More tests
- Merge it into Cython so that the `.pxd` files aren't necessary anymore? Maybe.

#### Please raise an issue if the generated code isn't correct.

It's difficult to catch all the corner cases.

### Stub Headers:

To prevent generating Cython code for `#include <foo>` system headers, python-autopxd2 uses stubbed headers. These are installed with the package and are located in the `autopxd/stubs` directory.

To regenerate the stub headers, use the `regenerate_stubs.py` script. This script downloads the necessary libc stub headers and optionally generates macOS stub headers. This is rarely necessary: only when libc or macOS introduce new header files. Submit a pull request with the updated files.
