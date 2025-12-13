# autopxd/stubs/cpparray.pxd
#
# Cython declarations for <array> (C++11)
# Source: ISO/IEC 14882:2011 (C++11 standard)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when array is included.
#
# Note: std::array<T, N> has a non-type template parameter N which
# Cython doesn't fully support. This stub provides common fixed-size aliases.

from libcpp cimport bool
from libc.stddef cimport size_t

cdef extern from "<array>" namespace "std":
    # Generic array declaration - size must be specified at instantiation
    # Note: Cython doesn't support non-type template parameters,
    # so users need to create specific typedefs like:
    # ctypedef array[int] int_array_10 "std::array<int, 10>"

    cdef cppclass array[T]:
        # Element access
        T& at(size_t) except +
        T& operator[](size_t)
        T& front()
        T& back()
        T* data()

        # Iterators - opaque, use data() + size() for iteration

        # Capacity
        bool empty()
        size_t size()
        size_t max_size()

        # Operations
        void fill(const T&)
        void swap(array&)

    # Common fixed-size array aliases
    # Users can add more as needed with:
    # ctypedef array[int] int_array_N "std::array<int, N>"

    # Helper for creating array with deduced type
    # Note: Requires C++17 deduction guides, not available in all contexts
