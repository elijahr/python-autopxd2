# autopxd2 Docker image with libclang support
#
# This image provides a complete environment for generating Cython .pxd files
# from C/C++ headers, including libclang for better header parsing.
#
# Usage:
#   # Build the image
#   docker build -t autopxd2 .
#
#   # Generate .pxd from a header file
#   docker run --rm -v $(pwd):/work autopxd2 autopxd /work/myheader.h
#
#   # Use libclang backend (better C++ support)
#   docker run --rm -v $(pwd):/work autopxd2 autopxd --backend libclang /work/myheader.h
#
#   # Interactive shell
#   docker run --rm -it -v $(pwd):/work autopxd2 bash

FROM python:3.12-slim

# Install system dependencies including clang, libclang, and cpp (C preprocessor)
RUN apt-get update && apt-get install -y --no-install-recommends \
    clang \
    libclang-dev \
    llvm-dev \
    cpp \
    && rm -rf /var/lib/apt/lists/*

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
