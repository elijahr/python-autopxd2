# API Reference

This section documents the public Python API for autopxd2.

## Modules

### [IR Module](ir.md)

The Intermediate Representation (IR) module defines data structures for representing C/C++ constructs:

- `Header` - Top-level container for parsed declarations
- `Struct`, `Enum`, `Function`, `Typedef`, `Variable` - Declaration types
- `CType`, `Pointer`, `Array`, `FunctionPointer` - Type representations

### [Backends](backends.md)

Parser backend implementations:

- `PycparserBackend` - Pure Python C99 parser
- `LibclangBackend` - LLVM clang-based parser with C++ support

## Quick Example

```python
from autopxd.backends import get_backend
from autopxd.ir_writer import write_pxd

# Parse a header
backend = get_backend()  # Uses default (pycparser)
with open("myheader.h") as f:
    code = f.read()

header = backend.parse(code, "myheader.h")

# Generate pxd output
pxd = write_pxd(header)
print(pxd)
```

## Common Patterns

### Inspecting Parsed Declarations

```python
from autopxd.ir import Struct, Function

header = backend.parse(code, "header.h")

for decl in header.declarations:
    if isinstance(decl, Struct):
        print(f"Struct: {decl.name}")
        for field in decl.fields:
            print(f"  {field.name}: {field.type}")
    elif isinstance(decl, Function):
        print(f"Function: {decl.name}")
        print(f"  Returns: {decl.return_type}")
```

### Choosing a Backend

```python
from autopxd.backends import get_backend, list_backends

# List available backends
print(list_backends())  # ['pycparser', 'libclang']

# Get a specific backend
backend = get_backend("libclang")
```
