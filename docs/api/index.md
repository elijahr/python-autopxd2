# API Reference

autopxd2's own Python API is small: a `translate()` function and a Click command.
Everything else — the intermediate representation, the parser backends, and the
Cython writer — lives in [`headerkit`](https://github.com/elijahr/headerkit), which
autopxd2 builds on. The pages below document the headerkit APIs that autopxd2 uses,
so that callers of `translate()` can work with the objects it produces.

## autopxd

::: autopxd
    options:
      show_root_heading: true
      show_source: true
      members:
        - translate
        - cli

## headerkit Modules

### [IR Module](ir.md)

The Intermediate Representation (IR) module defines data structures for representing C/C++ constructs:

- `Header` - Top-level container for parsed declarations
- `Struct`, `Enum`, `Function`, `Typedef`, `Variable` - Declaration types
- `CType`, `Pointer`, `Array`, `FunctionPointer` - Type representations

### [Backends](backends.md)

Parser backend implementations:

- `LibclangBackend` - LLVM clang-based parser with full C/C++ support
- The `tree-sitter` backend, registered by `headerkit[treesitter]`, is selected by
  name through `get_backend("tree-sitter")`

## Quick Example

```python
from headerkit.backends import get_backend
from headerkit.writers.cython import write_pxd

# Parse a header
backend = get_backend()  # Uses default (libclang)
with open("myheader.h") as f:
    code = f.read()

header = backend.parse(code, "myheader.h")

# Generate pxd output
pxd = write_pxd(header)
print(pxd)
```

Or go straight from source text to `.pxd` text:

```python
import autopxd

with open("myheader.h") as f:
    print(autopxd.translate(f.read(), "myheader.h"))
```

## Common Patterns

### Inspecting Parsed Declarations

```python
from headerkit.ir import Struct, Function

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
from headerkit.backends import get_backend, list_backends

# List registered backends
print(list_backends())  # ['libclang', 'tree-sitter']

# Get a specific backend
backend = get_backend("libclang")
```
