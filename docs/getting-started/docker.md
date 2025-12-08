# Docker Usage

autopxd2 provides a Docker image with libclang pre-installed, allowing you to generate high-quality `.pxd` files without installing clang on your system.

!!! tip "Recommended for C++ headers"
    The Docker image is the easiest way to use the libclang backend, which provides better C++ support and handles complex headers that pycparser cannot parse.

## Quick Start

```bash
# Build the Docker image
docker build -t autopxd2 https://github.com/elijahr/python-autopxd2.git

# Or build from local checkout
git clone https://github.com/elijahr/python-autopxd2.git
cd python-autopxd2
docker build -t autopxd2 .
```

## Usage Examples

### Generate pxd from a header file

```bash
# Mount your project directory and generate pxd
docker run --rm -v $(pwd):/work autopxd2 autopxd /work/myheader.h

# Save output to a file
docker run --rm -v $(pwd):/work autopxd2 autopxd /work/myheader.h > myheader.pxd
```

### Use libclang backend

```bash
# Explicitly use libclang for better C++ support
docker run --rm -v $(pwd):/work autopxd2 autopxd --backend libclang /work/myheader.hpp
```

### Include directories

```bash
# Add include paths for dependent headers
docker run --rm -v $(pwd):/work autopxd2 autopxd \
    -I /work/include \
    -I /work/third_party \
    /work/src/myheader.h
```

### Interactive shell

```bash
# Get an interactive shell in the container
docker run --rm -it -v $(pwd):/work autopxd2 bash

# Then run autopxd commands interactively
autopxd /work/myheader.h
```

## Docker Compose

For projects that frequently use autopxd2, add it to your `docker-compose.yml`:

```yaml
services:
  autopxd:
    build: https://github.com/elijahr/python-autopxd2.git
    volumes:
      - .:/work
    working_dir: /work
```

Then run:

```bash
docker compose run --rm autopxd autopxd myheader.h
```

## What's Included

The Docker image includes:

- Python 3.12
- clang and libclang development libraries
- autopxd2 with all dependencies
- The `clang` Python package for libclang bindings

## Building for Different Architectures

The Dockerfile supports both AMD64 and ARM64 architectures:

```bash
# Build for current architecture
docker build -t autopxd2 .

# Build for specific architecture
docker build --platform linux/amd64 -t autopxd2:amd64 .
docker build --platform linux/arm64 -t autopxd2:arm64 .
```
