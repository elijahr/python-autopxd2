# autopxd2

**Automatically generate Cython pxd files from C/C++ headers.**

autopxd2 parses C/C++ header files and generates Cython `.pxd` declaration files, enabling you to call C code from Python with minimal manual effort.

## Features

- **Full C/C++ support** - Structs, enums, typedefs, functions, classes, templates, namespaces
- **Macro extraction** - `#define` constants as typed declarations
- **Automatic imports** - Generates `cimport` statements for standard library types
- **Docker support** - Generate headers without installing LLVM locally

## Quick Example

```bash
# Generate pxd from a C/C++ header
autopxd myheader.h > myheader.pxd

# Or use Docker without local LLVM installation
docker run --rm -v $(pwd):/work -w /work ghcr.io/elijahr/python-autopxd2 autopxd myheader.h
```

## Installation

```bash
pip install autopxd2
```

autopxd2 uses `headerkit`, which vendors LLVM clang bindings directly, requiring only the system `libclang` shared library. You can install system `libclang` via your system package manager or with:

```bash
python -m headerkit.install_libclang
```

See [Installation Guide](getting-started/installation.md) for platform-specific LLVM setup.

## Next Steps

- [Installation Guide](getting-started/installation.md) - Detailed installation options
- [Quick Start](getting-started/quickstart.md) - Get started in 5 minutes
- [Docker Usage](getting-started/docker.md) - Use Docker for libclang support
- [Parser Backends](user-guide/backends.md) - Choose the right backend
