# Installation

## Basic Installation

Install autopxd2 from PyPI:

```bash
pip install autopxd2
```

This installs the package with the **pycparser** backend (pure Python C99 parser).

For **C++ support**, you also need the libclang backend - see [libclang Installation](#libclang-installation-c-support) below.

!!! note "Backend Selection"
    autopxd2 automatically uses libclang if available, falling back to pycparser
    otherwise. Use `autopxd --list-backends` to see which backends are available.

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
docker run --rm -v $(pwd):/work -w /work ghcr.io/elijahr/python-autopxd2 autopxd myheader.h
```

See [Docker Usage](docker.md) for more details.

## libclang Installation (C++ Support)

The libclang backend requires:

1. The system libclang library (LLVM)
2. The Python `clang2` package matching your LLVM version

!!! important "Version Matching Required"
    The `clang2` Python package **must match your system's LLVM version**.
    For example, LLVM 18 requires `clang2==18.*`.

### Quick Install (One-Liner)

If you have LLVM already installed, use this one-liner to install the matching clang2 package:

=== "pip"

    ```bash
    pip install "clang2==$(llvm-config --version | cut -d. -f1).*"
    ```

=== "uv"

    ```bash
    uv pip install "clang2==$(llvm-config --version | cut -d. -f1).*"
    ```

### macOS

```bash
# Install LLVM (if not already installed)
brew install llvm

# Install matching clang2 package (one-liner)
pip install "clang2==$($(brew --prefix llvm)/bin/llvm-config --version | cut -d. -f1).*"
```

Or with uv:

```bash
uv pip install "clang2==$($(brew --prefix llvm)/bin/llvm-config --version | cut -d. -f1).*"
```

### Ubuntu/Debian

```bash
# Install LLVM (if not already installed)
sudo apt-get install libclang-dev llvm

# Install matching clang2 package (one-liner)
pip install "clang2==$(llvm-config --version | cut -d. -f1).*"
```

Or with uv:

```bash
uv pip install "clang2==$(llvm-config --version | cut -d. -f1).*"
```

### Fedora/RHEL

```bash
# Install LLVM
sudo dnf install clang-devel llvm

# Install matching clang2 package
pip install "clang2==$(llvm-config --version | cut -d. -f1).*"
```

### Windows

1. Install LLVM from [releases.llvm.org](https://releases.llvm.org/)
2. Add LLVM `bin` directory to your PATH
3. Install matching clang2 package:

```powershell
# Check version first
llvm-config --version

# Install matching package (replace XX with major version)
pip install "clang2==XX.*"
```

### Manual Version Check

If the one-liner doesn't work, check your version manually:

```bash
llvm-config --version
# Output: 18.1.3 (means you need clang2==18.*)

pip install "clang2==18.*"
```

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

### Troubleshooting

If you try to use the libclang backend without clang2 installed, autopxd2 will detect your LLVM version and show the exact install command:

```
ValueError: libclang backend requires the clang2 package.
Detected LLVM version 18 on your system.
Install with: pip install 'clang2==18.*'
```
