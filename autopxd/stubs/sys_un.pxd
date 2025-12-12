# autopxd/stubs/sys_un.pxd
#
# Cython declarations for <sys/un.h>
# Source: POSIX.1-2017 (IEEE Std 1003.1)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when sys/un.h is included.

from autopxd.stubs.sys_socket cimport sa_family_t

cdef extern from "<sys/un.h>":
    cdef struct sockaddr_un:
        sa_family_t sun_family
        char sun_path[108]
