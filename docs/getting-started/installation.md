# Installation

## Basic Installation

Install autopxd2 from PyPI:

```bash
pip install autopxd2
```

This installs the package with both the pycparser and libclang Python bindings. However, the libclang backend requires the system libclang library to be installed for full functionality.

!!! note "Backend Selection"
    By default, autopxd2 uses libclang if available, falling back to pycparser.
    Use `autopxd --list-backends` to see which backends are available on your system.

## Development Installation

For development, clone the repository and install with development dependencies:

```bash
git clone https://github.com/elijahr/python-autopxd2.git
cd python-autopxd2
pip install -e .[dev]
```

## Docker (No Installation Required)

Use the Docker image for libclang support without installing anything locally:

```bash
docker build -t autopxd2 https://github.com/elijahr/python-autopxd2.git
docker run --rm -v $(pwd):/work autopxd2 autopxd /work/myheader.h
```

See [Docker Usage](docker.md) for more details.

## System libclang Installation

The libclang Python bindings are included with autopxd2, but the system libclang library must be installed separately.

### macOS

```bash
brew install llvm
```

### Ubuntu/Debian

```bash
sudo apt-get install libclang-dev
```

### Windows

1. Install LLVM from [releases.llvm.org](https://releases.llvm.org/)
2. Add LLVM to your PATH

### Verifying Installation

Check that autopxd2 can find libclang:

```bash
autopxd --list-backends
```

If libclang is installed correctly, you should see:

```
Available backends:
  libclang     Full C/C++ support via LLVM [available] (default)
  pycparser    Legacy C99 parser [available]

Default: libclang
```
