# Docker Usage

autopxd2 provides a Docker image with libclang pre-installed, allowing you to generate high-quality `.pxd` files without installing clang on your system.

!!! tip "Recommended for C++ headers"
    The Docker image is the easiest way to use the libclang backend, which provides better C++ support and handles complex headers that pycparser cannot parse.

## Quick Start

Use the pre-built image from GitHub Container Registry:

```bash
docker pull ghcr.io/elijahr/python-autopxd2
```

Or build locally:

```bash
git clone https://github.com/elijahr/python-autopxd2.git
cd python-autopxd2
docker build -t ghcr.io/elijahr/python-autopxd2 .
```

## Usage Examples

### Generate pxd from a header file

The container runs in `/work` by default, so mount your project there:

```bash
# Mount current directory to /work and generate pxd
docker run --rm -v $(pwd):/work -w /work ghcr.io/elijahr/python-autopxd2 \
    autopxd myheader.h

# Save output to a file
docker run --rm -v $(pwd):/work -w /work ghcr.io/elijahr/python-autopxd2 \
    autopxd myheader.h > myheader.pxd
```

### C++ headers

```bash
# libclang is used by default in the container
docker run --rm -v $(pwd):/work -w /work ghcr.io/elijahr/python-autopxd2 \
    autopxd myheader.hpp
```

### Include directories

System include paths are automatically detected inside the container. For project-specific headers, mount the directories and use `-I`:

```bash
# Project includes (already under /work)
docker run --rm -v $(pwd):/work -w /work ghcr.io/elijahr/python-autopxd2 \
    autopxd -I include -I src myheader.h
```

For external dependencies outside your project, mount them separately:

```bash
# Mount external library to /third_party
docker run --rm \
    -v $(pwd):/work \
    -v ~/libs/somelib:/third_party \
    -w /work \
    ghcr.io/elijahr/python-autopxd2 \
    autopxd -I include -I /third_party/include myheader.h
```

**Important:** Any directory referenced with `-I` must be accessible inside the container. Use relative paths for directories under `/work`, or mount external directories and use absolute paths.

### Interactive shell

```bash
# Get an interactive shell in the container
docker run --rm -it -v $(pwd):/work -w /work ghcr.io/elijahr/python-autopxd2 bash

# Then run autopxd commands interactively (paths are relative to /work)
autopxd -I include myheader.h
```

## Docker Compose

For projects that frequently use autopxd2, add it to your `docker-compose.yml`:

```yaml
services:
  autopxd:
    image: ghcr.io/elijahr/python-autopxd2
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
