# autopxd/stubs/arpa_inet.pxd
#
# Cython declarations for <arpa/inet.h>
# Source: POSIX.1-2017 (IEEE Std 1003.1)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when arpa/inet.h is included.

from libc.stdint cimport uint16_t, uint32_t

cdef extern from "<arpa/inet.h>":
    ctypedef uint32_t in_addr_t
    ctypedef uint16_t in_port_t

    cdef struct in_addr:
        in_addr_t s_addr

    uint32_t htonl(uint32_t hostlong)
    uint16_t htons(uint16_t hostshort)
    uint32_t ntohl(uint32_t netlong)
    uint16_t ntohs(uint16_t netshort)

    int inet_pton(int af, const char *src, void *dst)
    const char *inet_ntop(int af, const void *src, char *dst, unsigned int size)
    in_addr_t inet_addr(const char *cp)
    char *inet_ntoa(in_addr in_val)
