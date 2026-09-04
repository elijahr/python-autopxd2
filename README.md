# autopxd2

Automatically generate Cython `.pxd` declaration files from C/C++ header files.

[![PyPI version](https://badge.fury.io/py/autopxd2.svg)](https://pypi.org/project/autopxd2/)
[![Python versions](https://img.shields.io/pypi/pyversions/autopxd2.svg)](https://pypi.org/project/autopxd2/)
[![Test](https://github.com/elijahr/python-autopxd2/actions/workflows/test.yml/badge.svg)](https://github.com/elijahr/python-autopxd2/actions/workflows/test.yml)
[![Documentation](https://github.com/elijahr/python-autopxd2/actions/workflows/docs.yml/badge.svg)](https://elijahr.github.io/python-autopxd2/)
[![License](https://img.shields.io/github/license/elijahr/python-autopxd2.svg)](https://github.com/elijahr/python-autopxd2/blob/master/LICENSE)

## Overview

autopxd2 parses C and C++ header files and generates Cython `.pxd` declaration files, enabling you to call native C/C++ libraries from Cython without manually writing boilerplate declarations.

**Key features:**

- Generates complete `.pxd` declaration files from C/C++ headers
- Powered by `headerkit` and LLVM `libclang` (supporting LLVM 18–23)
- Full C++ support: classes, methods, constructors, destructors, multiple inheritance, templates, and namespaces
- Automatic system include path detection
- Auto-generates `cimport` statements for standard library types and bundled stubs
- Cross-platform support (Linux, macOS, Windows)

## Supported Features

### C Features

| Feature | Supported |
|---------|:---------:|
| Structs and unions | ✓ |
| Enums (with expressions) | ✓ |
| Typedefs | ✓ |
| Function declarations | ✓ |
| Function pointers | ✓ |
| Arrays (fixed and flexible) | ✓ |
| Pointers and const qualifiers | ✓ |
| Forward declarations | ✓ |
| Anonymous structs/unions | ✓ |
| Bit fields | ✓ |
| `#define` macros (int, float, string) | ✓ |
| Circular type dependencies | ✓ |

### C++ Features

| Feature | Supported |
|---------|:---------:|
| Classes and structs (`cppclass`) | ✓ |
| Constructors and destructors | ✓ |
| Methods (`const`, `@staticmethod`) | ✓ |
| Multiple inheritance | ✓ |
| Namespaces (including nested) | ✓ |
| Generic function and method templates (`T max[T](T a, T b)`) | ✓ |
| Class templates with type parameters | ✓ |
| Template specializations | ✓ |
| Operator overloading (renamed for Cython) | ✓ |
| References and const references | ✓ |

## Installation

```shell
pip install autopxd2
```

autopxd2 uses `headerkit`, which vendors official LLVM clang Python bindings for LLVM 18–23 directly. No separate `clang` or `clang2` Python package is needed.

You only need the system `libclang` shared library (`libclang.so`, `libclang.dylib`, or `libclang.dll`).

If `libclang` is not already installed on your system, install it via your system package manager:
- **macOS**: `brew install llvm`
- **Ubuntu/Debian**: `sudo apt-get install libclang-dev`
- **Fedora/RHEL**: `sudo dnf install clang-devel`
- **Windows**: `winget install LLVM.LLVM`

Or use HeaderKit's built-in installer:
```shell
python -m headerkit.install_libclang
```

See the [installation docs](https://elijahr.github.io/python-autopxd2/getting-started/installation/) for more details.

### Alternative: Tree-sitter Backend (No LLVM Dependency)

To parse C and C++ headers without requiring system `libclang`, install the `treesitter` extra:

```shell
pip install "autopxd2[treesitter]"
```

Then specify `--backend tree-sitter`:

```shell
autopxd --backend tree-sitter myheader.h myheader.pxd
```

## Quick Start

```shell
# Generate a .pxd file from a C header
autopxd myheader.h myheader.pxd

# Parse a C++ header
autopxd --cpp myclass.hpp myclass.pxd

# Add project-specific include directories (system includes are auto-detected)
autopxd -I ./include myheader.h myheader.pxd

# Write to stdout (omit output file or use '-')
autopxd myheader.h > myheader.pxd

# Read from stdin
cat myheader.h | autopxd -
```

## Usage

```
autopxd [OPTIONS] [INFILE] [OUTFILE]

Options:
  -v, --version                  Print version and exit.
  -b, --backend TEXT             Parser backend (default: auto, using libclang).
  --list-backends                List available backends and exit.
  --json                         JSON output (with --list-backends).
  -q, --quiet                    Suppress warnings.
  --debug / --no-debug           Print debug info to stderr.
  -I, --include-dir <dir>        Add include search path.
  -D, --define <macro>           Define preprocessor macro.
  -w, --whitelist <pattern>      Only emit from files matching pattern.
  -x, --cpp                      Parse as C++.
  --std <std>                    Language standard (e.g., c11, c++17).
  --clang-arg <arg>              Pass argument to clang.
  --no-default-includes          Disable system include auto-detection.
  -P, --project-prefix <path>    Treat path as project (not system) for umbrella headers.
  --no-recursive                 Disable recursive parsing of umbrella headers.
  --max-depth <n>                Max recursion depth for umbrella headers (default: 10).
  -h, --help                     Show this message and exit.
```

## Automatic Imports

autopxd2 automatically generates `cimport` statements for commonly used types when using the libclang backend.

### Cython Standard Library Types

When headers use types from C standard library headers, autopxd generates appropriate Cython cimports:

```c
// input.h
#include <stdio.h>
#include <stdint.h>

uint32_t process(FILE *f);
```

```cython
# Generated output
from libc.stdint cimport uint32_t
from libc.stdio cimport FILE

cdef extern from "input.h":
    uint32_t process(FILE* f)
```

### Bundled Stub Types

For types not in Cython's standard library, autopxd provides bundled stub declarations:

```c
// input.h
#include <stdarg.h>

void log_message(const char *fmt, va_list args);
```

```cython
# Generated output
from headerkit.stubs.stdarg cimport va_list

cdef extern from "input.h":
    void log_message(const char* fmt, va_list args)
```

### C++ STL Types

C++ standard library types are automatically imported from `libcpp`:

```cpp
// input.hpp
#include <vector>
#include <string>

std::vector<std::string> get_items();
```

```cython
# Generated output
from libcpp.string cimport string
from libcpp.vector cimport vector

cdef extern from "input.hpp":
    vector[string] get_items()
```

## Documentation

Full documentation is available at [elijahr.github.io/python-autopxd2](https://elijahr.github.io/python-autopxd2/).

## Docker

A Docker image with libclang pre-installed is available:

```shell
docker run --rm -v $(pwd):/work -w /work ghcr.io/elijahr/python-autopxd2 autopxd myheader.h
```

See [Docker Usage](https://elijahr.github.io/python-autopxd2/dev/getting-started/docker/) for more examples.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT License. See [LICENSE](LICENSE) for details.

## Acknowledgments

This project is a fork of [python-autopxd](https://github.com/tarruda/python-autopxd) by Thiago de Arruda.
