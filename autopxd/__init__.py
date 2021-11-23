import os
import platform
import subprocess
import sys

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

__version__ = "2.0.4"


def ensure_binary(s, encoding="utf-8", errors="strict"):
    """Coerce **s** to bytes.

    - `str` -> encoded to `bytes`
    - `bytes` -> `bytes`
    """
    if isinstance(s, str):
        return s.encode(encoding, errors)
    if isinstance(s, bytes):
        return s
    raise TypeError("not expecting type '%s'" % type(s))


def preprocess(code, extra_cpp_args=None, debug=False):
    if extra_cpp_args is None:
        extra_cpp_args = []
    if platform.system() == "Darwin":
        cmd = ["clang", "-E", "-I%s" % DARWIN_HEADERS_DIR]
    else:
        cmd = ["cpp"]
    cmd += (
        [
            "-nostdinc",
            "-D__attribute__(x)=",
            "-D__extension__=",
            "-D__inline=",
            "-D__asm=",
            "-I%s" % BUILTIN_HEADERS_DIR,
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


def parse(code, extra_cpp_args=None, whitelist=None, debug=False):
    if extra_cpp_args is None:
        extra_cpp_args = []
    preprocessed = preprocess(code, extra_cpp_args=extra_cpp_args, debug=debug)
    parser = c_parser.CParser()
    ast = parser.parse(preprocessed)
    decls = []
    for decl in ast.ext:
        if not hasattr(decl, "name") or decl.name not in IGNORE_DECLARATIONS:
            if not whitelist or decl.coord.file in whitelist:
                decls.append(decl)
    ast.ext = decls
    return ast


def translate(code, hdrname, extra_cpp_args=None, whitelist=None, debug=False):
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
    extra_incdir = os.path.dirname(hdrname)
    if extra_incdir:
        extra_cpp_args += ["-I%s" % extra_incdir]
    p = AutoPxd(hdrname)
    p.visit(parse(code, extra_cpp_args=extra_cpp_args, whitelist=whitelist, debug=debug))
    pxd_string = ""
    if p.stdint_declarations:
        pxd_string += "from libc.stdint cimport {:s}\n\n".format(", ".join(p.stdint_declarations))
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
    compiler_directive,
    debug,
):
    if version:
        print(__version__)
        return

    extra_cpp_args = ["-D%s" % directive for directive in compiler_directive]
    for directory in include_dir:
        extra_cpp_args += ["-I%s" % directory]

    outfile.write(translate(infile.read(), infile.name, extra_cpp_args, debug=debug))
