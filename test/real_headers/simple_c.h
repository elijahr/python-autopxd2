/**
 * simple_c.h - A minimal C header for testing autopxd2
 *
 * This header demonstrates common C patterns:
 * - Enums (named and typedef'd)
 * - Structs (named and typedef'd)
 * - Function declarations
 * - Function pointer typedefs
 * - Global variables
 */

#ifndef SIMPLE_C_H
#define SIMPLE_C_H

/* Error codes */
typedef enum {
    ERR_OK = 0,
    ERR_INVALID = -1,
    ERR_NOMEM = -2
} ErrorCode;

/* Named enum */
enum LogLevel {
    LOG_DEBUG,
    LOG_INFO,
    LOG_WARN,
    LOG_ERROR
};

/* Simple struct */
struct Point {
    int x;
    int y;
};

/* Typedef'd struct */
typedef struct {
    int width;
    int height;
} Size;

/* Struct with pointer fields */
typedef struct Buffer {
    char *data;
    unsigned int length;
    unsigned int capacity;
} Buffer;

/* Function pointer typedef */
typedef void (*Callback)(void *user_data);
typedef int (*Comparator)(const void *a, const void *b);

/* Function declarations */
struct Point point_create(int x, int y);
int point_distance(struct Point a, struct Point b);

Buffer *buffer_new(unsigned int capacity);
void buffer_free(Buffer *buf);
int buffer_append(Buffer *buf, const char *data, unsigned int len);

void set_log_level(enum LogLevel level);
void log_message(enum LogLevel level, const char *message);

/* Variadic function */
void log_printf(enum LogLevel level, const char *fmt, ...);

/* Global variable */
extern int global_debug_enabled;

#endif /* SIMPLE_C_H */
