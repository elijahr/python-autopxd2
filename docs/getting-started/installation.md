# Installation

## Basic Installation

Install autopxd2 from PyPI:

```bash
pip install autopxd2
```

This installs the core package with the pycparser backend, which works for most C headers.

## With libclang Support

For better C++ support and handling of complex headers, install with the libclang extra:

```bash
pip install autopxd2[libclang]
```

!!! note "System Requirements"
    The libclang extra requires libclang to be installed on your system. See [libclang Installation](#libclang-installation) below.

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

## libclang Installation

### macOS

```bash
# Install via Homebrew
brew install llvm

# The clang Python package should find libclang automatically
pip install clang
```

### Ubuntu/Debian

```bash
# Install clang and libclang
sudo apt-get install clang libclang-dev

# Install Python bindings
pip install clang
```

### Windows

1. Install LLVM from [releases.llvm.org](https://releases.llvm.org/)
2. Add LLVM to your PATH
3. Install the Python bindings:
   ```bash
   pip install clang
   ```

### Verifying Installation

Check that autopxd2 can find libclang:

```bash
python -c "from autopxd.backends import list_backends; print(list_backends())"
```

If libclang is installed correctly, you should see both `pycparser` and `libclang` in the output.
