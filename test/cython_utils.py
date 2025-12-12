"""Cython compilation validation utilities for tests."""

import shlex
import subprocess
import sys

from Cython.Build.Dependencies import cythonize_one
from Cython.Compiler.Main import CompilationOptions


def validate_cython_compiles(
    pxd_content: str,
    tmp_path,
    cplus: bool = False,
    pkg_config: str | None = None,
    smoke_test: str | None = None,
    header_only: bool = False,
    include_dirs: list[str] | None = None,
) -> None:
    """Validate that pxd content compiles with Cython and optionally links.

    Args:
        pxd_content: The pxd content to validate
        tmp_path: pytest tmp_path fixture
        cplus: If True, compile as C++
        pkg_config: Package name for pkg-config (enables full compile)
        smoke_test: Expression to call in smoke test function
        header_only: If True, compile to .o only (no linking)
        include_dirs: Extra -I paths for compilation

    Raises:
        Cython.Compiler.Errors.CompileError: If compilation fails
        subprocess.CalledProcessError: If gcc/g++ compilation fails
        AssertionError: If smoke test fails
    """
    # Write pxd
    pxd_file = tmp_path / "test.pxd"
    pxd_file.write_text(pxd_content)

    # Write pyx with optional smoke test
    pyx_file = tmp_path / "test.pyx"
    if smoke_test:
        pyx_file.write_text(f"""from test cimport *

def test_smoke():
    cdef result = {smoke_test}
    return result is not None
""")
    else:
        pyx_file.write_text("from test cimport *\n")

    # Cythonize
    src = pyx_file
    dst = tmp_path / ("test.cpp" if cplus else "test.c")
    options = CompilationOptions(
        language_level=3,
        cplus=cplus,
    )
    cythonize_one(str(src), str(dst), None, False, options=options)

    # If no pkg_config and not header_only, just do Cython validation
    if not pkg_config and not header_only:
        return

    # Get compile flags from pkg-config
    cflags = ""
    libs = ""
    if pkg_config:
        try:
            cflags = subprocess.check_output(
                ["pkg-config", "--cflags", pkg_config],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            libs = subprocess.check_output(
                ["pkg-config", "--libs", pkg_config],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(f"pkg-config failed for {pkg_config}: {e}") from e

    # Add include dirs
    if include_dirs:
        for d in include_dirs:
            cflags += f" -I{d}"

    # Get Python flags for extension modules
    try:
        python_cflags = subprocess.check_output(
            [sys.executable + "-config", "--cflags"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        python_ldflags = subprocess.check_output(
            [sys.executable + "-config", "--ldflags"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback for systems without python3-config
        # Use sysconfig to get the correct include path (works in venvs too)
        import sysconfig

        python_cflags = f"-I{sysconfig.get_path('include')}"
        python_ldflags = ""

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
            + shlex.split(cflags)
            + shlex.split(python_cflags)
        )
        subprocess.run(cmd, check=True, capture_output=True, text=True)
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
            + shlex.split(cflags)
            + shlex.split(libs)
            + shlex.split(python_cflags)
            + shlex.split(python_ldflags)
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
