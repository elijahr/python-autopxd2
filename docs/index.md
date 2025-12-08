# autopxd2

**Automatically generate Cython pxd files from C/C++ headers.**

autopxd2 parses C header files and generates Cython `.pxd` declaration files, enabling you to call C code from Python with minimal manual effort.

## Features

- **Automatic pxd generation** - Convert C headers to Cython declarations
- **Multiple parser backends** - pycparser (pure Python) and libclang (C++ support)
- **Docker support** - Generate headers without installing clang locally
- **CLI and Python API** - Use from command line or integrate into your build

## Quick Example

```bash
# Generate pxd from a C header
autopxd myheader.h > myheader.pxd

# Use libclang backend for C++ support (requires clang)
autopxd --backend libclang myheader.hpp > myheader.pxd

# Or use Docker for libclang without local installation
docker run --rm -v $(pwd):/work autopxd2 autopxd /work/myheader.h
```

## Installation

```bash
pip install autopxd2
```

The libclang backend is used automatically if your system has libclang installed.
See [Installation Guide](getting-started/installation.md) for setting up libclang.

## Next Steps

- [Installation Guide](getting-started/installation.md) - Detailed installation options
- [Quick Start](getting-started/quickstart.md) - Get started in 5 minutes
- [Docker Usage](getting-started/docker.md) - Use Docker for libclang support
- [Parser Backends](user-guide/backends.md) - Choose the right backend
