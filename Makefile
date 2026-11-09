.PHONY: help install test lint format typecheck docker-up docker-down docker-prune clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync

test: ## Run all tests
	uv run pytest tests/ -v

test-unit: ## Run unit tests only
	uv run pytest tests/unit/ -v

test-integration: ## Run integration tests only
	uv run pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests only
	uv run pytest tests/e2e/ -v

lint: ## Run linter
	uv run ruff check .

format: ## Run formatter
	uv run ruff format .

typecheck: ## Run type checker
	uv run mypy src/

docker-up: ## Start Docker services
	docker compose up -d

docker-down: ## Stop Docker services
	docker compose down

docker-prune: ## Reclaim all Docker build cache and dangling images (keeps volumes)
	docker builder prune -af
	docker image prune -f

clean: ## Clean generated files
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
