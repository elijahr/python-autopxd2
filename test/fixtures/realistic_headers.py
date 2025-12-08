# pylint: disable=line-too-long
"""Realistic header fixtures for testing parser backends.

These fixtures capture common patterns found in real C/C++ libraries
without external dependencies, making them suitable for automated testing.

Patterns inspired by:
- zlib: compression library with callbacks and opaque handles
- SQLite: database library with statement handles and callbacks
- jansson: JSON library with tagged unions and reference counting
"""

# =============================================================================
# Pattern: Library with version info, callbacks, and opaque handles (zlib-like)
# =============================================================================

COMPRESSION_LIB = """
/* Compression library header - similar to zlib patterns */

/* Version information */
#define COMPRESS_VERSION "1.0.0"
#define COMPRESS_VERNUM 0x1000

/* Type definitions */
typedef unsigned char Byte;
typedef unsigned int uInt;
typedef unsigned long uLong;
typedef void* voidp;

/* Callback function types */
typedef voidp (*alloc_func)(voidp opaque, uInt items, uInt size);
typedef void (*free_func)(voidp opaque, voidp address);

/* Forward declaration for internal state */
struct internal_state;

/* Main stream structure */
typedef struct compress_stream_s {
    Byte* next_in;      /* next input byte */
    uInt avail_in;      /* number of bytes available at next_in */
    uLong total_in;     /* total number of input bytes read so far */

    Byte* next_out;     /* next output byte */
    uInt avail_out;     /* remaining free space at next_out */
    uLong total_out;    /* total number of bytes output so far */

    const char* msg;    /* last error message, NULL if no error */
    struct internal_state* state;  /* opaque internal state */

    alloc_func zalloc;  /* used to allocate internal state */
    free_func zfree;    /* used to free internal state */
    voidp opaque;       /* private data for callbacks */
} compress_stream;

/* Error codes */
typedef enum {
    COMPRESS_OK = 0,
    COMPRESS_STREAM_END = 1,
    COMPRESS_NEED_DICT = 2,
    COMPRESS_ERRNO = -1,
    COMPRESS_STREAM_ERROR = -2,
    COMPRESS_DATA_ERROR = -3,
    COMPRESS_MEM_ERROR = -4,
    COMPRESS_BUF_ERROR = -5
} compress_status;

/* Compression levels */
#define COMPRESS_NO_COMPRESSION 0
#define COMPRESS_BEST_SPEED 1
#define COMPRESS_BEST_COMPRESSION 9
#define COMPRESS_DEFAULT_COMPRESSION -1

/* API functions */
const char* compress_version(void);
int compress_init(compress_stream* strm, int level);
int compress(compress_stream* strm, int flush);
int compress_end(compress_stream* strm);
int decompress_init(compress_stream* strm);
int decompress(compress_stream* strm, int flush);
int decompress_end(compress_stream* strm);

/* Utility functions */
uLong compress_bound(uLong sourceLen);
int compress_buffer(Byte* dest, uLong* destLen, const Byte* source, uLong sourceLen);
int decompress_buffer(Byte* dest, uLong* destLen, const Byte* source, uLong sourceLen);
"""

# =============================================================================
# Pattern: Database library with statement handles (SQLite-like)
# =============================================================================

DATABASE_LIB = """
/* Database library header - similar to SQLite patterns */

/* Opaque database connection handle */
typedef struct db_connection db;

/* Opaque prepared statement handle */
typedef struct db_statement db_stmt;

/* Result codes */
#define DB_OK 0
#define DB_ERROR 1
#define DB_BUSY 5
#define DB_LOCKED 6
#define DB_NOMEM 7
#define DB_READONLY 8
#define DB_DONE 101
#define DB_ROW 100

/* Data types */
#define DB_INTEGER 1
#define DB_FLOAT 2
#define DB_TEXT 3
#define DB_BLOB 4
#define DB_NULL 5

/* Callback for query results */
typedef int (*db_callback)(void* user_data, int ncols, char** values, char** names);

/* Connection management */
int db_open(const char* filename, db** ppDb);
int db_close(db* pDb);

/* Error handling */
int db_errcode(db* pDb);
const char* db_errmsg(db* pDb);

/* Simple query execution */
int db_exec(db* pDb, const char* sql, db_callback callback, void* user_data, char** errmsg);

/* Prepared statements */
int db_prepare(db* pDb, const char* sql, int nbytes, db_stmt** ppStmt, const char** pzTail);
int db_step(db_stmt* pStmt);
int db_finalize(db_stmt* pStmt);
int db_reset(db_stmt* pStmt);

/* Parameter binding */
int db_bind_int(db_stmt* pStmt, int idx, int value);
int db_bind_double(db_stmt* pStmt, int idx, double value);
int db_bind_text(db_stmt* pStmt, int idx, const char* value, int nbytes, void (*destructor)(void*));
int db_bind_blob(db_stmt* pStmt, int idx, const void* value, int nbytes, void (*destructor)(void*));
int db_bind_null(db_stmt* pStmt, int idx);

/* Column accessors */
int db_column_count(db_stmt* pStmt);
int db_column_type(db_stmt* pStmt, int idx);
int db_column_int(db_stmt* pStmt, int idx);
double db_column_double(db_stmt* pStmt, int idx);
const unsigned char* db_column_text(db_stmt* pStmt, int idx);
const void* db_column_blob(db_stmt* pStmt, int idx);
int db_column_bytes(db_stmt* pStmt, int idx);
const char* db_column_name(db_stmt* pStmt, int idx);
"""

# =============================================================================
# Pattern: JSON library with tagged unions (jansson-like)
# =============================================================================

JSON_LIB = """
/* JSON library header - similar to jansson patterns */

/* JSON value types */
typedef enum {
    JSON_OBJECT,
    JSON_ARRAY,
    JSON_STRING,
    JSON_INTEGER,
    JSON_REAL,
    JSON_TRUE,
    JSON_FALSE,
    JSON_NULL
} json_type;

/* Opaque JSON value - reference counted */
typedef struct json_t json_t;

/* Type checking macros would be here, but we define functions instead */

/* Type checking functions */
json_type json_typeof(const json_t* json);
int json_is_object(const json_t* json);
int json_is_array(const json_t* json);
int json_is_string(const json_t* json);
int json_is_integer(const json_t* json);
int json_is_real(const json_t* json);
int json_is_number(const json_t* json);
int json_is_true(const json_t* json);
int json_is_false(const json_t* json);
int json_is_boolean(const json_t* json);
int json_is_null(const json_t* json);

/* Reference counting */
json_t* json_incref(json_t* json);
void json_decref(json_t* json);

/* Object creation */
json_t* json_object(void);
json_t* json_array(void);
json_t* json_string(const char* value);
json_t* json_integer(long long value);
json_t* json_real(double value);
json_t* json_true(void);
json_t* json_false(void);
json_t* json_null(void);

/* Object accessors */
json_t* json_object_get(const json_t* object, const char* key);
int json_object_set_new(json_t* object, const char* key, json_t* value);
int json_object_del(json_t* object, const char* key);
int json_object_clear(json_t* object);
int json_object_update(json_t* object, json_t* other);
void* json_object_iter(json_t* object);
void* json_object_iter_next(json_t* object, void* iter);
const char* json_object_iter_key(void* iter);
json_t* json_object_iter_value(void* iter);
unsigned long json_object_size(const json_t* object);

/* Array accessors */
unsigned long json_array_size(const json_t* array);
json_t* json_array_get(const json_t* array, unsigned long index);
int json_array_set_new(json_t* array, unsigned long index, json_t* value);
int json_array_append_new(json_t* array, json_t* value);
int json_array_insert_new(json_t* array, unsigned long index, json_t* value);
int json_array_remove(json_t* array, unsigned long index);
int json_array_clear(json_t* array);

/* Value extraction */
const char* json_string_value(const json_t* string);
long long json_integer_value(const json_t* integer);
double json_real_value(const json_t* real);
double json_number_value(const json_t* json);

/* Parsing and serialization */
typedef struct {
    int line;
    int column;
    int position;
    char source[80];
    char text[160];
} json_error_t;

json_t* json_loads(const char* input, unsigned long flags, json_error_t* error);
json_t* json_loadf(void* input, unsigned long flags, json_error_t* error);
char* json_dumps(const json_t* json, unsigned long flags);
int json_dumpf(const json_t* json, void* output, unsigned long flags);

/* Serialization flags */
#define JSON_INDENT(n) ((n) & 0x1F)
#define JSON_COMPACT 0x20
#define JSON_ENSURE_ASCII 0x40
#define JSON_SORT_KEYS 0x80
#define JSON_PRESERVE_ORDER 0x100
"""

# =============================================================================
# Pattern: Complex struct with nested types and bitfields (network protocol)
# =============================================================================

NETWORK_PROTOCOL = """
/* Network protocol header - complex struct patterns */

typedef unsigned char uint8_t;
typedef unsigned short uint16_t;
typedef unsigned int uint32_t;
typedef unsigned long long uint64_t;

/* Protocol version */
#define PROTOCOL_VERSION_MAJOR 2
#define PROTOCOL_VERSION_MINOR 1

/* Message types */
typedef enum msg_type {
    MSG_CONNECT = 0x01,
    MSG_DISCONNECT = 0x02,
    MSG_PING = 0x03,
    MSG_PONG = 0x04,
    MSG_DATA = 0x10,
    MSG_ACK = 0x11,
    MSG_ERROR = 0xFF
} msg_type_t;

/* Flags for message header */
#define MSG_FLAG_ENCRYPTED 0x01
#define MSG_FLAG_COMPRESSED 0x02
#define MSG_FLAG_FRAGMENTED 0x04
#define MSG_FLAG_LAST_FRAGMENT 0x08

/* Message header (fixed size) */
typedef struct msg_header {
    uint8_t version;
    uint8_t type;
    uint8_t flags;
    uint8_t reserved;
    uint32_t sequence;
    uint32_t length;
    uint32_t checksum;
} msg_header_t;

/* Connection request */
typedef struct connect_request {
    msg_header_t header;
    char client_id[64];
    uint16_t port;
    uint16_t padding;
    uint32_t capabilities;
} connect_request_t;

/* Data message with variable payload */
typedef struct data_message {
    msg_header_t header;
    uint32_t channel_id;
    uint32_t fragment_offset;
    uint8_t payload[];  /* Flexible array member */
} data_message_t;

/* Error response */
typedef struct error_response {
    msg_header_t header;
    uint32_t error_code;
    char message[256];
} error_response_t;

/* Union for message parsing */
typedef union msg_payload {
    connect_request_t connect;
    data_message_t data;
    error_response_t error;
} msg_payload_t;

/* Connection handle */
typedef struct connection connection_t;

/* Callback types */
typedef void (*on_connect_cb)(connection_t* conn, void* user_data);
typedef void (*on_disconnect_cb)(connection_t* conn, int reason, void* user_data);
typedef void (*on_message_cb)(connection_t* conn, const msg_header_t* header, const void* payload, void* user_data);
typedef void (*on_error_cb)(connection_t* conn, int error_code, const char* message, void* user_data);

/* Event callbacks structure */
typedef struct callbacks {
    on_connect_cb on_connect;
    on_disconnect_cb on_disconnect;
    on_message_cb on_message;
    on_error_cb on_error;
    void* user_data;
} callbacks_t;

/* API functions */
connection_t* conn_create(const char* host, uint16_t port);
void conn_destroy(connection_t* conn);
int conn_connect(connection_t* conn, const callbacks_t* callbacks);
int conn_disconnect(connection_t* conn);
int conn_send(connection_t* conn, uint32_t channel, const void* data, uint32_t length);
int conn_poll(connection_t* conn, int timeout_ms);
int conn_is_connected(const connection_t* conn);
"""

# =============================================================================
# Pattern: C++ header with classes and templates (simplified)
# =============================================================================

CPP_CONTAINER = """
/* C++ container header - class patterns for Cython wrapping */

struct Point {
    int x;
    int y;
};

class Vector2D {
public:
    double x;
    double y;

    double magnitude() const;
    void normalize();
    Vector2D operator+(const Vector2D& other) const;
    Vector2D operator-(const Vector2D& other) const;
    double dot(const Vector2D& other) const;
};

class Rectangle {
public:
    Point origin;
    int width;
    int height;

    int area() const;
    bool contains(const Point& p) const;
    bool intersects(const Rectangle& other) const;
};

/* Factory functions */
Vector2D make_vector(double x, double y);
Rectangle make_rectangle(int x, int y, int w, int h);

/* Utility functions */
double distance(const Point& a, const Point& b);
double distance(const Vector2D& a, const Vector2D& b);
"""

# =============================================================================
# Collection of all fixtures for parameterized testing
# =============================================================================

ALL_FIXTURES = {
    "compression_lib": COMPRESSION_LIB,
    "database_lib": DATABASE_LIB,
    "json_lib": JSON_LIB,
    "network_protocol": NETWORK_PROTOCOL,
    "cpp_container": CPP_CONTAINER,
}

# C-only fixtures (compatible with pycparser after preprocessing)
C_FIXTURES = {
    "compression_lib": COMPRESSION_LIB,
    "database_lib": DATABASE_LIB,
    "json_lib": JSON_LIB,
    "network_protocol": NETWORK_PROTOCOL,
}

# C++ fixtures (only libclang)
CPP_FIXTURES = {
    "cpp_container": CPP_CONTAINER,
}
