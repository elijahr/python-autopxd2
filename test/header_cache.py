"""Download and cache library headers for testing.

This module downloads real library headers from their official sources
and caches them locally. Headers are stored in a cache directory that
is excluded from source control.

The cache is re-entrant - multiple test runs can share the same cache,
and downloads only happen if the file doesn't already exist.
"""

import hashlib
import urllib.request
from pathlib import Path

# Cache directory - outside of test/real_headers/ to keep fixtures separate
CACHE_DIR = Path(__file__).parent / ".header_cache"

# Header sources with URLs and expected checksums (SHA256)
# Using raw GitHub URLs from official repositories
HEADER_SOURCES = {
    "zlib": {
        "version": "1.3.1",
        "files": {
            "zlib.h": {
                "url": "https://raw.githubusercontent.com/madler/zlib/v1.3.1/zlib.h",
                "sha256": "8a5579af72ea4f427ff00a4150f0ccb3fc5c1e4379f726e101133b1ab9fc600c",
            },
            "zconf.h": {
                "url": "https://raw.githubusercontent.com/madler/zlib/v1.3.1/zconf.h",
                "sha256": "f5134250a67d57459234b63858f0d9d3ef8dcc48e9e1028d3f4fdcf6eae677ae",
            },
        },
    },
    "jansson": {
        "version": "2.14",
        "files": {
            "jansson.h": {
                "url": "https://raw.githubusercontent.com/akheron/jansson/v2.14/src/jansson.h",
                "sha256": "8945f933b82707edea06a9e006bd7b65b160a6301f7bf90da569e263deed11f2",
            },
            "jansson_config.h": {
                # This is a generated file, we provide a compatible version
                "url": None,  # Generated locally
                "content": """\
/* jansson_config.h - Configuration for jansson tests */
#ifndef JANSSON_CONFIG_H
#define JANSSON_CONFIG_H

/* Inline keyword support */
#ifdef __cplusplus
#define JSON_INLINE inline
#else
#define JSON_INLINE inline
#endif

#define JSON_INTEGER_IS_LONG_LONG 1
#define JSON_HAVE_LOCALECONV 1
#define JSON_HAVE_ATOMIC_BUILTINS 1
#define JSON_HAVE_SYNC_BUILTINS 1

typedef long long json_int_t;
#define JSON_INTEGER_FORMAT "lld"

#endif
""",
            },
        },
    },
}


def _compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _download_file(url: str, dest: Path) -> None:
    """Download a file from URL to destination."""
    print(f"Downloading {url} -> {dest}")
    with urllib.request.urlopen(url, timeout=30) as response:
        content = response.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)


def _ensure_header(library: str, filename: str, config: dict) -> Path:
    """Ensure a header file exists in cache, downloading if needed.

    Returns the path to the cached header file.
    """
    cache_path = CACHE_DIR / library / filename

    # If file exists and has correct hash (if specified), use it
    if cache_path.exists():
        if "sha256" in config and config["sha256"]:
            actual_hash = _compute_sha256(cache_path)
            if actual_hash == config["sha256"]:
                return cache_path
            print(f"Hash mismatch for {cache_path}, re-downloading")
        else:
            return cache_path

    # Create from content or download
    if config.get("content"):
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(config["content"])
    elif config.get("url"):
        _download_file(config["url"], cache_path)

        # Verify hash if specified
        if "sha256" in config and config["sha256"]:
            actual_hash = _compute_sha256(cache_path)
            if actual_hash != config["sha256"]:
                raise ValueError(f"Hash mismatch for {filename}: " f"expected {config['sha256']}, got {actual_hash}")
    else:
        raise ValueError(f"No URL or content for {library}/{filename}")

    return cache_path


def get_library_headers(library: str) -> Path:
    """Get the cache directory containing headers for a library.

    Downloads headers if not already cached.

    Args:
        library: Library name (e.g., "zlib", "jansson")

    Returns:
        Path to the directory containing the library's header files.

    Raises:
        ValueError: If the library is not known.
    """
    if library not in HEADER_SOURCES:
        raise ValueError(f"Unknown library: {library}. Known: {list(HEADER_SOURCES.keys())}")

    config = HEADER_SOURCES[library]
    library_dir = CACHE_DIR / library

    for filename, file_config in config["files"].items():
        _ensure_header(library, filename, file_config)

    return library_dir


def get_header_path(library: str, filename: str) -> Path:
    """Get the path to a specific header file.

    Downloads the header if not already cached.

    Args:
        library: Library name (e.g., "zlib")
        filename: Header filename (e.g., "zlib.h")

    Returns:
        Path to the header file.
    """
    get_library_headers(library)  # Ensure all headers are downloaded
    return CACHE_DIR / library / filename


def clear_cache() -> None:
    """Clear the header cache directory."""
    import shutil

    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)


if __name__ == "__main__":
    # CLI for manual cache management
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        clear_cache()
        print(f"Cleared cache: {CACHE_DIR}")
    elif len(sys.argv) > 1 and sys.argv[1] == "download":
        for lib in HEADER_SOURCES:
            path = get_library_headers(lib)
            print(f"Downloaded {lib} headers to {path}")
    else:
        print(f"Usage: {sys.argv[0]} [clear|download]")
        print(f"Cache directory: {CACHE_DIR}")
