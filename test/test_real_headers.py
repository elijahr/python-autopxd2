"""Tests using real library headers.

These tests verify that autopxd can parse actual headers from popular
C libraries like zlib and jansson.

Note: These tests use real header files copied into test/real_headers/.
They require the libclang backend since real-world headers often contain
features that pycparser cannot handle without preprocessing.
"""

import os
import subprocess
import sys

import pytest

from autopxd.backends import get_backend
from autopxd.ir import Enum, Function, Struct
from autopxd.ir_writer import write_pxd
from test.assertions import assert_header_pxd_equals

# Directory containing real header files
REAL_HEADERS_DIR = os.path.join(os.path.dirname(__file__), "real_headers")


def _get_system_include_args() -> list[str]:
    """Get system include paths for libclang.

    libclang doesn't automatically know about system headers, so we need
    to provide the paths explicitly. This includes both the SDK headers
    and the clang builtin headers (for stdarg.h, stddef.h, etc.).
    """
    args = []

    # Get include paths from clang -v output
    try:
        result = subprocess.run(
            ["clang", "-v", "-x", "c", "-E", "/dev/null"],
            capture_output=True,
            text=True,
        )
        # Parse the include paths from stderr
        in_includes = False
        for line in result.stderr.splitlines():
            if "#include <...> search starts here:" in line:
                in_includes = True
                continue
            if in_includes:
                if line.startswith("End of search list"):
                    break
                path = line.strip()
                if path and not path.endswith("(framework directory)"):
                    args.extend(["-I", path])
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Fallback: if we didn't get any paths, try platform-specific defaults
    if not args:
        if sys.platform == "darwin":
            try:
                sdk_path = subprocess.check_output(
                    ["xcrun", "--show-sdk-path"], text=True, stderr=subprocess.DEVNULL
                ).strip()
                args.extend(["-isysroot", sdk_path])
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        elif sys.platform == "linux":
            for path in ["/usr/include", "/usr/local/include"]:
                if os.path.isdir(path):
                    args.extend(["-I", path])

    return args


# These tests require libclang - use pytest -m "not libclang" to exclude
pytestmark = pytest.mark.libclang


@pytest.fixture
def libclang_backend():
    """Provide the libclang backend."""
    return get_backend("libclang")


class TestZlibHeader:
    """Test parsing the real zlib.h header."""

    @pytest.fixture
    def zlib_header(self, libclang_backend):
        """Parse zlib.h and return the IR."""
        zlib_path = os.path.join(REAL_HEADERS_DIR, "zlib.h")
        if not os.path.exists(zlib_path):
            pytest.skip("zlib.h not found in test/real_headers/")

        with open(zlib_path, encoding="utf-8") as f:
            code = f.read()

        # zlib.h includes zconf.h and system headers
        extra_args = [f"-I{REAL_HEADERS_DIR}"] + _get_system_include_args()
        return libclang_backend.parse(
            code,
            "zlib.h",
            extra_args=extra_args,
        )

    def test_parses_without_error(self, zlib_header):
        """Verify zlib.h parses successfully."""
        assert zlib_header is not None
        assert len(zlib_header.declarations) > 0

    def test_finds_z_stream_struct(self, zlib_header):
        """Verify we find the z_stream_s struct."""
        structs = [d for d in zlib_header.declarations if isinstance(d, Struct)]
        struct_names = {s.name for s in structs}
        assert "z_stream_s" in struct_names

    def test_finds_core_functions(self, zlib_header):
        """Verify we find zlib's core compression functions."""
        functions = [d for d in zlib_header.declarations if isinstance(d, Function)]
        func_names = {f.name for f in functions}

        # Core zlib functions
        expected = {"deflate", "inflate", "deflateInit_", "inflateInit_"}
        found = expected & func_names
        assert len(found) > 0, f"Expected some of {expected}, found functions: {func_names}"

    def test_pxd_matches_expected(self, zlib_header):
        """Verify generated pxd matches expected output.

        Note: Cython compilation validation is not possible for zlib because
        it uses macro-based type aliases (voidpf, Bytef, uInt, etc.) defined
        in zconf.h via #define rather than typedef. These macros are expanded
        by libclang but the alias names are used in the output, which Cython
        cannot resolve without the actual header.
        """
        expected_path = os.path.join(REAL_HEADERS_DIR, "zlib.expected.pxd")
        if not os.path.exists(expected_path):
            pytest.skip("zlib.expected.pxd not found")

        with open(expected_path, encoding="utf-8") as f:
            expected = f.read()

        actual = write_pxd(zlib_header)

        assert actual == expected, (
            f"\n{'='*60}\nEXPECTED ({os.path.basename(expected_path)}):\n{'='*60}\n{repr(expected)}\n"
            f"{'='*60}\nACTUAL:\n{'='*60}\n{repr(actual)}\n{'='*60}"
        )
        # NO Cython validation - see docstring for why


class TestJanssonHeader:
    """Test parsing the real jansson.h header."""

    @pytest.fixture
    def jansson_header(self, libclang_backend):
        """Parse jansson.h and return the IR."""
        jansson_path = os.path.join(REAL_HEADERS_DIR, "jansson.h")
        if not os.path.exists(jansson_path):
            pytest.skip("jansson.h not found in test/real_headers/")

        with open(jansson_path, encoding="utf-8") as f:
            code = f.read()

        # jansson.h includes jansson_config.h and system headers
        extra_args = [f"-I{REAL_HEADERS_DIR}"] + _get_system_include_args()
        return libclang_backend.parse(
            code,
            "jansson.h",
            extra_args=extra_args,
        )

    def test_parses_without_error(self, jansson_header):
        """Verify jansson.h parses successfully."""
        assert jansson_header is not None
        assert len(jansson_header.declarations) > 0

    def test_finds_json_type_enum(self, jansson_header):
        """Verify we find the json_type enum."""
        enums = [d for d in jansson_header.declarations if isinstance(d, Enum)]
        enum_names = {e.name for e in enums}
        assert "json_type" in enum_names

        # Find the json_type enum and check its values
        json_type_enum = next(e for e in enums if e.name == "json_type")
        value_names = {v.name for v in json_type_enum.values}
        assert "JSON_OBJECT" in value_names
        assert "JSON_ARRAY" in value_names
        assert "JSON_STRING" in value_names

    def test_finds_json_t_struct(self, jansson_header):
        """Verify we find the json_t struct."""
        structs = [d for d in jansson_header.declarations if isinstance(d, Struct)]
        struct_names = {s.name for s in structs}
        assert "json_t" in struct_names

    def test_finds_core_functions(self, jansson_header):
        """Verify we find jansson's core functions."""
        functions = [d for d in jansson_header.declarations if isinstance(d, Function)]
        func_names = {f.name for f in functions}

        # Core jansson functions
        expected = {"json_object", "json_array", "json_string", "json_loads", "json_dumps"}
        found = expected & func_names
        assert len(found) >= 3, f"Expected some of {expected}, found functions: {func_names}"

    def test_pxd_matches_expected(self, jansson_header):
        """Verify generated pxd matches expected output.

        Note: Cython compilation validation is not possible for jansson because
        it uses va_list from <stdarg.h> and FILE from <stdio.h>. These system
        types are not defined in the generated pxd, so Cython cannot resolve them.
        """
        expected_path = os.path.join(REAL_HEADERS_DIR, "jansson.expected.pxd")
        if not os.path.exists(expected_path):
            pytest.skip("jansson.expected.pxd not found")

        with open(expected_path, encoding="utf-8") as f:
            expected = f.read()

        actual = write_pxd(jansson_header)

        assert actual == expected, (
            f"\n{'='*60}\nEXPECTED ({os.path.basename(expected_path)}):\n{'='*60}\n{repr(expected)}\n"
            f"{'='*60}\nACTUAL:\n{'='*60}\n{repr(actual)}\n{'='*60}"
        )
        # NO Cython validation - see docstring for why


class TestSimpleCHeader:
    """Test parsing simple_c.h with pycparser backend."""

    @pytest.fixture
    def simple_c_header(self):
        """Parse simple_c.h with pycparser and return the IR."""
        c_path = os.path.join(REAL_HEADERS_DIR, "simple_c.h")
        if not os.path.exists(c_path):
            pytest.skip("simple_c.h not found in test/real_headers/")

        with open(c_path, encoding="utf-8") as f:
            code = f.read()

        backend = get_backend("pycparser")
        return backend.parse(code, "simple_c.h")

    def test_parses_without_error(self, simple_c_header):
        """Verify simple_c.h parses successfully."""
        assert simple_c_header is not None
        assert len(simple_c_header.declarations) > 0

    def test_pxd_matches_expected(self, simple_c_header, tmp_path):
        """Verify generated pxd matches expected output and compiles."""
        expected_path = os.path.join(REAL_HEADERS_DIR, "simple_c.expected.pxd")
        if not os.path.exists(expected_path):
            pytest.skip("simple_c.expected.pxd not found")

        assert_header_pxd_equals(
            simple_c_header,
            expected_path,
            tmp_path,
        )

    def test_finds_enums(self, simple_c_header):
        """Verify we find both enums."""
        enums = [d for d in simple_c_header.declarations if isinstance(d, Enum)]
        enum_names = {e.name for e in enums}
        assert "ErrorCode" in enum_names
        assert "LogLevel" in enum_names

    def test_finds_structs(self, simple_c_header):
        """Verify we find all structs."""
        structs = [d for d in simple_c_header.declarations if isinstance(d, Struct)]
        struct_names = {s.name for s in structs}
        assert "Point" in struct_names
        assert "Size" in struct_names
        assert "Buffer" in struct_names

    def test_finds_functions(self, simple_c_header):
        """Verify we find key functions."""
        functions = [d for d in simple_c_header.declarations if isinstance(d, Function)]
        func_names = {f.name for f in functions}
        assert "point_create" in func_names
        assert "buffer_new" in func_names
        assert "log_printf" in func_names


class TestCppHeaders:
    """Test parsing C++ headers."""

    @pytest.fixture
    def simple_cpp_header(self, libclang_backend):
        """Parse simple_cpp.hpp and return the IR."""
        hpp_path = os.path.join(REAL_HEADERS_DIR, "simple_cpp.hpp")
        if not os.path.exists(hpp_path):
            pytest.skip("simple_cpp.hpp not found in test/real_headers/")

        with open(hpp_path, encoding="utf-8") as f:
            code = f.read()

        extra_args = ["-x", "c++", "-std=c++11"] + _get_system_include_args()
        return libclang_backend.parse(
            code,
            "simple_cpp.hpp",
            extra_args=extra_args,
        )

    def test_parses_cpp_without_error(self, simple_cpp_header):
        """Verify C++ header parses successfully."""
        assert simple_cpp_header is not None
        assert len(simple_cpp_header.declarations) > 0

    def test_pxd_matches_expected(self, simple_cpp_header, tmp_path):
        """Verify generated pxd matches expected output and compiles."""
        expected_path = os.path.join(REAL_HEADERS_DIR, "simple_cpp.expected.pxd")
        if not os.path.exists(expected_path):
            pytest.skip("simple_cpp.expected.pxd not found")

        assert_header_pxd_equals(
            simple_cpp_header,
            expected_path,
            tmp_path,
            cplus=True,
        )


class TestHeaderDiscovery:
    """Tests for discovering and validating real headers."""

    def test_real_headers_directory_exists(self):
        """Verify the real_headers directory exists."""
        assert os.path.isdir(REAL_HEADERS_DIR), f"Missing directory: {REAL_HEADERS_DIR}"

    def test_has_required_headers(self):
        """Verify we have the expected header files."""
        expected_headers = ["zlib.h", "zconf.h", "jansson.h", "jansson_config.h"]
        for header in expected_headers:
            path = os.path.join(REAL_HEADERS_DIR, header)
            assert os.path.exists(path), f"Missing header: {header}"

    def test_headers_are_valid_files(self):
        """Verify header files have content."""
        for filename in os.listdir(REAL_HEADERS_DIR):
            if filename.endswith((".h", ".hpp")):
                path = os.path.join(REAL_HEADERS_DIR, filename)
                size = os.path.getsize(path)
                # Real headers should be more than just a few bytes
                assert size > 100, f"{filename} seems too small ({size} bytes)"
