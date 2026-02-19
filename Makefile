PYTHON ?= python3
VENV ?= .venv

.PHONY: help setup setup-venv dev test test-unit test-integration test-coverage test-deps build clean

help:
	@echo "LUCID Component Fixture CPU"
	@echo "  make setup           - Create .env from env.example (N/A - component only)"
	@echo "  make setup-venv      - Create .venv, install project + deps"
	@echo "  make test            - Unit + integration tests"
	@echo "  make test-unit       - Unit tests only"
	@echo "  make test-integration - Integration tests (if any)"
	@echo "  make test-coverage   - Tests with coverage report"
	@echo "  make build           - Build wheel and sdist (run make setup-venv first)"
	@echo "  make clean           - Remove build artifacts"

setup:
	@echo "Fixture CPU is a component - no .env needed. Components run via agent-core."

setup-venv:
	@test -d $(VENV) || ($(PYTHON) -m venv $(VENV) && echo "Created $(VENV).")
	@$(VENV)/bin/pip install -q -e ".[dev]"
	@$(VENV)/bin/pip install -q build pytest-cov
	@echo "Ready. Run 'make test' or 'make build'."

dev:
	@echo "Fixture CPU is a component - no standalone runtime. Use 'make test' or 'make build'."

test: test-unit test-integration
	@echo "All tests passed."

test-unit:
	@pytest tests/ -v -q

test-integration:
	@if [ -d tests/integration ]; then \
		pytest tests/integration/ -v -q; \
	else \
		echo "No integration tests."; \
	fi

test-coverage:
	@pytest tests/ --cov=src/lucid_component_fixture_cpu --cov-report=html --cov-report=term-missing -q

test-deps:
	@pip install -r requirements.txt

build:
	@test -d $(VENV) || (echo "Run 'make setup-venv' first." && exit 1)
	@$(VENV)/bin/python -m build

clean:
	@rm -rf build/ dist/ *.egg-info src/*.egg-info
