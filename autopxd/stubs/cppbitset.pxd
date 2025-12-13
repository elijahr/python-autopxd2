# autopxd/stubs/cppbitset.pxd
#
# Cython declarations for <bitset> (C++11)
# Source: ISO/IEC 14882:2011 (C++11 standard)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when bitset is included.
#
# Note: std::bitset<N> has a non-type template parameter N which
# Cython doesn't fully support. Users should create specific typedefs.

from libcpp cimport bool
from libcpp.string cimport string
from libc.stddef cimport size_t

cdef extern from "<bitset>" namespace "std":
    # bitset - generic declaration
    # Note: Users should create specific size typedefs like:
    # ctypedef bitset bitset8 "std::bitset<8>"
    # ctypedef bitset bitset32 "std::bitset<32>"
    # ctypedef bitset bitset64 "std::bitset<64>"

    cdef cppclass bitset:
        # Constructors
        bitset()
        bitset(unsigned long long)
        bitset(const string&)
        bitset(const char*)

        # Element access
        bool operator[](size_t)
        bool test(size_t) except +
        bool all()
        bool any()
        bool none()
        size_t count()

        # Capacity
        size_t size()

        # Modifiers
        bitset& set()
        bitset& set(size_t, bool)
        bitset& reset()
        bitset& reset(size_t)
        bitset& flip()
        bitset& flip(size_t)

        # Conversions
        unsigned long to_ulong() except +
        unsigned long long to_ullong() except +
        string to_string()

        # Operators defined as member functions
        bool operator==(const bitset&)
        bool operator!=(const bitset&)

    # Common fixed-size bitset aliases
    ctypedef bitset bitset8 "std::bitset<8>"
    ctypedef bitset bitset16 "std::bitset<16>"
    ctypedef bitset bitset32 "std::bitset<32>"
    ctypedef bitset bitset64 "std::bitset<64>"
