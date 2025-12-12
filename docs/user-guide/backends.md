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

- Full C++ support (classes, templates, namespaces)
- Extracts simple numeric macros as constants
- Handles comments and preprocessor directives directly
- Better error messages
- Handles complex headers reliably

**Cons:**

- Requires libclang to be installed
- Python `clang2` package version must match system libclang (these are official LLVM bindings)
- Slightly slower startup time
- Complex macros (expressions, function-like) are not extracted

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

## Macro Extraction (libclang only)

The libclang backend extracts `#define` macros as Cython constant declarations. The type is automatically detected from the macro value.

### Integer Macros

```c
#define SIZE 100
#define MASK 0xFF
#define MODE 0755
#define FLAGS 0b1010
#define BIG_NUM 100ULL
```

Generates `int` declarations:

```cython
    int SIZE
    int MASK
    int MODE
    int FLAGS
    int BIG_NUM
```

Supported formats: decimal, hex (`0x`), octal (`0`), binary (`0b`), with optional type suffixes (`U`, `L`, `UL`, `LL`, `ULL`).

### Floating-Point Macros

```c
#define PI 3.14159
#define EPSILON 1e-10
#define FACTOR 2.5f
```

Generates `double` declarations:

```cython
    double PI
    double EPSILON
    double FACTOR
```

### String Macros

```c
#define VERSION "1.0.0"
#define APP_NAME "myapp"
```

Generates `const char*` declarations:

```cython
    const char* VERSION
    const char* APP_NAME
```

### Expression Macros

```c
#define A 10
#define B 20
#define TOTAL (A + B)
#define FLAGS (0x01 | 0x02)
#define NEGATIVE -1
```

Expression macros that consist of numeric literals, operators, and other macro references are detected and declared with appropriate types:

```cython
    int A
    int B
    int TOTAL
    int FLAGS
    int NEGATIVE
```

### Unsupported Macros (silently ignored)

- **Function-like macros:** `#define MAX(a, b) ((a) > (b) ? (a) : (b))`
- **Empty macros:** `#define EMPTY`
- **String concatenation:** `#define CONCAT "hello" "world"`

The pycparser backend does not extract macros since it requires preprocessed input.

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
