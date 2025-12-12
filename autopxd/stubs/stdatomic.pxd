# autopxd/stubs/stdatomic.pxd
#
# Cython declarations for <stdatomic.h> (C11)
# Source: ISO/IEC 9899:2011 (C11 standard)
# License: Public domain (interface declarations)
#
# Note: For C++ code, use libcpp.atomic instead.
# Auto-imported by autopxd when stdatomic.h is included.

from libc.stdint cimport int8_t, int16_t, int32_t, int64_t
from libc.stdint cimport uint8_t, uint16_t, uint32_t, uint64_t
from libc.stdint cimport intptr_t, uintptr_t
from libc.stddef cimport size_t, ptrdiff_t

cdef extern from "<stdatomic.h>":
    # Memory order enum
    enum memory_order:
        memory_order_relaxed
        memory_order_consume
        memory_order_acquire
        memory_order_release
        memory_order_acq_rel
        memory_order_seq_cst

    # Atomic flag type
    ctypedef struct atomic_flag:
        pass

    # Atomic integer types
    ctypedef struct atomic_bool:
        pass
    ctypedef struct atomic_char:
        pass
    ctypedef struct atomic_schar:
        pass
    ctypedef struct atomic_uchar:
        pass
    ctypedef struct atomic_short:
        pass
    ctypedef struct atomic_ushort:
        pass
    ctypedef struct atomic_int:
        pass
    ctypedef struct atomic_uint:
        pass
    ctypedef struct atomic_long:
        pass
    ctypedef struct atomic_ulong:
        pass
    ctypedef struct atomic_llong:
        pass
    ctypedef struct atomic_ullong:
        pass
    ctypedef struct atomic_size_t:
        pass
    ctypedef struct atomic_ptrdiff_t:
        pass
    ctypedef struct atomic_intptr_t:
        pass
    ctypedef struct atomic_uintptr_t:
        pass

    # Atomic flag operations
    bint atomic_flag_test_and_set(atomic_flag* obj)
    bint atomic_flag_test_and_set_explicit(atomic_flag* obj, memory_order order)
    void atomic_flag_clear(atomic_flag* obj)
    void atomic_flag_clear_explicit(atomic_flag* obj, memory_order order)

    # Fence
    void atomic_thread_fence(memory_order order)
    void atomic_signal_fence(memory_order order)
