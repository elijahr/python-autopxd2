# CLI Reference

The `autopxd` command-line tool generates Cython `.pxd` files from C/C++ headers.

## Basic Usage

```bash
autopxd [OPTIONS] INFILE
```

## Options

### `-I, --include <dir>`

Add a directory to the include search path. Can be specified multiple times.

```bash
autopxd -I /usr/include -I ./include myheader.h
```

### `-R, --regex <pattern>`

Apply a sed-style search/replace pattern after preprocessing. Useful for fixing problematic constructs.

```bash
autopxd -R 's/__attribute__.*//g' myheader.h
```

### `--backend <name>`

Select the parser backend. Options: `pycparser` (default), `libclang`.

```bash
autopxd --backend libclang myheader.hpp
```

### `--compiler-directive <directive>`

Add a Cython compiler directive to the output.

```bash
autopxd --compiler-directive "language_level=3" myheader.h
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
autopxd myheader.h > myheader.pxd
```

### With include directories

```bash
autopxd -I /opt/local/include -I ./third_party mylib.h > mylib.pxd
```

### Using libclang for C++

```bash
autopxd --backend libclang myclass.hpp > myclass.pxd
```

### Fix problematic macros

```bash
autopxd -R 's/__restrict//g' -R 's/__extension__//g' header.h > header.pxd
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Parse error or invalid input |
| 2 | Invalid command-line arguments |
