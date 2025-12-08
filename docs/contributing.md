# Contributing

We welcome contributions to autopxd2!

## Development Setup

We recommend using [uv](https://github.com/astral-sh/uv) for fast dependency management.

1. Clone the repository:
   ```bash
   git clone https://github.com/elijahr/python-autopxd2.git
   cd python-autopxd2
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   # Using uv (recommended)
   uv venv
   source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
   uv pip install -e '.[test,lint,docs]'

   # Or using pip
   python -m venv .venv
   source .venv/bin/activate
   pip install -e '.[test,lint,docs]'
   ```

3. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest test/test_ir.py

# Run tests with coverage
pytest --cov=autopxd
```

## Code Style

We use [ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Check for issues
ruff check autopxd

# Auto-fix issues
ruff check --fix autopxd

# Format code
ruff format autopxd
```

Pre-commit hooks run automatically on commit to ensure consistent style.

## Type Checking

We use mypy with strict mode:

```bash
mypy autopxd/ --strict
```

## Building Documentation

```bash
# Serve docs locally with live reload
uv run mkdocs serve

# Or without uv
mkdocs serve

# Build static site
mkdocs build
```

The docs will be available at `http://127.0.0.1:8000/`.

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `pytest`
5. Run linters: `ruff check autopxd`
6. Run type check: `mypy autopxd/ --strict`
7. Commit with a clear message
8. Push and create a pull request

## Reporting Issues

Please report issues on [GitHub Issues](https://github.com/elijahr/python-autopxd2/issues).

Include:

- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Relevant error messages or output
