# Backends

Parser backends convert C/C++ source code into the autopxd IR.

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
