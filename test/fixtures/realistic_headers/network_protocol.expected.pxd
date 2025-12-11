from libc.stdint cimport uint16_t, uint32_t, uint8_t

cdef extern from "network_protocol.h":

    ctypedef unsigned char uint8_t

    ctypedef unsigned short uint16_t

    ctypedef unsigned int uint32_t

    ctypedef unsigned long long uint64_t

    cpdef enum msg_type:
        MSG_CONNECT
        MSG_DISCONNECT
        MSG_PING
        MSG_PONG
        MSG_DATA
        MSG_ACK
        MSG_ERROR

    ctypedef msg_type msg_type_t

    cdef struct msg_header:
        uint8_t version
        uint8_t type
        uint8_t flags
        uint8_t reserved
        uint32_t sequence
        uint32_t length
        uint32_t checksum

    ctypedef msg_header msg_header_t

    cdef struct connect_request:
        msg_header_t header
        char client_id[64]
        uint16_t port
        uint16_t padding
        uint32_t capabilities

    ctypedef connect_request connect_request_t

    cdef struct data_message:
        msg_header_t header
        uint32_t channel_id
        uint32_t fragment_offset
        uint8_t payload[]

    ctypedef data_message data_message_t

    cdef struct error_response:
        msg_header_t header
        uint32_t error_code
        char message[256]

    ctypedef error_response error_response_t

    cdef union msg_payload:
        connect_request_t connect
        data_message_t data
        error_response_t error

    ctypedef msg_payload msg_payload_t

    cdef struct connection

    ctypedef connection connection_t

    ctypedef void (*on_connect_cb)(connection_t* conn, void* user_data)

    ctypedef void (*on_disconnect_cb)(connection_t* conn, int reason, void* user_data)

    ctypedef void (*on_message_cb)(connection_t* conn, const msg_header_t* header, const void* payload, void* user_data)

    ctypedef void (*on_error_cb)(connection_t* conn, int error_code, const char* message, void* user_data)

    cdef struct callbacks:
        on_connect_cb on_connect
        on_disconnect_cb on_disconnect
        on_message_cb on_message
        on_error_cb on_error
        void* user_data

    ctypedef callbacks callbacks_t

    connection_t* conn_create(const char* host, uint16_t port)

    void conn_destroy(connection_t* conn)

    int conn_connect(connection_t* conn, const callbacks_t* callbacks)

    int conn_disconnect(connection_t* conn)

    int conn_send(connection_t* conn, uint32_t channel, const void* data, uint32_t length)

    int conn_poll(connection_t* conn, int timeout_ms)

    int conn_is_connected(const connection_t* conn)
