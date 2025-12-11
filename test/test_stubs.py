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
