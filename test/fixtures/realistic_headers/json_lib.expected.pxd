cdef extern from "json_lib.h":

    ctypedef enum json_type:
        JSON_OBJECT
        JSON_ARRAY
        JSON_STRING
        JSON_INTEGER
        JSON_REAL
        JSON_TRUE
        JSON_FALSE
        JSON_NULL

    cdef struct json_t

    json_type json_typeof(const json_t* json)

    int json_is_object(const json_t* json)

    int json_is_array(const json_t* json)

    int json_is_string(const json_t* json)

    int json_is_integer(const json_t* json)

    int json_is_real(const json_t* json)

    int json_is_number(const json_t* json)

    int json_is_true(const json_t* json)

    int json_is_false(const json_t* json)

    int json_is_boolean(const json_t* json)

    int json_is_null(const json_t* json)

    json_t* json_incref(json_t* json)

    void json_decref(json_t* json)

    json_t* json_object()

    json_t* json_array()

    json_t* json_string(const char* value)

    json_t* json_integer(long long value)

    json_t* json_real(double value)

    json_t* json_true()

    json_t* json_false()

    json_t* json_null()

    json_t* json_object_get(const json_t* object, const char* key)

    int json_object_set_new(json_t* object, const char* key, json_t* value)

    int json_object_del(json_t* object, const char* key)

    int json_object_clear(json_t* object)

    int json_object_update(json_t* object, json_t* other)

    void* json_object_iter(json_t* object)

    void* json_object_iter_next(json_t* object, void* iter)

    const char* json_object_iter_key(void* iter)

    json_t* json_object_iter_value(void* iter)

    unsigned long json_object_size(const json_t* object)

    unsigned long json_array_size(const json_t* array)

    json_t* json_array_get(const json_t* array, unsigned long index)

    int json_array_set_new(json_t* array, unsigned long index, json_t* value)

    int json_array_append_new(json_t* array, json_t* value)

    int json_array_insert_new(json_t* array, unsigned long index, json_t* value)

    int json_array_remove(json_t* array, unsigned long index)

    int json_array_clear(json_t* array)

    const char* json_string_value(const json_t* string)

    long long json_integer_value(const json_t* integer)

    double json_real_value(const json_t* real)

    double json_number_value(const json_t* json)

    ctypedef struct json_error_t:
        int line
        int column
        int position
        char source[80]
        char text[160]

    json_t* json_loads(const char* input, unsigned long flags, json_error_t* error)

    json_t* json_loadf(void* input, unsigned long flags, json_error_t* error)

    char* json_dumps(const json_t* json, unsigned long flags)

    int json_dumpf(const json_t* json, void* output, unsigned long flags)
