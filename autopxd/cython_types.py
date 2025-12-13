"""
Cython type registries for automatic cimport generation.

This module provides mappings from C/C++ header files to Cython modules,
enabling autopxd to automatically generate appropriate cimport statements.

Three registries are provided:
1. CYTHON_STDLIB_HEADERS - Maps system headers to Cython libc/posix/cpython modules
2. AUTOPXD_STUB_HEADERS - Maps headers to bundled autopxd stub modules
3. LIBCPP_HEADERS - Maps C++ STL headers to libcpp modules
"""

from __future__ import annotations

# =============================================================================
# Cython Standard Library Registry
# =============================================================================
# Maps C standard library headers to (cython_module, set_of_types)
# These types are available in Cython's bundled libc, posix, and cpython packages

CYTHON_STDLIB_HEADERS: dict[str, tuple[str, set[str]]] = {
    # libc headers
    "stddef.h": (
        "libc.stddef",
        {
            # Note: size_t and ssize_t are Cython built-ins, don't need cimport
            "ptrdiff_t",
            "wchar_t",
        },
    ),
    "stdint.h": (
        "libc.stdint",
        {
            "int8_t",
            "int16_t",
            "int32_t",
            "int64_t",
            "uint8_t",
            "uint16_t",
            "uint32_t",
            "uint64_t",
            "intptr_t",
            "uintptr_t",
            # Note: size_t is in libc.stddef, ssize_t is Cython built-in
            "intmax_t",
            "uintmax_t",
        },
    ),
    "stdio.h": (
        "libc.stdio",
        {"FILE", "fpos_t"},
    ),
    "stdlib.h": (
        "libc.stdlib",
        {"div_t", "ldiv_t", "lldiv_t"},
    ),
    "string.h": (
        "libc.string",
        set(),  # Functions only, no types
    ),
    "math.h": (
        "libc.math",
        set(),  # Functions only, no types
    ),
    "time.h": (
        "libc.time",
        {"time_t", "tm", "clock_t", "timespec"},
    ),
    "signal.h": (
        "libc.signal",
        {"sig_atomic_t", "sigset_t"},
    ),
    "errno.h": (
        "libc.errno",
        set(),  # errno variable only
    ),
    "setjmp.h": (
        "libc.setjmp",
        {"jmp_buf"},
    ),
    "locale.h": (
        "libc.locale",
        {"lconv"},
    ),
    # posix headers
    "unistd.h": (
        "posix.unistd",
        {"pid_t", "uid_t", "gid_t", "off_t"},
    ),
    "fcntl.h": (
        "posix.fcntl",
        set(),  # Constants and functions only
    ),
    "sys/stat.h": (
        "posix.stat",
        {"stat", "mode_t"},
    ),
    "sys/types.h": (
        "posix.types",
        {
            "pid_t",
            "uid_t",
            "gid_t",
            "off_t",
            "mode_t",
            "dev_t",
            "ino_t",
            "nlink_t",
        },
    ),
    # NOTE: posix.dirent doesn't exist in Cython - use our stub instead
    "dlfcn.h": (
        "posix.dlfcn",
        set(),  # Functions only
    ),
    # cpython headers
    "Python.h": (
        "cpython",
        {"PyObject", "PyTypeObject", "Py_ssize_t"},
    ),
}

# =============================================================================
# Autopxd Bundled Stub Registry
# =============================================================================
# Maps headers to autopxd stub module names (in autopxd.stubs package)
# These are types that Cython doesn't provide but are commonly needed

AUTOPXD_STUB_HEADERS: dict[str, str] = {
    "stdarg.h": "stdarg",
    "sys/socket.h": "sys_socket",
    "netinet/in.h": "netinet_in",
    "arpa/inet.h": "arpa_inet",
    "sys/statvfs.h": "sys_statvfs",
    "sys/select.h": "sys_select",
}

# Maps type names to their stub module
AUTOPXD_STUB_TYPES: dict[str, str] = {
    # stdarg
    "va_list": "stdarg",
    # dirent.h (not available in Cython's posix.dirent)
    "DIR": "dirent",
    "dirent": "dirent",
    # sys/socket.h
    "sockaddr": "sys_socket",
    "socklen_t": "sys_socket",
    "sa_family_t": "sys_socket",
    # netinet/in.h
    "sockaddr_in": "netinet_in",
    "sockaddr_in6": "netinet_in",
    "in_addr": "netinet_in",
    "in6_addr": "netinet_in",
    "in_port_t": "netinet_in",
    "in_addr_t": "netinet_in",
    # arpa/inet.h - functions only, types from netinet/in.h
    # sys/statvfs.h
    "statvfs": "sys_statvfs",
    # sys/select.h
    "fd_set": "sys_select",
    "timeval": "sys_select",
}

# =============================================================================
# C++ STL Registry
# =============================================================================
# Maps C++ STL headers to (cython_module, set_of_types)

LIBCPP_HEADERS: dict[str, tuple[str, set[str]]] = {
    "vector": ("libcpp.vector", {"vector"}),
    "string": ("libcpp.string", {"string"}),
    "map": ("libcpp.map", {"map"}),
    "set": ("libcpp.set", {"set"}),
    "unordered_map": ("libcpp.unordered_map", {"unordered_map"}),
    "unordered_set": ("libcpp.unordered_set", {"unordered_set"}),
    "memory": (
        "libcpp.memory",
        {"shared_ptr", "unique_ptr", "weak_ptr", "allocator"},
    ),
    "list": ("libcpp.list", {"list"}),
    "deque": ("libcpp.deque", {"deque"}),
    "queue": ("libcpp.queue", {"queue", "priority_queue"}),
    "stack": ("libcpp.stack", {"stack"}),
    "utility": ("libcpp.utility", {"pair", "move"}),
    "algorithm": ("libcpp.algorithm", set()),  # Functions only
    "iterator": ("libcpp.iterator", set()),  # Iterator concepts
    "functional": ("libcpp.functional", {"function", "reference_wrapper"}),
    "complex": ("libcpp.complex", {"complex"}),
    "limits": ("libcpp.limits", {"numeric_limits"}),
    "typeinfo": ("libcpp.typeinfo", {"type_info"}),
    "optional": ("libcpp.optional", {"optional", "nullopt_t"}),
    "variant": ("libcpp.variant", {"variant"}),
    "any": ("libcpp.any", {"any"}),
}

# =============================================================================
# Reverse Lookup Tables (built at import time)
# =============================================================================
# Maps type names to (cython_module, header_name)

CYTHON_STDLIB_TYPES: dict[str, tuple[str, str]] = {}
LIBCPP_TYPES: dict[str, tuple[str, str]] = {}


def _build_reverse_lookups() -> None:
    """Build reverse lookup tables from header mappings."""
    # Cython stdlib types
    for header, (module, types) in CYTHON_STDLIB_HEADERS.items():
        for type_name in types:
            # First header wins if type appears in multiple headers
            if type_name not in CYTHON_STDLIB_TYPES:
                CYTHON_STDLIB_TYPES[type_name] = (module, header)

    # C++ STL types
    for header, (module, types) in LIBCPP_HEADERS.items():
        for type_name in types:
            if type_name not in LIBCPP_TYPES:
                LIBCPP_TYPES[type_name] = (module, header)


# Build reverse lookups on module import
_build_reverse_lookups()


# =============================================================================
# Lookup Functions
# =============================================================================


def get_cython_module_for_type(type_name: str) -> str | None:
    """Get the Cython module that provides a type.

    Args:
        type_name: The C type name (e.g., "uint32_t", "FILE")

    Returns:
        The Cython module path (e.g., "libc.stdint") or None if not found.
    """
    entry = CYTHON_STDLIB_TYPES.get(type_name)
    return entry[0] if entry else None


def get_stub_module_for_type(type_name: str) -> str | None:
    """Get the autopxd stub module that provides a type.

    Args:
        type_name: The C type name (e.g., "va_list", "sockaddr")

    Returns:
        The stub module name (e.g., "stdarg") or None if not found.
    """
    return AUTOPXD_STUB_TYPES.get(type_name)


def get_libcpp_module_for_type(type_name: str) -> str | None:
    """Get the Cython libcpp module that provides a C++ type.

    Args:
        type_name: The C++ type name (e.g., "vector", "shared_ptr")

    Returns:
        The Cython module path (e.g., "libcpp.vector") or None if not found.
    """
    entry = LIBCPP_TYPES.get(type_name)
    return entry[0] if entry else None
