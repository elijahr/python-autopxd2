# Backends

Parser backends convert C/C++ source code into headerkit's IR. autopxd2 does not
define backends of its own; it selects among the ones headerkit registers.

## Backend Registry

::: headerkit.backends
    options:
      show_root_heading: true
      show_source: false
      members:
        - get_backend
        - list_backends
        - register_backend

## libclang Backend

::: headerkit.backends.libclang
    options:
      show_root_heading: true
      show_source: true
      members:
        - LibclangBackend

## tree-sitter Backend

Registered by the `headerkit[treesitter]` extra (installed via
`pip install "autopxd2[treesitter]"`). Select it with `get_backend("tree-sitter")` or
`autopxd --backend tree-sitter`. See
[Parser Backends](../user-guide/backends.md#tree-sitter) for its limitations.
