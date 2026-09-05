"""Cython compilation validation utilities for tests."""

import shlex
import subprocess
import sys
from typing import Any

from Cython.Build.Dependencies import cythonize_one
from Cython.Compiler.Main import CompilationOptions
from Cython.Compiler.TreeFragment import parse_from_strings

_TOUCH_FUNC = "_autopxd_gate_touch"


def _flatten(node) -> list:
    """Return the statement nodes of a possibly-nested StatListNode."""
    if node is None:
        return []
    if isinstance(node, (list, tuple)):
        out = []
        for item in node:
            out.extend(_flatten(item))
        return out
    if hasattr(node, "stats"):
        out = []
        for stat in node.stats:
            out.extend(_flatten(stat))
        return out
    return [node]


def _declarator_name(declarator) -> tuple[str | None, bool, bool]:
    """Walk a declarator chain to its name.

    Returns (name, is_function, is_templated). A Cython template function is
    spelled ``T maximum[T](T a, T b)``, so its declarator chain carries an
    array declarator; such a name has no address until it is instantiated.
    """
    is_function = False
    has_array = False
    while declarator is not None:
        kind = type(declarator).__name__
        if kind == "CFuncDeclaratorNode":
            is_function = True
        if kind == "CArrayDeclaratorNode":
            has_array = True
        if kind == "CNameDeclaratorNode":
            return declarator.name or None, is_function, is_function and has_array
        declarator = getattr(declarator, "base", None)
    return None, is_function, is_function and has_array


class _Declarations:
    """Names declared by a pxd, grouped by how a smoke test must reference them."""

    def __init__(self) -> None:
        self.types: list[str] = []
        self.fields: list[tuple[str, str]] = []
        self.enum_members: list[str] = []
        self.functions: list[str] = []
        self.variables: list[str] = []


def _collect_declarations(pxd_content: str, cplus: bool) -> _Declarations | None:
    """Parse a pxd with Cython's own parser and collect referenceable names.

    Returns None when the pxd does not parse; the caller then falls back to a
    bare cimport and lets cythonize report the underlying parse error.
    """
    try:
        tree = parse_from_strings("test", pxd_content, level="module_pxd")
    except Exception:  # noqa: BLE001 - any parse error means "cannot derive"
        return None

    decls = _Declarations()

    def visit(nodes) -> None:
        for node in nodes:
            kind = type(node).__name__
            if kind == "CDefExternNode":
                visit(_flatten(node.body))
            elif kind == "CVarDefNode":
                for declarator in node.declarators:
                    name, is_function, is_templated = _declarator_name(declarator)
                    if not name or is_templated:
                        continue
                    (decls.functions if is_function else decls.variables).append(name)
            elif kind == "CStructOrUnionDefNode":
                if not node.name:
                    continue
                decls.types.append(node.name)
                for attr in _flatten(node.attributes):
                    for declarator in getattr(attr, "declarators", []):
                        field, is_function, _ = _declarator_name(declarator)
                        if field and not is_function:
                            decls.fields.append((node.name, field))
            elif kind == "CEnumDefNode":
                if node.name:
                    decls.types.append(node.name)
                for item in _flatten(node.items):
                    if getattr(item, "name", None):
                        decls.enum_members.append(item.name)
            elif kind == "CTypeDefNode":
                name, _, _ = _declarator_name(node.declarator)
                if name:
                    decls.types.append(name)
            elif kind == "CppClassNode":
                # Templated classes cannot be named without arguments, and
                # C++ members are reached through a class instance we cannot
                # construct blind, so only the plain class name is touched.
                if node.name and not getattr(node, "templates", None):
                    decls.types.append(node.name)

    visit(_flatten(tree.body))

    if cplus:
        # An overloaded name makes a bare address-of ambiguous in C++.
        counts: dict[str, int] = {}
        for name in decls.functions:
            counts[name] = counts.get(name, 0) + 1
        decls.functions = [n for n in decls.functions if counts[n] == 1]

    return decls


def _derive_smoke_test_pyx(pxd_content: str, pxd_module: str, cplus: bool) -> str:
    """Build a pyx that forces every declaration in the pxd into the C output.

    Cython only emits a declaration's use into the generated C when a symbol is
    actually referenced. A bare ``cimport *`` therefore compiles the header and
    none of the generated pxd. This synthesises one reference per declared
    symbol so the C compiler checks the pxd against the real header.
    """
    decls = _collect_declarations(pxd_content, cplus)
    if decls is None:
        return f"from {pxd_module} cimport *\n"

    body: list[str] = ["    cdef void *_p = NULL", "    cdef long long _n = 0"]
    slot = {}
    for index, name in enumerate(dict.fromkeys(decls.types)):
        var = f"_t{index}"
        slot[name] = var
        body.append(f"    cdef {name} *{var} = NULL")
        body.append(f"    _p = <void*>{var}")
    for owner, field in dict.fromkeys(decls.fields):
        if owner in slot:
            body.append(f"    _p = <void*>&{slot[owner]}.{field}")
    for name in dict.fromkeys(decls.enum_members):
        body.append(f"    _n += <long long>{name}")
    for name in dict.fromkeys(decls.functions):
        body.append(f"    _p = <void*>&{name}")
    for name in dict.fromkeys(decls.variables):
        # sizeof rather than address-of: object-like macros are emitted as
        # plain variables in the pxd and have no address in C.
        body.append(f"    _n += <long long>sizeof({name})")
    body.append("    _p = _p")
    body.append("    _n = _n")

    indented = "\n".join(body)
    return f"""from {pxd_module} cimport *

cdef void {_TOUCH_FUNC}() noexcept:
{indented}
"""


def _generate_smoke_test_pyx(
    smoke_test: str | dict[str, Any] | None,
    pxd_module: str = "test",
    pxd_content: str | None = None,
    cplus: bool = False,
) -> str:
    """Generate pyx content with smoke test.

    Args:
        smoke_test: Can be:
            - None: derive a body that references every declaration in the pxd
            - str: Simple expression (backward compat)
            - dict with type="expression": Expression
            - dict with type="program": Multi-line code block

    Returns:
        Complete pyx file content as string
    """
    if smoke_test is None:
        return _derive_smoke_test_pyx(pxd_content or "", pxd_module, cplus)

    if isinstance(smoke_test, str):
        # Backward compatible: simple expression
        return f"""from {pxd_module} cimport *

def test_smoke():
    cdef result = {smoke_test}
    return result is not None
"""

    smoke_type = smoke_test.get("type", "expression")

    if smoke_type == "expression":
        expression = smoke_test["expression"]
        return f"""from {pxd_module} cimport *

def test_smoke():
    cdef result = {expression}
    return result is not None
"""

    if smoke_type == "program":
        code = smoke_test["code"]
        # Indent each line of the code block
        lines = code.strip().split("\n")
        indented_lines = ["    " + line for line in lines]
        indented_code = "\n".join(indented_lines)
        return f"""from {pxd_module} cimport *

def test_smoke():
{indented_code}
"""

    raise ValueError(f"Unknown smoke_test type: {smoke_type}")


def validate_cython_compiles(
    pxd_content: str,
    tmp_path,
    cplus: bool = False,
    pkg_config: str | None = None,
    smoke_test: str | dict[str, Any] | None = None,
    header_only: bool = False,
    include_dirs: list[str] | None = None,
    cython_only: bool = False,
) -> None:
    """Validate that pxd content compiles with Cython and optionally links.

    Args:
        pxd_content: The pxd content to validate
        tmp_path: pytest tmp_path fixture
        cplus: If True, compile as C++
        pkg_config: Package name for pkg-config (enables full compile)
        smoke_test: Expression or dict config for smoke test function
        header_only: If True, compile to .o only (no linking)
        include_dirs: Extra -I paths for compilation
        cython_only: If True, only validate Cython→C, skip C compilation

    Raises:
        Cython.Compiler.Errors.CompileError: If compilation fails
        subprocess.CalledProcessError: If gcc/g++ compilation fails
        AssertionError: If smoke test fails
    """
    # Write pxd
    pxd_file = tmp_path / "test.pxd"
    pxd_file.write_text(pxd_content)

    # Generate and write pyx with optional smoke test
    pyx_content = _generate_smoke_test_pyx(smoke_test, pxd_content=pxd_content, cplus=cplus)
    pyx_file = tmp_path / "test.pyx"
    pyx_file.write_text(pyx_content)

    # Cythonize
    src = pyx_file
    dst = tmp_path / ("test.cpp" if cplus else "test.c")
    options = CompilationOptions(
        language_level=3,
        cplus=cplus,
    )
    cythonize_one(str(src), str(dst), None, False, options=options)

    # If cython_only, stop here (for IR tests without C headers)
    if cython_only:
        return

    # If no pkg_config, warn and continue with header_only compilation
    if not pkg_config and not header_only:
        import warnings

        warnings.warn(
            "pkg_config not provided, continuing with header_only compilation (C code will be compiled but not linked)",
            stacklevel=2,
        )
        header_only = True

    # Get compile flags from pkg-config
    # Note: We keep pkg-config output as strings and split them with shlex
    # But we keep paths we construct ourselves as lists to avoid shlex mangling
    # backslashes on Windows
    pkg_cflags: list[str] = []
    pkg_libs: list[str] = []
    if pkg_config:
        try:
            cflags_str = subprocess.check_output(
                ["pkg-config", "--cflags", pkg_config],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            libs_str = subprocess.check_output(
                ["pkg-config", "--libs", pkg_config],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            pkg_cflags = shlex.split(cflags_str)
            pkg_libs = shlex.split(libs_str)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(f"pkg-config failed for {pkg_config}: {e}") from e

    # Add include dirs as separate list items (not string concatenation)
    # to preserve Windows backslashes
    extra_include_flags: list[str] = []
    if include_dirs:
        for d in include_dirs:
            extra_include_flags.append(f"-I{d}")

    # Get Python flags for extension modules
    python_cflags: list[str] = []
    python_ldflags: list[str] = []
    try:
        python_cflags_str = subprocess.check_output(
            [sys.executable + "-config", "--cflags"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        python_ldflags_str = subprocess.check_output(
            [sys.executable + "-config", "--ldflags"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        python_cflags = shlex.split(python_cflags_str)
        python_ldflags = shlex.split(python_ldflags_str)
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback for systems without python3-config
        # Use sysconfig to get the correct include path (works in venvs too)
        import sysconfig

        python_cflags = [f"-I{sysconfig.get_path('include')}"]
        python_ldflags = []

    # Compile
    compiler = "c++" if cplus else "cc"
    c_ext = ".cpp" if cplus else ".c"
    c_file = tmp_path / f"test{c_ext}"

    if header_only:
        # Compile to .o only (no linking)
        cmd = (
            [
                compiler,
                "-c",
                str(c_file),
                "-o",
                str(tmp_path / "test.o"),
                "-fPIC",
            ]
            + extra_include_flags
            + pkg_cflags
            + python_cflags
        )
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"C compilation STDERR: {result.stderr}")
            print(f"C compilation STDOUT: {result.stdout}")
            result.check_returncode()
    else:
        # Full compile to .so
        so_file = tmp_path / "test.so"

        # Use platform-appropriate linker flags
        if sys.platform == "darwin":
            # macOS requires -bundle for Python extensions
            linker_flags = ["-bundle", "-undefined", "dynamic_lookup"]
        else:
            # Linux and other platforms use -shared
            linker_flags = ["-shared"]

        cmd = (
            [
                compiler,
            ]
            + linker_flags
            + [
                "-fPIC",
                str(c_file),
                "-o",
                str(so_file),
            ]
            + extra_include_flags
            + pkg_cflags
            + pkg_libs
            + python_cflags
            + python_ldflags
        )
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"C compilation STDERR: {result.stderr}")
            print(f"C compilation STDOUT: {result.stdout}")
            result.check_returncode()

        # Import and run smoke test
        if smoke_test:
            sys.path.insert(0, str(tmp_path))
            try:
                # Need to use importlib to avoid caching issues
                import importlib.util

                spec = importlib.util.spec_from_file_location("test", str(so_file))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                assert module.test_smoke(), f"Smoke test failed: {smoke_test}"
            finally:
                sys.path.pop(0)
