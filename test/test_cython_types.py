"""Tests for Cython type registries."""

from autopxd.cython_types import (
    AUTOPXD_STUB_HEADERS,
    AUTOPXD_STUB_TYPES,
    CYTHON_STDLIB_HEADERS,
    CYTHON_STDLIB_TYPES,
    LIBCPP_HEADERS,
    LIBCPP_TYPES,
    get_cython_module_for_type,
    get_libcpp_module_for_type,
    get_stub_module_for_type,
)


class TestCythonStdlibRegistry:
    """Tests for Cython standard library mappings."""

    def test_stdint_header_mapping(self):
        """stdint.h maps to libc.stdint with expected types."""
        assert "stdint.h" in CYTHON_STDLIB_HEADERS
        module, types = CYTHON_STDLIB_HEADERS["stdint.h"]
        assert module == "libc.stdint"
        assert "uint32_t" in types
        assert "int64_t" in types
        # Note: ptrdiff_t and size_t are in stddef.h/libc.stddef, not stdint.h

    def test_stddef_header_mapping(self):
        """stddef.h maps to libc.stddef with expected types."""
        assert "stddef.h" in CYTHON_STDLIB_HEADERS
        module, types = CYTHON_STDLIB_HEADERS["stddef.h"]
        assert module == "libc.stddef"
        # Note: size_t and ssize_t are Cython built-ins, not in libc.stddef mapping
        assert "ptrdiff_t" in types
        assert "wchar_t" in types

    def test_stdio_header_mapping(self):
        """stdio.h maps to libc.stdio with FILE type."""
        assert "stdio.h" in CYTHON_STDLIB_HEADERS
        module, types = CYTHON_STDLIB_HEADERS["stdio.h"]
        assert module == "libc.stdio"
        assert "FILE" in types

    def test_time_header_mapping(self):
        """time.h maps to libc.time with time types."""
        assert "time.h" in CYTHON_STDLIB_HEADERS
        module, types = CYTHON_STDLIB_HEADERS["time.h"]
        assert module == "libc.time"
        assert "time_t" in types
        assert "tm" in types

    def test_posix_unistd_mapping(self):
        """unistd.h maps to posix.unistd."""
        assert "unistd.h" in CYTHON_STDLIB_HEADERS
        module, types = CYTHON_STDLIB_HEADERS["unistd.h"]
        assert module == "posix.unistd"
        assert "pid_t" in types

    def test_python_header_mapping(self):
        """Python.h maps to cpython module."""
        assert "Python.h" in CYTHON_STDLIB_HEADERS
        module, types = CYTHON_STDLIB_HEADERS["Python.h"]
        assert module == "cpython"
        assert "PyObject" in types

    def test_reverse_lookup_populated(self):
        """CYTHON_STDLIB_TYPES reverse lookup is populated."""
        assert "uint32_t" in CYTHON_STDLIB_TYPES
        assert CYTHON_STDLIB_TYPES["uint32_t"] == ("libc.stdint", "stdint.h")
        assert "FILE" in CYTHON_STDLIB_TYPES
        assert CYTHON_STDLIB_TYPES["FILE"] == ("libc.stdio", "stdio.h")

    def test_get_cython_module_for_type(self):
        """get_cython_module_for_type returns correct module."""
        assert get_cython_module_for_type("uint32_t") == "libc.stdint"
        assert get_cython_module_for_type("FILE") == "libc.stdio"
        assert get_cython_module_for_type("unknown_type") is None


class TestAutopxdStubRegistry:
    """Tests for autopxd bundled stub mappings."""

    def test_stdarg_header_mapping(self):
        """stdarg.h maps to stdarg stub."""
        assert "stdarg.h" in AUTOPXD_STUB_HEADERS
        assert AUTOPXD_STUB_HEADERS["stdarg.h"] == "stdarg"

    def test_socket_header_mapping(self):
        """sys/socket.h maps to sys_socket stub."""
        assert "sys/socket.h" in AUTOPXD_STUB_HEADERS
        assert AUTOPXD_STUB_HEADERS["sys/socket.h"] == "sys_socket"

    def test_netinet_header_mapping(self):
        """netinet/in.h maps to netinet_in stub."""
        assert "netinet/in.h" in AUTOPXD_STUB_HEADERS
        assert AUTOPXD_STUB_HEADERS["netinet/in.h"] == "netinet_in"

    def test_type_to_stub_mapping(self):
        """AUTOPXD_STUB_TYPES maps types to stub modules."""
        assert "va_list" in AUTOPXD_STUB_TYPES
        assert AUTOPXD_STUB_TYPES["va_list"] == "stdarg"
        assert "sockaddr" in AUTOPXD_STUB_TYPES
        assert AUTOPXD_STUB_TYPES["sockaddr"] == "sys_socket"

    def test_get_stub_module_for_type(self):
        """get_stub_module_for_type returns correct module."""
        assert get_stub_module_for_type("va_list") == "stdarg"
        assert get_stub_module_for_type("sockaddr") == "sys_socket"
        assert get_stub_module_for_type("unknown_type") is None


class TestLibcppRegistry:
    """Tests for C++ STL mappings."""

    def test_vector_header_mapping(self):
        """vector header maps to libcpp.vector."""
        assert "vector" in LIBCPP_HEADERS
        module, types = LIBCPP_HEADERS["vector"]
        assert module == "libcpp.vector"
        assert "vector" in types

    def test_string_header_mapping(self):
        """string header maps to libcpp.string."""
        assert "string" in LIBCPP_HEADERS
        module, types = LIBCPP_HEADERS["string"]
        assert module == "libcpp.string"
        assert "string" in types

    def test_memory_header_mapping(self):
        """memory header maps to libcpp.memory with smart pointers."""
        assert "memory" in LIBCPP_HEADERS
        module, types = LIBCPP_HEADERS["memory"]
        assert module == "libcpp.memory"
        assert "shared_ptr" in types
        assert "unique_ptr" in types

    def test_reverse_lookup_populated(self):
        """LIBCPP_TYPES reverse lookup is populated."""
        assert "vector" in LIBCPP_TYPES
        assert LIBCPP_TYPES["vector"] == ("libcpp.vector", "vector")
        assert "shared_ptr" in LIBCPP_TYPES
        assert LIBCPP_TYPES["shared_ptr"] == ("libcpp.memory", "memory")

    def test_get_libcpp_module_for_type(self):
        """get_libcpp_module_for_type returns correct module."""
        assert get_libcpp_module_for_type("vector") == "libcpp.vector"
        assert get_libcpp_module_for_type("shared_ptr") == "libcpp.memory"
        assert get_libcpp_module_for_type("unknown_type") is None
