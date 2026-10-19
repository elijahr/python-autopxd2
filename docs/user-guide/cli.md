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

Select the parser backend. Options: `auto` (default), `libclang`, `tree-sitter`.

- `auto`: Use the default backend (libclang) when it is available, otherwise the
  first available backend
- `libclang`: Full C/C++ support via LLVM
- `tree-sitter`: Fast C/C++ parsing without system LLVM dependencies
  (requires `pip install "autopxd2[treesitter]"`)

```bash
autopxd --backend libclang myheader.hpp
autopxd --backend tree-sitter myheader.hpp
```

See [Parser Backends](backends.md) for the differences between them.

### `--list-backends`

Show available backends and exit.

```bash
autopxd --list-backends
```

```console
$ autopxd --list-backends
Available backends:
  libclang     Full C/C++ support via LLVM [available] (default)
  tree-sitter  Fast C/C++ parsing without system LLVM dependencies [available]

Default: libclang
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

### `--allowlist <pattern>`

Only generate declarations from files matching the pattern. Can be specified multiple times.

A pattern with no path separator is matched against each file's basename, so `types.h` and `*.h` work wherever the file lives. A pattern with a separator is matched against the full path; a relative one is resolved against the input header's own directory, then each `-I` directory, then the working directory. Glob metacharacters (`*`, `?`, `[`) are supported.

The allowlist applies to the input header itself as well as to everything it includes, so an allowlist that does not name the input header drops that header's declarations too.

```bash
autopxd --allowlist main.h --allowlist types.h combined.h
autopxd --allowlist 'include/*.h' combined.h
```

### `--denylist <pattern>`

Never generate declarations from files matching the pattern. Can be specified multiple times. Same pattern syntax as `--allowlist`.

**Deny wins over allow.** A file matching both lists is excluded. This makes "everything under `include/`, except the private headers" expressible directly:

```bash
autopxd --allowlist 'include/*.h' --denylist 'include/*_internal.h' combined.h
```

`--denylist` deliberately has no short flag, so `-w` stays unambiguous while `--whitelist` is being retired.

### `-w, --whitelist <pattern>` (deprecated)

Deprecated alias for `--allowlist`, retained with its `-w` short flag. It still works and behaves identically, but emits a `DeprecationWarning` naming `--allowlist` as the replacement. Use `-q` / `--quiet` to silence that warning.

Passing both `--allowlist` and `--whitelist` is an error rather than a silent precedence guess.

### Which headers contribute declarations

With recursion on — the default — declarations from **every non-system included header** are emitted, not just those of the input header. `--no-recursive` confines the output to the input header's own declarations.

An allowlist narrows that set in **both** recursion modes. Combined:

| Options | Declarations emitted |
| --- | --- |
| *(default)* | The input header, plus every non-system header it includes |
| `--no-recursive` | The input header only |
| `--allowlist P` | Of the above set, only files matching `P` |
| `--denylist P` | Of the above set, minus files matching `P` |
| `--allowlist P --denylist Q` | Files matching `P` and not matching `Q` |

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

### `-P, --project-prefix <path>` [libclang]

Treat headers under the specified path as project headers rather than system headers. This is essential for umbrella headers—headers that include many sub-headers but have few declarations of their own (like `sodium.h`, `openssl/ssl.h`).

Without this option, declarations from sub-headers in system locations (e.g., `/usr/include`, `/opt/homebrew/include`) are filtered out. The `--project-prefix` option marks paths as project headers so their declarations are included.

Can be specified multiple times for multiple prefixes.

```bash
# Include declarations from all sodium/*.h sub-headers
autopxd -I /opt/homebrew/include \
    --project-prefix /opt/homebrew/include/sodium \
    /opt/homebrew/include/sodium.h

# Multiple prefixes
autopxd -I /usr/include \
    -P /usr/include/openssl \
    -P /usr/include/crypto \
    /usr/include/openssl/ssl.h
```

### `--no-recursive` [libclang]

Confine the output to the input header's own declarations. By default autopxd parses every non-system header the input includes and emits their declarations too.

Recursion is controlled by this flag alone. There is no include-count or declaration-count heuristic: a header with a single include is expanded exactly like one with fifty. To keep recursion on but restrict which of the reached headers contribute, use `--allowlist` or `--denylist` instead.

```bash
autopxd --no-recursive -P /opt/homebrew/include/sodium \
    /opt/homebrew/include/sodium.h
```

### `--max-depth <n>` [libclang]

Limit recursion depth for umbrella header processing (default: 10). `0` disables umbrella expansion entirely, equivalent to `--no-recursive`.

Values of `1` or greater currently all behave the same: each included header is parsed as its own translation unit, so the compiler has already flattened that header's own includes before the recursion descends a level. Circular includes are prevented by tracking visited files, not by this limit.

Only the libclang backend follows `#include` directives. Passing this option to another backend emits a warning, since it cannot be honored.

```bash
autopxd --max-depth 0 -P /opt/homebrew/include/sodium \
    /opt/homebrew/include/sodium.h
```

### `-q, --quiet`

Suppress warnings.

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

### Working with umbrella headers

Umbrella headers like `sodium.h` include many sub-headers but define few declarations themselves. Use `--project-prefix` to include declarations from sub-headers:

```bash
# Generate bindings for libsodium (installed via homebrew)
autopxd -I /opt/homebrew/include \
    -P /opt/homebrew/include/sodium \
    /opt/homebrew/include/sodium.h sodium.pxd

# Generate bindings for OpenSSL
autopxd -I /usr/include \
    -P /usr/include/openssl \
    /usr/include/openssl/ssl.h ssl.pxd
```

### Check available backends

```bash
autopxd --list-backends
```

## Troubleshooting

### libclang not available

If you see "libclang backend not available", install libclang:

**Using headerkit:**
```bash
python -m headerkit.install_libclang
```

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

### Empty output from umbrella headers

If you're parsing an umbrella header (like `sodium.h`) and getting empty or minimal output, the sub-headers are probably in a system location. Use `--project-prefix` to mark them as project headers:

```bash
# Find where the library headers are installed
pkg-config --cflags libsodium
# Output: -I/opt/homebrew/include

# Use --project-prefix with the sub-header directory
autopxd -I /opt/homebrew/include \
    -P /opt/homebrew/include/sodium \
    /opt/homebrew/include/sodium.h
```

You can verify the prefix is working by using `--debug` to see which declarations are being found.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Parse error or invalid input |
| 2 | Invalid command-line arguments |
