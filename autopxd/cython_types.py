"""Cython type registries - re-exported from headerkit."""

from headerkit.writers._cython_types import (
    CYTHON_STDLIB_HEADERS,
    CYTHON_STDLIB_TYPES,
    HEADERKIT_STUB_TYPES,
    LIBCPP_HEADERS,
    LIBCPP_TYPES,
    get_cython_module_for_type,
    get_libcpp_module_for_type,
    get_stub_module_for_type,
)

# Backward-compatible alias
AUTOPXD_STUB_TYPES = HEADERKIT_STUB_TYPES

# Backward compatibility: autopxd2 had AUTOPXD_STUB_HEADERS mapping
# headers to stub module names.
AUTOPXD_STUB_HEADERS: dict[str, str] = {
    "stdarg.h": "stdarg",
    "sys/socket.h": "sys_socket",
    "netinet/in.h": "netinet_in",
    "arpa/inet.h": "arpa_inet",
    "sys/statvfs.h": "sys_statvfs",
    "sys/select.h": "sys_select",
}

__all__ = [
    "AUTOPXD_STUB_HEADERS",
    "AUTOPXD_STUB_TYPES",
    "CYTHON_STDLIB_HEADERS",
    "CYTHON_STDLIB_TYPES",
    "HEADERKIT_STUB_TYPES",
    "LIBCPP_HEADERS",
    "LIBCPP_TYPES",
    "get_cython_module_for_type",
    "get_libcpp_module_for_type",
    "get_stub_module_for_type",
]
