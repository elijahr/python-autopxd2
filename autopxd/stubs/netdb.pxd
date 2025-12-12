# autopxd/stubs/netdb.pxd
#
# Cython declarations for <netdb.h>
# Source: POSIX.1-2017 (IEEE Std 1003.1)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when netdb.h is included.

from autopxd.stubs.sys_socket cimport sockaddr, socklen_t

cdef extern from "<netdb.h>":
    cdef struct hostent:
        char *h_name
        char **h_aliases
        int h_addrtype
        int h_length
        char **h_addr_list

    cdef struct addrinfo:
        int ai_flags
        int ai_family
        int ai_socktype
        int ai_protocol
        socklen_t ai_addrlen
        sockaddr *ai_addr
        char *ai_canonname
        addrinfo *ai_next

    # Constants
    enum:
        AI_PASSIVE
        AI_CANONNAME
        AI_NUMERICHOST
        AI_NUMERICSERV
        AI_V4MAPPED
        AI_ALL
        AI_ADDRCONFIG

    enum:
        NI_MAXHOST
        NI_MAXSERV
        NI_NUMERICHOST
        NI_NUMERICSERV
        NI_NOFQDN
        NI_NAMEREQD
        NI_DGRAM

    # Functions
    hostent *gethostbyname(const char *name)
    hostent *gethostbyaddr(const void *addr, socklen_t len, int type)
    int getaddrinfo(const char *node, const char *service,
                    const addrinfo *hints, addrinfo **res)
    void freeaddrinfo(addrinfo *res)
    int getnameinfo(const sockaddr *addr, socklen_t addrlen,
                    char *host, socklen_t hostlen,
                    char *serv, socklen_t servlen, int flags)
    const char *gai_strerror(int errcode)
