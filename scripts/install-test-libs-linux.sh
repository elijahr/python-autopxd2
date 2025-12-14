#!/bin/bash
# Install test libraries for autopxd2 on Linux (Debian/Ubuntu)
#
# This script installs all libraries used by test_real_headers.py.
# Run as root or with sudo.
#
# Usage:
#   sudo ./scripts/install-test-libs-linux.sh

set -e

echo "Installing test libraries for autopxd2..."

# Core C libraries (available in standard repos)
apt-get update
apt-get install -y --no-install-recommends \
    libz-dev \
    libjansson-dev \
    libsqlite3-dev \
    libcurl4-openssl-dev \
    libuv1-dev \
    libcjson-dev \
    libsodium-dev \
    libutf8proc-dev

# C++ libraries
apt-get install -y --no-install-recommends \
    libboost-dev \
    libfmt-dev \
    libspdlog-dev \
    nlohmann-json3-dev \
    catch2 \
    doctest-dev

# nng may not be available in older Ubuntu versions
# Try to install if available, skip otherwise
if apt-cache show libnng-dev > /dev/null 2>&1; then
    apt-get install -y --no-install-recommends libnng-dev
else
    echo "Note: libnng-dev not available in apt, skipping (test will be skipped)"
fi

# Python development headers (for Python.h tests)
apt-get install -y --no-install-recommends \
    python3-dev \
    python3-numpy

echo "Done installing test libraries."
