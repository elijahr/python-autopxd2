"""Tests for autopxd bundled stub files."""

import importlib.resources
import importlib.util
import subprocess
import sys

import pytest


class TestStubsPackage:
    """Tests that stubs package is properly structured."""

    def test_stubs_package_exists(self):
        """autopxd.stubs is importable."""
        import autopxd.stubs

        assert autopxd.stubs is not None

    def test_stdarg_stub_exists(self):
        """stdarg.pxd stub file exists in package."""
        files = importlib.resources.files("autopxd.stubs")
        stdarg_path = files / "stdarg.pxd"
        assert stdarg_path.is_file(), "stdarg.pxd should exist in autopxd.stubs"

    def test_stdarg_stub_content(self):
        """stdarg.pxd contains va_list declaration."""
        files = importlib.resources.files("autopxd.stubs")
        content = (files / "stdarg.pxd").read_text()
        assert "va_list" in content
        assert "cdef extern from" in content
        assert "stdarg.h" in content


class TestStubCythonCompilation:
    """Tests that stub files compile with Cython."""

    @pytest.fixture
    def cython_available(self):
        """Check if Cython is available."""
        if importlib.util.find_spec("Cython") is None:
            pytest.skip("Cython not available")
        return True

    def test_stdarg_compiles(self, cython_available, tmp_path):
        """stdarg.pxd compiles without errors."""
        # Create a test pxd that imports from the stub
        test_pxd = tmp_path / "test_import.pxd"
        test_pxd.write_text(
            """\
from autopxd.stubs.stdarg cimport va_list

cdef extern from "test.h":
    void test_func(va_list args)
"""
        )

        # Run cython to check syntax (won't link, just parse)
        result = subprocess.run(
            [sys.executable, "-m", "cython", "-3", str(test_pxd)],
            capture_output=True,
            text=True,
        )
        # Cython may warn but shouldn't error on valid pxd
        assert result.returncode == 0, f"Cython failed: {result.stderr}"


class TestSocketStubs:
    """Tests for socket-related stub files."""

    def test_sys_socket_stub_exists(self):
        """sys_socket.pxd exists in stubs package."""
        files = importlib.resources.files("autopxd.stubs")
        path = files / "sys_socket.pxd"
        assert path.is_file()

    def test_sys_socket_contains_sockaddr(self):
        """sys_socket.pxd declares sockaddr."""
        files = importlib.resources.files("autopxd.stubs")
        content = (files / "sys_socket.pxd").read_text()
        assert "sockaddr" in content
        assert "socklen_t" in content

    def test_netinet_in_stub_exists(self):
        """netinet_in.pxd exists in stubs package."""
        files = importlib.resources.files("autopxd.stubs")
        path = files / "netinet_in.pxd"
        assert path.is_file()

    def test_netinet_in_contains_sockaddr_in(self):
        """netinet_in.pxd declares sockaddr_in."""
        files = importlib.resources.files("autopxd.stubs")
        content = (files / "netinet_in.pxd").read_text()
        assert "sockaddr_in" in content
        assert "in_addr" in content


class TestAllStubsCompile:
    """Verify all stub files are syntactically correct Cython."""

    @pytest.mark.parametrize(
        "stub_file",
        [
            "arpa_inet.pxd",
            "dirent.pxd",
            "netdb.pxd",
            "netinet_in.pxd",
            "pthread.pxd",
            "regex.pxd",
            "semaphore.pxd",
            "stdarg.pxd",
            "stdatomic.pxd",
            "sys_socket.pxd",
            "sys_statvfs.pxd",
            "sys_un.pxd",
            "termios.pxd",
            "cppthread.pxd",
            "cppchrono.pxd",
            "cppfilesystem.pxd",
            "cppregex.pxd",
            "cpptuple.pxd",
            "cpparray.pxd",
            "cppvariant.pxd",
            "cppbitset.pxd",
        ],
    )
    def test_stub_compiles(self, stub_file, tmp_path):
        """Verify stub file is valid Cython syntax."""
        import os

        from Cython.Compiler.Main import CompilationOptions
        from Cython.Compiler.Main import compile as cython_compile

        stub_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "autopxd",
            "stubs",
            stub_file,
        )

        if not os.path.exists(stub_path):
            pytest.skip(f"Stub {stub_file} not yet created")

        # Create a pyx that imports from the stub
        stub_name = stub_file[:-4]  # Remove .pxd

        # C++ stubs need cython_cplus directive
        is_cpp_stub = stub_name.startswith("cpp")
        if is_cpp_stub:
            pyx_content = "# distutils: language = c++\n"
            pyx_content += f"from autopxd.stubs.{stub_name} cimport *\n"
        else:
            pyx_content = f"from autopxd.stubs.{stub_name} cimport *\n"

        pyx_file = tmp_path / "test_stub.pyx"
        pyx_file.write_text(pyx_content)

        # Attempt to compile
        options = CompilationOptions(
            language_level=3,
            cplus=is_cpp_stub,
        )
        try:
            result = cython_compile(str(pyx_file), options=options)
            if result and hasattr(result, "num_errors") and result.num_errors > 0:
                pytest.fail(f"Cython compilation had {result.num_errors} errors")
        except Exception as e:
            pytest.fail(f"Cython compilation failed: {e}")
