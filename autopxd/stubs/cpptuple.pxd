# autopxd/stubs/cpptuple.pxd
#
# Cython declarations for <tuple> (C++11)
# Source: ISO/IEC 14882:2011 (C++11 standard)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when tuple is included.
#
# Note: std::tuple is a variadic template which Cython cannot fully represent.
# This stub provides basic declarations for common use cases.

from libcpp cimport bool

cdef extern from "<tuple>" namespace "std":
    # tuple - declared as opaque since Cython can't handle variadic templates
    # Users should use fused types or specific instantiations
    cdef cppclass tuple[T1]:
        tuple()

    cdef cppclass tuple2 "std::tuple"[T1, T2]:
        tuple2()

    cdef cppclass tuple3 "std::tuple"[T1, T2, T3]:
        tuple3()

    cdef cppclass tuple4 "std::tuple"[T1, T2, T3, T4]:
        tuple4()

    cdef cppclass tuple5 "std::tuple"[T1, T2, T3, T4, T5]:
        tuple5()

    # tuple_size - type trait, limited support
    # Note: Cython doesn't support constexpr or ::value syntax directly

    # Helper functions
    # Note: make_tuple and get require template argument deduction
    # which Cython doesn't fully support

    # tie - creates tuple of references
    # Note: Also requires variadic templates

    # forward_as_tuple - forwards arguments as tuple
    # Note: Also requires variadic templates

    # tuple_cat - concatenate tuples
    # Note: Also requires variadic templates

    # ignore - placeholder for tie
    cdef struct _Ignore "std::ignore":
        pass
