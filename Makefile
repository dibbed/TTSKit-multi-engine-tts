.PHONY: help install install-dev install-optional test test-cov lint format clean build run-bot run-api docs

help: ## Show this help message
	@echo "TTSKit - Multi-Engine TTS Bot & Library"
	@echo "========================================"
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements-dev.txt

install-optional: ## Install optional dependencies
	pip install -r requirements-optional.txt

install-all: ## Install all dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pip install -r requirements-optional.txt

test: ## Run tests
	python -m pytest tests/ -v --maxfail=10

test-cov: ## Run tests with coverage
	python -m pytest tests/ -v --cov=ttskit --cov-report=html --cov-report=term-missing --cov-branch --maxfail=10

test-cov-branch: ## Run tests with branch coverage
	python -m pytest tests/ -v --cov=ttskit --cov-branch --cov-report=html --cov-report=term-missing --cov-report=xml

test-unit: ## Run unit tests only
	python -m pytest tests/ -v -m "unit"

test-integration: ## Run integration tests only
	python -m pytest tests/ -v -m "integration"

test-performance: ## Run performance tests only
	python -m pytest tests/ -v -m "performance"

test-specific: ## Run specific test file (usage: make test-specific FILE=tests/test_public_comprehensive.py)
	python -m pytest $(FILE) -v

test-debug: ## Run tests with debug output
	python -m pytest tests/ -v -s --tb=long

test-fast: ## Run tests without coverage (faster)
	python -m pytest tests/ -v --no-cov

lint: ## Run linting
	ruff check ttskit/ ttskit_cli/ tests/ examples/
	mypy ttskit/ ttskit_cli/

format: ## Format code
	ruff format ttskit/ ttskit_cli/ tests/ examples/
	isort ttskit/ ttskit_cli/ tests/ examples/

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: ## Build package
	python -m build

run-bot: ## Run the Telegram bot
	python -m ttskit_cli.main start

run-api: ## Run the REST API
	python -m ttskit.api.app

run-examples: ## Run example scripts
	python examples/01_basic.py
	python examples/02_fastapi.py
	python examples/03_batch.py

docs: ## Generate documentation
	cd docs && make html

docker-build: ## Build Docker image
	docker build -t ttskit:latest .

docker-run: ## Run Docker container
	docker run -p 8000:8000 --env-file .env ttskit:latest

docker-compose-up: ## Start with docker-compose
	docker-compose up -d

docker-compose-down: ## Stop docker-compose
	docker-compose down

setup: ## Setup TTSKit system (database, migrations, tests)
	python -m ttskit_cli.main setup

setup-dev: ## Setup development environment
	pip install -r requirements-dev.txt
	cp .env.example .env
	python -m ttskit_cli.main setup
	@echo "Development environment setup complete!"
	@echo "Please edit .env file with your configuration."

migrate: ## Run database migrations
	python -m ttskit_cli.main migrate

migrate-check: ## Check migration status
	python -m ttskit_cli.main migrate --check

init-db: ## Initialize database only
	python -c "from ttskit.database.init_db import init_database; init_database()"

test-security: ## Run security tests
	python test_security.py

test-database: ## Run database tests
	python test_database_api.py

test-telegram: ## Run telegram tests
	python test_telegram_database.py

check-deps: ## Check for dependency updates
	pip list --outdated

security-check: ## Run security checks
	bandit -r ttskit/ ttskit_cli/
	safety check

pre-commit: ## Run pre-commit checks
	ruff check ttskit/ ttskit_cli/ tests/ examples/
	ruff format --check ttskit/ ttskit_cli/ tests/ examples/
	mypy ttskit/ ttskit_cli/
	python -m pytest tests/ -v --cov=ttskit --cov-branch --cov-fail-under=80

test-quality: ## Run comprehensive quality checks
	python -m pytest tests/ -v --cov=ttskit --cov-branch --cov-report=html --cov-report=term-missing --cov-fail-under=85
	ruff check ttskit/ ttskit_cli/ tests/ examples/
	mypy ttskit/ ttskit_cli/

ci-test: ## Run tests for CI/CD pipeline
	python -m pytest tests/ -v --cov=ttskit --cov-branch --cov-report=xml --cov-fail-under=80 --junitxml=test-results.xml

test-coverage-report: ## Generate detailed coverage report
	python -m pytest tests/ -v --cov=ttskit --cov-branch --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"
