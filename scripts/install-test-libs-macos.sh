#!/bin/bash
# Install test libraries for autopxd2 on macOS
#
# This script installs all libraries used by test_real_headers.py using Homebrew.
# Requires Homebrew to be installed.
#
# Usage:
#   ./scripts/install-test-libs-macos.sh

set -e

echo "Installing test libraries for autopxd2..."

# Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo "Error: Homebrew is required. Install from https://brew.sh"
    exit 1
fi

# Core C libraries
brew install \
    zlib \
    jansson \
    sqlite \
    curl \
    libuv \
    cjson \
    libsodium \
    utf8proc

# C++ libraries
brew install \
    boost \
    fmt \
    spdlog \
    nlohmann-json \
    catch2 \
    doctest \
    nng

# Python development headers are included with Python installation
# numpy should be installed via pip in the project venv

echo "Done installing test libraries."
echo ""
echo "Note: Make sure numpy is installed in your Python environment:"
echo "  pip install numpy"
