# autopxd2 Docker image with libclang support
#
# This image provides a complete environment for generating Cython .pxd files
# from C/C++ headers, including libclang for better header parsing.
#
# Pre-built image available at: ghcr.io/elijahr/python-autopxd2
#
# Usage:
#   # Generate .pxd from a header file
#   docker run --rm -v $(pwd):/work -w /work ghcr.io/elijahr/python-autopxd2 autopxd myheader.h
#
#   # With include directories
#   docker run --rm -v $(pwd):/work -w /work ghcr.io/elijahr/python-autopxd2 autopxd -I include myheader.h
#
#   # External includes (mount separately)
#   docker run --rm -v $(pwd):/work -v ~/libs/foo:/foo -w /work ghcr.io/elijahr/python-autopxd2 autopxd -I /foo/include myheader.h
#
#   # Interactive shell
#   docker run --rm -it -v $(pwd):/work -w /work ghcr.io/elijahr/python-autopxd2 bash
#
# Build args:
#   TEST_MODE=1  Include test libraries for running real header tests

FROM python:3.12-slim

# Install system dependencies including clang, libclang, and cpp (C preprocessor)
RUN apt-get update && apt-get install -y --no-install-recommends \
    clang \
    libclang-dev \
    llvm-dev \
    cpp \
    && rm -rf /var/lib/apt/lists/*

# Optional: Install test libraries (only when building with --build-arg TEST_MODE=1)
ARG TEST_MODE=0
COPY scripts/install-test-libs-linux.sh /tmp/install-test-libs.sh
RUN if [ "$TEST_MODE" = "1" ]; then \
        chmod +x /tmp/install-test-libs.sh && /tmp/install-test-libs.sh; \
    fi && rm -f /tmp/install-test-libs.sh && rm -rf /var/lib/apt/lists/*

# Find LLVM version and configure library path
RUN LLVM_VERSION=$(ls /usr/lib/ | grep -oP 'llvm-\K\d+' | head -1) \
    && echo "Found LLVM version: $LLVM_VERSION" \
    && ln -s /usr/lib/llvm-${LLVM_VERSION}/lib/libclang.so /usr/lib/libclang.so \
    && echo "/usr/lib/llvm-${LLVM_VERSION}/lib" > /etc/ld.so.conf.d/llvm.conf \
    && ldconfig

# Install autopxd2 with libclang support
COPY . /app
WORKDIR /app

# Detect LLVM version and install matching clang2 package
# Install with test dependencies for in-container testing
RUN LLVM_VERSION=$(ls /usr/lib/ | grep -oP 'llvm-\K\d+' | head -1) \
    && pip install --no-cache-dir -e ".[test]" \
    && pip install --no-cache-dir "clang2==${LLVM_VERSION}.*"

# Set working directory for volume mounts
WORKDIR /work

# Default command shows help
CMD ["autopxd", "--help"]
