"""Tests using real library headers.

These tests verify that autopxd can parse actual headers from popular
C libraries like zlib and jansson.

Library headers (zlib.h, jansson.h) are downloaded dynamically and cached
in test/.header_cache/. Test fixture headers (simple_c.h, templates.hpp)
are kept in test/real_headers/.

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
from test.cython_utils import validate_cython_compiles
from test.header_cache import get_header_path, get_library_headers
from test.library_detection import detect_library

# Directory containing test fixture header files (our own test files)
REAL_HEADERS_DIR = os.path.join(os.path.dirname(__file__), "real_headers")

# Library configurations for full compilation tests
# Each library needs: pkg_config name, header path(s), smoke test expression
LIBRARY_CONFIGS = {
    # === C Libraries with pkg-config ===
    "zlib": {
        "pkg_config": "zlib",
        "system_header": "zlib.h",
        "smoke_test": "zlibVersion()",
        "cplus": False,
    },
    "jansson": {
        "pkg_config": "jansson",
        "system_header": "jansson.h",
        "smoke_test": "jansson_version_str()",
        "cplus": False,
    },
    "sqlite": {
        "pkg_config": "sqlite3",
        "system_header": "sqlite3.h",
        "smoke_test": "sqlite3_libversion()",
        "cplus": False,
    },
    "curl": {
        "pkg_config": "libcurl",
        "system_header": "curl/curl.h",
        "smoke_test": "curl_version()",
        "cplus": False,
    },
    "libuv": {
        "pkg_config": "libuv",
        "system_header": "uv.h",
        "smoke_test": "uv_version_string()",
        "cplus": False,
    },
    # === Additional C Libraries ===
    "cjson": {
        "pkg_config": "libcjson",
        "system_header": "cjson/cJSON.h",
        "smoke_test": "cJSON_Version()",
        "cplus": False,
    },
    # nng library uses cmake config (not pkg-config) on macOS
    "nng": {
        "detection": [
            {"type": "pkg_config", "package": "nng"},
            {"type": "cmake", "cmake_package": "nng"},
            {
                "type": "manual",
                "include_dirs": ["/opt/homebrew/include", "/usr/local/include", "/usr/include"],
                "library_dirs": ["/opt/homebrew/lib", "/usr/local/lib", "/usr/lib"],
                "libraries": ["nng"],
            },
        ],
        "system_header": "nng/nng.h",
        "smoke_test": "nng_version()",
        "cplus": False,
    },
    # sodium.h is an umbrella header - use project_prefixes to include sodium/* sub-headers
    "libsodium": {
        "pkg_config": "libsodium",
        "system_header": "sodium.h",
        "smoke_test": "sodium_init()",  # Now works with umbrella header support!
        "cplus": False,
        "project_prefixes": ("sodium",),  # Include declarations from sodium/*.h
    },
    "utf8proc": {
        "pkg_config": "libutf8proc",
        "system_header": "utf8proc.h",
        "smoke_test": "utf8proc_version()",
        "cplus": False,
    },
    # === C++ Libraries ===
    "catch2": {
        "detection": [
            {"type": "pkg_config", "package": "catch2"},
            {"type": "cmake", "cmake_package": "Catch2"},
            {
                "type": "manual",
                "include_dirs": ["/opt/homebrew/include", "/usr/local/include", "/usr/include"],
            },
        ],
        "system_header": "catch2/catch_all.hpp",
        "smoke_test": None,  # Test framework - compile-only
        "cplus": True,
        "std": "c++17",
        "header_only": True,
        # catch2 header is very slow to parse - skip in CI
        "skip_reason": "catch2 header parsing takes >5 minutes",
    },
    "fmt": {
        "detection": [
            {"type": "pkg_config", "package": "fmt"},
            {"type": "cmake", "cmake_package": "fmt"},
            {
                "type": "manual",
                "include_dirs": ["/opt/homebrew/include", "/usr/local/include", "/usr/include"],
                "library_dirs": ["/opt/homebrew/lib", "/usr/local/lib", "/usr/lib"],
                "libraries": ["fmt"],
            },
        ],
        "system_header": "fmt/core.h",
        "smoke_test": None,  # Uses formatting - compile-only
        "cplus": True,
        "std": "c++17",
        # fmt uses malloc without including cstdlib
        "preamble": "#include <cstdlib>",
        "pxd_only": True,  # Complex templates with forward refs
    },
    "spdlog": {
        "detection": [
            {"type": "pkg_config", "package": "spdlog"},
            {"type": "cmake", "cmake_package": "spdlog"},
            {
                "type": "manual",
                "include_dirs": ["/opt/homebrew/include", "/usr/local/include", "/usr/include"],
                "library_dirs": ["/opt/homebrew/lib", "/usr/local/lib", "/usr/lib"],
                "libraries": ["spdlog"],
            },
        ],
        "system_header": "spdlog/spdlog.h",
        "smoke_test": None,
        "cplus": True,
        "std": "c++17",
        # spdlog has complex internal forward references (logger class)
        # that Cython can't resolve, so we only validate pxd generation
        "pxd_only": True,
    },
    "doctest": {
        "detection": [
            {"type": "pkg_config", "package": "doctest"},
            {"type": "cmake", "cmake_package": "doctest"},
            {
                "type": "manual",
                "include_dirs": ["/opt/homebrew/include", "/usr/local/include", "/usr/include"],
            },
        ],
        "system_header": "doctest/doctest.h",
        "smoke_test": None,  # Test framework - compile-only
        "cplus": True,
        "std": "c++17",
        # doctest uses operator+= which Cython doesn't support
        "pxd_only": True,
    },
    "boost_lockfree": {
        "detection": [
            {"type": "pkg_config", "package": "boost"},
            {
                "type": "manual",
                "include_dirs": ["/opt/homebrew/include", "/usr/local/include", "/usr/include"],
            },
        ],
        "system_header": "boost/lockfree/queue.hpp",
        "smoke_test": None,  # Template library - compile-only
        "cplus": True,
        "std": "c++17",
        # boost headers are very slow to parse - skip in CI
        "skip_reason": "boost header parsing takes >5 minutes",
        # boost uses typename dependent types that Cython can't parse
        "pxd_only": True,
    },
    # === Python Libraries ===
    "python": {
        "detection": [
            {
                "type": "python_module",
                "module": "sysconfig",
                "include_getter": "get_path('include')",
            },
        ],
        "system_header": "Python.h",
        # Python.h is an umbrella header - functions are in sub-headers not exported
        "smoke_test": None,
        "cplus": False,
        "header_only": True,
    },
    "numpy": {
        "detection": [
            {
                "type": "python_module",
                "module": "numpy",
                "include_getter": "get_include()",
            },
        ],
        "system_header": "numpy/arrayobject.h",
        "smoke_test": None,  # Requires Py_Initialize() and import_array() - complex setup
        "cplus": False,
        # numpy/arrayobject.h includes Python.h, so we need Python's include path too
        "extra_includes": ["python"],
        # numpy uses _Complex double which Cython doesn't support
        "pxd_only": True,
    },
}


def _check_pkg_config(pkg_name: str) -> bool:
    """Check if a package is available via pkg-config."""
    try:
        subprocess.run(
            ["pkg-config", "--exists", pkg_name],
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _get_header_path(system_header: str, pkg_name: str) -> str | None:
    """Get the full path to a system header using pkg-config."""
    try:
        result = subprocess.run(
            ["pkg-config", "--cflags", pkg_name],
            capture_output=True,
            text=True,
        )
        # Parse -I flags to find include dir
        for flag in result.stdout.split():
            if flag.startswith("-I"):
                path = os.path.join(flag[2:], system_header)
                if os.path.exists(path):
                    return path
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Try standard locations
    for base in ["/usr/include", "/usr/local/include", "/opt/homebrew/include"]:
        path = os.path.join(base, system_header)
        if os.path.exists(path):
            return path

    # On macOS, try SDK path for system headers (pkg-config may not have -I flags)
    if sys.platform == "darwin":
        try:
            sdk_path = subprocess.check_output(
                ["xcrun", "--show-sdk-path"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            path = os.path.join(sdk_path, "usr", "include", system_header)
            if os.path.exists(path):
                return path
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    return None


def _get_system_include_args(cplus: bool = False) -> list[str]:
    """Get system include paths for libclang.

    libclang doesn't automatically know about system headers, so we need
    to provide the paths explicitly. This includes both the SDK headers
    and the clang builtin headers (for stdarg.h, stddef.h, etc.).

    For C++ mode, this also includes the C++ standard library (libc++) paths.

    :param cplus: If True, include C++ stdlib paths.
    """
    from autopxd.backends.libclang_backend import get_system_include_dirs

    args = get_system_include_dirs(cplus=cplus)

    # Fallback: if we didn't get any paths, try platform-specific defaults
    if not args:
        if sys.platform == "darwin":
            try:
                sdk_path = subprocess.check_output(
                    ["xcrun", "--show-sdk-path"], text=True, stderr=subprocess.DEVNULL
                ).strip()
                args = ["-isysroot", sdk_path]
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        elif sys.platform == "linux":
            for path in ["/usr/include", "/usr/local/include"]:
                if os.path.isdir(path):
                    args.append(f"-I{path}")

    return args


# These tests require libclang and real library installations
# Use pytest -m "not libclang" to exclude libclang tests
# Use pytest -m "not real_headers" to exclude tests requiring library installation
pytestmark = [pytest.mark.libclang, pytest.mark.real_headers]


@pytest.fixture
def libclang_backend():
    """Provide the libclang backend."""
    return get_backend("libclang")


class TestZlibHeader:
    """Test parsing the real zlib.h header."""

    @pytest.fixture
    def zlib_header(self, libclang_backend):
        """Parse zlib.h and return the IR."""
        # Download zlib headers if not cached
        zlib_dir = get_library_headers("zlib")
        zlib_path = get_header_path("zlib", "zlib.h")

        with open(zlib_path, encoding="utf-8") as f:
            code = f.read()

        # zlib.h includes zconf.h and system headers
        extra_args = [f"-I{zlib_dir}"] + _get_system_include_args()
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
        # Download jansson headers if not cached
        jansson_dir = get_library_headers("jansson")
        jansson_path = get_header_path("jansson", "jansson.h")

        with open(jansson_path, encoding="utf-8") as f:
            code = f.read()

        # jansson.h includes jansson_config.h and system headers
        extra_args = [f"-I{jansson_dir}"] + _get_system_include_args()
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

        extra_args = ["-x", "c++", "-std=c++11"] + _get_system_include_args(cplus=True)
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


class TestTemplates:
    """Test C++ template parsing."""

    @pytest.fixture
    def templates_header(self, libclang_backend):
        """Parse templates.hpp and return the IR."""
        hpp_path = os.path.join(REAL_HEADERS_DIR, "templates.hpp")
        if not os.path.exists(hpp_path):
            pytest.skip("templates.hpp not found")

        with open(hpp_path, encoding="utf-8") as f:
            code = f.read()

        extra_args = ["-x", "c++", "-std=c++17"] + _get_system_include_args(cplus=True)
        return libclang_backend.parse(code, "templates.hpp", extra_args=extra_args)

    def test_template_output_matches(self, templates_header, tmp_path):
        """Verify template pxd matches expected."""
        expected_path = os.path.join(REAL_HEADERS_DIR, "templates.expected.pxd")
        assert_header_pxd_equals(templates_header, expected_path, tmp_path, cplus=True)


class TestHeaderDiscovery:
    """Tests for discovering and validating real headers."""

    def test_real_headers_directory_exists(self):
        """Verify the real_headers directory exists."""
        assert os.path.isdir(REAL_HEADERS_DIR), f"Missing directory: {REAL_HEADERS_DIR}"

    def test_can_download_library_headers(self):
        """Verify library headers can be downloaded and cached."""
        # zlib headers
        zlib_dir = get_library_headers("zlib")
        assert (zlib_dir / "zlib.h").exists(), "zlib.h not downloaded"
        assert (zlib_dir / "zconf.h").exists(), "zconf.h not downloaded"

        # jansson headers
        jansson_dir = get_library_headers("jansson")
        assert (jansson_dir / "jansson.h").exists(), "jansson.h not downloaded"
        assert (jansson_dir / "jansson_config.h").exists(), "jansson_config.h not downloaded"

    def test_headers_are_valid_files(self):
        """Verify test fixture header files have content."""
        for filename in os.listdir(REAL_HEADERS_DIR):
            if filename.endswith((".h", ".hpp")):
                path = os.path.join(REAL_HEADERS_DIR, filename)
                size = os.path.getsize(path)
                # Real headers should be more than just a few bytes
                assert size > 100, f"{filename} seems too small ({size} bytes)"


class TestFullCompilation:
    """Tests that compile generated pxd against real libraries."""

    @pytest.mark.timeout(300)  # 5 minute timeout per library test
    @pytest.mark.parametrize("library", LIBRARY_CONFIGS.keys())
    def test_library_compiles(self, library, libclang_backend, tmp_path, request):
        """Generate pxd from system header and compile against library."""
        config = LIBRARY_CONFIGS[library]

        # Skip if marked with skip_reason (e.g., extremely slow headers)
        if "skip_reason" in config:
            pytest.skip(config["skip_reason"])

        # Use multi-method detection
        detection = detect_library(config)
        if not detection or not detection.found:
            # NOTE: Use pytest.fail here, NOT pytest.skip - missing libraries should fail loudly
            # Build helpful error message listing tried methods
            tried_methods = []
            if "detection" in config:
                tried_methods = [m.get("type", "unknown") for m in config["detection"]]
            if "pkg_config" in config:
                tried_methods.append(f"pkg_config:{config['pkg_config']}")
            platform_script = "macos" if sys.platform == "darwin" else "linux"
            pytest.fail(
                f"Library '{library}' not found (tried: {', '.join(tried_methods) or 'pkg_config'}).\n"
                f"To install test libraries: ./scripts/install-test-libs-{platform_script}.sh\n"
                f"Or run in Docker: docker build --build-arg TEST_MODE=1 -t autopxd2-test . && "
                f"docker run --rm -v $(pwd):/app -w /app autopxd2-test pytest test/test_real_headers.py"
            )

        # Find header (detection should have found it)
        header_path = detection.header_path
        if not header_path:
            # Try to find it in detected include dirs
            for inc_dir in detection.include_dirs:
                path = os.path.join(inc_dir, config["system_header"])
                if os.path.exists(path):
                    header_path = path
                    break

        if not header_path:
            pytest.fail(
                f"Header {config['system_header']} not found. "
                f"Detection method: {detection.method}, include_dirs: {detection.include_dirs}"
            )

        # Build include directories from detection result
        pkg_include_dirs = list(detection.include_dirs)

        # Add extra includes from other library configs (e.g., numpy needs Python.h)
        for extra_lib in config.get("extra_includes", []):
            if extra_lib in LIBRARY_CONFIGS:
                extra_config = LIBRARY_CONFIGS[extra_lib]
                extra_detection = detect_library(extra_config)
                if extra_detection:
                    for inc_dir in extra_detection.include_dirs:
                        if inc_dir not in pkg_include_dirs:
                            pkg_include_dirs.append(inc_dir)

        # Add the directory containing the header file to include paths
        # This is needed for headers that use relative includes like #include "foo.h"
        header_dir = os.path.dirname(header_path)
        if header_dir and header_dir not in pkg_include_dirs:
            pkg_include_dirs.insert(0, header_dir)

        # Parse header
        with open(header_path, encoding="utf-8", errors="replace") as f:
            code = f.read()

        # Apply preamble if specified (for headers that need stdlib includes)
        preamble = config.get("preamble", "")
        if preamble:
            code = preamble + "\n" + code

        is_cplus = config.get("cplus", False)
        std = config.get("std", "c++17" if is_cplus else None)
        # Build extra_args - system includes are added automatically by backend
        extra_args = []
        if is_cplus:
            extra_args = ["-x", "c++", f"-std={std}"]

        # Build project_prefixes for umbrella headers
        # This allows parsing declarations from sub-headers in system locations
        project_prefixes = config.get("project_prefixes")
        if project_prefixes:
            # Expand relative prefixes to full paths within detection include dirs
            expanded_prefixes = []
            for prefix in project_prefixes:
                for inc_dir in pkg_include_dirs:
                    full_prefix = os.path.join(inc_dir, prefix)
                    if os.path.isdir(full_prefix):
                        expanded_prefixes.append(full_prefix)
            project_prefixes = tuple(expanded_prefixes) if expanded_prefixes else None

        # Use the system_header as the filename for the extern block
        # This ensures #include directives match what's in the config
        # (e.g., "curl/curl.h" not just "curl.h")
        header_ir = libclang_backend.parse(
            code,
            config["system_header"],
            include_dirs=pkg_include_dirs,
            extra_args=extra_args,
            project_prefixes=project_prefixes,
        )

        # Generate pxd
        pxd = write_pxd(header_ir)
        assert pxd, f"Empty pxd generated for {library}"

        # pxd_only: Only validate pxd generation, skip Cython compilation
        # Used for C++ libraries with complex forward references that Cython can't resolve
        if config.get("pxd_only", False):
            return

        # Full compile with smoke test
        # Use detection result for compile flags, with pkg_config fallback for backward compat
        validate_cython_compiles(
            pxd,
            tmp_path,
            cplus=is_cplus,
            pkg_config=config.get("pkg_config"),
            smoke_test=config.get("smoke_test"),
            header_only=config.get("header_only", False),
            include_dirs=detection.include_dirs,
        )
