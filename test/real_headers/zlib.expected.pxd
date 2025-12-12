from autopxd.stubs.stdarg cimport va_list

cdef extern from "zlib.h":

    ctypedef unsigned char Byte

    ctypedef Byte Bytef

    ctypedef unsigned int uInt

    ctypedef unsigned long uLong

    ctypedef uLong uLongf

    ctypedef void* voidp

    ctypedef const void* voidpc

    ctypedef void* voidpf

    ctypedef unsigned int z_crc_t

    ctypedef size_t z_size_t

    const char* ZLIB_VERSION

    int ZLIB_VERNUM

    int ZLIB_VER_MAJOR

    int ZLIB_VER_MINOR

    int ZLIB_VER_REVISION

    int ZLIB_VER_SUBREVISION

    int Z_NO_FLUSH

    int Z_PARTIAL_FLUSH

    int Z_SYNC_FLUSH

    int Z_FULL_FLUSH

    int Z_FINISH

    int Z_BLOCK

    int Z_TREES

    int Z_OK

    int Z_STREAM_END

    int Z_NEED_DICT

    int Z_ERRNO

    int Z_STREAM_ERROR

    int Z_DATA_ERROR

    int Z_MEM_ERROR

    int Z_BUF_ERROR

    int Z_VERSION_ERROR

    int Z_NO_COMPRESSION

    int Z_BEST_SPEED

    int Z_BEST_COMPRESSION

    int Z_DEFAULT_COMPRESSION

    int Z_FILTERED

    int Z_HUFFMAN_ONLY

    int Z_RLE

    int Z_FIXED

    int Z_DEFAULT_STRATEGY

    int Z_BINARY

    int Z_TEXT

    int Z_UNKNOWN

    int Z_DEFLATED

    int Z_NULL

    int zlib_version

    ctypedef voidpf (*alloc_func)(voidpf, uInt, uInt)

    ctypedef void (*free_func)(voidpf, voidpf)

    cdef struct internal_state

    cdef struct z_stream_s:
        Bytef* next_in
        uInt avail_in
        uLong total_in
        Bytef* next_out
        uInt avail_out
        uLong total_out
        char* msg
        internal_state* state
        alloc_func zalloc
        free_func zfree
        voidpf opaque
        int data_type
        uLong adler
        uLong reserved

    ctypedef z_stream_s z_stream

    ctypedef z_stream* z_streamp

    cdef struct gz_header_s:
        int text
        uLong time
        int xflags
        int os
        Bytef* extra
        uInt extra_len
        uInt extra_max
        Bytef* name
        uInt name_max
        Bytef* comment
        uInt comm_max
        int hcrc
        int done

    ctypedef gz_header_s gz_header

    ctypedef gz_header* gz_headerp

    const char* zlibVersion()

    int deflate(z_streamp strm, int flush)

    int deflateEnd(z_streamp strm)

    int inflate(z_streamp strm, int flush)

    int inflateEnd(z_streamp strm)

    int deflateSetDictionary(z_streamp strm, Bytef* dictionary, uInt dictLength)

    int deflateGetDictionary(z_streamp strm, Bytef* dictionary, uInt* dictLength)

    int deflateCopy(z_streamp dest, z_streamp source)

    int deflateReset(z_streamp strm)

    int deflateParams(z_streamp strm, int level, int strategy)

    int deflateTune(z_streamp strm, int good_length, int max_lazy, int nice_length, int max_chain)

    uLong deflateBound(z_streamp strm, uLong sourceLen)

    int deflatePending(z_streamp strm, unsigned int* pending, int* bits)

    int deflatePrime(z_streamp strm, int bits, int value)

    int deflateSetHeader(z_streamp strm, gz_headerp head)

    int inflateSetDictionary(z_streamp strm, Bytef* dictionary, uInt dictLength)

    int inflateGetDictionary(z_streamp strm, Bytef* dictionary, uInt* dictLength)

    int inflateSync(z_streamp strm)

    int inflateCopy(z_streamp dest, z_streamp source)

    int inflateReset(z_streamp strm)

    int inflateReset2(z_streamp strm, int windowBits)

    int inflatePrime(z_streamp strm, int bits, int value)

    long inflateMark(z_streamp strm)

    int inflateGetHeader(z_streamp strm, gz_headerp head)

    ctypedef unsigned int (*in_func)(void*, unsigned char**)

    ctypedef int (*out_func)(void*, unsigned char*, unsigned int)

    int inflateBack(z_streamp strm, in_func in_, void* in_desc, out_func out, void* out_desc)

    int inflateBackEnd(z_streamp strm)

    uLong zlibCompileFlags()

    int compress(Bytef* dest, uLongf* destLen, Bytef* source, uLong sourceLen)

    int compress2(Bytef* dest, uLongf* destLen, Bytef* source, uLong sourceLen, int level)

    uLong compressBound(uLong sourceLen)

    int uncompress(Bytef* dest, uLongf* destLen, Bytef* source, uLong sourceLen)

    int uncompress2(Bytef* dest, uLongf* destLen, Bytef* source, uLong* sourceLen)

    uLong adler32(uLong adler, Bytef* buf, uInt len)

    uLong adler32_z(uLong adler, Bytef* buf, z_size_t len)

    uLong crc32(uLong crc, Bytef* buf, uInt len)

    uLong crc32_z(uLong crc, Bytef* buf, z_size_t len)

    uLong crc32_combine_op(uLong crc1, uLong crc2, uLong op)

    int deflateInit_(z_streamp strm, int level, const char* version, int stream_size)

    int inflateInit_(z_streamp strm, const char* version, int stream_size)

    int deflateInit2_(z_streamp strm, int level, int method, int windowBits, int memLevel, int strategy, const char* version, int stream_size)

    int inflateInit2_(z_streamp strm, int windowBits, const char* version, int stream_size)

    int inflateBackInit_(z_streamp strm, int windowBits, unsigned char* window, const char* version, int stream_size)

    cdef struct gzFile_s:
        unsigned int have
        unsigned char* next
        long pos

    ctypedef gzFile_s* gzFile

    gzFile gzdopen(int fd, const char* mode)

    int gzbuffer(gzFile file, unsigned int size)

    int gzsetparams(gzFile file, int level, int strategy)

    int gzread(gzFile file, voidp buf, unsigned int len)

    z_size_t gzfread(voidp buf, z_size_t size, z_size_t nitems, gzFile file)

    int gzwrite(gzFile file, voidpc buf, unsigned int len)

    z_size_t gzfwrite(voidpc buf, z_size_t size, z_size_t nitems, gzFile file)

    int gzprintf(gzFile file, const char* format, ...)

    int gzputs(gzFile file, const char* s)

    char* gzgets(gzFile file, char* buf, int len)

    int gzputc(gzFile file, int c)

    int gzgetc(gzFile file)

    int gzungetc(int c, gzFile file)

    int gzflush(gzFile file, int flush)

    int gzrewind(gzFile file)

    int gzeof(gzFile file)

    int gzdirect(gzFile file)

    int gzclose(gzFile file)

    int gzclose_r(gzFile file)

    int gzclose_w(gzFile file)

    const char* gzerror(gzFile file, int* errnum)

    void gzclearerr(gzFile file)

    int gzgetc_(gzFile file)

    gzFile gzopen(const char*, const char*)

    long gzseek(gzFile, long, int)

    long gztell(gzFile)

    long gzoffset(gzFile)

    uLong adler32_combine(uLong, uLong, long)

    uLong crc32_combine(uLong, uLong, long)

    uLong crc32_combine_gen(long)

    const char* zError(int)

    int inflateSyncPoint(z_streamp)

    z_crc_t* get_crc_table()

    int inflateUndermine(z_streamp, int)

    int inflateValidate(z_streamp, int)

    unsigned long inflateCodesUsed(z_streamp)

    int inflateResetKeep(z_streamp)

    int deflateResetKeep(z_streamp)

    int gzvprintf(gzFile file, const char* format, va_list va)
