# Backends

Parser backends convert C/C++ source code into the autopxd IR.

## Backend Registry

::: autopxd.backends
    options:
      show_root_heading: true
      show_source: false
      members:
        - get_backend
        - list_backends
        - register_backend

## pycparser Backend

::: autopxd.backends.pycparser_backend
    options:
      show_root_heading: true
      show_source: true
      members:
        - PycparserBackend

## libclang Backend

::: autopxd.backends.libclang_backend
    options:
      show_root_heading: true
      show_source: true
      members:
        - LibclangBackend
