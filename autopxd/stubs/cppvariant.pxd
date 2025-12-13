# autopxd/stubs/cppvariant.pxd
#
# Cython declarations for <variant> (C++17)
# Source: ISO/IEC 14882:2017 (C++17 standard)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when variant is included.
#
# Note: std::variant is a variadic template which Cython cannot fully represent.
# This stub provides basic declarations for common use cases.

from libcpp cimport bool
from libc.stddef cimport size_t

cdef extern from "<variant>" namespace "std":
    # monostate - empty alternative for default-constructible variant
    cdef cppclass monostate:
        pass

    # variant - declared as opaque since Cython can't handle variadic templates
    # Users should create specific instantiations like:
    # ctypedef variant2[int, string] int_or_string "std::variant<int, std::string>"

    cdef cppclass variant[T1]:
        variant()
        variant(const T1&)
        size_t index()
        bool valueless_by_exception()

    cdef cppclass variant2 "std::variant"[T1, T2]:
        variant2()
        variant2(const T1&)
        variant2(const T2&)
        size_t index()
        bool valueless_by_exception()

    cdef cppclass variant3 "std::variant"[T1, T2, T3]:
        variant3()
        size_t index()
        bool valueless_by_exception()

    cdef cppclass variant4 "std::variant"[T1, T2, T3, T4]:
        variant4()
        size_t index()
        bool valueless_by_exception()

    # bad_variant_access exception
    cdef cppclass bad_variant_access:
        const char* what()

    # variant_size - type trait
    # Note: Cython doesn't support constexpr ::value directly

    # variant_npos - sentinel value
    size_t variant_npos

    # Helper functions
    # Note: get<T>, get_if<T>, holds_alternative<T>, visit require
    # template argument deduction which Cython doesn't fully support

    # get_if - returns pointer, nullptr if wrong type
    # Users can call these with explicit template instantiation in Cython
