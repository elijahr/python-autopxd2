import fnmatch
import json
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
    """
    result = []
    for decl in declarations:
        if decl.location is None:
            continue
        for pattern in whitelist:
            if fnmatch.fnmatch(decl.location.file, pattern):
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

    # Parse with backend
    backend_obj = get_backend(backend_name)
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


@click.command(
    context_settings=CONTEXT_SETTINGS,
    help="Generate a Cython pxd file from a C header file.",
)
@click.option("--version", "-v", is_flag=True, help="Print program version and exit.")
@click.option(
    "--include-dir",
    "-I",
    multiple=True,
    metavar="<dir>",
    help="Allow the C preprocessor to search for files in <dir>.",
)
@click.option(
    "--compiler-directive",
    "-D",
    multiple=True,
    help="Additional directives for the C compiler.",
    metavar="<directive>",
)
@click.option(
    "--debug/--no-debug",
    default=False,
    help="Dump preprocessor output to stderr.",
)
@click.option(
    "--list-backends",
    is_flag=True,
    help="Show available backends and exit.",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output in JSON format (for --list-backends).",
)
@click.option(
    "--backend",
    "-b",
    type=click.Choice(["auto", "libclang", "pycparser"], case_sensitive=False),
    default="auto",
    help="Parser backend: auto (default), libclang, pycparser.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress warnings.",
)
@click.option(
    "--cpp",
    "-x",
    is_flag=True,
    help="Parse as C++ (requires libclang backend).",
)
@click.option(
    "--std",
    metavar="<standard>",
    help="Language standard (e.g., c11, c++17). Requires libclang.",
)
@click.option(
    "--clang-arg",
    multiple=True,
    metavar="<arg>",
    help="Pass argument to libclang (can be repeated).",
)
@click.option(
    "--whitelist",
    "-w",
    multiple=True,
    metavar="<file>",
    help="Only generate declarations from specified files.",
)
@click.argument(
    "infile",
    type=click.File("r"),
    default=sys.stdin,
)
@click.argument(
    "outfile",
    type=click.File("w"),
    default=sys.stdout,
)
def cli(
    version: bool,
    infile: IO[str],
    outfile: IO[str],
    include_dir: tuple[str, ...],
    compiler_directive: tuple[str, ...],
    debug: bool,
    list_backends: bool,
    json_output: bool,
    backend: str,
    quiet: bool,
    cpp: bool,
    std: str | None,
    clang_arg: tuple[str, ...],
    whitelist: tuple[str, ...],
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

    resolved_backend = resolve_backend(backend, cpp, quiet)
    validate_libclang_options(resolved_backend, std, clang_arg)

    # Build extra_args list from CLI options
    extra_args: list[str] = []
    for directive in compiler_directive:
        extra_args.append(f"-D{directive}")
    for directory in include_dir:
        extra_args.append(f"-I{directory}")
    # Add --std if specified
    if std:
        extra_args.append(f"-std={std}")
    # Add any extra clang args
    for arg in clang_arg:
        extra_args.append(arg)

    whitelist_list = list(whitelist) if whitelist else None

    outfile.write(
        translate(
            code=infile.read(),
            hdrname=infile.name,
            backend=resolved_backend,
            extra_args=extra_args if extra_args else None,
            whitelist=whitelist_list,
            debug=debug,
        )
    )
