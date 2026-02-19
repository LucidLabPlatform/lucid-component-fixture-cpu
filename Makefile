PYTHON ?= python3
VENV ?= .venv

.PHONY: help setup-venv test test-unit test-coverage build clean

help:
	@echo "LUCID Component Fixture CPU"
	@echo "  make setup-venv      - Create .venv, install project + deps"
	@echo "  make test            - Run tests"
	@echo "  make test-unit       - Unit tests only"
	@echo "  make test-coverage   - Tests with coverage report"
	@echo "  make build           - Build wheel and sdist (run make setup-venv first)"
	@echo "  make clean           - Remove build artifacts"

setup-venv:
	@test -d $(VENV) || ($(PYTHON) -m venv $(VENV) && echo "Created $(VENV).")
	@$(VENV)/bin/pip install -q -e ".[dev]"
	@$(VENV)/bin/pip install -q build pytest-cov
	@echo "Ready. Run 'make test' or 'make build'."

test: test-unit
	@echo "All tests passed."

test-unit:
	@pytest tests/ -v -q

test-coverage:
	@pytest tests/ --cov=src/lucid_component_fixture_cpu --cov-report=html --cov-report=term-missing -q

build:
	@test -d $(VENV) || (echo "Run 'make setup-venv' first." && exit 1)
	@$(VENV)/bin/python -m build

clean:
	@rm -rf build/ dist/ *.egg-info src/*.egg-info .venv
