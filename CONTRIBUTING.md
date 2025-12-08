# Contributing to python-autopxd2

Contributions are welcome! This document covers development setup, code quality standards, and the release process.

## Development Setup

We recommend using [uv](https://github.com/astral-sh/uv) for fast dependency management.

1. Clone the repository:

   ```shell
   git clone https://github.com/elijahr/python-autopxd2.git
   cd python-autopxd2
   ```

2. Create a virtual environment and install dependencies:

   ```shell
   # Using uv (recommended)
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e '.[test,lint,docs]'

   # Or using pip
   python -m venv .venv
   source .venv/bin/activate
   pip install -e '.[test,lint,docs]'
   ```

3. Install pre-commit hooks:

   ```shell
   pre-commit install
   ```

## Code Quality

We use pre-commit with [ruff](https://github.com/astral-sh/ruff) for linting and formatting. The following checks run automatically on commit:

- **ruff** - Linting (replaces flake8, pylint, isort, etc.)
- **ruff-format** - Code formatting (replaces black)

To run all checks manually:

```shell
pre-commit run --all-files
```

Or run ruff directly:

```shell
ruff check autopxd       # Lint
ruff check --fix autopxd # Lint and auto-fix
ruff format autopxd      # Format
```

## Type Checking

We use mypy with strict mode:

```shell
mypy autopxd/ --strict
```

## Running Tests

```shell
pytest
```

Or with verbose output:

```shell
pytest -v
```

## Building Documentation

```shell
# Serve docs locally with live reload
uv run mkdocs serve

# Or without uv
mkdocs serve

# Build static site
mkdocs build
```

## Submitting Changes

1. Create a branch for your changes
2. Ensure all tests pass and pre-commit checks are clean
3. Submit a pull request with a clear description of the changes

## Regenerating Stub Headers

The stub headers in `autopxd/stubs/` prevent generating Cython code for system headers. To regenerate them (rarely needed):

```shell
python regenerate_stubs.py
```

This downloads libc stub headers and generates macOS stubs if on macOS.

---

# Maintainer Guide

This section is for project maintainers who can publish releases.

## Release Process

### 1. Prepare the Release

1. Update version in `pyproject.toml`:

   ```toml
   version = "X.Y.Z"
   ```

2. Update `CHANGELOG.md` with the release notes

3. Commit and push to master:

   ```shell
   git add pyproject.toml CHANGELOG.md
   git commit -m "Bump to vX.Y.Z"
   git push origin master
   ```

### 2. Create a GitHub Release

1. Go to [Releases](https://github.com/elijahr/python-autopxd2/releases)
2. Click **Draft a new release**
3. Create a new tag: `vX.Y.Z`
4. Set the release title: `vX.Y.Z`
5. Add release notes (can copy from CHANGELOG.md)
6. Click **Publish release**

This triggers the publish workflow automatically.

### 3. Approve the PyPI Deployment

The workflow uses a protected `pypi` environment that requires approval:

1. Go to [Actions](https://github.com/elijahr/python-autopxd2/actions)
2. Find the running "Publish to PyPI" workflow
3. Click **Review deployments**
4. Select the `pypi` environment and click **Approve and deploy**

The package will be published to PyPI via OIDC trusted publishing.

### Manual Publishing (if needed)

You can also trigger a publish manually:

1. Go to [Actions → Publish to PyPI](https://github.com/elijahr/python-autopxd2/actions/workflows/publish.yml)
2. Click **Run workflow**
3. Enter the git ref (tag or commit SHA)
4. Click **Run workflow**
5. Approve the deployment as above

## PyPI Trusted Publishing Setup

This project uses [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC) instead of API tokens. This is configured on PyPI with:

- **Owner:** `elijahr`
- **Repository:** `python-autopxd2`
- **Workflow:** `publish.yml`
- **Environment:** `pypi`

To add a new maintainer who can approve deployments:

1. Go to [Settings → Environments → pypi](https://github.com/elijahr/python-autopxd2/settings/environments)
2. Under **Required reviewers**, add the maintainer's GitHub username
3. They must have write access to the repository

## Verifying a Release

After publishing, verify:

1. Package appears on [PyPI](https://pypi.org/project/autopxd2/)
2. Version is correct: `pip index versions autopxd2`
3. Installation works: `pip install autopxd2==X.Y.Z`
