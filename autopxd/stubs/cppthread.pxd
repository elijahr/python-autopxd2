# autopxd/stubs/cppthread.pxd
#
# Cython declarations for <thread> (C++11)
# Source: ISO/IEC 14882:2011 (C++11 standard)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when thread is included.

from libcpp cimport bool

cdef extern from "<thread>" namespace "std":
    cdef cppclass thread:
        thread()
        # Note: Constructor with callable requires specific template instantiation
        void join()
        void detach()
        bool joinable()

        cppclass id:
            pass

        id get_id()

        @staticmethod
        unsigned int hardware_concurrency()

cdef extern from "<thread>" namespace "std::this_thread":
    thread.id get_id() nogil
    void yield_ "std::this_thread::yield"() nogil
    # Note: sleep_for and sleep_until require chrono types
