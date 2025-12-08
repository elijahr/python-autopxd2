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

```bash
autopxd -I /usr/include -I ./include myheader.h
```

### `-D, --compiler-directive <directive>`

Pass a directive to the C preprocessor. Can be specified multiple times.

```bash
autopxd -D DEBUG -D VERSION=2 myheader.h
```

### `-R, --regex <pattern>`

Apply a sed-style search/replace pattern after preprocessing. Useful for fixing problematic constructs.

```bash
autopxd -R 's/__attribute__.*//g' myheader.h
```

### `-w, --whitelist <file>`

Only generate declarations from specified files. Can be specified multiple times.

```bash
autopxd -w main.h -w types.h combined.h
```

### `--clang-arg <arg>`

Pass an argument directly to libclang. Can be specified multiple times.

```bash
autopxd --clang-arg -DFOO --clang-arg -I/custom/include myheader.h
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
docker run --rm -v $(pwd):/work ghcr.io/elijahr/autopxd2 myheader.h myheader.pxd
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
