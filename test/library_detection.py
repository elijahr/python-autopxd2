"""Library detection strategies for test infrastructure.

This module provides multi-method library detection supporting:
- pkg-config: Standard Unix library detection
- cmake: CMake config file parsing
- manual: Explicit path specification
- python_module: Python module-based include paths (e.g., numpy.get_include())

Detection methods are tried in order until one succeeds.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DetectionResult:
    """Result of library detection."""

    found: bool
    include_dirs: list[str] = field(default_factory=list)
    library_dirs: list[str] = field(default_factory=list)
    libraries: list[str] = field(default_factory=list)
    cflags: list[str] = field(default_factory=list)
    ldflags: list[str] = field(default_factory=list)
    header_path: str | None = None
    method: str = ""  # Which detection method succeeded


class PkgConfigDetection:
    """Detect library via pkg-config."""

    def detect(self, config: dict[str, Any], system_header: str | None = None) -> DetectionResult | None:
        """Detect library using pkg-config.

        Args:
            config: Detection config with 'package' key
            system_header: Header path to find (e.g., "curl/curl.h")

        Returns:
            DetectionResult if found, None otherwise
        """
        package = config.get("package")
        if not package:
            return None

        if not self._check_exists(package):
            return None

        cflags_str = self._get_cflags(package)
        libs_str = self._get_libs(package)

        include_dirs = self._parse_include_dirs(cflags_str)
        library_dirs = self._parse_library_dirs(libs_str)
        libraries = self._parse_libraries(libs_str)
        other_cflags = self._parse_other_flags(cflags_str, "-I")
        other_ldflags = self._parse_other_flags(libs_str, "-L", "-l")

        header_path = None
        if system_header:
            header_path = self._find_header(system_header, include_dirs)

        return DetectionResult(
            found=True,
            include_dirs=include_dirs,
            library_dirs=library_dirs,
            libraries=libraries,
            cflags=other_cflags,
            ldflags=other_ldflags,
            header_path=header_path,
            method="pkg_config",
        )

    def _check_exists(self, package: str) -> bool:
        """Check if package exists via pkg-config --exists."""
        try:
            subprocess.run(
                ["pkg-config", "--exists", package],
                check=True,
                capture_output=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _get_cflags(self, package: str) -> str:
        """Get compiler flags via pkg-config --cflags."""
        try:
            result = subprocess.run(
                ["pkg-config", "--cflags", package],
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""

    def _get_libs(self, package: str) -> str:
        """Get linker flags via pkg-config --libs."""
        try:
            result = subprocess.run(
                ["pkg-config", "--libs", package],
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""

    def _parse_include_dirs(self, cflags: str) -> list[str]:
        """Extract -I directories from cflags."""
        dirs = []
        for flag in cflags.split():
            if flag.startswith("-I"):
                dirs.append(flag[2:])
        return dirs

    def _parse_library_dirs(self, libs: str) -> list[str]:
        """Extract -L directories from libs."""
        dirs = []
        for flag in libs.split():
            if flag.startswith("-L"):
                dirs.append(flag[2:])
        return dirs

    def _parse_libraries(self, libs: str) -> list[str]:
        """Extract -l library names from libs."""
        libraries = []
        for flag in libs.split():
            if flag.startswith("-l"):
                libraries.append(flag[2:])
        return libraries

    def _parse_other_flags(self, flags_str: str, *exclude_prefixes: str) -> list[str]:
        """Extract flags that don't match exclude prefixes."""
        other = []
        for flag in flags_str.split():
            if not any(flag.startswith(p) for p in exclude_prefixes):
                other.append(flag)
        return other

    def _find_header(self, system_header: str, include_dirs: list[str]) -> str | None:
        """Find header in include directories."""
        # Try pkg-config include dirs first
        for inc_dir in include_dirs:
            path = os.path.join(inc_dir, system_header)
            if os.path.exists(path):
                return path

        # Try standard locations
        for base in ["/usr/include", "/usr/local/include", "/opt/homebrew/include"]:
            path = os.path.join(base, system_header)
            if os.path.exists(path):
                return path

        # Try macOS SDK
        if sys.platform == "darwin":
            try:
                sdk_path = subprocess.check_output(
                    ["xcrun", "--show-sdk-path"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
                path = os.path.join(sdk_path, "usr", "include", system_header)
                if os.path.exists(path):
                    return path
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

        return None


class CMakeDetection:
    """Detect library via CMake config files."""

    def detect(self, config: dict[str, Any], system_header: str | None = None) -> DetectionResult | None:
        """Detect library using CMake config files.

        Args:
            config: Detection config with 'cmake_package' key
            system_header: Header path to find

        Returns:
            DetectionResult if found, None otherwise
        """
        cmake_package = config.get("cmake_package")
        if not cmake_package:
            return None

        # Find cmake config file
        config_path = self._find_cmake_config(cmake_package, config.get("cmake_config_path"))
        if not config_path:
            return None

        # Extract info from cmake config directory structure
        # Most cmake configs are in <prefix>/lib/cmake/<package>/<pkg>-config.cmake
        # So prefix is 4 levels up from the config file
        prefix = config_path.parent.parent.parent.parent

        include_dirs = []
        include_dir = prefix / "include"
        if include_dir.exists():
            include_dirs.append(str(include_dir))

        library_dirs = []
        lib_dir = prefix / "lib"
        if lib_dir.exists():
            library_dirs.append(str(lib_dir))

        # Try to find the library file
        libraries = []
        lib_name = cmake_package.lower()
        for ext in [".dylib", ".so", ".a"]:
            lib_file = lib_dir / f"lib{lib_name}{ext}"
            if lib_file.exists():
                libraries.append(lib_name)
                break

        header_path = None
        if system_header and include_dirs:
            for inc_dir in include_dirs:
                path = os.path.join(inc_dir, system_header)
                if os.path.exists(path):
                    header_path = path
                    break

        return DetectionResult(
            found=True,
            include_dirs=include_dirs,
            library_dirs=library_dirs,
            libraries=libraries,
            cflags=[],
            ldflags=[],
            header_path=header_path,
            method="cmake",
        )

    def _find_cmake_config(self, package: str, hint_path: str | None = None) -> Path | None:
        """Find CMake config file for package."""
        search_paths: list[Path] = []

        if hint_path:
            search_paths.append(Path(hint_path))

        # Standard cmake config locations
        for prefix in ["/opt/homebrew", "/usr/local", "/usr"]:
            prefix_path = Path(prefix)
            # Try various naming conventions
            for name in [package, package.lower(), package.upper()]:
                search_paths.extend(
                    [
                        prefix_path / "lib" / "cmake" / name,
                        prefix_path / "share" / "cmake" / name,
                        prefix_path / "share" / name / "cmake",
                    ]
                )

        for path in search_paths:
            if not path.exists():
                continue
            # Look for config file
            for config_name in [
                f"{package}Config.cmake",
                f"{package.lower()}-config.cmake",
                f"{package}-config.cmake",
            ]:
                config_file = path / config_name
                if config_file.exists():
                    return config_file

        return None


class ManualDetection:
    """Detection via manually specified paths."""

    def detect(self, config: dict[str, Any], system_header: str | None = None) -> DetectionResult | None:
        """Detect library using manual path specification.

        Args:
            config: Detection config with 'include_dirs', 'library_dirs', 'libraries'
            system_header: Header path to find

        Returns:
            DetectionResult if found, None otherwise
        """
        include_dirs = config.get("include_dirs", [])
        if not include_dirs:
            return None

        # Expand and validate paths
        expanded_dirs = []
        for d in include_dirs:
            expanded = os.path.expanduser(os.path.expandvars(d))
            if os.path.isdir(expanded):
                expanded_dirs.append(expanded)

        if not expanded_dirs:
            return None

        # Expand library dirs too
        library_dirs = []
        for d in config.get("library_dirs", []):
            expanded = os.path.expanduser(os.path.expandvars(d))
            if os.path.isdir(expanded):
                library_dirs.append(expanded)

        header_path = None
        if system_header:
            for inc_dir in expanded_dirs:
                path = os.path.join(inc_dir, system_header)
                if os.path.exists(path):
                    header_path = path
                    break

        return DetectionResult(
            found=True,
            include_dirs=expanded_dirs,
            library_dirs=library_dirs,
            libraries=config.get("libraries", []),
            cflags=[],
            ldflags=[],
            header_path=header_path,
            method="manual",
        )


class PythonModuleDetection:
    """Detection via Python module (e.g., numpy.get_include())."""

    def detect(self, config: dict[str, Any], system_header: str | None = None) -> DetectionResult | None:
        """Detect library using Python module include paths.

        Args:
            config: Detection config with 'module' and optional 'include_getter'
            system_header: Header path to find

        Returns:
            DetectionResult if found, None otherwise
        """
        module_name = config.get("module")
        if not module_name:
            return None

        try:
            import importlib

            module = importlib.import_module(module_name)

            include_getter = config.get("include_getter", "get_include()")

            # Handle method calls with arguments like "get_path('include')"
            if "(" in include_getter:
                # eval is safe here - controlled input from config
                include_path = eval(f"module.{include_getter}")  # noqa: S307
            else:
                # Simple attribute access
                include_path = getattr(module, include_getter)

            if isinstance(include_path, str):
                include_dirs = [include_path]
            else:
                include_dirs = list(include_path)

            header_path = None
            if system_header:
                for inc_dir in include_dirs:
                    path = os.path.join(inc_dir, system_header)
                    if os.path.exists(path):
                        header_path = path
                        break

            return DetectionResult(
                found=True,
                include_dirs=include_dirs,
                library_dirs=[],
                libraries=[],
                cflags=[],
                ldflags=[],
                header_path=header_path,
                method="python_module",
            )
        except (ImportError, AttributeError, TypeError):
            return None


# Detection strategy registry
DETECTION_STRATEGIES = {
    "pkg_config": PkgConfigDetection(),
    "cmake": CMakeDetection(),
    "manual": ManualDetection(),
    "python_module": PythonModuleDetection(),
}


def detect_library(config: dict[str, Any]) -> DetectionResult | None:
    """Detect a library using configured methods.

    Tries each detection method in order until one succeeds.
    Falls back to pkg_config shorthand if present.

    Args:
        config: Library configuration dict with either:
            - 'detection': list of detection method configs
            - 'pkg_config': shorthand for pkg-config package name

    Returns:
        DetectionResult if library found, None otherwise

    Example:
        >>> config = {
        ...     "detection": [
        ...         {"type": "pkg_config", "package": "nng"},
        ...         {"type": "cmake", "cmake_package": "nng"},
        ...         {"type": "manual", "include_dirs": ["/opt/homebrew/include"]},
        ...     ],
        ...     "system_header": "nng/nng.h",
        ... }
        >>> result = detect_library(config)
        >>> if result:
        ...     print(f"Found via {result.method}: {result.include_dirs}")
    """
    system_header = config.get("system_header")

    # Try explicit detection methods in order
    if "detection" in config:
        for method_config in config["detection"]:
            method_type = method_config.get("type")
            if method_type not in DETECTION_STRATEGIES:
                continue

            strategy = DETECTION_STRATEGIES[method_type]
            result = strategy.detect(method_config, system_header)
            if result and result.found:
                return result

    # Fallback: try pkg_config shorthand
    if "pkg_config" in config:
        result = DETECTION_STRATEGIES["pkg_config"].detect(
            {"package": config["pkg_config"]},
            system_header,
        )
        if result and result.found:
            return result

    return None
