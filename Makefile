.PHONY: help install install-dev test test-unit test-integration test-e2e test-coverage lint format type-check security-check benchmark clean build docker-build docker-run

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install

test: ## Run all tests
	pytest

test-unit: ## Run unit tests only
	pytest tests/unit/ -v

test-integration: ## Run integration tests only
	pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests only
	pytest tests/e2e/ -v

test-coverage: ## Run tests with coverage report
	pytest --cov=src --cov-report=html --cov-report=term-missing

lint: ## Run linting checks
	flake8 src/ tests/
	black --check src/ tests/
	isort --check-only src/ tests/

format: ## Format code with black and isort
	black src/ tests/
	isort src/ tests/

type-check: ## Run type checking with mypy
	mypy src/

security-check: ## Run security checks
	bandit -r src/ -f json -o bandit-report.json
	detect-secrets scan --baseline .secrets.baseline

benchmark: ## Run performance benchmarks
	pytest tests/benchmarks/ --benchmark-only

clean: ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf bandit-report.json

build: ## Build the package
	python -m build

docker-build: ## Build Docker image
	docker build -t kindle-sync:latest .

docker-run: ## Run Docker container
	docker run -d --name kindle-sync -p 8080:8080 -v $(PWD)/config.yaml:/app/config.yaml kindle-sync:latest

quality-check: lint type-check security-check ## Run all quality checks

ci: quality-check test-coverage ## Run CI pipeline locally

dev-setup: install-dev ## Set up development environment
	@echo "Development environment set up successfully!"
	@echo "Run 'make help' to see available commands"