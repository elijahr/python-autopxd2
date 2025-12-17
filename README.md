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

- Generates complete `.pxd` files from C/C++ headers
- Full C++ support with libclang backend
- Automatic system include path detection
- Auto-generates `cimport` statements for standard library types
- Cross-platform support (Linux, macOS, Windows)

## Supported Features

### C Features

| Feature | libclang | pycparser (legacy) |
|---------|:--------:|:------------------:|
| Structs and unions | ✓ | ✓ |
| Enums (with expressions) | ✓ | ✓ |
| Typedefs | ✓ | ✓ |
| Function declarations | ✓ | ✓ |
| Function pointers | ✓ | ✓ |
| Arrays (fixed and flexible) | ✓ | ✓ |
| Pointers and const qualifiers | ✓ | ✓ |
| Forward declarations | ✓ | ✓ |
| Anonymous structs/unions | ✓ | ✓ |
| Bit fields | ✓ | ✓ |
| `#define` macros (int, float, string) | ✓ | |
| Circular type dependencies | ✓ | |

### C++ Features (libclang only)

| Feature | Supported |
|---------|:---------:|
| Classes with fields and methods | ✓ |
| Namespaces (including nested) | ✓ |
| Templates with type parameters | ✓ |
| Template specializations | ✓ |
| Operator overloading (renamed for Cython) | ✓ |
| References and const references | ✓ |
| Inheritance declarations | ✓ |
| Static methods and fields | ✓ |

## Installation

```shell
pip install autopxd2
```

**Recommended:** Install the libclang backend for full C/C++ support. The `clang2` package version must match your system's LLVM version:

```shell
# One-liner: detect LLVM version and install matching clang2
pip install "clang2==$(llvm-config --version | cut -d. -f1).*"

# Or check version manually first
llvm-config --version  # e.g., 18.1.3 means you need clang2==18.*
pip install "clang2==18.*"
```

Without `clang2`, autopxd2 falls back to the legacy pycparser backend (C99 only, no macros, no circular dependency handling). If clang2 is missing, autopxd2 will detect your LLVM version and show the exact install command.

See the [installation docs](https://elijahr.github.io/python-autopxd2/dev/getting-started/installation/) for platform-specific LLVM setup (macOS with Homebrew, Ubuntu/Debian, Windows).

## Quick Start

```shell
# Generate a .pxd file from a C header
autopxd myheader.h myheader.pxd

# Add project-specific include directories (system includes are auto-detected)
autopxd -I ./include myheader.h myheader.pxd

# Write to stdout (omit output file)
autopxd myheader.h > myheader.pxd
```

## Usage

```
autopxd [OPTIONS] INFILE [OUTFILE]

Options marked [libclang] require the libclang backend.

Options:
  -v, --version              Print version and exit.
  -b, --backend <name>       Parser backend (default: auto, prefers libclang).
  --list-backends            List available backends and exit.
  -q, --quiet                Suppress warnings.
  --debug / --no-debug       Print debug info to stderr.
  -I, --include-dir <dir>    Add include search path.
  -D, --define <macro>       Define preprocessor macro.
  -w, --whitelist <pattern>  Only emit from files matching pattern.
  -x, --cpp                  [libclang] Parse as C++.
  --std <std>                [libclang] Language standard (e.g., c11, c++17).
  --clang-arg <arg>          [libclang] Pass argument to clang.
  --no-default-includes      [libclang] Disable system include auto-detection.
  -p, --project-prefix       [libclang] Whitelist paths for umbrella headers.
  --no-recursive             [libclang] Disable recursive include parsing.
  --max-depth <n>            [libclang] Max depth for recursive includes.
  -h, --help                 Show this message and exit.
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
from autopxd.stubs.stdarg cimport va_list

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

**Note:** Auto-import requires the libclang backend for header detection. The pycparser backend does not track included headers.

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
