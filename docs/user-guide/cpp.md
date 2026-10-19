# C++ Support

autopxd2 supports C++ headers through either parser backend.

!!! note
    The libclang backend (the default) and the tree-sitter backend both parse C++.
    See [Parser Backends](backends.md) for the trade-offs.

## Basic C++ Usage

```bash
# C++ mode is auto-detected from .hpp/.hh/.hxx extensions
autopxd --cpp myclass.hpp > myclass.pxd
```

Or with Docker:

```bash
docker run --rm -v $(pwd):/work -w /work ghcr.io/elijahr/python-autopxd2 autopxd myclass.hpp
```

## Supported C++ Features

### Classes & Structs

C++ classes and structs are converted to Cython `cppclass` definitions with support for multiple inheritance, constructors, `@staticmethod`, and `const` member methods.

Destructors are not emitted: a Cython `cppclass` block does not declare them, and Cython calls the C++ destructor automatically for stack-allocated instances.

```cpp
// widget.hpp
class BaseWidget {
public:
    virtual void show();
};

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

    cdef cppclass BaseWidget:
        void show()

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
double distance(const Point& a, const Point& b)
```

### Namespaces

Declarations inside a namespace are emitted in a dedicated `cdef extern from ... namespace` block:

```cpp
// ns.hpp
namespace outer {
    class Widget {
    public:
        Widget();
        int value() const;
    };
    int helper(int x);
}
```

Generates:

```cython
cdef extern from "ns.hpp" namespace "outer":

    cdef cppclass Widget:
        Widget()
        int value() const

    int helper(int x)
```

Nested namespaces are joined with `::`:

```cpp
namespace outer { namespace inner { int f(int); } }
```

Generates:

```cython
cdef extern from "nested.hpp" namespace "outer::inner":

    int f(int)
```

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
   autopxd mylib.hpp > mylib.pxd
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
