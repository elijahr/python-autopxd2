# Parser Backends

autopxd2 supports multiple parser backends for converting C/C++ headers to Cython declarations.

## Available Backends

### pycparser (Default)

A pure Python C99 parser. Works out of the box with no external dependencies.

**Pros:**

- No external dependencies
- Works on all platforms
- Fast for simple headers

**Cons:**

- C99 only (no C++ support)
- Requires preprocessed code (no comments or macros in input)
- May struggle with complex headers

**Usage:**

```bash
autopxd --backend pycparser myheader.h
```

### libclang

Uses LLVM's clang library for parsing. Provides the same parser used by actual compilers.

**Pros:**

- Full C++ support
- Handles comments and preprocessor directives directly
- Better error messages
- Handles complex headers reliably

**Cons:**

- Requires libclang to be installed
- Python `clang` package version must match system libclang (these are official LLVM bindings)
- Slightly slower startup time

**Usage:**

```bash
autopxd --backend libclang myheader.h

# For C++ headers
autopxd --backend libclang myheader.hpp
```

## Choosing a Backend

| Use Case | Recommended Backend |
|----------|---------------------|
| Simple C headers | pycparser |
| C++ headers | libclang |
| Headers with complex macros | libclang |
| Cross-platform without dependencies | pycparser |
| Production use with complex libraries | libclang |

## Backend Comparison

Both backends produce equivalent output for standard C constructs:

```c
// input.h
struct Point {
    int x;
    int y;
};

int distance(struct Point a, struct Point b);
```

Both backends produce:

```cython
cdef extern from "input.h":

    cdef struct Point:
        int x
        int y

    int distance(Point a, Point b)
```

## Using Docker for libclang

If you don't want to install libclang locally, use the Docker image:

```bash
docker run --rm -v $(pwd):/work autopxd2 autopxd --backend libclang /work/myheader.h
```

See [Docker Usage](../getting-started/docker.md) for details.

## Programmatic Backend Selection

```python
from autopxd.backends import get_backend, list_backends

# List available backends
print(list_backends())  # ['pycparser', 'libclang'] (if libclang installed)

# Get a specific backend
backend = get_backend("libclang")

# Parse a header
header = backend.parse(code, "myheader.h")
```
