# autopxd/stubs/regex.pxd
#
# Cython declarations for <regex.h>
# Source: POSIX.1-2017 (IEEE Std 1003.1)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when regex.h is included.

from libc.stddef cimport size_t

cdef extern from "<regex.h>":
    ctypedef struct regex_t:
        size_t re_nsub

    ctypedef long regoff_t

    cdef struct regmatch_t:
        regoff_t rm_so
        regoff_t rm_eo

    # Flags for regcomp
    enum:
        REG_EXTENDED
        REG_ICASE
        REG_NOSUB
        REG_NEWLINE

    # Flags for regexec
    enum:
        REG_NOTBOL
        REG_NOTEOL

    # Error codes
    enum:
        REG_NOMATCH
        REG_BADPAT
        REG_ECOLLATE
        REG_ECTYPE
        REG_EESCAPE
        REG_ESUBREG
        REG_EBRACK
        REG_EPAREN
        REG_EBRACE
        REG_BADBR
        REG_ERANGE
        REG_ESPACE
        REG_BADRPT

    int regcomp(regex_t* preg, const char* pattern, int cflags)
    int regexec(const regex_t* preg, const char* string, size_t nmatch,
                regmatch_t* pmatch, int eflags)
    void regfree(regex_t* preg)
    size_t regerror(int errcode, const regex_t* preg, char* errbuf, size_t errbuf_size)
