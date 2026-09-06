import fnmatch
import json
import os
import sys
import warnings
from collections.abc import (
    Callable,
)
from importlib.metadata import (
    version as get_version,
)
from typing import (
    IO,
)

import click
from headerkit import (
    Declaration,
)
from headerkit.backends import (
    get_backend,
    get_backend_info,
    get_default_backend,
    is_backend_available,
)
from headerkit.writers.cython import (
    write_pxd,
)

__version__ = get_version("autopxd2")


def _debug_print(msg: str) -> None:
    """Print debug message to stderr."""
    print(f"[autopxd] {msg}", file=sys.stderr)


def _normalize_for_match(path: str) -> str:
    """Normalize a path for comparison, mirroring headerkit's ``normalize_path``."""
    return path.replace("\\", "/").lower()


def _list_search_dirs(hdrname: str, include_dirs: list[str] | None) -> list[str]:
    """Directories a relative allowlist/denylist pattern is resolved against, in priority order.

    Mirrors headerkit's rule: the parsed file's own directory first, then the
    include search path, then the process working directory.
    """
    dirs = [os.path.dirname(os.path.abspath(hdrname)) or os.getcwd()]
    if include_dirs:
        dirs.extend(include_dirs)
    dirs.append(os.getcwd())
    return dirs


def _pattern_candidates(pattern: str, search_dirs: list[str]) -> list[str]:
    """Absolute forms an allowlist/denylist pattern may take, in priority order."""
    if os.path.isabs(pattern):
        absolute = os.path.abspath(pattern)
        return [_normalize_for_match(absolute), _normalize_for_match(os.path.realpath(absolute))]
    candidates: list[str] = []
    for directory in search_dirs:
        joined = os.path.abspath(os.path.join(directory, pattern))
        for variant in (joined, os.path.realpath(joined)):
            normalized = _normalize_for_match(variant)
            if normalized not in candidates:
                candidates.append(normalized)
    return candidates


def _pattern_matcher(
    patterns: list[str],
    search_dirs: list[str],
) -> "Callable[[Declaration], bool]":
    """Build a predicate reporting whether a declaration's file matches ``patterns``.

    A pattern containing no path separator is matched against the declaration
    file's BASENAME, so both a bare filename and a bare glob keep working
    wherever the file lives.  A pattern containing a separator is matched
    against the declaration file's absolute path; a relative such pattern is
    resolved the way headerkit resolves one -- against the parsed file's own
    directory first, then each include directory, then the working directory --
    and matches if any of those resolutions matches.

    Backends report ``location.file`` as whatever path reached the parser, which
    is often relative (e.g. ``./tux_foo.h``), so both sides are made absolute
    before comparison; symlinked and non-symlinked forms are both tried.

    Path comparison is case-insensitive and separator-normalized for
    cross-platform compatibility.
    """
    basename_patterns: list[str] = []
    path_patterns: list[str] = []
    for pattern in patterns:
        normalized = pattern.replace("\\", "/")
        if "/" in normalized:
            path_patterns.append(_normalize_for_match(normalized))
        else:
            basename_patterns.append(_normalize_for_match(normalized))

    resolved_patterns: list[str] = []
    for pattern in path_patterns:
        resolved_patterns.extend(_pattern_candidates(pattern, search_dirs))

    def matches(decl: Declaration) -> bool:
        if decl.location is None:
            return False
        decl_abs = os.path.abspath(decl.location.file)
        decl_forms = {
            _normalize_for_match(decl_abs),
            _normalize_for_match(os.path.realpath(decl_abs)),
        }
        decl_base = _normalize_for_match(os.path.basename(decl_abs))
        return any(fnmatch.fnmatch(decl_base, pattern) for pattern in basename_patterns) or any(
            fnmatch.fnmatch(form, pattern) for form in decl_forms for pattern in resolved_patterns
        )

    return matches


def _filter_declarations(
    declarations: list[Declaration],
    allowlist: list[str] | None = None,
    denylist: list[str] | None = None,
    hdrname: str = "",
    include_dirs: list[str] | None = None,
) -> list[Declaration]:
    """Narrow declarations to the allowlist, then subtract the denylist.

    headerkit applies both lists while parsing, but it never applies either to
    the declarations of the file it was handed: an allowlist that omits the
    input header still yields that header's declarations, and a denylist naming
    it does not remove them.  This pass closes that gap, so the lists mean the
    same thing for the root header as for every header it includes.

    Deny is applied after allow, so a file matching both is excluded -- the same
    precedence headerkit uses.

    Declarations without location info are excluded when an allowlist is active,
    because nothing can establish that they came from an allowed file.
    """
    search_dirs = _list_search_dirs(hdrname, include_dirs)
    result = declarations
    if allowlist:
        allowed = _pattern_matcher(allowlist, search_dirs)
        result = [decl for decl in result if allowed(decl)]
    if denylist:
        denied = _pattern_matcher(denylist, search_dirs)
        result = [decl for decl in result if not denied(decl)]
    return result


_INCLUDE_FOLLOWING_BACKENDS = frozenset({"libclang"})


def _backend_follows_includes(backend_name: str) -> bool:
    """Report whether a backend resolves and parses ``#include`` directives.

    Umbrella-header options only have something to act on when the backend
    reads included files. A backend that parses just the text it is given
    cannot honor them.
    """
    return backend_name.strip().lower() in _INCLUDE_FOLLOWING_BACKENDS


def translate(
    code: str,
    hdrname: str,
    backend: str = "auto",
    extra_args: list[str] | None = None,
    allowlist: list[str] | None = None,
    debug: bool = False,
    use_default_includes: bool = True,
    project_prefixes: tuple[str, ...] | None = None,
    recursive_includes: bool = True,
    max_depth: int | None = None,
    denylist: list[str] | None = None,
    whitelist: list[str] | None = None,
) -> str:
    """Generate Cython .pxd from C/C++ header code.

    Args:
        code: C/C++ header source code.
        hdrname: Header filename (used in cdef extern from).
        backend: Backend name ("auto", "libclang").
        extra_args: Extra arguments passed to backend (e.g., ["-I/usr/include"]).
        allowlist: Only include declarations from files matching these patterns.
            Supports fnmatch patterns like "*.h", "include/*.h". With recursion
            on (the default) and no allowlist, declarations from every
            non-system included header are emitted; an allowlist narrows that,
            in both recursion modes.
        debug: Print debug info to stderr.
        use_default_includes: If True (default), automatically detect and add
            system include directories when using the libclang backend.
        project_prefixes: [libclang] Tuple of path prefixes to treat as project
            headers (not system). Use this for umbrella headers of libraries
            installed in system locations (e.g., ("/opt/homebrew/include/sodium",)).
        recursive_includes: [libclang] If True (default), detect umbrella headers
            and recursively parse included project headers.
        max_depth: [libclang] Recursion depth limit for umbrella header
            processing. ``None`` (default) means unspecified and resolves to
            10. ``0`` disables umbrella expansion. Passing a value to a
            backend that does not follow includes raises :class:`UserWarning`,
            because such a caller expects declarations that backend will
            never produce.
        denylist: Exclude declarations from files matching these patterns.
            Same pattern syntax as ``allowlist``. A file matching both lists is
            excluded: deny wins over allow.
        whitelist: Deprecated alias for ``allowlist``. Emits
            :class:`DeprecationWarning`. Passing both raises :class:`ValueError`.

    Returns:
        Cython .pxd file contents.
    """
    if whitelist is not None:
        if allowlist is not None:
            raise ValueError(
                "Pass either allowlist or whitelist, not both. whitelist is the deprecated spelling of allowlist."
            )
        warnings.warn(
            "The 'whitelist' argument is deprecated; use 'allowlist' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        allowlist = whitelist

    # Resolve backend
    if backend == "auto":
        backend_name = get_default_backend()
    else:
        backend_name = backend

    if max_depth is not None and not _backend_follows_includes(backend_name):
        warnings.warn(
            f"The {backend_name} backend does not follow #include directives, so "
            f"max_depth={max_depth} cannot be honored and no declarations from "
            f"included files will appear in the result. Use the libclang backend "
            f"for umbrella header expansion.",
            UserWarning,
            stacklevel=2,
        )
    effective_max_depth = 10 if max_depth is None else max_depth

    if debug:
        _debug_print(f"Backend: {backend_name}")
        _debug_print(f"Parsing: {hdrname}")
        if project_prefixes:
            _debug_print(f"Project prefixes: {project_prefixes}")

    # Parse with backend
    backend_obj = get_backend(backend_name)

    # Extract include_dirs from extra_args
    # Handle both "-I/path" and "-I", "/path" formats
    include_dirs: list[str] = []
    other_args: list[str] = []
    args_iter = iter(extra_args or [])
    for arg in args_iter:
        if arg == "-I":
            # Next arg is the path
            try:
                include_dirs.append(next(args_iter))
            except StopIteration:
                pass  # -I at end with no path, ignore
        elif arg.startswith("-I"):
            include_dirs.append(arg[2:])
        else:
            other_args.append(arg)

    header = backend_obj.parse(
        code,
        hdrname,
        include_dirs=include_dirs or None,
        extra_args=other_args or None,
        use_default_includes=use_default_includes,
        project_prefixes=project_prefixes,
        recursive_includes=recursive_includes,
        max_depth=effective_max_depth,
        allowlist=allowlist or None,
        denylist=denylist or None,
    )

    if debug:
        _debug_print(f"Found {len(header.declarations)} declarations")

    # headerkit applies both lists while parsing, but never to the root header's
    # own declarations; this pass makes the lists mean the same thing there.
    if allowlist or denylist:
        header.declarations = _filter_declarations(
            header.declarations,
            allowlist=allowlist,
            denylist=denylist,
            hdrname=hdrname,
            include_dirs=include_dirs or None,
        )
        if debug:
            _debug_print(f"After allow/deny filtering: {len(header.declarations)} declarations")

    if debug:
        for decl in header.declarations:
            name = getattr(decl, "name", None) or "(anonymous)"
            _debug_print(f"  {type(decl).__name__}: {name}")

    # Generate pxd
    return write_pxd(header)


CONTEXT_SETTINGS: dict[str, list[str]] = dict(help_option_names=["-h", "--help"])


def _print_backends_human() -> None:
    """Print backend info in human-readable format."""
    info = get_backend_info()
    print("Available backends:")
    for backend in info:
        status = "[available]" if backend["available"] else "[not available]"
        default_marker = " (default)" if backend["default"] else ""
        print(f"  {backend['name']:12} {backend['description']} {status}{default_marker}")

    # Find default
    default = next((b["name"] for b in info if b["default"]), "none")
    print(f"\nDefault: {default}")


def _print_backends_json() -> None:
    """Print backend info in JSON format."""
    info = get_backend_info()
    output = {"backends": info}
    print(json.dumps(output))


DOCKER_DOCS_URL = "https://elijahr.github.io/python-autopxd2/getting-started/docker/"

LIBCLANG_REQUIRED_ERROR = f"""Error: libclang backend not available.
Install libclang with headerkit: python -m headerkit.install_libclang
Or install LLVM/Clang manually (e.g., apt install libclang-dev, brew install llvm)
Or use Docker: {DOCKER_DOCS_URL}
"""


def resolve_backend(
    backend: str,
) -> str:
    """Resolve which backend to use based on options.

    ``auto`` resolves to the registered default backend when that backend is
    available, and otherwise to the first available backend.

    :param backend: Backend option value (auto, libclang, or any registered backend).
    :returns: Resolved backend name.
    :raises SystemExit: If the requested backend, or every backend, is unavailable.
    """
    if backend != "auto":
        if not is_backend_available(backend):
            if backend == "libclang":
                click.echo(LIBCLANG_REQUIRED_ERROR, err=True)
            else:
                click.echo(f"Error: Backend '{backend}' is not available.", err=True)
            raise SystemExit(1)
        return backend

    # "auto" means the default backend when it is usable, else the first backend
    # that reports itself available.  headerkit picks its default at registration
    # time, without regard to whether that backend can actually run here.
    default = get_default_backend()
    if is_backend_available(default):
        return default
    for info in get_backend_info():
        name = str(info["name"])
        if info["available"]:
            return name

    click.echo(LIBCLANG_REQUIRED_ERROR, err=True)
    raise SystemExit(1)


@click.command(
    context_settings=CONTEXT_SETTINGS,
    help="""Generate Cython .pxd declarations from C/C++ headers.""",
)
# === General options ===
@click.option("--version", "-v", is_flag=True, help="Print version and exit.")
@click.option(
    "--backend",
    "-b",
    default="auto",
    help="Parser backend (default: auto, using libclang).",
)
@click.option(
    "--list-backends",
    is_flag=True,
    help="List available backends and exit.",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="JSON output (with --list-backends).",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress warnings.",
)
@click.option(
    "--debug/--no-debug",
    default=False,
    help="Print debug info to stderr.",
)
# === Preprocessing options ===
@click.option(
    "--include-dir",
    "-I",
    multiple=True,
    metavar="<dir>",
    help="Add include search path.",
)
@click.option(
    "--define",
    "-D",
    "defines",
    multiple=True,
    metavar="<macro>",
    help="Define preprocessor macro.",
)
@click.option(
    "--allowlist",
    multiple=True,
    metavar="<pattern>",
    help="Only emit declarations from files matching pattern. Repeatable.",
)
@click.option(
    "--denylist",
    multiple=True,
    metavar="<pattern>",
    help="Never emit declarations from files matching pattern. Wins over --allowlist. Repeatable.",
)
# === Clang / C++ options ===
@click.option(
    "--cpp",
    "-x",
    is_flag=True,
    help="Parse as C++.",
)
@click.option(
    "--std",
    metavar="<std>",
    help="Language standard (e.g., c11, c++17).",
)
@click.option(
    "--clang-arg",
    multiple=True,
    metavar="<arg>",
    help="Pass argument to clang.",
)
@click.option(
    "--no-default-includes",
    is_flag=True,
    help="Disable system include auto-detection.",
)
# === Umbrella header options ===
@click.option(
    "--project-prefix",
    "-P",
    "project_prefixes",
    multiple=True,
    metavar="<path>",
    help="Treat path as project (not system) for umbrella headers. "
    "Declarations from headers matching this prefix will be included. "
    "Can be specified multiple times.",
)
@click.option(
    "--no-recursive",
    is_flag=True,
    help="Disable recursive parsing of umbrella headers.",
)
@click.option(
    "--max-depth",
    type=int,
    default=None,
    metavar="<n>",
    help="Max recursion depth for umbrella headers (default: 10). [libclang]",
)
# === Deprecated (hidden) ===
@click.option(
    "--whitelist",
    "-w",
    multiple=True,
    metavar="<pattern>",
    help="Deprecated alias for --allowlist.",
)
@click.option(
    "--compiler-directive",
    "defines_deprecated",
    multiple=True,
    hidden=True,
)
@click.argument(
    "infile",
    type=click.File("r"),
    required=False,
)
@click.argument(
    "outfile",
    type=click.File("w"),
    default="-",
)
def cli(
    version: bool,
    infile: IO[str] | None,
    outfile: IO[str],
    include_dir: tuple[str, ...],
    defines: tuple[str, ...],
    defines_deprecated: tuple[str, ...],
    debug: bool,
    list_backends: bool,
    json_output: bool,
    backend: str,
    quiet: bool,
    cpp: bool,
    std: str | None,
    clang_arg: tuple[str, ...],
    allowlist: tuple[str, ...],
    denylist: tuple[str, ...],
    whitelist: tuple[str, ...],
    no_default_includes: bool,
    project_prefixes: tuple[str, ...],
    no_recursive: bool,
    max_depth: int | None,
) -> None:
    if version:
        print(__version__)
        return

    if json_output and not list_backends:
        click.echo("Error: --json requires --list-backends", err=True)
        raise SystemExit(1)

    if list_backends:
        if json_output:
            _print_backends_json()
        else:
            _print_backends_human()
        return

    # If infile was not given, check if stdin has piped data
    from_stdin = infile is None or infile.name == "<stdin>"
    if infile is None:
        content = ""
        if not sys.stdin.isatty():
            content = sys.stdin.read()
        if not content:
            click.echo("Error: Missing argument 'INFILE'.", err=True)
            raise SystemExit(2)
        code_input = content
        raw_hdrname = "input.h"
    else:
        code_input = infile.read()
        raw_hdrname = infile.name

    # Auto-detect C++ mode from file extension if not explicitly specified
    cpp_mode = cpp
    cpp_extensions = (".hpp", ".hh", ".hxx", ".H", ".tcc", ".tpp", ".h++")
    if not cpp_mode and raw_hdrname != "<stdin>" and any(raw_hdrname.endswith(ext) for ext in cpp_extensions):
        cpp_mode = True

    resolved_backend = resolve_backend(backend)

    # --std and --clang-arg reach the compiler driver only on libclang; any other
    # backend would drop them silently and emit plausible but wrong output.
    if resolved_backend != "libclang":
        clang_only = []
        if std:
            clang_only.append("--std")
        if clang_arg:
            clang_only.append("--clang-arg")
        if clang_only:
            click.echo(
                f"Error: {' and '.join(clang_only)} {'are' if len(clang_only) > 1 else 'is'} "
                f"only supported by the libclang backend, "
                f"but the resolved backend is '{resolved_backend}'.\n"
                f"Use --backend libclang, or drop the option.",
                err=True,
            )
            raise SystemExit(1)

    # Merge deprecated --compiler-directive into --define
    all_defines = defines + defines_deprecated
    if defines_deprecated and not quiet:
        click.echo(
            "Warning: --compiler-directive is deprecated, use --define or -D instead.",
            err=True,
        )

    # Build extra_args list from CLI options
    extra_args: list[str] = []
    if cpp_mode:
        extra_args.append("-x")
        extra_args.append("c++")
    for define in all_defines:
        extra_args.append(f"-D{define}")
    for directory in include_dir:
        extra_args.append(f"-I{directory}")
    # Add --std if specified
    if std:
        extra_args.append(f"-std={std}")
    # Add any extra clang args
    for arg in clang_arg:
        extra_args.append(arg)

    if whitelist and allowlist:
        click.echo(
            "Error: --whitelist is the deprecated spelling of --allowlist; pass one or the other, not both.",
            err=True,
        )
        raise SystemExit(1)
    if whitelist:
        # Warn here rather than letting translate() do it, so --quiet is honored
        # in the one place that knows about it.
        if not quiet:
            warnings.warn(
                "--whitelist is deprecated, use --allowlist instead.",
                DeprecationWarning,
                stacklevel=1,
            )
        allowlist = whitelist

    allowlist_list = list(allowlist) if allowlist else None
    denylist_list = list(denylist) if denylist else None

    # Convert project_prefixes tuple to tuple or None
    project_prefixes_arg = project_prefixes if project_prefixes else None

    if from_stdin:
        hdrname = "input.hpp" if cpp_mode else "input.h"
    else:
        hdrname = raw_hdrname

    outfile.write(
        translate(
            code=code_input,
            hdrname=hdrname,
            backend=resolved_backend,
            extra_args=extra_args if extra_args else None,
            allowlist=allowlist_list,
            denylist=denylist_list,
            debug=debug,
            use_default_includes=not no_default_includes,
            project_prefixes=project_prefixes_arg,
            recursive_includes=not no_recursive,
            max_depth=max_depth,
        )
    )
