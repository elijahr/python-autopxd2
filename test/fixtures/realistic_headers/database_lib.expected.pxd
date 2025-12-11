cdef extern from "database_lib.h":

    cdef struct db_connection

    ctypedef db_connection db

    cdef struct db_statement

    ctypedef db_statement db_stmt

    ctypedef int (*db_callback)(void* user_data, int ncols, char** values, char** names)

    int db_open(const char* filename, db** ppDb)

    int db_close(db* pDb)

    int db_errcode(db* pDb)

    const char* db_errmsg(db* pDb)

    int db_exec(db* pDb, const char* sql, db_callback callback, void* user_data, char** errmsg)

    int db_prepare(db* pDb, const char* sql, int nbytes, db_stmt** ppStmt, const char** pzTail)

    int db_step(db_stmt* pStmt)

    int db_finalize(db_stmt* pStmt)

    int db_reset(db_stmt* pStmt)

    int db_bind_int(db_stmt* pStmt, int idx, int value)

    int db_bind_double(db_stmt* pStmt, int idx, double value)

    ctypedef void (*_db_bind_text_destructor_ft)(void*)

    int db_bind_text(db_stmt* pStmt, int idx, const char* value, int nbytes, _db_bind_text_destructor_ft destructor)

    ctypedef void (*_db_bind_blob_destructor_ft)(void*)

    int db_bind_blob(db_stmt* pStmt, int idx, const void* value, int nbytes, _db_bind_blob_destructor_ft destructor)

    int db_bind_null(db_stmt* pStmt, int idx)

    int db_column_count(db_stmt* pStmt)

    int db_column_type(db_stmt* pStmt, int idx)

    int db_column_int(db_stmt* pStmt, int idx)

    double db_column_double(db_stmt* pStmt, int idx)

    const unsigned char* db_column_text(db_stmt* pStmt, int idx)

    const void* db_column_blob(db_stmt* pStmt, int idx)

    int db_column_bytes(db_stmt* pStmt, int idx)

    const char* db_column_name(db_stmt* pStmt, int idx)
