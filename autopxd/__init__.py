import json
import os
import sys
import warnings
from importlib.metadata import (
    version as get_version,
)
from typing import (
    IO,
    Literal,
)

import click
from headerkit.backends import (
    get_backend,
    get_backend_info,
    get_default_backend,
    is_backend_available,
)
from headerkit.transforms.builtin import (
    FilterByHeader,
)
from headerkit.writers.cython import (
    write_pxd,
)

__version__ = get_version("autopxd2")


def _debug_print(msg: str) -> None:
    """Print debug message to stderr."""
    print(f"[autopxd] {msg}", file=sys.stderr)


def _normalize_hdrname(hdrname: str) -> str:
    """Make a header name safe to embed in the generated ``cdef extern from``.

    The name lands inside a Cython string literal, where a backslash starts an
    escape sequence: a Windows path such as ``C:\\Users\\...`` is rejected as an
    invalid ``\\U`` escape. Forward slashes are valid in ``#include`` on every
    Windows compiler, so convert there. On POSIX a backslash is a legal
    filename character and is left alone.
    """
    if os.sep == "\\":
        return hdrname.replace("\\", "/")
    return hdrname


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
    *,
    stub_cimport_prefix: str | None = "headerkit.stubs",
    stub_mode: Literal["cimport", "standalone"] = "cimport",
    nogil: bool | str = False,
    exception_spec: str | None = None,
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
        stub_cimport_prefix: Package prefix for Cython stub cimports.
        stub_mode: Stub type resolution mode (``"cimport"`` or ``"standalone"``).
        nogil: If True, append ``nogil`` to emitted function declarations.
        exception_spec: Optional Cython exception specification (e.g. ``"+"``).

    Returns:
        Cython .pxd file contents.
    """
    hdrname = _normalize_hdrname(hdrname)

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

    backend_obj = get_backend(backend_name)

    if max_depth is not None and not getattr(backend_obj, "follows_includes", backend_name == "libclang"):
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

    # Extract include_dirs from extra_args
    # Handle both "-I/path" and "-I", "/path" formats
    include_dirs: list[str] = []
    other_args: list[str] = []
    args_iter = iter(extra_args or [])
    for arg in args_iter:
        if arg == "-I":
            try:
                include_dirs.append(next(args_iter))
            except StopIteration:
                pass
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

    if allowlist or denylist:
        header = FilterByHeader(
            allowlist=allowlist,
            denylist=denylist,
            header_path=hdrname,
            include_dirs=include_dirs or None,
        ).transform(header)
        if debug:
            _debug_print(f"After allow/deny filtering: {len(header.declarations)} declarations")

    if debug:
        for decl in header.declarations:
            name = getattr(decl, "name", None) or "(anonymous)"
            _debug_print(f"  {type(decl).__name__}: {name}")

    # Generate pxd
    return write_pxd(
        header,
        stub_cimport_prefix=stub_cimport_prefix,
        stub_mode=stub_mode,
        nogil=nogil,
        exception_spec=exception_spec,
    )


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
INSTALL_DOCS_URL = "https://elijahr.github.io/python-autopxd2/getting-started/installation/"

LIBCLANG_REQUIRED_ERROR = f"""Error: libclang backend not available.
To use libclang, install it via your system package manager:
  - Ubuntu/Debian:       sudo apt-get install libclang-dev
  - Alpine Linux (musl): apk add clang-dev
  - Fedora/RHEL:         sudo dnf install clang-devel
  - macOS:               brew install llvm
  - Automated installer: python -m headerkit.install_libclang

Alternatively, use the tree-sitter backend (no LLVM / system library required):
  pip install "autopxd2[treesitter]"
  autopxd --backend tree-sitter <header.h> [<output.pxd>]

Note: The tree-sitter backend is more limited than libclang: it parses the input
file only (does not follow #include directives), does not extract #define macros,
and cannot detect system include paths.

See installation docs: {INSTALL_DOCS_URL}
Or Docker usage: {DOCKER_DOCS_URL}
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
    backend_obj = get_backend(resolved_backend)

    # --std and --clang-arg reach the compiler driver only on backends that support compiler args;
    # any other backend would drop them silently and emit plausible but wrong output.
    if not getattr(backend_obj, "supports_compiler_args", resolved_backend == "libclang"):
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
