# autopxd/stubs/netinet_in.pxd
#
# Cython declarations for <netinet/in.h>
# Source: POSIX.1-2017 (IEEE Std 1003.1)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when netinet/in.h is included.

from libc.stdint cimport uint16_t, uint32_t
from autopxd.stubs.sys_socket cimport sa_family_t

cdef extern from "<netinet/in.h>":
    ctypedef uint16_t in_port_t
    ctypedef uint32_t in_addr_t

    cdef struct in_addr:
        in_addr_t s_addr

    cdef struct sockaddr_in:
        sa_family_t sin_family
        in_port_t sin_port
        in_addr sin_addr
        unsigned char sin_zero[8]

    cdef struct in6_addr:
        unsigned char s6_addr[16]

    cdef struct sockaddr_in6:
        sa_family_t sin6_family
        in_port_t sin6_port
        uint32_t sin6_flowinfo
        in6_addr sin6_addr
        uint32_t sin6_scope_id
