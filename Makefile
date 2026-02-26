# =============================================================================
# NLP2CMD Makefile
# =============================================================================
# Usage:
#   make help              - Show this help
#   make install           - Install dependencies
#   make setup-cache       - Setup external dependencies cache
#   make test              - Run all tests
#   make test-examples     - Run all examples
#   make test-e2e          - Run E2E tests
#   make test-web-schema   - Test web schema functionality
#   make docker-build      - Build Docker images
#   make docker-up         - Start services
#   make docker-test       - Run tests in Docker
#   make docker-push       - Push Docker image to registry
#   make push              - Complete release (bump version + build + push Docker + PyPI + Git tag)
#   make git-tag           - Create and push git tag for current version
#   make bump-patch        - Bump patch version (X.Y.Z -> X.Y.Z+1)
#   make bump-minor        - Bump minor version (X.Y.Z -> X.Y+1.0)
#   make bump-major        - Bump major version (X.Y.Z -> X+1.0.0)
#   make publish           - Publish to PyPI (with automatic patch bump)
# =============================================================================

.PHONY: help install setup-cache test test-unit test-e2e test-web-schema lint format clean \
        docker-build docker-up docker-down docker-test docker-e2e docker-push \
        dev demo demo-benchmark test-examples bump-patch bump-minor bump-major publish publish-test push git-tag report \
        scripts-maintenance scripts-thermo scripts-test \
        all 01_basics 02_benchmarks 03_integrations 04_domain_specific 05_advanced_features 06_tools_and_utilities

# Default target
.DEFAULT_GOAL := help

# Project settings
PROJECT_NAME := nlp2cmd
PYTHON := /usr/bin/python3.12
PIP := $(PYTHON) -m pip
PYTEST := pytest
DOCKER_COMPOSE := docker compose

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# =============================================================================
# Help
# =============================================================================

help: ## Show this help message
	@echo "$(BLUE)NLP2CMD - Natural Language to Domain-Specific Commands$(NC)"
	@echo ""
	@echo "$(YELLOW)Usage:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make install       # Install in development mode"
	@echo "  make test          # Run all tests"
	@echo "  make test-examples # Run all examples"
	@echo "  make docker-up     # Start Docker services"
	@echo "  make demo          # Run the demo"

# =============================================================================
# Development
# =============================================================================

install: ## Install package in development mode
	$(PIP) install -e ".[dev]" --break-system-packages

install-all: ## Install package with all dependencies
	$(PIP) install -e ".[all]" --break-system-packages

install-ci: ## Install for CI (no editable)
	$(PIP) install ".[dev]" --break-system-packages

deps: ## Install dependencies only
	$(PIP) install -r requirements.txt --break-system-packages

setup-cache: ## Setup external dependencies cache (Playwright browsers)
	@echo "$(BLUE)Setting up external dependencies cache...$(NC)"
	$(PYTHON) -m $(PROJECT_NAME) cache auto-setup
	@echo "$(GREEN)✓ Cache setup complete!$(NC)"

setup-dev: ## Complete development setup
	@echo "$(BLUE)Setting up development environment...$(NC)"
	$(MAKE) install-all
	$(MAKE) setup-cache
	@echo "$(GREEN)✓ Development setup complete!$(NC)"

# =============================================================================
# Testing
# =============================================================================

test: ## Run all tests
	$(PYTEST) tests/ -v --tb=short

test-unit: ## Run unit tests only
	$(PYTEST) tests/unit/ -v --tb=short

test-e2e: ## Run E2E tests only
	$(PYTEST) tests/e2e/ -v --tb=short

test-integration: ## Run integration tests only
	$(PYTEST) tests/integration/ -v --tb=short

test-web-schema: ## Test web schema functionality
	$(PYTEST) tests/iterative/test_typos_and_variations.py::TestTyposAndVariations::test_docker_typos -v
	$(PYTEST) tests/iterative/test_typos_and_variations.py::TestTyposAndVariations::test_shell_service_variations -v

test-nlp: ## Test NLP functionality (Polish language, fuzzy matching)
	$(PYTEST) tests/iterative/test_typos_and_variations.py -v

test-enhanced: ## Test enhanced NLP integration
	@echo "$(BLUE)Testing enhanced NLP integration...$(NC)"
	$(PYTHON) -c "from src.nlp2cmd.generation.enhanced_context import get_enhanced_detector; detector = get_enhanced_detector(); print('✓ Enhanced NLP available' if detector else '✗ Enhanced NLP not available')"

test-interactive: ## Test interactive shell mode
	@echo "$(BLUE)Testing interactive shell mode...$(NC)"
	@echo "Testing shell emulation with Polish commands..."
	@echo "Commands to test manually:"
	@echo "  nlp2cmd --interactive --dsl shell"
	@echo "  > pokaz pliki usera"
	@echo "  > znajdz pliki .log"
	@echo "  > uruchom usluge nginx"
	@echo "  > exit"

test-cache: ## Test cache management
	@echo "$(BLUE)Testing cache management...$(NC)"
	$(PYTHON) -m $(PROJECT_NAME) cache info
	$(PYTHON) -m $(PROJECT_NAME) cache check

test-cov: ## Run tests with coverage report
	$(PYTEST) tests/ -v --cov=$(PROJECT_NAME) --cov-report=html --cov-report=term

test-watch: ## Run tests in watch mode (requires pytest-watch)
	ptw tests/ -- -v --tb=short

# =============================================================================
# Code Quality
# =============================================================================

lint: ## Run linters (ruff, mypy)
	ruff check src/$(PROJECT_NAME)/ tests/
	mypy src/$(PROJECT_NAME)/ --ignore-missing-imports

format: ## Format code with ruff and black
	ruff format src/$(PROJECT_NAME)/ tests/
	black src/$(PROJECT_NAME)/ tests/

format-check: ## Check code formatting
	ruff format --check src/$(PROJECT_NAME)/ tests/
	black --check src/$(PROJECT_NAME)/ tests/

# =============================================================================
# Docker
# =============================================================================

docker-build: ## Build Docker images
	$(DOCKER_COMPOSE) build

docker-build-no-cache: ## Build Docker images without cache
	$(DOCKER_COMPOSE) build --no-cache

docker-up: ## Start all services
	$(DOCKER_COMPOSE) up -d

docker-up-dev: ## Start development services
	$(DOCKER_COMPOSE) --profile dev up -d

docker-down: ## Stop all services
	$(DOCKER_COMPOSE) down

docker-down-v: ## Stop all services and remove volumes
	$(DOCKER_COMPOSE) down -v

docker-test: ## Run tests in Docker
	$(DOCKER_COMPOSE) --profile test run --rm nlp2cmd-test

docker-e2e: ## Run E2E tests in Docker
	$(DOCKER_COMPOSE) --profile e2e run --rm nlp2cmd-e2e

docker-logs: ## Show logs
	$(DOCKER_COMPOSE) logs -f

docker-shell: ## Open shell in container
	$(DOCKER_COMPOSE) exec nlp2cmd /bin/bash

docker-ps: ## Show running containers
	$(DOCKER_COMPOSE) ps

docker-push: ## Push Docker image to registry
	@echo "$(YELLOW)Building Docker image...$(NC)"
	$(MAKE) docker-build
	@echo "$(YELLOW)Tagging Docker image with version...$(NC)"
	@VERSION=$$($(PWD)/venv/bin/python -c "import toml; content = toml.load(open('pyproject.toml')); print(content['project']['version'])") && \
	docker tag nlp2cmd:latest nlp2cmd:$$VERSION
	@echo "$(YELLOW)Pushing Docker image to registry...$(NC)"
	@echo "$(BLUE)Note: Make sure you're authenticated with Docker Hub:$(NC)"
	@echo "$(BLUE)  docker login$(NC)"
	@if docker push nlp2cmd:latest 2>/dev/null && docker push nlp2cmd:$$VERSION 2>/dev/null; then \
		echo "$(GREEN)Docker image pushed successfully!$(NC)"; \
	else \
		echo "$(YELLOW)Docker push failed. Please check:$(NC)"; \
		echo "$(YELLOW)1. Are you logged in to Docker Hub? Run: docker login$(NC)"; \
		echo "$(YELLOW)2. Do you have push permissions for the nlp2cmd repository?$(NC)"; \
		echo "$(YELLOW)3. Is your internet connection working?$(NC)"; \
		exit 1; \
	fi

# =============================================================================
# Development Utilities
# =============================================================================

demo: ## Run the end-to-end demo
	$(PYTHON) examples/architecture/end_to_end_demo.py

demo-benchmark: ## Run the benchmark demo
	PYTHONPATH=src $(PYTHON) examples/benchmark_nlp2cmd.py

demo-web: ## Demo web schema extraction
	@echo "$(BLUE)Demo: Web schema extraction...$(NC)"
	$(PYTHON) -m $(PROJECT_NAME) web-schema extract https://httpbin.org/forms/post --headless

demo-cache: ## Demo cache management
	@echo "$(BLUE)Demo: Cache management...$(NC)"
	$(PYTHON) -m $(PROJECT_NAME) cache info

demo-interactive: ## Demo interactive shell mode
	@echo "$(BLUE)Demo: Interactive shell mode...$(NC)"
	@echo "$(YELLOW)Starting interactive shell with Polish NLP...$(NC)"
	@echo "$(YELLOW)Try these commands:$(NC)"
	@echo "  > pokaz pliki usera"
	@echo "  > znajdz pliki .log wieksze niz 10MB"
	@echo "  > uruchom usluge nginx"
	@echo "  > pokaż procesy zużywające najwięcej pamięci"
	@echo "  > exit"
	@echo ""
	@echo "$(BLUE)Press Enter to start interactive mode...$(NC)"
	@read -r
	$(PYTHON) -m $(PROJECT_NAME) --interactive --dsl shell

test-examples: ## Run all examples to test functionality
	@echo "$(BLUE)Testing all examples...$(NC)"
	@echo "$(YELLOW)Architecture examples:$(NC)"
	PYTHONPATH=src $(PYTHON) examples/architecture/end_to_end_demo.py
	@echo ""
	@echo "$(YELLOW)Docker examples:$(NC)"
	PYTHONPATH=src $(PYTHON) examples/docker/basic_docker.py
	PYTHONPATH=src $(PYTHON) examples/docker/file_repair.py
	@echo ""
	@echo "$(YELLOW)Kubernetes examples:$(NC)"
	PYTHONPATH=src $(PYTHON) examples/kubernetes/basic_kubernetes.py
	@echo ""
	@echo "$(YELLOW)Pipeline examples:$(NC)"
	PYTHONPATH=src $(PYTHON) examples/pipelines/infrastructure_health.py
	PYTHONPATH=src $(PYTHON) examples/pipelines/log_analysis.py
	@echo ""
	@echo "$(YELLOW)Shell examples:$(NC)"
	PYTHONPATH=src $(PYTHON) examples/shell/basic_shell.py
	PYTHONPATH=src $(PYTHON) examples/shell/environment_analysis.py
	PYTHONPATH=src $(PYTHON) examples/shell/feedback_loop.py
	@echo ""
	@echo "$(YELLOW)SQL examples:$(NC)"
	@for file in examples/sql/*.py; do \
		if [ -f "$$file" ]; then \
			echo "Running $$file..."; \
			PYTHONPATH=src $(PYTHON) "$$file"; \
		fi; \
	done
	@echo ""
	@echo "$(YELLOW)Validation examples:$(NC)"
	PYTHONPATH=src $(PYTHON) examples/validation/config_validation.py
	@echo ""
	@echo "$(GREEN)All examples completed!$(NC)"

all:
	$(MAKE) -C examples all

01_basics 02_benchmarks 03_integrations 04_domain_specific 05_advanced_features 06_tools_and_utilities:
	$(MAKE) -C examples $@

repl: ## Start interactive REPL
	$(PYTHON) -m $(PROJECT_NAME).cli

run-example: ## Run a specific example (usage: make run-example FILE=sql/basic_sql.py)
	$(PYTHON) examples/$(FILE)

# =============================================================================
# Cleanup
# =============================================================================

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

clean-cache: ## Clean external dependencies cache
	@echo "$(YELLOW)Cleaning external dependencies cache...$(NC)"
	$(PYTHON) -m $(PROJECT_NAME) cache clear --all
	@echo "$(GREEN)✓ Cache cleared!$(NC)"

clean-docker: ## Clean Docker resources
	$(DOCKER_COMPOSE) down -v --rmi local
	docker system prune -f

clean-all: clean clean-docker clean-cache ## Clean everything including cache

# =============================================================================
# Release
# =============================================================================

build: clean ## Build package
	$(PYTHON) -m build

publish-test: build ## Publish to TestPyPI
	@echo "$(YELLOW)Creating temporary virtual environment for twine...$(NC)"
	$(PYTHON) -m venv publish-test-env
	publish-test-env/bin/pip install twine
	publish-test-env/bin/python -m twine upload --repository testpypi dist/*
	rm -rf publish-test-env

bump-patch: ## Bump patch version (X.Y.Z -> X.Y.Z+1)
	@echo "$(YELLOW)Bumping patch version...$(NC)"
	$(PYTHON) scripts/bump_version.py patch

bump-minor: ## Bump minor version (X.Y.Z -> X.Y+1.0)
	@echo "$(YELLOW)Bumping minor version...$(NC)"
	$(PYTHON) scripts/bump_version.py minor

bump-major: ## Bump major version (X.Y.Z -> X+1.0.0)
	@echo "$(YELLOW)Bumping major version...$(NC)"
	$(PYTHON) scripts/bump_version.py major

publish: build ## Publish to PyPI (with version bump)
	@echo "$(YELLOW)Bumping patch version...$(NC)"
	$(MAKE) bump-patch
	@echo "$(YELLOW)Rebuilding package with new version...$(NC)"
	$(MAKE) build
	@echo "$(YELLOW)Publishing to PyPI...$(NC)"
	@echo "$(YELLOW)Creating temporary virtual environment for twine...$(NC)"
	$(PYTHON) -m venv publish-env
	publish-env/bin/pip install twine
	publish-env/bin/python -m twine upload dist/*
	rm -rf publish-env

push: ## Complete release (bump version + build + push Docker + PyPI + Git tag)
	@echo "$(YELLOW)Starting complete release process...$(NC)"
	@echo "$(YELLOW)1. Bumping patch version...$(NC)"
	$(MAKE) bump-patch
	@echo "$(YELLOW)2. Building package...$(NC)"
	$(MAKE) build
	@echo "$(YELLOW)3. Publishing to PyPI...$(NC)"
	@echo "$(YELLOW)Creating temporary virtual environment for twine...$(NC)"
	$(PYTHON) -m venv push-env
	push-env/bin/pip install twine
	push-env/bin/python -m twine upload dist/*
	rm -rf push-env
	@echo "$(YELLOW)4. Building and pushing Docker image...$(NC)"
	@if $(MAKE) docker-push; then \
		echo "$(GREEN)Docker image pushed successfully!$(NC)"; \
		echo "$(YELLOW)5. Creating and pushing git tag...$(NC)"; \
		VERSION=$$($(PYTHON) -c "import toml; content = toml.load(open('pyproject.toml')); print(content['project']['version'])") && \
		git tag v$$VERSION && \
		git push origin v$$VERSION && \
		echo "$(GREEN)🎉 Complete release finished successfully!$(NC)"; \
		echo "$(GREEN)   - Package published to PyPI ✓$(NC)"; \
		echo "$(GREEN)   - Docker image pushed to registry ✓$(NC)"; \
		echo "$(GREEN)   - Git tag v$$VERSION pushed ✓$(NC)"; \
		echo "$(GREEN)   - Version bumped automatically ✓$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  Partial release completed!$(NC)"; \
		echo "$(YELLOW)   - Package published to PyPI ✓$(NC)"; \
		echo "$(YELLOW)   - Docker push failed ✗$(NC)"; \
		echo "$(YELLOW)   - Version bumped automatically ✓$(NC)"; \
		echo "$(BLUE)To complete the Docker push and git tag later:$(NC)"; \
		echo "$(BLUE)  docker login && make docker-push && make git-tag$(NC)"; \
	fi

git-tag: ## Create and push git tag for current version
	@echo "$(YELLOW)Creating and pushing git tag...$(NC)"
	@VERSION=$$($(PYTHON) -c "import toml; content = toml.load(open('pyproject.toml')); print(content['project']['version'])") && \
	git tag v$$VERSION && \
	git push origin v$$VERSION && \
	echo "$(GREEN)Git tag v$$VERSION pushed successfully!$(NC)"

# =============================================================================
# Info
# =============================================================================

version: ## Show version
	@$(PYTHON) -c "import $(PROJECT_NAME); print($(PROJECT_NAME).__version__)"

info: ## Show project info
	@echo "$(BLUE)Project:$(NC) $(PROJECT_NAME)"
	@echo "$(BLUE)Python:$(NC) $(shell $(PYTHON) --version)"
	@echo "$(BLUE)Pip:$(NC) $(shell $(PIP) --version)"
	@echo "$(BLUE)Version:$(NC) $(shell $(PYTHON) -c 'import $(PROJECT_NAME); print($(PROJECT_NAME).__version__)')

# =============================================================================
# Benchmarking and Reporting
# =============================================================================

report: benchmark ## Alias for benchmark target

benchmark: ## Run LLM benchmark (3 models ≤3B, all 6 nlp2cmd domains)
	@echo "$(BLUE)Running NLP2CMD LLM Benchmark...$(NC)"
	@echo "$(YELLOW)Testing 3 local models (≤3B) across shell, docker, sql, kubernetes, browser, git$(NC)"
	@echo "$(YELLOW)Requires: ollama running locally$(NC)"
	PYTHONPATH=src $(PYTHON) examples/benchmark_nlp2cmd.py
	@echo ""
	@echo "$(GREEN)✓ Benchmark complete!$(NC)"
	@echo "$(BLUE)Reports in benchmark_output/:$(NC)"
	@echo "  - benchmark_results.json  (detailed JSON)"
	@echo "  - benchmark_results.html  (interactive charts)"
	@echo "  - refactoring_plan.md     (refactoring recommendations)"
	@echo "  - benchmark.log           (execution log)"
	@echo ""
	@echo "$(YELLOW)Open HTML report:$(NC)"
	@echo "  xdg-open benchmark_output/benchmark_results.html"

benchmark-view: ## View the last benchmark summary JSON
	@if [ -f benchmark_output/benchmark_results.json ]; then \
		echo "$(BLUE)Last Benchmark Summary:$(NC)"; \
		cat benchmark_output/benchmark_results.json | jq '.summary'; \
	else \
		echo "$(YELLOW)No benchmark results found. Run 'make benchmark' first.$(NC)"; \
	fi

benchmark-html: ## Open benchmark HTML report in browser
	@if [ -f benchmark_output/benchmark_results.html ]; then \
		xdg-open benchmark_output/benchmark_results.html; \
	else \
		echo "$(YELLOW)No HTML report found. Run 'make benchmark' first.$(NC)"; \
	fi

benchmark-plan: ## View refactoring plan from benchmark
	@if [ -f benchmark_output/refactoring_plan.md ]; then \
		cat benchmark_output/refactoring_plan.md; \
	else \
		echo "$(YELLOW)No refactoring plan found. Run 'make benchmark' first.$(NC)"; \
	fi

benchmark-clean: ## Clean benchmark output
	rm -rf benchmark_output/
	@echo "$(GREEN)✓ Benchmark output cleaned!$(NC)"

# =============================================================================
# Scripts Organization
# =============================================================================

scripts-maintenance: ## List maintenance scripts
	@echo "$(BLUE)Maintenance Scripts:$(NC)"
	@ls -la scripts/maintenance/
	@echo ""
	@echo "$(YELLOW)Available scripts:$(NC)"
	@for script in scripts/maintenance/*.py; do \
		if [ -f "$$script" ]; then \
			echo "  $$(basename $$script) - $$(grep '^"""' "$$script" | head -1 | sed 's/"""//g' | sed 's/^[[:space:]]*//')"; \
		fi; \
	done

scripts-thermo: ## List thermodynamic scripts
	@echo "$(BLUE)Thermodynamic Scripts:$(NC)"
	@ls -la scripts/thermodynamic/
	@echo ""
	@echo "$(YELLOW)Available scripts:$(NC)"
	@for script in scripts/thermodynamic/*.py; do \
		if [ -f "$$script" ]; then \
			echo "  $$(basename $$script) - $$(grep '^"""' "$$script" | head -1 | sed 's/"""//g' | sed 's/^[[:space:]]*//')"; \
		fi; \
	done

scripts-test: ## List testing scripts
	@echo "$(BLUE)Testing Scripts:$(NC)"
	@ls -la scripts/testing/
	@echo ""
	@echo "$(YELLOW)Available scripts:$(NC)"
	@for script in scripts/testing/*.py; do \
		if [ -f "$$script" ]; then \
			echo "  $$(basename $$script) - $$(grep '^"""' "$$script" | head -1 | sed 's/"""//g' | sed 's/^[[:space:]]*//')"; \
		fi; \
	done

scripts-all: ## List all organized scripts
	@echo "$(BLUE)All Scripts Organization:$(NC)"
	@echo ""
	$(MAKE) scripts-maintenance
	@echo ""
	$(MAKE) scripts-thermo
	@echo ""
	$(MAKE) scripts-test

run-thermo: ## Run thermodynamic demo
	@echo "$(BLUE)Running thermodynamic demo...$(NC)"
	$(PYTHON) scripts/thermodynamic/termo_demo.py
