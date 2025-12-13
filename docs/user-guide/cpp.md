# C++ Support

autopxd2 supports C++ headers through the libclang backend.

!!! important
    C++ support requires the libclang backend. The default pycparser backend only supports C99.

## Basic C++ Usage

```bash
# Use libclang for C++ headers
autopxd --backend libclang myclass.hpp > myclass.pxd
```

Or with Docker:

```bash
docker run --rm -v $(pwd):/work -w /work ghcr.io/elijahr/python-autopxd2 autopxd myclass.hpp
```

## Supported C++ Features

### Classes

C++ classes are converted to Cython structs:

```cpp
// widget.hpp
class Widget {
public:
    int width;
    int height;
};
```

Generates:

```cython
cdef extern from "widget.hpp":

    cdef struct Widget:
        int width
        int height
```

### Structs

C++ structs work the same as C:

```cpp
struct Point {
    double x;
    double y;
};
```

### Functions

Global functions are converted directly:

```cpp
double distance(const Point& a, const Point& b);
```

Generates:

```cython
double distance(const Point & a, const Point & b)
```

### Namespaces

Currently, only top-level declarations are extracted. Namespaced declarations are not directly supported.

## Limitations

### Methods

Class methods are not included in the generated `.pxd`. Only public data members are extracted.

For full method support, you'll need to manually add method declarations or use Cython's `cppclass` syntax.

### Templates

Template classes are supported through the libclang backend, including primary templates
and full specializations. See [C++ Template Support](backends.md#c-template-support-libclang-only)
for details.

### Overloading

Multiple overloaded functions with the same name may produce conflicts. You may need to manually select which overload to use.

## Best Practices

1. **Use header-only libraries** where possible for simpler integration
2. **Start with the Docker image** to avoid libclang installation issues
3. **Check generated output** and manually adjust for complex C++ features
4. **Consider Cython's cppclass** for classes with methods you need to call

## Example Workflow

1. Generate initial pxd:
   ```bash
   autopxd --backend libclang mylib.hpp > mylib.pxd
   ```

2. Review and adjust for methods, templates, or other features

3. Create your Cython wrapper:
   ```cython
   # mylib.pyx
   from mylib cimport Widget

   def create_widget(width: int, height: int):
       cdef Widget w
       w.width = width
       w.height = height
       return (w.width, w.height)
   ```
