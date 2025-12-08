# autopxd2

Automatically generate Cython `.pxd` declaration files from C/C++ header files.

[![PyPI version](https://badge.fury.io/py/autopxd2.svg)](https://pypi.org/project/autopxd2/)
[![Python versions](https://img.shields.io/pypi/pyversions/autopxd2.svg)](https://pypi.org/project/autopxd2/)
[![Test](https://github.com/elijahr/python-autopxd2/actions/workflows/test.yml/badge.svg)](https://github.com/elijahr/python-autopxd2/actions/workflows/test.yml)
[![Documentation](https://github.com/elijahr/python-autopxd2/actions/workflows/docs.yml/badge.svg)](https://elijahr.github.io/python-autopxd2/)
[![License](https://img.shields.io/github/license/elijahr/python-autopxd2.svg)](https://github.com/elijahr/python-autopxd2/blob/master/LICENSE)

## Overview

autopxd2 parses C header files and generates Cython `.pxd` files, enabling you to call C libraries from Cython without manually writing declarations.

**Key features:**

- Generates complete `.pxd` files from C headers
- Handles structs, unions, enums, typedefs, and function declarations
- Cross-platform support (Linux, macOS, Windows)
- Multiple parser backends (pycparser, libclang)

## Installation

```shell
pip install autopxd2
```

This installs both parser backends. The libclang backend (with full C++ support) is used by default if the system libclang library is available; otherwise autopxd2 falls back to the pycparser backend (C99 only).

See the [installation docs](https://elijahr.github.io/python-autopxd2/getting-started/installation/) for system libclang setup.

## Quick Start

```shell
# Generate a .pxd file from a C header
autopxd myheader.h myheader.pxd

# Include additional directories
autopxd -I /usr/include myheader.h myheader.pxd

# Read from stdin, write to stdout
cat myheader.h | autopxd > myheader.pxd
```

## Usage

```
autopxd [OPTIONS] [INFILE] [OUTFILE]

Options:
  -v, --version                  Print program version and exit.
  -b, --backend <name>           Parser backend: auto (default), libclang, pycparser.
  --list-backends                Show available backends and exit.
  --json                         JSON output (for --list-backends).
  -x, --cpp                      Parse as C++ (requires libclang).
  --std <standard>               Language standard (e.g., c11, c++17).
  -I, --include-dir <dir>        Add directory to preprocessor search path.
  -D, --compiler-directive <d>   Pass directive to the C preprocessor.
  -R, --regex <pattern>          Apply sed-style substitution (s/.../.../g).
  -w, --whitelist <file>         Only generate from specified files.
  --clang-arg <arg>              Pass argument to libclang.
  -q, --quiet                    Suppress warnings.
  --debug / --no-debug           Dump preprocessor output to stderr.
  -h, --help                     Show this message and exit.
```

## Documentation

Full documentation is available at [elijahr.github.io/python-autopxd2](https://elijahr.github.io/python-autopxd2/).

## Docker

A Docker image is available for environments where installing dependencies is difficult:

```shell
docker run --rm -v $(pwd):/work ghcr.io/elijahr/autopxd2 myheader.h myheader.pxd
```

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT License. See [LICENSE](LICENSE) for details.

## Acknowledgments

This project is a fork of [python-autopxd](https://github.com/tarruda/python-autopxd) by Thiago de Arruda.
