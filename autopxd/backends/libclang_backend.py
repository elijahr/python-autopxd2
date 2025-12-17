# pylint: disable=cyclic-import
# Cyclic import is intentional - backends register themselves when loaded
"""libclang-based parser backend.

This backend uses libclang (LLVM's C/C++ parser) to parse header files.
It provides full C/C++ support including templates, namespaces, and classes.

Requirements
------------
* System libclang library must be installed
* Python clang2 bindings version must match system libclang version
  (e.g., ``clang2==18.*`` for LLVM 18)

If system libclang is not available, autopxd2 automatically falls back
to the pycparser backend (C99 only).

Advantages over pycparser
-------------------------
* Full C++ support (classes, templates, namespaces)
* Handles complex preprocessor constructs
* Uses the same parser as production compilers
* Better error messages with source locations

Limitations
-----------
* Macro extraction is limited due to Python bindings constraints
* Requires system libclang installation

Example
-------
::

    from autopxd.backends.libclang_backend import LibclangBackend

    backend = LibclangBackend()
    header = backend.parse(code, "myheader.hpp", extra_args=["-std=c++17"])
"""

import glob
import os
import subprocess
import sys

import clang.cindex
from clang.cindex import (
    CursorKind,
    TypeKind,
)

from autopxd.backends import (
    register_backend,
)
from autopxd.ir import (
    Array,
    Constant,
    CType,
    Declaration,
    Enum,
    EnumValue,
    Field,
    Function,
    FunctionPointer,
    Header,
    Parameter,
    Pointer,
    SourceLocation,
    Struct,
    Typedef,
    TypeExpr,
    Variable,
)


def _get_libclang_search_paths() -> list[str]:
    """Get platform-specific paths to search for libclang.

    Returns a list of candidate paths where libclang might be installed,
    ordered by preference (most common/preferred locations first).
    """
    paths: list[str] = []

    if sys.platform == "darwin":
        # Homebrew on Apple Silicon (most common modern setup)
        paths.append("/opt/homebrew/opt/llvm/lib/libclang.dylib")
        # Homebrew versioned installs on Apple Silicon (sorted newest first)
        paths.extend(sorted(glob.glob("/opt/homebrew/Cellar/llvm/*/lib/libclang.dylib"), reverse=True))
        # Homebrew on Intel Macs
        paths.append("/usr/local/opt/llvm/lib/libclang.dylib")
        paths.extend(sorted(glob.glob("/usr/local/Cellar/llvm/*/lib/libclang.dylib"), reverse=True))
        # Xcode Command Line Tools
        paths.append("/Library/Developer/CommandLineTools/usr/lib/libclang.dylib")
        # Xcode.app
        paths.append(
            "/Applications/Xcode.app/Contents/Developer/Toolchains/" "XcodeDefault.xctoolchain/usr/lib/libclang.dylib"
        )

    elif sys.platform == "linux":
        # Debian/Ubuntu versioned LLVM packages (sorted newest first)
        paths.extend(sorted(glob.glob("/usr/lib/llvm-*/lib/libclang.so*"), reverse=True))
        # RHEL/Fedora/CentOS (64-bit)
        paths.append("/usr/lib64/libclang.so")
        # Generic Linux
        paths.append("/usr/lib/libclang.so")
        paths.append("/usr/local/lib/libclang.so")

    elif sys.platform == "win32":
        # Official LLVM installer locations
        paths.append(r"C:\Program Files\LLVM\bin\libclang.dll")
        paths.append(r"C:\Program Files (x86)\LLVM\bin\libclang.dll")

    return paths


def _find_libclang_path() -> str | None:
    """Search common locations for libclang library.

    :returns: Path to libclang if found, None otherwise.
    """
    for path in _get_libclang_search_paths():
        if os.path.isfile(path):
            return path
    return None


# Module-level flag to track if we've already attempted configuration
_libclang_configured: bool = False


def _configure_libclang() -> bool:
    """Configure clang.cindex to find libclang library.

    Attempts default loading first (respects DYLD_LIBRARY_PATH, LD_LIBRARY_PATH,
    etc.), then searches common platform-specific locations.

    :returns: True if libclang is available and configured, False otherwise.
    """
    global _libclang_configured  # pylint: disable=global-statement

    if _libclang_configured:
        # Already configured, just check if it works
        try:
            clang.cindex.Config().get_cindex_library()
            return True
        except clang.cindex.LibclangError:
            return False

    _libclang_configured = True

    # First, try default loading (respects environment variables)
    try:
        clang.cindex.Config().get_cindex_library()
        return True
    except clang.cindex.LibclangError:
        pass

    # Default failed, search common locations
    libclang_path = _find_libclang_path()
    if libclang_path:
        clang.cindex.Config.set_library_file(libclang_path)
        # Verify it works now
        try:
            clang.cindex.Config().get_cindex_library()
            return True
        except clang.cindex.LibclangError:
            return False

    return False


def is_system_libclang_available() -> bool:
    """Check if the system libclang library is available.

    The Python clang2 package is always installed, but it requires the
    system libclang shared library (libclang.so/dylib) to function.
    This checks if that library can be loaded.

    If libclang is not in the default library search path, this function
    automatically searches common platform-specific locations:

    - macOS: Homebrew (Apple Silicon and Intel), Xcode Command Line Tools
    - Linux: /usr/lib/llvm-*/lib, /usr/lib64, /usr/lib, /usr/local/lib
    - Windows: C:\\Program Files\\LLVM\\bin

    :returns: True if system libclang is available and can be used.
    """
    return _configure_libclang()


# Cache for system include directories (computed once per process)
_system_include_cache_c: list[str] | None = None
_system_include_cache_cxx: list[str] | None = None


def get_system_include_dirs(cplus: bool = False) -> list[str]:
    """Get system include directories by querying the system clang compiler.

    This runs ``clang -v -x c -E /dev/null`` (or ``-x c++`` for C++) and
    parses the include paths from its output. The result is cached for
    subsequent calls.

    :param cplus: If True, query for C++ includes (includes libc++ paths).
    :returns: List of ``-I<path>`` arguments for system include directories.
        Returns empty list if clang is not available or detection fails.
    """
    global _system_include_cache_c, _system_include_cache_cxx  # noqa: PLW0603

    cache = _system_include_cache_cxx if cplus else _system_include_cache_c
    if cache is not None:
        return cache

    result_cache: list[str] = []

    try:
        # Use /dev/null on Unix, NUL on Windows
        null_file = "NUL" if sys.platform == "win32" else "/dev/null"
        lang = "c++" if cplus else "c"
        result = subprocess.run(
            ["clang", "-v", "-x", lang, "-E", null_file],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Parse the include paths from stderr
        in_includes = False
        for line in result.stderr.splitlines():
            if "#include <...> search starts here:" in line:
                in_includes = True
                continue
            if in_includes:
                if line.startswith("End of search list"):
                    break
                path = line.strip()
                if path and not path.endswith("(framework directory)"):
                    # Use -isystem for system includes to give local includes priority
                    result_cache.append(f"-isystem{path}")
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    if cplus:
        _system_include_cache_cxx = result_cache
    else:
        _system_include_cache_c = result_cache

    return result_cache


def _is_system_header(header_path: str, project_prefixes: tuple[str, ...] | None = None) -> bool:
    """Check if a header path is a system header.

    System headers are identified by:
    - Being in /usr/include, /usr/local/include
    - Being in SDK paths (MacOSX.sdk, etc.)
    - Being in compiler-specific paths (clang/include, gcc/include)
    - Being in framework directories

    Headers can be whitelisted as "project" headers using project_prefixes.
    This is useful for umbrella headers where the library is installed in
    a system location but we want to recursively parse its sub-headers.

    :param header_path: Path to the header file
    :param project_prefixes: Optional tuple of path prefixes to treat as project (not system)
    :returns: True if this is a system header
    """
    path_str = str(header_path).lower()

    # Check project prefixes first - if path matches, it's NOT a system header
    if project_prefixes:
        for prefix in project_prefixes:
            if prefix.lower() in path_str:
                return False

    # Common system header locations
    system_prefixes = (
        "/usr/include",
        "/usr/local/include",
        "/opt/homebrew/",
        "/opt/local/",
        ".sdk/",
        "/system/library/frameworks",
        "/library/developer/commandlinetools",
        "clang/include",
        "gcc/include",
        "g++/include",
        "c++/include",
    )

    return any(prefix.lower() in path_str for prefix in system_prefixes)


def _is_umbrella_header(
    header: Header,
    threshold: int = 3,
    project_prefixes: tuple[str, ...] | None = None,
) -> bool:
    """Detect if a header is an umbrella header.

    An umbrella header is characterized by:
    - Having multiple included headers (>= threshold)
    - Having few or no declarations of its own (< threshold)

    :param header: The parsed Header IR
    :param threshold: Minimum number of includes to consider umbrella header (default: 3)
    :param project_prefixes: Optional tuple of path prefixes to treat as project (not system)
    :returns: True if this appears to be an umbrella header
    """
    # Count non-system included headers
    project_includes = [h for h in header.included_headers if not _is_system_header(h, project_prefixes)]

    # Umbrella header criteria:
    # 1. Multiple project includes (at least threshold)
    # 2. Few or no declarations in the main file
    return len(project_includes) >= threshold and len(header.declarations) < threshold


def _deduplicate_declarations(declarations: list[Declaration]) -> list[Declaration]:
    """Remove duplicate declarations, keeping the first occurrence.

    Duplicates are identified by:
    - Same type (Struct, Function, Typedef, etc.)
    - Same name
    - Same namespace (for C++)

    Special handling for typedef struct pattern:
    - `typedef struct Foo {...} Foo;` creates both Struct and Typedef
    - We keep only the Struct (with typedef flag set) and remove the Typedef

    :param declarations: List of declarations to deduplicate
    :returns: List with duplicates removed, preserving order
    """
    seen: set[tuple[type, str | None, str | None]] = set()
    unique: list[Declaration] = []

    # First pass: collect struct names that have typedef'd versions
    typedef_struct_names: set[str | None] = set()
    for decl in declarations:
        if isinstance(decl, Typedef):
            # Check if this typedef aliases a struct with the same name
            underlying = decl.underlying_type
            if isinstance(underlying, CType):
                # Handle both "struct Foo" and "Foo" patterns
                type_name = underlying.name
                if type_name.startswith("struct "):
                    struct_name = type_name[7:]
                else:
                    struct_name = type_name

                if struct_name == decl.name:
                    typedef_struct_names.add(decl.name)

    # Second pass: filter declarations and mark typedef'd structs
    for decl in declarations:
        # Build a key: (type, name, namespace)
        decl_type = type(decl)
        decl_name = getattr(decl, "name", None)
        decl_ns = getattr(decl, "namespace", None)

        key = (decl_type, decl_name, decl_ns)

        # Skip typedef if it's a typedef struct pattern
        if isinstance(decl, Typedef) and decl_name in typedef_struct_names:
            continue

        # Mark struct as typedef'd if it has a matching typedef
        if isinstance(decl, Struct) and decl_name in typedef_struct_names:
            # Create a new Struct with is_typedef=True
            # (dataclasses are immutable by default, need to replace)
            from dataclasses import replace

            decl = replace(decl, is_typedef=True)

        if key not in seen:
            seen.add(key)
            unique.append(decl)

    return unique


def _mangle_specialization_name(cpp_name: str) -> str:
    """Convert C++ template specialization to valid Python identifier.

    Examples:
        Container<int> -> Container_int
        Map<int, double> -> Map_int_double
        Foo<int*> -> Foo_int_ptr
    """
    name = cpp_name.replace(" ", "")
    name = name.replace("<", "_").replace(">", "")
    name = name.replace(",", "_")
    name = name.replace("::", "_")
    name = name.replace("*", "_ptr")
    name = name.replace("&", "_ref")
    return name


class ClangASTConverter:
    """Converts libclang cursors to autopxd IR.

    This class walks a libclang translation unit and produces the
    equivalent autopxd IR declarations. It handles C and C++ constructs
    including structs, unions, enums, typedefs, functions, classes, and variables.

    :param filename: Source filename for filtering declarations.
        Only declarations from this file are included (system headers excluded).
    :param project_prefixes: Optional tuple of path prefixes to treat as project headers.
        Declarations from these paths will be included in addition to the main file.

    Note
    ----
    This class is internal to the libclang backend. Use
    :class:`LibclangBackend` for the public API.
    """

    def __init__(self, filename: str, project_prefixes: tuple[str, ...] | None = None) -> None:
        self.filename = filename
        self.project_prefixes = project_prefixes
        self.declarations: list[Declaration] = []
        # Track seen declarations to avoid duplicates
        self._seen: dict[str, bool] = {}
        # Current namespace context (for nested namespace support)
        self._namespace_stack: list[str] = []
        # Store translation unit for dependency resolution
        self._tu: clang.cindex.TranslationUnit | None = None

    @property
    def _current_namespace(self) -> str | None:
        """Get current namespace as '::'-joined string, or None if global."""
        return "::".join(self._namespace_stack) if self._namespace_stack else None

    def _remove_forward_declaration(self, name: str | None, kind: str) -> None:
        """Remove a forward declaration from declarations list.

        Called when we encounter a full definition after having emitted
        a forward declaration. We need to remove the forward declaration
        so it can be replaced by the complete definition.
        """
        if name is None:
            return

        # Find and remove the forward declaration
        for i, decl in enumerate(self.declarations):
            if isinstance(decl, Struct):
                if decl.name == name:
                    # Check if it's a forward declaration (no fields, no methods)
                    if not decl.fields and not decl.methods:
                        # Verify the kind matches
                        is_match = (
                            (kind == "struct" and not decl.is_union and not decl.is_cppclass)
                            or (kind == "union" and decl.is_union)
                            or (kind == "class" and decl.is_cppclass)
                        )
                        if is_match:
                            self.declarations.pop(i)
                            return

    def convert(self, tu: "clang.cindex.TranslationUnit") -> Header:
        """Convert a libclang TranslationUnit to our IR Header.

        Uses smart dependency resolution to include typedefs from included
        headers when they define types used in the main file.
        """
        self._tu = tu

        # Phase 1: Collect main file cursors and identify used/defined types
        main_cursors: list[clang.cindex.Cursor] = []
        used_types: set[str] = set()
        defined_types: set[str] = set()

        for child in tu.cursor.get_children():
            if not self._is_from_target_file(child):
                continue
            main_cursors.append(child)

            # Collect types used by this cursor
            used_types.update(self._collect_used_types(child))

            # Collect types defined by this cursor
            defined_types.update(self._collect_defined_types(child))

        # Phase 2: Calculate needed types (used but not defined in main file)
        needed_types = used_types - defined_types

        # Remove built-in C types that don't need definitions
        # These are either keywords, provided by Cython/libc, or platform-specific
        builtin_types = {
            # C keywords and basic types
            "void",
            "char",
            "short",
            "int",
            "long",
            "float",
            "double",
            "signed",
            "unsigned",
            "bool",
            "bint",
            # stddef.h / stdint.h types (provided by libc.stddef, libc.stdint)
            "size_t",
            "ssize_t",
            "ptrdiff_t",
            "wchar_t",
            "int8_t",
            "int16_t",
            "int32_t",
            "int64_t",
            "uint8_t",
            "uint16_t",
            "uint32_t",
            "uint64_t",
            "intptr_t",
            "uintptr_t",
            "intmax_t",
            "uintmax_t",
            # stdio.h types
            "FILE",
            "fpos_t",
            # stdarg.h types
            "va_list",
            # time.h types
            "time_t",
            "clock_t",
            # sys/types.h common types
            "off_t",
            "pid_t",
            "uid_t",
            "gid_t",
            "mode_t",
            "dev_t",
            "ino_t",
            "nlink_t",
            "blksize_t",
            "blkcnt_t",
            # Platform-specific internal types (should not be exposed)
            "__int64_t",
            "__uint64_t",
            "__int32_t",
            "__uint32_t",
            "__int16_t",
            "__uint16_t",
            "__int8_t",
            "__uint8_t",
            "__darwin_off_t",
            "__darwin_size_t",
            "__darwin_ssize_t",
            "__darwin_time_t",
            "__darwin_clock_t",
            "__darwin_pid_t",
            "__darwin_uid_t",
            "__darwin_gid_t",
            "__darwin_mode_t",
            "__darwin_dev_t",
            "__darwin_ino_t",
            "__darwin_ino64_t",
            # Linux internal types
            "__off_t",
            "__off64_t",
            "__pid_t",
            "__uid_t",
            "__gid_t",
            "__mode_t",
            "__dev_t",
            "__ino_t",
            "__ino64_t",
            "__time_t",
            "__clock_t",
            "__ssize_t",
        }
        needed_types -= builtin_types
        # Also filter out types that start with __ (internal/reserved)
        needed_types = {t for t in needed_types if not t.startswith("__")}

        # Phase 3: Find and process typedefs from included files for needed types
        if needed_types:
            self._resolve_dependencies(tu.cursor, needed_types)

        # Phase 4: Process main file declarations
        for cursor in main_cursors:
            self._process_cursor(cursor)

        return Header(path=self.filename, declarations=self.declarations)

    def _collect_used_types(self, cursor: "clang.cindex.Cursor") -> set[str]:
        """Recursively collect all typedef names used by a cursor."""
        used: set[str] = set()

        # Check the cursor's type
        if cursor.type.kind == TypeKind.TYPEDEF:
            decl = cursor.type.get_declaration()
            if decl.spelling:
                used.add(decl.spelling)

        # Check result type for functions
        if cursor.kind == CursorKind.FUNCTION_DECL:
            used.update(self._extract_typedef_names_from_type(cursor.result_type))
            for arg in cursor.get_arguments():
                used.update(self._extract_typedef_names_from_type(arg.type))

        # Recursively check children
        for child in cursor.get_children():
            # Check field types
            if child.kind == CursorKind.FIELD_DECL or child.kind == CursorKind.PARM_DECL:
                used.update(self._extract_typedef_names_from_type(child.type))
            # Recurse
            used.update(self._collect_used_types(child))

        return used

    def _extract_typedef_names_from_type(self, clang_type: "clang.cindex.Type") -> set[str]:
        """Extract typedef names from a type, including through pointers/arrays."""
        names: set[str] = set()
        kind = clang_type.kind

        if kind == TypeKind.TYPEDEF:
            decl = clang_type.get_declaration()
            if decl.spelling:
                names.add(decl.spelling)
            # Also check the underlying type for chained typedefs
            underlying = clang_type.get_canonical()
            if underlying.kind == TypeKind.TYPEDEF:
                udecl = underlying.get_declaration()
                if udecl.spelling:
                    names.add(udecl.spelling)
        elif kind == TypeKind.POINTER:
            pointee = clang_type.get_pointee()
            names.update(self._extract_typedef_names_from_type(pointee))
        elif kind in (
            TypeKind.CONSTANTARRAY,
            TypeKind.INCOMPLETEARRAY,
            TypeKind.VARIABLEARRAY,
            TypeKind.DEPENDENTSIZEDARRAY,
        ):
            element = clang_type.element_type
            names.update(self._extract_typedef_names_from_type(element))
        elif kind == TypeKind.ELABORATED:
            named = clang_type.get_named_type()
            names.update(self._extract_typedef_names_from_type(named))

        return names

    def _collect_defined_types(self, cursor: "clang.cindex.Cursor") -> set[str]:
        """Collect type names defined by a cursor."""
        defined: set[str] = set()
        kind = cursor.kind

        if (
            kind == CursorKind.TYPEDEF_DECL
            or kind in (CursorKind.STRUCT_DECL, CursorKind.UNION_DECL)
            or kind == CursorKind.ENUM_DECL
            or kind in (CursorKind.CLASS_DECL, CursorKind.CLASS_TEMPLATE)
        ):
            if cursor.spelling:
                defined.add(cursor.spelling)

        return defined

    def _resolve_dependencies(
        self,
        root_cursor: "clang.cindex.Cursor",
        needed_types: set[str],
    ) -> None:
        """Find and process typedefs from included files for needed types."""
        # Build a map of typedef name -> cursor for all non-main-file typedefs
        typedef_map: dict[str, clang.cindex.Cursor] = {}

        for child in root_cursor.get_children():
            if child.kind == CursorKind.TYPEDEF_DECL:
                if not self._is_from_target_file(child) and child.spelling:
                    typedef_map[child.spelling] = child

        # Build dependency graph and process in topological order
        def get_dependencies(type_name: str) -> set[str]:
            """Get types that this typedef depends on.

            This includes:
            1. Types referenced directly in the typedef's underlying type
            2. Types used by structs/unions that the typedef aliases
            """
            if type_name not in typedef_map:
                return set()
            cursor = typedef_map[type_name]
            underlying = cursor.underlying_typedef_type
            deps = self._extract_typedef_names_from_type(underlying)

            # If the underlying type is a struct/union, also collect types used by it
            # This handles cases like: typedef struct foo_s { bar_t field; } foo_t;
            # where bar_t needs to be resolved before foo_t
            decl = underlying.get_declaration()
            if decl.kind in (CursorKind.STRUCT_DECL, CursorKind.UNION_DECL):
                deps.update(self._collect_used_types(decl))

            # Only return deps that are also in typedef_map (defined in included files)
            return deps & set(typedef_map.keys())

        # System types that should not be emitted but can satisfy dependencies
        system_types_not_to_emit = {
            "size_t",
            "ssize_t",
            "ptrdiff_t",
            "wchar_t",
            "int8_t",
            "int16_t",
            "int32_t",
            "int64_t",
            "uint8_t",
            "uint16_t",
            "uint32_t",
            "uint64_t",
            "intptr_t",
            "uintptr_t",
            "intmax_t",
            "uintmax_t",
            "off_t",
            "time_t",
            "clock_t",
            "pid_t",
            "uid_t",
            "gid_t",
            "mode_t",
            "dev_t",
            "ino_t",
            "nlink_t",
            "blksize_t",
            "blkcnt_t",
        }

        # Expand needed_types to include all transitive dependencies
        all_needed: set[str] = set()
        to_expand = list(needed_types)
        while to_expand:
            type_name = to_expand.pop()
            if type_name in all_needed:
                continue
            if type_name in typedef_map:
                all_needed.add(type_name)
                deps = get_dependencies(type_name)
                to_expand.extend(deps - all_needed)

        # Filter out system types that shouldn't be emitted
        all_needed -= system_types_not_to_emit

        # Process in dependency order using simple topological sort
        processed: set[str] = set(system_types_not_to_emit)  # Treat system types as already processed
        # Sort alphabetically for deterministic output
        to_process = sorted(all_needed)
        max_iterations = len(to_process) * len(to_process) + 1  # Safety limit

        iterations = 0
        while to_process and iterations < max_iterations:
            iterations += 1
            type_name = to_process.pop(0)
            if type_name in processed:
                continue

            # Check if all dependencies are processed (system types count as processed)
            deps = get_dependencies(type_name)
            unmet_deps = deps - processed - system_types_not_to_emit
            if unmet_deps:
                # Re-queue and try again later
                to_process.append(type_name)
                continue

            # All dependencies met, process this typedef
            processed.add(type_name)
            if type_name in typedef_map:
                self._process_typedef(typedef_map[type_name])

    def _process_children(self, cursor: "clang.cindex.Cursor") -> None:
        """Process all children of a cursor."""
        for child in cursor.get_children():
            # Only process declarations from the target file
            if not self._is_from_target_file(child):
                continue
            self._process_cursor(child)

    def _is_from_target_file(self, cursor: "clang.cindex.Cursor") -> bool:
        """Check if cursor is from the target file or a whitelisted project path.

        Returns True if cursor is from:
        1. The main target file (self.filename), OR
        2. A path matching one of the project_prefixes (for umbrella headers)
        """
        loc = cursor.location
        if loc.file is None:
            return False

        file_path = loc.file.name

        # Check main file
        if file_path == self.filename:
            return True

        # Check project prefixes (for umbrella headers)
        if self.project_prefixes:
            for prefix in self.project_prefixes:
                if prefix.lower() in file_path.lower():
                    return True

        return False

    def _process_cursor(self, cursor: "clang.cindex.Cursor") -> None:
        """Process a top-level cursor."""
        kind = cursor.kind

        if kind == CursorKind.STRUCT_DECL:
            self._process_struct(cursor, is_union=False)
        elif kind == CursorKind.UNION_DECL:
            self._process_struct(cursor, is_union=True)
        elif kind == CursorKind.ENUM_DECL:
            self._process_enum(cursor)
        elif kind == CursorKind.FUNCTION_DECL:
            self._process_function(cursor)
        elif kind == CursorKind.TYPEDEF_DECL:
            self._process_typedef(cursor)
        elif kind == CursorKind.VAR_DECL:
            self._process_variable(cursor)
        elif kind == CursorKind.CLASS_DECL:
            # C++ class - uses cppclass in Cython
            self._process_struct(cursor, is_union=False, is_cppclass=True)
        elif kind == CursorKind.CLASS_TEMPLATE:
            # C++ class template
            self._process_class_template(cursor)
        elif kind == CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION:
            # C++ partial template specialization - emit comment explaining limitation
            self._process_partial_specialization(cursor)
        elif kind == CursorKind.NAMESPACE:
            # C++ namespace - recurse into it with namespace context
            self._process_namespace(cursor)
        elif kind == CursorKind.MACRO_DEFINITION:
            # #define macro - extract numeric constants
            self._process_macro(cursor)

    def _process_namespace(self, cursor: "clang.cindex.Cursor") -> None:
        """Process a C++ namespace declaration."""
        ns_name = cursor.spelling
        if ns_name:
            self._namespace_stack.append(ns_name)
            self._process_children(cursor)
            self._namespace_stack.pop()

    def _process_macro(self, cursor: "clang.cindex.Cursor") -> None:
        """Process a #define macro declaration.

        Extracts various macro types as Constants:
        - Simple integers: ``#define SIZE 100``
        - Integers with suffixes: ``#define SIZE 100ULL``
        - Hex/octal/binary: ``#define MASK 0xFF``
        - Floating point: ``#define PI 3.14159``
        - String literals: ``#define VERSION "1.0"``
        - Expression macros: ``#define TOTAL (A + B)``

        Function-like macros (with parameters) are skipped.
        """
        name = cursor.spelling
        if not name:
            return

        # Skip if already processed
        key = f"macro:{name}"
        if key in self._seen:
            return
        self._seen[key] = True

        # Get tokens - first token is the macro name, rest is the value
        tokens = list(cursor.get_tokens())
        if len(tokens) < 2:
            # No value (e.g., #define EMPTY)
            return

        # Check for function-like macro: name followed by '('
        # Function-like macros have the pattern: NAME ( params ) body
        if len(tokens) >= 2 and tokens[1].spelling == "(":
            # Could be function-like macro OR expression starting with paren
            # Function-like: #define MAX(a,b) ...
            # Expression: #define X (1+2)
            # Check if there's an identifier after the opening paren
            if len(tokens) >= 3:
                third = tokens[2].spelling
                # If it's an identifier followed by comma or close paren, it's function-like
                if third.isidentifier() or third == ")":
                    # Look ahead for comma or close paren pattern
                    for i, tok in enumerate(tokens[2:], start=2):
                        if tok.spelling == ")":
                            # Check if this closes the parameter list (more tokens after)
                            if i + 1 < len(tokens):
                                # Has body after params - function-like macro
                                return
                            break
                        if tok.spelling == ",":
                            # Has comma in parens - function-like macro
                            return

        # Determine macro type from tokens
        macro_type, value = self._analyze_macro_tokens(tokens[1:])
        if macro_type is None:
            return

        loc = cursor.location
        location = SourceLocation(
            file=loc.file.name if loc.file else self.filename,
            line=loc.line,
            column=loc.column,
        )

        self.declarations.append(
            Constant(
                name=name,
                value=value,
                type=macro_type,
                is_macro=True,
                location=location,
            )
        )

    def _analyze_macro_tokens(
        self, tokens: list["clang.cindex.Token"]
    ) -> tuple[CType | None, int | float | str | None]:
        """Analyze macro value tokens to determine type.

        Returns:
            Tuple of (CType, value) or (None, None) if unsupported.
        """
        if len(tokens) == 1:
            return self._analyze_single_token(tokens[0].spelling)

        # Multiple tokens - analyze as expression
        return self._analyze_expression_tokens(tokens)

    def _analyze_single_token(self, token: str) -> tuple[CType | None, int | float | str | None]:
        """Analyze a single-token macro value."""
        # String literal
        if token.startswith('"') and token.endswith('"'):
            return CType("char", ["const"]), token

        # Character literal
        if token.startswith("'") and token.endswith("'"):
            return CType("char"), token

        # Try numeric with suffix stripping
        value, is_float = self._parse_numeric_with_suffix(token)
        if value is not None:
            if is_float:
                return CType("double"), value
            return CType("int"), value

        return None, None

    def _parse_numeric_with_suffix(self, token: str) -> tuple[int | float | None, bool]:
        """Parse a numeric token, stripping type suffixes.

        Returns:
            Tuple of (value, is_float) or (None, False) if not numeric.
        """
        # Check for float first (has decimal point or exponent)
        if "." in token or "e" in token.lower():
            # Strip float suffixes: f, F, l, L
            if token.endswith(("f", "F", "l", "L")):
                token = token[:-1]
            try:
                return float(token), True
            except ValueError:
                return None, False

        # Integer - strip suffixes: ULL, LL, UL, LU, U, L (case insensitive)
        upper = token.upper()
        for suffix in ("ULL", "LLU", "LL", "UL", "LU", "U", "L"):
            if upper.endswith(suffix):
                token = token[: -len(suffix)]
                break

        # Try to parse as integer
        try:
            if token.startswith(("0x", "0X")):
                return int(token, 16), False
            if token.startswith(("0b", "0B")):
                return int(token, 2), False
            if token.startswith("0") and len(token) > 1 and token[1:].isdigit():
                return int(token, 8), False
            return int(token), False
        except ValueError:
            return None, False

    def _analyze_expression_tokens(
        self, tokens: list["clang.cindex.Token"]
    ) -> tuple[CType | None, int | float | str | None]:
        """Analyze a multi-token expression macro.

        For expressions like (A + B), we detect if it looks like an integer
        or float expression and declare the appropriate type.
        """
        # Collect all token spellings
        spellings = [t.spelling for t in tokens]

        # Check for string concatenation or complex string expressions
        has_string = any(s.startswith('"') for s in spellings)
        if has_string:
            # String expression - skip for now (complex to handle)
            return None, None

        # Check if expression contains float indicators
        has_float = False
        for s in spellings:
            if "." in s or "e" in s.lower():
                # Could be a float literal
                val, is_float = self._parse_numeric_with_suffix(s)
                if is_float:
                    has_float = True
                    break

        # Valid expression tokens for integer/float expressions
        valid_operators = {"+", "-", "*", "/", "%", "&", "|", "^", "~", "<<", ">>", "(", ")", "<", ">", "!", "?", ":"}

        for spelling in spellings:
            # Skip operators and parentheses
            if spelling in valid_operators:
                continue
            # Skip numeric literals (including with suffixes)
            val, _ = self._parse_numeric_with_suffix(spelling)
            if val is not None:
                continue
            # Skip identifiers (other macro references)
            if spelling.isidentifier():
                continue
            # Unknown token - not a simple expression
            return None, None

        # Expression looks valid - determine type
        # We don't evaluate, just declare the existence
        if has_float:
            return CType("double"), None
        return CType("int"), None

    def _process_struct(self, cursor: "clang.cindex.Cursor", is_union: bool, is_cppclass: bool = False) -> None:
        """Process a struct/union/class declaration."""
        name = cursor.spelling or None

        # Check if this is a template specialization
        # Method 1: Check specialized_template attribute (reliable when available)
        is_specialization = False
        try:
            specialized_template = cursor.specialized_template
            if specialized_template is not None and specialized_template != cursor:
                is_specialization = True
        except AttributeError:
            pass

        # Method 2: Fallback detection using displayname pattern
        # If cursor is CLASS_DECL/STRUCT_DECL (not CLASS_TEMPLATE) but displayname
        # contains template args like "Vector<bool>", it's a specialization
        if not is_specialization and is_cppclass:
            displayname = cursor.displayname
            if "<" in displayname and ">" in displayname:
                # This is a specialization - displayname has template args but
                # it's not a CLASS_TEMPLATE (which would be the primary template)
                if cursor.kind != CursorKind.CLASS_TEMPLATE:
                    is_specialization = True

        # Determine the key prefix for deduplication
        if is_cppclass:
            key_prefix = "class"
        elif is_union:
            key_prefix = "union"
        else:
            key_prefix = "struct"

        # For specializations, use display name for deduplication key
        if is_specialization:
            key = f"{key_prefix}:{cursor.displayname}"
        else:
            key = f"{key_prefix}:{name}"

        # Forward declarations have no definition - output as opaque type
        is_forward_decl = not cursor.is_definition()

        # Handle seen tracking:
        # - If we've seen a definition, skip any subsequent declarations
        # - If we've only seen a forward declaration, a definition should replace it
        definition_key = f"{key}:definition"
        if definition_key in self._seen:
            # Already have a definition, skip this
            return

        if is_forward_decl:
            # Only emit forward declaration if we haven't seen this type at all
            if key in self._seen:
                return
            self._seen[key] = True
        else:
            # This is a definition - mark it and remove any prior forward declaration
            self._seen[definition_key] = True
            if key in self._seen:
                # We previously emitted a forward declaration - need to remove it
                # and replace with the definition
                self._remove_forward_declaration(name, key_prefix)
            self._seen[key] = True

        fields: list[Field] = []
        methods: list[Function] = []
        if not is_forward_decl:
            for child in cursor.get_children():
                if child.kind == CursorKind.FIELD_DECL:
                    field = self._convert_field(child)
                    if field:
                        fields.append(field)
                elif child.kind == CursorKind.CXX_METHOD and is_cppclass:
                    method = self._convert_method(child)
                    if method:
                        methods.append(method)

        # Handle template specialization
        cpp_name = None
        if is_specialization:
            cpp_name = cursor.displayname
            name = _mangle_specialization_name(cpp_name)

        struct = Struct(
            name=name,
            fields=fields,
            methods=methods,
            is_union=is_union,
            is_cppclass=is_cppclass,
            namespace=self._current_namespace,
            cpp_name=cpp_name,
            location=self._get_location(cursor),
        )
        self.declarations.append(struct)

    def _process_class_template(self, cursor: "clang.cindex.Cursor") -> None:
        """Process a C++ class template declaration."""
        name = cursor.spelling or None
        if not name:
            return

        # Skip if already processed
        key = f"template:{name}"
        if key in self._seen:
            return
        self._seen[key] = True

        # Extract template type parameters and track non-type parameters
        template_params: list[str] = []
        nontype_params: list[tuple[str, str]] = []
        fields: list[Field] = []
        methods: list[Function] = []
        notes: list[str] = []
        inner_typedefs: dict[str, str] = {}

        for child in cursor.get_children():
            if child.kind == CursorKind.TEMPLATE_TYPE_PARAMETER:
                param_name = child.spelling or f"T{len(template_params)}"
                template_params.append(param_name)
            elif child.kind == CursorKind.TEMPLATE_NON_TYPE_PARAMETER:
                # Non-type template parameters (e.g., template<int N>)
                # Cython doesn't support these directly, so track for note
                param_name = child.spelling or "N"
                param_type = child.type.spelling
                nontype_params.append((param_name, param_type))
            elif child.kind == CursorKind.TYPEDEF_DECL:
                # Extract inner typedefs (e.g., typedef Iterator<T, PT> iterator)
                typedef_name = child.spelling
                underlying = child.underlying_typedef_type.spelling
                if typedef_name and underlying:
                    inner_typedefs[typedef_name] = underlying
            elif child.kind == CursorKind.FIELD_DECL:
                field = self._convert_field(child)
                if field:
                    fields.append(field)
            elif child.kind == CursorKind.CXX_METHOD:
                method = self._convert_method(child)
                if method:
                    methods.append(method)

        if not template_params:
            # No template parameters found - treat as regular class
            return

        # Add note if non-type parameters exist
        if nontype_params:
            for param_name, param_type in nontype_params:
                notes.append(
                    f"NOTE: Template has non-type parameter '{param_name}' ({param_type}). "
                    "Cython does not support non-type template parameters. "
                    "Use specific instantiations as needed."
                )

        struct = Struct(
            name=name,
            fields=fields,
            methods=methods,
            is_union=False,
            is_cppclass=True,
            namespace=self._current_namespace,
            template_params=template_params,
            notes=notes,
            inner_typedefs=inner_typedefs,
            location=self._get_location(cursor),
        )
        self.declarations.append(struct)

    def _process_partial_specialization(self, cursor: "clang.cindex.Cursor") -> None:
        """Process a C++ partial template specialization.

        Partial specializations cannot be represented in Cython, but we emit
        a comment to note their existence so users are aware.
        """
        display_name = cursor.displayname or cursor.spelling or "unknown"

        # Get the base template name (e.g., "Container" from "Container<T*>")
        base_name = cursor.spelling or None

        # Skip if no name
        if not base_name:
            return

        # Create a unique key for this partial specialization
        key = f"partial_spec:{display_name}"
        if key in self._seen:
            return
        self._seen[key] = True

        # Try to find the base template to add a note to it
        # Look for existing template with the base name
        for decl in self.declarations:
            if isinstance(decl, Struct) and decl.name == base_name and decl.template_params:
                # Add note about partial specialization
                note = (
                    f"NOTE: Partial specialization {display_name} exists in C++ "
                    "but cannot be declared in Cython. Use specific instantiations."
                )
                if note not in decl.notes:
                    decl.notes.append(note)
                return

        # If we didn't find the base template, emit a standalone note comment
        # by creating a minimal struct with just the note
        # This is a fallback - ideally the base template should exist
        note = (
            f"NOTE: Partial specialization {display_name} exists in C++ "
            "but cannot be declared in Cython. Use specific instantiations."
        )
        struct = Struct(
            name=base_name,
            fields=[],
            methods=[],
            is_union=False,
            is_cppclass=True,
            namespace=self._current_namespace,
            notes=[note],
            location=self._get_location(cursor),
        )
        self.declarations.append(struct)

    def _process_enum(self, cursor: "clang.cindex.Cursor") -> None:
        """Process an enum declaration."""
        name = cursor.spelling or None

        # Skip forward declarations
        if not cursor.is_definition():
            return

        # Skip if already processed
        key = f"enum:{name}"
        if name and key in self._seen:
            return
        if name:
            self._seen[key] = True

        values: list[EnumValue] = []
        for child in cursor.get_children():
            if child.kind == CursorKind.ENUM_CONSTANT_DECL:
                values.append(EnumValue(name=child.spelling, value=child.enum_value))

        enum = Enum(name=name, values=values, location=self._get_location(cursor))
        self.declarations.append(enum)

    def _process_function(self, cursor: "clang.cindex.Cursor") -> None:
        """Process a function declaration."""
        name = cursor.spelling
        if not name:
            return

        # Skip if already processed
        key = f"function:{name}"
        if key in self._seen:
            return
        self._seen[key] = True

        return_type = self._convert_type(cursor.result_type)
        if not return_type:
            return

        parameters: list[Parameter] = []
        is_variadic = cursor.type.is_function_variadic()

        for arg in cursor.get_arguments():
            param_type = self._convert_type(arg.type)
            if param_type:
                # Skip void parameter
                if isinstance(param_type, CType) and param_type.name == "void":
                    continue
                parameters.append(Parameter(name=arg.spelling or None, type=param_type))

        func = Function(
            name=name,
            return_type=return_type,
            parameters=parameters,
            is_variadic=is_variadic,
            namespace=self._current_namespace,
            location=self._get_location(cursor),
        )
        self.declarations.append(func)

    def _convert_method(self, cursor: "clang.cindex.Cursor") -> Function | None:
        """Convert a C++ method to a Function IR node."""
        name = cursor.spelling
        if not name:
            return None

        return_type = self._convert_type(cursor.result_type)
        if not return_type:
            return None

        parameters: list[Parameter] = []
        is_variadic = cursor.type.is_function_variadic()

        for arg in cursor.get_arguments():
            param_type = self._convert_type(arg.type)
            if param_type:
                # Skip void parameter
                if isinstance(param_type, CType) and param_type.name == "void":
                    continue
                parameters.append(Parameter(name=arg.spelling or None, type=param_type))

        return Function(
            name=name,
            return_type=return_type,
            parameters=parameters,
            is_variadic=is_variadic,
            location=self._get_location(cursor),
        )

    def _process_typedef(self, cursor: "clang.cindex.Cursor") -> None:
        """Process a typedef declaration."""
        name = cursor.spelling
        if not name:
            return

        # Skip if already processed
        key = f"typedef:{name}"
        if key in self._seen:
            return
        self._seen[key] = True

        underlying = cursor.underlying_typedef_type

        # Skip typedefs that reference compiler builtin types
        # These are internal to GCC/Clang and cannot be used in Cython
        underlying_spelling = underlying.spelling
        if underlying_spelling.startswith("__builtin_"):
            return

        # Special handling for struct/union typedefs that have inline definitions
        # e.g., typedef struct foo { int x; } foo_t;
        # We need to emit the struct definition first, then the typedef
        if underlying.kind in (TypeKind.RECORD, TypeKind.ELABORATED):
            # Get the actual record type
            record_type = underlying
            if underlying.kind == TypeKind.ELABORATED:
                record_type = underlying.get_named_type()

            if record_type.kind == TypeKind.RECORD:
                decl = record_type.get_declaration()
                # Check if this is a struct/union with a definition (not forward decl)
                if decl.is_definition():
                    struct_name = decl.spelling
                    # Only emit the struct if we haven't emitted a definition
                    key_prefix = "union" if decl.kind == CursorKind.UNION_DECL else "struct"
                    struct_key = f"{key_prefix}:{struct_name}"
                    definition_key = f"{struct_key}:definition"

                    # Check if this is typedef struct Foo {...} Foo; pattern
                    is_typedef_pattern = struct_name == name

                    # Check if we already have a definition - if so, update it
                    if definition_key in self._seen:
                        # Struct was already processed - update its is_typedef flag if needed
                        if is_typedef_pattern:
                            # Find and update the existing struct
                            from dataclasses import replace

                            for i, existing_decl in enumerate(self.declarations):
                                if isinstance(existing_decl, Struct) and existing_decl.name == struct_name:
                                    # Replace with typedef'd version
                                    self.declarations[i] = replace(existing_decl, is_typedef=True)
                                    break
                        # Don't create another struct, but might still need typedef
                    else:
                        # First time seeing this struct - create it
                        self._seen[struct_key] = True
                        self._seen[definition_key] = True  # Mark definition as seen
                        is_union = decl.kind == CursorKind.UNION_DECL

                        fields: list[Field] = []
                        for child in decl.get_children():
                            if child.kind == CursorKind.FIELD_DECL:
                                field = self._convert_field(child)
                                if field:
                                    fields.append(field)

                        struct = Struct(
                            name=struct_name or None,
                            fields=fields,
                            methods=[],
                            is_union=is_union,
                            is_cppclass=False,
                            namespace=self._current_namespace,
                            location=self._get_location(decl),
                            is_typedef=is_typedef_pattern,
                        )
                        self.declarations.append(struct)

                    # If struct name == typedef name, we've already handled it above
                    # Only create separate typedef if names differ
                    if struct_name and struct_name != name:
                        underlying_type: CType | Pointer | Array | FunctionPointer = CType(
                            name=struct_name
                        )  # Use just the name, not "struct name"

                        typedef = Typedef(
                            name=name,
                            underlying_type=underlying_type,
                            location=self._get_location(cursor),
                        )
                        self.declarations.append(typedef)
                    return

        # Resolve compile-time expressions (decltype, sizeof) to canonical types
        # This handles cases like: typedef decltype(nullptr) nullptr_t;
        underlying_spelling = underlying.spelling
        if "decltype(" in underlying_spelling or "sizeof(" in underlying_spelling:
            # Try to resolve to canonical type
            canonical = underlying.get_canonical()
            canonical_type = self._convert_type(canonical)

            if canonical_type:
                # Successfully resolved - use canonical type
                typedef = Typedef(
                    name=name,
                    underlying_type=canonical_type,
                    location=self._get_location(cursor),
                )
                self.declarations.append(typedef)
                return

        # Standard typedef handling
        standard_underlying_type = self._convert_type(underlying)
        if not standard_underlying_type:
            return

        typedef = Typedef(
            name=name,
            underlying_type=standard_underlying_type,
            location=self._get_location(cursor),
        )
        self.declarations.append(typedef)

    def _process_variable(self, cursor: "clang.cindex.Cursor") -> None:
        """Process a variable declaration."""
        name = cursor.spelling
        if not name:
            return

        # Skip if already processed
        key = f"var:{name}"
        if key in self._seen:
            return
        self._seen[key] = True

        var_type = self._convert_type(cursor.type)
        if not var_type:
            return

        var = Variable(name=name, type=var_type, location=self._get_location(cursor))
        self.declarations.append(var)

    def _convert_field(self, cursor: "clang.cindex.Cursor") -> Field | None:
        """Convert a field cursor to IR Field."""
        name = cursor.spelling
        if not name:
            return None

        field_type = self._convert_type(cursor.type)
        if not field_type:
            return None

        return Field(name=name, type=field_type)

    # pylint: disable=too-many-return-statements
    def _convert_type(self, clang_type: "clang.cindex.Type") -> TypeExpr | None:
        """Convert a libclang Type to our IR type expression."""
        # Get canonical type for consistency
        kind = clang_type.kind

        # Handle pointer types
        if kind == TypeKind.POINTER:
            pointee = clang_type.get_pointee()

            # Check for function pointer
            if pointee.kind == TypeKind.FUNCTIONPROTO:
                func_ptr = self._convert_function_type(pointee)
                if func_ptr:
                    return Pointer(pointee=func_ptr)
                return None

            pointee_type = self._convert_type(pointee)
            if pointee_type:
                return Pointer(pointee=pointee_type)
            return None

        # Handle array types
        if kind in (TypeKind.CONSTANTARRAY, TypeKind.INCOMPLETEARRAY, TypeKind.VARIABLEARRAY):
            element_type = self._convert_type(clang_type.element_type)
            if not element_type:
                return None

            size: int | str | None = None
            if kind == TypeKind.CONSTANTARRAY:
                size = clang_type.element_count
            # INCOMPLETEARRAY has no size (flexible array)
            # VARIABLEARRAY size is runtime-determined

            return Array(element_type=element_type, size=size)

        # Handle dependent-sized arrays (template parameter dependent)
        # These appear in templates like: template<int N> class Foo { T data[N]; };
        # Cython cannot represent these, so we convert to pointers
        if kind == TypeKind.DEPENDENTSIZEDARRAY:
            element_type = self._convert_type(clang_type.element_type)
            if not element_type:
                return None
            # Return as pointer since Cython can't represent dependent array sizes
            return Pointer(pointee=element_type)

        # Handle function types (for function pointer types)
        if kind == TypeKind.FUNCTIONPROTO:
            return self._convert_function_type(clang_type)

        # Handle elaborated types (struct X, enum Y, etc.)
        if kind == TypeKind.ELABORATED:
            # Get the underlying named type
            named_type = clang_type.get_named_type()
            return self._convert_type(named_type)

        # Handle record (struct/union) types
        if kind == TypeKind.RECORD:
            decl = clang_type.get_declaration()
            name = decl.spelling
            if decl.kind == CursorKind.UNION_DECL:
                return CType(name=f"union {name}" if name else "union")
            return CType(name=f"struct {name}" if name else "struct")

        # Handle enum types
        if kind == TypeKind.ENUM:
            decl = clang_type.get_declaration()
            name = decl.spelling
            return CType(name=f"enum {name}" if name else "enum")

        # Handle typedef types
        if kind == TypeKind.TYPEDEF:
            decl = clang_type.get_declaration()
            return CType(name=decl.spelling)

        # Handle nullptr_t type (C++11)
        # std::nullptr_t resolves to TypeKind.NULLPTR
        # Map to void* since Cython doesn't have a nullptr_t type
        if kind == TypeKind.NULLPTR:
            return Pointer(pointee=CType(name="void"))

        # Handle basic types
        spelling = clang_type.spelling

        # Extract qualifiers
        qualifiers: list[str] = []
        if clang_type.is_const_qualified():
            qualifiers.append("const")
        if clang_type.is_volatile_qualified():
            qualifiers.append("volatile")

        # Clean up the spelling to get base type
        base_type = spelling
        for qual in qualifiers:
            base_type = base_type.replace(qual, "").strip()

        return CType(name=base_type, qualifiers=qualifiers)

    def _convert_function_type(self, clang_type: "clang.cindex.Type") -> FunctionPointer | None:
        """Convert a function type to FunctionPointer."""
        result_type = self._convert_type(clang_type.get_result())
        if not result_type:
            return None

        parameters: list[Parameter] = []
        is_variadic = clang_type.is_function_variadic()

        for arg_type in clang_type.argument_types():
            param_type = self._convert_type(arg_type)
            if param_type:
                # Function pointer params don't have names
                parameters.append(Parameter(name=None, type=param_type))

        return FunctionPointer(
            return_type=result_type,
            parameters=parameters,
            is_variadic=is_variadic,
        )

    def _get_location(self, cursor: "clang.cindex.Cursor") -> SourceLocation | None:
        """Get source location from a cursor."""
        loc = cursor.location
        if loc.file:
            return SourceLocation(file=loc.file.name, line=loc.line, column=loc.column)
        return None


class LibclangBackend:
    """Parser backend using libclang.

    Uses LLVM's libclang to parse C and C++ code. This backend supports
    the full C++ language including templates, classes, and namespaces.

    Properties
    ----------
    name : str
        Returns ``"libclang"``.
    supports_macros : bool
        Returns ``False`` - macro extraction is limited in Python bindings.
    supports_cpp : bool
        Returns ``True`` - full C++ support.

    Example
    -------
    ::

        from autopxd.backends.libclang_backend import LibclangBackend

        backend = LibclangBackend()

        # Parse C++ code with specific standard
        header = backend.parse(
            code,
            "myheader.hpp",
            extra_args=["-std=c++17", "-DDEBUG=1"]
        )
    """

    def __init__(self) -> None:
        self._index: clang.cindex.Index | None = None
        # Cache for parsed headers (path -> Header) to avoid re-parsing
        self._parse_cache: dict[str, Header] = {}
        # Visited set to prevent circular includes
        self._visited: set[str] = set()

    @property
    def name(self) -> str:
        return "libclang"

    @property
    def supports_macros(self) -> bool:
        # Supports simple numeric macros (#define NAME 123)
        # Complex macros (expressions, function-like) are not supported
        return True

    @property
    def supports_cpp(self) -> bool:
        return True

    def _get_index(self) -> "clang.cindex.Index":
        """Get or create the clang index."""
        if self._index is None:
            self._index = clang.cindex.Index.create()
        return self._index

    def _resolve_include_path(
        self,
        include_path: str,
        base_dir: str,
        include_dirs: list[str],
    ) -> str | None:
        """Resolve an include path to an absolute path.

        :param include_path: The include path as it appears in the header
        :param base_dir: Directory of the including file
        :param include_dirs: List of include search directories
        :returns: Absolute path to the header file, or None if not found
        """
        # If already absolute, return as-is
        if os.path.isabs(include_path):
            if os.path.exists(include_path):
                return os.path.abspath(include_path)
            return None

        # Try relative to base directory first
        candidate = os.path.join(base_dir, include_path)
        if os.path.exists(candidate):
            return os.path.abspath(candidate)

        # Try each include directory
        for inc_dir in include_dirs:
            candidate = os.path.join(inc_dir, include_path)
            if os.path.exists(candidate):
                return os.path.abspath(candidate)

        return None

    def _parse_header_file(
        self,
        header_path: str,
        include_dirs: list[str],
        extra_args: list[str],
        use_default_includes: bool,
    ) -> Header:
        """Parse a single header file.

        :param header_path: Absolute path to header file
        :param include_dirs: Include directories
        :param extra_args: Extra compiler arguments
        :param use_default_includes: Whether to use system includes
        :returns: Parsed Header IR
        """
        # Check cache
        if header_path in self._parse_cache:
            return self._parse_cache[header_path]

        # Read the file
        with open(header_path, encoding="utf-8", errors="replace") as f:
            code = f.read()

        # Parse using the main parse method
        # Use the basename for the filename to match expected behavior
        filename = os.path.basename(header_path)
        header = self.parse(
            code,
            filename,
            include_dirs=include_dirs,
            extra_args=extra_args,
            use_default_includes=use_default_includes,
            recursive_includes=False,  # Prevent infinite recursion
        )

        # Cache the result
        self._parse_cache[header_path] = header
        return header

    def _parse_recursively(
        self,
        main_header: Header,
        main_path: str,
        include_dirs: list[str],
        extra_args: list[str],
        use_default_includes: bool,
        max_depth: int,
        current_depth: int = 0,
        project_prefixes: tuple[str, ...] | None = None,
    ) -> Header:
        """Recursively parse included headers and combine declarations.

        :param main_header: The main header that was parsed
        :param main_path: Path to the main header file
        :param include_dirs: Include directories
        :param extra_args: Extra compiler arguments
        :param use_default_includes: Whether to use system includes
        :param max_depth: Maximum recursion depth
        :param current_depth: Current recursion depth
        :param project_prefixes: Optional tuple of path prefixes to treat as project (not system)
        :returns: Combined Header with declarations from all includes
        """
        if current_depth >= max_depth:
            return main_header

        all_declarations: list[Declaration] = list(main_header.declarations)
        main_dir = os.path.dirname(os.path.abspath(main_path))

        # Process each included header
        for include_path in main_header.included_headers:
            # Skip system headers (unless whitelisted via project_prefixes)
            if _is_system_header(include_path, project_prefixes):
                continue

            # Get absolute path
            abs_path = self._resolve_include_path(
                include_path,
                main_dir,
                include_dirs,
            )

            if abs_path is None:
                # Could not resolve - skip
                continue

            # Check if already visited (circular include)
            if abs_path in self._visited:
                continue

            self._visited.add(abs_path)

            try:
                # Parse the included header
                sub_header = self._parse_header_file(
                    abs_path,
                    include_dirs,
                    extra_args,
                    use_default_includes,
                )

                # Recursively process its includes
                sub_header = self._parse_recursively(
                    sub_header,
                    abs_path,
                    include_dirs,
                    extra_args,
                    use_default_includes,
                    max_depth,
                    current_depth + 1,
                    project_prefixes,
                )

                # Add declarations from sub-header
                all_declarations.extend(sub_header.declarations)

            except Exception:
                # Skip headers that fail to parse
                # This is common with complex system headers
                continue

        # Deduplicate declarations
        unique_declarations = _deduplicate_declarations(all_declarations)

        # Return combined header
        return Header(
            path=main_header.path,
            declarations=unique_declarations,
            included_headers=main_header.included_headers,
        )

    def parse(
        self,
        code: str,
        filename: str,
        include_dirs: list[str] | None = None,
        extra_args: list[str] | None = None,
        use_default_includes: bool = True,
        recursive_includes: bool = True,
        max_depth: int = 10,
        project_prefixes: tuple[str, ...] | None = None,
    ) -> Header:
        """Parse C/C++ code using libclang.

        Unlike the pycparser backend, this method handles raw (unpreprocessed)
        code and performs preprocessing internally.

        Umbrella header support: If the header has few/no declarations but many
        includes (umbrella header pattern), this method can recursively parse the
        included headers and combine their declarations.

        :param code: C/C++ source code to parse (raw, not preprocessed).
        :param filename: Source filename for error messages and location tracking.
        :param include_dirs: Additional include directories (converted to ``-I`` flags).
        :param extra_args: Additional compiler arguments (e.g., ``["-std=c++17"]``).
        :param use_default_includes: If True (default), automatically detect and add
            system include directories by querying the system clang compiler.
            Set to False to disable this behavior.
        :param recursive_includes: If True (default), detect umbrella headers and
            recursively parse included project headers. System headers are always
            skipped. Set to False to only parse the main file.
        :param max_depth: Maximum recursion depth for include processing (default 10).
            Prevents infinite recursion from circular includes.
        :param project_prefixes: Optional tuple of path prefixes to treat as project
            headers (not system). Use this for umbrella headers of libraries installed
            in system locations (e.g., ``("/opt/homebrew/include/sodium",)``).
        :returns: :class:`~autopxd.ir.Header` containing parsed declarations.
        :raises RuntimeError: If parsing fails with errors.

        Example
        -------
        ::

            # Basic usage
            header = backend.parse(
                code,
                "myheader.hpp",
                include_dirs=["/usr/local/include"],
                extra_args=["-std=c++17", "-DNDEBUG"]
            )

            # Umbrella header (all-includes) pattern
            header = backend.parse(
                code,
                "LibraryAll.h",
                include_dirs=["./include"],
                recursive_includes=True  # Auto-detect and expand includes
            )

            # Umbrella header in system location
            header = backend.parse(
                code,
                "sodium.h",
                include_dirs=["/opt/homebrew/include"],
                project_prefixes=("/opt/homebrew/include/sodium",)  # Whitelist sodium/*
            )
        """
        args: list[str] = []

        # Detect C++ mode from extra_args
        is_cplus = bool(extra_args and any(arg in ("-x", "c++") or arg.startswith("-std=c++") for arg in extra_args))

        # Add user-specified include directories FIRST
        # This is important for C++ where user headers may need to come before system libc++
        if include_dirs:
            for inc_dir in include_dirs:
                args.append(f"-I{inc_dir}")

        # Add system include directories if enabled
        # Always add them when use_default_includes=True, regardless of other -I flags
        if use_default_includes:
            args.extend(get_system_include_dirs(cplus=is_cplus))

        # Add extra arguments
        if extra_args:
            args.extend(extra_args)

        # Parse the code with detailed preprocessing record for macro extraction
        index = self._get_index()
        tu = index.parse(
            filename,
            args=args,
            unsaved_files=[(filename, code)],
            options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
        )

        # Check for fatal errors
        for diag in tu.diagnostics:
            if diag.severity >= clang.cindex.Diagnostic.Error:
                raise RuntimeError(f"Parse error: {diag.spelling}")

        # Collect included headers
        included_headers: set[str] = set()
        for inclusion in tu.get_includes():
            # inclusion.include is a File with name attribute
            header_path = str(inclusion.include.name)
            # Store full path - caller can extract basename if needed
            included_headers.add(header_path)

        # Convert to IR
        converter = ClangASTConverter(filename, project_prefixes=project_prefixes)
        header = converter.convert(tu)

        # Attach included headers to the IR
        header.included_headers = included_headers

        # Check if we should do recursive include processing
        if recursive_includes and _is_umbrella_header(header, project_prefixes=project_prefixes):
            # Reset visited set for each top-level parse
            self._visited = set()
            # Add current file to visited
            if os.path.exists(filename):
                abs_filename = os.path.abspath(filename)
            else:
                # For in-memory code, use filename as-is
                abs_filename = filename
            self._visited.add(abs_filename)

            # Recursively parse included headers
            header = self._parse_recursively(
                header,
                abs_filename,
                include_dirs or [],
                extra_args or [],
                use_default_includes,
                max_depth,
                project_prefixes=project_prefixes,
            )

        return header


# Only register this backend if system libclang is available
# If not available, autopxd2 falls back to pycparser automatically
if is_system_libclang_available():
    register_backend("libclang", LibclangBackend)
