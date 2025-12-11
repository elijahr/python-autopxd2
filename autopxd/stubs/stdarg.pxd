# autopxd/stubs/stdarg.pxd
#
# Cython declarations for <stdarg.h>
# Source: C99 Standard (ISO/IEC 9899:1999)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when stdarg.h is included.
# va_list is an opaque type - the actual implementation is compiler-specific.

cdef extern from "<stdarg.h>":
    ctypedef struct va_list:
        pass
