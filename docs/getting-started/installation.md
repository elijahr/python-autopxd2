# Installation

## Recommended Installation

Install autopxd2:

```bash
pip install autopxd2
```

autopxd2 uses `headerkit`, which vendors LLVM clang Python bindings for LLVM 18–21 directly. There is no need to install a separate `clang2` or `clang` Python package.

You only need the system `libclang` shared library (`libclang.so`, `libclang.dylib`, or `libclang.dll`).

### Automatic libclang Installation

HeaderKit provides a built-in installer to automatically download and set up `libclang` for your platform:

```bash
python -m headerkit.install_libclang
```

## System Package Managers

Alternatively, you can install LLVM / libclang using your system's package manager:

### macOS

```bash
brew install llvm
```

### Ubuntu / Debian

```bash
sudo apt-get install libclang-dev llvm
```

### Fedora / RHEL

```bash
sudo dnf install clang-devel llvm
```

### Windows

1. Install LLVM from [releases.llvm.org](https://releases.llvm.org/) or via `winget install LLVM.LLVM`
2. Ensure the LLVM `bin` directory is in your `PATH`

## Development Installation

For development, clone the repository and install with development dependencies:

```bash
git clone https://github.com/elijahr/python-autopxd2.git
cd python-autopxd2
pip install -e .[dev]
```

## Docker (No Installation Required)

Use the Docker image for pre-configured libclang support without installing anything on your host system:

```bash
docker run --rm -v $(pwd):/work -w /work ghcr.io/elijahr/python-autopxd2 autopxd myheader.h
```

See [Docker Usage](docker.md) for more details.

## Verifying Installation

Check that autopxd2 can find libclang:

```bash
autopxd --list-backends
```

If libclang is installed correctly, you will see:

```
Available backends:
  libclang     Full C/C++ support via LLVM [available] (default)

Default: libclang
```
