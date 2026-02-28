cdef extern from "compression_lib.h":

    cdef struct compress_stream_s

    ctypedef unsigned char Byte

    ctypedef unsigned int uInt

    ctypedef unsigned long uLong

    ctypedef void* voidp

    ctypedef voidp (*alloc_func)(voidp, uInt, uInt)

    ctypedef void (*free_func)(voidp, voidp)

    ctypedef compress_stream_s compress_stream



    const char* COMPRESS_VERSION

    int COMPRESS_VERNUM

    int COMPRESS_NO_COMPRESSION

    int COMPRESS_BEST_SPEED

    int COMPRESS_BEST_COMPRESSION

    int COMPRESS_DEFAULT_COMPRESSION

    cdef struct internal_state

    cdef enum compress_status:
        COMPRESS_OK
        COMPRESS_STREAM_END
        COMPRESS_NEED_DICT
        COMPRESS_ERRNO
        COMPRESS_STREAM_ERROR
        COMPRESS_DATA_ERROR
        COMPRESS_MEM_ERROR
        COMPRESS_BUF_ERROR


    cdef struct compress_stream_s:
        Byte* next_in
        uInt avail_in
        uLong total_in
        Byte* next_out
        uInt avail_out
        uLong total_out
        const char* msg
        internal_state* state
        alloc_func zalloc
        free_func zfree
        voidp opaque


    const char* compress_version()

    int compress_init(compress_stream* strm, int level)

    int compress(compress_stream* strm, int flush)

    int compress_end(compress_stream* strm)

    int decompress_init(compress_stream* strm)

    int decompress(compress_stream* strm, int flush)

    int decompress_end(compress_stream* strm)

    uLong compress_bound(uLong sourceLen)

    int compress_buffer(Byte* dest, uLong* destLen, Byte* source, uLong sourceLen)

    int decompress_buffer(Byte* dest, uLong* destLen, Byte* source, uLong sourceLen)
