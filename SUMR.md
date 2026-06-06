# NLP2CMD

SUMD - Structured Unified Markdown Descriptor for AI-aware project refactorization

## Contents

- [Metadata](#metadata)
- [Architecture](#architecture)
- [Workflows](#workflows)
- [Quality Pipeline (`pyqual.yaml`)](#quality-pipeline-pyqualyaml)
- [Dependencies](#dependencies)
- [Call Graph](#call-graph)
- [Refactoring Analysis](#refactoring-analysis)
- [Intent](#intent)

## Metadata

- **name**: `nlp2cmd`
- **version**: `1.1.22`
- **python_requires**: `>=3.10`
- **license**: Apache-2.0
- **ai_model**: `openrouter/qwen/qwen3-coder-next`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, requirements-enhanced.txt, requirements-minimal.txt, requirements-thermodynamic.txt, requirements.llm.txt, requirements.txt, Makefile, app.doql.less, pyqual.yaml, goal.yaml, .env.example, Dockerfile, docker-compose.yml, project/(6 analysis files)

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

### DOQL Application Declaration (`app.doql.less`)

```less markpact:doql path=app.doql.less
// LESS format — define @variables here as needed

app {
  name: nlp2cmd;
  version: 1.1.22;
}

dependencies {
  runtime: "pyyaml>=6.0, pydantic>=2.0, rich>=13.0, click>=8.0, httpx>=0.25.0, jinja2>=3.0, jsonschema>=4.0, python-dotenv>=1.0, watchdog>=3.0, numpy>=1.24.0, psutil>=5.9.0, rapidfuzz>=3.0, nlp2cmd-intent>=0.1.1";
  dev: "pytest>=7.0, pytest-cov>=4.0, pytest-asyncio>=0.21, pytest-xdist>=3.0, pytest-mock>=3.10, playwright>=1.40.0, black>=23.0, ruff>=0.1, mypy>=1.0, pre-commit>=3.0, mkdocs>=1.5, mkdocs-material>=9.0, goal>=2.1.0, costs>=0.1.20, pfix>=0.1.60, mkdocstrings[python]>=0.24";
}

entity[name="FlowNode"] {
  id: string!;
  type: string!;
  label: string!;
  function: string;
  file: string;
  line: int;
  column: int;
  conditions: List[str]!;
  data_flow: List[str]!;
  metadata: Dict[str, Any]!;
}

entity[name="FlowEdge"] {
  source: string!;
  target: string!;
  edge_type: string!;
  label: string;
  conditions: List[str]!;
}

entity[name="FunctionInfo"] {
  name: string!;
  qualified_name: string!;
  file: string!;
  line: int!;
  column: int!;
  module: string!;
  class_name: string;
  is_method: bool!;
  is_private: bool!;
  is_property: bool!;
  docstring: string;
  args: List[str]!;
  returns: string;
  decorators: List[str]!;
  cfg_entry: string;
  cfg_exit: string;
  cfg_nodes: List[str]!;
  calls: List[str]!;
  called_by: List[str]!;
  complexity: Dict[str, Any]!;
  centrality: float!;
  reachability: string!;
}

entity[name="ClassInfo"] {
  name: string!;
  qualified_name: string!;
  file: string!;
  line: int!;
  module: string!;
  bases: List[str]!;
  methods: List[str]!;
  docstring: string;
  is_state_machine: bool!;
}

entity[name="ModuleInfo"] {
  name: string!;
  file: string!;
  is_package: bool!;
  imports: List[str]!;
  functions: List[str]!;
  classes: List[str]!;
}

entity[name="Pattern"] {
  name: string!;
  type: string!;
  confidence: float!;
  functions: List[str]!;
  entry_points: List[str]!;
  exit_points: List[str]!;
  metadata: Dict[str, Any]!;
}

entity[name="CodeSmell"] {
  name: string!;
  type: string!;
  file: string!;
  line: int!;
  severity: float!;
  description: string!;
  context: Dict[str, Any]!;
}

entity[name="Mutation"] {
  variable: string!;
  file: string!;
  line: int!;
  type: string!;
  scope: string!;
  context: string!;
}

entity[name="DataFlow"] {
  variable: string!;
  dependencies: Set[str]!;
  metadata: Dict[str, Any]!;
}

entity[name="Users"] {
  id: serial;
  uuid: uuid;
}

entity[name="Products"] {
  id: serial;
  sku: string;
}

entity[name="Orders"] {
  id: serial;
  user_id: int;
}

entity[name="OrderItems"] {
  id: serial;
  order_id: int;
}

entity[name="Logs"] {
  id: serial;
  timestamp: datetime;
  level: string;
}

database[name="postgres"] {
  type: postgresql;
  url: env.DATABASE_URL;
}

database[name="redis"] {
  type: redis;
  url: env.REDIS_URL;
}

interface[type="api"] {
  type: rest;
  framework: fastapi;
}

interface[type="cli"] {
  framework: click;
}
interface[type="cli"] page[name="nlp2cmd"] {

}

integration[name="email"] {
  type: smtp;
}

integration[name="nlp"] {
  type: api;
}

workflow[name="install"] {
  trigger: manual;
  step-1: run cmd=$(PIP) install -e ".[dev]" --break-system-packages;
}

workflow[name="install-all"] {
  trigger: manual;
  step-1: run cmd=$(PIP) install -e ".[all]" --break-system-packages;
}

workflow[name="install-desktop"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)Installing desktop automation tools...$(NC)";
  step-2: run cmd=./scripts/install_desktop_tools.sh;
}

workflow[name="install-ci"] {
  trigger: manual;
  step-1: run cmd=$(PIP) install ".[dev]" --break-system-packages;
}

workflow[name="deps"] {
  trigger: manual;
  step-1: run cmd=$(PIP) install -r requirements.txt --break-system-packages;
}

workflow[name="setup-cache"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)Setting up external dependencies cache...$(NC)";
  step-2: run cmd=$(PYTHON) -m $(PROJECT_NAME) cache auto-setup;
  step-3: run cmd=echo "$(GREEN)✓ Cache setup complete!$(NC)";
}

workflow[name="setup-dev"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)Setting up development environment...$(NC)";
  step-2: run cmd=$(MAKE) install-all;
  step-3: run cmd=$(MAKE) setup-cache;
  step-4: run cmd=echo "$(YELLOW)Note: For desktop automation support, run: make install-desktop$(NC)";
  step-5: run cmd=echo "$(GREEN)✓ Development setup complete!$(NC)";
}

workflow[name="update"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)Updating nlp2cmd and integration dependencies...$(NC)";
  step-2: run cmd=NLP2DSL_DIR="$(NLP2DSL_DIR)" bash scripts/update_integration_deps.sh;
  step-3: run cmd=echo "$(GREEN)✓ Update complete!$(NC)";
}

workflow[name="setup-dev-integration"] {
  trigger: manual;
  step-1: depend target=update;
}

workflow[name="test"] {
  trigger: manual;
  step-1: run cmd=$(PYTEST) tests/ -v --tb=short;
}

workflow[name="test-fast"] {
  trigger: manual;
  step-1: run cmd=$(PYTEST) tests/ -v --tb=short -m "not e2e and not slow and not browser";
}

workflow[name="test-slow"] {
  trigger: manual;
  step-1: run cmd=$(PYTEST) tests/ -v --tb=short -m "slow";
}

workflow[name="test-parallel"] {
  trigger: manual;
  step-1: run cmd=$(PYTEST) tests/ -v --tb=short -n auto --dist=loadscope;
}

workflow[name="test-unit"] {
  trigger: manual;
  step-1: run cmd=$(PYTEST) tests/unit/ -v --tb=short;
}

workflow[name="test-e2e"] {
  trigger: manual;
  step-1: run cmd=$(PYTEST) tests/e2e/ -v --tb=short;
}

workflow[name="test-integration"] {
  trigger: manual;
  step-1: run cmd=$(PYTEST) tests/integration/ -v --tb=short;
}

workflow[name="test-web-schema"] {
  trigger: manual;
  step-1: run cmd=$(PYTEST) tests/iterative/test_typos_and_variations.py::TestTyposAndVariations::test_docker_typos -v;
  step-2: run cmd=$(PYTEST) tests/iterative/test_typos_and_variations.py::TestTyposAndVariations::test_shell_service_variations -v;
}

workflow[name="test-nlp"] {
  trigger: manual;
  step-1: run cmd=$(PYTEST) tests/iterative/test_typos_and_variations.py -v;
}

workflow[name="test-enhanced"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)Testing enhanced NLP integration...$(NC)";
  step-2: run cmd=$(PYTHON) -c "from src.nlp2cmd.generation.enhanced_context import get_enhanced_detector; detector = get_enhanced_detector(); print('✓ Enhanced NLP available' if detector else '✗ Enhanced NLP not available')";
}

workflow[name="test-interactive"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)Testing interactive shell mode...$(NC)";
  step-2: run cmd=echo "Testing shell emulation with Polish commands...";
  step-3: run cmd=echo "Commands to test manually:";
  step-4: run cmd=echo "  nlp2cmd --interactive --dsl shell";
  step-5: run cmd=echo "  > pokaz pliki usera";
  step-6: run cmd=echo "  > znajdz pliki .log";
  step-7: run cmd=echo "  > uruchom usluge nginx";
  step-8: run cmd=echo "  > exit";
}

workflow[name="test-cache"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)Testing cache management...$(NC)";
  step-2: run cmd=$(PYTHON) -m $(PROJECT_NAME) cache info;
  step-3: run cmd=$(PYTHON) -m $(PROJECT_NAME) cache check;
}

workflow[name="test-cov"] {
  trigger: manual;
  step-1: run cmd=$(PYTEST) tests/ -v --cov=$(PROJECT_NAME) --cov-report=html --cov-report=term;
}

workflow[name="test-watch"] {
  trigger: manual;
  step-1: run cmd=ptw tests/ -- -v --tb=short;
}

workflow[name="lint"] {
  trigger: manual;
  step-1: run cmd=ruff check src/$(PROJECT_NAME)/ tests/;
  step-2: run cmd=mypy src/$(PROJECT_NAME)/ --ignore-missing-imports;
}

workflow[name="format"] {
  trigger: manual;
  step-1: run cmd=ruff format src/$(PROJECT_NAME)/ tests/;
  step-2: run cmd=black src/$(PROJECT_NAME)/ tests/;
}

workflow[name="format-check"] {
  trigger: manual;
  step-1: run cmd=ruff format --check src/$(PROJECT_NAME)/ tests/;
  step-2: run cmd=black --check src/$(PROJECT_NAME)/ tests/;
}

workflow[name="docker-build"] {
  trigger: manual;
  step-1: run cmd=$(DOCKER_COMPOSE) build;
}

workflow[name="docker-build-no-cache"] {
  trigger: manual;
  step-1: run cmd=$(DOCKER_COMPOSE) build --no-cache;
}

workflow[name="docker-up"] {
  trigger: manual;
  step-1: run cmd=$(DOCKER_COMPOSE) up -d;
}

workflow[name="docker-up-dev"] {
  trigger: manual;
  step-1: run cmd=$(DOCKER_COMPOSE) --profile dev up -d;
}

workflow[name="docker-down"] {
  trigger: manual;
  step-1: run cmd=$(DOCKER_COMPOSE) down;
}

workflow[name="docker-down-v"] {
  trigger: manual;
  step-1: run cmd=$(DOCKER_COMPOSE) down -v;
}

workflow[name="docker-test"] {
  trigger: manual;
  step-1: run cmd=$(DOCKER_COMPOSE) --profile test run --rm nlp2cmd-test;
}

workflow[name="docker-e2e"] {
  trigger: manual;
  step-1: run cmd=$(DOCKER_COMPOSE) --profile e2e run --rm nlp2cmd-e2e;
}

workflow[name="docker-logs"] {
  trigger: manual;
  step-1: run cmd=$(DOCKER_COMPOSE) logs -f;
}

workflow[name="docker-shell"] {
  trigger: manual;
  step-1: run cmd=$(DOCKER_COMPOSE) exec nlp2cmd /bin/bash;
}

workflow[name="docker-ps"] {
  trigger: manual;
  step-1: run cmd=$(DOCKER_COMPOSE) ps;
}

workflow[name="docker-push"] {
  trigger: manual;
  step-1: run cmd=echo "$(YELLOW)Building Docker image...$(NC)";
  step-2: run cmd=$(MAKE) docker-build;
  step-3: run cmd=echo "$(YELLOW)Tagging Docker image with version...$(NC)";
  step-4: run cmd=VERSION=$$($(PWD)/venv/bin/python -c "import toml; content = toml.load(open('pyproject.toml')); print(content['project']['version'])") && \;
  step-5: run cmd=docker tag nlp2cmd:latest nlp2cmd:$$VERSION;
  step-6: run cmd=echo "$(YELLOW)Pushing Docker image to registry...$(NC)";
  step-7: run cmd=echo "$(BLUE)Note: Make sure you're authenticated with Docker Hub:$(NC)";
  step-8: run cmd=echo "$(BLUE)  docker login$(NC)";
  step-9: run cmd=if docker push nlp2cmd:latest 2>/dev/null && docker push nlp2cmd:$$VERSION 2>/dev/null; then \;
  step-10: run cmd=echo "$(GREEN)Docker image pushed successfully!$(NC)"; \;
  step-11: run cmd=else \;
  step-12: run cmd=echo "$(YELLOW)Docker push failed. Please check:$(NC)"; \;
  step-13: run cmd=echo "$(YELLOW)1. Are you logged in to Docker Hub? Run: docker login$(NC)"; \;
  step-14: run cmd=echo "$(YELLOW)2. Do you have push permissions for the nlp2cmd repository?$(NC)"; \;
  step-15: run cmd=echo "$(YELLOW)3. Is your internet connection working?$(NC)"; \;
  step-16: run cmd=exit 1; \;
  step-17: run cmd=fi;
}

workflow[name="demo"] {
  trigger: manual;
  step-1: run cmd=PYTHONPATH=src $(PYTHON) examples/05_advanced_features/schema_driven_architecture/end_to_end_demo.py;
}

workflow[name="demo-benchmark"] {
  trigger: manual;
  step-1: run cmd=PYTHONPATH=src $(PYTHON) benchmarks/llm_benchmark.py;
}

workflow[name="demo-web"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)Demo: Web schema extraction...$(NC)";
  step-2: run cmd=$(PYTHON) -m $(PROJECT_NAME) web-schema extract https://httpbin.org/forms/post --headless;
}

workflow[name="demo-cache"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)Demo: Cache management...$(NC)";
  step-2: run cmd=$(PYTHON) -m $(PROJECT_NAME) cache info;
}

workflow[name="demo-interactive"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)Demo: Interactive shell mode...$(NC)";
  step-2: run cmd=echo "$(YELLOW)Starting interactive shell with Polish NLP...$(NC)";
  step-3: run cmd=echo "$(YELLOW)Try these commands:$(NC)";
  step-4: run cmd=echo "  > pokaz pliki usera";
  step-5: run cmd=echo "  > znajdz pliki .log wieksze niz 10MB";
  step-6: run cmd=echo "  > uruchom usluge nginx";
  step-7: run cmd=echo "  > pokaż procesy zużywające najwięcej pamięci";
  step-8: run cmd=echo "  > exit";
  step-9: run cmd=echo "";
  step-10: run cmd=echo "$(BLUE)Press Enter to start interactive mode...$(NC)";
  step-11: run cmd=read -r;
  step-12: run cmd=$(PYTHON) -m $(PROJECT_NAME) --interactive --dsl shell;
}

workflow[name="test-examples"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)Testing all examples...$(NC)";
  step-2: run cmd=echo "$(YELLOW)Architecture examples:$(NC)";
  step-3: run cmd=PYTHONPATH=src $(PYTHON) examples/architecture/end_to_end_demo.py;
  step-4: run cmd=echo "";
  step-5: run cmd=echo "$(YELLOW)Docker examples:$(NC)";
  step-6: run cmd=PYTHONPATH=src $(PYTHON) examples/docker/basic_docker.py;
  step-7: run cmd=PYTHONPATH=src $(PYTHON) examples/docker/file_repair.py;
  step-8: run cmd=echo "";
  step-9: run cmd=echo "$(YELLOW)Kubernetes examples:$(NC)";
  step-10: run cmd=PYTHONPATH=src $(PYTHON) examples/kubernetes/basic_kubernetes.py;
  step-11: run cmd=echo "";
  step-12: run cmd=echo "$(YELLOW)Pipeline examples:$(NC)";
  step-13: run cmd=PYTHONPATH=src $(PYTHON) examples/pipelines/infrastructure_health.py;
  step-14: run cmd=PYTHONPATH=src $(PYTHON) examples/pipelines/log_analysis.py;
  step-15: run cmd=echo "";
  step-16: run cmd=echo "$(YELLOW)Shell examples:$(NC)";
  step-17: run cmd=PYTHONPATH=src $(PYTHON) examples/shell/basic_shell.py;
  step-18: run cmd=PYTHONPATH=src $(PYTHON) examples/shell/environment_analysis.py;
  step-19: run cmd=PYTHONPATH=src $(PYTHON) examples/shell/feedback_loop.py;
  step-20: run cmd=echo "";
  step-21: run cmd=echo "$(YELLOW)SQL examples:$(NC)";
  step-22: run cmd=for file in examples/sql/*.py; do \;
  step-23: run cmd=if [ -f "$$file" ]; then \;
  step-24: run cmd=echo "Running $$file..."; \;
  step-25: run cmd=PYTHONPATH=src $(PYTHON) "$$file"; \;
  step-26: run cmd=fi; \;
  step-27: run cmd=done;
  step-28: run cmd=echo "";
  step-29: run cmd=echo "$(YELLOW)Validation examples:$(NC)";
  step-30: run cmd=PYTHONPATH=src $(PYTHON) examples/validation/config_validation.py;
  step-31: run cmd=echo "";
  step-32: run cmd=echo "$(GREEN)All examples completed!$(NC)";
}

workflow[name="repl"] {
  trigger: manual;
  step-1: run cmd=$(PYTHON) -m $(PROJECT_NAME).cli;
}

workflow[name="run-example"] {
  trigger: manual;
  step-1: run cmd=$(PYTHON) examples/$(FILE);
}

workflow[name="clean"] {
  trigger: manual;
  step-1: run cmd=rm -rf build/;
  step-2: run cmd=rm -rf dist/;
  step-3: run cmd=rm -rf *.egg-info/;
  step-4: run cmd=rm -rf .pytest_cache/;
  step-5: run cmd=rm -rf .mypy_cache/;
  step-6: run cmd=rm -rf .ruff_cache/;
  step-7: run cmd=rm -rf htmlcov/;
  step-8: run cmd=rm -rf .coverage;
  step-9: run cmd=rm -rf .cache/;
  step-10: run cmd=find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true;
  step-11: run cmd=find . -type f -name "*.pyc" -delete 2>/dev/null || true;
}

workflow[name="clean-cache"] {
  trigger: manual;
  step-1: run cmd=echo "$(YELLOW)Cleaning external dependencies cache...$(NC)";
  step-2: run cmd=$(PYTHON) -m $(PROJECT_NAME) cache clear --all;
  step-3: run cmd=echo "$(GREEN)✓ Cache cleared!$(NC)";
}

workflow[name="clean-docker"] {
  trigger: manual;
  step-1: run cmd=$(DOCKER_COMPOSE) down -v --rmi local;
  step-2: run cmd=docker system prune -f;
}

workflow[name="clean-all"] {
  trigger: manual;
  step-1: depend target=clean;
  step-2: depend target=clean-docker;
  step-3: depend target=clean-cache;
}

workflow[name="build"] {
  trigger: manual;
  step-1: run cmd=$(PYTHON) -m build;
}

workflow[name="publish-test"] {
  trigger: manual;
  step-1: run cmd=echo "$(YELLOW)Creating temporary virtual environment for twine...$(NC)";
  step-2: run cmd=$(PYTHON) -m venv publish-test-env;
  step-3: run cmd=publish-test-env/bin/pip install twine;
  step-4: run cmd=publish-test-env/bin/python -m twine upload --repository testpypi dist/*;
  step-5: run cmd=rm -rf publish-test-env;
}

workflow[name="bump-patch"] {
  trigger: manual;
  step-1: run cmd=echo "$(YELLOW)Bumping patch version...$(NC)";
  step-2: run cmd=$(PYTHON) scripts/bump_version.py patch;
}

workflow[name="bump-minor"] {
  trigger: manual;
  step-1: run cmd=echo "$(YELLOW)Bumping minor version...$(NC)";
  step-2: run cmd=$(PYTHON) scripts/bump_version.py minor;
}

workflow[name="bump-major"] {
  trigger: manual;
  step-1: run cmd=echo "$(YELLOW)Bumping major version...$(NC)";
  step-2: run cmd=$(PYTHON) scripts/bump_version.py major;
}

workflow[name="publish"] {
  trigger: manual;
  step-1: run cmd=echo "$(YELLOW)Bumping patch version...$(NC)";
  step-2: run cmd=$(MAKE) bump-patch;
  step-3: run cmd=echo "$(YELLOW)Building package with new version...$(NC)";
  step-4: run cmd=$(MAKE) build;
  step-5: run cmd=echo "$(YELLOW)Publishing to PyPI...$(NC)";
  step-6: run cmd=echo "$(YELLOW)Creating temporary virtual environment for twine...$(NC)";
  step-7: run cmd=$(PYTHON) -m venv publish-env;
  step-8: run cmd=publish-env/bin/pip install twine;
  step-9: run cmd=publish-env/bin/python -m twine upload dist/*;
  step-10: run cmd=rm -rf publish-env;
}

workflow[name="push"] {
  trigger: manual;
  step-1: run cmd=echo "$(YELLOW)Starting complete release process...$(NC)";
  step-2: run cmd=echo "$(YELLOW)1. Bumping patch version...$(NC)";
  step-3: run cmd=$(MAKE) bump-patch;
  step-4: run cmd=echo "$(YELLOW)2. Building package...$(NC)";
  step-5: run cmd=$(MAKE) build;
  step-6: run cmd=echo "$(YELLOW)3. Publishing to PyPI...$(NC)";
  step-7: run cmd=echo "$(YELLOW)Creating temporary virtual environment for twine...$(NC)";
  step-8: run cmd=$(PYTHON) -m venv push-env;
  step-9: run cmd=push-env/bin/pip install twine;
  step-10: run cmd=push-env/bin/python -m twine upload dist/*;
  step-11: run cmd=rm -rf push-env;
  step-12: run cmd=echo "$(YELLOW)4. Building and pushing Docker image...$(NC)";
  step-13: run cmd=if $(MAKE) docker-push; then \;
  step-14: run cmd=echo "$(GREEN)Docker image pushed successfully!$(NC)"; \;
  step-15: run cmd=echo "$(YELLOW)5. Creating and pushing git tag...$(NC)"; \;
  step-16: run cmd=VERSION=$$($(PYTHON) -c "import toml; content = toml.load(open('pyproject.toml')); print(content['project']['version'])") && \;
  step-17: run cmd=git tag v$$VERSION && \;
  step-18: run cmd=git push origin v$$VERSION && \;
  step-19: run cmd=echo "$(GREEN)🎉 Complete release finished successfully!$(NC)"; \;
  step-20: run cmd=echo "$(GREEN)   - Package published to PyPI ✓$(NC)"; \;
  step-21: run cmd=echo "$(GREEN)   - Docker image pushed to registry ✓$(NC)"; \;
  step-22: run cmd=echo "$(GREEN)   - Git tag v$$VERSION pushed ✓$(NC)"; \;
  step-23: run cmd=echo "$(GREEN)   - Version bumped automatically ✓$(NC)"; \;
  step-24: run cmd=else \;
  step-25: run cmd=echo "$(YELLOW)⚠️  Partial release completed!$(NC)"; \;
  step-26: run cmd=echo "$(YELLOW)   - Package published to PyPI ✓$(NC)"; \;
  step-27: run cmd=echo "$(YELLOW)   - Docker push failed ✗$(NC)"; \;
  step-28: run cmd=echo "$(YELLOW)   - Version bumped automatically ✓$(NC)"; \;
  step-29: run cmd=echo "$(BLUE)To complete the Docker push and git tag later:$(NC)"; \;
  step-30: run cmd=echo "$(BLUE)  docker login && make docker-push && make git-tag$(NC)"; \;
  step-31: run cmd=fi;
}

workflow[name="git-tag"] {
  trigger: manual;
  step-1: run cmd=echo "$(YELLOW)Creating and pushing git tag...$(NC)";
  step-2: run cmd=VERSION=$$($(PYTHON) -c "import toml; content = toml.load(open('pyproject.toml')); print(content['project']['version'])") && \;
  step-3: run cmd=git tag v$$VERSION && \;
  step-4: run cmd=git push origin v$$VERSION && \;
  step-5: run cmd=echo "$(GREEN)Git tag v$$VERSION pushed successfully!$(NC)";
}

workflow[name="version"] {
  trigger: manual;
  step-1: run cmd=$(PYTHON) -c "import $(PROJECT_NAME); print($(PROJECT_NAME).__version__)";
}

workflow[name="info"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)Project:$(NC) $(PROJECT_NAME)";
  step-2: run cmd=echo "$(BLUE)Python:$(NC) $(shell $(PYTHON) --version)";
  step-3: run cmd=echo "$(BLUE)Pip:$(NC) $(shell $(PIP) --version)";
  step-4: run cmd=echo "$(BLUE)Version:$(NC) $(shell $(PYTHON) -c 'import $(PROJECT_NAME); print($(PROJECT_NAME).__version__)');
}

workflow[name="report"] {
  trigger: manual;
  step-1: depend target=benchmark;
}

workflow[name="benchmark"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)Running NLP2CMD LLM Benchmark...$(NC)";
  step-2: run cmd=echo "$(YELLOW)Testing 5 local models (≤3B) across shell, docker, sql, kubernetes, browser, git$(NC)";
  step-3: run cmd=echo "$(YELLOW)Requires: ollama running locally$(NC)";
  step-4: run cmd=PYTHONPATH=src $(PYTHON) benchmarks/llm_benchmark.py;
  step-5: run cmd=echo "";
  step-6: run cmd=echo "$(GREEN)✓ Benchmark complete!$(NC)";
  step-7: run cmd=echo "$(BLUE)Reports in benchmark_output/:$(NC)";
  step-8: run cmd=echo "  - benchmark_results.json  (detailed JSON)";
  step-9: run cmd=echo "  - benchmark_results.html  (interactive charts)";
  step-10: run cmd=echo "  - refactoring_plan.md     (refactoring recommendations)";
  step-11: run cmd=echo "  - benchmark.log           (execution log)";
  step-12: run cmd=echo "";
  step-13: run cmd=echo "$(YELLOW)Open HTML report:$(NC)";
  step-14: run cmd=echo "  xdg-open benchmark_output/benchmark_results.html";
}

workflow[name="benchmark-no-cache"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)Running NLP2CMD LLM Benchmark (NO CACHE)...$(NC)";
  step-2: run cmd=echo "$(YELLOW)Testing pure LLM performance - all cache tiers disabled$(NC)";
  step-3: run cmd=echo "$(YELLOW)This forces fresh LLM calls for every query$(NC)";
  step-4: run cmd=echo "$(YELLOW)Requires: ollama running locally$(NC)";
  step-5: run cmd=PYTHONPATH=src $(PYTHON) benchmarks/llm_benchmark.py --no-cache;
  step-6: run cmd=echo "";
  step-7: run cmd=echo "$(GREEN)✓ No-cache benchmark complete!$(NC)";
  step-8: run cmd=echo "$(BLUE)Reports in benchmark_output/:$(NC)";
  step-9: run cmd=echo "  - benchmark_results.json  (detailed JSON)";
  step-10: run cmd=echo "  - benchmark_results.html  (interactive charts)";
  step-11: run cmd=echo "";
  step-12: run cmd=echo "$(YELLOW)Open HTML report:$(NC)";
  step-13: run cmd=echo "  xdg-open benchmark_output/benchmark_results.html";
}

workflow[name="benchmark-view"] {
  trigger: manual;
  step-1: run cmd=if [ -f benchmark_output/benchmark_results.json ]; then \;
  step-2: run cmd=echo "$(BLUE)Last Benchmark Summary:$(NC)"; \;
  step-3: run cmd=cat benchmark_output/benchmark_results.json | jq '.summary'; \;
  step-4: run cmd=else \;
  step-5: run cmd=echo "$(YELLOW)No benchmark results found. Run 'make benchmark' first.$(NC)"; \;
  step-6: run cmd=fi;
}

workflow[name="benchmark-html"] {
  trigger: manual;
  step-1: run cmd=if [ -f benchmark_output/benchmark_results.html ]; then \;
  step-2: run cmd=xdg-open benchmark_output/benchmark_results.html; \;
  step-3: run cmd=else \;
  step-4: run cmd=echo "$(YELLOW)No HTML report found. Run 'make benchmark' first.$(NC)"; \;
  step-5: run cmd=fi;
}

workflow[name="benchmark-plan"] {
  trigger: manual;
  step-1: run cmd=if [ -f benchmark_output/refactoring_plan.md ]; then \;
  step-2: run cmd=cat benchmark_output/refactoring_plan.md; \;
  step-3: run cmd=else \;
  step-4: run cmd=echo "$(YELLOW)No refactoring plan found. Run 'make benchmark' first.$(NC)"; \;
  step-5: run cmd=fi;
}

workflow[name="benchmark-learn"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)Running NLP2CMD Learning Benchmark...$(NC)";
  step-2: run cmd=echo "$(YELLOW)Tests evolutionary cache: cold → warm → hot across 16 domains$(NC)";
  step-3: run cmd=PYTHONPATH=src $(PYTHON) benchmarks/learning_benchmark.py;
  step-4: run cmd=echo "";
  step-5: run cmd=echo "$(GREEN)✓ Learning benchmark complete!$(NC)";
  step-6: run cmd=echo "$(BLUE)Reports in benchmark_output/:$(NC)";
  step-7: run cmd=echo "  - learning_benchmark.json  (detailed results)";
  step-8: run cmd=echo "  - learning_benchmark.html  (interactive charts)";
  step-9: run cmd=echo "";
  step-10: run cmd=echo "$(YELLOW)Open HTML report:$(NC)";
  step-11: run cmd=echo "  xdg-open benchmark_output/learning_benchmark.html";
}

workflow[name="benchmark-clean"] {
  trigger: manual;
  step-1: run cmd=rm -rf benchmark_output/;
  step-2: run cmd=echo "$(GREEN)✓ Benchmark output cleaned!$(NC)";
}

workflow[name="scripts-maintenance"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)Maintenance Scripts:$(NC)";
  step-2: run cmd=ls -la scripts/maintenance/;
  step-3: run cmd=echo "";
  step-4: run cmd=echo "$(YELLOW)Available scripts:$(NC)";
  step-5: run cmd=for script in scripts/maintenance/*.py; do \;
  step-6: run cmd=if [ -f "$$script" ]; then \;
  step-7: run cmd=echo "  $$(basename $$script) - $$(grep '^"""' "$$script" | head -1 | sed 's/"""//g' | sed 's/^[[:space:]]*//')"; \;
  step-8: run cmd=fi; \;
  step-9: run cmd=done;
}

workflow[name="scripts-thermo"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)Thermodynamic Scripts:$(NC)";
  step-2: run cmd=ls -la scripts/thermodynamic/;
  step-3: run cmd=echo "";
  step-4: run cmd=echo "$(YELLOW)Available scripts:$(NC)";
  step-5: run cmd=for script in scripts/thermodynamic/*.py; do \;
  step-6: run cmd=if [ -f "$$script" ]; then \;
  step-7: run cmd=echo "  $$(basename $$script) - $$(grep '^"""' "$$script" | head -1 | sed 's/"""//g' | sed 's/^[[:space:]]*//')"; \;
  step-8: run cmd=fi; \;
  step-9: run cmd=done;
}

workflow[name="scripts-test"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)Testing Scripts:$(NC)";
  step-2: run cmd=ls -la scripts/testing/;
  step-3: run cmd=echo "";
  step-4: run cmd=echo "$(YELLOW)Available scripts:$(NC)";
  step-5: run cmd=for script in scripts/testing/*.py; do \;
  step-6: run cmd=if [ -f "$$script" ]; then \;
  step-7: run cmd=echo "  $$(basename $$script) - $$(grep '^"""' "$$script" | head -1 | sed 's/"""//g' | sed 's/^[[:space:]]*//')"; \;
  step-8: run cmd=fi; \;
  step-9: run cmd=done;
}

workflow[name="scripts-all"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)All Scripts Organization:$(NC)";
  step-2: run cmd=echo "";
  step-3: run cmd=$(MAKE) scripts-maintenance;
  step-4: run cmd=echo "";
  step-5: run cmd=$(MAKE) scripts-thermo;
  step-6: run cmd=echo "";
  step-7: run cmd=$(MAKE) scripts-test;
}

workflow[name="run-thermo"] {
  trigger: manual;
  step-1: run cmd=echo "$(BLUE)Running thermodynamic demo...$(NC)";
  step-2: run cmd=$(PYTHON) scripts/thermodynamic/termo_demo.py;
}

deploy {
  target: docker-compose;
  compose_file: docker-compose.yml;
}

environment[name="local"] {
  runtime: docker-compose;
  env_file: .env;
  python_version: >=3.10;
}
```

## Workflows

## Quality Pipeline (`pyqual.yaml`)

```yaml markpact:pyqual path=pyqual.yaml
pipeline:
  name: project-analysis

  # Full project analysis pipeline — replaces project.sh
  # Runs: code2llm → cleanup → code2docs → redup → vallm → prefact
  # timeout: 0 = no limit (analysis tools can take 10-30 min on large repos)
  # The custom presets below exclude generated/vendor directories and project/
  # output so the analysis finishes in a practical time on very large repos.

  custom_tools:
    - name: code2llm_scoped
      binary: code2llm
      command: >-
        code2llm {workdir} -f all -o ./project --no-chunk
        --exclude project venv .venv venv_llm node_modules src-tauri webops
        test-env fresh_env dist build target out logs backups
        networkx-3.6.1-py3-none-any
      output: ""
      allow_failure: false

    - name: vallm_scoped
      binary: vallm
      command: "vallm batch {workdir} --recursive --format toon --output ./project --exclude project,venv,.venv,venv_llm,node_modules,src-tauri,webops,test-env,fresh_env,dist,build,target,out,logs,backups,networkx-3.6.1-py3-none-any"
      output: ""
      allow_failure: false

  stages:
    - name: analyze
      tool: code2llm_scoped
      timeout: 0

    - name: cleanup
      run: rm -f project/analysis.json project/analysis.yaml
      when: always

    - name: docs
      tool: code2docs
      timeout: 0

    - name: duplicates
      tool: redup
      timeout: 0

    - name: validate
      tool: vallm_scoped
      timeout: 0

    - name: prefact
      tool: prefact
      timeout: 0

  metrics:
    cc_max: 10              # average cyclomatic complexity ≤ 10 (current: 5.7)
    vallm_pass_min: 55      # vallm pass rate ≥ 55% (current: 56.3%)
    critical_max: 400       # critical functions ≤ 400 (current: 347)

  loop:
    max_iterations: 1
    on_fail: report
```

## Dependencies

### Runtime

```text markpact:deps python
pyyaml>=6.0
pydantic>=2.0
rich>=13.0
click>=8.0
httpx>=0.25.0
jinja2>=3.0
jsonschema>=4.0
python-dotenv>=1.0
watchdog>=3.0
numpy>=1.24.0
psutil>=5.9.0
rapidfuzz>=3.0
nlp2cmd-intent>=0.1.1
```

### Development

```text markpact:deps python scope=dev
pytest>=7.0
pytest-cov>=4.0
pytest-asyncio>=0.21
pytest-xdist>=3.0
pytest-mock>=3.10
playwright>=1.40.0
black>=23.0
ruff>=0.1
mypy>=1.0
pre-commit>=3.0
mkdocs>=1.5
mkdocs-material>=9.0
goal>=2.1.0
costs>=0.1.20
pfix>=0.1.60
mkdocstrings[python]>=0.24
```

## Call Graph

*341 nodes · 500 edges · 138 modules · CC̄=4.9*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `print` *(in test_nlp2cmd_commands)* | 0 | 4996 | 0 | **4996** |
| `list` *(in src.nlp2cmd.cli.commands.examples.ExamplesRegistry)* | 4 | 151 | 2 | **153** |
| `main` *(in examples.10_online_code_editors.03_adaptive_code)* | 37 ⚠ | 0 | 133 | **133** |
| `main` *(in examples.10_online_code_editors.02_mycompiler_run)* | 32 ⚠ | 0 | 116 | **116** |
| `print_rule` *(in examples._example_helpers)* | 2 | 107 | 1 | **108** |
| `set` *(in src.nlp2cmd.executor.execution_context.ExecutionContext)* | 1 | 105 | 0 | **105** |
| `main` *(in examples.09_online_drawing._old.03_adaptive_drawing)* | 11 ⚠ | 0 | 93 | **93** |
| `main` *(in examples.05_advanced_features.schema_driven_architecture.end_to_end_demo)* | 12 ⚠ | 0 | 87 | **87** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/wronai/nlp2cmd
# generated in 0.39s
# nodes: 341 | edges: 500 | modules: 138
# CC̄=4.9

HUBS[20]:
  test_nlp2cmd_commands.print
    CC=0  in:4996  out:0  total:4996
  src.nlp2cmd.cli.commands.examples.ExamplesRegistry.list
    CC=4  in:151  out:2  total:153
  examples.10_online_code_editors.03_adaptive_code.main
    CC=37  in:0  out:133  total:133
  examples.10_online_code_editors.02_mycompiler_run.main
    CC=32  in:0  out:116  total:116
  examples._example_helpers.print_rule
    CC=2  in:107  out:1  total:108
  src.nlp2cmd.executor.execution_context.ExecutionContext.set
    CC=1  in:105  out:0  total:105
  examples.09_online_drawing._old.03_adaptive_drawing.main
    CC=11  in:0  out:93  total:93
  examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.main
    CC=12  in:0  out:87  total:87
  examples.10_online_code_editors.04_jsfiddle_frontend.main
    CC=19  in:0  out:82  total:82
  examples.01_basics.sql_basics.workflows.main
    CC=10  in:0  out:81  total:81
  examples._example_helpers.print_separator
    CC=2  in:75  out:3  total:78
  examples.show_metrics.main
    CC=15  in:0  out:77  total:77
  examples.03_integrations.toon_format.usage_example.main
    CC=9  in:0  out:77  total:77
  examples.04_domain_specific._demo_helpers.print_metrics
    CC=11  in:57  out:17  total:74
  examples.03_integrations.validation.config_validation.main
    CC=5  in:0  out:68  total:68
  examples.02_benchmarks.sequential_testing.benchmark.main
    CC=6  in:0  out:67  total:67
  examples.09_online_drawing._old.04_object_database_drawing.main
    CC=18  in:0  out:66  total:66
  examples.09_online_drawing.05_autonomous.run.run_autonomous
    CC=18  in:1  out:65  total:66
  examples.09_online_drawing.06_visual_validator.run.draw_and_validate
    CC=21  in:2  out:62  total:64
  examples.04_domain_specific._demo_helpers.run_thermo_demo
    CC=1  in:58  out:3  total:61

MODULES:
  examples.01_basics.app2schema.example  [1 funcs]
    main  CC=1  out:8
  examples.01_basics.docker_basics.01_basics_docker_nlp2cmd  [2 funcs]
    get_command_for_task  CC=1  out:1
    main  CC=1  out:12
  examples.01_basics.docker_basics.example  [1 funcs]
    main  CC=5  out:22
  examples.01_basics.docker_basics.file_repair  [4 funcs]
    create_sample_files  CC=1  out:6
    main  CC=4  out:54
    repair_file  CC=11  out:21
    validate_file  CC=6  out:11
  examples.01_basics.kubernetes_basics.example  [1 funcs]
    main  CC=7  out:27
  examples.01_basics.shell_fundamentals.01_basics_shell_nlp2cmd  [3 funcs]
    get_command_for_task  CC=1  out:1
    main  CC=2  out:13
    run_nlp2cmd_command  CC=6  out:6
  examples.01_basics.shell_fundamentals._environment_sections  [9 funcs]
    print_command_validation  CC=4  out:6
    print_config_files  CC=6  out:14
    print_export_preview  CC=6  out:15
    print_full_report  CC=3  out:6
    print_resources  CC=3  out:31
    print_section_header  CC=1  out:3
    print_service_status  CC=6  out:5
    print_system_info  CC=2  out:10
    print_tool_detection  CC=11  out:11
  examples.01_basics.shell_fundamentals.environment_analysis  [1 funcs]
    main  CC=6  out:23
  examples.01_basics.shell_fundamentals.example  [1 funcs]
    main  CC=10  out:31
  examples.01_basics.shell_fundamentals.schema_cache  [1 funcs]
    main  CC=5  out:12
  examples.01_basics.sql_basics.advanced  [1 funcs]
    main  CC=2  out:60
  examples.01_basics.sql_basics.example  [1 funcs]
    main  CC=6  out:19
  examples.01_basics.sql_basics.llm_integration  [5 funcs]
    demonstrate_hybrid_approach  CC=1  out:2
    demonstrate_mock_llm  CC=2  out:13
    demonstrate_real_llm_setup  CC=5  out:13
    demonstrate_rule_based_fallback  CC=2  out:5
    main  CC=1  out:6
  examples.01_basics.sql_basics.workflows  [2 funcs]
    main  CC=10  out:81
    print_section  CC=1  out:2
  examples.02_benchmarks.performance_testing.benchmark  [8 funcs]
    benchmark_adapters  CC=3  out:22
    generate_markdown_report  CC=4  out:10
    generate_report  CC=2  out:16
    main  CC=2  out:15
    print_report_summary  CC=4  out:30
    print_section  CC=1  out:2
    run_sequential_benchmark  CC=3  out:16
    save_report  CC=1  out:7
  examples.02_benchmarks.sequential_testing.benchmark  [2 funcs]
    main  CC=6  out:67
    print_section  CC=1  out:2
  examples.03_integrations.pipelines.infrastructure_health  [1 funcs]
    main  CC=19  out:59
  examples.03_integrations.pipelines.log_analysis  [1 funcs]
    main  CC=15  out:52
  examples.03_integrations.toon_format.01_basic_usage.demo  [1 funcs]
    main  CC=1  out:16
  examples.03_integrations.toon_format.02_command_generator.demo  [1 funcs]
    main  CC=1  out:14
  examples.03_integrations.toon_format.03_data_manager.demo  [1 funcs]
    main  CC=1  out:13
  examples.03_integrations.toon_format.04_search_and_filter.demo  [1 funcs]
    main  CC=2  out:14
  examples.03_integrations.toon_format.05_advanced_patterns.demo  [1 funcs]
    main  CC=1  out:18
  examples.03_integrations.toon_format.07_loading_performance.demo  [2 funcs]
    benchmark_old_system  CC=4  out:9
    main  CC=2  out:26
  examples.03_integrations.toon_format.08_memory_usage.demo  [2 funcs]
    estimate_old_system_memory  CC=2  out:4
    main  CC=2  out:30
  examples.03_integrations.toon_format.11_basic_integration.demo  [1 funcs]
    main  CC=1  out:17
  examples.03_integrations.toon_format.12_advanced_integration.demo  [1 funcs]
    main  CC=1  out:17
  examples.03_integrations.toon_format.13_query_system.demo  [1 funcs]
    main  CC=1  out:17
  examples.03_integrations.toon_format.14_batch_processing.demo  [2 funcs]
    batch_validate  CC=4  out:3
    main  CC=1  out:29
  examples.03_integrations.toon_format.comparison_demo  [6 funcs]
    _read_file_content  CC=2  out:4
    benchmark_performance  CC=3  out:37
    compare_data_structure  CC=1  out:34
    compare_usage_patterns  CC=1  out:30
    demonstrate_llm_friendly_format  CC=1  out:38
    main  CC=3  out:17
  examples.03_integrations.toon_format.practical_usage  [7 funcs]
    _load_toon_data  CC=2  out:4
    show_advanced_usage  CC=1  out:9
    show_basic_usage  CC=1  out:9
    show_integration_examples  CC=1  out:7
    show_performance_tips  CC=1  out:9
    show_real_world_examples  CC=1  out:9
    main  CC=2  out:18
  examples.03_integrations.toon_format.simple_demo  [6 funcs]
    demo_advanced_features  CC=1  out:7
    demo_basic_usage  CC=1  out:5
    demo_integration_example  CC=1  out:3
    demo_performance_tips  CC=1  out:7
    demo_real_world_example  CC=1  out:3
    main  CC=2  out:27
  examples.03_integrations.toon_format.usage_example  [1 funcs]
    main  CC=9  out:77
  examples.03_integrations.validation.config_validation  [3 funcs]
    main  CC=5  out:68
    print_result  CC=6  out:8
    print_section  CC=1  out:2
  examples.03_integrations.web_development.01_basic_service_config.demo  [1 funcs]
    main  CC=4  out:19
  examples.03_integrations.web_development.02_deployment_planning.demo  [2 funcs]
    summary  CC=5  out:3
    main  CC=3  out:26
  examples.03_integrations.web_development.03_docker_compose.demo  [2 funcs]
    generate_compose  CC=5  out:0
    main  CC=1  out:16
  examples.03_integrations.web_development.04_service_deployment.demo  [1 funcs]
    main  CC=3  out:19
  examples.03_integrations.web_development.05_infrastructure_management.demo  [1 funcs]
    main  CC=2  out:19
  examples.03_integrations.web_development._demo_helpers  [5 funcs]
    handle_docker_execution  CC=4  out:11
    print_batch_banner  CC=1  out:7
    print_config  CC=4  out:6
    print_containers  CC=5  out:6
    print_files_saved  CC=2  out:3
  examples.03_integrations.web_development.demo_auto  [3 funcs]
    interactive_mode  CC=12  out:30
    run_demo_with_test  CC=12  out:46
    troubleshoot_and_fix  CC=11  out:23
  examples.03_integrations.web_development.demo_batch  [6 funcs]
    _cleanup  CC=3  out:6
    _execute_command  CC=2  out:11
    _load_commands  CC=4  out:5
    _print_batch_result  CC=3  out:8
    _print_final_status  CC=5  out:8
    run_batch_demo  CC=5  out:23
  examples.03_integrations.web_development.docker_manager  [4 funcs]
    __init__  CC=1  out:3
    show_logs  CC=13  out:19
    start_services  CC=6  out:8
    stop_services  CC=3  out:4
  examples.03_integrations.web_development.nlp2_cmd_web_controller  [1 funcs]
    save_full_deployment_plan  CC=7  out:13
  examples.04_domain_specific._demo_helpers  [11 funcs]
    print_demo_header  CC=1  out:1
    print_fallback_note  CC=1  out:1
    print_full_result  CC=3  out:9
    print_metrics  CC=11  out:17
    print_projected  CC=4  out:4
    print_rule  CC=2  out:1
    print_separator  CC=2  out:3
    print_simple_result  CC=3  out:5
    project_sample  CC=10  out:9
    run_thermo_demo  CC=1  out:3
  examples.04_domain_specific.api_key_prompts  [2 funcs]
    run_all_tests  CC=12  out:18
    test_prompt  CC=15  out:15
  examples.04_domain_specific.energy.example  [5 funcs]
    demo_electric_vehicle_charging  CC=1  out:4
    demo_gas_network  CC=1  out:4
    demo_renewable_integration  CC=1  out:4
    demo_unit_commitment  CC=1  out:4
    demo_water_distribution  CC=1  out:4
  examples.04_domain_specific.polish_llm_integration.01_pdf_extraction.demo  [1 funcs]
    main  CC=2  out:22
  examples.04_domain_specific.polish_llm_integration.02_text_chunking.demo  [1 funcs]
    main  CC=3  out:29
  examples.04_domain_specific.polish_llm_integration.03_llm_search.demo  [2 funcs]
    _calculate_relevance  CC=2  out:9
    main  CC=6  out:23
  examples.04_domain_specific.polish_llm_integration.04_results_ranking.demo  [1 funcs]
    main  CC=5  out:40
  examples.04_domain_specific.polish_llm_integration.05_integration.demo  [1 funcs]
    main  CC=2  out:27
  examples.04_domain_specific.polish_llm_integration.download_bielik  [1 funcs]
    download_bielik  CC=6  out:28
  examples.04_domain_specific.polish_llm_integration.example_pdf_search  [4 funcs]
    __init__  CC=1  out:1
    __init__  CC=6  out:12
    show_configuration_guide  CC=1  out:3
    test_pdf_search_queries  CC=9  out:36
  examples.04_domain_specific.polish_llm_integration.mock_test_polish_llm  [5 funcs]
    __init__  CC=1  out:2
    process_query  CC=5  out:14
    show_real_setup_instructions  CC=1  out:3
    test_integration_pattern  CC=8  out:14
    test_polish_queries  CC=10  out:24
  examples.04_domain_specific.polish_llm_integration.setup_and_test_bielik  [7 funcs]
    check_dependencies  CC=9  out:32
    download_model  CC=7  out:19
    run_interactive_demo  CC=8  out:14
    setup_complete  CC=1  out:14
    setup_environment  CC=2  out:7
    test_integration  CC=7  out:24
    main  CC=6  out:15
  examples.04_domain_specific.run_all  [2 funcs]
    print_summary_table  CC=2  out:5
    run_all_demos  CC=5  out:27
  examples.05_advanced_features.dynamic_schemas.demo_enhanced  [1 funcs]
    main  CC=12  out:49
  examples.05_advanced_features.dynamic_schemas.demo_intelligent_nlp2cmd  [3 funcs]
    transform  CC=5  out:5
    update_command_schema  CC=6  out:8
    demo_intelligent_nlp2cmd  CC=8  out:32
  examples.05_advanced_features.dynamic_schemas.demo_persistent_storage  [2 funcs]
    demonstrate_persistent_storage  CC=11  out:48
    show_storage_benefits  CC=2  out:6
  examples.05_advanced_features.dynamic_schemas.demo_schema_flow  [4 funcs]
    demonstrate_multiple_commands  CC=4  out:15
    demonstrate_schema_flow  CC=6  out:56
    main  CC=2  out:9
    show_schema_details  CC=6  out:18
  examples.05_advanced_features.dynamic_schemas.demo_version_detection  [9 funcs]
    _demo_docker  CC=1  out:12
    _demo_kubectl  CC=1  out:11
    _demo_ps  CC=1  out:10
    _demo_python  CC=1  out:10
    _demo_tool_version  CC=4  out:9
    demonstrate_version_detection  CC=1  out:7
    main  CC=1  out:7
    show_integration_example  CC=1  out:4
    show_version_mapping  CC=2  out:13
  examples.05_advanced_features.dynamic_schemas.example  [1 funcs]
    main  CC=1  out:15
  examples.05_advanced_features.dynamic_schemas.schema_flow_demo  [4 funcs]
    main  CC=1  out:7
    show_api_usage  CC=1  out:9
    show_file_locations  CC=4  out:17
    show_schema_extraction_flow  CC=7  out:42
  examples.05_advanced_features.dynamic_schemas.simple_schema_demo  [1 funcs]
    main  CC=6  out:46
  examples.05_advanced_features.schema_driven_architecture.02_decision_router.demo  [1 funcs]
    main  CC=3  out:20
  examples.05_advanced_features.schema_driven_architecture.03_llm_planner.demo  [1 funcs]
    main  CC=4  out:25
  examples.05_advanced_features.schema_driven_architecture.04_plan_executor.demo  [1 funcs]
    main  CC=4  out:23
  examples.05_advanced_features.schema_driven_architecture.05_result_aggregator.demo  [1 funcs]
    main  CC=2  out:23
  examples.05_advanced_features.schema_driven_architecture.end_to_end_demo  [3 funcs]
    main  CC=12  out:87
    print_section  CC=1  out:2
    print_step  CC=1  out:2
  examples.05_advanced_features.schema_driven_architecture.manual_appspec  [1 funcs]
    main  CC=1  out:13
  examples.05_advanced_features.schema_driven_architecture.mvp  [1 funcs]
    main  CC=1  out:8
  examples.05_advanced_features.thermodynamic_computing.example  [7 funcs]
    example_allocation  CC=2  out:11
    example_direct_problem  CC=3  out:12
    example_energy_savings  CC=1  out:10
    example_majority_voting  CC=2  out:11
    example_routing  CC=4  out:12
    example_scheduling  CC=3  out:14
    main  CC=3  out:14
  examples.06_desktop_automation.06_env_extract.run  [1 funcs]
    main  CC=5  out:27
  examples.06_desktop_automation.07_canvas_drawing.run  [1 funcs]
    main  CC=5  out:40
  examples.06_desktop_automation.08_captcha_solver.run  [1 funcs]
    main  CC=7  out:42
  examples.06_desktop_automation.09_complex_commands.run  [1 funcs]
    main  CC=16  out:38
  examples.06_tools_and_utilities.migration_tools.demo_versioned_schemas  [4 funcs]
    demonstrate_dual_versions  CC=4  out:34
    demonstrate_schema_updates  CC=11  out:41
    main  CC=5  out:23
    migrate_existing_schemas  CC=7  out:44
  examples.06_tools_and_utilities.migration_tools.guide  [6 funcs]
    main  CC=1  out:28
    migration_steps  CC=1  out:11
    new_way_examples  CC=1  out:9
    old_way_examples  CC=1  out:9
    performance_comparison  CC=1  out:20
    practical_examples  CC=1  out:7
  examples.07_stream_protocols.example_http_api  [1 funcs]
    main  CC=3  out:21
  examples.07_stream_protocols.example_libvirt  [1 funcs]
    main  CC=3  out:30
  examples.07_stream_protocols.example_multi_stream  [1 funcs]
    main  CC=7  out:23
  examples.07_stream_protocols.example_rtsp  [1 funcs]
    main  CC=3  out:22
  examples.07_stream_protocols.example_ssh  [1 funcs]
    main  CC=3  out:14
  examples.08_api_key_management.01_diagnose_credentials.run  [1 funcs]
    main  CC=18  out:21
  examples.08_api_key_management.01_diagnose_credentials_nlp2cmd  [2 funcs]
    get_command_for_service  CC=1  out:1
    main  CC=1  out:12
  examples.08_api_key_management.02_openrouter_key.run  [3 funcs]
    check_credentials  CC=11  out:19
    main  CC=4  out:9
    run_flow  CC=7  out:18
  examples.08_api_key_management.03_github_token.run  [3 funcs]
    check  CC=8  out:14
    main  CC=2  out:8
    run_flow  CC=7  out:12
  examples.08_api_key_management.04_huggingface_token.run  [3 funcs]
    check  CC=7  out:16
    main  CC=2  out:8
    run_flow  CC=7  out:12
  examples.08_api_key_management.05_openai_key.run  [3 funcs]
    check  CC=8  out:13
    main  CC=2  out:8
    run_flow  CC=7  out:12
  examples.08_api_key_management.06_multi_provider.run  [5 funcs]
    main  CC=5  out:11
    plan_all  CC=10  out:15
    scan  CC=1  out:2
    setup_all  CC=5  out:7
    setup_providers  CC=8  out:18
  examples.08_llm_validation.benchmark_validator  [6 funcs]
    _find_changed_cases  CC=7  out:1
    _print_changed_cases  CC=5  out:2
    _print_metric_comparison  CC=5  out:2
    compare_benchmarks  CC=2  out:7
    main  CC=7  out:17
    run_benchmark  CC=28  out:43
  examples.09_online_drawing.01_draw_chat.run  [1 funcs]
    main  CC=9  out:46
  examples.09_online_drawing.02_picsart.run  [1 funcs]
    main  CC=6  out:45
  examples.09_online_drawing.03_adaptive.run  [1 funcs]
    main  CC=8  out:53
  examples.09_online_drawing.04_object_database.run  [3 funcs]
    main  CC=6  out:18
    run_scene  CC=14  out:52
    show_database  CC=3  out:19
  examples.09_online_drawing.05_autonomous.run  [2 funcs]
    fetch_only  CC=5  out:12
    run_autonomous  CC=18  out:65
  examples.09_online_drawing.06_visual_validator.run  [3 funcs]
    draw_and_validate  CC=21  out:62
    run_demo  CC=5  out:19
    validate_screenshot  CC=5  out:14
  examples.09_online_drawing.07_shape_gallery.run  [12 funcs]
    _categories_to_show  CC=3  out:4
    _print_shape_group  CC=3  out:3
    _print_shape_line  CC=1  out:2
    _shape_stats  CC=2  out:5
    analyze_image_and_draw  CC=8  out:15
    draw_on_canvas  CC=8  out:29
    generate_html_gallery  CC=4  out:13
    generate_svg  CC=4  out:6
    generate_svg_files  CC=3  out:7
    list_shapes  CC=8  out:26
  examples.09_online_drawing.08_search_demo.run  [2 funcs]
    main  CC=3  out:10
    search_demo  CC=6  out:28
  examples.09_online_drawing.09_evolutionary_orchestrator.run  [4 funcs]
    main  CC=8  out:32
    mock_example_execution  CC=5  out:13
    print_learning_report  CC=2  out:27
    run_scenario  CC=3  out:9
  examples.09_online_drawing._old.01_draw_chat_shapes  [1 funcs]
    main  CC=3  out:47
  examples.09_online_drawing._old.01_draw_chat_shapes_nlp2cmd  [2 funcs]
    main  CC=4  out:24
    run_nlp2cmd_command  CC=7  out:7
  examples.09_online_drawing._old.02_picsart_painting  [1 funcs]
    main  CC=3  out:48
  examples.09_online_drawing._old.02_picsart_painting_nlp2cmd  [3 funcs]
    get_command_for_pattern_and_color  CC=2  out:0
    main  CC=5  out:32
    run_nlp2cmd_command  CC=7  out:7
  examples.09_online_drawing._old.03_adaptive_drawing  [2 funcs]
    generate_plan_with_llm  CC=9  out:11
    main  CC=11  out:93
  examples.09_online_drawing._old.03_adaptive_drawing_nlp2cmd  [3 funcs]
    get_adaptive_command  CC=2  out:0
    main  CC=5  out:30
    run_nlp2cmd_command  CC=7  out:7
  examples.09_online_drawing._old.04_object_database_drawing  [6 funcs]
    _fetch_from_url  CC=10  out:25
    _generate_shape_via_llm  CC=11  out:15
    fetch_online_database  CC=8  out:19
    get_shape  CC=7  out:8
    main  CC=18  out:66
    run_nlp2cmd_command  CC=6  out:7
  examples.09_online_drawing._old.05_autonomous_drawing  [3 funcs]
    fetch_only  CC=5  out:12
    resolve_shapes  CC=14  out:21
    run_autonomous  CC=12  out:59
  examples.09_online_drawing._run_utils  [17 funcs]
    save  CC=8  out:11
    __aexit__  CC=8  out:8
    navigate  CC=3  out:6
    screenshot  CC=1  out:1
    _classify_page_title  CC=7  out:3
    _click_if_visible  CC=5  out:5
    _collect_discovery_urls  CC=6  out:5
    _dismiss_selector_popups  CC=3  out:2
    _dismiss_text_popups  CC=3  out:2
    _inspect_required_element  CC=7  out:5
  examples.10_online_code_editors.01_codepen_live_nlp2cmd  [2 funcs]
    get_command_for_preset  CC=1  out:1
    main  CC=1  out:13
  examples.10_online_code_editors.02_mycompiler_run  [1 funcs]
    main  CC=32  out:116
  examples.10_online_code_editors.02_mycompiler_run_nlp2cmd  [2 funcs]
    get_command_for_code  CC=1  out:1
    main  CC=1  out:15
  examples.10_online_code_editors.03_adaptive_code  [3 funcs]
    detect_task  CC=4  out:2
    generate_code_with_llm  CC=9  out:13
    main  CC=37  out:133
  examples.10_online_code_editors.03_adaptive_code_nlp2cmd  [1 funcs]
    main  CC=1  out:12
  examples.10_online_code_editors.04_jsfiddle_frontend  [1 funcs]
    main  CC=19  out:82
  examples.10_online_code_editors.04_jsfiddle_frontend_nlp2cmd  [2 funcs]
    get_command_for_preset  CC=1  out:1
    main  CC=1  out:13
  examples.10_online_code_editors.05_dynamic_executor  [2 funcs]
    build_prompt  CC=3  out:2
    main  CC=8  out:42
  examples.10_online_code_editors.05_dynamic_executor_nlp2cmd  [1 funcs]
    main  CC=1  out:12
  examples._dynamic_orchestrator  [2 funcs]
    __init__  CC=1  out:2
    execute_task  CC=4  out:13
  examples._example_helpers  [2 funcs]
    print_rule  CC=2  out:1
    print_separator  CC=2  out:3
  examples._verbose_helper  [1 funcs]
    init_verbose  CC=2  out:1
  examples.run_task  [1 funcs]
    main  CC=11  out:34
  examples.show_metrics  [1 funcs]
    main  CC=15  out:77
  jspaint_app_test4  [1 funcs]
    run  CC=2  out:6
  src.app2schema.extract  [2 funcs]
    extract_appspec_to_file  CC=27  out:44
    extract_schema_to_file  CC=20  out:34
  src.nlp2cmd.appspec_runtime  [1 funcs]
    load_appspec  CC=10  out:27
  src.nlp2cmd.automation.password_store  [1 funcs]
    get_password_store  CC=2  out:1
  src.nlp2cmd.cli.commands.examples  [1 funcs]
    list  CC=4  out:2
  src.nlp2cmd.core.toon_integration  [1 funcs]
    get_data_manager  CC=3  out:1
  src.nlp2cmd.executor.execution_context  [1 funcs]
    set  CC=1  out:0
  src.nlp2cmd.generation.thermodynamic  [1 funcs]
    create_thermodynamic_generator  CC=1  out:6
  src.nlp2cmd.llm.router  [1 funcs]
    get_router  CC=2  out:1
  src.nlp2cmd.orchestration.handlers  [1 funcs]
    register_default_handlers  CC=1  out:16
  src.nlp2cmd.orchestration.learned_path  [1 funcs]
    get_workspace  CC=1  out:5
  src.nlp2cmd.registry.get_registry  [1 funcs]
    get_registry  CC=2  out:1
  src.nlp2cmd.streams.base  [1 funcs]
    parse_source_uri  CC=7  out:9
  test_nlp2cmd_commands  [1 funcs]
    print  CC=0  out:0

EDGES:
  jspaint_app_test4.run → test_nlp2cmd_commands.print
  examples.show_metrics.main → src.nlp2cmd.orchestration.learned_path.get_workspace
  examples._dynamic_orchestrator.DynamicOrchestrator.__init__ → src.nlp2cmd.orchestration.handlers.register_default_handlers
  examples._dynamic_orchestrator.DynamicOrchestrator.execute_task → test_nlp2cmd_commands.print
  examples._example_helpers.print_separator → test_nlp2cmd_commands.print
  examples._example_helpers.print_rule → test_nlp2cmd_commands.print
  examples.run_task.main → src.nlp2cmd.orchestration.handlers.register_default_handlers
  examples.run_task.main → test_nlp2cmd_commands.print
  examples.05_advanced_features.thermodynamic_computing.example.example_scheduling → examples._example_helpers.print_separator
  examples.05_advanced_features.thermodynamic_computing.example.example_scheduling → src.nlp2cmd.generation.thermodynamic.create_thermodynamic_generator
  examples.05_advanced_features.thermodynamic_computing.example.example_scheduling → test_nlp2cmd_commands.print
  examples.05_advanced_features.thermodynamic_computing.example.example_allocation → examples._example_helpers.print_separator
  examples.05_advanced_features.thermodynamic_computing.example.example_allocation → src.nlp2cmd.generation.thermodynamic.create_thermodynamic_generator
  examples.05_advanced_features.thermodynamic_computing.example.example_allocation → test_nlp2cmd_commands.print
  examples.05_advanced_features.thermodynamic_computing.example.example_energy_savings → examples._example_helpers.print_separator
  examples.05_advanced_features.thermodynamic_computing.example.example_energy_savings → test_nlp2cmd_commands.print
  examples.05_advanced_features.thermodynamic_computing.example.example_majority_voting → examples._example_helpers.print_separator
  examples.05_advanced_features.thermodynamic_computing.example.example_majority_voting → test_nlp2cmd_commands.print
  examples.05_advanced_features.thermodynamic_computing.example.example_routing → examples._example_helpers.print_separator
  examples.05_advanced_features.thermodynamic_computing.example.example_routing → src.nlp2cmd.generation.thermodynamic.create_thermodynamic_generator
  examples.05_advanced_features.thermodynamic_computing.example.example_routing → test_nlp2cmd_commands.print
  examples.05_advanced_features.thermodynamic_computing.example.example_direct_problem → examples._example_helpers.print_separator
  examples.05_advanced_features.thermodynamic_computing.example.example_direct_problem → src.nlp2cmd.generation.thermodynamic.create_thermodynamic_generator
  examples.05_advanced_features.thermodynamic_computing.example.example_direct_problem → test_nlp2cmd_commands.print
  examples.05_advanced_features.thermodynamic_computing.example.main → examples._example_helpers.print_separator
  examples.05_advanced_features.thermodynamic_computing.example.main → test_nlp2cmd_commands.print
  examples.05_advanced_features.thermodynamic_computing.example.main → examples.05_advanced_features.thermodynamic_computing.example.example_scheduling
  examples.05_advanced_features.thermodynamic_computing.example.main → examples.05_advanced_features.thermodynamic_computing.example.example_allocation
  examples.05_advanced_features.thermodynamic_computing.example.main → examples.05_advanced_features.thermodynamic_computing.example.example_energy_savings
  examples.05_advanced_features.thermodynamic_computing.example.main → examples.05_advanced_features.thermodynamic_computing.example.example_majority_voting
  examples.05_advanced_features.thermodynamic_computing.example.main → examples.05_advanced_features.thermodynamic_computing.example.example_routing
  examples.05_advanced_features.thermodynamic_computing.example.main → examples.05_advanced_features.thermodynamic_computing.example.example_direct_problem
  examples.05_advanced_features.schema_driven_architecture.manual_appspec.main → src.nlp2cmd.appspec_runtime.load_appspec
  examples.05_advanced_features.schema_driven_architecture.manual_appspec.main → test_nlp2cmd_commands.print
  examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.print_section → examples._example_helpers.print_separator
  examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.print_section → test_nlp2cmd_commands.print
  examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.print_step → test_nlp2cmd_commands.print
  examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.print_step → examples._example_helpers.print_rule
  examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.main → examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.print_section
  examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.main → examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.print_step
  examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.main → src.nlp2cmd.registry.get_registry.get_registry
  examples.05_advanced_features.schema_driven_architecture.mvp.main → src.app2schema.extract.extract_appspec_to_file
  examples.05_advanced_features.schema_driven_architecture.mvp.main → src.nlp2cmd.appspec_runtime.load_appspec
  examples.05_advanced_features.schema_driven_architecture.mvp.main → test_nlp2cmd_commands.print
  examples.05_advanced_features.schema_driven_architecture.05_result_aggregator.demo.main → test_nlp2cmd_commands.print
  examples.05_advanced_features.schema_driven_architecture.02_decision_router.demo.main → test_nlp2cmd_commands.print
  examples.05_advanced_features.schema_driven_architecture.04_plan_executor.demo.main → test_nlp2cmd_commands.print
  examples.05_advanced_features.schema_driven_architecture.03_llm_planner.demo.main → test_nlp2cmd_commands.print
  examples.05_advanced_features.dynamic_schemas.simple_schema_demo.main → test_nlp2cmd_commands.print
  examples.05_advanced_features.dynamic_schemas.demo_intelligent_nlp2cmd.IntelligentNLP2CMD.transform → test_nlp2cmd_commands.print
```

## Refactoring Analysis

*Pre-refactoring snapshot — use this section to identify targets. Generated from `project/` toon files.*

### Call Graph & Complexity (`project/calls.toon.yaml`)

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/wronai/nlp2cmd
# generated in 0.39s
# nodes: 341 | edges: 500 | modules: 138
# CC̄=4.9

HUBS[20]:
  test_nlp2cmd_commands.print
    CC=0  in:4996  out:0  total:4996
  src.nlp2cmd.cli.commands.examples.ExamplesRegistry.list
    CC=4  in:151  out:2  total:153
  examples.10_online_code_editors.03_adaptive_code.main
    CC=37  in:0  out:133  total:133
  examples.10_online_code_editors.02_mycompiler_run.main
    CC=32  in:0  out:116  total:116
  examples._example_helpers.print_rule
    CC=2  in:107  out:1  total:108
  src.nlp2cmd.executor.execution_context.ExecutionContext.set
    CC=1  in:105  out:0  total:105
  examples.09_online_drawing._old.03_adaptive_drawing.main
    CC=11  in:0  out:93  total:93
  examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.main
    CC=12  in:0  out:87  total:87
  examples.10_online_code_editors.04_jsfiddle_frontend.main
    CC=19  in:0  out:82  total:82
  examples.01_basics.sql_basics.workflows.main
    CC=10  in:0  out:81  total:81
  examples._example_helpers.print_separator
    CC=2  in:75  out:3  total:78
  examples.show_metrics.main
    CC=15  in:0  out:77  total:77
  examples.03_integrations.toon_format.usage_example.main
    CC=9  in:0  out:77  total:77
  examples.04_domain_specific._demo_helpers.print_metrics
    CC=11  in:57  out:17  total:74
  examples.03_integrations.validation.config_validation.main
    CC=5  in:0  out:68  total:68
  examples.02_benchmarks.sequential_testing.benchmark.main
    CC=6  in:0  out:67  total:67
  examples.09_online_drawing._old.04_object_database_drawing.main
    CC=18  in:0  out:66  total:66
  examples.09_online_drawing.05_autonomous.run.run_autonomous
    CC=18  in:1  out:65  total:66
  examples.09_online_drawing.06_visual_validator.run.draw_and_validate
    CC=21  in:2  out:62  total:64
  examples.04_domain_specific._demo_helpers.run_thermo_demo
    CC=1  in:58  out:3  total:61

MODULES:
  examples.01_basics.app2schema.example  [1 funcs]
    main  CC=1  out:8
  examples.01_basics.docker_basics.01_basics_docker_nlp2cmd  [2 funcs]
    get_command_for_task  CC=1  out:1
    main  CC=1  out:12
  examples.01_basics.docker_basics.example  [1 funcs]
    main  CC=5  out:22
  examples.01_basics.docker_basics.file_repair  [4 funcs]
    create_sample_files  CC=1  out:6
    main  CC=4  out:54
    repair_file  CC=11  out:21
    validate_file  CC=6  out:11
  examples.01_basics.kubernetes_basics.example  [1 funcs]
    main  CC=7  out:27
  examples.01_basics.shell_fundamentals.01_basics_shell_nlp2cmd  [3 funcs]
    get_command_for_task  CC=1  out:1
    main  CC=2  out:13
    run_nlp2cmd_command  CC=6  out:6
  examples.01_basics.shell_fundamentals._environment_sections  [9 funcs]
    print_command_validation  CC=4  out:6
    print_config_files  CC=6  out:14
    print_export_preview  CC=6  out:15
    print_full_report  CC=3  out:6
    print_resources  CC=3  out:31
    print_section_header  CC=1  out:3
    print_service_status  CC=6  out:5
    print_system_info  CC=2  out:10
    print_tool_detection  CC=11  out:11
  examples.01_basics.shell_fundamentals.environment_analysis  [1 funcs]
    main  CC=6  out:23
  examples.01_basics.shell_fundamentals.example  [1 funcs]
    main  CC=10  out:31
  examples.01_basics.shell_fundamentals.schema_cache  [1 funcs]
    main  CC=5  out:12
  examples.01_basics.sql_basics.advanced  [1 funcs]
    main  CC=2  out:60
  examples.01_basics.sql_basics.example  [1 funcs]
    main  CC=6  out:19
  examples.01_basics.sql_basics.llm_integration  [5 funcs]
    demonstrate_hybrid_approach  CC=1  out:2
    demonstrate_mock_llm  CC=2  out:13
    demonstrate_real_llm_setup  CC=5  out:13
    demonstrate_rule_based_fallback  CC=2  out:5
    main  CC=1  out:6
  examples.01_basics.sql_basics.workflows  [2 funcs]
    main  CC=10  out:81
    print_section  CC=1  out:2
  examples.02_benchmarks.performance_testing.benchmark  [8 funcs]
    benchmark_adapters  CC=3  out:22
    generate_markdown_report  CC=4  out:10
    generate_report  CC=2  out:16
    main  CC=2  out:15
    print_report_summary  CC=4  out:30
    print_section  CC=1  out:2
    run_sequential_benchmark  CC=3  out:16
    save_report  CC=1  out:7
  examples.02_benchmarks.sequential_testing.benchmark  [2 funcs]
    main  CC=6  out:67
    print_section  CC=1  out:2
  examples.03_integrations.pipelines.infrastructure_health  [1 funcs]
    main  CC=19  out:59
  examples.03_integrations.pipelines.log_analysis  [1 funcs]
    main  CC=15  out:52
  examples.03_integrations.toon_format.01_basic_usage.demo  [1 funcs]
    main  CC=1  out:16
  examples.03_integrations.toon_format.02_command_generator.demo  [1 funcs]
    main  CC=1  out:14
  examples.03_integrations.toon_format.03_data_manager.demo  [1 funcs]
    main  CC=1  out:13
  examples.03_integrations.toon_format.04_search_and_filter.demo  [1 funcs]
    main  CC=2  out:14
  examples.03_integrations.toon_format.05_advanced_patterns.demo  [1 funcs]
    main  CC=1  out:18
  examples.03_integrations.toon_format.07_loading_performance.demo  [2 funcs]
    benchmark_old_system  CC=4  out:9
    main  CC=2  out:26
  examples.03_integrations.toon_format.08_memory_usage.demo  [2 funcs]
    estimate_old_system_memory  CC=2  out:4
    main  CC=2  out:30
  examples.03_integrations.toon_format.11_basic_integration.demo  [1 funcs]
    main  CC=1  out:17
  examples.03_integrations.toon_format.12_advanced_integration.demo  [1 funcs]
    main  CC=1  out:17
  examples.03_integrations.toon_format.13_query_system.demo  [1 funcs]
    main  CC=1  out:17
  examples.03_integrations.toon_format.14_batch_processing.demo  [2 funcs]
    batch_validate  CC=4  out:3
    main  CC=1  out:29
  examples.03_integrations.toon_format.comparison_demo  [6 funcs]
    _read_file_content  CC=2  out:4
    benchmark_performance  CC=3  out:37
    compare_data_structure  CC=1  out:34
    compare_usage_patterns  CC=1  out:30
    demonstrate_llm_friendly_format  CC=1  out:38
    main  CC=3  out:17
  examples.03_integrations.toon_format.practical_usage  [7 funcs]
    _load_toon_data  CC=2  out:4
    show_advanced_usage  CC=1  out:9
    show_basic_usage  CC=1  out:9
    show_integration_examples  CC=1  out:7
    show_performance_tips  CC=1  out:9
    show_real_world_examples  CC=1  out:9
    main  CC=2  out:18
  examples.03_integrations.toon_format.simple_demo  [6 funcs]
    demo_advanced_features  CC=1  out:7
    demo_basic_usage  CC=1  out:5
    demo_integration_example  CC=1  out:3
    demo_performance_tips  CC=1  out:7
    demo_real_world_example  CC=1  out:3
    main  CC=2  out:27
  examples.03_integrations.toon_format.usage_example  [1 funcs]
    main  CC=9  out:77
  examples.03_integrations.validation.config_validation  [3 funcs]
    main  CC=5  out:68
    print_result  CC=6  out:8
    print_section  CC=1  out:2
  examples.03_integrations.web_development.01_basic_service_config.demo  [1 funcs]
    main  CC=4  out:19
  examples.03_integrations.web_development.02_deployment_planning.demo  [2 funcs]
    summary  CC=5  out:3
    main  CC=3  out:26
  examples.03_integrations.web_development.03_docker_compose.demo  [2 funcs]
    generate_compose  CC=5  out:0
    main  CC=1  out:16
  examples.03_integrations.web_development.04_service_deployment.demo  [1 funcs]
    main  CC=3  out:19
  examples.03_integrations.web_development.05_infrastructure_management.demo  [1 funcs]
    main  CC=2  out:19
  examples.03_integrations.web_development._demo_helpers  [5 funcs]
    handle_docker_execution  CC=4  out:11
    print_batch_banner  CC=1  out:7
    print_config  CC=4  out:6
    print_containers  CC=5  out:6
    print_files_saved  CC=2  out:3
  examples.03_integrations.web_development.demo_auto  [3 funcs]
    interactive_mode  CC=12  out:30
    run_demo_with_test  CC=12  out:46
    troubleshoot_and_fix  CC=11  out:23
  examples.03_integrations.web_development.demo_batch  [6 funcs]
    _cleanup  CC=3  out:6
    _execute_command  CC=2  out:11
    _load_commands  CC=4  out:5
    _print_batch_result  CC=3  out:8
    _print_final_status  CC=5  out:8
    run_batch_demo  CC=5  out:23
  examples.03_integrations.web_development.docker_manager  [4 funcs]
    __init__  CC=1  out:3
    show_logs  CC=13  out:19
    start_services  CC=6  out:8
    stop_services  CC=3  out:4
  examples.03_integrations.web_development.nlp2_cmd_web_controller  [1 funcs]
    save_full_deployment_plan  CC=7  out:13
  examples.04_domain_specific._demo_helpers  [11 funcs]
    print_demo_header  CC=1  out:1
    print_fallback_note  CC=1  out:1
    print_full_result  CC=3  out:9
    print_metrics  CC=11  out:17
    print_projected  CC=4  out:4
    print_rule  CC=2  out:1
    print_separator  CC=2  out:3
    print_simple_result  CC=3  out:5
    project_sample  CC=10  out:9
    run_thermo_demo  CC=1  out:3
  examples.04_domain_specific.api_key_prompts  [2 funcs]
    run_all_tests  CC=12  out:18
    test_prompt  CC=15  out:15
  examples.04_domain_specific.energy.example  [5 funcs]
    demo_electric_vehicle_charging  CC=1  out:4
    demo_gas_network  CC=1  out:4
    demo_renewable_integration  CC=1  out:4
    demo_unit_commitment  CC=1  out:4
    demo_water_distribution  CC=1  out:4
  examples.04_domain_specific.polish_llm_integration.01_pdf_extraction.demo  [1 funcs]
    main  CC=2  out:22
  examples.04_domain_specific.polish_llm_integration.02_text_chunking.demo  [1 funcs]
    main  CC=3  out:29
  examples.04_domain_specific.polish_llm_integration.03_llm_search.demo  [2 funcs]
    _calculate_relevance  CC=2  out:9
    main  CC=6  out:23
  examples.04_domain_specific.polish_llm_integration.04_results_ranking.demo  [1 funcs]
    main  CC=5  out:40
  examples.04_domain_specific.polish_llm_integration.05_integration.demo  [1 funcs]
    main  CC=2  out:27
  examples.04_domain_specific.polish_llm_integration.download_bielik  [1 funcs]
    download_bielik  CC=6  out:28
  examples.04_domain_specific.polish_llm_integration.example_pdf_search  [4 funcs]
    __init__  CC=1  out:1
    __init__  CC=6  out:12
    show_configuration_guide  CC=1  out:3
    test_pdf_search_queries  CC=9  out:36
  examples.04_domain_specific.polish_llm_integration.mock_test_polish_llm  [5 funcs]
    __init__  CC=1  out:2
    process_query  CC=5  out:14
    show_real_setup_instructions  CC=1  out:3
    test_integration_pattern  CC=8  out:14
    test_polish_queries  CC=10  out:24
  examples.04_domain_specific.polish_llm_integration.setup_and_test_bielik  [7 funcs]
    check_dependencies  CC=9  out:32
    download_model  CC=7  out:19
    run_interactive_demo  CC=8  out:14
    setup_complete  CC=1  out:14
    setup_environment  CC=2  out:7
    test_integration  CC=7  out:24
    main  CC=6  out:15
  examples.04_domain_specific.run_all  [2 funcs]
    print_summary_table  CC=2  out:5
    run_all_demos  CC=5  out:27
  examples.05_advanced_features.dynamic_schemas.demo_enhanced  [1 funcs]
    main  CC=12  out:49
  examples.05_advanced_features.dynamic_schemas.demo_intelligent_nlp2cmd  [3 funcs]
    transform  CC=5  out:5
    update_command_schema  CC=6  out:8
    demo_intelligent_nlp2cmd  CC=8  out:32
  examples.05_advanced_features.dynamic_schemas.demo_persistent_storage  [2 funcs]
    demonstrate_persistent_storage  CC=11  out:48
    show_storage_benefits  CC=2  out:6
  examples.05_advanced_features.dynamic_schemas.demo_schema_flow  [4 funcs]
    demonstrate_multiple_commands  CC=4  out:15
    demonstrate_schema_flow  CC=6  out:56
    main  CC=2  out:9
    show_schema_details  CC=6  out:18
  examples.05_advanced_features.dynamic_schemas.demo_version_detection  [9 funcs]
    _demo_docker  CC=1  out:12
    _demo_kubectl  CC=1  out:11
    _demo_ps  CC=1  out:10
    _demo_python  CC=1  out:10
    _demo_tool_version  CC=4  out:9
    demonstrate_version_detection  CC=1  out:7
    main  CC=1  out:7
    show_integration_example  CC=1  out:4
    show_version_mapping  CC=2  out:13
  examples.05_advanced_features.dynamic_schemas.example  [1 funcs]
    main  CC=1  out:15
  examples.05_advanced_features.dynamic_schemas.schema_flow_demo  [4 funcs]
    main  CC=1  out:7
    show_api_usage  CC=1  out:9
    show_file_locations  CC=4  out:17
    show_schema_extraction_flow  CC=7  out:42
  examples.05_advanced_features.dynamic_schemas.simple_schema_demo  [1 funcs]
    main  CC=6  out:46
  examples.05_advanced_features.schema_driven_architecture.02_decision_router.demo  [1 funcs]
    main  CC=3  out:20
  examples.05_advanced_features.schema_driven_architecture.03_llm_planner.demo  [1 funcs]
    main  CC=4  out:25
  examples.05_advanced_features.schema_driven_architecture.04_plan_executor.demo  [1 funcs]
    main  CC=4  out:23
  examples.05_advanced_features.schema_driven_architecture.05_result_aggregator.demo  [1 funcs]
    main  CC=2  out:23
  examples.05_advanced_features.schema_driven_architecture.end_to_end_demo  [3 funcs]
    main  CC=12  out:87
    print_section  CC=1  out:2
    print_step  CC=1  out:2
  examples.05_advanced_features.schema_driven_architecture.manual_appspec  [1 funcs]
    main  CC=1  out:13
  examples.05_advanced_features.schema_driven_architecture.mvp  [1 funcs]
    main  CC=1  out:8
  examples.05_advanced_features.thermodynamic_computing.example  [7 funcs]
    example_allocation  CC=2  out:11
    example_direct_problem  CC=3  out:12
    example_energy_savings  CC=1  out:10
    example_majority_voting  CC=2  out:11
    example_routing  CC=4  out:12
    example_scheduling  CC=3  out:14
    main  CC=3  out:14
  examples.06_desktop_automation.06_env_extract.run  [1 funcs]
    main  CC=5  out:27
  examples.06_desktop_automation.07_canvas_drawing.run  [1 funcs]
    main  CC=5  out:40
  examples.06_desktop_automation.08_captcha_solver.run  [1 funcs]
    main  CC=7  out:42
  examples.06_desktop_automation.09_complex_commands.run  [1 funcs]
    main  CC=16  out:38
  examples.06_tools_and_utilities.migration_tools.demo_versioned_schemas  [4 funcs]
    demonstrate_dual_versions  CC=4  out:34
    demonstrate_schema_updates  CC=11  out:41
    main  CC=5  out:23
    migrate_existing_schemas  CC=7  out:44
  examples.06_tools_and_utilities.migration_tools.guide  [6 funcs]
    main  CC=1  out:28
    migration_steps  CC=1  out:11
    new_way_examples  CC=1  out:9
    old_way_examples  CC=1  out:9
    performance_comparison  CC=1  out:20
    practical_examples  CC=1  out:7
  examples.07_stream_protocols.example_http_api  [1 funcs]
    main  CC=3  out:21
  examples.07_stream_protocols.example_libvirt  [1 funcs]
    main  CC=3  out:30
  examples.07_stream_protocols.example_multi_stream  [1 funcs]
    main  CC=7  out:23
  examples.07_stream_protocols.example_rtsp  [1 funcs]
    main  CC=3  out:22
  examples.07_stream_protocols.example_ssh  [1 funcs]
    main  CC=3  out:14
  examples.08_api_key_management.01_diagnose_credentials.run  [1 funcs]
    main  CC=18  out:21
  examples.08_api_key_management.01_diagnose_credentials_nlp2cmd  [2 funcs]
    get_command_for_service  CC=1  out:1
    main  CC=1  out:12
  examples.08_api_key_management.02_openrouter_key.run  [3 funcs]
    check_credentials  CC=11  out:19
    main  CC=4  out:9
    run_flow  CC=7  out:18
  examples.08_api_key_management.03_github_token.run  [3 funcs]
    check  CC=8  out:14
    main  CC=2  out:8
    run_flow  CC=7  out:12
  examples.08_api_key_management.04_huggingface_token.run  [3 funcs]
    check  CC=7  out:16
    main  CC=2  out:8
    run_flow  CC=7  out:12
  examples.08_api_key_management.05_openai_key.run  [3 funcs]
    check  CC=8  out:13
    main  CC=2  out:8
    run_flow  CC=7  out:12
  examples.08_api_key_management.06_multi_provider.run  [5 funcs]
    main  CC=5  out:11
    plan_all  CC=10  out:15
    scan  CC=1  out:2
    setup_all  CC=5  out:7
    setup_providers  CC=8  out:18
  examples.08_llm_validation.benchmark_validator  [6 funcs]
    _find_changed_cases  CC=7  out:1
    _print_changed_cases  CC=5  out:2
    _print_metric_comparison  CC=5  out:2
    compare_benchmarks  CC=2  out:7
    main  CC=7  out:17
    run_benchmark  CC=28  out:43
  examples.09_online_drawing.01_draw_chat.run  [1 funcs]
    main  CC=9  out:46
  examples.09_online_drawing.02_picsart.run  [1 funcs]
    main  CC=6  out:45
  examples.09_online_drawing.03_adaptive.run  [1 funcs]
    main  CC=8  out:53
  examples.09_online_drawing.04_object_database.run  [3 funcs]
    main  CC=6  out:18
    run_scene  CC=14  out:52
    show_database  CC=3  out:19
  examples.09_online_drawing.05_autonomous.run  [2 funcs]
    fetch_only  CC=5  out:12
    run_autonomous  CC=18  out:65
  examples.09_online_drawing.06_visual_validator.run  [3 funcs]
    draw_and_validate  CC=21  out:62
    run_demo  CC=5  out:19
    validate_screenshot  CC=5  out:14
  examples.09_online_drawing.07_shape_gallery.run  [12 funcs]
    _categories_to_show  CC=3  out:4
    _print_shape_group  CC=3  out:3
    _print_shape_line  CC=1  out:2
    _shape_stats  CC=2  out:5
    analyze_image_and_draw  CC=8  out:15
    draw_on_canvas  CC=8  out:29
    generate_html_gallery  CC=4  out:13
    generate_svg  CC=4  out:6
    generate_svg_files  CC=3  out:7
    list_shapes  CC=8  out:26
  examples.09_online_drawing.08_search_demo.run  [2 funcs]
    main  CC=3  out:10
    search_demo  CC=6  out:28
  examples.09_online_drawing.09_evolutionary_orchestrator.run  [4 funcs]
    main  CC=8  out:32
    mock_example_execution  CC=5  out:13
    print_learning_report  CC=2  out:27
    run_scenario  CC=3  out:9
  examples.09_online_drawing._old.01_draw_chat_shapes  [1 funcs]
    main  CC=3  out:47
  examples.09_online_drawing._old.01_draw_chat_shapes_nlp2cmd  [2 funcs]
    main  CC=4  out:24
    run_nlp2cmd_command  CC=7  out:7
  examples.09_online_drawing._old.02_picsart_painting  [1 funcs]
    main  CC=3  out:48
  examples.09_online_drawing._old.02_picsart_painting_nlp2cmd  [3 funcs]
    get_command_for_pattern_and_color  CC=2  out:0
    main  CC=5  out:32
    run_nlp2cmd_command  CC=7  out:7
  examples.09_online_drawing._old.03_adaptive_drawing  [2 funcs]
    generate_plan_with_llm  CC=9  out:11
    main  CC=11  out:93
  examples.09_online_drawing._old.03_adaptive_drawing_nlp2cmd  [3 funcs]
    get_adaptive_command  CC=2  out:0
    main  CC=5  out:30
    run_nlp2cmd_command  CC=7  out:7
  examples.09_online_drawing._old.04_object_database_drawing  [6 funcs]
    _fetch_from_url  CC=10  out:25
    _generate_shape_via_llm  CC=11  out:15
    fetch_online_database  CC=8  out:19
    get_shape  CC=7  out:8
    main  CC=18  out:66
    run_nlp2cmd_command  CC=6  out:7
  examples.09_online_drawing._old.05_autonomous_drawing  [3 funcs]
    fetch_only  CC=5  out:12
    resolve_shapes  CC=14  out:21
    run_autonomous  CC=12  out:59
  examples.09_online_drawing._run_utils  [17 funcs]
    save  CC=8  out:11
    __aexit__  CC=8  out:8
    navigate  CC=3  out:6
    screenshot  CC=1  out:1
    _classify_page_title  CC=7  out:3
    _click_if_visible  CC=5  out:5
    _collect_discovery_urls  CC=6  out:5
    _dismiss_selector_popups  CC=3  out:2
    _dismiss_text_popups  CC=3  out:2
    _inspect_required_element  CC=7  out:5
  examples.10_online_code_editors.01_codepen_live_nlp2cmd  [2 funcs]
    get_command_for_preset  CC=1  out:1
    main  CC=1  out:13
  examples.10_online_code_editors.02_mycompiler_run  [1 funcs]
    main  CC=32  out:116
  examples.10_online_code_editors.02_mycompiler_run_nlp2cmd  [2 funcs]
    get_command_for_code  CC=1  out:1
    main  CC=1  out:15
  examples.10_online_code_editors.03_adaptive_code  [3 funcs]
    detect_task  CC=4  out:2
    generate_code_with_llm  CC=9  out:13
    main  CC=37  out:133
  examples.10_online_code_editors.03_adaptive_code_nlp2cmd  [1 funcs]
    main  CC=1  out:12
  examples.10_online_code_editors.04_jsfiddle_frontend  [1 funcs]
    main  CC=19  out:82
  examples.10_online_code_editors.04_jsfiddle_frontend_nlp2cmd  [2 funcs]
    get_command_for_preset  CC=1  out:1
    main  CC=1  out:13
  examples.10_online_code_editors.05_dynamic_executor  [2 funcs]
    build_prompt  CC=3  out:2
    main  CC=8  out:42
  examples.10_online_code_editors.05_dynamic_executor_nlp2cmd  [1 funcs]
    main  CC=1  out:12
  examples._dynamic_orchestrator  [2 funcs]
    __init__  CC=1  out:2
    execute_task  CC=4  out:13
  examples._example_helpers  [2 funcs]
    print_rule  CC=2  out:1
    print_separator  CC=2  out:3
  examples._verbose_helper  [1 funcs]
    init_verbose  CC=2  out:1
  examples.run_task  [1 funcs]
    main  CC=11  out:34
  examples.show_metrics  [1 funcs]
    main  CC=15  out:77
  jspaint_app_test4  [1 funcs]
    run  CC=2  out:6
  src.app2schema.extract  [2 funcs]
    extract_appspec_to_file  CC=27  out:44
    extract_schema_to_file  CC=20  out:34
  src.nlp2cmd.appspec_runtime  [1 funcs]
    load_appspec  CC=10  out:27
  src.nlp2cmd.automation.password_store  [1 funcs]
    get_password_store  CC=2  out:1
  src.nlp2cmd.cli.commands.examples  [1 funcs]
    list  CC=4  out:2
  src.nlp2cmd.core.toon_integration  [1 funcs]
    get_data_manager  CC=3  out:1
  src.nlp2cmd.executor.execution_context  [1 funcs]
    set  CC=1  out:0
  src.nlp2cmd.generation.thermodynamic  [1 funcs]
    create_thermodynamic_generator  CC=1  out:6
  src.nlp2cmd.llm.router  [1 funcs]
    get_router  CC=2  out:1
  src.nlp2cmd.orchestration.handlers  [1 funcs]
    register_default_handlers  CC=1  out:16
  src.nlp2cmd.orchestration.learned_path  [1 funcs]
    get_workspace  CC=1  out:5
  src.nlp2cmd.registry.get_registry  [1 funcs]
    get_registry  CC=2  out:1
  src.nlp2cmd.streams.base  [1 funcs]
    parse_source_uri  CC=7  out:9
  test_nlp2cmd_commands  [1 funcs]
    print  CC=0  out:0

EDGES:
  jspaint_app_test4.run → test_nlp2cmd_commands.print
  examples.show_metrics.main → src.nlp2cmd.orchestration.learned_path.get_workspace
  examples._dynamic_orchestrator.DynamicOrchestrator.__init__ → src.nlp2cmd.orchestration.handlers.register_default_handlers
  examples._dynamic_orchestrator.DynamicOrchestrator.execute_task → test_nlp2cmd_commands.print
  examples._example_helpers.print_separator → test_nlp2cmd_commands.print
  examples._example_helpers.print_rule → test_nlp2cmd_commands.print
  examples.run_task.main → src.nlp2cmd.orchestration.handlers.register_default_handlers
  examples.run_task.main → test_nlp2cmd_commands.print
  examples.05_advanced_features.thermodynamic_computing.example.example_scheduling → examples._example_helpers.print_separator
  examples.05_advanced_features.thermodynamic_computing.example.example_scheduling → src.nlp2cmd.generation.thermodynamic.create_thermodynamic_generator
  examples.05_advanced_features.thermodynamic_computing.example.example_scheduling → test_nlp2cmd_commands.print
  examples.05_advanced_features.thermodynamic_computing.example.example_allocation → examples._example_helpers.print_separator
  examples.05_advanced_features.thermodynamic_computing.example.example_allocation → src.nlp2cmd.generation.thermodynamic.create_thermodynamic_generator
  examples.05_advanced_features.thermodynamic_computing.example.example_allocation → test_nlp2cmd_commands.print
  examples.05_advanced_features.thermodynamic_computing.example.example_energy_savings → examples._example_helpers.print_separator
  examples.05_advanced_features.thermodynamic_computing.example.example_energy_savings → test_nlp2cmd_commands.print
  examples.05_advanced_features.thermodynamic_computing.example.example_majority_voting → examples._example_helpers.print_separator
  examples.05_advanced_features.thermodynamic_computing.example.example_majority_voting → test_nlp2cmd_commands.print
  examples.05_advanced_features.thermodynamic_computing.example.example_routing → examples._example_helpers.print_separator
  examples.05_advanced_features.thermodynamic_computing.example.example_routing → src.nlp2cmd.generation.thermodynamic.create_thermodynamic_generator
  examples.05_advanced_features.thermodynamic_computing.example.example_routing → test_nlp2cmd_commands.print
  examples.05_advanced_features.thermodynamic_computing.example.example_direct_problem → examples._example_helpers.print_separator
  examples.05_advanced_features.thermodynamic_computing.example.example_direct_problem → src.nlp2cmd.generation.thermodynamic.create_thermodynamic_generator
  examples.05_advanced_features.thermodynamic_computing.example.example_direct_problem → test_nlp2cmd_commands.print
  examples.05_advanced_features.thermodynamic_computing.example.main → examples._example_helpers.print_separator
  examples.05_advanced_features.thermodynamic_computing.example.main → test_nlp2cmd_commands.print
  examples.05_advanced_features.thermodynamic_computing.example.main → examples.05_advanced_features.thermodynamic_computing.example.example_scheduling
  examples.05_advanced_features.thermodynamic_computing.example.main → examples.05_advanced_features.thermodynamic_computing.example.example_allocation
  examples.05_advanced_features.thermodynamic_computing.example.main → examples.05_advanced_features.thermodynamic_computing.example.example_energy_savings
  examples.05_advanced_features.thermodynamic_computing.example.main → examples.05_advanced_features.thermodynamic_computing.example.example_majority_voting
  examples.05_advanced_features.thermodynamic_computing.example.main → examples.05_advanced_features.thermodynamic_computing.example.example_routing
  examples.05_advanced_features.thermodynamic_computing.example.main → examples.05_advanced_features.thermodynamic_computing.example.example_direct_problem
  examples.05_advanced_features.schema_driven_architecture.manual_appspec.main → src.nlp2cmd.appspec_runtime.load_appspec
  examples.05_advanced_features.schema_driven_architecture.manual_appspec.main → test_nlp2cmd_commands.print
  examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.print_section → examples._example_helpers.print_separator
  examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.print_section → test_nlp2cmd_commands.print
  examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.print_step → test_nlp2cmd_commands.print
  examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.print_step → examples._example_helpers.print_rule
  examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.main → examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.print_section
  examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.main → examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.print_step
  examples.05_advanced_features.schema_driven_architecture.end_to_end_demo.main → src.nlp2cmd.registry.get_registry.get_registry
  examples.05_advanced_features.schema_driven_architecture.mvp.main → src.app2schema.extract.extract_appspec_to_file
  examples.05_advanced_features.schema_driven_architecture.mvp.main → src.nlp2cmd.appspec_runtime.load_appspec
  examples.05_advanced_features.schema_driven_architecture.mvp.main → test_nlp2cmd_commands.print
  examples.05_advanced_features.schema_driven_architecture.05_result_aggregator.demo.main → test_nlp2cmd_commands.print
  examples.05_advanced_features.schema_driven_architecture.02_decision_router.demo.main → test_nlp2cmd_commands.print
  examples.05_advanced_features.schema_driven_architecture.04_plan_executor.demo.main → test_nlp2cmd_commands.print
  examples.05_advanced_features.schema_driven_architecture.03_llm_planner.demo.main → test_nlp2cmd_commands.print
  examples.05_advanced_features.dynamic_schemas.simple_schema_demo.main → test_nlp2cmd_commands.print
  examples.05_advanced_features.dynamic_schemas.demo_intelligent_nlp2cmd.IntelligentNLP2CMD.transform → test_nlp2cmd_commands.print
```

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 1043f 1790686L | python:762,json:158,shell:76,yaml:26,txt:12,yml:3,ini:1,toml:1 | 2026-06-06
# generated in 0.78s
# CC̅=4.9 | critical:217/4083 | dups:0 | cycles:0

HEALTH[20]:
  🟡 CC    main CC=15 (limit:15)
  🟡 CC    main CC=18 (limit:15)
  🟡 CC    to_compose CC=17 (limit:15)
  🟡 CC    _detect_intent CC=19 (limit:15)
  🟡 CC    _extract_entities CC=16 (limit:15)
  🟡 CC    main CC=19 (limit:15)
  🟡 CC    main CC=15 (limit:15)
  🟡 CC    run_autonomous CC=18 (limit:15)
  🟡 CC    main CC=18 (limit:15)
  🟡 CC    draw_and_validate CC=21 (limit:15)
  🟡 CC    main CC=16 (limit:15)
  🟡 CC    main CC=32 (limit:15)
  🟡 CC    main CC=19 (limit:15)
  🟡 CC    main CC=37 (limit:15)
  🟡 CC    main CC=21 (limit:15)
  🟡 CC    run_benchmark CC=28 (limit:15)
  🟡 CC    test_prompt CC=15 (limit:15)
  🟡 CC    _get_command_for_query CC=15 (limit:15)
  🟡 CC    run_learning_benchmark CC=15 (limit:15)
  🟡 CC    _select_action CC=41 (limit:15)

REFACTOR[1]:
  1. split 20 high-CC methods  (CC>15)

PIPELINES[2962]:
  [1] Src [run]: run → print
      PURITY: 100% pure
  [2] Src [main]: main → get_workspace
      PURITY: 100% pure
  [3] Src [__init__]: __init__ → register_default_handlers
      PURITY: 100% pure
  [4] Src [execute_task]: execute_task → print
      PURITY: 100% pure
  [5] Src [main]: main → register_default_handlers
      PURITY: 100% pure
  [6] Src [main]: main → print_separator → print
      PURITY: 100% pure
  [7] Src [main]: main → load_appspec
      PURITY: 100% pure
  [8] Src [mock_sql_select]: mock_sql_select
      PURITY: 100% pure
  [9] Src [mock_shell_count_pattern]: mock_shell_count_pattern
      PURITY: 100% pure
  [10] Src [mock_k8s_get]: mock_k8s_get
      PURITY: 100% pure
  [11] Src [main]: main → print_section → print_separator → print
      PURITY: 100% pure
  [12] Src [main]: main → extract_appspec_to_file → extract_schema → _extract_web_dom_schema → ...(1 more)
      PURITY: 100% pure
  [13] Src [aggregate]: aggregate
      PURITY: 100% pure
  [14] Src [_to_json]: _to_json
      PURITY: 100% pure
  [15] Src [_to_yaml]: _to_yaml
      PURITY: 100% pure
  [16] Src [_to_table]: _to_table
      PURITY: 100% pure
  [17] Src [_to_markdown]: _to_markdown
      PURITY: 100% pure
  [18] Src [main]: main → print
      PURITY: 100% pure
  [19] Src [route]: route
      PURITY: 100% pure
  [20] Src [main]: main → print
      PURITY: 100% pure
  [21] Src [_mock_execute]: _mock_execute
      PURITY: 100% pure
  [22] Src [execute_step]: execute_step
      PURITY: 100% pure
  [23] Src [execute_plan]: execute_plan
      PURITY: 100% pure
  [24] Src [main]: main → print
      PURITY: 100% pure
  [25] Src [generate_plan]: generate_plan
      PURITY: 100% pure
  [26] Src [main]: main → print
      PURITY: 100% pure
  [27] Src [main]: main → print
      PURITY: 100% pure
  [28] Src [__init__]: __init__
      PURITY: 100% pure
  [29] Src [transform]: transform → print
      PURITY: 100% pure
  [30] Src [detect_and_adapt]: detect_and_adapt
      PURITY: 100% pure
  [31] Src [_select_best_version]: _select_best_version
      PURITY: 100% pure
  [32] Src [_needs_update]: _needs_update
      PURITY: 100% pure
  [33] Src [update_command_schema]: update_command_schema → print
      PURITY: 100% pure
  [34] Src [_increment_version]: _increment_version
      PURITY: 100% pure
  [35] Src [clear_cache]: clear_cache
      PURITY: 100% pure
  [36] Src [demo_intelligent_nlp2cmd]: demo_intelligent_nlp2cmd → print
      PURITY: 100% pure
  [37] Src [demonstrate_persistent_storage]: demonstrate_persistent_storage → print
      PURITY: 100% pure
  [38] Src [show_storage_benefits]: show_storage_benefits → print
      PURITY: 100% pure
  [39] Src [main]: main → print
      PURITY: 100% pure
  [40] Src [main]: main → demonstrate_schema_flow → print
      PURITY: 100% pure
  [41] Src [main]: main → demonstrate_version_detection → print
      PURITY: 100% pure
  [42] Src [main]: main → show_schema_extraction_flow → print
      PURITY: 100% pure
  [43] Src [main]: main → extract_appspec_to_file → extract_schema → _extract_web_dom_schema → ...(1 more)
      PURITY: 100% pure
  [44] Src [main]: main → get_command_for_service
      PURITY: 100% pure
  [45] Src [main]: main → check → get_password_store
      PURITY: 100% pure
  [46] Src [main]: main → get_password_store
      PURITY: 100% pure
  [47] Src [main]: main → scan → get_password_store
      PURITY: 100% pure
  [48] Src [main]: main → check_credentials → get_password_store
      PURITY: 100% pure
  [49] Src [main]: main → check → get_password_store
      PURITY: 100% pure
  [50] Src [main]: main → check → get_password_store
      PURITY: 100% pure

LAYERS:
  tools/                          CC̄=7.0    ←in:0  →out:0
  │ !! comprehensive_command_scanner   853L  3C   24m  CC=17     ←0
  │ !! enhanced_schema_generator   811L  3C   37m  CC=11     ←0
  │ !! non_llm_schema_extractor   724L  3C   28m  CC=11     ←0
  │ !! generate_cmd_simple        578L  0C    4m  CC=187    ←0
  │ !! intelligent_command_generator   523L  3C   18m  CC=7      ←0
  │ !! generate_cmd_from_prompts   521L  1C    5m  CC=144    ←0
  │ !! intelligent_schema_generator   473L  2C   14m  CC=17     ←0
  │ analyze_version_detection   334L  0C    6m  CC=9      ←0
  │ cmd2schema                 244L  1C    9m  CC=7      ←0
  │ !! update_schemas             176L  0C    3m  CC=16     ←0
  │ validate_schemas           123L  0C    1m  CC=14     ←0
  │ !! compare_batches             95L  0C    1m  CC=21     ←0
  │ !! compare_llm                 85L  0C    1m  CC=16     ←0
  │ quick_test_nlp2cmd          70L  0C    1m  CC=7      ←0
  │
  benchmarks/                     CC̄=5.4    ←in:0  →out:85  !! split
  │ !! llm_benchmark             1265L  2C   29m  CC=14     ←0
  │ !! learning_benchmark         593L  0C    6m  CC=15     ←0
  │ thermodynamic_benchmark    395L  1C    7m  CC=9      ←0
  │
  src/                            CC̄=5.2    ←in:0  →out:0
  │ !! phrase_database.json     772539L  0C    0m  CC=0.0    ←0
  │ !! patterns.json             2016L  0C    0m  CC=0.0    ←0
  │ !! site_explorer             1716L  3C   34m  CC=72     ←1
  │ !! pipeline_runner_browser   1692L  1C    3m  CC=280    ←0
  │ !! command_detector.json     1630L  0C    0m  CC=0.0    ←0
  │ !! doctor                    1388L  3C   23m  CC=56     ←3
  │ !! template_generator        1238L  2C   98m  CC=34     ←0
  │ !! action_planner            1226L  3C   23m  CC=12     ←0
  │ !! pipeline_runner_plans     1202L  1C   13m  CC=168    ←0
  │ !! schema_fallback           1169L  3C   17m  CC=48     ←0
  │ !! evolutionary_cache        1048L  3C   24m  CC=23     ←1
  │ !! router                     951L  3C   22m  CC=17     ←7
  │ !! extract                    942L  2C   15m  CC=45     ←9
  │ !! intract-bindings.json      931L  0C    0m  CC=0.0    ←0
  │ !! run                        919L  0C    4m  CC=183    ←0
  │ !! generate                   910L  0C    4m  CC=64     ←1
  │ !! __init__                   909L  2C   43m  CC=26     ←0
  │ !! regex                      908L  3C   12m  CC=38     ←0
  │ !! templates.json             855L  0C    0m  CC=0.0    ←0
  │ !! main                       843L  0C   11m  CC=71     ←0
  │ !! drawing_blueprints         826L  1C   20m  CC=3      ←2
  │ !! runner                     826L  3C   10m  CC=54     ←0
  │ !! form_data_loader           823L  1C   47m  CC=18     ←0
  │ !! form_handler               787L  3C    9m  CC=37     ←0
  │ !! semantic_matcher_optimized   750L  3C   30m  CC=12     ←0
  │ !! kubernetes                 731L  3C   23m  CC=12     ←0
  │ !! handlers                   714L  0C   19m  CC=18     ←2
  │ !! validator                  692L  2C   13m  CC=43     ←0
  │ !! dynamic                    650L  2C   21m  CC=25     ←0
  │ !! desktop                    649L  3C   21m  CC=31     ←0
  │ !! plan_executor              645L  1C   18m  CC=34     ←0
  │ !! examples                   641L  3C   13m  CC=13     ←75
  │ !! docker                     635L  3C   19m  CC=14     ←0
  │ !! ml_intent_classifier       615L  3C   14m  CC=11     ←1
  │ !! step_orchestrator          615L  2C   12m  CC=16     ←0
  │ !! browser                    595L  2C   26m  CC=40     ←0
  │ !! auto_repair                580L  3C   12m  CC=22     ←1
  │ !! enhanced_context           570L  2C   14m  CC=22     ←0
  │ !! core_transform             569L  1C   22m  CC=19     ←0
  │ !! multilingual_phrases.json   545L  0C    0m  CC=0.0    ←0
  │ !! pipeline                   543L  1C   15m  CC=54     ←0
  │ !! interactive                536L  1C    9m  CC=24     ←0
  │ !! vector_store               534L  2C   15m  CC=8      ←1
  │ !! captcha_solver             528L  2C   10m  CC=12     ←0
  │ !! complex_planner            524L  3C   10m  CC=24     ←18
  │ !! browser                    522L  2C   15m  CC=13     ←1
  │ !! __init__                   509L  2C   14m  CC=12     ←0
  │ !! orchestrator               507L  1C   11m  CC=19     ←0
  │ !! thermodynamic_generator    506L  1C   10m  CC=24     ←0
  │ resource_discovery         489L  3C   10m  CC=11     ←3
  │ !! environment_analyzer       486L  1C   15m  CC=15     ←0
  │ !! sql                        478L  3C   15m  CC=15     ←1
  │ firefox_sessions           472L  1C   11m  CC=14     ←0
  │ canvas_execution           461L  1C   20m  CC=8      ←0
  │ draw_navigation_skill      457L  1C   15m  CC=12     ←0
  │ shell                      455L  3C   18m  CC=8      ←0
  │ !! feedback_analyzer          454L  1C   11m  CC=41     ←0
  │ engine                     453L  3C   20m  CC=14     ←0
  │ fuzzy_schema_matcher_class   449L  1C   21m  CC=9      ←0
  │ !! train_model                444L  0C    7m  CC=29     ←0
  │ !! llm_extractor              443L  1C   11m  CC=15     ←0
  │ env_extractor              439L  2C   11m  CC=13     ←0
  │ !! thermodynamic_components   438L  4C   11m  CC=38     ←0
  │ action_registry            437L  1C   12m  CC=5      ←0
  │ !! pipeline_runner_desktop    435L  1C    8m  CC=44     ←0
  │ canvas_adapter             434L  1C   13m  CC=10     ←0
  │ !! dql                        431L  3C   13m  CC=22     ←0
  │ intents.yaml               424L  0C    0m  CC=0.0    ←0
  │ program                    423L  12C   32m  CC=5      ←0
  │ !! adaptive_learner_class     422L  1C   14m  CC=31     ←0
  │ versioned_store            421L  1C   13m  CC=14     ←0
  │ llm_simple                 420L  10C   19m  CC=13     ←0
  │ !! python_extractors          420L  2C   11m  CC=30     ←0
  │ __init__                   419L  3C    7m  CC=6      ←0
  │ !! toon_parser                418L  3C   22m  CC=28     ←2
  │ !! command_detector           415L  2C    5m  CC=31     ←0
  │ repair                     413L  2C    7m  CC=13     ←0
  │ __init__                   410L  4C   11m  CC=8      ←1
  │ !! session                    405L  3C   10m  CC=30     ←0
  │ normalizer                 400L  2C   13m  CC=6      ←0
  │ cache                      400L  0C    9m  CC=9      ←0
  │ !! extractors                 400L  5C   10m  CC=16     ←0
  │ visual_validator           399L  4C    8m  CC=12     ←0
  │ !! planner                    397L  1C   17m  CC=18     ←0
  │ !! companies                  396L  1C    8m  CC=21     ←1
  │ per_command_store          395L  1C   14m  CC=7      ←0
  │ service_configs            394L  0C    2m  CC=6      ←0
  │ !! draw_validation_skill      394L  1C   11m  CC=21     ←1
  │ !! extractor                  389L  3C   10m  CC=15     ←1
  │ plan_executor              389L  1C    9m  CC=14     ←1
  │ __init__                   383L  3C   11m  CC=14     ←0
  │ hybrid                     381L  4C   12m  CC=7      ←2
  │ !! __init__                   377L  4C   11m  CC=34     ←0
  │ expanded_phrases.json      373L  0C    0m  CC=0.0    ←0
  │ structured                 371L  5C    7m  CC=9      ←0
  │ step_validator             370L  3C   18m  CC=11     ←0
  │ data_loader                370L  3C   28m  CC=5      ←2
  │ draw_object                370L  4C   11m  CC=12     ←0
  │ !! extraction                 370L  8C   10m  CC=24     ←0
  │ !! text_to_shape              370L  3C    9m  CC=24     ←0
  │ !! semantic_shell             369L  2C   14m  CC=32     ←0
  │ mouse_controller           358L  2C   23m  CC=5      ←0
  │ correction_engine_class    357L  1C    7m  CC=14     ←0
  │ !! data_tree                  355L  3C   12m  CC=16     ←0
  │ rtsp_stream                354L  1C   17m  CC=13     ←0
  │ !! version_aware_generator    353L  1C   11m  CC=17     ←0
  │ history                    349L  2C   15m  CC=12     ←0
  │ auto_repair                341L  1C   12m  CC=6      ←1
  │ !! reflection                 338L  3C    9m  CC=29     ←1
  │ !! session_password_store     337L  1C    7m  CC=36     ←0
  │ service                    337L  3C   11m  CC=9      ←0
  │ !! feedback_loop_class        336L  1C    6m  CC=21     ←0
  │ browser_config             331L  2C   23m  CC=14     ←0
  │ tracker                    325L  3C   18m  CC=13     ←3
  │ !! shell_generators           321L  8C   11m  CC=23     ←0
  │ !! polish_support             318L  1C   13m  CC=20     ←1
  │ !! external_cache             316L  1C   13m  CC=16     ←0
  │ registry                   309L  2C   20m  CC=9      ←0
  │ !! core_backends              308L  4C   12m  CC=19     ←0
  │ disk                       308L  2C   14m  CC=12     ←0
  │ helpers                    307L  0C   10m  CC=13     ←1
  │ !! interaction                299L  10C   10m  CC=19     ←0
  │ validating                 297L  8C    9m  CC=9      ←0
  │ skill                      290L  1C   18m  CC=11     ←0
  │ openrouter                 289L  2C    8m  CC=5      ←0
  │ entity_resolver            288L  2C   17m  CC=7      ←0
  │ vision                     281L  2C    9m  CC=4      ←0
  │ playwright_installer       281L  0C    6m  CC=10     ←3
  │ !! script_extractors          279L  2C    6m  CC=30     ←0
  │ !! schema_driven              276L  2C    8m  CC=41     ←0
  │ step_gate                  271L  1C   11m  CC=14     ←0
  │ !! dynamic_generator          269L  1C    6m  CC=15     ←0
  │ !! firefox_password_reader    267L  1C    6m  CC=16     ←0
  │ llm_multi                  267L  5C   10m  CC=6      ←0
  │ history                    267L  0C    6m  CC=9      ←0
  │ commands                   267L  8C   19m  CC=7      ←1
  │ generator                  265L  2C   15m  CC=12     ←0
  │ token_costs                260L  2C   10m  CC=12     ←2
  │ !! checker                    257L  2C    9m  CC=36     ←1
  │ !! docker_validator           255L  1C    5m  CC=50     ←0
  │ forms                      252L  1C    8m  CC=6      ←0
  │ web_schema                 249L  0C    5m  CC=14     ←0
  │ metrics_collector          249L  1C   10m  CC=6      ←0
  │ execution_record           248L  1C   11m  CC=9      ←2
  │ scheduling_energy          247L  1C    8m  CC=8      ←0
  │ core_models                244L  5C   12m  CC=5      ←0
  │ intent_matcher             241L  3C   10m  CC=12     ←0
  │ !! runtime_bridge             238L  3C   10m  CC=22     ←0
  │ !! shell_executor             235L  1C    6m  CC=17     ←0
  │ base                       230L  4C   12m  CC=8      ←0
  │ config                     226L  4C   19m  CC=9      ←2
  │ adapter                    225L  1C   10m  CC=6      ←0
  │ nl_parser                  225L  1C    8m  CC=11     ←0
  │ disambiguator              225L  2C    5m  CC=11     ←0
  │ !! debug_info                 224L  0C    3m  CC=20     ←2
  │ tools                      224L  0C    9m  CC=8      ←1
  │ desktop_action_executor    223L  1C   13m  CC=5      ←0
  │ toon_integration           223L  1C   32m  CC=9      ←1
  │ !! save                       222L  2C    6m  CC=18     ←1
  │ !! libvirt_stream             219L  1C   14m  CC=17     ←0
  │ !! pipeline_runner_shell      217L  1C    3m  CC=27     ←0
  │ playwright                 215L  1C    8m  CC=9      ←0
  │ keyword_intent_detector_config.json   215L  0C    0m  CC=0.0    ←0
  │ base                       214L  3C   12m  CC=6      ←0
  │ !! testql_export              207L  0C    9m  CC=22     ←1
  │ complex_detector           203L  2C    1m  CC=14     ←0
  │ keyboard_controller        202L  1C   11m  CC=4      ←0
  │ skill                      200L  2C    9m  CC=7      ←0
  │ langevin_sampler           198L  1C    4m  CC=12     ←0
  │ autonomous_drawing_pipeline   194L  1C   10m  CC=5      ←0
  │ kee_pass_xc_reader         193L  1C    5m  CC=10     ←0
  │ pipeline_runner            192L  1C    2m  CC=11     ←0
  │ pipeline_components        192L  3C   10m  CC=7      ←1
  │ orchestrator               189L  1C    9m  CC=13     ←0
  │ !! svg_path_parser            189L  0C    1m  CC=41     ←3
  │ function_cache             189L  1C    8m  CC=11     ←0
  │ session_logger             188L  1C   12m  CC=9      ←0
  │ base                       186L  3C   10m  CC=7      ←5
  │ browser_setup              183L  2C    6m  CC=14     ←0
  │ thermodynamic_router       181L  1C    4m  CC=8      ←0
  │ resources                  176L  2C   11m  CC=4      ←2
  │ !! page_analyzer              176L  1C    3m  CC=29     ←0
  │ tools                      176L  0C    3m  CC=12     ←1
  │ object_fetcher_class       176L  1C    6m  CC=13     ←0
  │ multi_command              175L  2C    8m  CC=5      ←1
  │ yaml_compat                175L  0C    0m  CC=0.0    ←0
  │ allocation_energy          173L  1C    4m  CC=8      ←0
  │ !! query_input                172L  1C    7m  CC=15     ←4
  │ display                    170L  0C   12m  CC=7      ←2
  │ llm_planner                169L  1C    4m  CC=7      ←0
  │ media_utils                165L  1C    8m  CC=7      ←5
  │ iconify_fetcher            164L  1C    3m  CC=6      ←0
  │ __init__                   160L  0C    2m  CC=2      ←0
  │ !! existing_browser_manager   160L  1C    3m  CC=28     ←0
  │ __init__                   160L  0C    0m  CC=0.0    ←0
  │ media_recorder             159L  1C    7m  CC=5      ←0
  │ routing_energy             159L  1C    5m  CC=9      ←0
  │ dispatcher                 158L  1C    4m  CC=7      ←0
  │ registry                   149L  1C    7m  CC=1      ←0
  │ rule_planner               148L  1C    8m  CC=11     ←0
  │ runner                     148L  1C    4m  CC=6      ←0
  │ !! form_field_filters         147L  0C    5m  CC=20     ←2
  │ __init__                   147L  1C   11m  CC=9      ←1
  │ !! plan                       145L  0C    2m  CC=29     ←1
  │ path_optimizer             144L  1C    7m  CC=9      ←0
  │ markdown_output            144L  2C   15m  CC=9      ←17
  │ !! kubernetes_validator       143L  1C    2m  CC=58     ←0
  │ cli                        143L  0C    1m  CC=2      ←1
  │ !! browser_connector          143L  1C    4m  CC=21     ←0
  │ legacy_drawcommand         142L  0C    3m  CC=9      ←4
  │ events                     142L  7C    7m  CC=1      ←0
  │ queries                    142L  6C    7m  CC=7      ←0
  │ router                     140L  1C    7m  CC=4      ←0
  │ colors                     135L  1C    6m  CC=6      ←0
  │ data_files                 134L  0C    6m  CC=8      ←10
  │ hybrid_thermodynamic_generator   133L  1C    3m  CC=2      ←0
  │ correction_engine          133L  1C    7m  CC=4      ←0
  │ vector_planner             131L  1C    6m  CC=8      ←0
  │ majority_voter             131L  1C    3m  CC=7      ←0
  │ !! plan_validator             131L  1C    3m  CC=16     ←0
  │ field_classifier           129L  1C    4m  CC=14     ←0
  │ __init__                   129L  0C    0m  CC=0.0    ←0
  │ window_manager             127L  1C    5m  CC=10     ←0
  │ !! canvas_to_vql              125L  0C    3m  CC=17     ←1
  │ engine                     125L  1C    4m  CC=7      ←0
  │ navigation                 125L  3C    3m  CC=7      ←0
  │ bitwarden_reader           124L  1C    3m  CC=11     ←0
  │ energy_estimator           124L  1C    1m  CC=1      ←0
  │ info                       121L  1C    4m  CC=9      ←1
  │ vnc_stream                 121L  1C    7m  CC=11     ←0
  │ env_password_reader        120L  1C    1m  CC=13     ←0
  │ store                      120L  1C    7m  CC=13     ←0
  │ plan_gate                  119L  2C    8m  CC=9      ←1
  │ error_pattern              118L  1C    4m  CC=4      ←2
  │ dispatcher                 117L  1C    4m  CC=6      ←0
  │ env_manager                116L  1C    4m  CC=7      ←0
  │ page_analyzer              116L  1C    3m  CC=7      ←0
  │ shape_planner              115L  1C    5m  CC=8      ←0
  │ syntax_cache               115L  1C    8m  CC=3      ←4
  │ git_templates              115L  0C    0m  CC=0.0    ←0
  │ sql_templates              114L  0C    0m  CC=0.0    ←0
  │ form_schema.json           114L  0C    0m  CC=0.0    ←0
  │ !! sql_validator              113L  1C    2m  CC=34     ←0
  │ browser_controller         111L  1C    5m  CC=6      ←0
  │ constraint_energy          111L  1C    4m  CC=3      ←0
  │ server                     110L  0C    7m  CC=10     ←0
  │ llm_client                 109L  0C    4m  CC=8      ←1
  │ hf_token_retriever         109L  1C    2m  CC=7      ←0
  │ energy_model               108L  1C    4m  CC=2      ←0
  │ shell_templates            108L  0C    0m  CC=0.0    ←0
  │ ssh_stream                 107L  1C    8m  CC=5      ←0
  │ !! action_handler             106L  1C    4m  CC=15     ←0
  │ __init__                   106L  0C    0m  CC=0.0    ←0
  │ !! shell_validator            105L  1C    2m  CC=31     ←0
  │ package_mgmt_templates     104L  0C    0m  CC=0.0    ←0
  │ shape_registry             102L  1C    4m  CC=3      ←0
  │ executor_registry          101L  1C    7m  CC=3      ←1
  │ event_store                101L  1C   13m  CC=3      ←0
  │ form_analyzer              101L  1C    7m  CC=4      ←0
  │ navigation_constants       100L  0C    0m  CC=0.0    ←0
  │ token_navigator             99L  2C    4m  CC=5      ←0
  │ !! json_parse                  98L  0C    3m  CC=20     ←1
  │ cdp_detector                98L  1C    4m  CC=13     ←0
  │ semantic_entities           97L  1C    7m  CC=9      ←0
  │ !! token_navigator             97L  2C    3m  CC=18     ←0
  │ entropy_production_regularizer    97L  1C    3m  CC=1      ←0
  │ backend_detector            96L  1C    6m  CC=6      ←0
  │ facade                      95L  2C    7m  CC=2      ←0
  │ model_performance           94L  1C    3m  CC=3      ←0
  │ token_prompt_handler        93L  1C    5m  CC=5      ←0
  │ appspec                     93L  2C    6m  CC=12     ←0
  │ svg                         92L  1C    8m  CC=6      ←0
  │ validation_result           91L  1C    9m  CC=6      ←0
  │ spec                        91L  1C    5m  CC=4      ←1
  │ !! pipeline_gate               91L  1C    6m  CC=20     ←4
  │ link_extractor              91L  1C    4m  CC=10     ←0
  │ desktop_templates           91L  0C    0m  CC=0.0    ←0
  │ canvas_plan                 90L  0C    2m  CC=11     ←1
  │ ws_stream                   90L  1C    8m  CC=8      ←0
  │ services.yaml               88L  0C    0m  CC=0.0    ←0
  │ quadratic_energy            87L  1C    3m  CC=2      ←0
  │ !! ftp_stream                  87L  1C    4m  CC=16     ←0
  │ validation_report           85L  1C    2m  CC=8      ←0
  │ base                        84L  1C    8m  CC=3      ←0
  │ draw_filled_circle_handler    84L  1C    2m  CC=5      ←0
  │ task_metric                 83L  1C    2m  CC=3      ←0
  │ cli                         83L  0C    1m  CC=3      ←0
  │ drawing                     82L  0C    1m  CC=1      ←0
  │ langevin_config             82L  1C    0m  CC=0.0    ←0
  │ fuzzy_schema_matcher        81L  0C    1m  CC=5      ←0
  │ page_schema_extractor       80L  1C    3m  CC=6      ←0
  │ browser_launcher            80L  1C    4m  CC=3      ←0
  │ base                        79L  2C    6m  CC=3      ←0
  │ docker_templates            78L  0C    0m  CC=0.0    ←0
  │ shapes                      78L  0C    0m  CC=0.0    ←0
  │ !! http_stream                 77L  1C    3m  CC=15     ←0
  │ factory                     77L  1C    6m  CC=6      ←3
  │ sampler_result              77L  1C    0m  CC=0.0    ←0
  │ devops_templates            77L  0C    0m  CC=0.0    ←0
  │ __init__                    77L  0C    0m  CC=0.0    ←0
  │ navigate                    76L  1C    2m  CC=10     ←0
  │ kubernetes_templates        76L  0C    0m  CC=0.0    ←0
  │ registry                    74L  1C    7m  CC=1      ←0
  │ draw_bezier_handler         74L  1C    1m  CC=5      ←0
  │ csp_energy                  72L  1C    4m  CC=2      ←0
  │ data_templates              72L  0C    0m  CC=0.0    ←0
  │ router_config.json          72L  0C    0m  CC=0.0    ←0
  │ !! execution_policy            71L  1C    1m  CC=18     ←0
  │ radio_extractor             70L  1C    2m  CC=13     ←0
  │ generated_function          70L  1C    2m  CC=2      ←0
  │ scheduling_energy           70L  1C    0m  CC=0.0    ←0
  │ routing_energy              70L  1C    0m  CC=0.0    ←0
  │ allocation_energy           70L  1C    0m  CC=0.0    ←0
  │ rag_templates               70L  0C    0m  CC=0.0    ←0
  │ nl_to_vql                   69L  0C    1m  CC=6      ←2
  │ base                        69L  3C    2m  CC=1      ←0
  │ credential                  68L  1C    1m  CC=4      ←0
  │ fuzzy_schema_matcher_config    68L  1C    3m  CC=4      ←0
  │ blueprint_planner           68L  1C    2m  CC=5      ←0
  │ console_wrapper             68L  1C    5m  CC=6      ←0
  │ pipeline_runner_utils       68L  0C    0m  CC=0.0    ←0
  │ base                        67L  4C    3m  CC=1      ←0
  │ svg_repo_fetcher            67L  1C    1m  CC=5      ←0
  │ !! engine                      67L  0C    1m  CC=17     ←0
  │ iot_templates               67L  0C    0m  CC=0.0    ←0
  │ button_extractor            66L  1C    2m  CC=9      ←0
  │ execution_context           66L  1C    3m  CC=8      ←62
  │ base                        65L  2C    3m  CC=1      ←1
  │ learned_rule                65L  1C    3m  CC=3      ←0
  │ learned_path                65L  1C    1m  CC=1      ←4
  │ ffmpeg_templates            65L  0C    0m  CC=0.0    ←0
  │ base                        64L  3C    1m  CC=7      ←0
  │ validator                   64L  1C    2m  CC=8      ←0
  │ base                        64L  3C    3m  CC=3      ←0
  │ draw_polygon_handler        64L  1C    1m  CC=4      ←0
  │ browser_templates           64L  0C    0m  CC=0.0    ←0
  │ remote_templates            64L  0C    0m  CC=0.0    ←0
  │ castle_generator            63L  1C    1m  CC=3      ←0
  │ simple_icons_fetcher        63L  1C    1m  CC=4      ←0
  │ spice_stream                63L  1C    3m  CC=4      ←0
  │ draw_svg_path_handler       63L  1C    1m  CC=5      ←0
  │ step_metric                 63L  1C    1m  CC=1      ←0
  │ types                       63L  3C    0m  CC=0.0    ←0
  │ presentation_templates      63L  0C    0m  CC=0.0    ←0
  │ form_extractor              62L  1C    2m  CC=8      ←0
  │ copy_button_extractor       62L  1C    2m  CC=7      ←0
  │ match_result                62L  1C    2m  CC=4      ←0
  │ base                        62L  3C    3m  CC=3      ←0
  │ canvas_mixin                62L  1C    3m  CC=1      ←0
  │ execution_plan              61L  1C    2m  CC=2      ←0
  │ draw_line_handler           61L  1C    1m  CC=4      ←0
  │ config                      61L  1C    4m  CC=6      ←1
  │ feedback_result             60L  1C    1m  CC=1      ←0
  │ draw_arc_handler            60L  1C    1m  CC=3      ←0
  │ api_templates               60L  0C    0m  CC=0.0    ←0
  │ junk_field_patterns.yaml    60L  0C    0m  CC=0.0    ←0
  │ token_extractor             59L  1C    2m  CC=6      ←0
  │ phrase_schema               59L  1C    2m  CC=4      ←0
  │ validation_constants        58L  0C    0m  CC=0.0    ←0
  │ media_templates             57L  0C    0m  CC=0.0    ←0
  │ __init__                    57L  0C    0m  CC=0.0    ←0
  │ optimization_schema.json    57L  0C    0m  CC=0.0    ←0
  │ appspec_runtime             56L  2C    2m  CC=10     ←3
  │ debug_helpers               56L  0C    2m  CC=7      ←0
  │ cat_generator               55L  1C    1m  CC=4      ←0
  │ base                        55L  2C    1m  CC=2      ←0
  │ integration                 54L  0C    2m  CC=3      ←3
  │ __init__                    54L  0C    0m  CC=0.0    ←0
  │ api                         54L  0C    0m  CC=0.0    ←0
  │ rdp_stream                  53L  1C    3m  CC=5      ←0
  │ base                        53L  2C    0m  CC=0.0    ←0
  │ task_result                 53L  1C    0m  CC=0.0    ←0
  │ selectors.yaml              53L  0C    0m  CC=0.0    ←0
  │ rocket_generator            52L  1C    1m  CC=2      ←0
  │ step_def                    52L  1C    1m  CC=1      ←0
  │ svg                         50L  1C    2m  CC=2      ←1
  │ butterfly_generator         50L  1C    1m  CC=5      ←0
  │ __base_fetcher              50L  1C    1m  CC=1      ←0
  │ step_diagnosis              50L  1C    0m  CC=0.0    ←0
  │ task_schema                 50L  1C    0m  CC=0.0    ←0
  │ bird_generator              49L  1C    1m  CC=2      ←0
  │ fill_at_handler             49L  1C    1m  CC=2      ←0
  │ click_canvas_handler        49L  1C    1m  CC=2      ←0
  │ draw_filled_ellipse_handler    49L  1C    1m  CC=2      ←0
  │ step_result                 49L  1C    0m  CC=0.0    ←0
  │ car_generator               48L  1C    1m  CC=3      ←0
  │ ir_convert                  48L  0C    1m  CC=5      ←1
  │ draw_ellipse_handler        48L  1C    1m  CC=2      ←0
  │ thermodynamic               48L  0C    1m  CC=1      ←5
  │ syntax_validator            47L  1C    1m  CC=6      ←0
  │ cloud_detailed_generator    47L  1C    1m  CC=4      ←0
  │ draw_rectangle_handler      47L  1C    1m  CC=2      ←0
  │ repair_attempt              47L  1C    0m  CC=0.0    ←0
  │ feedback_result             47L  1C    0m  CC=0.0    ←0
  │ step_status                 47L  1C    0m  CC=0.0    ←0
  │ fish_generator              46L  1C    1m  CC=3      ←0
  │ arrow_generator             46L  1C    1m  CC=3      ←0
  │ draw_circle_handler         46L  1C    1m  CC=2      ←0
  │ draw_filled_rectangle_handler    46L  1C    1m  CC=2      ←0
  │ contact_paths.yaml          46L  0C    0m  CC=0.0    ←0
  │ plan_execute                45L  0C    2m  CC=4      ←0
  │ iframe_analyzer             45L  1C    2m  CC=6      ←0
  │ __init__                    44L  0C    1m  CC=2      ←0
  │ select_tool_handler         44L  1C    1m  CC=2      ←0
  │ failure_type                44L  1C    0m  CC=0.0    ←0
  │ base_validator              43L  1C    2m  CC=1      ←0
  │ navigation_result           43L  1C    0m  CC=0.0    ←0
  │ fetched_shape               43L  1C    0m  CC=0.0    ←0
  │ __init__                    43L  0C    0m  CC=0.0    ←0
  │ action_schema               41L  1C    3m  CC=3      ←0
  │ canvas_info                 41L  1C    0m  CC=0.0    ←0
  │ docker_app                  41L  0C    0m  CC=0.0    ←0
  │ boat_generator              40L  1C    1m  CC=1      ←0
  │ __init__                    40L  0C    0m  CC=0.0    ←0
  │ mountain_generator          39L  1C    1m  CC=1      ←0
  │ llm_helpers                 39L  0C    2m  CC=8      ←6
  │ object_assessment           38L  1C    0m  CC=0.0    ←0
  │ __init__                    38L  0C    0m  CC=0.0    ←0
  │ base                        37L  2C    3m  CC=1      ←0
  │ shape_generator             37L  1C    1m  CC=1      ←0
  │ task_plan                   37L  1C    1m  CC=1      ←0
  │ metrics                     37L  0C    1m  CC=1      ←0
  │ set_line_width_handler      37L  1C    1m  CC=2      ←0
  │ correction_result           37L  1C    0m  CC=0.0    ←0
  │ drawing_plan                37L  1C    0m  CC=0.0    ←0
  │ optimization_report.yaml    37L  0C    0m  CC=0.0    ←0
  │ __init__                    37L  0C    0m  CC=0.0    ←0
  │ password_store              36L  0C    1m  CC=2      ←7
  │ diamond_generator           36L  1C    1m  CC=1      ←0
  │ crescent_generator          36L  1C    1m  CC=3      ←0
  │ sun_generator               36L  1C    1m  CC=3      ←0
  │ grid_generator              36L  1C    1m  CC=3      ←0
  │ correction_plan             36L  1C    0m  CC=0.0    ←0
  │ flower_generator            35L  1C    1m  CC=3      ←0
  │ drawing_step                35L  1C    0m  CC=0.0    ←0
  │ __init__                    35L  0C    0m  CC=0.0    ←0
  │ ir                          34L  1C    1m  CC=1      ←0
  │ wave_generator              34L  1C    1m  CC=2      ←0
  │ correction_step             34L  1C    0m  CC=0.0    ←0
  │ navigation_step             34L  1C    0m  CC=0.0    ←0
  │ tree_generator              33L  1C    1m  CC=2      ←0
  │ star_generator              33L  1C    1m  CC=2      ←0
  │ cross_generator             33L  1C    1m  CC=1      ←0
  │ navigation_state            33L  1C    0m  CC=0.0    ←0
  │ task                        33L  1C    0m  CC=0.0    ←0
  │ __init__                    33L  0C    0m  CC=0.0    ←0
  │ __init__                    33L  0C    0m  CC=0.0    ←0
  │ __init__                    33L  0C    0m  CC=0.0    ←0
  │ spiral_generator            32L  1C    1m  CC=2      ←0
  │ set_color_handler           32L  1C    1m  CC=2      ←0
  │ object_status               32L  1C    0m  CC=0.0    ←0
  │ environment_report          32L  1C    0m  CC=0.0    ←0
  │ __init__                    32L  0C    0m  CC=0.0    ←0
  │ plan_step                   31L  1C    1m  CC=2      ←0
  │ canvas_safety_policy        31L  1C    0m  CC=0.0    ←0
  │ resource                    31L  1C    0m  CC=0.0    ←0
  │ __init__                    31L  0C    0m  CC=0.0    ←0
  │ house_generator             30L  1C    1m  CC=1      ←0
  │ ellipse_generator           30L  1C    1m  CC=2      ←0
  │ heart_generator             30L  1C    1m  CC=2      ←0
  │ __init__                    30L  0C    0m  CC=0.0    ←0
  │ composite_validator         29L  1C    2m  CC=2      ←0
  │ dot_generator               29L  1C    1m  CC=2      ←0
  │ circle_generator            29L  1C    1m  CC=2      ←0
  │ __init__                    29L  0C    0m  CC=0.0    ←0
  │ __init__                    29L  0C    0m  CC=0.0    ←0
  │ __init__                    29L  0C    0m  CC=0.0    ←0
  │ navigation                  29L  0C    0m  CC=0.0    ←0
  │ action_result               28L  1C    2m  CC=1      ←0
  │ service_info                28L  1C    0m  CC=0.0    ←0
  │ octagon_generator           27L  1C    1m  CC=2      ←0
  │ hexagon_generator           27L  1C    1m  CC=2      ←0
  │ pentagon_generator          27L  1C    1m  CC=2      ←0
  │ step_result                 27L  1C    0m  CC=0.0    ←0
  │ tool_info                   27L  1C    0m  CC=0.0    ←0
  │ __init__                    27L  0C    0m  CC=0.0    ←0
  │ triangle_generator          26L  1C    1m  CC=1      ←0
  │ rectangle_generator         26L  1C    1m  CC=1      ←0
  │ execution_result            26L  1C    0m  CC=0.0    ←0
  │ correction_rule             26L  1C    0m  CC=0.0    ←0
  │ feedback_type               26L  1C    0m  CC=0.0    ←0
  │ __init__                    26L  0C    0m  CC=0.0    ←0
  │ line_generator              25L  1C    1m  CC=1      ←0
  │ square_generator            25L  1C    1m  CC=1      ←0
  │ intent_ir                   25L  0C    2m  CC=2      ←0
  │ get_canvas_center_handler    25L  1C    1m  CC=3      ←0
  │ param_schema                25L  1C    0m  CC=0.0    ←0
  │ param_type                  25L  1C    0m  CC=0.0    ←0
  │ evolutionary_orchestrator    25L  0C    0m  CC=0.0    ←0
  │ __init__                    24L  0C    0m  CC=0.0    ←0
  │ __init__                    24L  0C    0m  CC=0.0    ←0
  │ __init__                    24L  0C    0m  CC=0.0    ←0
  │ shell_execution_policy.json    24L  0C    0m  CC=0.0    ←0
  │ __init__                    24L  0C    0m  CC=0.0    ←0
  │ __init__                    23L  0C    1m  CC=2      ←0
  │ form_data.json              23L  0C    0m  CC=0.0    ←0
  │ intract-policy.json         23L  0C    0m  CC=0.0    ←0
  │ playwright                  22L  1C    1m  CC=1      ←0
  │ step_status                 22L  1C    0m  CC=0.0    ←0
  │ __init__                    22L  0C    0m  CC=0.0    ←0
  │ __init__                    22L  0C    0m  CC=0.0    ←0
  │ __init__                    22L  0C    0m  CC=0.0    ←0
  │ __init__                    21L  0C    1m  CC=2      ←0
  │ __init__                    21L  0C    0m  CC=0.0    ←0
  │ validation                  21L  0C    0m  CC=0.0    ←0
  │ __init__                    21L  0C    0m  CC=0.0    ←0
  │ __init__                    21L  0C    0m  CC=0.0    ←0
  │ get_registry                20L  0C    1m  CC=2      ←6
  │ __init__                    20L  0C    0m  CC=0.0    ←0
  │ object_fetcher              19L  0C    0m  CC=0.0    ←0
  │ canvas_constants            19L  0C    0m  CC=0.0    ←0
  │ __init__                    19L  0C    0m  CC=0.0    ←0
  │ metrics_helpers             18L  0C    2m  CC=2      ←5
  │ wait_for_canvas_handler     17L  1C    1m  CC=1      ←0
  │ __init__                    17L  0C    0m  CC=0.0    ←0
  │ __init__                    17L  0C    0m  CC=0.0    ←0
  │ energy_models               17L  0C    0m  CC=0.0    ←0
  │ color_validation            16L  0C    1m  CC=2      ←2
  │ __init__                    16L  0C    0m  CC=0.0    ←0
  │ __init__                    16L  0C    0m  CC=0.0    ←0
  │ runner_result               15L  1C    0m  CC=0.0    ←0
  │ __init__                    15L  0C    0m  CC=0.0    ←0
  │ __init__                    15L  0C    0m  CC=0.0    ←0
  │ __init__                    15L  0C    0m  CC=0.0    ←0
  │ adaptive_learner            14L  0C    0m  CC=0.0    ←0
  │ __init__                    14L  0C    0m  CC=0.0    ←0
  │ __init__                    13L  0C    0m  CC=0.0    ←0
  │ __init__                    13L  0C    0m  CC=0.0    ←0
  │ keyword_detector            12L  0C    0m  CC=0.0    ←0
  │ __init__                    12L  0C    0m  CC=0.0    ←0
  │ generator                   12L  0C    0m  CC=0.0    ←0
  │ __init__                    11L  0C    0m  CC=0.0    ←0
  │ feedback_loop               10L  0C    0m  CC=0.0    ←0
  │ correction_engine            9L  0C    0m  CC=0.0    ←0
  │ __init__                     9L  0C    0m  CC=0.0    ←0
  │ adapter                      9L  0C    0m  CC=0.0    ←0
  │ __main__                     8L  0C    0m  CC=0.0    ←0
  │ canvas                       8L  0C    0m  CC=0.0    ←0
  │ __init__                     8L  0C    0m  CC=0.0    ←0
  │ __main__                     7L  0C    0m  CC=0.0    ←0
  │ __init__                     6L  0C    0m  CC=0.0    ←0
  │ keyword_patterns             5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     3L  0C    0m  CC=0.0    ←0
  │ defaults.json                1L  0C    0m  CC=0.0    ←0
  │ semantic_embeddings.json     1L  0C    0m  CC=0.0    ←0
  │
  scripts/                        CC̄=4.0    ←in:0  →out:28  !! split
  │ !! implement_core_integration   805L  1C   10m  CC=11     ←0
  │ !! generate_intract_manifest   799L  0C   15m  CC=24     ←0
  │ !! implement_high_priority_fixes   518L  1C   10m  CC=6      ←0
  │ final_analysis_and_next_steps   476L  1C   10m  CC=9      ←0
  │ final_project_summary      461L  1C   10m  CC=7      ←0
  │ !! fix_comprehensive_test_issues   395L  1C    9m  CC=17     ←0
  │ run_e2e_tests              354L  1C   16m  CC=6      ←0
  │ !! auto_apply_refactors       289L  0C    3m  CC=20     ←0
  │ termo2                     283L  0C    7m  CC=6      ←0
  │ !! llx_refactor               256L  0C    6m  CC=19     ←0
  │ refactor_detect_normalized   249L  0C   10m  CC=7      ←2
  │ apply_refactors_to_source   235L  0C    4m  CC=1      ←0
  │ refactor_shell_entities    234L  0C   11m  CC=3      ←2
  │ termo_demo                 226L  0C    5m  CC=6      ←0
  │ !! split_god_modules          217L  1C   10m  CC=16     ←0
  │ generate_refactor_report   186L  0C    1m  CC=8      ←0
  │ split_pipeline_runner      177L  0C    2m  CC=3      ←0
  │ install_desktop_tools.sh   167L  0C    5m  CC=0.0    ←0
  │ compare_entity_extractors   158L  0C    7m  CC=11     ←0
  │ vrp_solver                 135L  1C   12m  CC=8      ←0
  │ apply_polish_integration   124L  0C    4m  CC=9      ←0
  │ termo                      116L  0C    4m  CC=3      ←0
  │ restore_system             115L  0C    4m  CC=9      ←0
  │ cyclomatic_complexity_refactor_report.json   107L  0C    0m  CC=0.0    ←0
  │ or_scheduler               104L  1C    9m  CC=5      ←0
  │ !! split_web_controller        96L  1C    4m  CC=16     ←0
  │ refactoring_summary         92L  0C    1m  CC=1      ←0
  │ hyperparameter_optimizer    85L  1C    4m  CC=3      ←0
  │ apply_nlp2cmd_fixes         84L  0C    5m  CC=2      ←0
  │ unit_commitment_solver      80L  1C    3m  CC=6      ←0
  │ test_commands_docker.sh     78L  0C    0m  CC=0.0    ←0
  │ genomic_pipeline_scheduler    65L  1C    3m  CC=5      ←0
  │ setup_external              63L  0C    1m  CC=7      ←0
  │ bump_version                62L  0C    1m  CC=6      ←0
  │ apply_complexity_refactors    60L  0C    1m  CC=2      ←0
  │ update_integration_deps.sh    51L  0C    0m  CC=0.0    ←0
  │ install_mcp_stack.sh        46L  0C    2m  CC=0.0    ←0
  │ termo1                      25L  0C    1m  CC=3      ←0
  │ power_plant                 23L  1C    0m  CC=0.0    ←0
  │ pipeline_step               20L  1C    0m  CC=0.0    ←0
  │ surgery                     20L  1C    0m  CC=0.0    ←0
  │ hyperparameter_space        20L  1C    0m  CC=0.0    ←0
  │ delivery_point              20L  1C    0m  CC=0.0    ←0
  │ genomic_sample              18L  1C    0m  CC=0.0    ←0
  │ operating_room              18L  1C    0m  CC=0.0    ←0
  │
  test_screenshots/               CC̄=3.9    ←in:0  →out:62  !! split
  │ test_openrouter_workflow.sh   225L  0C    4m  CC=0.0    ←0
  │ analyze_screenshots        217L  0C    4m  CC=12     ←0
  │ compare_screenshots        151L  0C    4m  CC=9      ←0
  │ raport_testu.txt            67L  0C    0m  CC=0.0    ←0
  │ capture_script.sh           34L  0C    0m  CC=0.0    ←0
  │
  examples/                       CC̄=3.6    ←in:277  →out:85  !! split
  │ !! runtime_schemas.json      3600L  0C    0m  CC=0.0    ←0
  │ !! appspec_cache.json        1430L  0C    0m  CC=0.0    ←0
  │ !! nlp2_cmd_web_controller    782L  1C   30m  CC=7      ←0
  │ !! _run_utils                 757L  2C   29m  CC=13     ←1
  │ !! validation                 732L  2C   12m  CC=8      ←0
  │ !! 04_object_database_drawing   574L  3C   15m  CC=18     ←0
  │ benchmark_before.json      495L  0C    0m  CC=0.0    ←0
  │ benchmark_after.json       495L  0C    0m  CC=0.0    ←0
  │ practical_usage            470L  1C    8m  CC=2      ←0
  │ benchmark                  465L  0C    9m  CC=4      ←0
  │ !! benchmark_validator        425L  2C    6m  CC=28     ←0
  │ !! 03_adaptive_code           417L  0C    4m  CC=37     ←1
  │ 03_adaptive_20260303_143144.json   404L  0C    0m  CC=0.0    ←0
  │ 03_adaptive_20260303_145342.json   404L  0C    0m  CC=0.0    ←0
  │ 03_adaptive_20260303_145059.json   404L  0C    0m  CC=0.0    ←0
  │ end_to_end_demo            402L  0C    7m  CC=12     ←0
  │ demo_versioned_schemas     399L  0C    4m  CC=11     ←0
  │ !! 02_mycompiler_run          393L  0C    1m  CC=32     ←0
  │ !! example_pdf_search         386L  2C   12m  CC=15     ←0
  │ run                        384L  0C   12m  CC=8      ←0
  │ mock_test_polish_llm       378L  2C    7m  CC=10     ←0
  │ _verbose_helper            356L  0C   11m  CC=6      ←15
  │ generated_shell_appspec.json   352L  0C    0m  CC=0.0    ←0
  │ comparison_demo            346L  1C   19m  CC=8      ←0
  │ llm_integration            345L  1C    6m  CC=6      ←0
  │ guide                      344L  0C    6m  CC=1      ←0
  │ !! api_key_prompts            343L  1C    2m  CC=15     ←0
  │ advanced                   334L  0C    1m  CC=2      ←0
  │ config_validation          328L  0C    3m  CC=6      ←0
  │ 01_draw_chat_20260303_143953.json   320L  0C    0m  CC=0.0    ←0
  │ 01_draw_chat_20260303_144543.json   320L  0C    0m  CC=0.0    ←0
  │ 01_draw_chat_20260303_144325.json   320L  0C    0m  CC=0.0    ←0
  │ 01_draw_chat_20260303_142823.json   320L  0C    0m  CC=0.0    ←0
  │ 01_draw_chat_20260303_142636.json   320L  0C    0m  CC=0.0    ←0
  │ workflows                  319L  0C    2m  CC=10     ←0
  │ setup_and_test_bielik      311L  1C    8m  CC=9      ←0
  │ run                        308L  0C    5m  CC=8      ←0
  │ 05_autonomous_drawing      305L  0C    4m  CC=14     ←0
  │ file_repair                299L  0C    4m  CC=11     ←0
  │ !! run                        297L  0C    4m  CC=21     ←0
  │ !! 04_jsfiddle_frontend       297L  0C    1m  CC=19     ←0
  │ demo_intelligent_nlp2cmd   295L  1C    9m  CC=11     ←0
  │ 02_picsart_20260303_144922.json   290L  0C    0m  CC=0.0    ←0
  │ !! 01_codepen_live            289L  0C    4m  CC=21     ←0
  │ run_examples.sh            282L  0C   10m  CC=0.0    ←0
  │ !! infrastructure_health      280L  0C    6m  CC=19     ←0
  │ example                    267L  0C    7m  CC=4      ←0
  │ !! run                        266L  0C    3m  CC=18     ←0
  │ dsl_demo                   264L  0C   11m  CC=3      ←0
  │ simple_demo                263L  0C    6m  CC=2      ←0
  │ complete_examples          262L  0C    7m  CC=6      ←0
  │ demo_schema_flow           260L  0C    4m  CC=6      ←0
  │ run.sh                     255L  0C    1m  CC=0.0    ←0
  │ 02_picsart_20260303_142942.json   254L  0C    0m  CC=0.0    ←0
  │ docker_manager             251L  1C    5m  CC=13     ←0
  │ 03_adaptive_drawing        251L  0C    2m  CC=11     ←0
  │ simple_demo                244L  0C    7m  CC=2      ←0
  │ _demo_helpers              243L  0C   18m  CC=9      ←3
  │ 02_picsart_20260303_144722.json   242L  0C    0m  CC=0.0    ←0
  │ demo                       240L  0C    6m  CC=9      ←0
  │ run                        231L  0C    4m  CC=14     ←0
  │ demo_auto                  226L  0C    3m  CC=12     ←0
  │ 01_draw_chat_20260303_142425.json   224L  0C    0m  CC=0.0    ←0
  │ !! nl_command_parser          210L  1C    4m  CC=19     ←0
  │ generated_shell_dynamic_schema.json   207L  0C    0m  CC=0.0    ←0
  │ run.sh                     206L  0C    4m  CC=0.0    ←0
  │ feedback_loop              203L  0C    9m  CC=5      ←0
  │ schema_flow_demo           194L  0C    4m  CC=7      ←0
  │ example                    192L  0C    8m  CC=1      ←0
  │ example                    190L  0C    8m  CC=1      ←0
  │ benchmark                  189L  0C    3m  CC=6      ←0
  │ _verbose_schema            189L  0C    2m  CC=13     ←1
  │ example                    188L  0C    8m  CC=1      ←0
  │ !! log_analysis               187L  0C    4m  CC=15     ←0
  │ example                    186L  0C    8m  CC=1      ←0
  │ example                    183L  0C    7m  CC=3      ←0
  │ example                    183L  0C    8m  CC=1      ←0
  │ _demo_helpers              182L  0C   12m  CC=11     ←14
  │ _environment_sections      179L  0C   11m  CC=11     ←1
  │ demo_version_detection     177L  0C    9m  CC=4      ←0
  │ test_results.json          175L  0C    0m  CC=0.0    ←0
  │ run                        165L  0C    5m  CC=10     ←0
  │ example                    160L  0C    7m  CC=1      ←0
  │ web_app_example            159L  3C    8m  CC=3      ←0
  │ 01_draw_chat_20260303_170506.json   158L  0C    0m  CC=0.0    ←0
  │ 01_draw_chat_20260303_170742.json   158L  0C    0m  CC=0.0    ←0
  │ 01_draw_chat_20260303_171110.json   158L  0C    0m  CC=0.0    ←0
  │ 01_draw_chat_20260303_170840.json   158L  0C    0m  CC=0.0    ←0
  │ 01_draw_chat_20260303_171804.json   158L  0C    0m  CC=0.0    ←0
  │ 01_draw_chat_20260303_170729.json   158L  0C    0m  CC=0.0    ←0
  │ 02_picsart_painting_nlp2cmd   157L  0C    4m  CC=7      ←0
  │ demo_persistent_storage    154L  0C    2m  CC=11     ←0
  │ run                        154L  0C    1m  CC=8      ←0
  │ 05_dynamic_executor        153L  0C    2m  CC=8      ←0
  │ example                    153L  0C    5m  CC=5      ←0
  │ 03_adaptive_drawing_nlp2cmd   146L  0C    4m  CC=7      ←0
  │ example                    145L  0C    6m  CC=1      ←0
  │ example                    142L  0C    1m  CC=10     ←0
  │ 01_draw_chat_shapes_nlp2cmd   141L  0C    4m  CC=7      ←0
  │ commands_demo.sh           140L  0C    0m  CC=0.0    ←0
  │ run_all                    139L  0C    2m  CC=5      ←0
  │ intents                    139L  0C    1m  CC=8      ←0
  │ run                        136L  0C    1m  CC=6      ←0
  │ demo                       134L  1C    5m  CC=6      ←0
  │ example                    133L  0C    3m  CC=5      ←0
  │ demo                       132L  2C    9m  CC=4      ←0
  │ run                        132L  0C    1m  CC=9      ←0
  │ !! deployment_plan            131L  1C    3m  CC=17     ←0
  │ nlp2_cmd_web_api           130L  1C    5m  CC=2      ←0
  │ demo                       128L  3C    6m  CC=5      ←0
  │ demo_batch                 128L  0C    6m  CC=5      ←0
  │ demo_enhanced              126L  0C    1m  CC=12     ←0
  │ run                        126L  0C    3m  CC=11     ←0
  │ !! show_metrics               124L  0C    1m  CC=15     ←0
  │ 03_adaptive_20260303_170926.json   122L  0C    0m  CC=0.0    ←0
  │ 03_adaptive_20260303_171825.json   122L  0C    0m  CC=0.0    ←0
  │ 03_adaptive_20260303_170902.json   122L  0C    0m  CC=0.0    ←0
  │ usage_example              121L  0C    1m  CC=9      ←0
  │ simple_schema_demo         119L  0C    1m  CC=6      ←0
  │ demo                       119L  2C    5m  CC=5      ←0
  │ 02_picsart_painting        117L  0C    1m  CC=3      ←0
  │ benchmark_report.json      116L  0C    0m  CC=0.0    ←0
  │ benchmark_report.json      116L  0C    0m  CC=0.0    ←0
  │ example                    111L  0C    1m  CC=6      ←0
  │ example                    111L  0C    1m  CC=7      ←0
  │ run                        108L  0C    3m  CC=7      ←0
  │ !! run                        108L  0C    1m  CC=16     ←0
  │ demo                       108L  4C    8m  CC=2      ←0
  │ demo                       108L  1C    4m  CC=7      ←0
  │ 01_draw_chat_shapes        105L  0C    1m  CC=3      ←0
  │ 02_picsart_20260303_171011.json   104L  0C    0m  CC=0.0    ←0
  │ 01_basics_shell_nlp2cmd    103L  0C    3m  CC=6      ←0
  │ manual_appspec             102L  0C    1m  CC=1      ←0
  │ run_task                   101L  0C    1m  CC=11     ←0
  │ run                        101L  0C    3m  CC=8      ←0
  │ demo                       101L  0C    4m  CC=3      ←0
  │ example                    100L  0C    4m  CC=2      ←0
  │ demo                       100L  1C    1m  CC=2      ←0
  │ learned_schemas.json       100L  0C    0m  CC=0.0    ←0
  │ demo                        99L  2C    1m  CC=4      ←0
  │ run                         99L  0C    2m  CC=6      ←0
  │ run                         98L  0C    1m  CC=7      ←0
  │ _dynamic_orchestrator       97L  1C    2m  CC=4      ←0
  │ demo                        97L  2C    2m  CC=4      ←0
  │ demo                        97L  2C    5m  CC=4      ←0
  │ demo                        96L  2C    3m  CC=6      ←0
  │ Makefile                    96L  0C    0m  CC=0.0    ←0
  │ demo                        95L  2C    2m  CC=5      ←0
  │ run                         95L  0C    1m  CC=5      ←0
  │ demo                        94L  1C    5m  CC=3      ←0
  │ run                         93L  0C    3m  CC=8      ←0
  │ demo                        93L  0C    3m  CC=4      ←0
  │ example                     93L  0C    1m  CC=5      ←0
  │ demo                        91L  0C    3m  CC=4      ←0
  │ 02_mycompiler_run_nlp2cmd    90L  0C    3m  CC=6      ←0
  │ example_rtsp                89L  0C    1m  CC=3      ←0
  │ old_system_loader           89L  1C    5m  CC=8      ←0
  │ example_multi_stream        88L  0C    1m  CC=7      ←0
  │ 01_codepen_live_nlp2cmd     86L  0C    3m  CC=6      ←0
  │ generator                   86L  0C    1m  CC=6      ←0
  │ 01_diagnose_credentials_nlp2cmd    85L  0C    3m  CC=5      ←0
  │ example_libvirt             85L  0C    1m  CC=3      ←0
  │ 04_jsfiddle_frontend_nlp2cmd    85L  0C    3m  CC=6      ←0
  │ 01_basics_docker_nlp2cmd    84L  0C    3m  CC=5      ←0
  │ test_feedback_results.json    84L  0C    0m  CC=0.0    ←0
  │ demo                        83L  1C    2m  CC=5      ←0
  │ demo                        80L  2C    4m  CC=2      ←0
  │ output_file_manager         77L  1C    4m  CC=1      ←0
  │ demo                        77L  1C    1m  CC=2      ←0
  │ demo                        76L  0C    1m  CC=1      ←0
  │ demo                        75L  1C    1m  CC=2      ←0
  │ demo                        75L  1C    1m  CC=2      ←0
  │ demo                        75L  1C    1m  CC=2      ←0
  │ example                     74L  0C    1m  CC=1      ←0
  │ demo                        74L  0C    1m  CC=1      ←0
  │ 03_adaptive_code_nlp2cmd    74L  0C    2m  CC=6      ←0
  │ 05_dynamic_executor_nlp2cmd    74L  0C    2m  CC=6      ←0
  │ run.sh                      72L  0C    0m  CC=0.0    ←0
  │ demo                        71L  0C    1m  CC=1      ←0
  │ download_bielik             71L  0C    1m  CC=6      ←0
  │ demo                        71L  1C    1m  CC=2      ←0
  │ demo                        70L  0C    1m  CC=1      ←0
  │ demo                        69L  0C    1m  CC=1      ←0
  │ run.sh                      69L  0C    0m  CC=0.0    ←0
  │ !! run                         68L  0C    1m  CC=18     ←0
  │ demo_validation.sh          67L  0C    0m  CC=0.0    ←0
  │ demo                        66L  0C    1m  CC=1      ←0
  │ demo                        65L  1C    1m  CC=3      ←0
  │ demo                        64L  1C    1m  CC=2      ←0
  │ demo                        64L  1C    1m  CC=2      ←0
  │ demo                        64L  1C    1m  CC=2      ←0
  │ demo                        63L  0C    1m  CC=1      ←0
  │ shell_validation_report.txt    63L  0C    0m  CC=0.0    ←0
  │ validation_report.txt       63L  0C    0m  CC=0.0    ←0
  │ run.sh                      62L  0C    0m  CC=0.0    ←0
  │ run                         61L  0C    1m  CC=5      ←0
  │ demo                        61L  0C    1m  CC=1      ←0
  │ demo                        60L  0C    1m  CC=1      ←0
  │ demo                        60L  0C    1m  CC=2      ←0
  │ demo                        59L  0C    1m  CC=2      ←0
  │ example_ssh                 59L  0C    1m  CC=3      ←0
  │ keywords                    56L  0C    1m  CC=3      ←0
  │ demo_screenshot_video.sh    56L  0C    0m  CC=0.0    ←0
  │ environment_analysis        55L  0C    1m  CC=6      ←0
  │ example_http_api            54L  0C    1m  CC=3      ←0
  │ service_config              54L  1C    0m  CC=0.0    ←0
  │ demo                        53L  0C    1m  CC=2      ←0
  │ __init__                    52L  0C    0m  CC=0.0    ←0
  │ demo                        51L  0C    1m  CC=2      ←0
  │ service_type                51L  1C    0m  CC=0.0    ←0
  │ demo                        50L  0C    1m  CC=3      ←0
  │ run.sh                      45L  0C    0m  CC=0.0    ←0
  │ run.sh                      45L  0C    0m  CC=0.0    ←0
  │ schema_cache                43L  0C    1m  CC=5      ←0
  │ kubectl_dynamic_schema.json    30L  0C    0m  CC=0.0    ←0
  │ kubectl_dynamic_schema.json    29L  0C    0m  CC=0.0    ←0
  │ 03_interactive_mode.sh      28L  0C    0m  CC=0.0    ←0
  │ 07_batch_multiple.sh        28L  0C    0m  CC=0.0    ←0
  │ sequential_benchmark_results.json    27L  0C    0m  CC=0.0    ←0
  │ chat-service-docker-compose.yml    27L  0C    0m  CC=0.0    ←0
  │ sequential_benchmark_results.json    27L  0C    0m  CC=0.0    ←0
  │ mvp                         26L  0C    1m  CC=1      ←0
  │ 02_video_only.sh            26L  0C    0m  CC=0.0    ←0
  │ _example_helpers            24L  0C    2m  CC=2      ←47
  │ example                     24L  0C    1m  CC=1      ←0
  │ 04_oferteo_extraction.sh    24L  0C    0m  CC=0.0    ←0
  │ 01_screenshot_only.sh       23L  0C    0m  CC=0.0    ←0
  │ prompt.txt                  21L  0C    0m  CC=0.0    ←0
  │ 05_simple_formfill.sh       19L  0C    0m  CC=0.0    ←0
  │ 06_formfill_with_discovery.sh    19L  0C    0m  CC=0.0    ←0
  │ mcp-config.cursor.json      18L  0C    0m  CC=0.0    ←0
  │ chat-service-config.json    17L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ validation_star_red.json    14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ run.sh                      14L  0C    0m  CC=0.0    ←0
  │ e2e.sh                      14L  0C    0m  CC=0.0    ←0
  │ nlp2cmd_web_controller      12L  0C    0m  CC=0.0    ←0
  │
  docker/                         CC̄=3.5    ←in:0  →out:0
  │ demo_desktop_gui           283L  0C    6m  CC=9      ←0
  │ Dockerfile                  69L  0C    0m  CC=0.0    ←0
  │ start-vnc.sh                51L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml          28L  0C    0m  CC=0.0    ←0
  │
  ./                              CC̄=0.1    ←in:0  →out:0
  │ !! planfile.yaml            29074L  0C    0m  CC=0.0    ←0
  │ !! out_interprocedural_decision_paths.json  8372L  0C    0m  CC=0.0    ←0
  │ !! intract.yaml              1271L  0C    0m  CC=0.0    ←0
  │ !! Makefile                   555L  0C    0m  CC=0.0    ←0
  │ goal.yaml                  430L  0C    0m  CC=0.0    ←0
  │ test_nlp2cmd_enhanced.sh   380L  0C   14m  CC=0.0    ←0
  │ test_nlp2cmd_commands.sh   320L  0C    5m  CC=0.0    ←268
  │ pyproject.toml             311L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml         223L  0C    0m  CC=0.0    ←0
  │ out_call_graph.json        166L  0C    0m  CC=0.0    ←0
  │ manual_appspec.json        160L  0C    0m  CC=0.0    ←0
  │ config.yaml                141L  0C    0m  CC=0.0    ←0
  │ Dockerfile                 105L  0C    0m  CC=0.0    ←0
  │ prefact.yaml                82L  0C    0m  CC=0.0    ←0
  │ generate_quick              63L  0C    0m  CC=0.0    ←0
  │ generate_working            60L  0C    0m  CC=0.0    ←0
  │ requirements.txt            60L  0C    0m  CC=0.0    ←0
  │ run_all_tests.sh            59L  0C    0m  CC=0.0    ←0
  │ pyqual.yaml                 59L  0C    0m  CC=0.0    ←0
  │ generate_chunks             57L  0C    0m  CC=0.0    ←0
  │ requirements-enhanced.txt    54L  0C    0m  CC=0.0    ←0
  │ projektor.yaml              51L  0C    0m  CC=0.0    ←0
  │ project.sh                  48L  0C    0m  CC=0.0    ←0
  │ generated_appspec.json      47L  0C    0m  CC=0.0    ←0
  │ pytest.ini                  41L  0C    0m  CC=0.0    ←0
  │ run_test.sh                 38L  0C    0m  CC=0.0    ←0
  │ examples.sh                 36L  0C    1m  CC=0.0    ←0
  │ out_function_entries.json    21L  0C    0m  CC=0.0    ←0
  │ oferteo_pl_data.txt         20L  0C    0m  CC=0.0    ←0
  │ jspaint_app_test4           18L  0C    1m  CC=2      ←0
  │ requirements-thermodynamic.txt    16L  0C    0m  CC=0.0    ←0
  │ requirements-minimal.txt    12L  0C    0m  CC=0.0    ←0
  │ requirements.llm.txt        11L  0C    0m  CC=0.0    ←0
  │ code2llm_workaround         10L  0C    0m  CC=0.0    ←0
  │ .markdownlint.json          10L  0C    0m  CC=0.0    ←0
  │ install_vnc.sh               1L  0C    0m  CC=0.0    ←0
  │ tree.sh                      1L  0C    0m  CC=0.0    ←0
  │
  command_schemas/                CC̄=0.0    ←in:0  →out:0
  │ !! generated_schemas.json    6405L  0C    0m  CC=0.0    ←0
  │ !! all_schemas.json          6405L  0C    0m  CC=0.0    ←0
  │ !! quick_batch_1_llm.json     571L  0C    0m  CC=0.0    ←0
  │ !! batch_1_test.json          561L  0C    0m  CC=0.0    ←0
  │ quick_batch_3_llm.json     451L  0C    0m  CC=0.0    ←0
  │ index.json                 444L  0C    0m  CC=0.0    ←0
  │ validated_schemas.json     442L  0C    0m  CC=0.0    ←0
  │ quick_batch_2_llm.json     416L  0C    0m  CC=0.0    ←0
  │ batch_3_final.json         268L  0C    0m  CC=0.0    ←0
  │ batch_2_test.json          268L  0C    0m  CC=0.0    ←0
  │ batch_3_test.json          259L  0C    0m  CC=0.0    ←0
  │ docker.appspec.json        149L  0C    0m  CC=0.0    ←0
  │ tar.json                   145L  0C    0m  CC=0.0    ←0
  │ node.json                  121L  0C    0m  CC=0.0    ←0
  │ docker.appspec.json        104L  0C    0m  CC=0.0    ←0
  │ generated_docker_dynamic_schema.json   101L  0C    0m  CC=0.0    ←0
  │ gpg.json                    92L  0C    0m  CC=0.0    ←0
  │ df.json                     92L  0C    0m  CC=0.0    ←0
  │ linux_shortcuts.json        84L  0C    0m  CC=0.0    ←0
  │ ls.json                     83L  0C    0m  CC=0.0    ←0
  │ macos_shortcuts.json        80L  0C    0m  CC=0.0    ←0
  │ rsync.json                  78L  0C    0m  CC=0.0    ←0
  │ windows_shortcuts.json      78L  0C    0m  CC=0.0    ←0
  │ nmap.json                   77L  0C    0m  CC=0.0    ←0
  │ pytest.json                 70L  0C    0m  CC=0.0    ←0
  │ ssh-keygen.json             70L  0C    0m  CC=0.0    ←0
  │ grep.json                   68L  0C    0m  CC=0.0    ←0
  │ black.json                  63L  0C    0m  CC=0.0    ←0
  │ batch_1_detailed.json       62L  0C    0m  CC=0.0    ←0
  │ cp.json                     61L  0C    0m  CC=0.0    ←0
  │ jq.json                     59L  0C    0m  CC=0.0    ←0
  │ make.json                   57L  0C    0m  CC=0.0    ←0
  │ sort.json                   56L  0C    0m  CC=0.0    ←0
  │ pip.json                    53L  0C    0m  CC=0.0    ←0
  │ iptables.json               53L  0C    0m  CC=0.0    ←0
  │ lsof.json                   51L  0C    0m  CC=0.0    ←0
  │ kubectl.appspec.json        51L  0C    0m  CC=0.0    ←0
  │ netstat.json                50L  0C    0m  CC=0.0    ←0
  │ python3.json                49L  0C    0m  CC=0.0    ←0
  │ mv.json                     46L  0C    0m  CC=0.0    ←0
  │ free.json                   44L  0C    0m  CC=0.0    ←0
  │ find.json                   43L  0C    0m  CC=0.0    ←0
  │ split.json                  42L  0C    0m  CC=0.0    ←0
  │ sensors.json                41L  0C    0m  CC=0.0    ←0
  │ search.json                 41L  0C    0m  CC=0.0    ←0
  │ sed.json                    40L  0C    0m  CC=0.0    ←0
  │ cat.json                    40L  0C    0m  CC=0.0    ←0
  │ chmod.json                  40L  0C    0m  CC=0.0    ←0
  │ zip.json                    39L  0C    0m  CC=0.0    ←0
  │ iconv.json                  39L  0C    0m  CC=0.0    ←0
  │ rm.json                     39L  0C    0m  CC=0.0    ←0
  │ open_url.json               36L  0C    0m  CC=0.0    ←0
  │ generated_kubectl_dynamic_schema.json    35L  0C    0m  CC=0.0    ←0
  │ type_text.json              35L  0C    0m  CC=0.0    ←0
  │ nslookup.json               33L  0C    0m  CC=0.0    ←0
  │ uptime.json                 29L  0C    0m  CC=0.0    ←0
  │ kubectl.json                28L  0C    0m  CC=0.0    ←0
  │ ps.json                     28L  0C    0m  CC=0.0    ←0
  │ click.json                  28L  0C    0m  CC=0.0    ←0
  │ navigate.json               27L  0C    0m  CC=0.0    ←0
  │ openssl.json                22L  0C    0m  CC=0.0    ←0
  │ traceroute.json             22L  0C    0m  CC=0.0    ←0
  │ eslint.json                 22L  0C    0m  CC=0.0    ←0
  │ psql.json                   22L  0C    0m  CC=0.0    ←0
  │ mysqldump.json              22L  0C    0m  CC=0.0    ←0
  │ mysql.json                  22L  0C    0m  CC=0.0    ←0
  │ npm.json                    22L  0C    0m  CC=0.0    ←0
  │ mongodump.json              22L  0C    0m  CC=0.0    ←0
  │ git.json                    21L  0C    0m  CC=0.0    ←0
  │ docker.json                 21L  0C    0m  CC=0.0    ←0
  │ nginx.json                  11L  0C    0m  CC=0.0    ←0
  │ docker.json                 10L  0C    0m  CC=0.0    ←0
  │
  artifacts/                      CC̄=0.0    ←in:0  →out:0
  │ !! comprehensive_test_results.json  1625L  0C    0m  CC=0.0    ←0
  │ multi_site_test_results.json   270L  0C    0m  CC=0.0    ←0
  │ enhanced_context_test_results.json   131L  0C    0m  CC=0.0    ←0
  │ web_schema_test_results.json   125L  0C    0m  CC=0.0    ←0
  │ benchmark_report.json      116L  0C    0m  CC=0.0    ←0
  │ intelligent_nlp2cmd_results.json    98L  0C    0m  CC=0.0    ←0
  │ test_results_with_llm.json    85L  0C    0m  CC=0.0    ←0
  │ test_results_no_llm.json    85L  0C    0m  CC=0.0    ←0
  │ nlp2cmd_monitoring_log.json    82L  0C    0m  CC=0.0    ←0
  │ ci_test_results.json        60L  0C    0m  CC=0.0    ←0
  │ generated_commands.txt      45L  0C    0m  CC=0.0    ←0
  │ sequential_benchmark_results.json    27L  0C    0m  CC=0.0    ←0
  │
  config/                         CC̄=0.0    ←in:0  →out:0
  │ litellm_config.yaml        440L  0C    0m  CC=0.0    ←0
  │
  benchmark_output/               CC̄=0.0    ←in:0  →out:0
  │ !! learning_benchmark.json   5388L  0C    0m  CC=0.0    ←0
  │ !! benchmark_results.json    2852L  0C    0m  CC=0.0    ←0
  │
  data/                           CC̄=0.0    ←in:0  →out:0
  │ !! phrase_database.json     771890L  0C    0m  CC=0.0    ←0
  │ !! patterns.json             2915L  0C    0m  CC=0.0    ←0
  │ !! templates.json             858L  0C    0m  CC=0.0    ←0
  │ enhanced_intents.json      218L  0C    0m  CC=0.0    ←0
  │ form_schema.json           178L  0C    0m  CC=0.0    ←0
  │ prompt.txt                 120L  0C    0m  CC=0.0    ←0
  │ enhanced_domain_patterns.json   106L  0C    0m  CC=0.0    ←0
  │ apps.yaml                   90L  0C    0m  CC=0.0    ←0
  │ domain_weights.json         59L  0C    0m  CC=0.0    ←0
  │ colors.yaml                 46L  0C    0m  CC=0.0    ←0
  │ polish_shell_patterns.json    45L  0C    0m  CC=0.0    ←0
  │ polish_table_mappings.json    42L  0C    0m  CC=0.0    ←0
  │ shapes.yaml                 38L  0C    0m  CC=0.0    ←0
  │ polish_intent_mappings.json    31L  0C    0m  CC=0.0    ←0
  │ close_app.yaml              29L  0C    0m  CC=0.0    ←0
  │ draw.yaml                   28L  0C    0m  CC=0.0    ←0
  │ open_app.yaml               27L  0C    0m  CC=0.0    ←0
  │ email_compose.yaml          26L  0C    0m  CC=0.0    ←0
  │ navigate.yaml               25L  0C    0m  CC=0.0    ←0
  │ screenshot.yaml             25L  0C    0m  CC=0.0    ←0
  │ email_check.yaml            21L  0C    0m  CC=0.0    ←0
  │ new_tab.yaml                20L  0C    0m  CC=0.0    ←0
  │ minimize_all.yaml           15L  0C    0m  CC=0.0    ←0
  │

COUPLING:
                                             test_nlp2cmd_commands      examples.04_domain_specific         examples.03_integrations              scripts.maintenance    examples.05_advanced_features                      src.nlp2cmd       examples.09_online_drawing                         examples               examples.01_basics  examples.10_online_code_editors            scripts.thermodynamic  examples.06_tools_and_utilities                     tools.schema   examples.08_api_key_management     examples.07_stream_protocols
            test_nlp2cmd_commands                               ──                             ←797                             ←793                             ←593                             ←458                             ←369                             ←377                              ←80                             ←270                             ←139                             ←159                             ←136                             ←127                             ←104                              ←90  hub
      examples.04_domain_specific                              797                               ──                                                                                                                                  11                                                                50                                                                                                 ←5                                                                                                                                      hub
         examples.03_integrations                              793                                                                ──                                                                                                 11                                                                48                                                                                                                                                                                                                                         !! fan-out
              scripts.maintenance                              593                                                                                                 ──                                                                 5                                                                                                                                                                                                                                                                                                           !! fan-out
    examples.05_advanced_features                              458                                                                                                                                  ──                               10                                                                10                                                                                                                                                                                                                                         !! fan-out
                      src.nlp2cmd                              369                              ←11                              ←11                               ←5                              ←10                               ──                                1                               ←5                               ←1                                1                               ←6                               ←1                               ←5                               ←9                               ←6  hub
       examples.09_online_drawing                              377                                                                                                                                                                   15                               ──                               20                                                                                                                                                                                                                                         !! fan-out
                         examples                               80                              ←50                              ←48                                                               ←10                                5                              ←20                               ──                              ←72                              ←72                                                                                                                                                                       hub
               examples.01_basics                              270                                                                                                                                                                    1                                                                72                               ──                                                                                                                                                                                                        !! fan-out
  examples.10_online_code_editors                              139                                                                                                                                                                    5                                                                72                                                                ──                                                                                                                                                                       !! fan-out
            scripts.thermodynamic                              159                                5                                                                                                                                   6                                                                                                                                                                   ──                                                                                                                                      !! fan-out
  examples.06_tools_and_utilities                              136                                                                                                                                                                    1                                                                                                                                                                                                    ──                                                                                                     !! fan-out
                     tools.schema                              127                                                                                                                                                                    5                                                                                                                                                                                                                                     ──                                                                    !! fan-out
   examples.08_api_key_management                              104                                                                                                                                                                    9                                                                                                                                                                                                                                                                      ──                                   !! fan-out
     examples.07_stream_protocols                               90                                                                                                                                                                    6                                                                                                                                                                                                                                                                                                       ──  !! fan-out
  CYCLES: none
  HUB: src.nlp2cmd/ (fan-in=114)
  HUB: examples.04_domain_specific/ (fan-in=5)
  HUB: test_nlp2cmd_commands/ (fan-in=4996)
  HUB: examples/ (fan-in=277)
  HUB: src.app2schema/ (fan-in=12)
  SMELL: examples.02_benchmarks/ fan-out=72 → split needed
  SMELL: scripts/ fan-out=28 → split needed
  SMELL: scripts.thermodynamic/ fan-out=170 → split needed
  SMELL: examples.08_llm_validation/ fan-out=24 → split needed
  SMELL: examples.06_desktop_automation/ fan-out=51 → split needed
  SMELL: examples.10_online_code_editors/ fan-out=216 → split needed
  SMELL: src.nlp2cmd/ fan-out=371 → split needed
  SMELL: examples.05_advanced_features/ fan-out=485 → split needed
  SMELL: examples.03_integrations/ fan-out=852 → split needed
  SMELL: tools.manual_tests/ fan-out=11 → split needed
  SMELL: examples.01_basics/ fan-out=348 → split needed
  SMELL: docker.novnc/ fan-out=30 → split needed
  SMELL: examples.08_api_key_management/ fan-out=113 → split needed
  SMELL: tools.analysis/ fan-out=77 → split needed
  SMELL: examples.04_domain_specific/ fan-out=858 → split needed
  SMELL: tools.schema/ fan-out=132 → split needed
  SMELL: examples.06_tools_and_utilities/ fan-out=137 → split needed
  SMELL: scripts.testing/ fan-out=31 → split needed
  SMELL: test_screenshots/ fan-out=62 → split needed
  SMELL: examples/ fan-out=85 → split needed
  SMELL: examples.09_online_drawing/ fan-out=412 → split needed
  SMELL: examples.07_stream_protocols/ fan-out=96 → split needed
  SMELL: benchmarks/ fan-out=85 → split needed
  SMELL: tools.generation/ fan-out=56 → split needed
  SMELL: scripts.maintenance/ fan-out=598 → split needed

EXTERNAL:
  validation: run `vallm batch .` → validation.toon
  duplication: run `redup scan .` → duplication.toon
```

### Duplication (`project/duplication.toon.yaml`)

```toon markpact:analysis path=project/duplication.toon.yaml
# redup/duplication | 152 groups | 1021f 254687L | 2026-06-06

SUMMARY:
  files_scanned: 1021
  total_lines:   254687
  dup_groups:    152
  dup_fragments: 514
  saved_lines:   5810
  scan_ms:       13975

HOTSPOTS[7] (files with most duplication):
  webops/voice_service.py  dup=752L  groups=12  frags=12  (0.3%)
  webops/docker_app.py  dup=423L  groups=7  frags=7  (0.2%)
  networkx-3.6.1-py3-none-any/networkx/drawing/nx_pylab.py  dup=295L  groups=1  frags=8  (0.1%)
  networkx-3.6.1-py3-none-any/networkx/generators/small.py  dup=204L  groups=3  frags=6  (0.1%)
  examples/03_integrations/toon_format/simple_demo.py  dup=199L  groups=3  frags=5  (0.1%)
  examples/06_tools_and_utilities/migration_tools/guide.py  dup=193L  groups=2  frags=3  (0.1%)
  networkx-3.6.1-py3-none-any/networkx/algorithms/components/connected.py  dup=183L  groups=3  frags=3  (0.1%)

DUPLICATES[152] (ranked by impact):
  [1df9ba1fb4dcca4d] !! STRU  demo_protein_folding  L=23 N=35 saved=782 sim=1.00
      examples/04_domain_specific/bioinformatics/example.py:42-64  (demo_protein_folding)
      examples/04_domain_specific/bioinformatics/example.py:87-108  (demo_proteomics_analysis)
      examples/04_domain_specific/education/example.py:43-62  (demo_exam_scheduling)
      examples/04_domain_specific/education/example.py:65-84  (demo_learning_path)
      examples/04_domain_specific/education/example.py:108-127  (demo_student_grouping)
      examples/04_domain_specific/education/example.py:130-149  (demo_resource_optimization)
      examples/04_domain_specific/education/example.py:152-171  (demo_curriculum_planning)
      examples/04_domain_specific/energy/example.py:39-59  (demo_renewable_integration)
      examples/04_domain_specific/energy/example.py:62-81  (demo_water_distribution)
      examples/04_domain_specific/energy/example.py:106-125  (demo_electric_vehicle_charging)
      examples/04_domain_specific/energy/example.py:128-147  (demo_demand_response)
      examples/04_domain_specific/energy/example.py:150-169  (demo_microgrid)
      examples/04_domain_specific/finance/example.py:61-78  (demo_trade_execution)
      examples/04_domain_specific/finance/example.py:81-101  (demo_risk_allocation)
      examples/04_domain_specific/finance/example.py:126-145  (demo_options_strategy)
      examples/04_domain_specific/finance/example.py:148-167  (demo_credit_scoring)
      examples/04_domain_specific/healthcare/example.py:39-59  (demo_nurse_scheduling)
      examples/04_domain_specific/healthcare/example.py:62-86  (demo_patient_allocation)
      examples/04_domain_specific/healthcare/example.py:112-131  (demo_ambulance_dispatch)
      examples/04_domain_specific/healthcare/example.py:134-153  (demo_icu_bed_management)
      examples/04_domain_specific/healthcare/example.py:156-175  (demo_pharmacy_inventory)
      examples/04_domain_specific/logistics/example.py:36-55  (demo_warehouse_optimization)
      examples/04_domain_specific/logistics/example.py:58-77  (demo_production_scheduling)
      examples/04_domain_specific/logistics/example.py:102-122  (demo_supply_chain_network)
      examples/04_domain_specific/logistics/example.py:125-144  (demo_cross_docking)
      examples/04_domain_specific/physics/example.py:38-57  (demo_molecular_dynamics)
      examples/04_domain_specific/physics/example.py:60-78  (demo_telescope_scheduling)
      examples/04_domain_specific/physics/example.py:103-122  (demo_climate_modeling)
      examples/04_domain_specific/physics/example.py:125-144  (demo_particle_physics)
      examples/04_domain_specific/physics/example.py:147-166  (demo_materials_science)
      examples/04_domain_specific/smart_cities/example.py:38-62  (demo_smart_grid)
      examples/04_domain_specific/smart_cities/example.py:65-85  (demo_waste_management)
      examples/04_domain_specific/smart_cities/example.py:110-129  (demo_parking_management)
      examples/04_domain_specific/smart_cities/example.py:132-151  (demo_air_quality)
      examples/04_domain_specific/smart_cities/example.py:154-173  (demo_water_management)
  [112cd8080b6675a6] !! STRU  root  L=392 N=2 saved=392 sim=1.00
      webops/docker_app.py:231-622  (root)
      webops/voice_service.py:673-1356  (root)
  [1c504824e27e993c] !! STRU  boykov_kolmogorov  L=147 N=3 saved=294 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/flow/boykovkolmogorov.py:15-161  (boykov_kolmogorov)
      networkx-3.6.1-py3-none-any/networkx/algorithms/flow/dinitz_alg.py:15-140  (dinitz)
      networkx-3.6.1-py3-none-any/networkx/algorithms/flow/edmondskarp.py:121-241  (edmonds_karp)
  [e55bbf4ddeeaeb7f] !! STRU  draw_bipartite  L=42 N=8 saved=294 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/drawing/nx_pylab.py:2548-2589  (draw_bipartite)
      networkx-3.6.1-py3-none-any/networkx/drawing/nx_pylab.py:2592-2628  (draw_circular)
      networkx-3.6.1-py3-none-any/networkx/drawing/nx_pylab.py:2631-2668  (draw_kamada_kawai)
      networkx-3.6.1-py3-none-any/networkx/drawing/nx_pylab.py:2671-2707  (draw_random)
      networkx-3.6.1-py3-none-any/networkx/drawing/nx_pylab.py:2710-2749  (draw_spectral)
      networkx-3.6.1-py3-none-any/networkx/drawing/nx_pylab.py:2752-2792  (draw_spring)
      networkx-3.6.1-py3-none-any/networkx/drawing/nx_pylab.py:2840-2881  (draw_planar)
      networkx-3.6.1-py3-none-any/networkx/drawing/nx_pylab.py:2884-2901  (draw_forceatlas2)
  [82287e07fa035376] !! STRU  demo_drug_discovery  L=20 N=8 saved=140 sim=1.00
      examples/04_domain_specific/bioinformatics/example.py:111-130  (demo_drug_discovery)
      examples/04_domain_specific/education/example.py:87-105  (demo_classroom_allocation)
      examples/04_domain_specific/energy/example.py:84-103  (demo_gas_network)
      examples/04_domain_specific/finance/example.py:104-123  (demo_arbitrage_detection)
      examples/04_domain_specific/healthcare/example.py:89-109  (demo_emergency_department)
      examples/04_domain_specific/logistics/example.py:80-99  (demo_inventory_optimization)
      examples/04_domain_specific/physics/example.py:81-100  (demo_quantum_computing)
      examples/04_domain_specific/smart_cities/example.py:88-107  (demo_public_transport)
  [b3c744b38d0610b9] !! STRU  demo_genomic_pipeline  L=23 N=7 saved=138 sim=1.00
      examples/04_domain_specific/bioinformatics/example.py:17-39  (demo_genomic_pipeline)
      examples/04_domain_specific/education/example.py:17-40  (demo_course_timetabling)
      examples/04_domain_specific/energy/example.py:17-36  (demo_unit_commitment)
      examples/04_domain_specific/healthcare/example.py:17-36  (demo_or_scheduling)
      examples/04_domain_specific/logistics/example.py:17-33  (demo_vehicle_routing)
      examples/04_domain_specific/physics/example.py:17-35  (demo_particle_collision)
      examples/04_domain_specific/smart_cities/example.py:17-35  (demo_traffic_optimization)
  [1b0b45f30d99f404] !! STRU  demo_system_monitoring  L=22 N=7 saved=132 sim=1.00
      examples/04_domain_specific/data_science/dsl_demo.py:69-90  (demo_system_monitoring)
      examples/04_domain_specific/data_science/dsl_demo.py:93-114  (demo_network_operations)
      examples/04_domain_specific/data_science/dsl_demo.py:117-138  (demo_process_management)
      examples/04_domain_specific/data_science/dsl_demo.py:141-162  (demo_development_tools)
      examples/04_domain_specific/data_science/dsl_demo.py:165-186  (demo_security_operations)
      examples/04_domain_specific/data_science/dsl_demo.py:189-210  (demo_backup_operations)
      examples/04_domain_specific/data_science/dsl_demo.py:213-234  (demo_system_maintenance)
  [710bf2d11fd81ed8] !! STRU  main  L=54 N=3 saved=108 sim=1.00
      examples/03_integrations/toon_format/11_basic_integration/demo.py:13-66  (main)
      examples/03_integrations/toon_format/12_advanced_integration/demo.py:13-70  (main)
      examples/03_integrations/toon_format/13_query_system/demo.py:13-67  (main)
  [a93cd3bc2ecf844d] !! STRU  disjoint_union  L=51 N=3 saved=102 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/operators/binary.py:84-134  (disjoint_union)
      networkx-3.6.1-py3-none-any/networkx/algorithms/operators/binary.py:138-179  (intersection)
      networkx-3.6.1-py3-none-any/networkx/algorithms/operators/binary.py:301-379  (compose)
  [3db9e6d4c43b7808] ! STRU  number_attracting_components  L=25 N=5 saved=100 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/components/attracting.py:59-83  (number_attracting_components)
      networkx-3.6.1-py3-none-any/networkx/algorithms/components/connected.py:95-149  (number_connected_components)
      networkx-3.6.1-py3-none-any/networkx/algorithms/components/strongly_connected.py:186-222  (number_strongly_connected_components)
      networkx-3.6.1-py3-none-any/networkx/algorithms/components/weakly_connected.py:72-107  (number_weakly_connected_components)
      networkx-3.6.1-py3-none-any/networkx/algorithms/isolate.py:90-107  (number_of_isolates)
  [2f1e809a98550e02] ! STRU  main  L=49 N=3 saved=98 sim=1.00
      examples/04_domain_specific/debugging/07_file_operations/demo.py:23-71  (main)
      examples/04_domain_specific/debugging/08_system_commands/demo.py:23-71  (main)
      examples/04_domain_specific/debugging/09_network_commands/demo.py:23-71  (main)
  [0a0be185aa5f0cf3] ! EXAC  run_nlp2cmd_command  L=23 N=5 saved=92 sim=1.00
      examples/10_online_code_editors/01_codepen_live_nlp2cmd.py:26-48  (run_nlp2cmd_command)
      examples/10_online_code_editors/02_mycompiler_run_nlp2cmd.py:26-48  (run_nlp2cmd_command)
      examples/10_online_code_editors/03_adaptive_code_nlp2cmd.py:26-48  (run_nlp2cmd_command)
      examples/10_online_code_editors/04_jsfiddle_frontend_nlp2cmd.py:26-48  (run_nlp2cmd_command)
      examples/10_online_code_editors/05_dynamic_executor_nlp2cmd.py:26-48  (run_nlp2cmd_command)
  [69363a05cdddbf3f] ! STRU  minimum_spanning_edges  L=91 N=2 saved=91 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/tree/mst.py:369-459  (minimum_spanning_edges)
      networkx-3.6.1-py3-none-any/networkx/algorithms/tree/mst.py:464-553  (maximum_spanning_edges)
  [29c17be98159ebe8] ! STRU  min_cost_flow_cost  L=87 N=2 saved=87 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/flow/mincost.py:13-99  (min_cost_flow_cost)
      networkx-3.6.1-py3-none-any/networkx/algorithms/flow/mincost.py:105-192  (min_cost_flow)
  [2b86977beebe7a94] ! STRU  demo_advanced_features  L=42 N=3 saved=84 sim=1.00
      examples/03_integrations/toon_format/simple_demo.py:141-182  (demo_advanced_features)
      examples/03_integrations/toon_format/simple_demo.py:185-220  (demo_performance_tips)
      examples/06_tools_and_utilities/migration_tools/guide.py:244-304  (practical_examples)
  [b2b7c14d928812b2] ! STRU  degree_centrality  L=41 N=3 saved=82 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/degree_alg.py:10-50  (degree_centrality)
      networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/degree_alg.py:55-100  (in_degree_centrality)
      networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/degree_alg.py:105-150  (out_degree_centrality)
  [e3c0147ffd6312ec] ! STRU  laplacian_spectrum  L=41 N=3 saved=82 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/linalg/spectrum.py:17-57  (laplacian_spectrum)
      networkx-3.6.1-py3-none-any/networkx/linalg/spectrum.py:61-91  (normalized_laplacian_spectrum)
      networkx-3.6.1-py3-none-any/networkx/linalg/spectrum.py:95-123  (adjacency_spectrum)
  [ce32e4979f882d23] ! EXAC  run_nlp2cmd_command  L=40 N=3 saved=80 sim=1.00
      examples/09_online_drawing/_old/01_draw_chat_shapes_nlp2cmd.py:29-68  (run_nlp2cmd_command)
      examples/09_online_drawing/_old/02_picsart_painting_nlp2cmd.py:29-68  (run_nlp2cmd_command)
      examples/09_online_drawing/_old/03_adaptive_drawing_nlp2cmd.py:29-68  (run_nlp2cmd_command)
  [b9b0699ae952c0cd] ! STRU  main  L=39 N=3 saved=78 sim=1.00
      examples/04_domain_specific/bioinformatics/02_file_processing/demo.py:22-60  (main)
      examples/04_domain_specific/bioinformatics/03_blast_operations/demo.py:22-60  (main)
      examples/04_domain_specific/bioinformatics/04_data_conversion/demo.py:22-60  (main)
  [8afbf75a9b7d7fd8] ! STRU  connected_components  L=73 N=2 saved=73 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/components/connected.py:18-90  (connected_components)
      networkx-3.6.1-py3-none-any/networkx/algorithms/components/weakly_connected.py:15-67  (weakly_connected_components)
  [eb090f013b10ef03] ! STRU  check_planarity  L=73 N=2 saved=73 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/planarity.py:43-115  (check_planarity)
      networkx-3.6.1-py3-none-any/networkx/algorithms/planarity.py:119-131  (check_planarity_recursive)
  [4160a1bbd796e065] ! STRU  old_way_examples  L=66 N=2 saved=66 sim=1.00
      examples/06_tools_and_utilities/migration_tools/guide.py:14-79  (old_way_examples)
      examples/06_tools_and_utilities/migration_tools/guide.py:82-147  (new_way_examples)
  [620a0b352d470f0a] ! STRU  diameter  L=66 N=2 saved=66 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/distance_measures.py:338-403  (diameter)
      networkx-3.6.1-py3-none-any/networkx/algorithms/distance_measures.py:554-616  (radius)
  [df1f8e9cc35ae7ff] ! STRU  _directed_neighbor_switch  L=61 N=2 saved=61 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/generators/joint_degree_seq.py:356-416  (_directed_neighbor_switch)
      networkx-3.6.1-py3-none-any/networkx/generators/joint_degree_seq.py:419-468  (_directed_neighbor_switch_rev)
  [ad6def0b915a677e] ! STRU  read_graph6  L=61 N=2 saved=61 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/readwrite/graph6.py:197-257  (read_graph6)
      networkx-3.6.1-py3-none-any/networkx/readwrite/sparse6.py:255-315  (read_sparse6)
  [d36d6de161fdcc7d] ! EXAC  __getattr__  L=4 N=16 saved=60 sim=1.00
      src/nlp2cmd/generation/allocation_energy.py:39-42  (__getattr__)
      src/nlp2cmd/generation/hybrid_thermodynamic_generator.py:39-42  (__getattr__)
      src/nlp2cmd/generation/routing_energy.py:39-42  (__getattr__)
      src/nlp2cmd/generation/scheduling_energy.py:39-42  (__getattr__)
      src/nlp2cmd/generation/thermodynamic_components.py:16-19  (__getattr__)
      src/nlp2cmd/generation/thermodynamic_generator.py:39-42  (__getattr__)
      src/nlp2cmd/thermodynamic/constraint_energy.py:25-28  (__getattr__)
      src/nlp2cmd/thermodynamic/energy_estimator.py:25-28  (__getattr__)
      src/nlp2cmd/thermodynamic/energy_model.py:25-28  (__getattr__)
      src/nlp2cmd/thermodynamic/entropy_production_regularizer.py:25-28  (__getattr__)
      src/nlp2cmd/thermodynamic/langevin_config.py:25-28  (__getattr__)
      src/nlp2cmd/thermodynamic/langevin_sampler.py:25-28  (__getattr__)
      src/nlp2cmd/thermodynamic/majority_voter.py:25-28  (__getattr__)
      src/nlp2cmd/thermodynamic/quadratic_energy.py:25-28  (__getattr__)
      src/nlp2cmd/thermodynamic/sampler_result.py:25-28  (__getattr__)
      src/nlp2cmd/thermodynamic/thermodynamic_router.py:25-28  (__getattr__)
  [0d8f0292b8cf9b8a] ! STRU  dfs_postorder_nodes  L=56 N=2 saved=56 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/depth_first_search.py:296-351  (dfs_postorder_nodes)
      networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/depth_first_search.py:355-410  (dfs_preorder_nodes)
  [5d608e257278a879] ! STRU  is_connected  L=55 N=2 saved=55 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/components/connected.py:154-208  (is_connected)
      networkx-3.6.1-py3-none-any/networkx/algorithms/components/weakly_connected.py:112-166  (is_weakly_connected)
  [9e6185e65eb251a4] ! STRU  demo_real_world_example  L=50 N=2 saved=50 sim=1.00
      examples/03_integrations/toon_format/simple_demo.py:54-103  (demo_real_world_example)
      examples/03_integrations/toon_format/simple_demo.py:106-138  (demo_integration_example)
  [aa68418ac0714704] ! STRU  cartesian_product  L=49 N=2 saved=49 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/operators/product.py:185-233  (cartesian_product)
      networkx-3.6.1-py3-none-any/networkx/algorithms/operators/product.py:237-286  (lexicographic_product)
  [68afb13c325e2389] ! STRU  write_edgelist  L=47 N=2 saved=47 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/edgelist.py:33-79  (write_edgelist)
      networkx-3.6.1-py3-none-any/networkx/readwrite/edgelist.py:127-173  (write_edgelist)
  [eaa1dfa7cff02e75] ! STRU  main  L=11 N=5 saved=44 sim=1.00
      examples/04_domain_specific/education/example.py:174-184  (main)
      examples/04_domain_specific/energy/example.py:172-182  (main)
      examples/04_domain_specific/healthcare/example.py:178-188  (main)
      examples/04_domain_specific/physics/example.py:169-179  (main)
      examples/04_domain_specific/smart_cities/example.py:176-186  (main)
  [673c8766aa8ae3e1] ! STRU  icosahedral_graph  L=43 N=2 saved=43 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/generators/small.py:556-598  (icosahedral_graph)
      networkx-3.6.1-py3-none-any/networkx/generators/small.py:746-786  (petersen_graph)
  [9de79818db2b912e] ! EXAC  array  L=4 N=11 saved=40 sim=1.00
      src/nlp2cmd/generation/thermodynamic_components.py:20-23  (array)
      src/nlp2cmd/thermodynamic/constraint_energy.py:29-32  (array)
      src/nlp2cmd/thermodynamic/energy_estimator.py:29-32  (array)
      src/nlp2cmd/thermodynamic/energy_model.py:29-32  (array)
      src/nlp2cmd/thermodynamic/entropy_production_regularizer.py:29-32  (array)
      src/nlp2cmd/thermodynamic/langevin_config.py:29-32  (array)
      src/nlp2cmd/thermodynamic/langevin_sampler.py:29-32  (array)
      src/nlp2cmd/thermodynamic/majority_voter.py:29-32  (array)
      src/nlp2cmd/thermodynamic/quadratic_energy.py:29-32  (array)
      src/nlp2cmd/thermodynamic/sampler_result.py:29-32  (array)
      src/nlp2cmd/thermodynamic/thermodynamic_router.py:29-32  (array)
  [fc1362d9959b8595] ! EXAC  zeros_like  L=4 N=11 saved=40 sim=1.00
      src/nlp2cmd/generation/thermodynamic_components.py:24-27  (zeros_like)
      src/nlp2cmd/thermodynamic/constraint_energy.py:33-36  (zeros_like)
      src/nlp2cmd/thermodynamic/energy_estimator.py:33-36  (zeros_like)
      src/nlp2cmd/thermodynamic/energy_model.py:33-36  (zeros_like)
      src/nlp2cmd/thermodynamic/entropy_production_regularizer.py:33-36  (zeros_like)
      src/nlp2cmd/thermodynamic/langevin_config.py:33-36  (zeros_like)
      src/nlp2cmd/thermodynamic/langevin_sampler.py:33-36  (zeros_like)
      src/nlp2cmd/thermodynamic/majority_voter.py:33-36  (zeros_like)
      src/nlp2cmd/thermodynamic/quadratic_energy.py:33-36  (zeros_like)
      src/nlp2cmd/thermodynamic/sampler_result.py:33-36  (zeros_like)
      src/nlp2cmd/thermodynamic/thermodynamic_router.py:33-36  (zeros_like)
  [61f4431993447d69] ! EXAC  sum  L=4 N=11 saved=40 sim=1.00
      src/nlp2cmd/generation/thermodynamic_components.py:36-39  (sum)
      src/nlp2cmd/thermodynamic/constraint_energy.py:37-40  (sum)
      src/nlp2cmd/thermodynamic/energy_estimator.py:37-40  (sum)
      src/nlp2cmd/thermodynamic/energy_model.py:37-40  (sum)
      src/nlp2cmd/thermodynamic/entropy_production_regularizer.py:37-40  (sum)
      src/nlp2cmd/thermodynamic/langevin_config.py:37-40  (sum)
      src/nlp2cmd/thermodynamic/langevin_sampler.py:37-40  (sum)
      src/nlp2cmd/thermodynamic/majority_voter.py:37-40  (sum)
      src/nlp2cmd/thermodynamic/quadratic_energy.py:37-40  (sum)
      src/nlp2cmd/thermodynamic/sampler_result.py:37-40  (sum)
      src/nlp2cmd/thermodynamic/thermodynamic_router.py:37-40  (sum)
  [52015e90877b1e7a] ! EXAC  exp  L=4 N=11 saved=40 sim=1.00
      src/nlp2cmd/generation/thermodynamic_components.py:40-43  (exp)
      src/nlp2cmd/thermodynamic/constraint_energy.py:41-44  (exp)
      src/nlp2cmd/thermodynamic/energy_estimator.py:41-44  (exp)
      src/nlp2cmd/thermodynamic/energy_model.py:41-44  (exp)
      src/nlp2cmd/thermodynamic/entropy_production_regularizer.py:41-44  (exp)
      src/nlp2cmd/thermodynamic/langevin_config.py:41-44  (exp)
      src/nlp2cmd/thermodynamic/langevin_sampler.py:41-44  (exp)
      src/nlp2cmd/thermodynamic/majority_voter.py:41-44  (exp)
      src/nlp2cmd/thermodynamic/quadratic_energy.py:41-44  (exp)
      src/nlp2cmd/thermodynamic/sampler_result.py:41-44  (exp)
      src/nlp2cmd/thermodynamic/thermodynamic_router.py:41-44  (exp)
  [51e8b7bfd786bfb1] ! STRU  demo_basic_usage  L=38 N=2 saved=38 sim=1.00
      examples/03_integrations/toon_format/simple_demo.py:14-51  (demo_basic_usage)
      examples/04_domain_specific/bioinformatics/complete_examples.py:196-231  (demo_advanced_features)
  [5c86bc69bff822b5] ! EXAC  random  L=4 N=10 saved=36 sim=1.00
      src/nlp2cmd/thermodynamic/constraint_energy.py:45-48  (random)
      src/nlp2cmd/thermodynamic/energy_estimator.py:45-48  (random)
      src/nlp2cmd/thermodynamic/energy_model.py:45-48  (random)
      src/nlp2cmd/thermodynamic/entropy_production_regularizer.py:45-48  (random)
      src/nlp2cmd/thermodynamic/langevin_config.py:45-48  (random)
      src/nlp2cmd/thermodynamic/langevin_sampler.py:45-48  (random)
      src/nlp2cmd/thermodynamic/majority_voter.py:45-48  (random)
      src/nlp2cmd/thermodynamic/quadratic_energy.py:45-48  (random)
      src/nlp2cmd/thermodynamic/sampler_result.py:45-48  (random)
      src/nlp2cmd/thermodynamic/thermodynamic_router.py:45-48  (random)
  [29f7f2eee2f6824a] ! EXAC  sqrt  L=4 N=10 saved=36 sim=1.00
      src/nlp2cmd/thermodynamic/constraint_energy.py:49-52  (sqrt)
      src/nlp2cmd/thermodynamic/energy_estimator.py:49-52  (sqrt)
      src/nlp2cmd/thermodynamic/energy_model.py:49-52  (sqrt)
      src/nlp2cmd/thermodynamic/entropy_production_regularizer.py:49-52  (sqrt)
      src/nlp2cmd/thermodynamic/langevin_config.py:49-52  (sqrt)
      src/nlp2cmd/thermodynamic/langevin_sampler.py:49-52  (sqrt)
      src/nlp2cmd/thermodynamic/majority_voter.py:49-52  (sqrt)
      src/nlp2cmd/thermodynamic/quadratic_energy.py:49-52  (sqrt)
      src/nlp2cmd/thermodynamic/sampler_result.py:49-52  (sqrt)
      src/nlp2cmd/thermodynamic/thermodynamic_router.py:49-52  (sqrt)
  [1f6fc7e4f3653581] ! EXAC  mean  L=4 N=10 saved=36 sim=1.00
      src/nlp2cmd/thermodynamic/constraint_energy.py:53-56  (mean)
      src/nlp2cmd/thermodynamic/energy_estimator.py:53-56  (mean)
      src/nlp2cmd/thermodynamic/energy_model.py:53-56  (mean)
      src/nlp2cmd/thermodynamic/entropy_production_regularizer.py:53-56  (mean)
      src/nlp2cmd/thermodynamic/langevin_config.py:53-56  (mean)
      src/nlp2cmd/thermodynamic/langevin_sampler.py:53-56  (mean)
      src/nlp2cmd/thermodynamic/majority_voter.py:53-56  (mean)
      src/nlp2cmd/thermodynamic/quadratic_energy.py:53-56  (mean)
      src/nlp2cmd/thermodynamic/sampler_result.py:53-56  (mean)
      src/nlp2cmd/thermodynamic/thermodynamic_router.py:53-56  (mean)
  [6ab3c0a4a1c988eb] ! EXAC  std  L=4 N=10 saved=36 sim=1.00
      src/nlp2cmd/thermodynamic/constraint_energy.py:57-60  (std)
      src/nlp2cmd/thermodynamic/energy_estimator.py:57-60  (std)
      src/nlp2cmd/thermodynamic/energy_model.py:57-60  (std)
      src/nlp2cmd/thermodynamic/entropy_production_regularizer.py:57-60  (std)
      src/nlp2cmd/thermodynamic/langevin_config.py:57-60  (std)
      src/nlp2cmd/thermodynamic/langevin_sampler.py:57-60  (std)
      src/nlp2cmd/thermodynamic/majority_voter.py:57-60  (std)
      src/nlp2cmd/thermodynamic/quadratic_energy.py:57-60  (std)
      src/nlp2cmd/thermodynamic/sampler_result.py:57-60  (std)
      src/nlp2cmd/thermodynamic/thermodynamic_router.py:57-60  (std)
  [f7c0a84881945cce] ! STRU  get_counterexample  L=36 N=2 saved=36 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/planarity.py:135-170  (get_counterexample)
      networkx-3.6.1-py3-none-any/networkx/algorithms/planarity.py:174-193  (get_counterexample_recursive)
  [88af0eaa860c609f] ! STRU  is_arborescence  L=36 N=2 saved=36 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/tree/recognition.py:83-118  (is_arborescence)
      networkx-3.6.1-py3-none-any/networkx/algorithms/tree/recognition.py:123-158  (is_branching)
  [16897491a14d9018] ! STRU  get_password_store  L=6 N=7 saved=36 sim=1.00
      src/nlp2cmd/automation/password_store.py:31-36  (get_password_store)
      src/nlp2cmd/cli/syntax_cache.py:81-86  (get_syntax_cache)
      src/nlp2cmd/exploration/resource_discovery.py:484-489  (get_resource_discovery_manager)
      src/nlp2cmd/generation/enhanced_context.py:565-570  (get_enhanced_detector)
      src/nlp2cmd/generation/multi_command.py:157-162  (get_multi_command_detector)
      src/nlp2cmd/history/tracker.py:309-314  (get_global_history)
      src/nlp2cmd/registry/get_registry.py:14-19  (get_registry)
  [b0271334264e46eb] ! EXAC  get_workspace  L=5 N=8 saved=35 sim=1.00
      src/nlp2cmd/orchestration/function_cache.py:44-48  (get_workspace)
      src/nlp2cmd/orchestration/generated_function.py:44-48  (get_workspace)
      src/nlp2cmd/orchestration/learned_path.py:44-48  (get_workspace)
      src/nlp2cmd/orchestration/metrics.py:21-25  (get_workspace)
      src/nlp2cmd/orchestration/metrics_collector.py:44-48  (get_workspace)
      src/nlp2cmd/orchestration/path_optimizer.py:44-48  (get_workspace)
      src/nlp2cmd/orchestration/step_metric.py:44-48  (get_workspace)
      src/nlp2cmd/orchestration/task_metric.py:46-50  (get_workspace)
  [02f5ba69c51d6a75] ! STRU  treewidth_min_fill_in  L=17 N=3 saved=34 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/treewidth.py:69-85  (treewidth_min_fill_in)
      networkx-3.6.1-py3-none-any/networkx/utils/decorators.py:264-308  (np_random_state)
      networkx-3.6.1-py3-none-any/networkx/utils/decorators.py:311-368  (py_random_state)
  [21433200b4211b8f] ! STRU  main  L=34 N=2 saved=34 sim=1.00
      scripts/maintenance/apply_polish_integration.py:87-120  (main)
      scripts/maintenance/restore_system.py:78-111  (main)
  [1f6b8235a9a531cf] ! STRU  execute  L=33 N=2 saved=33 sim=1.00
      src/nlp2cmd/step_handlers/click_canvas_handler.py:16-48  (execute)
      src/nlp2cmd/step_handlers/fill_at_handler.py:16-48  (execute)
  [a293571d196cf55f] ! STRU  heawood_graph  L=31 N=2 saved=31 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/generators/small.py:417-447  (heawood_graph)
      networkx-3.6.1-py3-none-any/networkx/generators/small.py:653-678  (moebius_kantor_graph)
  [11df0389e3127f5e] ! STRU  _timed_default_yes  L=31 N=2 saved=31 sim=1.00
      src/nlp2cmd/cli/helpers.py:80-110  (_timed_default_yes)
      src/nlp2cmd/cli/helpers.py:113-143  (_timed_default_no)
  [a9144ffee9ec19c8]   EXAC  _get_jellyfish  L=10 N=4 saved=30 sim=1.00
      src/nlp2cmd/generation/fuzzy_schema_matcher_class.py:29-38  (_get_jellyfish)
      src/nlp2cmd/generation/fuzzy_schema_matcher_config.py:29-38  (_get_jellyfish)
      src/nlp2cmd/generation/match_result.py:29-38  (_get_jellyfish)
      src/nlp2cmd/generation/phrase_schema.py:29-38  (_get_jellyfish)
  [6d1a103988c05704]   EXAC  _get_rapidfuzz  L=10 N=4 saved=30 sim=1.00
      src/nlp2cmd/generation/fuzzy_schema_matcher_class.py:41-50  (_get_rapidfuzz)
      src/nlp2cmd/generation/fuzzy_schema_matcher_config.py:41-50  (_get_rapidfuzz)
      src/nlp2cmd/generation/match_result.py:41-50  (_get_rapidfuzz)
      src/nlp2cmd/generation/phrase_schema.py:41-50  (_get_rapidfuzz)
  [90ef05c375c46b2e]   STRU  graph_could_be_isomorphic  L=15 N=3 saved=30 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/isomorph.py:106-120  (graph_could_be_isomorphic)
      networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/isomorph.py:161-175  (fast_graph_could_be_isomorphic)
      networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/isomorph.py:208-222  (faster_graph_could_be_isomorphic)
  [0af3e255dbc233f6]   EXAC  gradient  L=14 N=3 saved=28 sim=1.00
      src/nlp2cmd/thermodynamic/allocation_energy.py:124-137  (gradient)
      src/nlp2cmd/thermodynamic/csp_energy.py:59-72  (gradient)
      src/nlp2cmd/thermodynamic/routing_energy.py:97-110  (gradient)
  [3f2b096cdec56651]   EXAC  _get_man_page  L=14 N=3 saved=28 sim=1.00
      tools/schema/comprehensive_command_scanner.py:523-536  (_get_man_page)
      tools/schema/enhanced_schema_generator.py:278-292  (_get_man_page)
      tools/schema/non_llm_schema_extractor.py:363-376  (_get_man_page)
  [2daba0c9d42d48bb]   STRU  house_graph  L=27 N=2 saved=27 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/generators/small.py:495-521  (house_graph)
      networkx-3.6.1-py3-none-any/networkx/generators/small.py:683-718  (octahedral_graph)
  [bc12f1fb2d8000f0]   EXAC  _get_router  L=6 N=5 saved=24 sim=1.00
      src/nlp2cmd/skills/drawing/draw_navigation_skill.py:50-55  (_get_router)
      src/nlp2cmd/skills/drawing/draw_object.py:133-137  (_get_router)
      src/nlp2cmd/skills/drawing/draw_validation_skill.py:64-68  (_get_router)
      src/nlp2cmd/skills/drawing/text_to_shape.py:211-216  (_get_router)
      src/nlp2cmd/skills/drawing/visual_validator.py:139-144  (_get_router)
  [f190b38051ddf0ce]   STRU  run_flow  L=24 N=2 saved=24 sim=1.00
      examples/08_api_key_management/03_github_token/run.py:60-83  (run_flow)
      examples/08_api_key_management/04_huggingface_token/run.py:67-90  (run_flow)
  [cd16ca256d13a504]   STRU  main  L=12 N=3 saved=24 sim=1.00
      examples/08_api_key_management/03_github_token/run.py:86-97  (main)
      examples/08_api_key_management/04_huggingface_token/run.py:93-104  (main)
      examples/08_api_key_management/05_openai_key/run.py:78-89  (main)
  [7978f911b308f197]   STRU  read_leda  L=24 N=2 saved=24 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/readwrite/leda.py:23-46  (read_leda)
      networkx-3.6.1-py3-none-any/networkx/readwrite/p2g.py:64-84  (read_p2g)
  [7d7458ce4574c173]   STRU  is_bipartite  L=23 N=2 saved=23 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/basic.py:88-110  (is_bipartite)
      networkx-3.6.1-py3-none-any/networkx/algorithms/distance_regular.py:25-69  (is_distance_regular)
  [ef09a568bbcd25f4]   EXAC  run_nlp2cmd_command  L=22 N=2 saved=22 sim=1.00
      examples/01_basics/docker_basics/01_basics_docker_nlp2cmd.py:25-46  (run_nlp2cmd_command)
      examples/08_api_key_management/01_diagnose_credentials_nlp2cmd.py:26-47  (run_nlp2cmd_command)
  [fb7562197a68a2a1]   EXAC  _load_known_services  L=22 N=2 saved=22 sim=1.00
      src/nlp2cmd/automation/action_planner.py:348-369  (_load_known_services)
      src/nlp2cmd/automation/service_configs.py:297-318  (_load_known_services)
  [2b82c2c849cc5150]   STRU  apply_to_keywords_py  L=22 N=2 saved=22 sim=1.00
      scripts/maintenance/apply_refactors_to_source.py:14-35  (apply_to_keywords_py)
      scripts/maintenance/apply_refactors_to_source.py:38-57  (apply_to_templates_py)
  [c075f03586e2fac1]   EXAC  _can_use_desktop_automation  L=21 N=2 saved=21 sim=1.00
      src/nlp2cmd/automation/action_planner.py:442-462  (_can_use_desktop_automation)
      src/nlp2cmd/automation/service_configs.py:374-394  (_can_use_desktop_automation)
  [ea4b17147cce5af3]   STRU  load_polish_patterns  L=7 N=4 saved=21 sim=1.00
      scripts/maintenance/apply_nlp2cmd_fixes.py:11-17  (load_polish_patterns)
      scripts/maintenance/apply_nlp2cmd_fixes.py:19-25  (load_intent_mappings)
      scripts/maintenance/apply_nlp2cmd_fixes.py:27-33  (load_table_mappings)
      scripts/maintenance/apply_nlp2cmd_fixes.py:35-41  (load_domain_weights)
  [88cbcc9b5e080a67]   STRU  _debug  L=3 N=8 saved=21 sim=1.00
      src/nlp2cmd/adapters/canvas_adapter.py:31-33  (_debug)
      src/nlp2cmd/adapters/desktop.py:43-45  (_debug)
      src/nlp2cmd/automation/captcha_solver.py:25-27  (_debug)
      src/nlp2cmd/automation/complex_planner.py:26-28  (_debug)
      src/nlp2cmd/llm/openrouter.py:26-28  (_debug)
      src/nlp2cmd/llm/repair.py:32-34  (_debug)
      src/nlp2cmd/llm/validator.py:31-33  (_debug)
      src/nlp2cmd/llm/vision.py:25-27  (_debug)
  [ab21db35adb81d05]   STRU  get_pattern_analysis_info  L=20 N=2 saved=20 sim=1.00
      examples/09_online_drawing/_old/02_picsart_painting_nlp2cmd.py:80-99  (get_pattern_analysis_info)
      examples/09_online_drawing/_old/03_adaptive_drawing_nlp2cmd.py:80-92  (get_color_analysis_info)
  [d18b4f96cb2d0824]   STRU  main  L=20 N=2 saved=20 sim=1.00
      examples/10_online_code_editors/03_adaptive_code_nlp2cmd.py:51-70  (main)
      examples/10_online_code_editors/05_dynamic_executor_nlp2cmd.py:51-70  (main)
  [90e2270aaebe6d90]   EXAC  _detect_category  L=19 N=2 saved=19 sim=1.00
      tools/schema/comprehensive_command_scanner.py:563-581  (_detect_category)
      tools/schema/non_llm_schema_extractor.py:464-482  (_detect_category)
  [471f2dae375ec1d4]   EXAC  print  L=6 N=4 saved=18 sim=1.00
      src/nlp2cmd/cli/cache.py:49-54  (print)
      src/nlp2cmd/cli/history.py:37-42  (print)
      src/nlp2cmd/cli/web_schema.py:41-46  (print)
      src/nlp2cmd/execution/runner.py:30-35  (print)
  [2b2491568e1b9fda]   EXAC  _parse_man_sections  L=18 N=2 saved=18 sim=1.00
      tools/schema/enhanced_schema_generator.py:683-700  (_parse_man_sections)
      tools/schema/non_llm_schema_extractor.py:484-502  (_parse_man_sections)
  [ebf199e4c2d565bb]   STRU  nodes  L=6 N=4 saved=18 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/classes/function.py:53-58  (nodes)
      networkx-3.6.1-py3-none-any/networkx/classes/function.py:90-95  (number_of_nodes)
      networkx-3.6.1-py3-none-any/networkx/classes/function.py:98-103  (number_of_edges)
      networkx-3.6.1-py3-none-any/networkx/classes/function.py:164-166  (is_directed)
  [92d06ddb16034a0d]   STRU  _directed_edges_cross_edges  L=17 N=2 saved=17 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/operators/product.py:33-49  (_directed_edges_cross_edges)
      networkx-3.6.1-py3-none-any/networkx/algorithms/operators/product.py:52-68  (_undirected_edges_cross_edges)
  [8d518a81e0d421b5]   EXAC  fetch_only  L=16 N=2 saved=16 sim=1.00
      examples/09_online_drawing/05_autonomous/run.py:189-204  (fetch_only)
      examples/09_online_drawing/_old/05_autonomous_drawing.py:228-243  (fetch_only)
  [bd456dfe142de551]   STRU  main  L=16 N=2 saved=16 sim=1.00
      examples/05_advanced_features/dynamic_schemas/demo_version_detection.py:158-173  (main)
      examples/05_advanced_features/dynamic_schemas/schema_flow_demo.py:167-190  (main)
  [79a0f39547bdbf81]   EXAC  _get_help_text  L=15 N=2 saved=15 sim=1.00
      tools/schema/comprehensive_command_scanner.py:507-521  (_get_help_text)
      tools/schema/non_llm_schema_extractor.py:347-361  (_get_help_text)
  [5b149e8173382290]   STRU  validate_syntax  L=14 N=2 saved=14 sim=1.00
      src/nlp2cmd/adapters/canvas_adapter.py:416-429  (validate_syntax)
      src/nlp2cmd/adapters/desktop.py:633-646  (validate_syntax)
  [559993757886a72a]   STRU  register_action  L=13 N=2 saved=13 sim=1.00
      src/nlp2cmd/dom_actions/registry.py:57-69  (register_action)
      src/nlp2cmd/step_handlers/registry.py:132-144  (register_handler)
  [0ebb90d82bc4ed63]   EXAC  _print  L=6 N=3 saved=12 sim=1.00
      src/nlp2cmd/cli/auto_repair.py:74-79  (_print)
      src/nlp2cmd/cli/commands/doctor.py:85-90  (_print)
      src/nlp2cmd/cli/commands/examples.py:170-175  (_print)
  [fbbb087ae2aba8ec]   EXAC  process_voice_command  L=12 N=2 saved=12 sim=1.00
      webops/voice_service.py:1370-1381  (process_voice_command)
      webops/voice_service_clean.py:455-466  (process_voice_command)
  [bc77a55901099f59]   STRU  get_vector_store  L=6 N=3 saved=12 sim=1.00
      src/nlp2cmd/automation/vector_store.py:252-257  (get_vector_store)
      src/nlp2cmd/nlp/config.py:213-218  (get_service_registry)
      src/nlp2cmd/nlp/config.py:221-226  (get_intent_registry)
  [f1becd20ea4ca80f]   STRU  _debug  L=3 N=5 saved=12 sim=1.00
      src/nlp2cmd/llm/adaptive_learner_class.py:39-41  (_debug)
      src/nlp2cmd/llm/error_pattern.py:39-41  (_debug)
      src/nlp2cmd/llm/learned_rule.py:39-41  (_debug)
      src/nlp2cmd/llm/model_performance.py:39-41  (_debug)
      src/nlp2cmd/llm/router.py:44-46  (_debug)
  [433f8eabcdeb8820]   STRU  __init__  L=6 N=3 saved=12 sim=1.00
      webops/voice_service.py:322-327  (__init__)
      webops/voice_service_clean.py:356-361  (__init__)
      webops/voice_service_clean.py:211-216  (__init__)
  [494e1157c35bf331]   STRU  get_command_for_task  L=11 N=2 saved=11 sim=1.00
      examples/01_basics/docker_basics/01_basics_docker_nlp2cmd.py:49-59  (get_command_for_task)
      examples/01_basics/shell_fundamentals/01_basics_shell_nlp2cmd.py:65-75  (get_command_for_task)
  [61a23712544e7e88]   STRU  strategy_connected_sequential_bfs  L=11 N=2 saved=11 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/coloring/greedy_coloring.py:146-156  (strategy_connected_sequential_bfs)
      networkx-3.6.1-py3-none-any/networkx/algorithms/coloring/greedy_coloring.py:159-169  (strategy_connected_sequential_dfs)
  [c7ceae55c1282249]   STRU  _csr_gen_triples  L=11 N=2 saved=11 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/convert_matrix.py:715-725  (_csr_gen_triples)
      networkx-3.6.1-py3-none-any/networkx/convert_matrix.py:728-738  (_csc_gen_triples)
  [2a0afb05f246de10]   EXAC  _print  L=5 N=3 saved=10 sim=1.00
      src/nlp2cmd/evolutionary/engine.py:36-40  (_print)
      src/nlp2cmd/evolutionary/planner.py:35-39  (_print)
      src/nlp2cmd/evolutionary/runner.py:32-36  (_print)
  [faa9dfe20c6d39a4]   STRU  main  L=10 N=2 saved=10 sim=1.00
      examples/04_domain_specific/finance/example.py:170-179  (main)
      examples/04_domain_specific/logistics/example.py:147-156  (main)
  [148f89b67fed8b1f]   STRU  extract_command  L=10 N=2 saved=10 sim=1.00
      src/nlp2cmd/generation/llm_simple.py:337-346  (extract_command)
      src/nlp2cmd/generation/llm_simple.py:368-377  (extract_command)
  [9643d7686903e0a2]   EXAC  websocket_endpoint  L=9 N=2 saved=9 sim=1.00
      webops/docker_app.py:641-649  (websocket_endpoint)
      webops/voice_service.py:1385-1393  (websocket_endpoint)
  [66d9fac0233fe4f9]   EXAC  __init__  L=9 N=2 saved=9 sim=1.00
      webops/voice_service_clean.py:342-350  (__init__)
      webops/voice_service_clean.py:186-194  (__init__)
  [fd19ace052dac285]   STRU  print_rule  L=9 N=2 saved=9 sim=1.00
      examples/04_domain_specific/_demo_helpers.py:21-29  (print_rule)
      examples/_example_helpers.py:16-24  (print_rule)
  [21eb3398cdd6a2b6]   STRU  display_success  L=3 N=4 saved=9 sim=1.00
      src/nlp2cmd/cli/display.py:109-111  (display_success)
      src/nlp2cmd/cli/display.py:114-116  (display_error)
      src/nlp2cmd/cli/display.py:119-121  (display_warning)
      src/nlp2cmd/cli/display.py:124-126  (display_debug)
  [b6dd50da350f9f35]   STRU  _check_msgpack  L=9 N=2 saved=9 sim=1.00
      src/nlp2cmd/generation/data_loader.py:29-37  (_check_msgpack)
      src/nlp2cmd/generation/ml_intent_classifier.py:36-44  (_check_spacy)
  [980223efbab8c5e4]   STRU  _check_torch  L=9 N=2 saved=9 sim=1.00
      src/nlp2cmd/generation/semantic_matcher_optimized.py:81-89  (_check_torch)
      src/nlp2cmd/generation/semantic_matcher_optimized.py:92-100  (_check_ctranslate2)
  [17b281cb9a404c9d]   EXAC  add_prefix  L=8 N=2 saved=8 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/operators/all.py:72-79  (add_prefix)
      networkx-3.6.1-py3-none-any/networkx/algorithms/operators/binary.py:448-455  (add_prefix)
  [5139510199ae0201]   EXAC  __len__  L=8 N=2 saved=8 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/classes/coreviews.py:284-291  (__len__)
      networkx-3.6.1-py3-none-any/networkx/classes/coreviews.py:333-340  (__len__)
  [3cc9f1b239a0b2f4]   EXAC  __iter__  L=8 N=2 saved=8 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/classes/coreviews.py:293-300  (__iter__)
      networkx-3.6.1-py3-none-any/networkx/classes/coreviews.py:342-349  (__iter__)
  [64468f9d1a95d274]   EXAC  __setstate__  L=4 N=3 saved=8 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/classes/reportviews.py:1056-1059  (__setstate__)
      networkx-3.6.1-py3-none-any/networkx/classes/reportviews.py:1296-1299  (__setstate__)
      networkx-3.6.1-py3-none-any/networkx/classes/reportviews.py:1408-1411  (__setstate__)
  [7836895cc148b6bb]   EXAC  group  L=4 N=3 saved=8 sim=1.00
      src/nlp2cmd/cli/cache.py:18-21  (group)
      src/nlp2cmd/cli/history.py:11-14  (group)
      src/nlp2cmd/cli/web_schema.py:18-21  (group)
  [b4479793d2732e64]   EXAC  option  L=4 N=3 saved=8 sim=1.00
      src/nlp2cmd/cli/cache.py:22-25  (option)
      src/nlp2cmd/cli/history.py:19-22  (option)
      src/nlp2cmd/cli/web_schema.py:26-29  (option)
  [0338c4ee243f92b4]   EXAC  argument  L=4 N=3 saved=8 sim=1.00
      src/nlp2cmd/cli/cache.py:26-29  (argument)
      src/nlp2cmd/cli/history.py:23-26  (argument)
      src/nlp2cmd/cli/web_schema.py:22-25  (argument)
  [e54f5fb596751f6a]   EXAC  command  L=4 N=3 saved=8 sim=1.00
      src/nlp2cmd/cli/cache.py:14-17  (command)
      src/nlp2cmd/cli/history.py:15-18  (command)
      src/nlp2cmd/cli/web_schema.py:14-17  (command)
  [95872a7c751eb3f8]   EXAC  _extract_description  L=8 N=2 saved=8 sim=1.00
      tools/schema/comprehensive_command_scanner.py:554-561  (_extract_description)
      tools/schema/enhanced_schema_generator.py:637-643  (_extract_description)
  [bf0f753724593dd1]   EXAC  broadcast_log  L=8 N=2 saved=8 sim=1.00
      webops/docker_app.py:143-150  (broadcast_log)
      webops/voice_service.py:455-462  (broadcast_log)
  [d12f1103f2fe5e45]   STRU  to_directed  L=8 N=2 saved=8 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/classes/function.py:527-534  (to_directed)
      networkx-3.6.1-py3-none-any/networkx/classes/function.py:537-544  (to_undirected)
  [79ef72e13c419ad4]   STRU  null_graph  L=8 N=2 saved=8 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/generators/classic.py:754-761  (null_graph)
      networkx-3.6.1-py3-none-any/networkx/generators/classic.py:917-926  (trivial_graph)
  [8b433b1655732ba8]   STRU  _debug  L=4 N=3 saved=8 sim=1.00
      src/nlp2cmd/adapters/browser.py:18-21  (_debug)
      src/nlp2cmd/utils/debug_helpers.py:14-17  (_debug)
      src/nlp2cmd/web_schema/site_explorer.py:35-38  (_debug)
  [0822beaafe87a9b3]   STRU  get_cache_stats  L=4 N=3 saved=8 sim=1.00
      src/nlp2cmd/cli/syntax_cache.py:112-115  (get_cache_stats)
      src/nlp2cmd/core/toon_integration.py:210-213  (load_command_schemas)
      src/nlp2cmd/core/toon_integration.py:220-223  (get_project_info)
  [6bab693518695269]   STRU  execution_record_enabled  L=4 N=3 saved=8 sim=1.00
      src/nlp2cmd/plan_execution/execution_record.py:54-57  (execution_record_enabled)
      src/nlp2cmd/post_execution/checker.py:11-17  (post_check_enabled)
      src/nlp2cmd/post_execution/checker.py:20-26  (post_check_strict)
  [be10847759ce69a6]   EXAC  filter_iter  L=7 N=2 saved=7 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py:681-687  (filter_iter)
      networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py:859-865  (filter_iter)
  [f2b7b3b0d53b9304]   EXAC  filter_pred_iter  L=7 N=2 saved=7 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py:696-702  (filter_pred_iter)
      networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py:874-880  (filter_pred_iter)
  [69caabac4953f8d1]   EXAC  filter_succ_iter  L=7 N=2 saved=7 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py:704-710  (filter_succ_iter)
      networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py:882-888  (filter_succ_iter)
  [3af2ab21146e21ca]   EXAC  filter_iter  L=7 N=2 saved=7 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py:717-723  (filter_iter)
      networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py:895-901  (filter_iter)
  [733b76ad9c8c608d]   EXAC  _normalize_url  L=7 N=2 saved=7 sim=1.00
      src/nlp2cmd/page_analysis/link_extractor.py:85-91  (_normalize_url)
      src/nlp2cmd/web_schema/site_explorer.py:1321-1327  (_normalize_url)
  [1614e79077ff30ae]   EXAC  health_check  L=7 N=2 saved=7 sim=1.00
      webops/voice_service.py:1360-1366  (health_check)
      webops/voice_service_clean.py:445-451  (health_check)
  [2fd4e308ca3700b3]   STRU  extract_from_file  L=7 N=2 saved=7 sim=1.00
      src/nlp2cmd/schema_extraction/script_extractors.py:39-45  (extract_from_file)
      src/nlp2cmd/schema_extraction/script_extractors.py:180-186  (extract_from_file)
  [7b4642e397e32b82]   EXAC  _parse_json  L=3 N=3 saved=6 sim=1.00
      src/nlp2cmd/skills/drawing/draw_navigation_skill.py:455-457  (_parse_json)
      src/nlp2cmd/skills/drawing/draw_object.py:368-370  (_parse_json)
      src/nlp2cmd/skills/drawing/draw_validation_skill.py:392-394  (_parse_json)
  [c7e92d7e2b0453f8]   EXAC  __init__  L=6 N=2 saved=6 sim=1.00
      webops/voice_service.py:311-316  (__init__)
      webops/voice_service_clean.py:200-205  (__init__)
  [009a51e82b6a8b4d]   EXAC  __init__  L=6 N=2 saved=6 sim=1.00
      webops/voice_service.py:332-337  (__init__)
      webops/voice_service_clean.py:221-226  (__init__)
  [f670616153e60d95]   STRU  neighbors  L=6 N=2 saved=6 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/classes/function.py:82-87  (neighbors)
      networkx-3.6.1-py3-none-any/networkx/classes/function.py:343-363  (subgraph)
  [aaae754bdb04529d]   STRU  cache_group  L=3 N=3 saved=6 sim=1.00
      src/nlp2cmd/cli/cache.py:99-101  (cache_group)
      src/nlp2cmd/cli/history.py:58-60  (history_group)
      src/nlp2cmd/cli/web_schema.py:59-61  (web_schema_group)
  [08f6dae0c39f9f1c]   STRU  get_monitor  L=3 N=3 saved=6 sim=1.00
      src/nlp2cmd/monitoring/resources.py:145-147  (get_monitor)
      webops/docker_app.py:652-654  (create_voice_app)
      webops/voice_service.py:1396-1398  (create_webops_voice_app)
  [16424173d363eab4]   EXAC  edges_from  L=5 N=2 saved=5 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/edgebfs.py:144-148  (edges_from)
      networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/edgedfs.py:130-134  (edges_from)
  [64c2035a419a4646]   EXAC  module_filename  L=5 N=2 saved=5 sim=1.00
      scripts/maintenance/split_god_modules.py:94-98  (module_filename)
      scripts/maintenance/split_web_controller.py:23-27  (module_filename)
  [0e3a17eea133c3d6]   EXAC  print_yaml_block  L=5 N=2 saved=5 sim=1.00
      src/nlp2cmd/cli/helpers.py:58-62  (print_yaml_block)
      src/nlp2cmd/context/disambiguator.py:20-24  (print_yaml_block)
  [2ae96377dcd09c8f]   EXAC  print_section  L=4 N=2 saved=4 sim=1.00
      examples/01_basics/sql_basics/workflows.py:24-27  (print_section)
      examples/03_integrations/validation/config_validation.py:25-28  (print_section)
  [3782e77d6eba0c79]   EXAC  iterate  L=4 N=2 saved=4 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py:682-685  (iterate)
      networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py:860-863  (iterate)
  [7da123d27d6b98c1]   EXAC  iterate  L=4 N=2 saved=4 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py:697-700  (iterate)
      networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py:875-878  (iterate)
  [38aabf05f330af6e]   EXAC  iterate  L=4 N=2 saved=4 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py:705-708  (iterate)
      networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py:883-886  (iterate)
  [9929c053983f01e6]   EXAC  iterate  L=4 N=2 saved=4 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py:718-721  (iterate)
      networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py:896-899  (iterate)
  [de94fcb9594ebaf7]   EXAC  __init__  L=4 N=2 saved=4 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/classes/reportviews.py:1303-1306  (__init__)
      networkx-3.6.1-py3-none-any/networkx/classes/reportviews.py:1415-1418  (__init__)
  [a89a01721cf02649]   EXAC  connect  L=4 N=2 saved=4 sim=1.00
      webops/docker_app.py:133-136  (connect)
      webops/voice_service.py:445-448  (connect)
  [31a489a088ce93a5]   EXAC  disconnect  L=4 N=2 saved=4 sim=1.00
      webops/docker_app.py:138-141  (disconnect)
      webops/voice_service.py:450-453  (disconnect)
  [8f810e17d2ec77e6]   EXAC  edge_id  L=3 N=2 saved=3 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/edgebfs.py:156-158  (edge_id)
      networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/edgedfs.py:142-144  (edge_id)
  [ec8b948cee144627]   EXAC  edges_from  L=3 N=2 saved=3 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/edgebfs.py:132-134  (edges_from)
      networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/edgedfs.py:118-120  (edges_from)
  [1d6d405e687b5504]   EXAC  edges_from  L=3 N=2 saved=3 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/edgebfs.py:138-140  (edges_from)
      networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/edgedfs.py:124-126  (edges_from)
  [acf4e919dc25b5b3]   EXAC  __setstate__  L=3 N=2 saved=3 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/classes/coreviews.py:129-131  (__setstate__)
      networkx-3.6.1-py3-none-any/networkx/classes/coreviews.py:188-190  (__setstate__)
  [428c39d0f8033cd4]   EXAC  is_multigraph  L=3 N=2 saved=3 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/classes/digraph.py:1257-1259  (is_multigraph)
      networkx-3.6.1-py3-none-any/networkx/classes/graph.py:1584-1586  (is_multigraph)
  [8bbb96d1a07dc72e]   EXAC  is_directed  L=3 N=2 saved=3 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/classes/digraph.py:1261-1263  (is_directed)
      networkx-3.6.1-py3-none-any/networkx/classes/multidigraph.py:876-878  (is_directed)
  [d928b1cf2cef5f77]   EXAC  is_directed  L=3 N=2 saved=3 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/classes/graph.py:1588-1590  (is_directed)
      networkx-3.6.1-py3-none-any/networkx/classes/multigraph.py:1030-1032  (is_directed)
  [ddc1a9eaaea1f9af]   EXAC  is_multigraph  L=3 N=2 saved=3 sim=1.00
      networkx-3.6.1-py3-none-any/networkx/classes/multidigraph.py:872-874  (is_multigraph)
      networkx-3.6.1-py3-none-any/networkx/classes/multigraph.py:1026-1028  (is_multigraph)
  [25c1136189c1e6ba]   EXAC  camel_to_snake  L=3 N=2 saved=3 sim=1.00
      scripts/maintenance/split_god_modules.py:89-91  (camel_to_snake)
      scripts/maintenance/split_web_controller.py:18-20  (camel_to_snake)
  [9010de500ab2da8f]   EXAC  list_actions  L=3 N=2 saved=3 sim=1.00
      src/nlp2cmd/dom_actions/registry.py:26-28  (list_actions)
      src/nlp2cmd/step_handlers/registry.py:26-28  (list_actions)
  [b333020df632b18f]   EXAC  _shell_intent_file_search  L=3 N=2 saved=3 sim=1.00
      src/nlp2cmd/generation/template_generator.py:631-633  (_shell_intent_file_search)
      src/nlp2cmd/generation/template_generator.py:845-847  (_shell_intent_file_search)
  [5a0ff58926871c07]   EXAC  dispose  L=3 N=2 saved=3 sim=1.00
      src/nlp2cmd/skills/drawing/renderers/base.py:82-84  (dispose)
      src/nlp2cmd/skills/drawing/renderers/playwright.py:213-215  (dispose)
  [a8f6eab811af752e]   EXAC  __aexit__  L=3 N=2 saved=3 sim=1.00
      src/nlp2cmd/skills/search/engine.py:451-453  (__aexit__)
      src/nlp2cmd/skills/search/skill.py:198-200  (__aexit__)
  [95e08268c63a4858]   EXAC  __init__  L=3 N=2 saved=3 sim=1.00
      webops/docker_app.py:66-68  (__init__)
      webops/voice_service.py:79-81  (__init__)
  [580302e481bcb57a]   STRU  get_status  L=3 N=2 saved=3 sim=1.00
      examples/03_integrations/web_development/web_app_example.py:90-92  (get_status)
      examples/03_integrations/web_development/web_app_example.py:100-102  (get_services)
  [975e4ede19dcf1df]   STRU  get_action  L=3 N=2 saved=3 sim=1.00
      src/nlp2cmd/dom_actions/registry.py:72-74  (get_action)
      src/nlp2cmd/step_handlers/registry.py:147-149  (get_handler)

REFACTOR[152] (ranked by priority):
  [1] ○ extract_function   → examples/04_domain_specific/utils/demo_protein_folding.py
      WHY: 35 occurrences of 23-line block across 8 files — saves 782 lines
      FILES: examples/04_domain_specific/bioinformatics/example.py, examples/04_domain_specific/education/example.py, examples/04_domain_specific/energy/example.py, examples/04_domain_specific/finance/example.py, examples/04_domain_specific/healthcare/example.py +3 more
  [2] ◐ extract_module     → webops/utils/root.py
      WHY: 2 occurrences of 392-line block across 2 files — saves 392 lines
      FILES: webops/docker_app.py, webops/voice_service.py
  [3] ◐ extract_module     → networkx-3.6.1-py3-none-any/networkx/algorithms/flow/utils/boykov_kolmogorov.py
      WHY: 3 occurrences of 147-line block across 3 files — saves 294 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/flow/boykovkolmogorov.py, networkx-3.6.1-py3-none-any/networkx/algorithms/flow/dinitz_alg.py, networkx-3.6.1-py3-none-any/networkx/algorithms/flow/edmondskarp.py
  [4] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/drawing/utils/draw_bipartite.py
      WHY: 8 occurrences of 42-line block across 1 files — saves 294 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/drawing/nx_pylab.py
  [5] ○ extract_function   → examples/04_domain_specific/utils/demo_drug_discovery.py
      WHY: 8 occurrences of 20-line block across 8 files — saves 140 lines
      FILES: examples/04_domain_specific/bioinformatics/example.py, examples/04_domain_specific/education/example.py, examples/04_domain_specific/energy/example.py, examples/04_domain_specific/finance/example.py, examples/04_domain_specific/healthcare/example.py +3 more
  [6] ○ extract_function   → examples/04_domain_specific/utils/demo_genomic_pipeline.py
      WHY: 7 occurrences of 23-line block across 7 files — saves 138 lines
      FILES: examples/04_domain_specific/bioinformatics/example.py, examples/04_domain_specific/education/example.py, examples/04_domain_specific/energy/example.py, examples/04_domain_specific/healthcare/example.py, examples/04_domain_specific/logistics/example.py +2 more
  [7] ○ extract_function   → examples/04_domain_specific/data_science/utils/demo_system_monitoring.py
      WHY: 7 occurrences of 22-line block across 1 files — saves 132 lines
      FILES: examples/04_domain_specific/data_science/dsl_demo.py
  [8] ◐ extract_module     → examples/03_integrations/toon_format/utils/main.py
      WHY: 3 occurrences of 54-line block across 3 files — saves 108 lines
      FILES: examples/03_integrations/toon_format/11_basic_integration/demo.py, examples/03_integrations/toon_format/12_advanced_integration/demo.py, examples/03_integrations/toon_format/13_query_system/demo.py
  [9] ○ extract_module     → networkx-3.6.1-py3-none-any/networkx/algorithms/operators/utils/disjoint_union.py
      WHY: 3 occurrences of 51-line block across 1 files — saves 102 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/operators/binary.py
  [10] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/utils/number_attracting_components.py
      WHY: 5 occurrences of 25-line block across 5 files — saves 100 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/components/attracting.py, networkx-3.6.1-py3-none-any/networkx/algorithms/components/connected.py, networkx-3.6.1-py3-none-any/networkx/algorithms/components/strongly_connected.py, networkx-3.6.1-py3-none-any/networkx/algorithms/components/weakly_connected.py, networkx-3.6.1-py3-none-any/networkx/algorithms/isolate.py
  [11] ◐ extract_function   → examples/04_domain_specific/debugging/utils/main.py
      WHY: 3 occurrences of 49-line block across 3 files — saves 98 lines
      FILES: examples/04_domain_specific/debugging/07_file_operations/demo.py, examples/04_domain_specific/debugging/08_system_commands/demo.py, examples/04_domain_specific/debugging/09_network_commands/demo.py
  [12] ○ extract_function   → examples/10_online_code_editors/utils/run_nlp2cmd_command.py
      WHY: 5 occurrences of 23-line block across 5 files — saves 92 lines
      FILES: examples/10_online_code_editors/01_codepen_live_nlp2cmd.py, examples/10_online_code_editors/02_mycompiler_run_nlp2cmd.py, examples/10_online_code_editors/03_adaptive_code_nlp2cmd.py, examples/10_online_code_editors/04_jsfiddle_frontend_nlp2cmd.py, examples/10_online_code_editors/05_dynamic_executor_nlp2cmd.py
  [13] ○ extract_module     → networkx-3.6.1-py3-none-any/networkx/algorithms/tree/utils/minimum_spanning_edges.py
      WHY: 2 occurrences of 91-line block across 1 files — saves 91 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/tree/mst.py
  [14] ○ extract_module     → networkx-3.6.1-py3-none-any/networkx/algorithms/flow/utils/min_cost_flow_cost.py
      WHY: 2 occurrences of 87-line block across 1 files — saves 87 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/flow/mincost.py
  [15] ◐ extract_function   → examples/utils/demo_advanced_features.py
      WHY: 3 occurrences of 42-line block across 2 files — saves 84 lines
      FILES: examples/03_integrations/toon_format/simple_demo.py, examples/06_tools_and_utilities/migration_tools/guide.py
  [16] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/utils/degree_centrality.py
      WHY: 3 occurrences of 41-line block across 1 files — saves 82 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/degree_alg.py
  [17] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/linalg/utils/laplacian_spectrum.py
      WHY: 3 occurrences of 41-line block across 1 files — saves 82 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/linalg/spectrum.py
  [18] ◐ extract_function   → examples/09_online_drawing/_old/utils/run_nlp2cmd_command.py
      WHY: 3 occurrences of 40-line block across 3 files — saves 80 lines
      FILES: examples/09_online_drawing/_old/01_draw_chat_shapes_nlp2cmd.py, examples/09_online_drawing/_old/02_picsart_painting_nlp2cmd.py, examples/09_online_drawing/_old/03_adaptive_drawing_nlp2cmd.py
  [19] ◐ extract_function   → examples/04_domain_specific/bioinformatics/utils/main.py
      WHY: 3 occurrences of 39-line block across 3 files — saves 78 lines
      FILES: examples/04_domain_specific/bioinformatics/02_file_processing/demo.py, examples/04_domain_specific/bioinformatics/03_blast_operations/demo.py, examples/04_domain_specific/bioinformatics/04_data_conversion/demo.py
  [20] ◐ extract_module     → networkx-3.6.1-py3-none-any/networkx/algorithms/components/utils/connected_components.py
      WHY: 2 occurrences of 73-line block across 2 files — saves 73 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/components/connected.py, networkx-3.6.1-py3-none-any/networkx/algorithms/components/weakly_connected.py
  [21] ○ extract_module     → networkx-3.6.1-py3-none-any/networkx/algorithms/utils/check_planarity.py
      WHY: 2 occurrences of 73-line block across 1 files — saves 73 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/planarity.py
  [22] ○ extract_module     → examples/06_tools_and_utilities/migration_tools/utils/old_way_examples.py
      WHY: 2 occurrences of 66-line block across 1 files — saves 66 lines
      FILES: examples/06_tools_and_utilities/migration_tools/guide.py
  [23] ○ extract_module     → networkx-3.6.1-py3-none-any/networkx/algorithms/utils/diameter.py
      WHY: 2 occurrences of 66-line block across 1 files — saves 66 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/distance_measures.py
  [24] ○ extract_module     → networkx-3.6.1-py3-none-any/networkx/generators/utils/_directed_neighbor_switch.py
      WHY: 2 occurrences of 61-line block across 1 files — saves 61 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/generators/joint_degree_seq.py
  [25] ◐ extract_module     → networkx-3.6.1-py3-none-any/networkx/readwrite/utils/read_graph6.py
      WHY: 2 occurrences of 61-line block across 2 files — saves 61 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/readwrite/graph6.py, networkx-3.6.1-py3-none-any/networkx/readwrite/sparse6.py
  [26] ○ extract_class      → src/nlp2cmd/utils/__getattr__.py
      WHY: 16 occurrences of 4-line block across 16 files — saves 60 lines
      FILES: src/nlp2cmd/generation/allocation_energy.py, src/nlp2cmd/generation/hybrid_thermodynamic_generator.py, src/nlp2cmd/generation/routing_energy.py, src/nlp2cmd/generation/scheduling_energy.py, src/nlp2cmd/generation/thermodynamic_components.py +11 more
  [27] ○ extract_module     → networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/utils/dfs_postorder_nodes.py
      WHY: 2 occurrences of 56-line block across 1 files — saves 56 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/depth_first_search.py
  [28] ◐ extract_module     → networkx-3.6.1-py3-none-any/networkx/algorithms/components/utils/is_connected.py
      WHY: 2 occurrences of 55-line block across 2 files — saves 55 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/components/connected.py, networkx-3.6.1-py3-none-any/networkx/algorithms/components/weakly_connected.py
  [29] ○ extract_function   → examples/03_integrations/toon_format/utils/demo_real_world_example.py
      WHY: 2 occurrences of 50-line block across 1 files — saves 50 lines
      FILES: examples/03_integrations/toon_format/simple_demo.py
  [30] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/operators/utils/cartesian_product.py
      WHY: 2 occurrences of 49-line block across 1 files — saves 49 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/operators/product.py
  [31] ◐ extract_function   → networkx-3.6.1-py3-none-any/networkx/utils/write_edgelist.py
      WHY: 2 occurrences of 47-line block across 2 files — saves 47 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/edgelist.py, networkx-3.6.1-py3-none-any/networkx/readwrite/edgelist.py
  [32] ○ extract_function   → examples/04_domain_specific/utils/main.py
      WHY: 5 occurrences of 11-line block across 5 files — saves 44 lines
      FILES: examples/04_domain_specific/education/example.py, examples/04_domain_specific/energy/example.py, examples/04_domain_specific/healthcare/example.py, examples/04_domain_specific/physics/example.py, examples/04_domain_specific/smart_cities/example.py
  [33] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/generators/utils/icosahedral_graph.py
      WHY: 2 occurrences of 43-line block across 1 files — saves 43 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/generators/small.py
  [34] ○ extract_class      → src/nlp2cmd/utils/array.py
      WHY: 11 occurrences of 4-line block across 11 files — saves 40 lines
      FILES: src/nlp2cmd/generation/thermodynamic_components.py, src/nlp2cmd/thermodynamic/constraint_energy.py, src/nlp2cmd/thermodynamic/energy_estimator.py, src/nlp2cmd/thermodynamic/energy_model.py, src/nlp2cmd/thermodynamic/entropy_production_regularizer.py +6 more
  [35] ○ extract_class      → src/nlp2cmd/utils/zeros_like.py
      WHY: 11 occurrences of 4-line block across 11 files — saves 40 lines
      FILES: src/nlp2cmd/generation/thermodynamic_components.py, src/nlp2cmd/thermodynamic/constraint_energy.py, src/nlp2cmd/thermodynamic/energy_estimator.py, src/nlp2cmd/thermodynamic/energy_model.py, src/nlp2cmd/thermodynamic/entropy_production_regularizer.py +6 more
  [36] ○ extract_class      → src/nlp2cmd/utils/sum.py
      WHY: 11 occurrences of 4-line block across 11 files — saves 40 lines
      FILES: src/nlp2cmd/generation/thermodynamic_components.py, src/nlp2cmd/thermodynamic/constraint_energy.py, src/nlp2cmd/thermodynamic/energy_estimator.py, src/nlp2cmd/thermodynamic/energy_model.py, src/nlp2cmd/thermodynamic/entropy_production_regularizer.py +6 more
  [37] ○ extract_class      → src/nlp2cmd/utils/exp.py
      WHY: 11 occurrences of 4-line block across 11 files — saves 40 lines
      FILES: src/nlp2cmd/generation/thermodynamic_components.py, src/nlp2cmd/thermodynamic/constraint_energy.py, src/nlp2cmd/thermodynamic/energy_estimator.py, src/nlp2cmd/thermodynamic/energy_model.py, src/nlp2cmd/thermodynamic/entropy_production_regularizer.py +6 more
  [38] ◐ extract_function   → examples/utils/demo_basic_usage.py
      WHY: 2 occurrences of 38-line block across 2 files — saves 38 lines
      FILES: examples/03_integrations/toon_format/simple_demo.py, examples/04_domain_specific/bioinformatics/complete_examples.py
  [39] ○ extract_class      → src/nlp2cmd/thermodynamic/utils/random.py
      WHY: 10 occurrences of 4-line block across 10 files — saves 36 lines
      FILES: src/nlp2cmd/thermodynamic/constraint_energy.py, src/nlp2cmd/thermodynamic/energy_estimator.py, src/nlp2cmd/thermodynamic/energy_model.py, src/nlp2cmd/thermodynamic/entropy_production_regularizer.py, src/nlp2cmd/thermodynamic/langevin_config.py +5 more
  [40] ○ extract_class      → src/nlp2cmd/thermodynamic/utils/sqrt.py
      WHY: 10 occurrences of 4-line block across 10 files — saves 36 lines
      FILES: src/nlp2cmd/thermodynamic/constraint_energy.py, src/nlp2cmd/thermodynamic/energy_estimator.py, src/nlp2cmd/thermodynamic/energy_model.py, src/nlp2cmd/thermodynamic/entropy_production_regularizer.py, src/nlp2cmd/thermodynamic/langevin_config.py +5 more
  [41] ○ extract_class      → src/nlp2cmd/thermodynamic/utils/mean.py
      WHY: 10 occurrences of 4-line block across 10 files — saves 36 lines
      FILES: src/nlp2cmd/thermodynamic/constraint_energy.py, src/nlp2cmd/thermodynamic/energy_estimator.py, src/nlp2cmd/thermodynamic/energy_model.py, src/nlp2cmd/thermodynamic/entropy_production_regularizer.py, src/nlp2cmd/thermodynamic/langevin_config.py +5 more
  [42] ○ extract_class      → src/nlp2cmd/thermodynamic/utils/std.py
      WHY: 10 occurrences of 4-line block across 10 files — saves 36 lines
      FILES: src/nlp2cmd/thermodynamic/constraint_energy.py, src/nlp2cmd/thermodynamic/energy_estimator.py, src/nlp2cmd/thermodynamic/energy_model.py, src/nlp2cmd/thermodynamic/entropy_production_regularizer.py, src/nlp2cmd/thermodynamic/langevin_config.py +5 more
  [43] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/utils/get_counterexample.py
      WHY: 2 occurrences of 36-line block across 1 files — saves 36 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/planarity.py
  [44] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/tree/utils/is_arborescence.py
      WHY: 2 occurrences of 36-line block across 1 files — saves 36 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/tree/recognition.py
  [45] ○ extract_function   → src/nlp2cmd/utils/get_password_store.py
      WHY: 7 occurrences of 6-line block across 7 files — saves 36 lines
      FILES: src/nlp2cmd/automation/password_store.py, src/nlp2cmd/cli/syntax_cache.py, src/nlp2cmd/exploration/resource_discovery.py, src/nlp2cmd/generation/enhanced_context.py, src/nlp2cmd/generation/multi_command.py +2 more
  [46] ○ extract_function   → src/nlp2cmd/orchestration/utils/get_workspace.py
      WHY: 8 occurrences of 5-line block across 8 files — saves 35 lines
      FILES: src/nlp2cmd/orchestration/function_cache.py, src/nlp2cmd/orchestration/generated_function.py, src/nlp2cmd/orchestration/learned_path.py, src/nlp2cmd/orchestration/metrics.py, src/nlp2cmd/orchestration/metrics_collector.py +3 more
  [47] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/utils/treewidth_min_fill_in.py
      WHY: 3 occurrences of 17-line block across 2 files — saves 34 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/treewidth.py, networkx-3.6.1-py3-none-any/networkx/utils/decorators.py
  [48] ◐ extract_function   → scripts/maintenance/utils/main.py
      WHY: 2 occurrences of 34-line block across 2 files — saves 34 lines
      FILES: scripts/maintenance/apply_polish_integration.py, scripts/maintenance/restore_system.py
  [49] ◐ extract_function   → src/nlp2cmd/step_handlers/utils/execute.py
      WHY: 2 occurrences of 33-line block across 2 files — saves 33 lines
      FILES: src/nlp2cmd/step_handlers/click_canvas_handler.py, src/nlp2cmd/step_handlers/fill_at_handler.py
  [50] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/generators/utils/heawood_graph.py
      WHY: 2 occurrences of 31-line block across 1 files — saves 31 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/generators/small.py
  [51] ○ extract_function   → src/nlp2cmd/cli/utils/_timed_default_yes.py
      WHY: 2 occurrences of 31-line block across 1 files — saves 31 lines
      FILES: src/nlp2cmd/cli/helpers.py
  [52] ○ extract_function   → src/nlp2cmd/generation/utils/_get_jellyfish.py
      WHY: 4 occurrences of 10-line block across 4 files — saves 30 lines
      FILES: src/nlp2cmd/generation/fuzzy_schema_matcher_class.py, src/nlp2cmd/generation/fuzzy_schema_matcher_config.py, src/nlp2cmd/generation/match_result.py, src/nlp2cmd/generation/phrase_schema.py
  [53] ○ extract_function   → src/nlp2cmd/generation/utils/_get_rapidfuzz.py
      WHY: 4 occurrences of 10-line block across 4 files — saves 30 lines
      FILES: src/nlp2cmd/generation/fuzzy_schema_matcher_class.py, src/nlp2cmd/generation/fuzzy_schema_matcher_config.py, src/nlp2cmd/generation/match_result.py, src/nlp2cmd/generation/phrase_schema.py
  [54] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/utils/graph_could_be_isomorphic.py
      WHY: 3 occurrences of 15-line block across 1 files — saves 30 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/isomorph.py
  [55] ○ extract_function   → src/nlp2cmd/thermodynamic/utils/gradient.py
      WHY: 3 occurrences of 14-line block across 3 files — saves 28 lines
      FILES: src/nlp2cmd/thermodynamic/allocation_energy.py, src/nlp2cmd/thermodynamic/csp_energy.py, src/nlp2cmd/thermodynamic/routing_energy.py
  [56] ○ extract_function   → tools/schema/utils/_get_man_page.py
      WHY: 3 occurrences of 14-line block across 3 files — saves 28 lines
      FILES: tools/schema/comprehensive_command_scanner.py, tools/schema/enhanced_schema_generator.py, tools/schema/non_llm_schema_extractor.py
  [57] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/generators/utils/house_graph.py
      WHY: 2 occurrences of 27-line block across 1 files — saves 27 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/generators/small.py
  [58] ○ extract_function   → src/nlp2cmd/skills/drawing/utils/_get_router.py
      WHY: 5 occurrences of 6-line block across 5 files — saves 24 lines
      FILES: src/nlp2cmd/skills/drawing/draw_navigation_skill.py, src/nlp2cmd/skills/drawing/draw_object.py, src/nlp2cmd/skills/drawing/draw_validation_skill.py, src/nlp2cmd/skills/drawing/text_to_shape.py, src/nlp2cmd/skills/drawing/visual_validator.py
  [59] ○ extract_function   → examples/08_api_key_management/utils/run_flow.py
      WHY: 2 occurrences of 24-line block across 2 files — saves 24 lines
      FILES: examples/08_api_key_management/03_github_token/run.py, examples/08_api_key_management/04_huggingface_token/run.py
  [60] ○ extract_function   → examples/08_api_key_management/utils/main.py
      WHY: 3 occurrences of 12-line block across 3 files — saves 24 lines
      FILES: examples/08_api_key_management/03_github_token/run.py, examples/08_api_key_management/04_huggingface_token/run.py, examples/08_api_key_management/05_openai_key/run.py
  [61] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/readwrite/utils/read_leda.py
      WHY: 2 occurrences of 24-line block across 2 files — saves 24 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/readwrite/leda.py, networkx-3.6.1-py3-none-any/networkx/readwrite/p2g.py
  [62] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/utils/is_bipartite.py
      WHY: 2 occurrences of 23-line block across 2 files — saves 23 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/basic.py, networkx-3.6.1-py3-none-any/networkx/algorithms/distance_regular.py
  [63] ○ extract_function   → examples/utils/run_nlp2cmd_command.py
      WHY: 2 occurrences of 22-line block across 2 files — saves 22 lines
      FILES: examples/01_basics/docker_basics/01_basics_docker_nlp2cmd.py, examples/08_api_key_management/01_diagnose_credentials_nlp2cmd.py
  [64] ○ extract_function   → src/nlp2cmd/automation/utils/_load_known_services.py
      WHY: 2 occurrences of 22-line block across 2 files — saves 22 lines
      FILES: src/nlp2cmd/automation/action_planner.py, src/nlp2cmd/automation/service_configs.py
  [65] ○ extract_function   → scripts/maintenance/utils/apply_to_keywords_py.py
      WHY: 2 occurrences of 22-line block across 1 files — saves 22 lines
      FILES: scripts/maintenance/apply_refactors_to_source.py
  [66] ○ extract_function   → src/nlp2cmd/automation/utils/_can_use_desktop_automation.py
      WHY: 2 occurrences of 21-line block across 2 files — saves 21 lines
      FILES: src/nlp2cmd/automation/action_planner.py, src/nlp2cmd/automation/service_configs.py
  [67] ○ extract_function   → scripts/maintenance/utils/load_polish_patterns.py
      WHY: 4 occurrences of 7-line block across 1 files — saves 21 lines
      FILES: scripts/maintenance/apply_nlp2cmd_fixes.py
  [68] ○ extract_function   → src/nlp2cmd/utils/_debug.py
      WHY: 8 occurrences of 3-line block across 8 files — saves 21 lines
      FILES: src/nlp2cmd/adapters/canvas_adapter.py, src/nlp2cmd/adapters/desktop.py, src/nlp2cmd/automation/captcha_solver.py, src/nlp2cmd/automation/complex_planner.py, src/nlp2cmd/llm/openrouter.py +3 more
  [69] ○ extract_function   → examples/09_online_drawing/_old/utils/get_pattern_analysis_info.py
      WHY: 2 occurrences of 20-line block across 2 files — saves 20 lines
      FILES: examples/09_online_drawing/_old/02_picsart_painting_nlp2cmd.py, examples/09_online_drawing/_old/03_adaptive_drawing_nlp2cmd.py
  [70] ○ extract_function   → examples/10_online_code_editors/utils/main.py
      WHY: 2 occurrences of 20-line block across 2 files — saves 20 lines
      FILES: examples/10_online_code_editors/03_adaptive_code_nlp2cmd.py, examples/10_online_code_editors/05_dynamic_executor_nlp2cmd.py
  [71] ○ extract_function   → tools/schema/utils/_detect_category.py
      WHY: 2 occurrences of 19-line block across 2 files — saves 19 lines
      FILES: tools/schema/comprehensive_command_scanner.py, tools/schema/non_llm_schema_extractor.py
  [72] ○ extract_class      → src/nlp2cmd/utils/print.py
      WHY: 4 occurrences of 6-line block across 4 files — saves 18 lines
      FILES: src/nlp2cmd/cli/cache.py, src/nlp2cmd/cli/history.py, src/nlp2cmd/cli/web_schema.py, src/nlp2cmd/execution/runner.py
  [73] ○ extract_function   → tools/schema/utils/_parse_man_sections.py
      WHY: 2 occurrences of 18-line block across 2 files — saves 18 lines
      FILES: tools/schema/enhanced_schema_generator.py, tools/schema/non_llm_schema_extractor.py
  [74] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/classes/utils/nodes.py
      WHY: 4 occurrences of 6-line block across 1 files — saves 18 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/classes/function.py
  [75] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/operators/utils/_directed_edges_cross_edges.py
      WHY: 2 occurrences of 17-line block across 1 files — saves 17 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/operators/product.py
  [76] ○ extract_function   → examples/09_online_drawing/utils/fetch_only.py
      WHY: 2 occurrences of 16-line block across 2 files — saves 16 lines
      FILES: examples/09_online_drawing/05_autonomous/run.py, examples/09_online_drawing/_old/05_autonomous_drawing.py
  [77] ○ extract_function   → examples/05_advanced_features/dynamic_schemas/utils/main.py
      WHY: 2 occurrences of 16-line block across 2 files — saves 16 lines
      FILES: examples/05_advanced_features/dynamic_schemas/demo_version_detection.py, examples/05_advanced_features/dynamic_schemas/schema_flow_demo.py
  [78] ○ extract_function   → tools/schema/utils/_get_help_text.py
      WHY: 2 occurrences of 15-line block across 2 files — saves 15 lines
      FILES: tools/schema/comprehensive_command_scanner.py, tools/schema/non_llm_schema_extractor.py
  [79] ○ extract_function   → src/nlp2cmd/adapters/utils/validate_syntax.py
      WHY: 2 occurrences of 14-line block across 2 files — saves 14 lines
      FILES: src/nlp2cmd/adapters/canvas_adapter.py, src/nlp2cmd/adapters/desktop.py
  [80] ○ extract_function   → src/nlp2cmd/utils/register_action.py
      WHY: 2 occurrences of 13-line block across 2 files — saves 13 lines
      FILES: src/nlp2cmd/dom_actions/registry.py, src/nlp2cmd/step_handlers/registry.py
  [81] ○ extract_function   → src/nlp2cmd/cli/utils/_print.py
      WHY: 3 occurrences of 6-line block across 3 files — saves 12 lines
      FILES: src/nlp2cmd/cli/auto_repair.py, src/nlp2cmd/cli/commands/doctor.py, src/nlp2cmd/cli/commands/examples.py
  [82] ○ extract_function   → webops/utils/process_voice_command.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: webops/voice_service.py, webops/voice_service_clean.py
  [83] ○ extract_function   → src/nlp2cmd/utils/get_vector_store.py
      WHY: 3 occurrences of 6-line block across 2 files — saves 12 lines
      FILES: src/nlp2cmd/automation/vector_store.py, src/nlp2cmd/nlp/config.py
  [84] ○ extract_function   → src/nlp2cmd/llm/utils/_debug.py
      WHY: 5 occurrences of 3-line block across 5 files — saves 12 lines
      FILES: src/nlp2cmd/llm/adaptive_learner_class.py, src/nlp2cmd/llm/error_pattern.py, src/nlp2cmd/llm/learned_rule.py, src/nlp2cmd/llm/model_performance.py, src/nlp2cmd/llm/router.py
  [85] ○ extract_function   → webops/utils/__init__.py
      WHY: 3 occurrences of 6-line block across 2 files — saves 12 lines
      FILES: webops/voice_service.py, webops/voice_service_clean.py
  [86] ○ extract_function   → examples/01_basics/utils/get_command_for_task.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: examples/01_basics/docker_basics/01_basics_docker_nlp2cmd.py, examples/01_basics/shell_fundamentals/01_basics_shell_nlp2cmd.py
  [87] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/coloring/utils/strategy_connected_sequential_bfs.py
      WHY: 2 occurrences of 11-line block across 1 files — saves 11 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/coloring/greedy_coloring.py
  [88] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/utils/_csr_gen_triples.py
      WHY: 2 occurrences of 11-line block across 1 files — saves 11 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/convert_matrix.py
  [89] ○ extract_function   → src/nlp2cmd/evolutionary/utils/_print.py
      WHY: 3 occurrences of 5-line block across 3 files — saves 10 lines
      FILES: src/nlp2cmd/evolutionary/engine.py, src/nlp2cmd/evolutionary/planner.py, src/nlp2cmd/evolutionary/runner.py
  [90] ○ extract_function   → examples/04_domain_specific/utils/main.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: examples/04_domain_specific/finance/example.py, examples/04_domain_specific/logistics/example.py
  [91] ○ extract_function   → src/nlp2cmd/generation/utils/extract_command.py
      WHY: 2 occurrences of 10-line block across 1 files — saves 10 lines
      FILES: src/nlp2cmd/generation/llm_simple.py
  [92] ○ extract_function   → webops/utils/websocket_endpoint.py
      WHY: 2 occurrences of 9-line block across 2 files — saves 9 lines
      FILES: webops/docker_app.py, webops/voice_service.py
  [93] ○ extract_function   → webops/utils/__init__.py
      WHY: 2 occurrences of 9-line block across 1 files — saves 9 lines
      FILES: webops/voice_service_clean.py
  [94] ○ extract_function   → examples/utils/print_rule.py
      WHY: 2 occurrences of 9-line block across 2 files — saves 9 lines
      FILES: examples/04_domain_specific/_demo_helpers.py, examples/_example_helpers.py
  [95] ○ extract_function   → src/nlp2cmd/cli/utils/display_success.py
      WHY: 4 occurrences of 3-line block across 1 files — saves 9 lines
      FILES: src/nlp2cmd/cli/display.py
  [96] ○ extract_function   → src/nlp2cmd/generation/utils/_check_msgpack.py
      WHY: 2 occurrences of 9-line block across 2 files — saves 9 lines
      FILES: src/nlp2cmd/generation/data_loader.py, src/nlp2cmd/generation/ml_intent_classifier.py
  [97] ○ extract_function   → src/nlp2cmd/generation/utils/_check_torch.py
      WHY: 2 occurrences of 9-line block across 1 files — saves 9 lines
      FILES: src/nlp2cmd/generation/semantic_matcher_optimized.py
  [98] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/operators/utils/add_prefix.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/operators/all.py, networkx-3.6.1-py3-none-any/networkx/algorithms/operators/binary.py
  [99] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/classes/utils/__len__.py
      WHY: 2 occurrences of 8-line block across 1 files — saves 8 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/classes/coreviews.py
  [100] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/classes/utils/__iter__.py
      WHY: 2 occurrences of 8-line block across 1 files — saves 8 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/classes/coreviews.py
  [101] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/classes/utils/__setstate__.py
      WHY: 3 occurrences of 4-line block across 1 files — saves 8 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/classes/reportviews.py
  [102] ○ extract_class      → src/nlp2cmd/cli/utils/group.py
      WHY: 3 occurrences of 4-line block across 3 files — saves 8 lines
      FILES: src/nlp2cmd/cli/cache.py, src/nlp2cmd/cli/history.py, src/nlp2cmd/cli/web_schema.py
  [103] ○ extract_class      → src/nlp2cmd/cli/utils/option.py
      WHY: 3 occurrences of 4-line block across 3 files — saves 8 lines
      FILES: src/nlp2cmd/cli/cache.py, src/nlp2cmd/cli/history.py, src/nlp2cmd/cli/web_schema.py
  [104] ○ extract_class      → src/nlp2cmd/cli/utils/argument.py
      WHY: 3 occurrences of 4-line block across 3 files — saves 8 lines
      FILES: src/nlp2cmd/cli/cache.py, src/nlp2cmd/cli/history.py, src/nlp2cmd/cli/web_schema.py
  [105] ○ extract_function   → src/nlp2cmd/cli/utils/command.py
      WHY: 3 occurrences of 4-line block across 3 files — saves 8 lines
      FILES: src/nlp2cmd/cli/cache.py, src/nlp2cmd/cli/history.py, src/nlp2cmd/cli/web_schema.py
  [106] ○ extract_function   → tools/schema/utils/_extract_description.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: tools/schema/comprehensive_command_scanner.py, tools/schema/enhanced_schema_generator.py
  [107] ○ extract_class      → webops/utils/broadcast_log.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: webops/docker_app.py, webops/voice_service.py
  [108] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/classes/utils/to_directed.py
      WHY: 2 occurrences of 8-line block across 1 files — saves 8 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/classes/function.py
  [109] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/generators/utils/null_graph.py
      WHY: 2 occurrences of 8-line block across 1 files — saves 8 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/generators/classic.py
  [110] ○ extract_function   → src/nlp2cmd/utils/_debug.py
      WHY: 3 occurrences of 4-line block across 3 files — saves 8 lines
      FILES: src/nlp2cmd/adapters/browser.py, src/nlp2cmd/utils/debug_helpers.py, src/nlp2cmd/web_schema/site_explorer.py
  [111] ○ extract_function   → src/nlp2cmd/utils/get_cache_stats.py
      WHY: 3 occurrences of 4-line block across 2 files — saves 8 lines
      FILES: src/nlp2cmd/cli/syntax_cache.py, src/nlp2cmd/core/toon_integration.py
  [112] ○ extract_function   → src/nlp2cmd/utils/execution_record_enabled.py
      WHY: 3 occurrences of 4-line block across 2 files — saves 8 lines
      FILES: src/nlp2cmd/plan_execution/execution_record.py, src/nlp2cmd/post_execution/checker.py
  [113] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/utils/filter_iter.py
      WHY: 2 occurrences of 7-line block across 1 files — saves 7 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py
  [114] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/utils/filter_pred_iter.py
      WHY: 2 occurrences of 7-line block across 1 files — saves 7 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py
  [115] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/utils/filter_succ_iter.py
      WHY: 2 occurrences of 7-line block across 1 files — saves 7 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py
  [116] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/utils/filter_iter.py
      WHY: 2 occurrences of 7-line block across 1 files — saves 7 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py
  [117] ○ extract_function   → src/nlp2cmd/utils/_normalize_url.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/nlp2cmd/page_analysis/link_extractor.py, src/nlp2cmd/web_schema/site_explorer.py
  [118] ○ extract_function   → webops/utils/health_check.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: webops/voice_service.py, webops/voice_service_clean.py
  [119] ○ extract_function   → src/nlp2cmd/schema_extraction/utils/extract_from_file.py
      WHY: 2 occurrences of 7-line block across 1 files — saves 7 lines
      FILES: src/nlp2cmd/schema_extraction/script_extractors.py
  [120] ○ extract_function   → src/nlp2cmd/skills/drawing/utils/_parse_json.py
      WHY: 3 occurrences of 3-line block across 3 files — saves 6 lines
      FILES: src/nlp2cmd/skills/drawing/draw_navigation_skill.py, src/nlp2cmd/skills/drawing/draw_object.py, src/nlp2cmd/skills/drawing/draw_validation_skill.py
  [121] ○ extract_class      → webops/utils/__init__.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: webops/voice_service.py, webops/voice_service_clean.py
  [122] ○ extract_class      → webops/utils/__init__.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: webops/voice_service.py, webops/voice_service_clean.py
  [123] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/classes/utils/neighbors.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/classes/function.py
  [124] ○ extract_function   → src/nlp2cmd/cli/utils/cache_group.py
      WHY: 3 occurrences of 3-line block across 3 files — saves 6 lines
      FILES: src/nlp2cmd/cli/cache.py, src/nlp2cmd/cli/history.py, src/nlp2cmd/cli/web_schema.py
  [125] ○ extract_function   → utils/get_monitor.py
      WHY: 3 occurrences of 3-line block across 3 files — saves 6 lines
      FILES: src/nlp2cmd/monitoring/resources.py, webops/docker_app.py, webops/voice_service.py
  [126] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/utils/edges_from.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/edgebfs.py, networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/edgedfs.py
  [127] ○ extract_function   → scripts/maintenance/utils/module_filename.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: scripts/maintenance/split_god_modules.py, scripts/maintenance/split_web_controller.py
  [128] ○ extract_function   → src/nlp2cmd/utils/print_yaml_block.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/nlp2cmd/cli/helpers.py, src/nlp2cmd/context/disambiguator.py
  [129] ○ extract_function   → examples/utils/print_section.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: examples/01_basics/sql_basics/workflows.py, examples/03_integrations/validation/config_validation.py
  [130] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/utils/iterate.py
      WHY: 2 occurrences of 4-line block across 1 files — saves 4 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py
  [131] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/utils/iterate.py
      WHY: 2 occurrences of 4-line block across 1 files — saves 4 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py
  [132] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/utils/iterate.py
      WHY: 2 occurrences of 4-line block across 1 files — saves 4 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py
  [133] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/utils/iterate.py
      WHY: 2 occurrences of 4-line block across 1 files — saves 4 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py
  [134] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/classes/utils/__init__.py
      WHY: 2 occurrences of 4-line block across 1 files — saves 4 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/classes/reportviews.py
  [135] ○ extract_class      → webops/utils/connect.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: webops/docker_app.py, webops/voice_service.py
  [136] ○ extract_class      → webops/utils/disconnect.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: webops/docker_app.py, webops/voice_service.py
  [137] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/utils/edge_id.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/edgebfs.py, networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/edgedfs.py
  [138] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/utils/edges_from.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/edgebfs.py, networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/edgedfs.py
  [139] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/utils/edges_from.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/edgebfs.py, networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/edgedfs.py
  [140] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/classes/utils/__setstate__.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/classes/coreviews.py
  [141] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/classes/utils/is_multigraph.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/classes/digraph.py, networkx-3.6.1-py3-none-any/networkx/classes/graph.py
  [142] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/classes/utils/is_directed.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/classes/digraph.py, networkx-3.6.1-py3-none-any/networkx/classes/multidigraph.py
  [143] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/classes/utils/is_directed.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/classes/graph.py, networkx-3.6.1-py3-none-any/networkx/classes/multigraph.py
  [144] ○ extract_function   → networkx-3.6.1-py3-none-any/networkx/classes/utils/is_multigraph.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: networkx-3.6.1-py3-none-any/networkx/classes/multidigraph.py, networkx-3.6.1-py3-none-any/networkx/classes/multigraph.py
  [145] ○ extract_function   → scripts/maintenance/utils/camel_to_snake.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: scripts/maintenance/split_god_modules.py, scripts/maintenance/split_web_controller.py
  [146] ○ extract_function   → src/nlp2cmd/utils/list_actions.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/nlp2cmd/dom_actions/registry.py, src/nlp2cmd/step_handlers/registry.py
  [147] ○ extract_class      → src/nlp2cmd/generation/utils/_shell_intent_file_search.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/nlp2cmd/generation/template_generator.py
  [148] ○ extract_function   → src/nlp2cmd/skills/drawing/renderers/utils/dispose.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/nlp2cmd/skills/drawing/renderers/base.py, src/nlp2cmd/skills/drawing/renderers/playwright.py
  [149] ○ extract_function   → src/nlp2cmd/skills/search/utils/__aexit__.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/nlp2cmd/skills/search/engine.py, src/nlp2cmd/skills/search/skill.py
  [150] ○ extract_class      → webops/utils/__init__.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: webops/docker_app.py, webops/voice_service.py
  [151] ○ extract_function   → examples/03_integrations/web_development/utils/get_status.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: examples/03_integrations/web_development/web_app_example.py
  [152] ○ extract_function   → src/nlp2cmd/utils/get_action.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/nlp2cmd/dom_actions/registry.py, src/nlp2cmd/step_handlers/registry.py

QUICK_WINS[111] (low risk, high savings — do first):
  [1] extract_function   saved=782L  → examples/04_domain_specific/utils/demo_protein_folding.py
      FILES: example.py, example.py, example.py +5
  [4] extract_function   saved=294L  → networkx-3.6.1-py3-none-any/networkx/drawing/utils/draw_bipartite.py
      FILES: nx_pylab.py
  [5] extract_function   saved=140L  → examples/04_domain_specific/utils/demo_drug_discovery.py
      FILES: example.py, example.py, example.py +5
  [6] extract_function   saved=138L  → examples/04_domain_specific/utils/demo_genomic_pipeline.py
      FILES: example.py, example.py, example.py +4
  [7] extract_function   saved=132L  → examples/04_domain_specific/data_science/utils/demo_system_monitoring.py
      FILES: dsl_demo.py
  [9] extract_module     saved=102L  → networkx-3.6.1-py3-none-any/networkx/algorithms/operators/utils/disjoint_union.py
      FILES: binary.py
  [10] extract_function   saved=100L  → networkx-3.6.1-py3-none-any/networkx/algorithms/utils/number_attracting_components.py
      FILES: attracting.py, connected.py, strongly_connected.py +2
  [12] extract_function   saved=92L  → examples/10_online_code_editors/utils/run_nlp2cmd_command.py
      FILES: 01_codepen_live_nlp2cmd.py, 02_mycompiler_run_nlp2cmd.py, 03_adaptive_code_nlp2cmd.py +2
  [13] extract_module     saved=91L  → networkx-3.6.1-py3-none-any/networkx/algorithms/tree/utils/minimum_spanning_edges.py
      FILES: mst.py
  [14] extract_module     saved=87L  → networkx-3.6.1-py3-none-any/networkx/algorithms/flow/utils/min_cost_flow_cost.py
      FILES: mincost.py

DEPENDENCY_RISK[1] (duplicates spanning multiple packages):
  get_monitor  packages=2  files=3
      src/nlp2cmd/monitoring/resources.py
      webops/docker_app.py
      webops/voice_service.py

EFFORT_ESTIMATE (total ≈ 240.7h):
  hard   demo_protein_folding                saved=782L  ~1564min
  hard   root                                saved=392L  ~1176min
  hard   boykov_kolmogorov                   saved=294L  ~882min
  hard   draw_bipartite                      saved=294L  ~882min
  hard   demo_drug_discovery                 saved=140L  ~280min
  hard   demo_genomic_pipeline               saved=138L  ~276min
  hard   demo_system_monitoring              saved=132L  ~264min
  hard   main                                saved=108L  ~324min
  hard   disjoint_union                      saved=102L  ~306min
  hard   number_attracting_components        saved=100L  ~200min
  ... +142 more (~8289min)

METRICS-TARGET:
  dup_groups:  152 → 0
  saved_lines: 5810 lines recoverable
```

### Evolution / Churn (`project/evolution.toon.yaml`)

```toon markpact:analysis path=project/evolution.toon.yaml
# code2llm/evolution | 3129 func | 414f | 2026-06-06
# generated in 0.02s

NEXT[10] (ranked by impact):
  [1] !! SPLIT-FUNC      BrowserExecutionMixin._run_dom_multi_action  CC=280  fan=108
      WHY: CC=280 exceeds 15
      EFFORT: ~1h  IMPACT: 30240

  [2] !! SPLIT-FUNC      handle_run_mode  CC=183  fan=80
      WHY: CC=183 exceeds 15
      EFFORT: ~1h  IMPACT: 14640

  [3] !! SPLIT-FUNC      PlanExecutionMixin.execute_action_plan  CC=168  fan=74
      WHY: CC=168 exceeds 15
      EFFORT: ~1h  IMPACT: 12432

  [4] !! SPLIT-FUNC      main  CC=71  fan=56
      WHY: CC=71 exceeds 15
      EFFORT: ~1h  IMPACT: 3976

  [5] !! SPLIT-FUNC      _execute_multi_step_with_video  CC=64  fan=54
      WHY: CC=64 exceeds 15
      EFFORT: ~1h  IMPACT: 3456

  [6] !! SPLIT-FUNC      SiteExplorer.find_form  CC=72  fan=30
      WHY: CC=72 exceeds 15
      EFFORT: ~1h  IMPACT: 2160

  [7] !! SPLIT-FUNC      ExecutionRunner.run_with_recovery  CC=54  fan=35
      WHY: CC=54 exceeds 15
      EFFORT: ~1h  IMPACT: 1890

  [8] !! SPLIT-FUNC      _extract_web_dom_schema  CC=45  fan=37
      WHY: CC=45 exceeds 15
      EFFORT: ~1h  IMPACT: 1665

  [9] !! SPLIT-FUNC      ExecutionRunner.run_command  CC=50  fan=32
      WHY: CC=50 exceeds 15
      EFFORT: ~1h  IMPACT: 1600

  [10] !! SPLIT-FUNC      handle_generate_query  CC=41  fan=38
      WHY: CC=41 exceeds 15
      EFFORT: ~1h  IMPACT: 1558


RISKS[3]:
  ⚠ Splitting src/nlp2cmd/data/phrase_database.json may break 0 import paths
  ⚠ Splitting data/phrase_database.json may break 0 import paths
  ⚠ Splitting planfile.yaml may break 0 import paths

METRICS-TARGET:
  CC̄:          5.3 → ≤3.7
  max-CC:      280 → ≤20
  god-modules: 69 → 0
  high-CC(≥15): 188 → ≤94
  hub-types:   0 → ≤0

PATTERNS (language parser shared logic):
  _extract_declarations() in base.py — unified extraction for:
    - TypeScript: interfaces, types, classes, functions, arrow funcs
    - PHP: namespaces, traits, classes, functions, includes
    - Ruby: modules, classes, methods, requires
    - C++: classes, structs, functions, #includes
    - C#: classes, interfaces, methods, usings
    - Java: classes, interfaces, methods, imports
    - Go: packages, functions, structs
    - Rust: modules, functions, traits, use statements

  Shared regex patterns per language:
    - import: language-specific import/require/using patterns
    - class: class/struct/trait declarations with inheritance
    - function: function/method signatures with visibility
    - brace_tracking: for C-family languages ({ })
    - end_keyword_tracking: for Ruby (module/class/def...end)

  Benefits:
    - Consistent extraction logic across all languages
    - Reduced code duplication (~70% reduction in parser LOC)
    - Easier maintenance: fix once, apply everywhere
    - Standardized FunctionInfo/ClassInfo models

HISTORY:
  prev CC̄=5.3 → now CC̄=5.3
```

### Validation (`project/validation.toon.yaml`)

```toon markpact:analysis path=project/validation.toon.yaml
# vallm batch | 1817f | 0✓ 1554⚠ 0✗ | 2026-06-05

SUMMARY:
  scanned: 1817  passed: 0 (0.0%)  warnings: 1554  errors: 0  unsupported: 0

WARNINGS[1554]{path,score}:
  networkx-3.6.1-py3-none-any/networkx/drawing/nx_pylab.py,0.56
    issues[8]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,display: CC=60 exceeds limit 15,257
      complexity.lizard_length,warning,display: 307 lines exceeds limit 100,257
      complexity.lizard_cc,warning,__call__: CC=22 exceeds limit 15,1646
      complexity.lizard_cc,warning,draw_networkx_edges: CC=39 exceeds limit 15,1750
      complexity.lizard_length,warning,draw_networkx_edges: 171 lines exceeds limit 100,1750
      complexity.lizard_cc,warning,draw_networkx_edge_labels: CC=19 exceeds limit 15,2276
      complexity.lizard_length,warning,draw_networkx_edge_labels: 146 lines exceeds limit 100,2276
  networkx-3.6.1-py3-none-any/networkx/utils/backends.py,0.56
    issues[13]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,__new__: CC=32 exceeds limit 15,218
      complexity.lizard_length,warning,__new__: 129 lines exceeds limit 100,218
      complexity.lizard_cc,warning,_call_if_any_backends_installed: CC=79 exceeds limit 15,554
      complexity.lizard_length,warning,_call_if_any_backends_installed: 341 lines exceeds limit 100,554
      complexity.lizard_cc,warning,_convert_arguments: CC=54 exceeds limit 15,1148
      complexity.lizard_length,warning,_convert_arguments: 160 lines exceeds limit 100,1148
      complexity.lizard_length,warning,_convert_graph: 112 lines exceeds limit 100,1359
      complexity.lizard_cc,warning,_convert_and_call_for_tests: CC=58 exceeds limit 15,1588
      complexity.lizard_length,warning,_convert_and_call_for_tests: 202 lines exceeds limit 100,1588
      complexity.lizard_cc,warning,_make_doc: CC=27 exceeds limit 15,1870
      complexity.lizard_cc,warning,_get_from_cache: CC=33 exceeds limit 15,2000
      complexity.lizard_cc,warning,_set_to_cache: CC=16 exceeds limit 15,2084
  src/app2schema/extract.py,0.56
    issues[8]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_extract_web_dom_schema: CC=46 exceeds limit 15,232
      complexity.lizard_length,warning,_extract_web_dom_schema: 170 lines exceeds limit 100,232
      complexity.lizard_cc,warning,discover_openapi_spec_url: CC=23 exceeds limit 15,559
      complexity.lizard_cc,warning,extract_schema: CC=30 exceeds limit 15,622
      complexity.lizard_length,warning,extract_schema: 152 lines exceeds limit 100,622
      complexity.lizard_cc,warning,extract_appspec_to_file: CC=27 exceeds limit 15,822
      complexity.lizard_cc,warning,extract_schema_to_file: CC=20 exceeds limit 15,891
  src/nlp2cmd/automation/schema_fallback.py,0.56
    issues[10]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,generate_fallback: CC=22 exceeds limit 15,87
      complexity.lizard_cc,warning,_try_rule_based: CC=24 exceeds limit 15,188
      complexity.lizard_length,warning,_try_rule_based: 189 lines exceeds limit 100,188
      complexity.lizard_cc,warning,_try_dynamic_page_schema: CC=26 exceeds limit 15,501
      complexity.lizard_length,warning,_try_dynamic_page_schema: 144 lines exceeds limit 100,501
      complexity.lizard_cc,warning,_extract_page_schema: CC=47 exceeds limit 15,674
      complexity.lizard_length,warning,_extract_page_schema: 129 lines exceeds limit 100,674
      complexity.lizard_cc,warning,_try_page_analysis: CC=22 exceeds limit 15,847
      complexity.lizard_cc,warning,_parse_llm_steps: CC=18 exceeds limit 15,1085
  src/nlp2cmd/cli/commands/doctor.py,0.56
    issues[9]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,print_summary: CC=21 exceeds limit 15,489
      complexity.lizard_cc,warning,_try_existing_browser: CC=40 exceeds limit 15,626
      complexity.lizard_length,warning,_try_existing_browser: 115 lines exceeds limit 100,626
      complexity.lizard_cc,warning,_try_system_browser: CC=56 exceeds limit 15,772
      complexity.lizard_length,warning,_try_system_browser: 163 lines exceeds limit 100,772
      complexity.lizard_cc,warning,_try_playwright_browser: CC=28 exceeds limit 15,975
      complexity.lizard_cc,warning,_navigate_and_get_token: CC=22 exceeds limit 15,1079
      complexity.lizard_cc,warning,doctor_command: CC=16 exceeds limit 15,1319
  src/nlp2cmd/web_schema/site_explorer.py,0.56
    issues[11]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,find_content: CC=42 exceeds limit 15,348
      complexity.lizard_length,warning,find_content: 166 lines exceeds limit 100,348
      complexity.lizard_cc,warning,find_form: CC=73 exceeds limit 15,561
      complexity.lizard_length,warning,find_form: 246 lines exceeds limit 100,561
      complexity.lizard_cc,warning,_explore_recursive: CC=20 exceeds limit 15,865
      complexity.lizard_cc,warning,_analyze_page._is_junk_desc: CC=25 exceeds limit 15,997
      complexity.lizard_cc,warning,_analyze_page: CC=40 exceeds limit 15,959
      complexity.lizard_length,warning,_analyze_page: 109 lines exceeds limit 100,959
      complexity.lizard_cc,warning,_score_page: CC=26 exceeds limit 15,1210
      complexity.lizard_cc,warning,_get_sitemap_urls: CC=30 exceeds limit 15,1329
  networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/isomorphvf2.py,0.58
    issues[7]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,syntactic_feasibility: CC=32 exceeds limit 15,498
      complexity.lizard_cc,warning,candidate_pairs_iter: CC=17 exceeds limit 15,647
      complexity.lizard_cc,warning,syntactic_feasibility: CC=81 exceeds limit 15,728
      complexity.lizard_length,warning,syntactic_feasibility: 143 lines exceeds limit 100,728
      complexity.lizard_cc,warning,__init__: CC=17 exceeds limit 15,1056
      complexity.lizard_cc,warning,__init__: CC=29 exceeds limit 15,1145
  networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/tests/test_vf2pp_helpers.py,0.58
    issues[7]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,test_no_covered_neighbors_with_labels: 116 lines exceeds limit 100,581
      complexity.lizard_length,warning,test_covered_neighbors_with_labels: 107 lines exceeds limit 100,792
      complexity.lizard_length,warning,test_cut_different_labels: 105 lines exceeds limit 100,1314
      complexity.lizard_length,warning,test_cut_different_labels: 120 lines exceeds limit 100,1940
      complexity.lizard_length,warning,test_feasibility_different_labels: 104 lines exceeds limit 100,2192
      complexity.lizard_length,warning,test_cut_different_labels: 109 lines exceeds limit 100,2625
  networkx-3.6.1-py3-none-any/networkx/algorithms/similarity.py,0.58
    issues[7]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,optimize_edit_paths.match_edges: CC=38 exceeds limit 15,736
      complexity.lizard_cc,warning,optimize_edit_paths.get_edit_ops: CC=25 exceeds limit 15,839
      complexity.lizard_cc,warning,optimize_edit_paths.get_edit_paths: CC=23 exceeds limit 15,938
      complexity.lizard_cc,warning,optimize_edit_paths: CC=42 exceeds limit 15,540
      complexity.lizard_length,warning,optimize_edit_paths: 132 lines exceeds limit 100,540
      complexity.lizard_cc,warning,_simrank_similarity_python: CC=16 exceeds limit 15,1342
  networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/ismags.py,0.61
    issues[6]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,make_partition: CC=16 exceeds limit 15,162
      complexity.lizard_cc,warning,create_aligned_partitions: CC=19 exceeds limit 15,543
      complexity.lizard_cc,warning,_map_nodes: CC=32 exceeds limit 15,877
      complexity.lizard_cc,warning,_refine_opp: CC=19 exceeds limit 15,1130
      complexity.lizard_cc,warning,_process_ordered_pair_partitions: CC=23 exceeds limit 15,1207
  networkx-3.6.1-py3-none-any/networkx/algorithms/matching.py,0.61
    issues[6]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,max_weight_matching.addBlossom: CC=26 exceeds limit 15,575
      complexity.lizard_cc,warning,max_weight_matching.max_weight_matching.expandBlossom._recurse: CC=18 exceeds limit 15,676
      complexity.lizard_cc,warning,max_weight_matching.verifyOptimum: CC=18 exceeds limit 15,884
      complexity.lizard_cc,warning,max_weight_matching: CC=69 exceeds limit 15,321
      complexity.lizard_length,warning,max_weight_matching: 162 lines exceeds limit 100,321
  networkx-3.6.1-py3-none-any/networkx/readwrite/gml.py,0.61
    issues[6]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,parse_gml_lines.tokenize: CC=16 exceeds limit 15,302
      complexity.lizard_cc,warning,parse_gml_lines.parse_kv: CC=16 exceeds limit 15,376
      complexity.lizard_cc,warning,parse_gml_lines: CC=24 exceeds limit 15,299
      complexity.lizard_cc,warning,literal_stringizer.stringize: CC=23 exceeds limit 15,550
      complexity.lizard_cc,warning,generate_gml.stringize: CC=29 exceeds limit 15,711
  src/nlp2cmd/automation/action_planner.py,0.61
    issues[6]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_try_canvas_decomposition: CC=19 exceeds limit 15,985
      complexity.lizard_cc,warning,_generate_canvas_plan_with_llm: CC=25 exceeds limit 15,1147
      complexity.lizard_length,warning,_generate_canvas_plan_with_llm: 164 lines exceeds limit 100,1147
      complexity.lizard_length,warning,_generate_rule_based_canvas_plan: 108 lines exceeds limit 100,1345
      complexity.lizard_cc,warning,_search_vector_db_for_pattern: CC=19 exceeds limit 15,1480
  src/nlp2cmd/cli/main.py,0.61
    issues[6]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_register_subcommands_for_args: CC=23 exceeds limit 15,109
      complexity.lizard_cc,warning,_run_preflight_checks: CC=23 exceeds limit 15,191
      complexity.lizard_cc,warning,main: CC=71 exceeds limit 15,394
      complexity.lizard_length,warning,main: 225 lines exceeds limit 100,394
      complexity.lizard_cc,warning,cli_entry_point: CC=21 exceeds limit 15,742
  src/nlp2cmd/execution/runner.py,0.61
    issues[6]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,run_command: CC=50 exceeds limit 15,147
      complexity.lizard_length,warning,run_command: 219 lines exceeds limit 100,147
      complexity.lizard_cc,warning,_maybe_explore_missing_resource: CC=20 exceeds limit 15,497
      complexity.lizard_cc,warning,run_with_recovery: CC=54 exceeds limit 15,585
      complexity.lizard_length,warning,run_with_recovery: 193 lines exceeds limit 100,585
  src/nlp2cmd/validators/__init__.py,0.61
    issues[6]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,validate: CC=34 exceeds limit 15,184
      complexity.lizard_cc,warning,validate: CC=31 exceeds limit 15,289
      complexity.lizard_cc,warning,_find_docker_image: CC=16 exceeds limit 15,420
      complexity.lizard_cc,warning,validate: CC=50 exceeds limit 15,495
      complexity.lizard_cc,warning,validate: CC=58 exceeds limit 15,620
  networkx-3.6.1-py3-none-any/networkx/algorithms/flow/capacityscaling.py,0.64
    issues[5]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_build_residual_network: CC=20 exceeds limit 15,42
      complexity.lizard_cc,warning,_build_flow_dict: CC=20 exceeds limit 15,108
      complexity.lizard_cc,warning,capacity_scaling: CC=37 exceeds limit 15,155
      complexity.lizard_length,warning,capacity_scaling: 101 lines exceeds limit 100,155
  networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/vf2pp.py,0.64
    issues[5]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_matching_order: CC=19 exceeds limit 15,375
      complexity.lizard_cc,warning,_find_candidates_Di: CC=16 exceeds limit 15,529
      complexity.lizard_cc,warning,_cut_PT: CC=28 exceeds limit 15,635
      complexity.lizard_cc,warning,_restore_Tinout_Di: CC=35 exceeds limit 15,1011
  networkx-3.6.1-py3-none-any/networkx/readwrite/text.py,0.64
    issues[5]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,generate_network_text: CC=42 exceeds limit 15,73
      complexity.lizard_length,warning,generate_network_text: 148 lines exceeds limit 100,73
      complexity.lizard_cc,warning,_parse_network_text: CC=32 exceeds limit 15,647
      complexity.lizard_length,warning,_parse_network_text: 115 lines exceeds limit 100,647
  src/nlp2cmd/adapters/dynamic.py,0.64
    issues[5]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,register_schema_source: CC=22 exceeds limit 15,164
      complexity.lizard_cc,warning,_generate_from_template: CC=25 exceeds limit 15,339
      complexity.lizard_cc,warning,_generate_shell_command: CC=16 exceeds limit 15,447
      complexity.lizard_cc,warning,_generate_api_command: CC=18 exceeds limit 15,488
  src/nlp2cmd/cli/commands/generate.py,0.64
    issues[5]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,handle_generate_query: CC=41 exceeds limit 15,24
      complexity.lizard_length,warning,handle_generate_query: 160 lines exceeds limit 100,24
      complexity.lizard_cc,warning,_execute_multi_step_with_video: CC=63 exceeds limit 15,324
      complexity.lizard_length,warning,_execute_multi_step_with_video: 308 lines exceeds limit 100,324
  src/nlp2cmd/generation/regex.py,0.64
    issues[5]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,__init__: 250 lines exceeds limit 100,339
      complexity.lizard_cc,warning,_load_patterns_from_json: CC=20 exceeds limit 15,598
      complexity.lizard_cc,warning,_process_match: CC=18 exceeds limit 15,686
      complexity.lizard_cc,warning,_post_process: CC=38 exceeds limit 15,761
  src/nlp2cmd/schema_driven.py,0.64
    issues[5]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_select_action: CC=41 exceeds limit 15,40
      complexity.lizard_cc,warning,_extract_params: CC=17 exceeds limit 15,110
      complexity.lizard_cc,warning,_render_http: CC=29 exceeds limit 15,191
      complexity.lizard_cc,warning,_render_shell: CC=25 exceeds limit 15,229
  src/nlp2cmd/step_handlers/session.py,0.64
    issues[5]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_handle_login_page: CC=22 exceeds limit 15,55
      complexity.lizard_cc,warning,_poll_for_key: CC=16 exceeds limit 15,189
      complexity.lizard_cc,warning,execute: CC=30 exceeds limit 15,264
      complexity.lizard_cc,warning,_find_best_link: CC=17 exceeds limit 15,331
  src/nlp2cmd/web_schema/form_handler.py,0.64
    issues[5]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,detect_form_fields: CC=37 exceeds limit 15,74
      complexity.lizard_length,warning,detect_form_fields: 234 lines exceeds limit 100,74
      complexity.lizard_cc,warning,automatic_fill._looks_like_honeypot_or_search: CC=25 exceeds limit 15,484
      complexity.lizard_cc,warning,fill_form: CC=27 exceeds limit 15,665
  tools/generation/generate_cmd_from_prompts.py,0.64
    issues[5]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_generate_simple: CC=144 exceeds limit 15,59
      complexity.lizard_length,warning,_generate_simple: 182 lines exceeds limit 100,59
      complexity.lizard_length,warning,create_enhanced_prompt_list: 114 lines exceeds limit 100,292
      complexity.lizard_cc,warning,main: CC=16 exceeds limit 15,431
  benchmarks/llm_benchmark.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,clean_command: CC=19 exceeds limit 15,462
      complexity.lizard_cc,warning,run_benchmark: CC=22 exceeds limit 15,526
      complexity.lizard_cc,warning,build_summary: CC=41 exceeds limit 15,648
  examples/03_integrations/web_development/nlp2cmd_web_controller.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,to_compose: CC=17 exceeds limit 15,75
      complexity.lizard_cc,warning,_detect_intent: CC=19 exceeds limit 15,490
      complexity.lizard_cc,warning,_extract_entities: CC=16 exceeds limit 15,538
  examples/09_online_drawing/_run_utils.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,dismiss_popups: CC=17 exceeds limit 15,180
      complexity.lizard_cc,warning,check_page_health: CC=22 exceeds limit 15,295
      complexity.lizard_cc,warning,discover_working_url: CC=27 exceeds limit 15,385
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/traveling_salesman.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,asadpour_atsp: CC=24 exceeds limit 15,361
      complexity.lizard_cc,warning,simulated_annealing_tsp: CC=21 exceeds limit 15,1050
      complexity.lizard_cc,warning,threshold_accepting_tsp: CC=20 exceeds limit 15,1280
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/group.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,group_betweenness_centrality: CC=30 exceeds limit 15,24
      complexity.lizard_cc,warning,prominent_group: CC=18 exceeds limit 15,241
      complexity.lizard_cc,warning,_heuristic: CC=16 exceeds limit 15,460
  networkx-3.6.1-py3-none-any/networkx/algorithms/coloring/equitable_coloring.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,procedure_P: CC=49 exceeds limit 15,141
      complexity.lizard_length,warning,procedure_P: 166 lines exceeds limit 100,141
      complexity.lizard_cc,warning,equitable_color: CC=17 exceeds limit 15,390
  networkx-3.6.1-py3-none-any/networkx/algorithms/cycles.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,simple_cycles: CC=29 exceeds limit 15,106
      complexity.lizard_cc,warning,chordless_cycles: CC=46 exceeds limit 15,478
      complexity.lizard_cc,warning,find_cycle: CC=19 exceeds limit 15,881
  networkx-3.6.1-py3-none-any/networkx/algorithms/d_separation.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,is_d_separator: CC=20 exceeds limit 15,231
      complexity.lizard_cc,warning,find_minimal_d_separator: CC=16 exceeds limit 15,339
      complexity.lizard_cc,warning,is_minimal_d_separator: CC=20 exceeds limit 15,446
  networkx-3.6.1-py3-none-any/networkx/algorithms/shortest_paths/weighted.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_dijkstra_multisource: CC=24 exceeds limit 15,784
      complexity.lizard_cc,warning,_inner_bellman_ford: CC=22 exceeds limit 15,1389
      complexity.lizard_cc,warning,bidirectional_dijkstra: CC=19 exceeds limit 15,2310
  networkx-3.6.1-py3-none-any/networkx/convert_matrix.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,from_pandas_edgelist: CC=20 exceeds limit 15,312
      complexity.lizard_cc,warning,to_numpy_array: CC=20 exceeds limit 15,882
      complexity.lizard_cc,warning,from_numpy_array: CC=29 exceeds limit 15,1121
  networkx-3.6.1-py3-none-any/networkx/drawing/layout.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,spring_layout: CC=29 exceeds limit 15,452
      complexity.lizard_cc,warning,forceatlas2_layout: CC=18 exceeds limit 15,1604
      complexity.lizard_length,warning,forceatlas2_layout: 112 lines exceeds limit 100,1604
  networkx-3.6.1-py3-none-any/networkx/generators/lattice.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,grid_2d_graph: CC=16 exceeds limit 15,37
      complexity.lizard_cc,warning,triangular_lattice_graph: CC=33 exceeds limit 15,200
      complexity.lizard_cc,warning,hexagonal_lattice_graph: CC=28 exceeds limit 15,307
  networkx-3.6.1-py3-none-any/networkx/readwrite/tests/test_graphml.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,setup_class: 290 lines exceeds limit 100,12
      complexity.lizard_length,warning,test_yfiles_extension: 125 lines exceeds limit 100,555
      complexity.lizard_length,warning,test_read_attributes_with_groups: 290 lines exceeds limit 100,777
  scripts/maintenance/auto_apply_refactors.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,apply_keywords_refactor: CC=20 exceeds limit 15,13
      complexity.lizard_length,warning,apply_keywords_refactor: 101 lines exceeds limit 100,13
      complexity.lizard_cc,warning,apply_templates_refactor: CC=16 exceeds limit 15,142
  scripts/maintenance/implement_core_integration.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,create_enhanced_intent_detector: 133 lines exceeds limit 100,147
      complexity.lizard_length,warning,create_polish_language_module: 153 lines exceeds limit 100,296
      complexity.lizard_length,warning,create_integration_script: 134 lines exceeds limit 100,594
  scripts/test-scripts/test_comprehensive_commands.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,run_command: CC=63 exceeds limit 15,31
      complexity.lizard_length,warning,run_command: 146 lines exceeds limit 100,31
      complexity.lizard_length,warning,generate_test_commands: 128 lines exceeds limit 100,235
  scripts/test-scripts/test_enhanced_context.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,test_enhanced_detection: CC=26 exceeds limit 15,14
      complexity.lizard_length,warning,test_enhanced_detection: 110 lines exceeds limit 100,14
      complexity.lizard_cc,warning,infer_intent_from_command: CC=49 exceeds limit 15,163
  scripts/test-scripts/test_multi_site_context.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,test_multi_site_context: CC=37 exceeds limit 15,14
      complexity.lizard_length,warning,test_multi_site_context: 148 lines exceeds limit 100,14
      complexity.lizard_cc,warning,infer_intent_from_command: CC=55 exceeds limit 15,207
  scripts/test-scripts/test_web_schema_context.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,test_web_schema_context: CC=31 exceeds limit 15,14
      complexity.lizard_length,warning,test_web_schema_context: 121 lines exceeds limit 100,14
      complexity.lizard_cc,warning,infer_intent_from_command: CC=55 exceeds limit 15,173
  src/nlp2cmd/adapters/browser.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,generate: CC=39 exceeds limit 15,337
      complexity.lizard_length,warning,generate: 173 lines exceeds limit 100,337
      complexity.lizard_cc,warning,validate_syntax: CC=25 exceeds limit 15,553
  src/nlp2cmd/automation/password_store.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_find_profile: CC=16 exceeds limit 15,91
      complexity.lizard_cc,warning,get_credentials: CC=17 exceeds limit 15,672
      complexity.lizard_cc,warning,print_diagnosis: CC=36 exceeds limit 15,821
  src/nlp2cmd/cli/commands/interactive.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,process: 111 lines exceeds limit 100,74
      complexity.lizard_cc,warning,display_feedback: CC=17 exceeds limit 15,242
      complexity.lizard_cc,warning,_correction_loop: CC=24 exceeds limit 15,452
  src/nlp2cmd/cli/commands/run.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,handle_run_mode: CC=178 exceeds limit 15,51
      complexity.lizard_length,warning,handle_run_mode: 637 lines exceeds limit 100,51
      complexity.lizard_cc,warning,_suggest_next_steps: CC=16 exceeds limit 15,840
  src/nlp2cmd/generation/keywords/keyword_detector.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,detect: CC=16 exceeds limit 15,241
      complexity.lizard_cc,warning,_fast_path_detection: CC=73 exceeds limit 15,366
      complexity.lizard_length,warning,_fast_path_detection: 523 lines exceeds limit 100,366
  src/nlp2cmd/llm/validator.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_deterministic_pre_check: CC=43 exceeds limit 15,295
      complexity.lizard_length,warning,_deterministic_pre_check: 117 lines exceeds limit 100,295
      complexity.lizard_cc,warning,_build_dynamic_hints: CC=38 exceeds limit 15,463
  src/nlp2cmd/nlp_light/semantic_shell.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,extract_intent: CC=32 exceeds limit 15,44
      complexity.lizard_cc,warning,generate_plan: CC=18 exceeds limit 15,87
      complexity.lizard_cc,warning,_extract_username_with_nlp: CC=29 exceeds limit 15,290
  src/nlp2cmd/orchestration/handlers.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,handle_inject_code: CC=16 exceeds limit 15,218
      complexity.lizard_cc,warning,handle_discover_url: CC=18 exceeds limit 15,451
      complexity.lizard_cc,warning,handle_check_health: CC=17 exceeds limit 15,512
  src/nlp2cmd/pipeline_runner_browser.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_run_dom_dql: CC=28 exceeds limit 15,33
      complexity.lizard_cc,warning,_run_dom_multi_action: CC=279 exceeds limit 15,117
      complexity.lizard_length,warning,_run_dom_multi_action: 998 lines exceeds limit 100,117
  src/nlp2cmd/pipeline_runner_plans.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,execute_action_plan: CC=166 exceeds limit 15,182
      complexity.lizard_length,warning,execute_action_plan: 623 lines exceeds limit 100,182
      complexity.lizard_cc,warning,_llm_suggest_article_selectors: CC=21 exceeds limit 15,1125
  src/nlp2cmd/pipeline_runner_utils.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_is_junk_field: CC=20 exceeds limit 15,98
      complexity.lizard_cc,warning,_filter_form_fields: CC=18 exceeds limit 15,159
      complexity.lizard_cc,warning,load_from_data: CC=18 exceeds limit 15,286
  src/nlp2cmd/schema_extraction/python_extractors.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_extract_typer_command: CC=30 exceeds limit 15,108
      complexity.lizard_cc,warning,_extract_click_command: CC=16 exceeds limit 15,185
      complexity.lizard_cc,warning,_extract_argparse_cli: CC=20 exceeds limit 15,347
  src/nlp2cmd/schema_extraction/script_extractors.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,extract_from_source: CC=30 exceeds limit 15,47
      complexity.lizard_length,warning,extract_from_source: 109 lines exceeds limit 100,47
      complexity.lizard_cc,warning,extract_from_source: CC=18 exceeds limit 15,188
  src/nlp2cmd/skills/drawing/text_to_shape.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,validate_geometry: CC=19 exceeds limit 15,41
      complexity.lizard_cc,warning,generate: CC=24 exceeds limit 15,221
      complexity.lizard_cc,warning,_parse_response: CC=16 exceeds limit 15,326
  tools/generation/generate_cmd_simple.py,0.68
    issues[4]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,load_prompts: 123 lines exceeds limit 100,11
      complexity.lizard_cc,warning,generate_command: CC=187 exceeds limit 15,202
      complexity.lizard_length,warning,generate_command: 246 lines exceeds limit 100,202
  examples/01_basics/shell_fundamentals/environment_analysis.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,main: CC=37 exceeds limit 15,36
      complexity.lizard_length,warning,main: 177 lines exceeds limit 100,36
  examples/01_basics/shell_fundamentals/feedback_loop.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,simulate_interactive_session: CC=17 exceeds limit 15,24
      complexity.lizard_length,warning,simulate_interactive_session: 212 lines exceeds limit 100,24
  examples/03_integrations/pipelines/infrastructure_health.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,main: CC=19 exceeds limit 15,118
      complexity.lizard_length,warning,main: 117 lines exceeds limit 100,118
  examples/03_integrations/web_development/demo.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,demo_nlp_commands: CC=42 exceeds limit 15,33
      complexity.lizard_length,warning,demo_nlp_commands: 134 lines exceeds limit 100,33
  examples/03_integrations/web_development/demo_auto.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,run_demo_with_test: CC=20 exceeds limit 15,27
      complexity.lizard_cc,warning,interactive_mode: CC=20 exceeds limit 15,267
  examples/03_integrations/web_development/demo_batch.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,run_batch_demo: CC=32 exceeds limit 15,21
      complexity.lizard_length,warning,run_batch_demo: 111 lines exceeds limit 100,21
  examples/04_domain_specific/debugging/test_improvements.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,test_shell_improvements: CC=18 exceeds limit 15,19
      complexity.lizard_length,warning,test_shell_improvements: 126 lines exceeds limit 100,19
  examples/04_domain_specific/debugging/validation.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,get_test_cases: 477 lines exceeds limit 100,37
      complexity.lizard_cc,warning,generate_report: CC=16 exceeds limit 15,622
  examples/04_domain_specific/polish_llm_integration/test_bielik_simple.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,test_bielik: CC=19 exceeds limit 15,18
      complexity.lizard_length,warning,test_bielik: 135 lines exceeds limit 100,18
  examples/08_llm_validation/benchmark_validator.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,run_benchmark: CC=28 exceeds limit 15,235
      complexity.lizard_cc,warning,compare_benchmarks: CC=16 exceeds limit 15,340
  examples/09_online_drawing/05_autonomous/run.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,run_autonomous: CC=17 exceeds limit 15,46
      complexity.lizard_length,warning,run_autonomous: 104 lines exceeds limit 100,46
  examples/09_online_drawing/06_visual_validator/run.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,draw_and_validate: CC=21 exceeds limit 15,52
      complexity.lizard_length,warning,draw_and_validate: 111 lines exceeds limit 100,52
  examples/10_online_code_editors/01_codepen_live.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,main: CC=21 exceeds limit 15,120
      complexity.lizard_length,warning,main: 115 lines exceeds limit 100,120
  examples/10_online_code_editors/02_mycompiler_run.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,main: CC=32 exceeds limit 15,132
      complexity.lizard_length,warning,main: 216 lines exceeds limit 100,132
  examples/10_online_code_editors/03_adaptive_code.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,main: CC=37 exceeds limit 15,152
      complexity.lizard_length,warning,main: 219 lines exceeds limit 100,152
  examples/10_online_code_editors/04_jsfiddle_frontend.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,main: CC=19 exceeds limit 15,128
      complexity.lizard_length,warning,main: 124 lines exceeds limit 100,128
  examples/_verbose_helper.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,dump_page_schema: CC=27 exceeds limit 15,46
      complexity.lizard_length,warning,dump_page_schema: 184 lines exceeds limit 100,46
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/modularity_max.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_greedy_modularity_communities_generator: CC=34 exceeds limit 15,17
      complexity.lizard_cc,warning,naive_greedy_modularity_communities: CC=16 exceeds limit 15,361
  networkx-3.6.1-py3-none-any/networkx/algorithms/connectivity/cuts.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,minimum_node_cut: CC=17 exceeds limit 15,310
      complexity.lizard_cc,warning,minimum_edge_cut: CC=20 exceeds limit 15,456
  networkx-3.6.1-py3-none-any/networkx/algorithms/connectivity/tests/test_edge_augmentation.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_augment_and_check: CC=19 exceeds limit 15,276
      complexity.lizard_cc,warning,_check_augmentations: CC=17 exceeds limit 15,401
  networkx-3.6.1-py3-none-any/networkx/algorithms/distance_measures.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_extrema_bounding: CC=44 exceeds limit 15,22
      complexity.lizard_cc,warning,resistance_distance: CC=20 exceeds limit 15,783
  networkx-3.6.1-py3-none-any/networkx/algorithms/flow/networksimplex.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,network_simplex: CC=44 exceeds limit 15,332
      complexity.lizard_length,warning,network_simplex: 106 lines exceeds limit 100,332
  networkx-3.6.1-py3-none-any/networkx/algorithms/minors/contraction.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_quotient_graph: CC=17 exceeds limit 15,347
      complexity.lizard_cc,warning,contracted_nodes: CC=16 exceeds limit 15,431
  networkx-3.6.1-py3-none-any/networkx/algorithms/operators/product.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_directed_edges_cross_edges: CC=17 exceeds limit 15,33
      complexity.lizard_cc,warning,_undirected_edges_cross_edges: CC=17 exceeds limit 15,52
  networkx-3.6.1-py3-none-any/networkx/algorithms/shortest_paths/generic.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,shortest_path: CC=16 exceeds limit 15,43
      complexity.lizard_cc,warning,average_shortest_path_length: CC=16 exceeds limit 15,326
  networkx-3.6.1-py3-none-any/networkx/algorithms/simple_paths.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_bidirectional_pred_succ: CC=20 exceeds limit 15,658
      complexity.lizard_cc,warning,_bidirectional_dijkstra: CC=25 exceeds limit 15,763
  networkx-3.6.1-py3-none-any/networkx/algorithms/tree/branchings.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,maximum_branching: CC=23 exceeds limit 15,191
      complexity.lizard_length,warning,maximum_branching: 101 lines exceeds limit 100,191
  networkx-3.6.1-py3-none-any/networkx/algorithms/tree/mst.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,kruskal_mst_edges: CC=17 exceeds limit 15,146
      complexity.lizard_cc,warning,prim_mst_edges: CC=30 exceeds limit 15,255
  networkx-3.6.1-py3-none-any/networkx/algorithms/triads.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,triadic_census: CC=29 exceeds limit 15,131
      complexity.lizard_cc,warning,triad_type: CC=25 exceeds limit 15,407
  networkx-3.6.1-py3-none-any/networkx/convert.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,to_networkx_graph: CC=25 exceeds limit 15,34
      complexity.lizard_cc,warning,from_dict_of_dicts: CC=26 exceeds limit 15,374
  networkx-3.6.1-py3-none-any/networkx/generators/joint_degree_seq.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,joint_degree_graph: CC=21 exceeds limit 15,146
      complexity.lizard_cc,warning,directed_joint_degree_graph: CC=20 exceeds limit 15,473
  networkx-3.6.1-py3-none-any/networkx/generators/random_graphs.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,dual_barabasi_albert_graph: CC=16 exceeds limit 15,737
      complexity.lizard_cc,warning,extended_barabasi_albert_graph: CC=27 exceeds limit 15,842
  networkx-3.6.1-py3-none-any/networkx/generators/social.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,davis_southern_women_graph: 136 lines exceeds limit 100,105
      complexity.lizard_length,warning,les_miserables_graph: 257 lines exceeds limit 100,290
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_small.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,test_properties_of_named_small_graphs: CC=24 exceeds limit 15,31
      complexity.lizard_length,warning,test_properties_of_named_small_graphs: 137 lines exceeds limit 100,31
  networkx-3.6.1-py3-none-any/networkx/readwrite/gexf.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,add_attributes: CC=21 exceeds limit 15,477
      complexity.lizard_cc,warning,make_graph: CC=16 exceeds limit 15,730
  networkx-3.6.1-py3-none-any/networkx/readwrite/graphml.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,add_graph_element: CC=21 exceeds limit 15,749
      complexity.lizard_cc,warning,decode_data_elements: CC=17 exceeds limit 15,961
  networkx-3.6.1-py3-none-any/networkx/readwrite/multiline_adjlist.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,generate_multiline_adjlist: CC=23 exceeds limit 15,39
      complexity.lizard_cc,warning,parse_multiline_adjlist: CC=18 exceeds limit 15,195
  networkx-3.6.1-py3-none-any/networkx/readwrite/tests/test_text.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,test_write_network_text_iterative_add_directed_edges: 141 lines exceeds limit 100,309
      complexity.lizard_length,warning,test_write_network_text_graph_max_depth: 104 lines exceeds limit 100,1167
  scripts/install_desktop_tools.sh,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,main: CC=22 exceeds limit 15,30
      complexity.lizard_length,warning,main: 108 lines exceeds limit 100,30
  scripts/maintenance/fix_comprehensive_test_issues.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,analyze_issues: CC=17 exceeds limit 15,28
      complexity.lizard_cc,warning,identify_root_causes: CC=17 exceeds limit 15,94
  src/nlp2cmd/adapters/canvas.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,execute_drawing_plan: CC=60 exceeds limit 15,445
      complexity.lizard_length,warning,execute_drawing_plan: 314 lines exceeds limit 100,445
  src/nlp2cmd/automation/feedback_loop.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,extract_page_context: CC=29 exceeds limit 15,108
      complexity.lizard_cc,warning,classify_failure: CC=21 exceeds limit 15,262
  src/nlp2cmd/cli/debug_info.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,show_schema_info: CC=20 exceeds limit 15,17
      complexity.lizard_cc,warning,show_decision_tree_info: CC=17 exceeds limit 15,103
  src/nlp2cmd/dom_actions/companies.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_extract_websites: CC=21 exceeds limit 15,238
      complexity.lizard_cc,warning,_find_external_website: CC=17 exceeds limit 15,333
  src/nlp2cmd/feedback/__init__.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,analyze: CC=41 exceeds limit 15,142
      complexity.lizard_length,warning,analyze: 123 lines exceeds limit 100,142
  src/nlp2cmd/generation/enhanced_context.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_build_semantic_index: CC=22 exceeds limit 15,201
      complexity.lizard_cc,warning,_extract_entities: CC=22 exceeds limit 15,284
  src/nlp2cmd/generation/evolutionary_cache.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_try_polish_template: CC=16 exceeds limit 15,637
      complexity.lizard_cc,warning,lookup_multistep: CC=23 exceeds limit 15,928
  src/nlp2cmd/generation/keywords/keyword_patterns.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_load_patterns_from_json: CC=19 exceeds limit 15,73
      complexity.lizard_cc,warning,_load_detector_config_from_json: CC=33 exceeds limit 15,128
  src/nlp2cmd/generation/pipeline.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,process: CC=54 exceeds limit 15,128
      complexity.lizard_length,warning,process: 156 lines exceeds limit 100,128
  src/nlp2cmd/generation/thermodynamic.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,generate: CC=24 exceeds limit 15,135
      complexity.lizard_length,warning,generate: 120 lines exceeds limit 100,135
  src/nlp2cmd/generation/thermodynamic_components.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,__post_init__: CC=38 exceeds limit 15,73
      complexity.lizard_cc,warning,_extract_variables: CC=16 exceeds limit 15,249
  src/nlp2cmd/generation/train_model.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,train_all_models: CC=29 exceeds limit 15,223
      complexity.lizard_length,warning,train_all_models: 124 lines exceeds limit 100,223
  src/nlp2cmd/intelligent/command_detector.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,__init__: 187 lines exceeds limit 100,25
      complexity.lizard_cc,warning,_load_config_from_json: CC=31 exceeds limit 15,229
  src/nlp2cmd/llm/router.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,_builtin_model_list: 113 lines exceeds limit 100,185
      complexity.lizard_cc,warning,_call_direct_fallback: CC=17 exceeds limit 15,671
  src/nlp2cmd/orchestration/engine.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,run: CC=19 exceeds limit 15,166
      complexity.lizard_cc,warning,_parse_json: CC=17 exceeds limit 15,560
  src/nlp2cmd/parsing/toon_parser.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_parse_lines: CC=28 exceeds limit 15,55
      complexity.lizard_cc,warning,_node_to_dict: CC=16 exceeds limit 15,340
  src/nlp2cmd/pipeline_runner_desktop.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_execute_desktop_plan_step: CC=44 exceeds limit 15,117
      complexity.lizard_length,warning,_execute_desktop_plan_step: 152 lines exceeds limit 100,117
  src/nlp2cmd/plan_execution/plan_executor.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_execute_desktop_mode: CC=33 exceeds limit 15,199
      complexity.lizard_length,warning,_execute_desktop_mode: 105 lines exceeds limit 100,199
  src/nlp2cmd/schemas/__init__.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,_register_builtin_schemas: 116 lines exceeds limit 100,110
      complexity.lizard_cc,warning,_validate_dockerfile: CC=26 exceeds limit 15,670
  src/nlp2cmd/skills/drawing/object_fetcher.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,parse_svg_path: CC=41 exceeds limit 15,35
      complexity.lizard_length,warning,parse_svg_path: 125 lines exceeds limit 100,35
  src/nlp2cmd/step_handlers/extraction.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,execute: CC=22 exceeds limit 15,27
      complexity.lizard_cc,warning,execute: CC=24 exceeds limit 15,231
  src/nlp2cmd/web_schema/form_data_loader.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_add_selector_to_type_selectors: CC=18 exceeds limit 15,263
      complexity.lizard_cc,warning,_build_field_values: CC=16 exceeds limit 15,414
  tests/unit/test_typo_tolerance.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,test_typo_tolerance: CC=17 exceeds limit 15,15
      complexity.lizard_length,warning,test_typo_tolerance: 104 lines exceeds limit 100,15
  tools/manual_tests/test_multisentence_logs_and_parsing.py,0.71
    issues[3]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,main: CC=71 exceeds limit 15,367
      complexity.lizard_length,warning,main: 197 lines exceeds limit 100,367
  docker/novnc/demos/demo_desktop_gui.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,run_demo: 147 lines exceeds limit 100,90
  examples/01_basics/sql_basics/advanced.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,main: 268 lines exceeds limit 100,23
  examples/01_basics/sql_basics/workflows.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,main: 215 lines exceeds limit 100,30
  examples/02_benchmarks/sequential_testing/benchmark.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,main: 107 lines exceeds limit 100,44
  examples/03_integrations/toon_format/comparison_demo.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_parse_file: CC=17 exceeds limit 15,104
  examples/03_integrations/toon_format/practical_usage.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,show_real_world_examples: 145 lines exceeds limit 100,144
  examples/03_integrations/validation/config_validation.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,main: 217 lines exceeds limit 100,47
  examples/04_domain_specific/debugging/intents.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,debug_intents: 102 lines exceeds limit 100,19
  examples/04_domain_specific/polish_llm_integration/example_pdf_search.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,generate_pdf_search_command: CC=25 exceeds limit 15,290
  examples/04_domain_specific/polish_llm_integration/test_polish_llm.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,test_polish_queries: CC=18 exceeds limit 15,206
  examples/05_advanced_features/schema_driven_architecture/end_to_end_demo.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,main: 183 lines exceeds limit 100,145
  examples/06_desktop_automation/09_complex_commands/run.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,main: CC=16 exceeds limit 15,24
  examples/06_tools_and_utilities/migration_tools/demo_versioned_schemas.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,demonstrate_schema_updates: 112 lines exceeds limit 100,99
  examples/08_api_key_management/01_diagnose_credentials/run.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,main: CC=17 exceeds limit 15,21
  examples/09_online_drawing/_old/03_adaptive_drawing.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,main: 110 lines exceeds limit 100,101
  networkx-3.6.1-py3-none-any/networkx/algorithms/assortativity/neighbor_degree.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,average_neighbor_degree: CC=21 exceeds limit 15,7
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/link_analysis.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,birank: CC=18 exceeds limit 15,9
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/matching.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,eppstein_matching: CC=17 exceeds limit 15,186
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/projection.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,projected_graph: CC=16 exceeds limit 15,19
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/betweenness.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_rescale: CC=17 exceeds limit 15,498
  networkx-3.6.1-py3-none-any/networkx/algorithms/cluster.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_directed_weighted_triangles_and_degree_iter: CC=16 exceeds limit 15,195
  networkx-3.6.1-py3-none-any/networkx/algorithms/coloring/greedy_coloring.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_greedy_coloring_with_interchange: CC=23 exceeds limit 15,442
  networkx-3.6.1-py3-none-any/networkx/algorithms/coloring/tests/test_coloring.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,test_hardest_prob: 160 lines exceeds limit 100,267
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/asyn_fluid.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,asyn_fluidc: CC=21 exceeds limit 15,17
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/bipartitions.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,kernighan_lin_bisection: CC=18 exceeds limit 15,58
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/divisive.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,edge_current_flow_betweenness_partition: CC=17 exceeds limit 15,108
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/louvain.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_one_level: CC=20 exceeds limit 15,227
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/lukes.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,lukes_partitioning: CC=26 exceeds limit 15,29
  networkx-3.6.1-py3-none-any/networkx/algorithms/components/biconnected.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_biconnected_dfs: CC=17 exceeds limit 15,339
  networkx-3.6.1-py3-none-any/networkx/algorithms/connectivity/connectivity.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,edge_connectivity: CC=21 exceeds limit 15,647
  networkx-3.6.1-py3-none-any/networkx/algorithms/connectivity/disjoint_paths.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,edge_disjoint_paths: CC=21 exceeds limit 15,27
  networkx-3.6.1-py3-none-any/networkx/algorithms/connectivity/edge_augmentation.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,unconstrained_bridge_augmentation: CC=20 exceeds limit 15,695
  networkx-3.6.1-py3-none-any/networkx/algorithms/connectivity/kcutsets.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,all_node_cuts: CC=36 exceeds limit 15,26
  networkx-3.6.1-py3-none-any/networkx/algorithms/connectivity/stoerwagner.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,stoer_wagner: CC=16 exceeds limit 15,17
  networkx-3.6.1-py3-none-any/networkx/algorithms/dag.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,all_topological_sorts: CC=17 exceeds limit 15,456
  networkx-3.6.1-py3-none-any/networkx/algorithms/distance_regular.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,intersection_array: CC=18 exceeds limit 15,119
  networkx-3.6.1-py3-none-any/networkx/algorithms/flow/preflowpush.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,preflow_push_impl: CC=32 exceeds limit 15,22
  networkx-3.6.1-py3-none-any/networkx/algorithms/flow/shortestaugmentingpath.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,shortest_augmenting_path_impl: CC=29 exceeds limit 15,15
  networkx-3.6.1-py3-none-any/networkx/algorithms/graphical.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,is_digraphical: CC=23 exceeds limit 15,376
  networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/tests/test_vf2pp.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,test_custom_multigraph3_same_labels: 113 lines exceeds limit 100,958
  networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/tree_isomorphism.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,rooted_tree_isomorphism: CC=19 exceeds limit 15,77
  networkx-3.6.1-py3-none-any/networkx/algorithms/link_analysis/hits_alg.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_hits_python: CC=17 exceeds limit 15,99
  networkx-3.6.1-py3-none-any/networkx/algorithms/link_analysis/pagerank_alg.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_pagerank_python: CC=16 exceeds limit 15,115
  networkx-3.6.1-py3-none-any/networkx/algorithms/lowest_common_ancestors.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,tree_all_pairs_lowest_common_ancestor: CC=24 exceeds limit 15,166
  networkx-3.6.1-py3-none-any/networkx/algorithms/planar_drawing.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,get_canonical_ordering: CC=25 exceeds limit 15,140
  networkx-3.6.1-py3-none-any/networkx/algorithms/planarity.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,remove_back_edges: CC=17 exceeds limit 15,655
  networkx-3.6.1-py3-none-any/networkx/algorithms/regular.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,k_factor: CC=21 exceeds limit 15,76
  networkx-3.6.1-py3-none-any/networkx/algorithms/shortest_paths/astar.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,astar_path: CC=16 exceeds limit 15,13
  networkx-3.6.1-py3-none-any/networkx/algorithms/sparsifiers.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,spanner: CC=27 exceeds limit 15,15
  networkx-3.6.1-py3-none-any/networkx/algorithms/summarization.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,dedensify: CC=17 exceeds limit 15,70
  networkx-3.6.1-py3-none-any/networkx/algorithms/swap.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,connected_double_edge_swap: CC=23 exceeds limit 15,234
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_triads.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,test_triadic_census_on_random_graph: CC=16 exceeds limit 15,222
  networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/edgebfs.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,edge_bfs: CC=17 exceeds limit 15,21
  networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/edgedfs.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,edge_dfs: CC=17 exceeds limit 15,19
  networkx-3.6.1-py3-none-any/networkx/classes/function.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,selfloop_edges: CC=33 exceeds limit 15,1258
  networkx-3.6.1-py3-none-any/networkx/classes/tests/dispatch_interface.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,convert_from_nx: CC=28 exceeds limit 15,67
  networkx-3.6.1-py3-none-any/networkx/classes/tests/test_reportviews.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,test_iterkeys: CC=18 exceeds limit 15,823
  networkx-3.6.1-py3-none-any/networkx/drawing/nx_agraph.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,from_agraph: CC=16 exceeds limit 15,37
  networkx-3.6.1-py3-none-any/networkx/drawing/nx_latex.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,to_latex_raw: CC=27 exceeds limit 15,140
  networkx-3.6.1-py3-none-any/networkx/drawing/nx_pydot.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,from_pydot: CC=18 exceeds limit 15,92
  networkx-3.6.1-py3-none-any/networkx/generators/community.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,stochastic_block_model: CC=36 exceeds limit 15,499
  networkx-3.6.1-py3-none-any/networkx/generators/degree_seq.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,directed_havel_hakimi_graph: CC=22 exceeds limit 15,535
  networkx-3.6.1-py3-none-any/networkx/generators/directed.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,scale_free_graph: CC=19 exceeds limit 15,192
  networkx-3.6.1-py3-none-any/networkx/generators/line.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_select_starting_cell: CC=19 exceeds limit 15,413
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_internet_as_graphs.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,test_degree_values: CC=20 exceeds limit 15,119
  networkx-3.6.1-py3-none-any/networkx/linalg/tests/test_algebraic_connectivity.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,test_buckminsterfullerene: 109 lines exceeds limit 100,197
  networkx-3.6.1-py3-none-any/networkx/readwrite/edgelist.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,parse_edgelist: CC=16 exceeds limit 15,177
  networkx-3.6.1-py3-none-any/networkx/readwrite/json_graph/node_link.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,node_link_graph: CC=18 exceeds limit 15,144
  networkx-3.6.1-py3-none-any/networkx/readwrite/pajek.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,parse_pajek: CC=25 exceeds limit 15,167
  networkx-3.6.1-py3-none-any/networkx/readwrite/tests/test_gexf.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,setup_class: 119 lines exceeds limit 100,66
  networkx-3.6.1-py3-none-any/networkx/relabel.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_relabel_inplace: CC=25 exceeds limit 15,130
  networkx-3.6.1-py3-none-any/networkx/tests/test_all_random_functions.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,run_all_random_functions: 155 lines exceeds limit 100,41
  networkx-3.6.1-py3-none-any/networkx/utils/configs.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_on_setattr: CC=24 exceeds limit 15,348
  scripts/maintenance/apply_refactors_to_source.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,create_patch_files: 144 lines exceeds limit 100,60
  scripts/maintenance/generate_refactor_report.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,generate_refactor_report: 117 lines exceeds limit 100,9
  scripts/maintenance/llx_refactor.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,run_refactor: CC=18 exceeds limit 15,174
  scripts/test-scripts/test_summary_and_fixes.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,analyze_test_results: CC=26 exceeds limit 15,9
  src/nlp2cmd/adapters/desktop.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_build_actions: CC=31 exceeds limit 15,290
  src/nlp2cmd/adapters/dql.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_generate_qb_select: CC=22 exceeds limit 15,116
  src/nlp2cmd/adapters/shell_generators.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,generate_file_search: CC=23 exceeds limit 15,16
  src/nlp2cmd/automation/complex_planner.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_match_template: CC=24 exceeds limit 15,370
  src/nlp2cmd/automation/vector_store.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,initialize_default_patterns: 216 lines exceeds limit 100,260
  src/nlp2cmd/browser_manager/browser_connector.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,connect: CC=21 exceeds limit 15,23
  src/nlp2cmd/browser_manager/existing_browser_manager.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,get_token_interactive: CC=27 exceeds limit 15,77
  src/nlp2cmd/browser_manager/token_navigator.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,navigate: CC=18 exceeds limit 15,27
  src/nlp2cmd/cli/auto_repair.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,categorize_error: CC=22 exceeds limit 15,81
  src/nlp2cmd/core/core_backends.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,extract_entities: CC=19 exceeds limit 15,166
  src/nlp2cmd/core/core_transform.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,transform: CC=19 exceeds limit 15,120
  src/nlp2cmd/dom_actions/save.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_extract_candidate: CC=18 exceeds limit 15,92
  src/nlp2cmd/evolutionary/planner.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_get_available_strategies: CC=18 exceeds limit 15,355
  src/nlp2cmd/execution/shell_executor.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_parse_command: CC=17 exceeds limit 15,103
  src/nlp2cmd/executor/__init__.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_validate_step: CC=16 exceeds limit 15,249
  src/nlp2cmd/exploration/data_tree.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_match_node: CC=16 exceeds limit 15,180
  src/nlp2cmd/generation/ml_intent_classifier.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,create_default_training_data: 154 lines exceeds limit 100,380
  src/nlp2cmd/generation/template_generator.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_prepare_sql_entities: CC=34 exceeds limit 15,279
  src/nlp2cmd/intelligent/version_aware_generator.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_post_process_command: CC=17 exceeds limit 15,237
  src/nlp2cmd/llm/adaptive_learner.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,evolve: CC=31 exceeds limit 15,378
  src/nlp2cmd/orchestration/reflection.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,classify_error: CC=29 exceeds limit 15,74
  src/nlp2cmd/pipeline_runner_shell.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_run_shell: CC=27 exceeds limit 15,44
  src/nlp2cmd/plan_execution/step_orchestrator.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_trigger_error_fallback: CC=16 exceeds limit 15,518
  src/nlp2cmd/polish_support.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,normalize_stt_errors: CC=20 exceeds limit 15,137
  src/nlp2cmd/registry/__init__.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,_register_builtin_actions: 264 lines exceeds limit 100,216
  src/nlp2cmd/router/__init__.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_load_config_from_data: CC=34 exceeds limit 15,132
  src/nlp2cmd/schema_extraction/extractors.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,_parse_help_output: CC=16 exceeds limit 15,332
  src/nlp2cmd/skills/drawing/validation.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,check_progress: CC=21 exceeds limit 15,328
  src/nlp2cmd/step_handlers/interaction.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,execute: CC=19 exceeds limit 15,18
  src/nlp2cmd/streams/ftp_stream.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,execute: CC=16 exceeds limit 15,26
  src/nlp2cmd/streams/libvirt_stream.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,execute: CC=17 exceeds limit 15,95
  src/nlp2cmd/utils/external_cache.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,main: CC=16 exceeds limit 15,241
  src/nlp2cmd/utils/yaml_compat.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,safe_load: CC=24 exceeds limit 15,51
  tests/e2e/conftest.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,mock_sql_select: CC=20 exceeds limit 15,201
  tests/e2e/test_canvas_e2e.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,test_draw_ladybug_blueprint: CC=25 exceeds limit 15,205
  tools/analysis/compare_batches.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,compare_batch_files: CC=21 exceeds limit 15,8
  tools/analysis/compare_llm.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,compare_schemas: CC=16 exceeds limit 15,7
  tools/manual_tests/test_quick_30.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,test_first_30: CC=19 exceeds limit 15,11
  tools/schema/comprehensive_command_scanner.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_length,warning,_load_command_signatures: 162 lines exceeds limit 100,597
  tools/schema/intelligent_schema_generator.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,main: CC=17 exceeds limit 15,403
  tools/schema/update_schemas.py,0.74
    issues[2]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
      complexity.lizard_cc,warning,load_commands_from_files: CC=16 exceeds limit 15,11
  .markdownlint.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/backups/20260126_173553/tests/integration/test_workflows.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  .projektor/backups/20260126_173854/tests/integration/test_workflows.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  .projektor/last_plan_NLP2-3.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_164503/meta.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_164503/plan.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_164503/result.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_164503/validation_errors.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_165003/meta.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_165003/plan.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_165003/result.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_165003/validation_errors.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_165233/execution.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_165233/meta.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_165233/plan.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_165233/result.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_165524/meta.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_165524/plan.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_165524/plan_repaired.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_165524/result.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_165524/validation_errors.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_173544/execution.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_173544/meta.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_173544/plan.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_173544/plan_repaired.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_173544/result.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_173845/execution.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_173845/meta.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_173845/plan.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_173845/plan_repaired.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/runs/NLP2-3_20260126_173845/result.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/state.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/tickets/NLP2-1.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/tickets/NLP2-2.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  .projektor/tickets/NLP2-3.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  artifacts/benchmark_report.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  artifacts/ci_test_results.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  artifacts/comprehensive_test_results.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  artifacts/enhanced_context_test_results.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  artifacts/multi_site_test_results.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  artifacts/nlp2cmd_monitoring_log.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  artifacts/results/intelligent_nlp2cmd_results.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  artifacts/results/test_results_no_llm.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  artifacts/results/test_results_with_llm.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  artifacts/sequential_benchmark_results.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  artifacts/web_schema_test_results.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  benchmark_output/.nlp2cmd_bench/gemma2_2b/learned_schemas.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  benchmark_output/.nlp2cmd_bench/learned_schemas.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  benchmark_output/.nlp2cmd_bench/qwen2.5-coder_3b/learned_schemas.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  benchmark_output/.nlp2cmd_bench/qwen2.5_3b/learned_schemas.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  benchmark_output/benchmark_results.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  benchmark_output/learning_benchmark.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  benchmarks/learning_benchmark.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  benchmarks/thermodynamic_benchmark.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  code2llm_workaround.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  command_schemas/browser/click.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/browser/navigate.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/browser/open_url.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/browser/search.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/browser/type_text.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/black.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/cat.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/chmod.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/cp.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/df.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/docker.appspec.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/docker.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/eslint.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/find.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/free.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/git.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/gpg.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/grep.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/iconv.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/iptables.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/jq.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/kubectl.appspec.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/kubectl.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/ls.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/lsof.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/make.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/mongodump.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/mv.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/mysql.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/mysqldump.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/netstat.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/nmap.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/node.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/npm.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/nslookup.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/openssl.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/pip.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/ps.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/psql.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/pytest.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/python3.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/rm.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/rsync.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/sed.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/sensors.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/sort.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/split.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/ssh-keygen.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/tar.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/traceroute.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/uptime.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/commands/zip.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/docker.appspec.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/docker.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/exports/all_schemas.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/exports/batches/batch_1_detailed.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/exports/batches/batch_1_test.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/exports/batches/batch_2_test.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/exports/batches/batch_3_final.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/exports/batches/batch_3_test.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/exports/batches/quick_batch_1_llm.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/exports/batches/quick_batch_2_llm.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/exports/batches/quick_batch_3_llm.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/exports/dynamic/generated_docker_dynamic_schema.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/exports/dynamic/generated_kubectl_dynamic_schema.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/exports/generated_schemas.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/exports/validated_schemas.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/index.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/keyboard/linux_shortcuts.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/keyboard/macos_shortcuts.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/keyboard/windows_shortcuts.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  command_schemas/nginx.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  config.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  config/litellm_config.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  data/command_detector.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  data/defaults.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  data/domain_weights.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  data/enhanced_domain_patterns.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  data/enhanced_intents.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  data/entities/apps.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  data/entities/colors.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  data/entities/shapes.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  data/expanded_phrases.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  data/form_data.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  data/form_schema.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  data/intents/close_app.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  data/intents/draw.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  data/intents/email_check.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  data/intents/email_compose.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  data/intents/minimize_all.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  data/intents/navigate.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  data/intents/new_tab.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  data/intents/open_app.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  data/intents/screenshot.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  data/keyword_intent_detector_config.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  data/multilingual_phrases.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  data/optimization_schema.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  data/patterns.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  data/phrase_database.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  data/polish_intent_mappings.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  data/polish_shell_patterns.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  data/polish_table_mappings.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  data/router_config.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  data/semantic_embeddings.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  data/shell_execution_policy.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  data/templates.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  docker/init-db.sql,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse SQL: Download error: Language 'SQL' not available for download. Available groups: [""all""]",
  docker/novnc/start-vnc.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/01_basics/app2schema/example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/01_basics/app2schema/generated_appspec.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/01_basics/docker_basics/01_basics_docker_nlp2cmd.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/01_basics/docker_basics/command_schemas/commands/docker.appspec.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/01_basics/docker_basics/example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/01_basics/docker_basics/file_repair.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/01_basics/kubernetes_basics/command_schemas/exports/dynamic/kubectl_dynamic_schema.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/01_basics/kubernetes_basics/example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/01_basics/shell_fundamentals/01_basics_shell_nlp2cmd.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/01_basics/shell_fundamentals/appspec_cache.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/01_basics/shell_fundamentals/example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/01_basics/shell_fundamentals/generated_shell_appspec.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/01_basics/shell_fundamentals/generated_shell_dynamic_schema.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/01_basics/shell_fundamentals/runtime_schemas.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/01_basics/shell_fundamentals/schema_cache.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/01_basics/shell_fundamentals/schema_cache.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/01_basics/sql_basics/example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/01_basics/sql_basics/llm_integration.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/02_benchmarks/performance_testing/benchmark.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/02_benchmarks/performance_testing/benchmark_report.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/02_benchmarks/sequential_testing/sequential_benchmark_results.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/03_integrations/pipelines/log_analysis.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/01_basic_usage/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/01_basic_usage/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/02_command_generator/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/02_command_generator/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/03_data_manager/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/03_data_manager/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/04_search_and_filter/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/04_search_and_filter/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/05_advanced_patterns/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/05_advanced_patterns/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/06_old_system_mock/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/06_old_system_mock/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/07_loading_performance/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/07_loading_performance/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/08_memory_usage/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/08_memory_usage/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/10_migration_guide/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/11_basic_integration/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/11_basic_integration/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/12_advanced_integration/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/12_advanced_integration/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/13_query_system/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/13_query_system/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/14_batch_processing/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/14_batch_processing/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/simple_demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/toon_format/usage_example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/web_development/01_basic_service_config/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/web_development/01_basic_service_config/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/03_integrations/web_development/02_deployment_planning/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/web_development/02_deployment_planning/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/03_integrations/web_development/03_docker_compose/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/web_development/03_docker_compose/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/03_integrations/web_development/04_service_deployment/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/web_development/04_service_deployment/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/03_integrations/web_development/05_infrastructure_management/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/web_development/05_infrastructure_management/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/03_integrations/web_development/simple_web_test.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/web_development/web_app_example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/03_integrations/web_development/web_generated/chat-service-config.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/_demo_helpers.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/api_key_prompts.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/bioinformatics/01_sequence_analysis/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/bioinformatics/01_sequence_analysis/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/bioinformatics/02_file_processing/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/bioinformatics/02_file_processing/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/bioinformatics/03_blast_operations/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/bioinformatics/03_blast_operations/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/bioinformatics/04_data_conversion/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/bioinformatics/04_data_conversion/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/bioinformatics/05_pipeline_automation/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/bioinformatics/05_pipeline_automation/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/bioinformatics/complete_examples.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/bioinformatics/example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/data_science/dsl_demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/data_science/example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/01_python_api_concept/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/01_python_api_concept/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/02_shell_commands/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/02_shell_commands/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/03_mixed_workflow/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/03_mixed_workflow/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/04_advanced_patterns/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/04_advanced_patterns/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/05_real_world_examples/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/05_real_world_examples/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/06_test_framework/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/06_test_framework/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/07_file_operations/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/07_file_operations/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/08_system_commands/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/08_system_commands/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/09_network_commands/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/09_network_commands/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/10_advanced_validation/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/10_advanced_validation/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/commands_demo.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/generator.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/keywords.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/debugging/simple_demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/devops/example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/drug_discovery/example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/education/example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/energy/example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/finance/example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/healthcare/example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/logistics/example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/physics/example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/polish_llm_integration/01_pdf_extraction/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/polish_llm_integration/01_pdf_extraction/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/polish_llm_integration/02_text_chunking/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/polish_llm_integration/02_text_chunking/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/polish_llm_integration/03_llm_search/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/polish_llm_integration/03_llm_search/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/polish_llm_integration/04_results_ranking/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/polish_llm_integration/04_results_ranking/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/polish_llm_integration/05_integration/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/polish_llm_integration/05_integration/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/polish_llm_integration/download_bielik.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/polish_llm_integration/mock_test_polish_llm.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/polish_llm_integration/setup_and_test_bielik.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/run_all.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/04_domain_specific/smart_cities/example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/05_advanced_features/dynamic_schemas/demo_enhanced.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/05_advanced_features/dynamic_schemas/demo_intelligent_nlp2cmd.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/05_advanced_features/dynamic_schemas/demo_persistent_storage.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/05_advanced_features/dynamic_schemas/demo_schema_flow.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/05_advanced_features/dynamic_schemas/demo_version_detection.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/05_advanced_features/dynamic_schemas/example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/05_advanced_features/dynamic_schemas/schema_flow_demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/05_advanced_features/dynamic_schemas/simple_schema_demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/05_advanced_features/schema_driven_architecture/01_architecture_overview/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/05_advanced_features/schema_driven_architecture/02_decision_router/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/05_advanced_features/schema_driven_architecture/02_decision_router/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/05_advanced_features/schema_driven_architecture/03_llm_planner/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/05_advanced_features/schema_driven_architecture/03_llm_planner/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/05_advanced_features/schema_driven_architecture/04_plan_executor/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/05_advanced_features/schema_driven_architecture/05_result_aggregator/demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/05_advanced_features/schema_driven_architecture/05_result_aggregator/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/05_advanced_features/schema_driven_architecture/manual_appspec.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/05_advanced_features/schema_driven_architecture/mvp.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/05_advanced_features/thermodynamic_computing/example.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/06_desktop_automation/00_full_lifecycle/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/06_desktop_automation/01_terminal/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/06_desktop_automation/02_calculator/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/06_desktop_automation/03_text_editor/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/06_desktop_automation/04_browser_tabs/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/06_desktop_automation/05_email_client/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/06_desktop_automation/06_env_extract/run.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/06_desktop_automation/07_canvas_drawing/run.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/06_desktop_automation/08_captcha_solver/run.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/06_tools_and_utilities/migration_tools/guide.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/07_browser_automation/01_screenshot_only.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/07_browser_automation/02_video_only.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/07_browser_automation/03_interactive_mode.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/07_browser_automation/04_oferteo_extraction.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/07_browser_automation/05_simple_formfill.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/07_browser_automation/06_formfill_with_discovery.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/07_browser_automation/07_batch_multiple.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/07_stream_protocols/example_http_api.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/07_stream_protocols/example_libvirt.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/07_stream_protocols/example_multi_stream.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/07_stream_protocols/example_rtsp.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/07_stream_protocols/example_ssh.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/08_api_key_management/01_diagnose_credentials_nlp2cmd.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/08_api_key_management/02_openrouter_key/run.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/08_api_key_management/03_github_token/run.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/08_api_key_management/04_huggingface_token/run.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/08_api_key_management/05_openai_key/run.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/08_api_key_management/06_multi_provider/run.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/08_llm_validation/benchmark_after.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/08_llm_validation/benchmark_before.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/08_llm_validation/demo_validation.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/08_llm_validation/test_feedback_loop.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/08_llm_validation/test_feedback_results.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/08_llm_validation/test_results.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/08_llm_validation/test_validator.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/01_draw_chat/run.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/01_draw_chat/screenshots/draw_chat_house_blue.meta.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/01_draw_chat/screenshots/draw_chat_house_blue_session.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/01_draw_chat/screenshots/draw_chat_star_red.meta.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/01_draw_chat/screenshots/draw_chat_star_red_session.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/02_picsart/run.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/02_picsart/screenshots/picsart_spiral_blue.meta.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/02_picsart/screenshots/picsart_spiral_blue_session.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/02_picsart/screenshots/picsart_spiral_red.meta.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/02_picsart/screenshots/picsart_spiral_red_session.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/03_adaptive/run.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/03_adaptive/screenshots/adaptive_circle_0000FF_jspaint.meta.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/03_adaptive/screenshots/adaptive_circle_FF0000_draw_chat.meta.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/03_adaptive/screenshots/adaptive_circle_session.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/03_adaptive/screenshots/adaptive_star_0000FF_draw_chat.meta.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/03_adaptive/screenshots/adaptive_star_0000FF_jspaint.meta.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/03_adaptive/screenshots/adaptive_star_FF0000_draw_chat.meta.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/03_adaptive/screenshots/adaptive_star_FF0000_jspaint.meta.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/03_adaptive/screenshots/adaptive_star_session.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/04_object_database/run.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/07_shape_gallery/run.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/08_search_demo/run.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/09_evolutionary_orchestrator/run.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/_old/01_draw_chat_shapes.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/_old/01_draw_chat_shapes_nlp2cmd.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/_old/02_picsart_painting.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/_old/02_picsart_painting_nlp2cmd.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/_old/03_adaptive_drawing_nlp2cmd.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/_old/04_object_database_drawing.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/_old/05_autonomous_drawing.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/run.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/screenshots/adaptive_circle_session.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/09_online_drawing/screenshots/adaptive_house_session.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  examples/10_online_code_editors/01_codepen_live_nlp2cmd.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/10_online_code_editors/02_mycompiler_run_nlp2cmd.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/10_online_code_editors/03_adaptive_code_nlp2cmd.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/10_online_code_editors/04_jsfiddle_frontend_nlp2cmd.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/10_online_code_editors/05_dynamic_executor.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/10_online_code_editors/05_dynamic_executor_nlp2cmd.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/_dynamic_orchestrator.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/_example_helpers.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/demo_screenshot_video.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/run_examples.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  examples/run_task.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  examples/show_metrics.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  generate_chunks.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  generate_quick.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  generate_working.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  generated_appspec.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  goal.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  install_vnc.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  jspaint_app_test4.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  manual_appspec.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/clique.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/clustering_coefficient.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/connectivity.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/density.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/distance_measures.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/dominating_set.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/kcomponents.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/matching.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/maxcut.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/ramsey.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/steinertree.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/tests/test_approx_clust_coeff.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/tests/test_clique.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/tests/test_connectivity.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/tests/test_density.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/tests/test_distance_measures.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/tests/test_dominating_set.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/tests/test_kcomponents.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/tests/test_matching.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/tests/test_maxcut.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/tests/test_ramsey.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/tests/test_steinertree.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/tests/test_traveling_salesman.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/tests/test_treewidth.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/tests/test_vertex_cover.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/treewidth.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/approximation/vertex_cover.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/assortativity/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/assortativity/connectivity.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/assortativity/correlation.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/assortativity/mixing.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/assortativity/pairs.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/assortativity/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/assortativity/tests/base_test.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/assortativity/tests/test_connectivity.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/assortativity/tests/test_correlation.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/assortativity/tests/test_mixing.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/assortativity/tests/test_neighbor_degree.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/assortativity/tests/test_pairs.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/asteroidal.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/basic.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/centrality.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/cluster.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/covering.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/edgelist.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/extendability.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/generators.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/matrix.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/redundancy.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/spectral.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/tests/test_basic.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/tests/test_centrality.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/tests/test_cluster.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/tests/test_covering.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/tests/test_edgelist.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/tests/test_extendability.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/tests/test_generators.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/tests/test_link_analysis.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/tests/test_matching.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/tests/test_matrix.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/tests/test_project.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/tests/test_redundancy.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bipartite/tests/test_spectral_bipartivity.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/boundary.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/bridges.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/broadcasting.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/betweenness_subset.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/closeness.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/current_flow_betweenness.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/current_flow_betweenness_subset.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/current_flow_closeness.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/degree_alg.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/dispersion.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/eigenvector.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/flow_matrix.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/harmonic.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/katz.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/laplacian.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/load.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/percolation.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/reaching.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/second_order.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/subgraph_alg.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_betweenness_centrality.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_betweenness_centrality_subset.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_closeness_centrality.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_current_flow_betweenness_centrality.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_current_flow_betweenness_centrality_subset.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_current_flow_closeness.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_degree_centrality.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_dispersion.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_eigenvector_centrality.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_group.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_harmonic_centrality.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_katz_centrality.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_laplacian_centrality.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_load_centrality.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_percolation_centrality.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_reaching.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_second_order_centrality.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_subgraph.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_trophic.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/tests/test_voterank.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/trophic.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/centrality/voterank_alg.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/chains.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/chordal.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/clique.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/coloring/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/coloring/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/communicability_alg.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/centrality.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/community_utils.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/kclique.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/label_propagation.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/leiden.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/local.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/quality.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/tests/test_asyn_fluid.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/tests/test_bipartitions.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/tests/test_centrality.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/tests/test_divisive.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/tests/test_kclique.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/tests/test_label_propagation.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/tests/test_leiden.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/tests/test_local.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/tests/test_louvain.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/tests/test_lukes.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/tests/test_modularity_max.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/tests/test_quality.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/community/tests/test_utils.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/components/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/components/attracting.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/components/connected.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/components/semiconnected.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/components/strongly_connected.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/components/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/components/tests/test_attracting.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/components/tests/test_biconnected.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/components/tests/test_connected.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/components/tests/test_semiconnected.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/components/tests/test_strongly_connected.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/components/tests/test_weakly_connected.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/components/weakly_connected.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/connectivity/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/connectivity/edge_kcomponents.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/connectivity/kcomponents.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/connectivity/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/connectivity/tests/test_connectivity.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/connectivity/tests/test_cuts.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/connectivity/tests/test_disjoint_paths.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/connectivity/tests/test_edge_kcomponents.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/connectivity/tests/test_kcomponents.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/connectivity/tests/test_kcutsets.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/connectivity/tests/test_stoer_wagner.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/connectivity/utils.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/core.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/covering.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/cuts.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/dominance.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/dominating.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/efficiency_measures.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/euler.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/flow/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/flow/boykovkolmogorov.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/flow/dinitz_alg.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/flow/edmondskarp.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/flow/gomory_hu.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/flow/maxflow.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/flow/mincost.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/flow/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/flow/tests/test_gomory_hu.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/flow/tests/test_maxflow.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/flow/tests/test_maxflow_large_graph.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/flow/tests/test_mincost.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/flow/tests/test_networksimplex.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/flow/utils.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/graph_hashing.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/hierarchy.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/hybrid.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/isolate.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/isomorph.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/matchhelpers.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/temporalisomorphvf2.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/tests/test_ismags.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/tests/test_isomorphism.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/tests/test_isomorphvf2.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/tests/test_match_helpers.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/tests/test_temporalisomorphvf2.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/tests/test_tree_isomorphism.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/tests/test_vf2userfunc.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/isomorphism/vf2userfunc.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/link_analysis/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/link_analysis/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/link_analysis/tests/test_hits.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/link_analysis/tests/test_pagerank.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/link_prediction.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/minors/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/minors/tests/test_contraction.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/mis.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/moral.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/node_classification.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/non_randomness.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/operators/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/operators/all.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/operators/binary.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/operators/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/operators/tests/test_all.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/operators/tests/test_binary.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/operators/tests/test_product.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/operators/tests/test_unary.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/operators/unary.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/perfect_graph.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/polynomials.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/reciprocity.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/richclub.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/shortest_paths/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/shortest_paths/dense.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/shortest_paths/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/shortest_paths/tests/test_astar.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/shortest_paths/tests/test_dense.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/shortest_paths/tests/test_dense_numpy.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/shortest_paths/tests/test_generic.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/shortest_paths/tests/test_unweighted.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/shortest_paths/tests/test_weighted.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/shortest_paths/unweighted.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/smallworld.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/smetric.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/structuralholes.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_asteroidal.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_boundary.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_bridges.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_broadcasting.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_chains.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_chordal.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_clique.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_cluster.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_communicability.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_core.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_covering.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_cuts.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_cycles.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_d_separation.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_dag.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_distance_measures.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_distance_regular.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_dominance.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_dominating.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_efficiency.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_euler.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_graph_hashing.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_graphical.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_hierarchy.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_hybrid.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_isolate.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_link_prediction.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_lowest_common_ancestors.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_matching.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_max_weight_clique.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_mis.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_moral.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_node_classification.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_non_randomness.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_perfect_graph.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_planar_drawing.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_planarity.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_polynomials.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_reciprocity.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_regular.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_richclub.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_similarity.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_simple_paths.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_smallworld.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_smetric.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_sparsifiers.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_structuralholes.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_summarization.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_swap.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_threshold.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_time_dependent.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_tournament.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_vitality.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_voronoi.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_walks.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tests/test_wiener.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/threshold.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/time_dependent.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tournament.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/beamsearch.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/breadth_first_search.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/depth_first_search.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/tests/test_beamsearch.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/tests/test_bfs.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/tests/test_dfs.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/tests/test_edgebfs.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/traversal/tests/test_edgedfs.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tree/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tree/coding.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tree/decomposition.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tree/distance_measures.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tree/operations.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tree/recognition.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tree/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tree/tests/test_branchings.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tree/tests/test_coding.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tree/tests/test_decomposition.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tree/tests/test_distance_measures.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tree/tests/test_mst.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tree/tests/test_operations.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/tree/tests/test_recognition.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/vitality.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/voronoi.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/walks.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/algorithms/wiener.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/coreviews.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/digraph.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/filters.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/graph.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/graphviews.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/multidigraph.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/multigraph.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/reportviews.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/tests/historical_tests.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/tests/test_coreviews.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/tests/test_digraph.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/tests/test_digraph_historical.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/tests/test_filters.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/tests/test_function.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/tests/test_graph.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/tests/test_graph_historical.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/tests/test_graphviews.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/tests/test_multidigraph.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/tests/test_multigraph.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/tests/test_special.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/classes/tests/test_subgraphviews.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/conftest.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/drawing/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/drawing/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/drawing/tests/test_agraph.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/drawing/tests/test_image_comparison_pylab_mpl.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/drawing/tests/test_latex.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/drawing/tests/test_layout.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/drawing/tests/test_pydot.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/drawing/tests/test_pylab.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/exception.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/atlas.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/classic.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/cographs.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/duplication.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/ego.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/expanders.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/geometric.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/harary_graph.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/internet_as_graphs.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/intersection.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/interval_graph.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/mycielski.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/nonisomorphic_trees.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/random_clustered.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/small.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/spectral_graph_forge.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/stochastic.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/sudoku.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_atlas.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_classic.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_cographs.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_community.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_degree_seq.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_directed.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_duplication.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_ego.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_expanders.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_geometric.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_harary_graph.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_intersection.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_interval_graph.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_joint_degree_seq.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_lattice.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_line.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_mycielski.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_nonisomorphic_trees.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_random_clustered.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_random_graphs.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_spectral_graph_forge.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_stochastic.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_sudoku.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_time_series.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_trees.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/tests/test_triads.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/time_series.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/trees.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/generators/triads.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/lazy_imports.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/linalg/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/linalg/algebraicconnectivity.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/linalg/attrmatrix.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/linalg/bethehessianmatrix.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/linalg/graphmatrix.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/linalg/laplacianmatrix.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/linalg/modularitymatrix.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/linalg/spectrum.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/linalg/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/linalg/tests/test_attrmatrix.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/linalg/tests/test_bethehessian.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/linalg/tests/test_graphmatrix.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/linalg/tests/test_laplacian.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/linalg/tests/test_modularity.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/linalg/tests/test_spectrum.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/adjlist.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/graph6.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/json_graph/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/json_graph/adjacency.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/json_graph/cytoscape.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/json_graph/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/json_graph/tests/test_adjacency.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/json_graph/tests/test_cytoscape.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/json_graph/tests/test_node_link.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/json_graph/tests/test_tree.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/json_graph/tree.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/leda.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/p2g.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/sparse6.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/tests/test_adjlist.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/tests/test_edgelist.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/tests/test_gml.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/tests/test_graph6.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/tests/test_leda.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/tests/test_p2g.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/tests/test_pajek.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/readwrite/tests/test_sparse6.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/tests/test_convert.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/tests/test_convert_numpy.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/tests/test_convert_pandas.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/tests/test_convert_scipy.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/tests/test_exceptions.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/tests/test_import.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/tests/test_lazy_imports.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/tests/test_relabel.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/tests/test_removed_functions_exception_messages.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/utils/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/utils/decorators.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/utils/heaps.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/utils/mapped_queue.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/utils/misc.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/utils/random_sequence.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/utils/rcm.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/utils/tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/utils/tests/test__init.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/utils/tests/test_backends.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/utils/tests/test_config.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/utils/tests/test_decorators.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/utils/tests/test_heaps.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/utils/tests/test_mapped_queue.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/utils/tests/test_misc.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/utils/tests/test_random_sequence.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/utils/tests/test_rcm.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/utils/tests/test_unionfind.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  networkx-3.6.1-py3-none-any/networkx/utils/union_find.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  out_call_graph.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  out_function_entries.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  out_interprocedural_decision_paths.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  planfile.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  prefact.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  project.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  projektor.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  pyproject.toml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse TOML: Download error: Language 'TOML' not available for download. Available groups: [""all""]",
  pyqual.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  run_all_tests.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  run_test.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  scripts/bump_version.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/maintenance/apply_complexity_refactors.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/maintenance/apply_nlp2cmd_fixes.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/maintenance/apply_polish_integration.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/maintenance/cyclomatic_complexity_refactor_report.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  scripts/maintenance/final_analysis_and_next_steps.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/maintenance/final_project_summary.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/maintenance/implement_high_priority_fixes.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/maintenance/refactor_detect_normalized.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/maintenance/refactor_shell_entities.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/maintenance/refactoring_summary.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/maintenance/restore_system.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/maintenance/split_pipeline_runner.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/setup_external.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/test-scripts/test_automated_monitoring.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/test-scripts/test_continuous_integration.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/test-scripts/test_final_validation.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/test-scripts/test_fixes_validation.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/test-scripts/test_improved_system.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/test-scripts/test_nlp2cmd_shell_integration.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/test-scripts/test_polish_integration.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/test-scripts/test_toon_core_integration.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/test-scripts/test_toon_integration.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/test_commands_docker.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  scripts/testing/compare_entity_extractors.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/testing/run_e2e_tests.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/thermodynamic/termo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/thermodynamic/termo1.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/thermodynamic/termo2.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  scripts/thermodynamic/termo_demo.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/app2schema/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/app2schema/__main__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/app2schema/cli.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/__main__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/adapters/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/adapters/appspec.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/adapters/base.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/adapters/docker.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/adapters/kubernetes.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/adapters/shell.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/adapters/sql.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/aggregator/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/appspec_runtime.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/automation/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/automation/captcha_solver.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/automation/drawing_blueprints.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/automation/env_extractor.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/automation/firefox_sessions.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/automation/mouse_controller.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/automation/service_configs.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/automation/shape_planner.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/automation/step_validator.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/browser_manager/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/browser_manager/base.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/browser_manager/cdp_detector.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/browser_token/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/browser_token/base.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/browser_token/browser_launcher.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/browser_token/hf_token_retriever.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/browser_token/token_navigator.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/browser_token/token_prompt_handler.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/canvas_planner/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/canvas_planner/base.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/canvas_planner/blueprint_planner.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/canvas_planner/llm_planner.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/canvas_planner/orchestrator.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/canvas_planner/rule_planner.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/canvas_planner/vector_planner.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/cli/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/cli/cache.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/cli/commands/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/cli/commands/examples.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/cli/commands/tools.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/cli/display.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/cli/helpers.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/cli/history.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/cli/markdown_output.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/cli/session_logger.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/cli/syntax_cache.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/cli/web_schema.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/context/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/context/disambiguator.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/core/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/core/core_models.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/core/toon_integration.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/data/browser_config/contact_paths.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  src/nlp2cmd/data/browser_config/junk_field_patterns.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  src/nlp2cmd/data/browser_config/selectors.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  src/nlp2cmd/data/command_detector.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/data/config/intents.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  src/nlp2cmd/data/config/services.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  src/nlp2cmd/data/defaults.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/data/expanded_phrases.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/data/form_data.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/data/form_schema.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/data/keyword_intent_detector_config.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/data/multilingual_phrases.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/data/optimization_schema.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/data/patterns.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/data/phrase_database.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/data/router_config.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/data/semantic_embeddings.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/data/shell_execution_policy.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/data/templates.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/desktop_executor/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/desktop_executor/backend_detector.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/desktop_executor/base.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/desktop_executor/browser_controller.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/desktop_executor/desktop_action_executor.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/desktop_executor/env_manager.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/desktop_executor/keyboard_controller.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/desktop_executor/window_manager.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/dom_actions/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/dom_actions/base.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/dom_actions/dispatcher.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/dom_actions/forms.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/dom_actions/navigation.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/dom_actions/registry.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/enhanced/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/environment/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/evolutionary/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/evolutionary/engine.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/evolutionary/runner.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/evolutionary/store.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/evolutionary/types.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/evolutionary_orchestrator.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/execution/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/execution/base.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/execution/browser.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/execution/executor_registry.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/execution/media_recorder.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/exploration/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/exploration/base.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/exploration/disk.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/exploration/resource_discovery.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/exploration/service.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/auto_repair.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/complex_detector.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/data_loader.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/fuzzy_schema_matcher.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/hybrid.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/keywords/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/llm_multi.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/llm_simple.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/multi_command.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/pipeline_components.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/schema/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/schema/adapter.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/schema/generator.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/semantic_entities.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/semantic_matcher_optimized.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/structured.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/templates/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/templates/api_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/templates/browser_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/templates/data_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/templates/desktop_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/templates/devops_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/templates/docker_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/templates/ffmpeg_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/templates/git_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/templates/iot_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/templates/kubernetes_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/templates/media_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/templates/package_mgmt_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/templates/presentation_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/templates/rag_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/templates/remote_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/templates/shell_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/templates/sql_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/generation/validating.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/history/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/history/tracker.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/intelligent/dynamic_generator.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/ir.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/llm/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/llm/openrouter.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/llm/repair.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/llm/vision.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/monitoring/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/monitoring/resources.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/monitoring/token_costs.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/nlp/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/nlp/config.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/nlp/entity_resolver.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/nlp/intent_matcher.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/nlp/normalizer.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/nlp_enhanced/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/nlp_light/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/optimization_report.yaml,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse YAML: Download error: Language 'YAML' not available for download. Available groups: [""all""]",
  src/nlp2cmd/orchestration/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/orchestration/metrics.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/page_analysis/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/page_analysis/base.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/page_analysis/field_classifier.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/page_analysis/form_analyzer.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/page_analysis/iframe_analyzer.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/page_analysis/link_extractor.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/page_analysis/page_analyzer.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/page_schema/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/page_schema/base.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/page_schema/button_extractor.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/page_schema/copy_button_extractor.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/page_schema/form_extractor.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/page_schema/page_schema_extractor.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/page_schema/radio_extractor.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/page_schema/token_extractor.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/pipeline_runner.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/plan_execution/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/plan_execution/browser_setup.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/planner/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/schema_based/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/schema_based/adapter.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/schema_based/generator.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/schema_extraction/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/schema_extraction/llm_extractor.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/schema_extraction/registry.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/service/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/service/cli.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/service/docker_app.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/drawing/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/drawing/colors.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/drawing/commands.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/drawing/correction_engine.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/drawing/draw_object.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/drawing/event_store.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/drawing/events.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/drawing/navigation.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/drawing/nl_parser.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/drawing/queries.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/drawing/renderers/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/drawing/renderers/base.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/drawing/renderers/playwright.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/drawing/renderers/svg.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/drawing/shapes.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/drawing/skill.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/drawing/visual_validator.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/search/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/search/engine.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/skills/search/skill.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/step_handlers/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/step_handlers/base.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/step_handlers/dispatcher.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/step_handlers/drawing.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/step_handlers/navigate.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/step_handlers/registry.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/storage/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/storage/per_command_store.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/storage/versioned_store.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/streams/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/streams/base.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/streams/http_stream.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/streams/rdp_stream.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/streams/router.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/streams/rtsp_stream.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/streams/spice_stream.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/streams/ssh_stream.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/streams/vnc_stream.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/streams/ws_stream.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/thermodynamic/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/thermodynamic/energy_models.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/utils/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/utils/data_files.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/utils/playwright_installer.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/web_schema/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/web_schema/browser_config.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/web_schema/extractor.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  src/nlp2cmd/web_schema/history.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  test_action_planner_logic.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  test_colors5.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  test_nlp2cmd_commands.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  test_nlp2cmd_enhanced.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  test_screenshots/analyze_screenshots.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  test_screenshots/capture_script.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  test_screenshots/compare_screenshots.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  test_screenshots/test_openrouter_workflow.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
  tests/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/base/test_base_adapter.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/conftest.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/conftest_browser.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/e2e/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/e2e/test_complete_flow.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/e2e/test_domain_scenarios.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/e2e/test_linux_commands_compression.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/e2e/test_linux_commands_files.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/e2e/test_linux_commands_hardware.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/e2e/test_linux_commands_misc.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/e2e/test_linux_commands_monitoring.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/e2e/test_linux_commands_network.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/e2e/test_linux_commands_packages.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/e2e/test_linux_commands_processes.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/e2e/test_linux_commands_text.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/e2e/test_linux_commands_users.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/e2e/test_registry_validation.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/e2e/test_service_e2e.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/fixtures/entity_extraction_eval.json,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse JSON: Download error: Language 'JSON' not available for download. Available groups: [""all""]",
  tests/integration/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/integration/test_llm_router_live.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/integration/test_polish_queries.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/integration/test_thermodynamic_e2e.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/integration/test_workflows.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_accuracy.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_custom_patterns.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_docker_keywords.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_docker_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_extraction.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_iter_0_baseline.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_iter_10_thermodynamic.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_iter_4_5_llm.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_iter_6_7_structured.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_iter_9_hybrid.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_k8s_keywords.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_k8s_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_keyword_detection.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_polish_commands.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_postprocessing.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_semantic_entities.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_shell_keywords.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_shell_list_folder_mixed_language.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_shell_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_shell_users_keywords.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_sql_keywords.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_sql_templates.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_template_customization.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/iterative/test_typos_and_variations.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/performance/__init__.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/performance/test_latency_regression.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/test_form_detection.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/simple_shell_commands.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_adapters.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_adapters_comprehensive.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_adaptive_learner.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_api_key_workflow.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_app2schema.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_auto_repair.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_automation.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_browser_automation.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_browser_manager.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_browser_token.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_canvas_planner.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_cli_entry_point.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_config.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_core.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_desktop_automation.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_desktop_executor.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_display_syntax.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_docker_validators.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_dom_actions.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_drawing_blueprints.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_drawing_new_skills.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_drawing_skill.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_drawing_skills_3.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_dynamic_schema_integration.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_environment.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_evolutionary_orchestrator_split.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_execution_plan.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_execution_runner_syntax.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_executor.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_executors.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_feedback_comprehensive.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_firefox_sessions.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_hybrid_generator_shadow_metadata.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_intent_matcher.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_k8s_validators.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_keyword_detector_missing_data.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_llm_router.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_llm_step_sanitizer.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_multistep_browser.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_multistep_cache_service_safety.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_nlp_integration.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_normalizer.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_orchestration.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_page_analysis.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_page_schema.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_password_store.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_pipeline_runner_step_errors.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_plan_execution.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_plan_step_robustness.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_planner_aggregator.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_prompt_secret_skip_pattern.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_refactored_methods.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_registry.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_router.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_rule_based_backend_extractor_modes.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_rule_based_pipeline_shadow_metadata.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_run_mode_sql.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_schema_fallback.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_schema_loading.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_schema_management.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_schema_validation.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_schemas_feedback.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_search_skill.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_semantic_shell_entity_extractor_modes.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_sequential_dsl_generation.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_service.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_service_query_shadow_metadata.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_shadow_entity_metadata_capture.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_shell_validators.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_similarity_cache.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_sql_validators.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_step_handlers.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_thermodynamic.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_transform_result.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_user_directory.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tests/unit/test_validation_result.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tools/analysis/analyze_version_detection.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tools/generation/intelligent_command_generator.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tools/manual_tests/quick_test_nlp2cmd.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tools/manual_tests/test_100_commands.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tools/manual_tests/test_batch_10.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tools/manual_tests/test_enhanced.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tools/manual_tests/test_intelligent_nlp2cmd.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tools/manual_tests/test_llm_quick.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tools/manual_tests/test_nlp2cmd_generation.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tools/manual_tests/test_template_usage.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tools/schema/cmd2schema.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tools/schema/enhanced_schema_generator.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tools/schema/non_llm_schema_extractor.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tools/schema/validate_schemas.py,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse PYTHON: Download error: Language 'PYTHON' not available for download. Available groups: [""all""]",
  tree.sh,0.78
    issues[1]{rule,severity,message,line}:
      syntax.unsupported,warning,"Could not parse BASH: Download error: Language 'BASH' not available for download. Available groups: [""all""]",
```

## Intent

NLP2CMD - Transforms natural language into domain-specific commands (SQL, Shell, Docker, Kubernetes) using a multi-layered detection pipeline and thermodynamic optimization.
