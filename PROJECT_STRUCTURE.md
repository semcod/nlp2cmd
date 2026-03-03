# NLP2CMD Project Structure

This document describes the project structure after the v1.0.93 refactoring for better maintainability and clarity.

## Directory Structure

```
nlp2cmd/
├── src/                          # Source code
│   ├── nlp2cmd/                  # Main package
│   │   ├── adapters/             # Domain adapters (shell, docker, k8s, browser, canvas, etc.)
│   │   ├── aggregator/           # Result aggregation
│   │   ├── automation/           # Browser/desktop automation, action planning
│   │   │   ├── action_planner.py       # Multi-step command decomposition (1393 lines)
│   │   │   ├── service_configs.py      # API service definitions (extracted from action_planner)
│   │   │   ├── drawing_blueprints.py   # Canvas drawing templates
│   │   │   ├── firefox_sessions.py     # Firefox session/cookie injection
│   │   │   ├── schema_fallback.py      # Dynamic re-planning on failures
│   │   │   ├── step_validator.py       # Step pre/post-condition validation
│   │   │   └── vector_store.py         # Semantic pattern search
│   │   ├── cli/                  # CLI interface (main, commands, display)
│   │   │   └── commands/         # Subcommands: generate, run, doctor, interactive, tools
│   │   ├── core/                 # Core models, backends, transforms
│   │   ├── execution/            # Modular executor framework
│   │   ├── orchestration/        # Dynamic LLM-driven orchestration engine
│   │   │   ├── engine.py         # Orchestrator: plan → execute → reflect
│   │   │   ├── reflection.py     # ResultAnalyzer: LLM validation, error classification
│   │   │   └── handlers.py       # 11 step handlers (shell, code gen, browser, etc.)
│   │   ├── generation/           # NLP pipeline, keyword detection, templates, LLM integration
│   │   │   ├── keywords/         # Keyword-based intent detector
│   │   │   ├── schema/           # Schema-based generation
│   │   │   └── templates/        # Domain-specific command templates
│   │   ├── nlp/                  # NLP config, normalizer, entity resolver, intent matcher
│   │   ├── thermodynamic/        # Thermodynamic optimization engine
│   │   ├── web_schema/           # Web form handling, site exploration
│   │   ├── pipeline_runner.py          # Core PipelineRunner (170 lines, mixin composition)
│   │   ├── pipeline_runner_shell.py    # Shell execution mixin
│   │   ├── pipeline_runner_browser.py  # Browser/DOM execution mixin
│   │   ├── pipeline_runner_desktop.py  # Desktop automation mixin
│   │   ├── pipeline_runner_plans.py    # Action plan execution mixin
│   │   └── pipeline_runner_utils.py    # Shared utilities, data classes
│   └── app2schema/               # AppSpec extraction tool
├── examples/                     # Example scripts and demos
│   ├── 01_basics/                # Shell, SQL, Docker, K8s fundamentals
│   ├── 02_benchmarks/            # Performance and sequential benchmarks
│   ├── 03_integrations/          # Pipelines, TOON format, web, validation
│   ├── 04_domain_specific/       # Bioinformatics, finance, healthcare, etc.
│   ├── 05_advanced_features/     # Dynamic schemas, thermodynamic computing
│   ├── 06_desktop_automation/    # Canvas drawing, env extraction, captcha
│   └── 07_stream_protocols/      # SSH, RTSP, HTTP, libvirt streams
├── tests/                        # Test suite (1543+ tests)
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   ├── e2e/                      # End-to-end tests
│   ├── iterative/                # Iterative test scenarios
│   └── performance/              # Latency regression tests
├── scripts/                      # Utility scripts
│   ├── maintenance/              # Project maintenance and setup
│   ├── testing/                  # Test runner utilities
│   └── thermodynamic/            # Thermodynamic optimization scripts
├── tools/                        # Development tools
│   ├── analysis/                 # Version detection, batch comparison
│   ├── generation/               # Command generators
│   ├── manual_tests/             # Manual test scripts
│   └── schema/                   # Schema generation and validation
├── docs/                         # Documentation
├── data/                         # Data files, intents, entities
├── command_schemas/              # Command schema definitions (JSON)
└── artifacts/                    # Build and test artifacts
```

## Key Architecture: PipelineRunner Mixin Split

The largest file (`pipeline_runner.py`, formerly 4413 lines) was refactored into a mixin composition:

| File | Lines | Responsibility |
|------|-------|---------------|
| `pipeline_runner.py` | 170 | Core class, `__init__`, `run`, mixin composition |
| `pipeline_runner_shell.py` | 174 | Shell command execution, safety checks |
| `pipeline_runner_browser.py` | 1520 | DOM/DQL execution, multi-action browser automation |
| `pipeline_runner_desktop.py` | 348 | Desktop automation (xdotool/ydotool/wmctrl) |
| `pipeline_runner_plans.py` | 2234 | Multi-step ActionPlan execution |
| `pipeline_runner_utils.py` | 380 | Shared utilities, `RunnerResult`, `VideoRecorder` |

All imports of `PipelineRunner` remain backward-compatible.

## Key Architecture: ActionPlanner Service Extraction

`action_planner.py` (formerly 1734 lines) had service configs extracted:

| File | Lines | Responsibility |
|------|-------|---------------|
| `action_planner.py` | 1393 | `ActionPlanner` class, decomposition logic |
| `service_configs.py` | 368 | API service definitions, email clients, NL aliases, LLM prompt |

## Makefile Integration

```bash
make report              # Generate benchmark report
make demo                # Run main demo
make bump-patch          # Bump patch version
make scripts-all         # List all scripts
```

## Adding New Code

- **Adapters**: `src/nlp2cmd/adapters/` — one file per domain
- **Templates**: `src/nlp2cmd/generation/templates/` — one file per domain
- **Examples**: `examples/NN_category/` — numbered directories
- **Tests**: `tests/unit/`, `tests/e2e/`, `tests/iterative/`
- **Scripts**: `scripts/maintenance/`, `scripts/testing/`
- **API services**: `src/nlp2cmd/automation/service_configs.py`
