cdef extern from "simple_c.h":

    cdef struct Point

    ctypedef void (*Callback)(void*)

    ctypedef int (*Comparator)(const void*, const void*)



    cdef enum ErrorCode:
        ERR_OK
        ERR_INVALID
        ERR_NOMEM

    cdef enum LogLevel:
        LOG_DEBUG
        LOG_INFO
        LOG_WARN
        LOG_ERROR

    int global_debug_enabled


    cdef struct Point:
        int x
        int y

    ctypedef struct Size:
        int width
        int height

    ctypedef struct Buffer:
        char* data
        unsigned int length
        unsigned int capacity


    Point point_create(int x, int y)

    int point_distance(Point a, Point b)

    Buffer* buffer_new(unsigned int capacity)

    void buffer_free(Buffer* buf)

    int buffer_append(Buffer* buf, const char* data, unsigned int len)

    void set_log_level(LogLevel level)

    void log_message(LogLevel level, const char* message)

    void log_printf(LogLevel level, const char* fmt, ...)
