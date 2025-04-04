# Makefile for building and testing the aiosimon_io package
# This Makefile is used to automate the process of building, testing,
# and checking the code quality of the aiosimon_io package.
# It provides targets for running tests, checking code style, building
# the package, generating documentation, and uploading the package to PyPI.
# It also includes a target for cleaning up build artifacts.
# The Makefile uses Sphinx for generating documentation and pytest for
# running tests. It also uses flake8, black, isort, and mypy for checking
# code quality. The Makefile is designed to be run from the command line
# and can be customized by setting environment variables or command line
# arguments.

.PHONY: all dev test test-coverage check build docs upload clean

# Prepare development environment
dev:
	@echo "Setting up development environment..."
	@command -v pip > /dev/null 2>&1 || (echo "pip is not installed. Please install it first." && exit 1)
	@rm -fr venv
	@python -m venv venv
	@python -m pip install -e .[dev]
	@echo "Development environment set up. Activate it with 'source venv/bin/activate' (Linux/Mac) or 'venv\Scripts\activate' (Windows)."

# Run tests
test:
	@echo "Running tests..."
	@command -v pytest > /dev/null 2>&1 || (echo "pytest is not installed. Please install it first." && exit 1)
	@pytest > /dev/null 2>&1 && echo "- OK" || (echo "- Tests failed:" && pytest)

# Run tests with coverage
test-coverage:
	@echo "Running tests with coverage..."
	@command -v pytest > /dev/null 2>&1 || (echo "pytest is not installed. Please install it first." && exit 1)
	pytest --cov=aiosimon_io --cov-report=html

check: test
	@echo "Running flake8..."
	@command -v flake8 > /dev/null 2>&1 || (echo "flake8 is not installed. Please install it first." && exit 1)
	@flake8 aiosimon_io/. > /dev/null 2>&1 && echo "- OK" || (echo "- flake8 failed:" && flake8 aiosimon_io/.)
	@flake8 tests/. > /dev/null 2>&1 && echo "- OK" || (echo "- flake8 failed:" && flake8 tests/.)
	@echo "Running black..."
	@command -v black > /dev/null 2>&1 || (echo "black is not installed. Please install it first." && exit 1)
	@black --check aiosimon_io tests > /dev/null 2>&1 && echo "- OK" || (echo "- black failed:" && black --check aiosimon_io tests)
	@echo "Running isort..."
	@command -v isort > /dev/null 2>&1 || (echo "isort is not installed. Please install it first." && exit 1)
	@isort --check-only aiosimon_io tests > /dev/null 2>&1 && echo "- OK" || (echo "- isort failed:" && isort --check-only aiosimon_io tests)
	@echo "Running mypy..."
	@command -v mypy > /dev/null 2>&1 || (echo "mypy is not installed. Please install it first." && exit 1)
	@mypy aiosimon_io/ > /dev/null 2>&1 && echo "- OK" || (echo "- mypy failed:" && mypy aiosimon_io/)
	@echo "Running validate-pyproject..."
	@command -v validate-pyproject > /dev/null 2>&1 || (echo "validate-pyproject is not installed. Please install it first." && exit 1)
	@validate-pyproject pyproject.toml > /dev/null 2>&1 && echo "- OK" || (echo "- validate-pyproject failed:" && validate-pyproject pyproject.toml)

# Generate documentation
docs:
	@echo "Generating documentation..."
	@command -v sphinx-build > /dev/null 2>&1 || (echo "Sphinx is not installed. Please install it first." && exit 1)
	sphinx-build -b html docs/source docs/build/html

# Build the package
build: dev check docs
	@command -v python > /dev/null 2>&1 || (echo "Python is not installed. Please install it first." && exit 1)
	python -m build

# Upload the package to PyPI
upload:
	@command -v twine > /dev/null 2>&1 || (echo "twine is not installed. Please install it first." && exit 1)
	twine upload --repository testpypi dist/*

# Clean build artifacts
clean:
	rm -rf dist *.egg-info htmlcov docs/build .mypy_cache .pytest_cache
