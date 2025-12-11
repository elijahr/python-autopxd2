# autopxd/stubs/sys_socket.pxd
#
# Cython declarations for <sys/socket.h>
# Source: POSIX.1-2017 (IEEE Std 1003.1)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when sys/socket.h is included.

from libc.stdint cimport uint8_t, uint16_t

cdef extern from "<sys/socket.h>":
    ctypedef unsigned int socklen_t
    ctypedef unsigned short sa_family_t

    cdef struct sockaddr:
        sa_family_t sa_family
        char sa_data[14]
