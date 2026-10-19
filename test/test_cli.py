"""Tests for CLI functionality."""

import json
import os
import pathlib
import tempfile
import warnings

import pytest
from click.testing import CliRunner
from headerkit.backends import get_backend_info, is_backend_available

from autopxd import cli, translate


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

    def test_unknown_backend_not_available(self) -> None:
        """Unknown backends should not be available."""
        assert is_backend_available("nonexistent") is False


class TestBackendInfo:
    """Tests for backend info retrieval."""

    def test_get_backend_info_returns_list(self) -> None:
        """get_backend_info should return a list of backend info dicts."""
        info = get_backend_info()
        assert isinstance(info, list)
        assert {b["name"] for b in info} == {"libclang", "tree-sitter"}

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
        assert "libclang" in result.output
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


@pytest.mark.libclang
class TestBackendOption:
    """Tests for --backend option."""

    def test_backend_auto_accepted(self, simple_header_file) -> None:
        """--backend auto should resolve to an available backend and translate."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "auto", simple_header_file])
        assert result.exit_code == 0
        assert "int x" in result.output

    def test_backend_invalid_rejected(self, simple_header_file) -> None:
        """--backend with invalid value should error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "invalid", simple_header_file])
        assert result.exit_code != 0


@pytest.mark.libclang
class TestQuietOption:
    """Tests for --quiet option."""

    def test_quiet_accepted(self, simple_header_file) -> None:
        """--quiet should translate and emit only the pxd, no diagnostics."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--quiet", simple_header_file])
        assert result.exit_code == 0
        assert "int x" in result.output

    def test_quiet_short_form(self, simple_header_file) -> None:
        """-q should behave identically to --quiet."""
        runner = CliRunner()
        long_form = runner.invoke(cli, ["--quiet", simple_header_file])
        short_form = runner.invoke(cli, ["-q", simple_header_file])
        assert short_form.exit_code == 0
        assert short_form.output == long_form.output


@pytest.mark.libclang
class TestCppOption:
    """Tests for --cpp option."""

    def test_cpp_accepted(self, simple_header_file) -> None:
        """--cpp should parse the header in C++ mode and still translate it."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--cpp", simple_header_file])
        assert result.exit_code == 0
        assert "int x" in result.output

    def test_cpp_short_form(self, simple_header_file) -> None:
        """-x should behave identically to --cpp."""
        runner = CliRunner()
        long_form = runner.invoke(cli, ["--cpp", simple_header_file])
        short_form = runner.invoke(cli, ["-x", simple_header_file])
        assert short_form.exit_code == 0
        assert short_form.output == long_form.output


@pytest.mark.libclang
class TestStdOption:
    """Tests for --std option."""

    def test_std_accepted(self, simple_header_file) -> None:
        """--std c11 should be passed to the parser and translate successfully."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--std", "c11", simple_header_file])
        assert result.exit_code == 0
        assert "int x" in result.output

    def test_std_cpp17_accepted(self, simple_header_file) -> None:
        """--std c++17 with --cpp should be passed to the parser and translate successfully."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--cpp", "--std", "c++17", simple_header_file])
        assert result.exit_code == 0
        assert "int x" in result.output

    def test_std_cpp17_without_cpp_mode_errors(self, simple_header_file) -> None:
        """A C++ std without --cpp is rejected: libclang parses a .h file as C."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--std", "c++17", simple_header_file])
        assert result.exit_code != 0


@pytest.mark.libclang
class TestClangArgOption:
    """Tests for --clang-arg option."""

    def test_clang_arg_accepted(self, simple_header_file) -> None:
        """--clang-arg should be forwarded to the parser without breaking translation."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--clang-arg", "-DFOO=1", simple_header_file])
        assert result.exit_code == 0
        assert "int x" in result.output

    def test_clang_arg_defines_macro(self) -> None:
        """--clang-arg -D should make a macro-guarded declaration visible."""
        runner = CliRunner()
        source = "#ifdef FOO\nint guarded_fn(void);\n#endif\nint always_fn(void);\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".h", delete=False, encoding="utf-8") as f:
            f.write(source)
            path = f.name
        try:
            without = runner.invoke(cli, [path])
            with_define = runner.invoke(cli, ["--clang-arg", "-DFOO", path])
            assert without.exit_code == 0
            assert with_define.exit_code == 0
            assert "guarded_fn" not in without.output
            assert "guarded_fn" in with_define.output
            assert "always_fn" in without.output
        finally:
            os.unlink(path)

    def test_clang_arg_multiple(self, simple_header_file) -> None:
        """--clang-arg can be specified multiple times."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--clang-arg", "-DFOO", "--clang-arg", "-DBAR", simple_header_file])
        assert result.exit_code == 0
        assert "int x" in result.output


@pytest.mark.libclang
class TestWhitelistOption:
    """Tests for --whitelist option."""

    def test_whitelist_excludes_non_whitelisted_header(self, simple_header_file) -> None:
        """A whitelist that omits the input header should drop its declarations."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--whitelist", "foo.h", simple_header_file])
        assert result.exit_code == 0
        assert "int x" not in result.output
        assert "pass" in result.output

    def test_whitelist_includes_whitelisted_header(self, simple_header_file) -> None:
        """A whitelist naming the input header should keep its declarations."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--whitelist", simple_header_file, simple_header_file])
        assert result.exit_code == 0
        assert "int x" in result.output

    def test_whitelist_short_form(self, simple_header_file) -> None:
        """-w should behave identically to --whitelist."""
        runner = CliRunner()
        long_form = runner.invoke(cli, ["--whitelist", "foo.h", simple_header_file])
        short_form = runner.invoke(cli, ["-w", "foo.h", simple_header_file])
        assert short_form.exit_code == 0
        assert short_form.output == long_form.output

    def test_whitelist_multiple(self, simple_header_file) -> None:
        """--whitelist can be specified multiple times."""
        runner = CliRunner()
        result = runner.invoke(cli, ["-w", "foo.h", "-w", "bar.h", simple_header_file])
        assert result.exit_code == 0
        assert "int x" not in result.output


@pytest.fixture
def allow_deny_header_dir():
    """A directory holding outer.h, which includes siblings inner.h and other.h."""
    with tempfile.TemporaryDirectory() as tmp:
        directory = pathlib.Path(tmp)
        (directory / "inner.h").write_text("int inner_fn(void);\n", encoding="utf-8")
        (directory / "other.h").write_text("int other_fn(void);\n", encoding="utf-8")
        (directory / "outer.h").write_text(
            '#include "inner.h"\n#include "other.h"\nint outer_fn(void);\n', encoding="utf-8"
        )
        yield directory


@pytest.mark.libclang
class TestAllowlistOption:
    """Tests for --allowlist, --denylist, and the deprecated --whitelist alias."""

    def test_allowlist_excludes_non_matching_header(self, simple_header_file) -> None:
        """An allowlist that omits the input header drops its declarations."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--allowlist", "foo.h", simple_header_file])
        assert result.exit_code == 0
        assert "int x" not in result.output
        assert "pass" in result.output

    def test_allowlist_keeps_matching_header(self, simple_header_file) -> None:
        """An allowlist naming the input header keeps its declarations."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--allowlist", simple_header_file, simple_header_file])
        assert result.exit_code == 0
        assert "int x" in result.output

    def test_allowlist_narrows_included_headers(self, allow_deny_header_dir) -> None:
        """With recursion on, an allowlist narrows which included headers contribute."""
        runner = CliRunner()
        outer = str(allow_deny_header_dir / "outer.h")
        result = runner.invoke(cli, ["--allowlist", "inner.h", "--allowlist", "outer.h", outer])
        assert result.exit_code == 0
        assert "inner_fn" in result.output
        assert "outer_fn" in result.output
        assert "other_fn" not in result.output

    def test_allowlist_accepts_glob(self, allow_deny_header_dir) -> None:
        """A glob allowlist selects included headers without pre-expansion by autopxd."""
        runner = CliRunner()
        outer = str(allow_deny_header_dir / "outer.h")
        result = runner.invoke(cli, ["--allowlist", "o*.h", outer])
        assert result.exit_code == 0
        assert "outer_fn" in result.output
        assert "other_fn" in result.output
        assert "inner_fn" not in result.output

    def test_denylist_excludes_matching_header(self, allow_deny_header_dir) -> None:
        """A denylist drops declarations from the headers it names."""
        runner = CliRunner()
        outer = str(allow_deny_header_dir / "outer.h")
        result = runner.invoke(cli, ["--denylist", "inner.h", outer])
        assert result.exit_code == 0
        assert "inner_fn" not in result.output
        assert "outer_fn" in result.output
        assert "other_fn" in result.output

    def test_denylist_excludes_the_input_header_itself(self, simple_header_file) -> None:
        """A denylist naming the input header drops that header's own declarations."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--denylist", simple_header_file, simple_header_file])
        assert result.exit_code == 0
        assert "int x" not in result.output

    def test_denylist_beats_allowlist(self, allow_deny_header_dir) -> None:
        """A file matching both lists is excluded: deny wins over allow."""
        runner = CliRunner()
        outer = str(allow_deny_header_dir / "outer.h")
        result = runner.invoke(cli, ["--allowlist", "*.h", "--denylist", "inner.h", outer])
        assert result.exit_code == 0
        assert "inner_fn" not in result.output
        assert "outer_fn" in result.output
        assert "other_fn" in result.output

    def test_denylist_has_no_short_flag(self, simple_header_file) -> None:
        """--denylist takes no short flag, so -w stays unambiguous."""
        runner = CliRunner()
        result = runner.invoke(cli, ["-d", "foo.h", simple_header_file])
        assert result.exit_code != 0

    def test_whitelist_still_works_and_warns(self, simple_header_file) -> None:
        """--whitelist keeps working and names --allowlist as its replacement."""
        runner = CliRunner()
        with pytest.warns(DeprecationWarning, match="--allowlist"):
            result = runner.invoke(cli, ["--whitelist", "foo.h", simple_header_file], catch_exceptions=False)
        assert result.exit_code == 0
        assert "int x" not in result.output

    def test_whitelist_short_form_still_warns(self, simple_header_file) -> None:
        """-w is retained for the deprecated spelling and warns the same way."""
        runner = CliRunner()
        with pytest.warns(DeprecationWarning, match="--allowlist"):
            result = runner.invoke(cli, ["-w", "foo.h", simple_header_file], catch_exceptions=False)
        assert result.exit_code == 0
        assert "int x" not in result.output

    def test_allowlist_does_not_warn(self, simple_header_file) -> None:
        """The canonical spelling emits no deprecation warning."""
        runner = CliRunner()
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            result = runner.invoke(cli, ["--allowlist", "foo.h", simple_header_file], catch_exceptions=False)
        assert result.exit_code == 0

    def test_quiet_suppresses_the_deprecation_warning(self, simple_header_file) -> None:
        """--quiet silences the --whitelist deprecation without changing the output."""
        runner = CliRunner()
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            quiet = runner.invoke(cli, ["--quiet", "-w", "foo.h", simple_header_file], catch_exceptions=False)
        assert quiet.exit_code == 0
        with pytest.warns(DeprecationWarning):
            loud = runner.invoke(cli, ["-w", "foo.h", simple_header_file], catch_exceptions=False)
        assert quiet.output == loud.output

    def test_allowlist_and_whitelist_together_is_an_error(self, simple_header_file) -> None:
        """Passing both spellings is an error rather than a silent precedence guess."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--allowlist", "foo.h", "-w", "bar.h", simple_header_file])
        assert result.exit_code == 1
        assert "not both" in result.output


@pytest.mark.libclang
class TestTranslateAllowDenyApi:
    """translate() mirrors the CLI's allow/deny behavior."""

    def test_allowlist_narrows(self, allow_deny_header_dir) -> None:
        outer = allow_deny_header_dir / "outer.h"
        pxd = translate(outer.read_text(), str(outer), allowlist=["inner.h", "outer.h"])
        assert "inner_fn" in pxd
        assert "outer_fn" in pxd
        assert "other_fn" not in pxd

    def test_allowlist_glob_narrows(self, allow_deny_header_dir) -> None:
        outer = allow_deny_header_dir / "outer.h"
        pxd = translate(outer.read_text(), str(outer), allowlist=["o*.h"])
        assert "outer_fn" in pxd
        assert "other_fn" in pxd
        assert "inner_fn" not in pxd

    def test_denylist_excludes(self, allow_deny_header_dir) -> None:
        outer = allow_deny_header_dir / "outer.h"
        pxd = translate(outer.read_text(), str(outer), denylist=["inner.h"])
        assert "inner_fn" not in pxd
        assert "outer_fn" in pxd

    def test_denylist_beats_allowlist(self, allow_deny_header_dir) -> None:
        outer = allow_deny_header_dir / "outer.h"
        pxd = translate(outer.read_text(), str(outer), allowlist=["*.h"], denylist=["inner.h"])
        assert "inner_fn" not in pxd
        assert "other_fn" in pxd
        assert "outer_fn" in pxd

    def test_whitelist_warns_and_forwards(self, allow_deny_header_dir) -> None:
        outer = allow_deny_header_dir / "outer.h"
        with pytest.warns(DeprecationWarning, match="allowlist"):
            deprecated = translate(outer.read_text(), str(outer), whitelist=["inner.h", "outer.h"])
        canonical = translate(outer.read_text(), str(outer), allowlist=["inner.h", "outer.h"])
        assert deprecated == canonical

    def test_allowlist_does_not_warn(self, allow_deny_header_dir) -> None:
        outer = allow_deny_header_dir / "outer.h"
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            translate(outer.read_text(), str(outer), allowlist=["outer.h"])

    def test_both_lists_is_an_error(self, allow_deny_header_dir) -> None:
        outer = allow_deny_header_dir / "outer.h"
        with pytest.raises(ValueError, match="not both"):
            translate(outer.read_text(), str(outer), allowlist=["a.h"], whitelist=["b.h"])


@pytest.mark.libclang
class TestEndToEnd:
    """End-to-end CLI tests."""

    def test_simple_header_produces_output(self) -> None:
        """Simple header should produce pxd output."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.h", "w") as f:
                f.write("int foo;")
            result = runner.invoke(cli, ["--backend", "libclang", "test.h", "out.pxd"])
            assert result.exit_code == 0
            with open("out.pxd") as f:
                output = f.read()
            assert "cdef extern" in output or "int foo" in output

    def test_backend_libclang_works(self) -> None:
        """--backend libclang should successfully parse."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.h", "w") as f:
                f.write("int bar;")
            result = runner.invoke(cli, ["--backend", "libclang", "test.h", "out.pxd"])
            assert result.exit_code == 0

    def test_include_dir_works(self) -> None:
        """-I should add include directory."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.h", "w") as f:
                f.write("int x;")
            result = runner.invoke(cli, ["--backend", "libclang", "-I", "/tmp", "test.h", "out.pxd"])
            assert result.exit_code == 0

    def test_struct_output(self) -> None:
        """Struct should be properly parsed."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.h", "w") as f:
                f.write("struct Foo { int x; };")
            result = runner.invoke(cli, ["--backend", "libclang", "test.h", "out.pxd"])
            assert result.exit_code == 0
            with open("out.pxd") as f:
                output = f.read()
            assert "Foo" in output

    def test_missing_infile_errors(self) -> None:
        """Missing infile argument should error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "libclang"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output

    def test_output_to_file(self) -> None:
        """Output written to explicit outfile."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.h", "w") as f:
                f.write("int foo;")
            result = runner.invoke(cli, ["--backend", "libclang", "test.h", "out.pxd"])
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
            result = runner.invoke(cli, ["--backend", "libclang", "test.h", "out.pxd"])
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
            result = runner.invoke(cli, ["--backend", "libclang", "test.h", "out.pxd"])
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
            result = runner.invoke(cli, ["--backend", "libclang", "test.h", "out.pxd"])
            assert result.exit_code == 0
            with open("out.pxd") as f:
                output = f.read()
            assert "ctypedef" in output
            assert "uint" in output


@pytest.fixture
def nested_header_dir():
    """Create a directory holding outer.h, which includes a sibling inner.h."""
    with tempfile.TemporaryDirectory() as tmp:
        directory = pathlib.Path(tmp)
        (directory / "inner.h").write_text("int inner_fn(void);\n", encoding="utf-8")
        (directory / "outer.h").write_text('#include "inner.h"\nint outer_fn(void);\n', encoding="utf-8")
        yield directory


@pytest.mark.libclang
class TestProjectPrefixOption:
    """Tests for --project-prefix option."""

    def test_included_header_needs_no_prefix_when_recursing(self, nested_header_dir) -> None:
        """With recursion on (the default), a non-system included header contributes anyway.

        --project-prefix now only reclassifies headers that live in system
        locations; a sibling header in the input's own directory is already
        treated as a project header, so the prefix neither adds nor removes
        anything here -- it only reorders the emitted declarations.
        """
        runner = CliRunner()
        outer = str(nested_header_dir / "outer.h")
        without = runner.invoke(cli, [outer])
        with_prefix = runner.invoke(cli, ["--project-prefix", str(nested_header_dir), outer])
        assert without.exit_code == 0
        assert with_prefix.exit_code == 0
        for output in (without.output, with_prefix.output):
            assert "inner_fn" in output
            assert "outer_fn" in output
        assert sorted(without.output.split()) == sorted(with_prefix.output.split())

    def test_no_recursive_drops_the_included_header(self, nested_header_dir) -> None:
        """--no-recursive confines output to the input header's own declarations."""
        runner = CliRunner()
        outer = str(nested_header_dir / "outer.h")
        result = runner.invoke(cli, ["--no-recursive", outer])
        assert result.exit_code == 0
        assert "outer_fn" in result.output
        assert "inner_fn" not in result.output

    def test_project_prefix_short_form(self, nested_header_dir) -> None:
        """-P should behave identically to --project-prefix."""
        runner = CliRunner()
        outer = str(nested_header_dir / "outer.h")
        long_form = runner.invoke(cli, ["--project-prefix", str(nested_header_dir), outer])
        short_form = runner.invoke(cli, ["-P", str(nested_header_dir), outer])
        assert short_form.exit_code == 0
        assert short_form.output == long_form.output

    def test_project_prefix_multiple(self, nested_header_dir) -> None:
        """Several -P prefixes should be honored together."""
        runner = CliRunner()
        outer = str(nested_header_dir / "outer.h")
        result = runner.invoke(cli, ["-P", "/nonexistent-prefix", "-P", str(nested_header_dir), outer])
        assert result.exit_code == 0
        assert "inner_fn" in result.output
        assert "outer_fn" in result.output


@pytest.mark.libclang
class TestNoRecursiveOption:
    """Tests for --no-recursive option.

    The flag's effect is not observable in single-file CLI output: with the input
    header's own directory as a project prefix, output is byte-identical with and
    without it. These tests therefore pin only that the flag parses and still
    produces a correct translation.
    """

    def test_no_recursive_still_translates(self, nested_header_dir) -> None:
        """--no-recursive should not prevent the input header from being translated."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--no-recursive", str(nested_header_dir / "outer.h")])
        assert result.exit_code == 0
        assert "outer_fn" in result.output


@pytest.mark.libclang
class TestMaxDepthOption:
    """Tests for --max-depth option.

    As with --no-recursive, the depth limit has no observable effect on single-file
    CLI output, so these tests pin argument parsing and a correct translation only.
    """

    def test_max_depth_still_translates(self, nested_header_dir) -> None:
        """--max-depth should not prevent the input header from being translated."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--max-depth", "5", str(nested_header_dir / "outer.h")])
        assert result.exit_code == 0
        assert "outer_fn" in result.output

    def test_max_depth_rejects_non_integer(self, nested_header_dir) -> None:
        """--max-depth should reject a non-integer value."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--max-depth", "abc", str(nested_header_dir / "outer.h")])
        assert result.exit_code != 0


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
        """--backend auto should use libclang."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.h", "w") as f:
                f.write("int bar;")
            result = runner.invoke(cli, ["--backend", "auto", "test.h", "out.pxd"])
            assert result.exit_code == 0

    def test_stdin_c_support(self) -> None:
        """Reading C code from stdin via '-' should generate valid pxd."""
        runner = CliRunner()
        result = runner.invoke(cli, ["-"], input="typedef struct { int x; } Point;\n")
        assert result.exit_code == 0
        assert "Point:" in result.output
        assert "int x" in result.output

    def test_stdin_cpp_support(self) -> None:
        """Reading C++ code from stdin via '-' with --cpp should generate valid pxd."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--cpp", "-"], input="class Widget { public: int w; };\n")
        assert result.exit_code == 0
        assert "Widget:" in result.output
        assert "int w" in result.output

    def test_piped_stdin_without_dash_argument(self) -> None:
        """Piping to autopxd without arguments should read from stdin automatically."""
        runner = CliRunner()
        result = runner.invoke(cli, [], input="typedef struct { int y; } Coord;\n")
        assert result.exit_code == 0
        assert "Coord:" in result.output
        assert "int y" in result.output

    def test_auto_detect_cpp_from_extension(self) -> None:
        """.hpp / .hh files should automatically parse in C++ mode without needing --cpp."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("mywidget.hpp", "w") as f:
                f.write("class MyWidget { public: int width; };")
            result = runner.invoke(cli, ["mywidget.hpp"])
            assert result.exit_code == 0
            assert "cppclass MyWidget:" in result.output
            assert "int width" in result.output

    def test_unknown_backend_errors_cleanly(self) -> None:
        """Unknown backend name should show clear error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "nonexistent_backend", "-"], input="int x;\n")
        assert result.exit_code != 0
        assert "Error: Backend 'nonexistent_backend' is not available." in result.output


@pytest.mark.treesitter
@pytest.mark.skipif(
    not is_backend_available("tree-sitter"),
    reason="tree-sitter optional dependency not installed",
)
class TestTreeSitterEndToEnd:
    """End-to-end CLI tests for the tree-sitter backend."""

    def test_treesitter_backend_cli(self) -> None:
        """--backend tree-sitter should parse C and C++ declarations."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--backend", "tree-sitter", "-"], input="int add(int a, int b);\n")
        assert result.exit_code == 0
        assert "int add(int a, int b)" in result.output

        cpp_result = runner.invoke(
            cli,
            ["--backend", "tree-sitter", "-"],
            input="class Shape { public: int id; void draw(); };\n",
        )
        assert cpp_result.exit_code == 0
        assert "cdef cppclass Shape:" in cpp_result.output
        assert "int id" in cpp_result.output
        assert "void draw()" in cpp_result.output
