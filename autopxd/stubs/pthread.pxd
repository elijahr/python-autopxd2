# autopxd/stubs/pthread.pxd
#
# Cython declarations for <pthread.h>
# Source: POSIX.1-2017 (IEEE Std 1003.1)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when pthread.h is included.

cdef extern from "<pthread.h>":
    # Opaque types (implementation-defined)
    ctypedef struct pthread_t:
        pass
    ctypedef struct pthread_attr_t:
        pass
    ctypedef struct pthread_mutex_t:
        pass
    ctypedef struct pthread_mutexattr_t:
        pass
    ctypedef struct pthread_cond_t:
        pass
    ctypedef struct pthread_condattr_t:
        pass
    ctypedef struct pthread_rwlock_t:
        pass
    ctypedef struct pthread_rwlockattr_t:
        pass
    ctypedef struct pthread_key_t:
        pass
    ctypedef struct pthread_once_t:
        pass

    # Thread functions
    int pthread_create(pthread_t *thread, const pthread_attr_t *attr,
                       void *(*start_routine)(void *), void *arg)
    int pthread_join(pthread_t thread, void **retval)
    int pthread_detach(pthread_t thread)
    void pthread_exit(void *retval)
    pthread_t pthread_self()
    int pthread_equal(pthread_t t1, pthread_t t2)

    # Mutex functions
    int pthread_mutex_init(pthread_mutex_t *mutex, const pthread_mutexattr_t *attr)
    int pthread_mutex_destroy(pthread_mutex_t *mutex)
    int pthread_mutex_lock(pthread_mutex_t *mutex)
    int pthread_mutex_trylock(pthread_mutex_t *mutex)
    int pthread_mutex_unlock(pthread_mutex_t *mutex)

    # Condition variable functions
    int pthread_cond_init(pthread_cond_t *cond, const pthread_condattr_t *attr)
    int pthread_cond_destroy(pthread_cond_t *cond)
    int pthread_cond_wait(pthread_cond_t *cond, pthread_mutex_t *mutex)
    int pthread_cond_signal(pthread_cond_t *cond)
    int pthread_cond_broadcast(pthread_cond_t *cond)

    # Read-write lock functions
    int pthread_rwlock_init(pthread_rwlock_t *rwlock, const pthread_rwlockattr_t *attr)
    int pthread_rwlock_destroy(pthread_rwlock_t *rwlock)
    int pthread_rwlock_rdlock(pthread_rwlock_t *rwlock)
    int pthread_rwlock_wrlock(pthread_rwlock_t *rwlock)
    int pthread_rwlock_unlock(pthread_rwlock_t *rwlock)
