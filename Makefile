# Kindle Scribe Sync - Makefile
# Provides convenient commands for development and testing

.PHONY: help install install-dev test test-unit test-integration test-e2e test-quick test-ci test-coverage clean lint format type-check security docker-build docker-test docker-clean docs

# Default target
help:
	@echo "Kindle Scribe Sync - Available Commands:"
	@echo ""
	@echo "Installation:"
	@echo "  install          Install production dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-e2e         Run end-to-end tests only"
	@echo "  test-quick       Run quick tests (unit, no slow)"
	@echo "  test-ci          Run CI-appropriate tests"
	@echo "  test-coverage    Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             Run linting checks"
	@echo "  format           Format code with black and isort"
	@echo "  type-check       Run type checking with mypy"
	@echo "  security         Run security checks"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build     Build Docker image"
	@echo "  docker-test      Test Docker image"
	@echo "  docker-clean     Clean Docker resources"
	@echo ""
	@echo "Utilities:"
	@echo "  clean            Clean temporary files"
	@echo "  docs             Generate documentation"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-test.txt

# Testing
test:
	./scripts/run-tests.sh --type all --verbose

test-unit:
	./scripts/run-tests.sh --type unit --verbose --coverage

test-integration:
	./scripts/run-tests.sh --type integration --verbose

test-e2e:
	./scripts/run-tests.sh --type e2e --verbose

test-quick:
	./scripts/run-tests.sh --quick --verbose

test-ci:
	./scripts/run-tests.sh --ci --coverage

test-coverage:
	./scripts/run-tests.sh --type all --coverage --report test-report.md

# Code Quality
lint:
	flake8 src/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics
	black --check src/ tests/
	isort --check-only src/ tests/

format:
	black src/ tests/
	isort src/ tests/

type-check:
	mypy src/ --ignore-missing-imports

security:
	bandit -r src/ -f json -o bandit-report.json
	safety check --json --output safety-report.json

# Docker
docker-build:
	docker build -t kindle-sync:latest .

docker-test:
	docker run --rm kindle-sync:latest python -c "import src; print('Import successful')"
	docker-compose config
	docker-compose build

docker-clean:
	docker system prune -f
	docker image prune -f

# Utilities
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -f test-results.xml
	rm -f bandit-report.json
	rm -f safety-report.json
	rm -f test-report.md

docs:
	@echo "Documentation generation not implemented yet"

# Development helpers
dev-setup: install-dev
	@echo "Setting up development environment..."
	@echo "Creating sample config file..."
	cp config.yaml.example config.yaml
	@echo "Development setup complete!"

# Test specific components
test-config:
	python -m pytest tests/unit/test_config.py -v

test-file-watcher:
	python -m pytest tests/unit/test_file_watcher.py -v

test-pdf-converter:
	python -m pytest tests/unit/test_pdf_converter.py -v

test-kindle-sync:
	python -m pytest tests/unit/test_kindle_sync.py -v

test-sync-processor:
	python -m pytest tests/unit/test_sync_processor.py -v

# Performance testing
test-performance:
	python -m pytest tests/ -m "slow" --benchmark-only

# Specific test markers
test-network:
	python -m pytest tests/ -m "network" -v

test-email:
	python -m pytest tests/ -m "email" -v

test-ocr:
	python -m pytest tests/ -m "ocr" -v

test-file-system:
	python -m pytest tests/ -m "file_system" -v

# Continuous integration
ci: test-ci lint type-check security

# Pre-commit checks
pre-commit: format lint type-check test-quick

# Release preparation
release-check: test-coverage lint type-check security docker-test
	@echo "Release checks completed successfully!"

# Help for specific targets
help-test:
	@echo "Test Commands:"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-e2e         Run end-to-end tests only"
	@echo "  test-quick       Run quick tests (unit, no slow)"
	@echo "  test-ci          Run CI-appropriate tests"
	@echo "  test-coverage    Run tests with coverage report"
	@echo "  test-performance Run performance tests"
	@echo "  test-config      Test configuration module"
	@echo "  test-file-watcher Test file watcher module"
	@echo "  test-pdf-converter Test PDF converter module"
	@echo "  test-kindle-sync Test Kindle sync module"
	@echo "  test-sync-processor Test sync processor module"

help-docker:
	@echo "Docker Commands:"
	@echo "  docker-build     Build Docker image"
	@echo "  docker-test      Test Docker image"
	@echo "  docker-clean     Clean Docker resources"

help-quality:
	@echo "Code Quality Commands:"
	@echo "  lint             Run linting checks"
	@echo "  format           Format code with black and isort"
	@echo "  type-check       Run type checking with mypy"
	@echo "  security         Run security checks"
	@echo "  pre-commit       Run pre-commit checks"
	@echo "  ci               Run CI checks"
