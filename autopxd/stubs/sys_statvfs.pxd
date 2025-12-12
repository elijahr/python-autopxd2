# autopxd/stubs/sys_statvfs.pxd
#
# Cython declarations for <sys/statvfs.h>
# Source: POSIX.1-2017 (IEEE Std 1003.1)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when sys/statvfs.h is included.

cdef extern from "<sys/statvfs.h>":
    ctypedef unsigned long fsblkcnt_t
    ctypedef unsigned long fsfilcnt_t

    cdef struct statvfs:
        unsigned long f_bsize
        unsigned long f_frsize
        fsblkcnt_t f_blocks
        fsblkcnt_t f_bfree
        fsblkcnt_t f_bavail
        fsfilcnt_t f_files
        fsfilcnt_t f_ffree
        fsfilcnt_t f_favail
        unsigned long f_fsid
        unsigned long f_flag
        unsigned long f_namemax

    # Flags for f_flag
    enum:
        ST_RDONLY
        ST_NOSUID

    int statvfs(const char* path, statvfs* buf)
    int fstatvfs(int fd, statvfs* buf)
