# CLI Reference

The `autopxd` command-line tool generates Cython `.pxd` files from C/C++ headers.

## Basic Usage

```bash
autopxd [OPTIONS] [INFILE] [OUTFILE]
```

## Options

### `-v, --version`

Print program version and exit.

```bash
autopxd --version
```

### `-b, --backend <name>`

Select the parser backend. Options: `auto` (default), `libclang`, `pycparser`.

- `auto`: Use libclang if available, fall back to pycparser
- `libclang`: Full C/C++ support via LLVM
- `pycparser`: Legacy C99 parser (no C++ support)

```bash
autopxd --backend libclang myheader.hpp
autopxd -b pycparser myheader.h
```

### `--list-backends`

Show available backends and exit.

```bash
autopxd --list-backends
```

### `--json`

Output in JSON format (for use with `--list-backends`).

```bash
autopxd --list-backends --json
```

### `-x, --cpp`

Parse as C++ (requires libclang backend).

```bash
autopxd --cpp myclass.hpp
```

### `--std <standard>`

Specify the language standard (requires libclang backend).

```bash
autopxd --std c11 myheader.h
autopxd --std c++17 myclass.hpp
```

### `-I, --include-dir <dir>`

Add a directory to the include search path. Can be specified multiple times.

**Note:** The libclang backend automatically detects system include paths (e.g., `/usr/include`), so you typically only need `-I` for project-specific directories.

```bash
autopxd -I ./include -I ./third_party myheader.h
```

### `-D, --define <macro>`

Define a preprocessor macro. Can be specified multiple times.

```bash
autopxd -D DEBUG -D VERSION=2 myheader.h
```

### `-w, --whitelist <file>`

Only generate declarations from specified files. Can be specified multiple times.

```bash
autopxd -w main.h -w types.h combined.h
```

### `--clang-arg <arg>` [libclang]

Pass an argument directly to libclang. Can be specified multiple times.

```bash
autopxd --clang-arg -DFOO --clang-arg -I/custom/include myheader.h
```

### `--no-default-includes` [libclang]

Disable automatic detection of system include directories. By default, the libclang backend queries the system clang compiler to find standard include paths. Use this option if you need full control over include paths.

```bash
# Disable auto-detection and specify all paths manually
autopxd --no-default-includes -I /my/custom/sysroot/include myheader.h
```

### `-q, --quiet`

Suppress warnings (e.g., backend fallback warnings).

```bash
autopxd -q myheader.h
```

### `--debug / --no-debug`

Dump preprocessor output to stderr for debugging.

```bash
autopxd --debug myheader.h 2>preprocessed.txt
```

### `-h, --help`

Show help message and exit.

```bash
autopxd --help
```

## Examples

### Generate pxd from a header

```bash
autopxd myheader.h myheader.pxd
```

### With include directories

```bash
autopxd -I /opt/local/include -I ./third_party mylib.h mylib.pxd
```

### Using libclang for C++

```bash
autopxd --backend libclang --cpp myclass.hpp myclass.pxd
```

### Using C++17 standard

```bash
autopxd -x --std c++17 modern.hpp modern.pxd
```

### Fix problematic macros

```bash
autopxd -R 's/__restrict//g' -R 's/__extension__//g' header.h header.pxd
```

### Check available backends

```bash
autopxd --list-backends
```

## Troubleshooting

### libclang not available

If you see "libclang not available, falling back to pycparser", install the system libclang library:

**Ubuntu/Debian:**
```bash
apt install libclang-dev
```

**macOS:**
```bash
brew install llvm
```

**Or use Docker:**
```bash
docker run --rm -v $(pwd):/work -w /work ghcr.io/elijahr/python-autopxd2 autopxd myheader.h
```

### C++ parsing fails

Make sure you're using the libclang backend:

```bash
autopxd --backend libclang --cpp myheader.hpp
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Parse error or invalid input |
| 2 | Invalid command-line arguments |
