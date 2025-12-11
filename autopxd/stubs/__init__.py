"""
Bundled Cython stub files for types not in Cython's standard library.

This package provides .pxd declarations for commonly used C types that
Cython doesn't include in its libc/posix packages. These stubs are
automatically imported by autopxd when the corresponding headers are
detected in parsed code.

Available stubs:
- stdarg.pxd: va_list for variadic functions
- sys_socket.pxd: socket types (sockaddr, socklen_t)
- netinet_in.pxd: IPv4/IPv6 address types
- arpa_inet.pxd: inet_ntoa, inet_addr, etc.
- sys_statvfs.pxd: filesystem statistics
- sys_select.pxd: fd_set, select()
"""
