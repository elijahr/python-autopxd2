from libc.stdio cimport FILE
from autopxd.stubs.stdarg cimport va_list

cdef extern from "jansson.h":

    ctypedef long long json_int_t

    ctypedef size_t (*json_load_callback_t)(void*, size_t, void*)

    ctypedef int (*json_dump_callback_t)(const char*, size_t, void*)

    ctypedef void* (*json_malloc_t)(size_t)

    ctypedef void (*json_free_t)(void*)



    int JANSSON_MAJOR_VERSION

    int JANSSON_MINOR_VERSION

    int JANSSON_MICRO_VERSION

    const char* JANSSON_VERSION

    int JANSSON_VERSION_HEX

    int JANSSON_THREAD_SAFE_REFCOUNT

    const char* JSON_INTEGER_FORMAT

    int json_auto_t

    int JSON_ERROR_TEXT_LENGTH

    int JSON_ERROR_SOURCE_LENGTH

    int JSON_VALIDATE_ONLY

    int JSON_STRICT

    int JSON_REJECT_DUPLICATES

    int JSON_DISABLE_EOF_CHECK

    int JSON_DECODE_ANY

    int JSON_DECODE_INT_AS_REAL

    int JSON_ALLOW_NUL

    int JSON_MAX_INDENT

    int JSON_COMPACT

    int JSON_ENSURE_ASCII

    int JSON_SORT_KEYS

    int JSON_PRESERVE_ORDER

    int JSON_ENCODE_ANY

    int JSON_ESCAPE_SLASH

    int JSON_EMBED

    cdef enum json_type:
        JSON_OBJECT
        JSON_ARRAY
        JSON_STRING
        JSON_INTEGER
        JSON_REAL
        JSON_TRUE
        JSON_FALSE
        JSON_NULL

    cdef enum json_error_code:
        json_error_unknown
        json_error_out_of_memory
        json_error_stack_overflow
        json_error_cannot_open_file
        json_error_invalid_argument
        json_error_invalid_utf8
        json_error_premature_end_of_input
        json_error_end_of_input_expected
        json_error_invalid_syntax
        json_error_invalid_format
        json_error_wrong_type
        json_error_null_character
        json_error_null_value
        json_error_null_byte_in_key
        json_error_duplicate_key
        json_error_numeric_overflow
        json_error_item_not_found
        json_error_index_out_of_range


    ctypedef struct json_error_t:
        int line
        int column
        int position
        char source[80]
        char text[160]

    ctypedef struct json_t:
        json_type type
        size_t refcount


    json_t* json_object()

    json_t* json_array()

    json_t* json_string(const char* value)

    json_t* json_stringn(const char* value, size_t len)

    json_t* json_string_nocheck(const char* value)

    json_t* json_stringn_nocheck(const char* value, size_t len)

    json_t* json_integer(json_int_t value)

    json_t* json_real(double value)

    json_t* json_true()

    json_t* json_false()

    json_t* json_null()

    json_t* json_incref(json_t* json)

    void json_delete(json_t* json)

    void json_decref(json_t* json)

    void json_decrefp(json_t** json)

    json_error_code json_error_code(json_error_t* e)

    void json_object_seed(size_t seed)

    size_t json_object_size(json_t* object)

    json_t* json_object_get(json_t* object, const char* key)

    json_t* json_object_getn(json_t* object, const char* key, size_t key_len)

    int json_object_set_new(json_t* object, const char* key, json_t* value)

    int json_object_setn_new(json_t* object, const char* key, size_t key_len, json_t* value)

    int json_object_set_new_nocheck(json_t* object, const char* key, json_t* value)

    int json_object_setn_new_nocheck(json_t* object, const char* key, size_t key_len, json_t* value)

    int json_object_del(json_t* object, const char* key)

    int json_object_deln(json_t* object, const char* key, size_t key_len)

    int json_object_clear(json_t* object)

    int json_object_update(json_t* object, json_t* other)

    int json_object_update_existing(json_t* object, json_t* other)

    int json_object_update_missing(json_t* object, json_t* other)

    int json_object_update_recursive(json_t* object, json_t* other)

    void* json_object_iter(json_t* object)

    void* json_object_iter_at(json_t* object, const char* key)

    void* json_object_key_to_iter(const char* key)

    void* json_object_iter_next(json_t* object, void* iter)

    const char* json_object_iter_key(void* iter)

    size_t json_object_iter_key_len(void* iter)

    json_t* json_object_iter_value(void* iter)

    int json_object_iter_set_new(json_t* object, void* iter, json_t* value)

    int json_object_set(json_t* object, const char* key, json_t* value)

    int json_object_setn(json_t* object, const char* key, size_t key_len, json_t* value)

    int json_object_set_nocheck(json_t* object, const char* key, json_t* value)

    int json_object_setn_nocheck(json_t* object, const char* key, size_t key_len, json_t* value)

    int json_object_iter_set(json_t* object, void* iter, json_t* value)

    int json_object_update_new(json_t* object, json_t* other)

    int json_object_update_existing_new(json_t* object, json_t* other)

    int json_object_update_missing_new(json_t* object, json_t* other)

    size_t json_array_size(json_t* array)

    json_t* json_array_get(json_t* array, size_t index)

    int json_array_set_new(json_t* array, size_t index, json_t* value)

    int json_array_append_new(json_t* array, json_t* value)

    int json_array_insert_new(json_t* array, size_t index, json_t* value)

    int json_array_remove(json_t* array, size_t index)

    int json_array_clear(json_t* array)

    int json_array_extend(json_t* array, json_t* other)

    int json_array_set(json_t* array, size_t ind, json_t* value)

    int json_array_append(json_t* array, json_t* value)

    int json_array_insert(json_t* array, size_t ind, json_t* value)

    const char* json_string_value(json_t* string)

    size_t json_string_length(json_t* string)

    json_int_t json_integer_value(json_t* integer)

    double json_real_value(json_t* real)

    double json_number_value(json_t* json)

    int json_string_set(json_t* string, const char* value)

    int json_string_setn(json_t* string, const char* value, size_t len)

    int json_string_set_nocheck(json_t* string, const char* value)

    int json_string_setn_nocheck(json_t* string, const char* value, size_t len)

    int json_integer_set(json_t* integer, json_int_t value)

    int json_real_set(json_t* real, double value)

    json_t* json_pack(const char* fmt, ...)

    json_t* json_pack_ex(json_error_t* error, size_t flags, const char* fmt, ...)

    json_t* json_vpack_ex(json_error_t* error, size_t flags, const char* fmt, va_list ap)

    int json_unpack(json_t* root, const char* fmt, ...)

    int json_unpack_ex(json_t* root, json_error_t* error, size_t flags, const char* fmt, ...)

    int json_vunpack_ex(json_t* root, json_error_t* error, size_t flags, const char* fmt, va_list ap)

    json_t* json_sprintf(const char* fmt, ...)

    json_t* json_vsprintf(const char* fmt, va_list ap)

    int json_equal(json_t* value1, json_t* value2)

    json_t* json_copy(json_t* value)

    json_t* json_deep_copy(json_t* value)

    json_t* json_loads(const char* input, size_t flags, json_error_t* error)

    json_t* json_loadb(const char* buffer, size_t buflen, size_t flags, json_error_t* error)

    json_t* json_loadf(FILE* input, size_t flags, json_error_t* error)

    json_t* json_loadfd(int input, size_t flags, json_error_t* error)

    json_t* json_load_file(const char* path, size_t flags, json_error_t* error)

    json_t* json_load_callback(json_load_callback_t callback, void* data, size_t flags, json_error_t* error)

    char* json_dumps(json_t* json, size_t flags)

    size_t json_dumpb(json_t* json, char* buffer, size_t size, size_t flags)

    int json_dumpf(json_t* json, FILE* output, size_t flags)

    int json_dumpfd(json_t* json, int output, size_t flags)

    int json_dump_file(json_t* json, const char* path, size_t flags)

    int json_dump_callback(json_t* json, json_dump_callback_t callback, void* data, size_t flags)

    void json_set_alloc_funcs(json_malloc_t malloc_fn, json_free_t free_fn)

    void json_get_alloc_funcs(json_malloc_t* malloc_fn, json_free_t* free_fn)

    const char* jansson_version_str()

    int jansson_version_cmp(int major, int minor, int micro)
