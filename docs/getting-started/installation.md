# Installation

## Basic Installation

Install autopxd2 from PyPI:

```bash
pip install autopxd2
```

This installs the package with both parser backends:

- **libclang** - Full C/C++ support via LLVM (default if system libclang available)
- **pycparser** - Pure Python C99 parser (fallback)

!!! note "Automatic Fallback"
    autopxd2 automatically uses libclang if the system library is available,
    falling back to pycparser otherwise. Use `autopxd --list-backends` to see
    which backends are available on your system.

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

The libclang backend requires both:

1. The system libclang library
2. The Python `clang` package (included with autopxd2)

!!! important "Version Matching Required"
    The Python `clang` package provides the official LLVM project bindings and **must match your system's libclang version**. For example, if you have LLVM 18 installed, you need `clang==18.*`.

    ```bash
    # Check your LLVM version
    llvm-config --version  # e.g., 18.1.3

    # Install matching Python package
    pip install "clang==18.*"
    ```

### macOS

```bash
brew install llvm

# Install matching Python clang package
LLVM_VERSION=$($(brew --prefix llvm)/bin/llvm-config --version | cut -d. -f1)
pip install "clang==${LLVM_VERSION}.*"
```

### Ubuntu/Debian

```bash
sudo apt-get install libclang-dev llvm

# Install matching Python clang package
LLVM_VERSION=$(llvm-config --version | cut -d. -f1)
pip install "clang==${LLVM_VERSION}.*"
```

### Windows

1. Install LLVM from [releases.llvm.org](https://releases.llvm.org/)
2. Add LLVM to your PATH
3. Install matching Python clang package: `pip install "clang==<version>.*"`

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
