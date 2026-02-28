from importlib import (
    resources,
)

BUILTIN_HEADERS_DIR = resources.files("autopxd").joinpath("stubs/include")
DARWIN_HEADERS_DIR = resources.files("autopxd").joinpath("stubs/darwin-include")
