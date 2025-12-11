cdef extern from "compression_lib.h":

    ctypedef unsigned char Byte

    ctypedef unsigned int uInt

    ctypedef unsigned long uLong

    ctypedef void* voidp

    ctypedef voidp (*alloc_func)(voidp opaque, uInt items, uInt size)

    ctypedef void (*free_func)(voidp opaque, voidp address)

    cdef struct internal_state

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

    ctypedef compress_stream_s compress_stream

    ctypedef enum compress_status:
        COMPRESS_OK
        COMPRESS_STREAM_END
        COMPRESS_NEED_DICT
        COMPRESS_ERRNO
        COMPRESS_STREAM_ERROR
        COMPRESS_DATA_ERROR
        COMPRESS_MEM_ERROR
        COMPRESS_BUF_ERROR

    const char* compress_version()

    int compress_init(compress_stream* strm, int level)

    int compress(compress_stream* strm, int flush)

    int compress_end(compress_stream* strm)

    int decompress_init(compress_stream* strm)

    int decompress(compress_stream* strm, int flush)

    int decompress_end(compress_stream* strm)

    uLong compress_bound(uLong sourceLen)

    int compress_buffer(Byte* dest, uLong* destLen, const Byte* source, uLong sourceLen)

    int decompress_buffer(Byte* dest, uLong* destLen, const Byte* source, uLong sourceLen)
