# Installation

## Recommended Installation

Install autopxd2:

```bash
pip install autopxd2
```

autopxd2 uses `headerkit`, which vendors LLVM clang Python bindings for LLVM 18–23 directly. There is no need to install a separate `clang2` or `clang` Python package.

You only need the system `libclang` shared library (`libclang.so`, `libclang.dylib`, or `libclang.dll`).

### Automatic libclang Installation

HeaderKit provides a built-in installer to automatically download and set up `libclang` for your platform:

```bash
python -m headerkit.install_libclang
```

## Without LLVM: the tree-sitter Backend

If you cannot install a system `libclang`, install the `treesitter` extra instead:

```bash
pip install "autopxd2[treesitter]"
```

Then pass `--backend tree-sitter`:

```bash
autopxd --backend tree-sitter myheader.h myheader.pxd
```

This backend parses only the file you give it: it does not follow `#include`
directives, does not extract `#define` macros, does not detect system include
paths, and rejects `--std` and `--clang-arg`. See [Parser Backends](../user-guide/backends.md).

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

### Alpine Linux / musl

```bash
apk add clang-dev
```

### Fedora / RHEL

```bash
sudo dnf install clang-devel llvm
```

### Windows

1. Install LLVM from [releases.llvm.org](https://releases.llvm.org/) or via `winget install LLVM.LLVM`
2. Ensure the LLVM `bin` directory is in your `PATH`

## Headless CI & Build Containers (cibuildwheel, Docker)

In minimal Docker containers or CI build environments (such as Alpine/`musllinux`, `manylinux`, or slim Debian images) where `libclang` is not present, you can:

1. **Install `libclang` in the container:**
   - **Alpine / musllinux**: `apk add clang-dev`
   - **Debian / Ubuntu**: `apt-get install -y libclang-dev`
   - **RHEL / manylinux**: `dnf install -y clang-devel`

   *(For example, in `cibuildwheel` config in `pyproject.toml`:)*
   ```toml
   [[tool.cibuildwheel.overrides]]
   select = ["*-musllinux_*"]
   before-all = "apk add clang-dev"
   ```

2. **Or use the Tree-sitter backend (no system packages required):**
   Declare `autopxd2[treesitter]` in your build dependencies:
   ```toml
   [build-system]
   requires = ["meson-python", "autopxd2[treesitter]"]
   ```
   and pass `--backend tree-sitter` in your build script (e.g. `meson.build`).

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
  tree-sitter  Fast C/C++ parsing without system LLVM dependencies [available]

Default: libclang
```

The `tree-sitter` line appears once the `treesitter` extra is installed; it is listed
as unavailable otherwise.
