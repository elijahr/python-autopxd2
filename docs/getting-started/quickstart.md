# Quick Start

This guide will get you generating Cython `.pxd` files in under 5 minutes.

## Basic Usage

Given a C header file `example.h`:

```c
// example.h
typedef struct {
    int x;
    int y;
} Point;

Point create_point(int x, int y);
double distance(Point a, Point b);
```

Generate a `.pxd` file:

```bash
autopxd example.h > example.pxd
```

This produces:

```cython
cdef extern from "example.h":

    cdef struct Point:
        int x
        int y

    Point create_point(int x, int y)

    double distance(Point a, Point b)
```

## Include Directories

The libclang backend automatically detects system include paths, so standard headers like `<stddef.h>` and `<stdint.h>` work out of the box.

For project-specific includes, use `-I`:

```bash
autopxd -I ./include -I ./third_party myheader.h
```

To disable automatic system include detection (e.g., for cross-compilation), use `--no-default-includes`:

```bash
autopxd --no-default-includes -I /custom/sysroot/include myheader.h
```

## Choosing a Backend

autopxd2 supports two parser backends:

| Backend | Best For | Requirements |
|---------|----------|--------------|
| pycparser | Simple C headers | None (pure Python) |
| libclang | C++ headers, complex macros | libclang installed |

Use the `--backend` option:

```bash
# Use pycparser (default)
autopxd --backend pycparser myheader.h

# Use libclang for C++ support
autopxd --backend libclang myheader.hpp
```

## Using with Cython

After generating the `.pxd` file, use it in your Cython code:

```cython
# mymodule.pyx
from example cimport Point, create_point, distance

def make_point(x: int, y: int) -> tuple:
    cdef Point p = create_point(x, y)
    return (p.x, p.y)

def calc_distance(p1: tuple, p2: tuple) -> float:
    cdef Point a, b
    a.x, a.y = p1
    b.x, b.y = p2
    return distance(a, b)
```

## Python API

You can also use autopxd2 programmatically:

```python
from autopxd.backends import get_backend
from autopxd.ir_writer import write_pxd

# Parse a header file
backend = get_backend("pycparser")  # or "libclang"
with open("example.h") as f:
    code = f.read()

header = backend.parse(code, "example.h")

# Generate pxd content
pxd = write_pxd(header)
print(pxd)
```

## Next Steps

- [Parser Backends](../user-guide/backends.md) - Learn about backend differences
- [C++ Support](../user-guide/cpp.md) - Working with C++ headers
- [Docker Usage](docker.md) - Use Docker for libclang without local installation
