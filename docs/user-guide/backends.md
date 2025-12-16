# Parser Backends

autopxd2 supports two parser backends. **libclang is strongly recommended** for all use cases.

## Available Backends

### libclang (Recommended)

Uses LLVM's clang library for parsing. Provides the same parser used by production compilers.

**Pros:**

- Full C++ support (classes, templates, namespaces)
- Extracts macros as constants (integers, floats, strings, expressions)
- Automatic system include path detection
- Handles comments and preprocessor directives directly
- Better error messages
- Handles complex headers reliably

**Cons:**

- Requires libclang to be installed
- Python `clang2` package version must match system libclang (these are official LLVM bindings)
- Slightly slower startup time
- Function-like macros are not extracted

**Usage:**

```bash
autopxd --backend libclang myheader.h

# For C++ headers
autopxd --backend libclang myheader.hpp
```

## System Include Paths

The libclang backend automatically detects system include directories by querying the system clang compiler. This means headers like `<stddef.h>` and `<stdint.h>` work without requiring manual `-I` flags.

```bash
# This works automatically - system includes are detected
autopxd myheader.h
```

To disable automatic include detection:

```bash
autopxd --no-default-includes myheader.h
```

You can still add additional include directories:

```bash
autopxd -I /my/project/include myheader.h
```

### pycparser (Legacy)

A pure Python C99 parser. Falls back to this if libclang is not available.

!!! warning "Legacy Backend"
    pycparser is maintained for backwards compatibility but is **not recommended**.
    It lacks C++ support, macro extraction, and circular dependency handling.

**Cons:**

- C99 only (no C++ support)
- No macro extraction
- No circular dependency handling
- Requires preprocessed code
- May struggle with complex headers

**Usage:**

```bash
autopxd --backend pycparser myheader.h
```

## Choosing a Backend

**Use libclang for everything.** The only reason to use pycparser is if you cannot install LLVM on your system.

| Use Case | Recommended Backend |
|----------|---------------------|
| C headers | libclang |
| C++ headers | libclang |
| Headers with macros | libclang |
| Complex library headers | libclang |
| Cannot install LLVM | pycparser (fallback) |

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

## C++ Template Support (libclang only)

The libclang backend supports C++ templates, including primary templates and full specializations.

### Primary Templates

C++ class templates with type parameters are translated to Cython's template syntax:

```cpp
template<typename T>
class Container {
public:
    T value;
    T get();
    void set(T v);
};
```

Generates:

```cython
cdef cppclass Container[T]:
    T value
    T get()
    void set(T v)
```

Multiple type parameters are supported:

```cpp
template<typename K, typename V>
class Map {
public:
    V lookup(K key);
    void insert(K key, V value);
};
```

Generates:

```cython
cdef cppclass Map[K, V]:
    V lookup(K key)
    void insert(K key, V value)
```

### Template Specializations

Full template specializations are emitted with mangled Python-safe names and the original C++ name as a string literal:

```cpp
template<>
class Container<int> {
public:
    int special_value;
    int get_special();
};
```

Generates:

```cython
cdef cppclass Container_int "Container<int>":
    int special_value
    int get_special()
```

The mangling scheme converts special characters to valid Python identifiers:
- `<` and `>` are removed, contents become underscore-separated
- `*` becomes `_ptr`
- `&` becomes `_ref`
- `::` becomes `_`

Examples:
- `Container<int>` → `Container_int`
- `Map<int, double>` → `Map_int_double`
- `Foo<int*>` → `Foo_int_ptr`

## Using Docker for libclang

If you don't want to install libclang locally, use the Docker image:

```bash
docker run --rm -v $(pwd):/work -w /work ghcr.io/elijahr/python-autopxd2 autopxd myheader.h
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
