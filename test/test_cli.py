"""Tests for CLI functionality."""

import json

from click.testing import CliRunner

from autopxd import cli
from autopxd.backends import get_backend_info, is_backend_available


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

    def test_json_without_list_backends_errors(self) -> None:
        """--json without --list-backends should error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--json"], input="int x;")
        assert result.exit_code != 0
        assert "--json requires --list-backends" in result.output


class TestBackendOption:
    """Tests for --backend option."""

    def test_backend_pycparser_accepted(self) -> None:
        """--backend pycparser should be accepted."""
        runner = CliRunner()
        # Use stdin with simple header
        result = runner.invoke(cli, ["--backend", "pycparser"], input="int x;")
        # Should not error on unknown option
        assert "No such option" not in result.output

    def test_backend_auto_accepted(self) -> None:
        """--backend auto should be accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "auto"], input="int x;")
        assert "No such option" not in result.output

    def test_backend_invalid_rejected(self) -> None:
        """--backend with invalid value should error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "invalid"], input="int x;")
        assert result.exit_code != 0


class TestQuietOption:
    """Tests for --quiet option."""

    def test_quiet_accepted(self) -> None:
        """--quiet should be accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--quiet"], input="int x;")
        assert "No such option" not in result.output

    def test_quiet_short_form(self) -> None:
        """-q should work as short form."""
        runner = CliRunner()
        result = runner.invoke(cli, ["-q"], input="int x;")
        assert "No such option" not in result.output


class TestCppOption:
    """Tests for --cpp option."""

    def test_cpp_accepted(self) -> None:
        """--cpp should be accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--cpp"], input="int x;")
        assert "No such option" not in result.output

    def test_cpp_short_form(self) -> None:
        """-x should work as short form."""
        runner = CliRunner()
        result = runner.invoke(cli, ["-x"], input="int x;")
        assert "No such option" not in result.output


class TestStdOption:
    """Tests for --std option."""

    def test_std_accepted(self) -> None:
        """--std should be accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--std", "c11"], input="int x;")
        assert "No such option" not in result.output

    def test_std_cpp17_accepted(self) -> None:
        """--std c++17 should be accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--std", "c++17"], input="int x;")
        assert "No such option" not in result.output


class TestClangArgOption:
    """Tests for --clang-arg option."""

    def test_clang_arg_accepted(self) -> None:
        """--clang-arg should be accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--clang-arg", "-DFOO=1"], input="int x;")
        assert "No such option" not in result.output

    def test_clang_arg_multiple(self) -> None:
        """--clang-arg can be specified multiple times."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--clang-arg", "-DFOO", "--clang-arg", "-DBAR"], input="int x;")
        assert "No such option" not in result.output


class TestWhitelistOption:
    """Tests for --whitelist option."""

    def test_whitelist_accepted(self) -> None:
        """--whitelist should be accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--whitelist", "foo.h"], input="int x;")
        assert "No such option" not in result.output

    def test_whitelist_short_form(self) -> None:
        """-w should work as short form."""
        runner = CliRunner()
        result = runner.invoke(cli, ["-w", "foo.h"], input="int x;")
        assert "No such option" not in result.output

    def test_whitelist_multiple(self) -> None:
        """--whitelist can be specified multiple times."""
        runner = CliRunner()
        result = runner.invoke(cli, ["-w", "foo.h", "-w", "bar.h"], input="int x;")
        assert "No such option" not in result.output


class TestBackendResolution:
    """Tests for backend resolution logic."""

    def test_explicit_pycparser_no_warning(self) -> None:
        """--backend pycparser should not show fallback warning."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "pycparser"], input="int x;")
        assert "falling back to pycparser" not in result.output


class TestLibclangOnlyOptions:
    """Tests for options that require libclang."""

    def test_std_with_pycparser_errors(self) -> None:
        """--std with pycparser backend should error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "pycparser", "--std", "c11"], input="int x;")
        assert result.exit_code != 0
        assert "--std requires libclang" in result.output

    def test_clang_arg_with_pycparser_errors(self) -> None:
        """--clang-arg with pycparser backend should error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "pycparser", "--clang-arg", "-DFOO"], input="int x;")
        assert result.exit_code != 0
        assert "--clang-arg requires libclang" in result.output

    def test_cpp_without_libclang_errors(self) -> None:
        """--cpp without libclang should error."""
        runner = CliRunner()
        # Force libclang unavailable by using pycparser backend
        result = runner.invoke(cli, ["--backend", "pycparser", "--cpp"], input="int x;")
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
