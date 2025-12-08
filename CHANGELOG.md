# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **BREAKING**: Rewrote `translate()` function to use new IR-based backend system
- **BREAKING**: Removed `--regex` CLI option (was broken/unused)
- **BREAKING**: Removed legacy `parse()` and `preprocess()` functions from public API
- `translate()` now accepts `backend` parameter to select pycparser or libclang
- Renamed `extra_cpp_args` parameter to `extra_args` in `translate()`

### Added
- Full CLI integration with backend system (`--backend` option now works)
- Whitelist filtering for declarations by source file
- Support for anonymous enums in struct fields
- Support for anonymous struct/union variables
- Recursive function pointer parameter extraction
- Source location tracking for all declaration types

### Removed
- `autopxd/writer.py` - Legacy pycparser AST visitor (replaced by IR system)
- `autopxd/nodes.py` - Legacy node types (replaced by IR types)
- `parse()` function from public API
- `preprocess()` function from public API

### Fixed
- CLI `--backend` option now correctly routes to selected backend
- Anonymous nested struct/union extraction with proper synthetic names
- Function pointer typedef syntax in Cython output
- Keyword escaping with C name aliases for all declaration types
- `ctypedef` vs `cdef`/`cpdef` handling for typedef'd types
- Self-typedef patterns (`typedef struct X X;`) no longer produce duplicates
- Struct/union/enum prefix stripping for known types
- Const qualifier deduplication

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

[Unreleased]: https://github.com/elijahr/python-autopxd2/compare/v2.5.0...HEAD
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
