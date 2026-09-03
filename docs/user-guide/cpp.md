# C++ Support

autopxd2 supports C++ headers through the libclang backend.

!!! important
    C++ support requires the libclang backend, which is the only backend in autopxd2.

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

### Classes & Structs

C++ classes and structs are converted to Cython `cppclass` definitions with support for multiple inheritance, constructors, destructors, `@staticmethod`, and `const` member methods:

```cpp
// widget.hpp
class Widget : public BaseWidget {
public:
    int width;
    int height;
    Widget();
    Widget(int w, int h);
    virtual ~Widget();
    int area() const;
    static Widget create();
};
```

Generates:

```cython
cdef extern from "widget.hpp":

    cdef cppclass Widget(BaseWidget):
        int width
        int height
        Widget()
        Widget(int w, int h)
        int area() const
        @staticmethod
        Widget create()
```

### Generic Function & Method Templates

Generic C++ function and method templates are fully supported using Cython template brackets syntax:

```cpp
template<typename T>
T max_val(T a, T b);
```

Generates:

```cython
T max_val[T](T a, T b)
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

### Overloading

Multiple overloaded free functions with identical names may produce conflicts in C mode. In C++ mode (`--cpp`), Cython natively supports function overloading.

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
