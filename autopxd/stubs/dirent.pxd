# autopxd/stubs/dirent.pxd
#
# Cython declarations for <dirent.h>
# Source: POSIX.1-2017 (IEEE Std 1003.1)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when dirent.h is included.

from libc.stdint cimport uint64_t

cdef extern from "<dirent.h>":
    ctypedef struct DIR:
        pass

    cdef struct dirent:
        uint64_t d_ino
        char d_name[256]

    DIR *opendir(const char *name)
    dirent *readdir(DIR *dirp)
    int closedir(DIR *dirp)
    void rewinddir(DIR *dirp)
    void seekdir(DIR *dirp, long loc)
    long telldir(DIR *dirp)
    int dirfd(DIR *dirp)
