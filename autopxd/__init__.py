import json
import os
import platform
import re
import subprocess
import sys
import tempfile

import click
from pycparser import (
    c_parser,
)

from .declarations import (
    BUILTIN_HEADERS_DIR,
    DARWIN_HEADERS_DIR,
    IGNORE_DECLARATIONS,
)
from .writer import (
    AutoPxd,
)

__version__ = "2.2.2"


def ensure_binary(s, encoding="utf-8", errors="strict"):
    """Coerce **s** to bytes.

    - `str` -> encoded to `bytes`
    - `bytes` -> `bytes`
    """
    if isinstance(s, str):
        return s.encode(encoding, errors)
    if isinstance(s, bytes):
        return s
    raise TypeError(f"not expecting type '{type(s)}'")


def _find_cl():
    """Use vswhere.exe to locate the Microsoft C compiler."""
    host_platform = {
        "X86": "X86",
        "AMD64": "X64",
        "ARM64": "ARM64",
    }.get(platform.machine(), "X86")
    build_platform = {
        "X86": "x86",
        "AMD64": "x64",
        "ARM64": "arm64",
    }.get(platform.machine(), "x86")
    program_files = os.getenv("ProgramFiles(x86)") or os.getenv("ProgramFiles")
    cmd = [
        os.path.join(program_files, r"Microsoft Visual Studio\Installer\vswhere.exe"),
        "-prerelease",
        "-latest",
        "-format",
        "json",
        "-utf8",
        "-find",
        rf"**\bin\Host{host_platform}\{build_platform}\cl.exe",
    ]
    try:
        return json.loads(subprocess.check_output(cmd, encoding="utf-8"))[-1]
    except (OSError, subprocess.CalledProcessError, IndexError) as ex:
        raise RuntimeError("No suitable compiler available") from ex


def _preprocess_msvc(code, extra_cpp_args, debug):
    fd, source_file = tempfile.mkstemp(suffix=".c")
    os.close(fd)
    with open(source_file, "wb") as f:
        f.write(ensure_binary(code))

    result = []
    try:
        cmd = [
            _find_cl(),
            "/E",
            "/X",
            "/utf-8",
            "/D__attribute__(x)=",
            "/D__extension__=",
            "/D__inline=",
            "/D__asm=",
            f"/I{BUILTIN_HEADERS_DIR}",
            *(extra_cpp_args or []),
            source_file,
        ]
        with subprocess.Popen(cmd, stdout=subprocess.PIPE) as proc:
            while proc.poll() is None:
                result.extend(proc.communicate()[0].decode("utf-8").splitlines())
    finally:
        os.unlink(source_file)
    if proc.returncode:
        raise RuntimeError("Invoking C preprocessor failed")

    # Normalise the paths in #line pragmas so that they are correctly matched
    # later on
    def fix_path(match):
        file = match.group(1).replace("\\\\", "\\")
        if file == source_file:
            file = "<stdin>"
        return f'"{file}"'

    res = "\n".join(re.sub(r'"(.+?)"', fix_path, line) for line in result)

    if debug:
        sys.stderr.write(res)
    return res


def preprocess(code, extra_cpp_args=None, debug=False):
    if extra_cpp_args is None:
        extra_cpp_args = []
    if platform.system() == "Darwin":
        cmd = ["clang", "-E", f"-I{DARWIN_HEADERS_DIR}"]
    elif platform.system() == "Windows":
        # Since Windows may not have GCC installed, we check for a cpp command
        # first and if it does not run, then use our MSVC implementation
        try:
            subprocess.check_call(["cpp", "--version"])
        except (OSError, subprocess.CalledProcessError):
            return _preprocess_msvc(code, extra_cpp_args, debug)
        else:
            cmd = ["cpp"]
    else:
        cmd = ["cpp"]
    cmd += (
        [
            "-nostdinc",
            "-D__attribute__(x)=",
            "-D__extension__=",
            "-D__inline=",
            "-D__asm=",
            f"-I{BUILTIN_HEADERS_DIR}",
        ]
        + extra_cpp_args
        + ["-"]
    )
    with subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE) as proc:
        result = [proc.communicate(input=ensure_binary(code))[0]]
        while proc.poll() is None:
            result.append(proc.communicate()[0])
    if proc.returncode:
        raise Exception("Invoking C preprocessor failed")
    res = b"".join(result).decode("utf-8")
    if debug:
        sys.stderr.write(res)
    return res.replace("\r\n", "\n")


def parse(code, extra_cpp_args=None, whitelist=None, debug=False, regex=None):
    if extra_cpp_args is None:
        extra_cpp_args = []
    if regex is None:
        regex = []
    preprocessed = preprocess(code, extra_cpp_args=extra_cpp_args, debug=debug)
    parser = c_parser.CParser()

    for r in regex:
        assert r[0] == "s" and r[-1] == "g" and r[1] == r[-2], 'Only search/replace is allowed: "s/.../.../g"'
        delimiter = r[1]
        assert r.count(delimiter) == 3, 'Malformed regex. Only search/replace is allowed: "s/.../.../g"'
        _, search, replace, _ = r.split(delimiter)

        preprocessed = re.sub(search, replace, preprocessed)

    ast = parser.parse(preprocessed)
    decls = []
    for decl in ast.ext:
        if not hasattr(decl, "name") or decl.name not in IGNORE_DECLARATIONS:
            if not whitelist or os.path.normpath(decl.coord.file) in whitelist:
                decls.append(decl)
    ast.ext = decls
    return ast


def translate(code, hdrname, extra_cpp_args=None, whitelist=None, debug=False, regex=None):
    """
    to generate pxd mappings for only certain files, populate the whitelist parameter
    with the filenames (including relative path):
    whitelist = ['/usr/include/baz.h', 'include/tux.h']

    if the input file is a file that we want in the whitelist, i.e. `whitelist = [hdrname]`,
    the following extra step is required:
    extra_cpp_args += [hdrname]
    """
    if extra_cpp_args is None:
        extra_cpp_args = []
    if regex is None:
        regex = []
    extra_incdir = os.path.dirname(hdrname)
    if extra_incdir:
        extra_cpp_args += [f"-I{extra_incdir}"]
    p = AutoPxd(hdrname)
    p.visit(
        parse(
            code,
            extra_cpp_args=extra_cpp_args,
            whitelist=whitelist,
            debug=debug,
            regex=regex,
        )
    )
    pxd_string = ""
    if p.stdint_declarations:
        cimports = ", ".join(p.stdint_declarations)
        pxd_string += f"from libc.stdint cimport {cimports}\n\n"
    pxd_string += str(p)
    return pxd_string


WHITELIST = []

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


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
    "--regex",
    "-R",
    multiple=True,
    help="Apply sed-style search/replace (s/.../.../g) after preprocessor",
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
    version,
    infile,
    outfile,
    include_dir,
    regex,
    compiler_directive,
    debug,
):
    if version:
        print(__version__)
        return

    extra_cpp_args = [f"-D{directive}" for directive in compiler_directive]
    for directory in include_dir:
        extra_cpp_args += [f"-I{directory}"]

    outfile.write(translate(infile.read(), infile.name, extra_cpp_args, debug=debug, regex=regex))
