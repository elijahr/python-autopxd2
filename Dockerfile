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

# Install system dependencies including clang and libclang
RUN apt-get update && apt-get install -y --no-install-recommends \
    clang \
    libclang-dev \
    llvm-dev \
    && rm -rf /var/lib/apt/lists/*

# Set LIBCLANG_PATH for the Python clang2 bindings
ENV LIBCLANG_PATH=/usr/lib/llvm-16/lib

# Install autopxd2 with libclang support
COPY . /app
WORKDIR /app

RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir clang2==16.*

# Set working directory for volume mounts
WORKDIR /work

# Default command shows help
CMD ["autopxd", "--help"]
