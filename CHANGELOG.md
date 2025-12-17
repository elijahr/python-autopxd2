# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.2.0] - 2025-12-17

### Added
- **Umbrella header support** - New CLI options for parsing library-wide "umbrella" headers that aggregate sub-headers:
  - `--project-prefix` / `-p` - Whitelist paths containing this prefix for recursive parsing
  - `--no-recursive` - Disable recursive include parsing
  - `--max-depth` - Limit recursion depth for included headers
- **C++ template support** - libclang backend now handles C++ templates:
  - Template class declarations with type parameters (`template<typename T>`)
  - Template specialization detection with explanatory comments
  - Non-type template parameters detected with notes (Cython limitation)
- **Operator aliasing** - C++ operators are renamed to Cython-compatible names (e.g., `operator[]` → `__getitem__`, `operator==` → `__eq__`)
- **Circular dependency resolution** - Multi-phase output generation that correctly handles circular type dependencies. Libraries like libuv and sqlite3 that have function pointer typedefs referencing structs now generate valid Cython.
- **New POSIX stubs** - `sys_un.pxd` (Unix domain sockets), `semaphore.pxd` (POSIX semaphores), `regex.pxd` (POSIX regex), `sys_statvfs.pxd` (filesystem stats).
- **C11 stdatomic stub** - `stdatomic.pxd` provides atomic types and memory ordering for C11 code.
- **C++ stubs** - `cppthread.pxd` (std::thread), `cppchrono.pxd` (std::chrono), `cppfilesystem.pxd` (std::filesystem).
- **Full compilation test suite** - Tests now compile generated pxd files against real libraries (zlib, jansson, curl, sqlite3, libuv, libsodium, etc.) to verify correctness.

### Changed
- **clang2 is now optional** - The `clang2` package is no longer a hard dependency. When the libclang backend is requested but clang2 is not installed, autopxd2 detects your system's LLVM version and provides the exact install command (e.g., `pip install 'clang2==18.*'`).
- **libclang is now the recommended backend** - Documentation updated to recommend libclang for all use cases. pycparser is now marked as legacy (C99 only, no macros, no circular dependency handling).
- **Test headers downloaded dynamically** - Library headers (zlib.h, jansson.h) are now downloaded from official GitHub repositories and cached locally, reducing repository size.

### Fixed
- **`__builtin_va_list` filtering** - GCC/Clang internal types starting with `__builtin_` are now filtered from generated pxd output, fixing Cython compilation errors when parsing system headers.
- **Windows path handling** - Fixed backslash stripping in compilation paths that caused test failures on Windows.
- **Template specialization LLVM compatibility** - Added fallback detection for template specializations that works across LLVM versions 16-21.

## [3.1.1] - 2025-12-11

### Added
- **Automatic system include detection** - The libclang backend now automatically detects system include directories by querying the system clang compiler. Headers like `<stddef.h>` and `<stdint.h>` now work without requiring manual `-I` flags.
- **`--no-default-includes` CLI option** - Disable automatic system include detection when needed.

### Changed
- **Renamed `--compiler-directive` to `--define`** - The `-D` flag now uses `--define` as its long form. `--compiler-directive` remains as a deprecated hidden alias.
- **Reorganized CLI help** - Options are now grouped logically, with `[libclang]` markers clearly indicating backend-specific options.
- **Improved documentation** - Docker examples now show proper volume mounting for include directories with `-w /work` for cleaner relative paths.

## [3.1.0] - 2025-12-11

### Added
- **Auto-import Cython standard library types** - Types from `libc` (stdio, stdint, stdlib, string, time, math, etc.), `posix` (unistd, stat, types), and `cpython` modules are now automatically imported when detected in headers.
- **Auto-import C++ STL types** - C++ standard library types (`std::vector`, `std::string`, `std::map`, `std::shared_ptr`, etc.) are automatically imported from Cython's `libcpp` modules.
- **Bundled stub declarations** - Types not included in Cython's standard library (`va_list`, socket types like `sockaddr`, `socklen_t`, `sockaddr_in`) are now provided via bundled stub files.
- **C++ namespace support** - libclang backend now properly handles C++ namespaces, including nested namespaces. Declarations are grouped by namespace in the output.
- **Macro extraction** - The libclang backend now extracts `#define` macros with automatic type detection:
  - Integer macros (decimal, hex, octal, binary) with optional suffixes (ULL, L, etc.) → `int`
  - Floating-point macros (including scientific notation) → `double`
  - String literal macros → `const char*`
  - Expression macros (arithmetic, bitwise, macro references) → `int` or `double`

### Fixed
- **Forward declarations now emitted** - Struct, union, and class forward declarations (e.g., `struct internal_state;`) are now properly emitted in the generated pxd, fixing Cython compilation errors when opaque pointers reference forward-declared types.
- **`_Atomic` type qualifier handling** - The C11 `_Atomic` type qualifier is now properly stripped from generated pxd output. Both `_Atomic type` and `_Atomic(type)` syntaxes are handled, fixing Cython compilation errors for headers using C11 atomics.

## [3.0.0] - 2025-12-10

### Added
- **libclang backend** - New parser backend with full C++ support including classes, methods, templates, and namespaces. Auto-selected when libclang is available, with fallback to pycparser for systems without it.
- **C++ support** - Parse C++ headers with `--cpp` flag or `.hpp`/`.cpp` extensions. Generates proper `cdef cppclass` declarations with methods.
- **New CLI options**:
  - `--backend` / `-b` - Select parser backend (`auto`, `libclang`, `pycparser`)
  - `--cpp` / `-x` - Parse as C++ (requires libclang)
  - `--std` - Language standard (e.g., `c11`, `c++17`)
  - `--clang-arg` - Pass additional arguments to libclang
  - `--whitelist` / `-w` - Only generate declarations from specified files
  - `--quiet` / `-q` - Suppress warnings
  - `--list-backends` - Show available backends
  - `--json` - JSON output for `--list-backends`
- **Docker image** - Official multi-platform image (amd64/arm64) with libclang pre-installed at `ghcr.io/elijahr/python-autopxd2`
- **Documentation** - New documentation site with user guide, API reference, and contributing guide

### Changed
- **Complete rewrite** of the parsing and code generation system using an intermediate representation (IR)
- `translate()` function signature: `extra_cpp_args` renamed to `extra_args`, new `backend` parameter added

### Removed
- **`--regex` / `-R` option** - Removed from CLI
- **stdin input** - File path argument is now required
- `parse()` and `preprocess()` functions from public API
- Legacy `autopxd/writer.py` and `autopxd/nodes.py` modules

## [2.5.0] - 2024-12-01

### Changed
- Greatly improved time taken by `vswhere.exe` to find `cl.exe` on Windows ([#55](https://github.com/elijahr/python-autopxd2/pull/55))
- Refactored installation to use only pyproject.toml ([#53](https://github.com/elijahr/python-autopxd2/pull/53))
- Updated linting to use pre-commit ([#53](https://github.com/elijahr/python-autopxd2/pull/53))

### Added
- Contribution guidelines ([#53](https://github.com/elijahr/python-autopxd2/pull/53))

### Fixed
- Improved handling of non-literal-as-value in enum parsing ([#52](https://github.com/elijahr/python-autopxd2/pull/52))
- Fixed parsing crash when using binary operation in enum ([#51](https://github.com/elijahr/python-autopxd2/pull/51))
- Fixed configuration of `vswhere.exe` to find `cl.exe` on Windows ([#49](https://github.com/elijahr/python-autopxd2/pull/49))

## [2.4.0] - 2024-09-10

### Added
- Support for Python 3.12 ([#45](https://github.com/elijahr/python-autopxd2/pull/45))
- Support for char and binary expression in enum ([#47](https://github.com/elijahr/python-autopxd2/pull/47))
- Wheel distribution on PyPI ([#46](https://github.com/elijahr/python-autopxd2/pull/46))

## [2.3.0] - 2023-01-08

### Added
- Support for const and volatile qualifiers ([#42](https://github.com/elijahr/python-autopxd2/pull/42))

## [2.2.3] - 2022-10-04

### Changed
- Repository moved to https://github.com/elijahr/python-autopxd2

## [2.2.0] - 2022-08-03

### Added
- Microsoft Visual C++ support ([#40](https://github.com/elijahr/python-autopxd2/pull/40))

## [2.1.1] - 2022-05-24

### Added
- `--regex` option for arbitrary conversions ([#38](https://github.com/elijahr/python-autopxd2/pull/38))

### Fixed
- Various fixes and improvements ([#38](https://github.com/elijahr/python-autopxd2/pull/38))

## [2.0.4] - 2021-11-23

### Fixed
- Windows CRLF issue ([#24](https://github.com/elijahr/python-autopxd2/pull/24))

## [2.0.3] - 2021-10-08

### Fixed
- Removed unnecessary `importlib_resources` from install_requires

## [2.0.2] - 2021-10-07

### Changed
- Migrated to setup.cfg configuration

## [2.0.1] - 2021-10-06

### Added
- `--compiler-directive` option
- Type annotations for nodes.py
- Linting and formatting with black
- GitHub Actions CI (migrated from Travis CI)

### Removed
- Python 2 support

## [1.1.0] - 2020-01-03

### Added
- macOS support

[Unreleased]: https://github.com/elijahr/python-autopxd2/compare/v3.2.0...HEAD
[3.2.0]: https://github.com/elijahr/python-autopxd2/compare/v3.1.1...v3.2.0
[3.1.1]: https://github.com/elijahr/python-autopxd2/compare/v3.1.0...v3.1.1
[3.1.0]: https://github.com/elijahr/python-autopxd2/compare/v3.0.0...v3.1.0
[3.0.0]: https://github.com/elijahr/python-autopxd2/compare/v2.5.0...v3.0.0
[2.5.0]: https://github.com/elijahr/python-autopxd2/compare/v2.4.0...v2.5.0
[2.4.0]: https://github.com/elijahr/python-autopxd2/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/elijahr/python-autopxd2/compare/v2.2.3...v2.3.0
[2.2.3]: https://github.com/elijahr/python-autopxd2/compare/v2.2.0...v2.2.3
[2.2.0]: https://github.com/elijahr/python-autopxd2/compare/v2.1.1...v2.2.0
[2.1.1]: https://github.com/elijahr/python-autopxd2/compare/v2.0.4...v2.1.1
[2.0.4]: https://github.com/elijahr/python-autopxd2/compare/v2.0.3...v2.0.4
[2.0.3]: https://github.com/elijahr/python-autopxd2/compare/v2.0.2...v2.0.3
[2.0.2]: https://github.com/elijahr/python-autopxd2/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/elijahr/python-autopxd2/compare/v1.1.0...v2.0.1
[1.1.0]: https://github.com/elijahr/python-autopxd2/releases/tag/v1.1.0
