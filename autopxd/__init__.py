import fnmatch
import json
import os
import sys
from importlib.metadata import (
    version as get_version,
)
from typing import (
    IO,
)

import click

from .backends import (
    get_backend,
    get_backend_info,
    get_default_backend,
    is_backend_available,
)
from .ir import (
    Declaration,
)
from .ir_writer import (
    write_pxd,
)

__version__ = get_version("autopxd2")


def _debug_print(msg: str) -> None:
    """Print debug message to stderr."""
    print(f"[autopxd] {msg}", file=sys.stderr)


def _filter_by_whitelist(
    declarations: list[Declaration],
    whitelist: list[str],
) -> list[Declaration]:
    """Filter declarations to only those from whitelisted files.

    Uses fnmatch for pattern matching, supporting glob patterns like:
    - "myheader.h" - exact match
    - "*.h" - all .h files
    - "include/*.h" - all .h files in include/

    Declarations without location info are excluded when whitelist is active.

    Path normalization is applied for cross-platform compatibility:
    - Paths are normalized with os.path.normpath
    - On Windows, case-insensitive comparison is used
    """
    result = []
    # Normalize whitelist patterns
    normalized_whitelist = [os.path.normpath(p) for p in whitelist]

    for decl in declarations:
        if decl.location is None:
            continue
        decl_file = os.path.normpath(decl.location.file)
        for pattern in normalized_whitelist:
            # On Windows, use case-insensitive matching
            if sys.platform == "win32":
                if fnmatch.fnmatch(decl_file.lower(), pattern.lower()):
                    result.append(decl)
                    break
            else:
                if fnmatch.fnmatch(decl_file, pattern):
                    result.append(decl)
                    break
    return result


def translate(
    code: str,
    hdrname: str,
    backend: str = "auto",
    extra_args: list[str] | None = None,
    whitelist: list[str] | None = None,
    debug: bool = False,
    use_default_includes: bool = True,
    project_prefixes: tuple[str, ...] | None = None,
    recursive_includes: bool = True,
    max_depth: int = 10,
) -> str:
    """Generate Cython .pxd from C/C++ header code.

    Args:
        code: C/C++ header source code.
        hdrname: Header filename (used in cdef extern from).
        backend: Backend name ("auto", "pycparser", "libclang").
        extra_args: Extra arguments passed to backend (e.g., ["-I/usr/include"]).
        whitelist: Only include declarations from files matching these patterns.
            Supports fnmatch patterns like "*.h", "include/*.h".
        debug: Print debug info to stderr.
        use_default_includes: If True (default), automatically detect and add
            system include directories when using the libclang backend.
        project_prefixes: [libclang] Tuple of path prefixes to treat as project
            headers (not system). Use this for umbrella headers of libraries
            installed in system locations (e.g., ("/opt/homebrew/include/sodium",)).
        recursive_includes: [libclang] If True (default), detect umbrella headers
            and recursively parse included project headers.
        max_depth: [libclang] Maximum recursion depth for umbrella header
            processing (default: 10).

    Returns:
        Cython .pxd file contents.
    """
    # Resolve backend
    if backend == "auto":
        backend_name = get_default_backend()
    else:
        backend_name = backend

    if debug:
        _debug_print(f"Backend: {backend_name}")
        _debug_print(f"Parsing: {hdrname}")
        if project_prefixes:
            _debug_print(f"Project prefixes: {project_prefixes}")

    # Parse with backend
    backend_obj = get_backend(backend_name)
    # Check if backend supports libclang-specific options
    parse_code = getattr(backend_obj.parse, "__code__", None)
    parse_varnames = parse_code.co_varnames if parse_code else ()

    # Extract include_dirs from extra_args for backends that support it
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

    if "project_prefixes" in parse_varnames:
        # libclang backend with full umbrella header support
        # Using runtime introspection to detect supported kwargs, so ignore type check
        header = backend_obj.parse(
            code,
            hdrname,
            include_dirs=include_dirs or None,
            extra_args=other_args or None,
            use_default_includes=use_default_includes,  # type: ignore[call-arg]
            project_prefixes=project_prefixes,
            recursive_includes=recursive_includes,
            max_depth=max_depth,
        )
    elif "use_default_includes" in parse_varnames:
        # libclang backend without umbrella header params
        header = backend_obj.parse(
            code,
            hdrname,
            extra_args=extra_args or [],
            use_default_includes=use_default_includes,  # type: ignore[call-arg]
        )
    else:
        # pycparser or other backend
        header = backend_obj.parse(code, hdrname, extra_args=extra_args or [])

    if debug:
        _debug_print(f"Found {len(header.declarations)} declarations")

    # Apply whitelist filter
    if whitelist:
        header.declarations = _filter_by_whitelist(header.declarations, whitelist)
        if debug:
            _debug_print(f"After whitelist: {len(header.declarations)} declarations")

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

FALLBACK_WARNING = f"""Warning: libclang not available, falling back to pycparser (legacy).
Limitations: No C++ support, limited preprocessor handling, may fail on complex headers.
To fix: Install LLVM/Clang (e.g., apt install libclang-dev, brew install llvm)
Or use Docker: {DOCKER_DOCS_URL}
"""

LIBCLANG_REQUIRED_ERROR = f"""Error: libclang backend required but not available.
Install LLVM/Clang (e.g., apt install libclang-dev, brew install llvm)
Or use Docker: {DOCKER_DOCS_URL}
"""


def resolve_backend(
    backend: str,
    cpp: bool,
    quiet: bool,
) -> str:
    """Resolve which backend to use based on options.

    :param backend: Backend option value (auto, libclang, pycparser).
    :param cpp: Whether --cpp was specified.
    :param quiet: Whether to suppress warnings.
    :returns: Resolved backend name.
    :raises SystemExit: If required backend is unavailable.
    """
    # Check for conflicting options: --backend pycparser --cpp
    if cpp and backend == "pycparser":
        click.echo(
            "Error: --cpp requires libclang backend (pycparser does not support C++).\n"
            "Remove --backend pycparser or --cpp.",
            err=True,
        )
        raise SystemExit(1)

    # --cpp implies libclang
    if cpp:
        if not is_backend_available("libclang"):
            click.echo(LIBCLANG_REQUIRED_ERROR, err=True)
            raise SystemExit(1)
        return "libclang"

    # Explicit backend selection
    if backend == "libclang":
        if not is_backend_available("libclang"):
            click.echo(LIBCLANG_REQUIRED_ERROR, err=True)
            raise SystemExit(1)
        return "libclang"

    if backend == "pycparser":
        return "pycparser"

    # Auto mode
    if is_backend_available("libclang"):
        return "libclang"

    # Fallback to pycparser with warning
    if not quiet:
        click.echo(FALLBACK_WARNING, err=True)
    return "pycparser"


def validate_libclang_options(
    resolved_backend: str,
    std: str | None,
    clang_arg: tuple[str, ...],
    project_prefixes: tuple[str, ...] | None = None,
    no_recursive: bool = False,
    max_depth: int = 10,
) -> None:
    """Validate that libclang-only options aren't used with pycparser.

    :raises SystemExit: If validation fails.
    """
    if resolved_backend != "libclang":
        if std:
            click.echo(
                f"Error: --std requires libclang backend (got {resolved_backend}).\n"
                "Install LLVM/Clang or remove --std option.",
                err=True,
            )
            raise SystemExit(1)
        if clang_arg:
            click.echo(
                f"Error: --clang-arg requires libclang backend (got {resolved_backend}).\n"
                "Install LLVM/Clang or remove --clang-arg option.",
                err=True,
            )
            raise SystemExit(1)
        if project_prefixes:
            click.echo(
                f"Error: --project-prefix requires libclang backend (got {resolved_backend}).\n"
                "Install LLVM/Clang or remove --project-prefix option.",
                err=True,
            )
            raise SystemExit(1)
        if no_recursive:
            click.echo(
                f"Error: --no-recursive requires libclang backend (got {resolved_backend}).\n"
                "Install LLVM/Clang or remove --no-recursive option.",
                err=True,
            )
            raise SystemExit(1)
        if max_depth != 10:
            click.echo(
                f"Error: --max-depth requires libclang backend (got {resolved_backend}).\n"
                "Install LLVM/Clang or remove --max-depth option.",
                err=True,
            )
            raise SystemExit(1)


@click.command(
    context_settings=CONTEXT_SETTINGS,
    help="""Generate Cython .pxd declarations from C/C++ headers.

\b
Options marked [libclang] require the libclang backend.
""",
)
# === General options ===
@click.option("--version", "-v", is_flag=True, help="Print version and exit.")
@click.option(
    "--backend",
    "-b",
    type=click.Choice(["auto", "libclang", "pycparser"], case_sensitive=False),
    default="auto",
    help="Parser backend (default: auto, prefers libclang).",
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
# === Preprocessing options (both backends) ===
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
    "--whitelist",
    "-w",
    multiple=True,
    metavar="<pattern>",
    help="Only emit from files matching pattern.",
)
# === libclang-only options ===
@click.option(
    "--cpp",
    "-x",
    is_flag=True,
    help="[libclang] Parse as C++.",
)
@click.option(
    "--std",
    metavar="<std>",
    help="[libclang] Language standard (e.g., c11, c++17).",
)
@click.option(
    "--clang-arg",
    multiple=True,
    metavar="<arg>",
    help="[libclang] Pass argument to clang.",
)
@click.option(
    "--no-default-includes",
    is_flag=True,
    help="[libclang] Disable system include auto-detection.",
)
# === Umbrella header options ===
@click.option(
    "--project-prefix",
    "-P",
    "project_prefixes",
    multiple=True,
    metavar="<path>",
    help="[libclang] Treat path as project (not system) for umbrella headers. "
    "Declarations from headers matching this prefix will be included. "
    "Can be specified multiple times.",
)
@click.option(
    "--no-recursive",
    is_flag=True,
    help="[libclang] Disable recursive parsing of umbrella headers.",
)
@click.option(
    "--max-depth",
    type=int,
    default=10,
    metavar="<n>",
    help="[libclang] Max recursion depth for umbrella headers (default: 10).",
)
# === Deprecated (hidden) ===
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
    default=sys.stdout,
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
    whitelist: tuple[str, ...],
    no_default_includes: bool,
    project_prefixes: tuple[str, ...],
    no_recursive: bool,
    max_depth: int,
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

    # Require infile for translation
    if infile is None:
        click.echo("Error: Missing argument 'INFILE'.", err=True)
        raise SystemExit(2)

    resolved_backend = resolve_backend(backend, cpp, quiet)
    validate_libclang_options(resolved_backend, std, clang_arg, project_prefixes, no_recursive, max_depth)

    # Merge deprecated --compiler-directive into --define
    all_defines = defines + defines_deprecated
    if defines_deprecated and not quiet:
        click.echo(
            "Warning: --compiler-directive is deprecated, use --define or -D instead.",
            err=True,
        )

    # Build extra_args list from CLI options
    extra_args: list[str] = []
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

    whitelist_list = list(whitelist) if whitelist else None

    # Convert project_prefixes tuple to tuple or None
    project_prefixes_arg = project_prefixes if project_prefixes else None

    outfile.write(
        translate(
            code=infile.read(),
            hdrname=infile.name,
            backend=resolved_backend,
            extra_args=extra_args if extra_args else None,
            whitelist=whitelist_list,
            debug=debug,
            use_default_includes=not no_default_includes,
            project_prefixes=project_prefixes_arg,
            recursive_includes=not no_recursive,
            max_depth=max_depth,
        )
    )
