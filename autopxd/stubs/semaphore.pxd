# autopxd/stubs/semaphore.pxd
#
# Cython declarations for <semaphore.h>
# Source: POSIX.1-2017 (IEEE Std 1003.1)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when semaphore.h is included.

cdef extern from "<semaphore.h>":
    ctypedef struct sem_t:
        pass

    int sem_init(sem_t* sem, int pshared, unsigned int value)
    int sem_destroy(sem_t* sem)
    int sem_wait(sem_t* sem)
    int sem_trywait(sem_t* sem)
    int sem_post(sem_t* sem)
    int sem_getvalue(sem_t* sem, int* sval)

    sem_t* sem_open(const char* name, int oflag, ...)
    int sem_close(sem_t* sem)
    int sem_unlink(const char* name)
