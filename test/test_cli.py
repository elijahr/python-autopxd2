"""Tests for CLI functionality."""

import json
import os
import tempfile

import pytest
from click.testing import CliRunner

from autopxd import cli
from autopxd.backends import get_backend_info, is_backend_available


@pytest.fixture
def simple_header_file():
    """Create a temporary file with simple C code."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".h", delete=False, encoding="utf-8") as f:
        f.write("int x;")
        f.flush()
        yield f.name
    os.unlink(f.name)


class TestBackendAvailability:
    """Tests for backend availability checking."""

    def test_pycparser_always_available(self) -> None:
        """pycparser should always be available."""
        assert is_backend_available("pycparser") is True

    def test_unknown_backend_not_available(self) -> None:
        """Unknown backends should not be available."""
        assert is_backend_available("nonexistent") is False


class TestBackendInfo:
    """Tests for backend info retrieval."""

    def test_get_backend_info_returns_list(self) -> None:
        """get_backend_info should return a list of backend info dicts."""
        info = get_backend_info()
        assert isinstance(info, list)
        assert len(info) >= 1  # At least pycparser

    def test_backend_info_has_required_fields(self) -> None:
        """Each backend info should have name, available, default, description."""
        info = get_backend_info()
        for backend in info:
            assert "name" in backend
            assert "available" in backend
            assert "default" in backend
            assert "description" in backend

    def test_exactly_one_default_backend(self) -> None:
        """Exactly one backend should be marked as default."""
        info = get_backend_info()
        defaults = [b for b in info if b["default"]]
        assert len(defaults) == 1


class TestListBackends:
    """Tests for --list-backends option."""

    def test_list_backends_exits_zero(self) -> None:
        """--list-backends should exit with code 0."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--list-backends"])
        assert result.exit_code == 0

    def test_list_backends_shows_available(self) -> None:
        """--list-backends should show available backends."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--list-backends"])
        assert "pycparser" in result.output
        assert "[available]" in result.output or "[not available]" in result.output

    def test_list_backends_shows_default(self) -> None:
        """--list-backends should indicate the default backend."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--list-backends"])
        assert "Default:" in result.output


class TestListBackendsJson:
    """Tests for --list-backends --json option."""

    def test_list_backends_json_valid(self) -> None:
        """--list-backends --json should output valid JSON."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--list-backends", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "backends" in data

    def test_list_backends_json_structure(self) -> None:
        """JSON output should have correct structure."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--list-backends", "--json"])
        data = json.loads(result.output)
        assert isinstance(data["backends"], list)
        for backend in data["backends"]:
            assert "name" in backend
            assert "available" in backend
            assert "default" in backend

    def test_json_without_list_backends_errors(self, simple_header_file) -> None:
        """--json without --list-backends should error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--json", simple_header_file])
        assert result.exit_code != 0
        assert "--json requires --list-backends" in result.output


class TestBackendOption:
    """Tests for --backend option."""

    def test_backend_pycparser_accepted(self, simple_header_file) -> None:
        """--backend pycparser should be accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "pycparser", simple_header_file])
        # Should not error on unknown option
        assert "No such option" not in result.output

    def test_backend_auto_accepted(self, simple_header_file) -> None:
        """--backend auto should be accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "auto", simple_header_file])
        assert "No such option" not in result.output

    def test_backend_invalid_rejected(self, simple_header_file) -> None:
        """--backend with invalid value should error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "invalid", simple_header_file])
        assert result.exit_code != 0


class TestQuietOption:
    """Tests for --quiet option."""

    def test_quiet_accepted(self, simple_header_file) -> None:
        """--quiet should be accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--quiet", simple_header_file])
        assert "No such option" not in result.output

    def test_quiet_short_form(self, simple_header_file) -> None:
        """-q should work as short form."""
        runner = CliRunner()
        result = runner.invoke(cli, ["-q", simple_header_file])
        assert "No such option" not in result.output


class TestCppOption:
    """Tests for --cpp option."""

    def test_cpp_accepted(self, simple_header_file) -> None:
        """--cpp should be accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--cpp", simple_header_file])
        assert "No such option" not in result.output

    def test_cpp_short_form(self, simple_header_file) -> None:
        """-x should work as short form."""
        runner = CliRunner()
        result = runner.invoke(cli, ["-x", simple_header_file])
        assert "No such option" not in result.output


class TestStdOption:
    """Tests for --std option."""

    def test_std_accepted(self, simple_header_file) -> None:
        """--std should be accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--std", "c11", simple_header_file])
        assert "No such option" not in result.output

    def test_std_cpp17_accepted(self, simple_header_file) -> None:
        """--std c++17 should be accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--std", "c++17", simple_header_file])
        assert "No such option" not in result.output


class TestClangArgOption:
    """Tests for --clang-arg option."""

    def test_clang_arg_accepted(self, simple_header_file) -> None:
        """--clang-arg should be accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--clang-arg", "-DFOO=1", simple_header_file])
        assert "No such option" not in result.output

    def test_clang_arg_multiple(self, simple_header_file) -> None:
        """--clang-arg can be specified multiple times."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--clang-arg", "-DFOO", "--clang-arg", "-DBAR", simple_header_file])
        assert "No such option" not in result.output


class TestWhitelistOption:
    """Tests for --whitelist option."""

    def test_whitelist_accepted(self, simple_header_file) -> None:
        """--whitelist should be accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--whitelist", "foo.h", simple_header_file])
        assert "No such option" not in result.output

    def test_whitelist_short_form(self, simple_header_file) -> None:
        """-w should work as short form."""
        runner = CliRunner()
        result = runner.invoke(cli, ["-w", "foo.h", simple_header_file])
        assert "No such option" not in result.output

    def test_whitelist_multiple(self, simple_header_file) -> None:
        """--whitelist can be specified multiple times."""
        runner = CliRunner()
        result = runner.invoke(cli, ["-w", "foo.h", "-w", "bar.h", simple_header_file])
        assert "No such option" not in result.output


class TestBackendResolution:
    """Tests for backend resolution logic."""

    def test_explicit_pycparser_no_warning(self, simple_header_file) -> None:
        """--backend pycparser should not show fallback warning."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "pycparser", simple_header_file])
        assert "falling back to pycparser" not in result.output


class TestLibclangOnlyOptions:
    """Tests for options that require libclang."""

    def test_std_with_pycparser_errors(self, simple_header_file) -> None:
        """--std with pycparser backend should error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "pycparser", "--std", "c11", simple_header_file])
        assert result.exit_code != 0
        assert "--std requires libclang" in result.output

    def test_clang_arg_with_pycparser_errors(self, simple_header_file) -> None:
        """--clang-arg with pycparser backend should error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "pycparser", "--clang-arg", "-DFOO", simple_header_file])
        assert result.exit_code != 0
        assert "--clang-arg requires libclang" in result.output

    def test_cpp_without_libclang_errors(self, simple_header_file) -> None:
        """--cpp without libclang should error."""
        runner = CliRunner()
        # Force libclang unavailable by using pycparser backend
        result = runner.invoke(cli, ["--backend", "pycparser", "--cpp", simple_header_file])
        assert result.exit_code != 0


class TestEndToEnd:
    """End-to-end CLI tests."""

    def test_simple_header_produces_output(self) -> None:
        """Simple header should produce pxd output."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.h", "w") as f:
                f.write("int foo;")
            result = runner.invoke(cli, ["--backend", "pycparser", "test.h", "out.pxd"])
            assert result.exit_code == 0
            with open("out.pxd") as f:
                output = f.read()
            assert "cdef extern" in output or "int foo" in output

    def test_backend_pycparser_works(self) -> None:
        """--backend pycparser should successfully parse."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.h", "w") as f:
                f.write("int bar;")
            result = runner.invoke(cli, ["--backend", "pycparser", "test.h", "out.pxd"])
            assert result.exit_code == 0

    def test_include_dir_works(self) -> None:
        """-I should add include directory."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.h", "w") as f:
                f.write("int x;")
            result = runner.invoke(cli, ["--backend", "pycparser", "-I", "/tmp", "test.h", "out.pxd"])
            assert result.exit_code == 0

    def test_struct_output(self) -> None:
        """Struct should be properly parsed."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.h", "w") as f:
                f.write("struct Foo { int x; };")
            result = runner.invoke(cli, ["--backend", "pycparser", "test.h", "out.pxd"])
            assert result.exit_code == 0
            with open("out.pxd") as f:
                output = f.read()
            assert "Foo" in output

    def test_missing_infile_errors(self) -> None:
        """Missing infile argument should error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "pycparser"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output

    def test_output_to_file(self) -> None:
        """Output written to explicit outfile."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.h", "w") as f:
                f.write("int foo;")
            result = runner.invoke(cli, ["--backend", "pycparser", "test.h", "out.pxd"])
            assert result.exit_code == 0
            with open("out.pxd") as f:
                output = f.read()
            assert "cdef extern" in output or "int foo" in output

    def test_enum_output(self) -> None:
        """Enum should be properly parsed."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.h", "w") as f:
                f.write("enum Color { RED, GREEN, BLUE };")
            result = runner.invoke(cli, ["--backend", "pycparser", "test.h", "out.pxd"])
            assert result.exit_code == 0
            with open("out.pxd") as f:
                output = f.read()
            assert "Color" in output
            assert "RED" in output

    def test_function_output(self) -> None:
        """Function should be properly parsed."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.h", "w") as f:
                f.write("int add(int a, int b);")
            result = runner.invoke(cli, ["--backend", "pycparser", "test.h", "out.pxd"])
            assert result.exit_code == 0
            with open("out.pxd") as f:
                output = f.read()
            assert "int add(int a, int b)" in output

    def test_typedef_output(self) -> None:
        """Typedef should be properly parsed."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.h", "w") as f:
                f.write("typedef unsigned int uint;")
            result = runner.invoke(cli, ["--backend", "pycparser", "test.h", "out.pxd"])
            assert result.exit_code == 0
            with open("out.pxd") as f:
                output = f.read()
            assert "ctypedef" in output
            assert "uint" in output


class TestProjectPrefixOption:
    """Tests for --project-prefix option."""

    def test_project_prefix_accepted(self, simple_header_file) -> None:
        """--project-prefix should be accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--project-prefix", "/some/path", simple_header_file])
        assert "No such option" not in result.output

    def test_project_prefix_short_form(self, simple_header_file) -> None:
        """-P should work as short form."""
        runner = CliRunner()
        result = runner.invoke(cli, ["-P", "/some/path", simple_header_file])
        assert "No such option" not in result.output

    def test_project_prefix_multiple(self, simple_header_file) -> None:
        """--project-prefix can be specified multiple times."""
        runner = CliRunner()
        result = runner.invoke(cli, ["-P", "/path1", "-P", "/path2", simple_header_file])
        assert "No such option" not in result.output

    def test_project_prefix_with_pycparser_errors(self, simple_header_file) -> None:
        """--project-prefix with pycparser backend should error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "pycparser", "-P", "/path", simple_header_file])
        assert result.exit_code != 0
        assert "--project-prefix requires libclang" in result.output


class TestNoRecursiveOption:
    """Tests for --no-recursive option."""

    def test_no_recursive_accepted(self, simple_header_file) -> None:
        """--no-recursive should be accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--no-recursive", simple_header_file])
        assert "No such option" not in result.output

    def test_no_recursive_with_pycparser_errors(self, simple_header_file) -> None:
        """--no-recursive with pycparser backend should error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "pycparser", "--no-recursive", simple_header_file])
        assert result.exit_code != 0
        assert "--no-recursive requires libclang" in result.output


class TestMaxDepthOption:
    """Tests for --max-depth option."""

    def test_max_depth_accepted(self, simple_header_file) -> None:
        """--max-depth should be accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--max-depth", "5", simple_header_file])
        assert "No such option" not in result.output

    def test_max_depth_with_pycparser_errors(self, simple_header_file) -> None:
        """--max-depth with pycparser backend should error (when non-default)."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "pycparser", "--max-depth", "5", simple_header_file])
        assert result.exit_code != 0
        assert "--max-depth requires libclang" in result.output


@pytest.mark.libclang
class TestLibclangEndToEnd:
    """End-to-end CLI tests using libclang backend."""

    def test_libclang_simple_header(self) -> None:
        """libclang backend should parse simple header."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.h", "w") as f:
                f.write("int foo;")
            result = runner.invoke(cli, ["--backend", "libclang", "test.h", "out.pxd"])
            assert result.exit_code == 0
            with open("out.pxd") as f:
                output = f.read()
            assert "int foo" in output

    def test_libclang_struct(self) -> None:
        """libclang backend should parse struct."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.h", "w") as f:
                f.write("struct Point { int x; int y; };")
            result = runner.invoke(cli, ["--backend", "libclang", "test.h", "out.pxd"])
            assert result.exit_code == 0
            with open("out.pxd") as f:
                output = f.read()
            assert "Point" in output

    def test_libclang_cpp_class(self) -> None:
        """libclang with --cpp should parse C++ class."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.hpp", "w") as f:
                f.write("class Foo { public: int x; };")
            result = runner.invoke(cli, ["--cpp", "test.hpp", "out.pxd"])
            assert result.exit_code == 0
            with open("out.pxd") as f:
                output = f.read()
            assert "Foo" in output

    def test_auto_backend_uses_libclang(self) -> None:
        """--backend auto should use libclang when available."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.h", "w") as f:
                f.write("int bar;")
            result = runner.invoke(cli, ["--backend", "auto", "test.h", "out.pxd"])
            assert result.exit_code == 0
            # Should not show pycparser fallback warning
            assert "falling back to pycparser" not in result.output
