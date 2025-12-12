# autopxd/stubs/cppchrono.pxd
#
# Cython declarations for <chrono> (C++11)
# Source: ISO/IEC 14882:2011 (C++11 standard)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when chrono is included.
#
# Note: std::chrono uses non-type template parameters (ratio) which Cython
# cannot represent. Duration types are declared as opaque structs.

from libc.stdint cimport int64_t
from libcpp cimport bool

cdef extern from "<chrono>" namespace "std::chrono":
    # Duration types (opaque - Cython can't handle ratio template params)
    cdef cppclass nanoseconds:
        nanoseconds()
        nanoseconds(int64_t)
        int64_t count()

    cdef cppclass microseconds:
        microseconds()
        microseconds(int64_t)
        int64_t count()

    cdef cppclass milliseconds:
        milliseconds()
        milliseconds(int64_t)
        int64_t count()

    cdef cppclass seconds:
        seconds()
        seconds(int64_t)
        int64_t count()

    cdef cppclass minutes:
        minutes()
        minutes(int64_t)
        int64_t count()

    cdef cppclass hours:
        hours()
        hours(int64_t)
        int64_t count()

    # Time point types (opaque)
    cdef cppclass system_clock_time_point "std::chrono::system_clock::time_point":
        pass

    cdef cppclass steady_clock_time_point "std::chrono::steady_clock::time_point":
        pass

    cdef cppclass high_resolution_clock_time_point "std::chrono::high_resolution_clock::time_point":
        pass

    # Clock operations
    system_clock_time_point system_clock_now "std::chrono::system_clock::now"() nogil
    steady_clock_time_point steady_clock_now "std::chrono::steady_clock::now"() nogil
    high_resolution_clock_time_point high_resolution_clock_now "std::chrono::high_resolution_clock::now"() nogil
