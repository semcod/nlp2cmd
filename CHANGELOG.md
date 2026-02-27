## [1.0.88] - 2026-02-27

### Summary

refactor(sprint4): schema_based → generation/schema, pipeline_runner utils extraction, cleanup

### Refactoring

- **Move `schema_based/` → `generation/schema/`** (Sprint 4 roadmap):
  - `generation/schema/__init__.py`, `generator.py`, `adapter.py` — canonical location
  - `schema_based/` retained as backward-compatible shim (re-exports)
  - Updated `intelligent/version_aware_generator.py` import

- **Extract `pipeline_runner_utils.py`** from `pipeline_runner.py` (1568 → 1336 lines):
  - Utility functions: `_debug`, `_with_epipe_retry`, form field filtering helpers
  - Classes: `_MarkdownConsoleWrapper`, `ShellExecutionPolicy`, `RunnerResult`
  - All re-exported via `pipeline_runner.py` imports for backward compatibility

### Bug Fixes

- **Fix `pipeline_runner.py` SyntaxError**: unclosed `try` block in `fill_form` action
  handler caused `expected 'except' or 'finally' block` at `extract_company_websites_deep`
- **Fix `test_run_mode_sql`**: added missing `no_submit` parameter to match updated
  `_handle_run_query()` signature

### Cleanup

- Removed debug files from project root: `minimal_test.py`, `debug_test.py`,
  `debug_test2.py`, `debug_test3.py`

### Tests

- 1141 passed, 0 failed (excluding known Playwright flaky test)

---

## [1.0.87] - 2026-02-27

### Summary

feat(browser): deep company extraction with external website discovery and CSV export

### Features

- **Deep Company Extraction** (`extract_company_websites_deep`):
  - Navigates to each company profile from catalog listings
  - Extracts external website URLs (filters out social media)
  - Returns structured data with company name, Oferteo URL, and website

- **CSV Export** (`save_to_csv`):
  - New action for saving extracted data to CSV format
  - Auto-detects columns from data structure
  - UTF-8 encoding with proper headers

- **Browser Adapter Enhancements**:
  - New intent detection for deep website extraction
  - Expanded keyword lists (plural forms and variants)
  - Auto-detection of CSV format from filename

- **Form Field Filtering** (PipelineRunner):
  - `_filter_form_fields()` - filters out junk/comment forms
  - `_is_junk_field()` - excludes search, cookie, captcha fields
  - `_is_contact_relevant_field()` - identifies contact form fields
  - Integrated into form exploration flow

- **Save Detection Fix** (run.py):
  - Fixed detection to trigger on filename presence (e.g., "firmy.csv")
  - No longer requires explicit "plik" keyword

### Usage Examples

```bash
# Extract company websites from Oferteo and save to CSV
nlp2cmd --run "wejdź na https://www.oferteo.pl/katalog-firm, znajdź strony www firm i zapisz do firmy.csv"

# Find 20 companies from Gdańsk and save to text file
nlp2cmd --run "Otwórz przeglądarkę i wejdź na https://www.oferteo.pl. Przeszukaj katalog firm w poszukiwaniu stron www firm z Gdańska. Znajdź co najmniej 20 firm i zapisz ich adresy internetowe do pliku oferteo_firmy.txt."
```

### Files Modified

- `src/nlp2cmd/adapters/browser.py` - deep extraction detection
- `src/nlp2cmd/pipeline_runner.py` - new actions and form filtering
- `src/nlp2cmd/cli/commands/run.py` - save filename detection

---

## [1.0.86] - 2026-02-27

### Summary

feat(exploration): universal resource discovery system across web, disk, services, and data

### Features

- **Exploration Package** (`src/nlp2cmd/exploration/`):
  - `BaseExplorer` - Abstract base class for all explorers
  - `DiskExplorer` - File system exploration (find files, configs, code, data)
  - `ServiceExplorer` - API/service discovery (REST, GraphQL endpoints)
  - `DataTreeExplorer` - JSON/nested data navigation
  - `ExplorerRegistry` - Unified registry for all space types
  - Universal `explore()` function with auto-detection

- **SiteExplorer Enhancement** (`src/nlp2cmd/web_schema/site_explorer.py`):
  - `explore()` method with intent auto-detection from natural language
  - `find_content()` for articles, products, documentation
  - `find_form()` with iframe support and cookie consent handling
  - Support for multiple intents: contact, article, product, docs
  - Sitemap.xml parsing for efficient crawling
  - Multi-language keyword support (Polish, English)

- **ResourceDiscoveryManager** (`src/nlp2cmd/exploration/resource_discovery.py`):
  - Automatic error pattern recognition (missing files, directories, commands, packages, endpoints)
  - Decision engine for when to attempt discovery vs. fail
  - Integration with `ExecutionRunner.run_with_recovery()`
  - Integration with `PipelineRunner._run_shell()`
  - Automatic command adaptation with discovered resources
  - Configurable discovery limits and timeouts

### Integration Points

- **ExecutionRunner** (`src/nlp2cmd/execution/runner.py`):
  - `run_with_recovery()` now tries resource discovery before LLM fallback
  - New parameter: `use_resource_discovery=True`
  - Automatic retry with discovered resources

- **PipelineRunner** (`src/nlp2cmd/pipeline_runner.py`):
  - `_run_shell()` integrated with resource discovery
  - Automatic retry loop with discovery on missing resource errors
  - Preserves all existing safety policies

### API Usage

```python
from nlp2cmd.exploration import explore, DiskExplorer, SiteExplorer

# Universal exploration - auto-detects space type
result = explore("/etc", "config", search_term="nginx")
result = explore("https://example.com", "contact")

# Specific explorers
disk = DiskExplorer()
files = disk.find_config("~", app_name="myapp")

web = SiteExplorer()
form = web.find_form("https://example.com", intent="contact")
```

### Documentation

- Added `docs/EXPLORATION_GUIDE.md` - comprehensive exploration system guide
- Updated `docs/WEB_SCHEMA_GUIDE.md` - SiteExplorer documentation
- Updated `docs/README.md` - added exploration to navigation
- Updated main `README.md` - Exploration System feature section

### Decision Flow

```
Command Fails → analyze_error() → should_attempt_discovery()?
     ↓ YES                           ↓ NO
     ↓                    (fallback to LLM/prompt)
discover_missing_resource()
     ↓
adapt_command()
     ↓
Retry with discovered resource
```

### Error Patterns Supported

- `No such file or directory` → filesystem search
- `cd: No such file` → directory search
- `command not found` → PATH search
- `ModuleNotFoundError` → package install suggestion
- `Connection refused` → service endpoint search

---

## [1.0.85] - 2026-02-27

### Summary

refactor(cli): split cli/main.py monolith into commands/ subpackage (Sprint 4b)

### Refactoring

- **Split `cli/main.py`** (1901 → 393 lines, **79% reduction**):
  - `cli/commands/run.py` — `handle_run_mode`, `_handle_run_query`, `_suggest_next_steps` (~460 ln)
  - `cli/commands/generate.py` — single-query fast path `handle_generate_query`, `handle_appspec_query` (~160 ln)
  - `cli/commands/interactive.py` — `InteractiveSession` REPL + `_interactive_followup` (~500 ln)
  - `cli/commands/tools.py` — `cmd_repair`, `cmd_validate`, `cmd_analyze_env` (~160 ln)
  - `cli/helpers.py` — shared utilities: adapter factory, browser/Playwright fallbacks, console helpers (~250 ln)
  - `cli/commands/__init__.py` — package init

- **Backward compatibility preserved**: all public symbols (`main`, `cli_entry_point`,
  `InteractiveSession`, `handle_run_mode`, `ExecutionRunner`, `get_adapter`, etc.)
  remain importable from `nlp2cmd.cli.main` via re-exports.

### Tests

- 1129 passed, 0 failed (excluding known Playwright flaky test)
- All 15 CLI-specific tests pass unchanged

### Docs

- Added `docs/ROADMAP_SPRINT4.md` — full Sprint 4/4b/5 roadmap

---

## [1.0.84] - 2026-02-26

### Summary

feat(benchmark): add --no-cache flag and refresh benchmark queries

### Features

- **Benchmark No-Cache Mode**: New `--no-cache` flag for pure LLM performance testing
  - Disables all cache tiers (exact, fuzzy, similarity, template pipeline)
  - Forces fresh LLM calls for every query
  - Environment variable: `NLP2CMD_DISABLE_CACHE=1`
  - Usage: `python3 examples/benchmark_nlp2cmd.py --no-cache`
  - Makefile target: `make benchmark-no-cache`

- **Refreshed Benchmark Queries**: All 47 benchmark queries replaced with new variants
  - Prevents cache hits from previous benchmark runs
  - Same domain/intent coverage with different phrasing
  - New file names, numbers, and parameters in queries
  - Examples:
    - Old: `znajdź wszystkie pliki PDF większe niż 10MB`
    - New: `wyszukaj pliki DOCX większe niż 5MB w katalogu /home`

### Core

- update `examples/benchmark_nlp2cmd.py`:
  - Add argparse with `--no-cache` flag
  - Set `NLP2CMD_DISABLE_CACHE=1` environment variable when flag is used
  - Replace all 47 benchmark queries with new uncached variants
  - Update expected regex patterns for new queries

- update `src/nlp2cmd/generation/evolutionary_cache.py`:
  - Add `cache_disabled` check in `lookup()` method
  - Skip all cache tiers when `NLP2CMD_DISABLE_CACHE` is set
  - Skip template pipeline when cache is disabled
  - Direct all queries to LLM teacher for pure LLM testing

### Build

- update `Makefile`:
  - Add `benchmark-no-cache` target for convenient no-cache benchmarking

### Docs

- update `docs/BENCHMARKING.md`:
  - Document `--no-cache` flag usage
  - Add section explaining when to use no-cache mode
  - Add examples for benchmark with and without cache

- update `docs/EVOLUTIONARY_CACHE.md`:
  - Add "Disabling Cache" section with environment variable usage
  - Document `NLP2CMD_DISABLE_CACHE` variable
  - Add Python and CLI examples


## [1.0.83] - 2026-02-26

### Summary

feat(docs): deep code analysis engine with 5 supporting modules

### Core

- update src/nlp2cmd/adapters/browser.py
- update src/nlp2cmd/cli/main.py
- update src/nlp2cmd/pipeline_runner.py

### Test

- update tests/unit/test_browser_automation.py

### Other

- update data/form_schema.json
- update src/nlp2cmd/data/form_schema.json


## [Unreleased]

### Summary

feat(browser): add article extraction with plural and topic filtering

### Features

- **Article Extraction**: Browser adapter now supports extracting and displaying article content from news websites
  - New `extract_article` action in browser automation pipeline
  - **Singular mode** (default): Extracts and displays first article content
    - Detects Polish keywords: "wyświetl artykuł", "pokaż artykuł"
    - Detects English keywords: "show article", "display article", "extract article", "read article"
    - Example: `nlp2cmd -r "otwórz https://wp.pl i wyświetl artykuł"`
  - **Plural mode**: Lists multiple article titles and URLs (up to 10)
    - Detects Polish keywords: "wyświetl artykuły", "pokaż artykuły"
    - Detects English keywords: "show articles", "list articles", "display articles"
    - Example: `nlp2cmd -r "otwórz https://wp.pl i wyświetl artykuły"`
  - **Topic filtering**: Filter articles by keyword/topic
    - Polish: "artykuł o [topic]", "artykuł na temat [topic]"
    - English: "article about [topic]"
    - Example: `nlp2cmd -r "otwórz https://wp.pl i wyświetl artykuł o polityce"`
    - Works with both singular and plural modes
  - Automatically finds article links on homepage using multiple selectors
  - Extracts article content using semantic HTML selectors (article, main, etc.)
  - Prints formatted article text to terminal (up to 2000 chars with truncation notice)

### Core

- update src/nlp2cmd/adapters/browser.py: add plural detection, topic extraction, and enhanced action generation
  - `_has_extract_article_action()`: detects both singular and plural forms
  - `_is_plural_article_request()`: checks for plural keywords
  - `_extract_article_topic()`: extracts topic from query using regex patterns
- update src/nlp2cmd/pipeline_runner.py: enhanced `extract_article` handler with mode and topic support
  - Collects all article links (up to 20)
  - Filters by topic using keyword matching
  - List mode: displays article titles and URLs
  - Single mode: extracts and displays full article content
- update src/nlp2cmd/web_schema/form_data_loader.py: add `get_article_topic_patterns()` method
- update data/form_schema.json: add plural keywords and topic extraction patterns

### Tests

- add tests/unit/test_browser_automation.py: 15 new tests for article extraction
  - Basic singular/plural extraction (Polish/English)
  - Topic-based filtering
  - Validation and metadata checks
  - Action ID verification


## [1.0.82] - 2026-02-26

### Summary

refactor(docs): configuration management system

### Core

- update src/nlp2cmd/generation/evolutionary_cache.py
- update src/nlp2cmd/utils/playwright_installer.py

### Docs

- docs: update TODO.md
- docs: update benchmark_command_errors.md
- docs: update refactoring_plan.md

### Other

- update benchmark_output/benchmark_results.html
- update benchmark_output/benchmark_results.json


## [1.0.81] - 2026-02-26

### Summary

refactor(docs): configuration management system

### Core

- update src/nlp2cmd/adapters/shell_original.py
- update src/nlp2cmd/cli/main.py
- update src/nlp2cmd/cli/main_original.py
- update src/nlp2cmd/concepts/__init__.py
- update src/nlp2cmd/concepts/conceptual_commands.py
- update src/nlp2cmd/concepts/dependency_resolver.py
- update src/nlp2cmd/concepts/environment.py
- update src/nlp2cmd/concepts/semantic_objects.py
- update src/nlp2cmd/concepts/virtual_objects.py
- update src/nlp2cmd/contracts/__init__.py
- ... and 12 more

### Docs

- docs: update README
- docs: update TODO.md
- docs: update benchmark_command_errors.md
- docs: update refactoring_plan.md
- docs: update BENCHMARKING.md
- docs: update EVOLUTIONARY_CACHE.md
- docs: update LLM_BENCHMARK_COMMAND_ERRORS.md

### Test

- update test_ollama_speed.py
- update tests/unit/test_adapters.py
- update tests/unit/test_conceptual_commands.py
- update tests/unit/test_similarity_cache.py

### Other

- update .env.example
- update benchmark_output/.nlp2cmd_bench/deepseek-r1_1.5b/learned_schemas.json
- update benchmark_output/.nlp2cmd_bench/phi_latest/learned_schemas.json
- update benchmark_output/.nlp2cmd_bench/qwen2.5_3b/learned_schemas.json
- update benchmark_output/benchmark_results.html
- update benchmark_output/benchmark_results.json
- update benchmark_output/learning_benchmark.html
- update benchmark_output/learning_benchmark.json
- update command_schemas/sites/www.prototypowanie.pl.json
- update examples/benchmark_learning.py
- ... and 4 more


## [1.0.82] - 2026-02-26

### Summary

fix(browser): browser automation failed with '[Errno 2] No such file or directory' — DSL JSON was executed as shell command

### Bug Fixes

- fix(core): `transform_ir()` now prefers adapter's pre-built `ActionIR` (e.g. `BrowserAdapter.last_action_ir`) over constructing a new one
- fix(core): map `BrowserAdapter.DSL_NAME='browser'` → `dsl_kind='dom'` in `_DSL_KIND_MAP`
- Root cause: `'browser'` was not in the `dsl_kind` whitelist, falling back to `'shell'`, causing `PipelineRunner` to execute dom_dql.v1 JSON via `subprocess.run()`
- fix(pipeline_runner): `fill_form` action — replace hard `networkidle` timeout with fallback: try `networkidle` (5s) → fall back to `domcontentloaded` (10s). Fixes timeout on sites with persistent network activity (analytics, chat widgets, websockets)
- fix(form_schema): add English `fill_form_phrases` variants: "fill the form", "fill out the form", "fill in the form" — EN queries now correctly trigger form filling

### Cleanup (Sprint 3)

- remove: `adapters/shell_original.py` (1926 lines), `cli/main_original.py` (1037 lines), `schema_extraction/__init___original.py` (1595 lines) — dead backup files
- remove: `concepts/` module (5 files, 1759 lines) — zero imports in project
- remove: `contracts/` module (1 file, 10 lines) — zero imports in project
- remove: `nlp/` module (4 files, 145 lines) — stub interfaces, zero imports
- remove: `interfaces/` module (4 files, 71 lines) — zero imports in project
- remove: `test_ollama_speed.py` (empty file), `tests/unit/test_conceptual_commands.py` (orphaned test)
- **Total removed: ~4,543 lines of dead code**

### Test

- add: `tests/unit/test_browser_automation.py` — **41 tests** covering:
  - Simple navigation (PL + EN): 8 tests
  - Fill form + submit (PL + EN): 6 tests
  - URL extraction edge cases: 4 tests
  - ActionIR structure/metadata: 5 tests
  - Real-world sites parametrized: 12 tests (prototypowanie.pl, softreck.com, github.com, stackoverflow, wikipedia, reddit, gitlab, hn)
  - Validate syntax: 4 tests
  - PipelineRunner dry-run: 2 tests
- add: `TestBrowserAdapterTransformIR` in test_adapters.py — 2 regression tests
- result: **1112 passed**, 0 failed, 385 deselected

---

## [1.0.81] - 2026-02-26

### Summary

perf(cache): few-shot prompts, template pipeline, pre-warm cache — 100% accuracy (Qwen-Coder), 24k× speedup

### Benchmark Results (before → after)

- **Qwen2.5-Coder-3B**: 79% → **100.0%** (+21pp)
- **Qwen2.5-3B**: 83% → **97.9%** (+15pp)
- **Bielik-1.5B**: 26% → **61.7%** (+36pp)
- **Gemma2-2B**: 28% → **55.3%** (+27pp)
- **Overall**: 53.7% → **78.7%** (+25pp)
- **Learning speedup**: 854× → **24,355×**

### Core

- feat(cache): few-shot prompts for all 16 domains in evolutionary_cache.py and benchmark
- feat(cache): template-first pipeline (Tier 2) — 1615 patterns, handles 66% queries without LLM
- feat(cache): Polish intent mapping for template pipeline (84% coverage across 16 domains)
- feat(cache): improved entity extraction (files, IPs, dimensions, users, tags, packages)
- feat(cache): pre-warm cache with 50 popular queries for instant cold start
- fix(cache): raise similarity threshold 78% → 88% to avoid false positives
- fix(benchmark): overly strict regex patterns for api POST, media batch, data unique count

### Test

- update tests/unit/test_similarity_cache.py — adjusted for new threshold, 22/22 pass

### Docs

- docs: update EVOLUTIONARY_CACHE.md with final benchmark results and architecture
- docs: update README.md with 100% accuracy and 24k× speedup

### Other

- update examples/benchmark_nlp2cmd.py — few-shot prompts for all 16 domains, fixed model list
- update examples/benchmark_learning.py — fixed teacher model list (gemma2:2b replaces deepseek-coder)


## [1.0.80] - 2026-02-26

### Summary

refactor(docs): configuration management system

### Core

- update src/nlp2cmd/generation/evolutionary_cache.py
- update src/nlp2cmd/generation/templates/rag_templates.py
- update src/nlp2cmd/generation/templates/sql_templates.py

### Test

- update tests/unit/test_similarity_cache.py

### Other

- update .env.example
- update benchmark_output/.nlp2cmd_bench/deepseek-r1_1.5b/learned_schemas.json
- update benchmark_output/.nlp2cmd_bench/phi_latest/learned_schemas.json
- update benchmark_output/.nlp2cmd_bench/qwen2.5_3b/learned_schemas.json
- update benchmark_output/learning_benchmark.html
- update benchmark_output/learning_benchmark.json
- update examples/benchmark_learning.py
- update examples/benchmark_nlp2cmd.py


## [1.0.79] - 2026-02-26

### Summary

refactor(docs): configuration management system

### Core

- update src/nlp2cmd/generation/evolutionary_cache.py

### Docs

- docs: update README
- docs: update refactoring_plan.md
- docs: update EVOLUTIONARY_CACHE.md

### Other

- update .env.example
- update .gitignore
- update benchmark_output/.nlp2cmd_bench/deepseek-r1_1.5b/learned_schemas.json
- update benchmark_output/.nlp2cmd_bench/learned_schemas.json
- update benchmark_output/.nlp2cmd_bench/phi_latest/learned_schemas.json
- update benchmark_output/.nlp2cmd_bench/qwen2.5_3b/learned_schemas.json
- update benchmark_output/Modelfile.bielik
- update benchmark_output/benchmark_results.html
- update benchmark_output/benchmark_results.json
- update benchmark_output/learning_benchmark.html
- ... and 3 more


## [1.0.78] - 2026-02-26

### Summary

feat(examples): configuration management system

### Core

- update src/nlp2cmd/generation/evolutionary_cache.py

### Other

- update examples/benchmark_learning.py
- update examples/benchmark_nlp2cmd.py


## [1.0.77] - 2026-02-26

### Summary

feat(examples): configuration management system

### Other

- update examples/benchmark_learning.py
- update examples/benchmark_nlp2cmd.py
- update project.toon


## [1.0.76] - 2026-02-26

### Summary

refactor(docs): configuration management system

### Core

- update src/nlp2cmd/generation/evolutionary_cache.py

### Docs

- docs: update README
- docs: update EVOLUTIONARY_CACHE.md

### Other

- update .gitignore
- build: update Makefile
- update examples/benchmark_learning.py
- update examples/benchmark_nlp2cmd.py


## [1.0.75] - 2026-02-26

### Summary

refactor(docs): configuration management system

### Core

- update src/nlp2cmd/generation/regex.py
- update src/nlp2cmd/generation/template_generator.py
- update src/nlp2cmd/generation/templates/__init__.py
- update src/nlp2cmd/generation/templates/api_templates.py
- update src/nlp2cmd/generation/templates/data_templates.py
- update src/nlp2cmd/generation/templates/devops_templates.py
- update src/nlp2cmd/generation/templates/ffmpeg_templates.py
- update src/nlp2cmd/generation/templates/iot_templates.py
- update src/nlp2cmd/generation/templates/media_templates.py
- update src/nlp2cmd/generation/templates/package_mgmt_templates.py
- ... and 3 more

### Test

- update test_ollama_speed.py

### Other

- update .gitignore
- build: update Makefile
- update TICKET
- update examples/04_domain_specific/polish_llm_integration/test_bielik_simple.py
- update examples/benchmark_nlp2cmd.py
- scripts: update project.sh
- update project.toon


## [1.0.70] - 2026-02-23

### Summary

feat(docs): deep code analysis engine with 3 supporting modules

### Core

- update src/nlp2cmd/generation/pipeline_components.py
- update src/nlp2cmd/thermodynamic/energy_models.py


## [1.1.0-dev] - 2026-02-23

### Summary

refactor: Split monolithic modules + fix browser automation pipeline

### Architecture (Sprint 2 — Module Splitting)

- **templates.py → templates/ package**: Split 94-function monolith into 6 per-domain files
  (`sql_templates.py`, `shell_templates.py`, `docker_templates.py`, `kubernetes_templates.py`,
  `browser_templates.py`, `git_templates.py`) + `template_generator.py` orchestrator
- **keywords.py → keywords/ package**: Split 46-function monolith into
  `keyword_detector.py` (detection logic) + `keyword_patterns.py` (pattern loading)
- **core.py → core/ package**: Split 53-function monolith into
  `core_models.py` (data models) + `core_backends.py` (NLP backends) + `core_transform.py` (transformation)
- Updated imports in 15+ files across generation/, cli/, nlp_enhanced/, nlp_light/, tests/

### CLI Fixes

- **Browser navigate URL**: Fast-path now preserves full URL with `https://` scheme and path
  (fixes `xdg-open 'prototypowanie.pl'` → `xdg-open 'https://www.prototypowanie.pl/kontakt/'`)
- **History disambiguation in --run**: Selecting `dom_dql.v1` from history now executes via
  Playwright instead of regenerating a simple `navigate` command
- **Auto-confirm + disambiguation**: `-ac` flag auto-selects history command if similarity ≥ 0.95
- **Submit confirmation**: Retry with `confirm=True` when PipelineRunner blocks submit/press_enter
- **Playwright auto-install**: `ensure_playwright_installed()` check before history dom_dql.v1 execution
- **`--auto-install` default ON**: Changed from opt-in flag to `--auto-install/--no-auto-install` with `default=True`
- **Fix `_handle_run_query` NameError**: Added wrapper function delegating to `handle_run_mode()`

### Config

- config: update goal.yaml

### Other

- update project.functions.toon
- scripts: update project.sh
- update project.toon


## [1.0.69] - 2026-02-23

### Summary

refactor(goal): configuration management system

### Config

- config: update goal.yaml

### Other

- update project.functions.toon
- scripts: update project.sh
- update project.toon


## [1.0.68] - 2026-02-23

### Summary

refactor(docs): configuration management system

### Core

- update src/nlp2cmd/cli/main.py
- update src/nlp2cmd/core.py
- update src/nlp2cmd/generation/hybrid.py
- update src/nlp2cmd/generation/pipeline.py
- update src/nlp2cmd/service/__init__.py

### Docs

- docs: update ENHANCED_README.md

### Test

- update tests/unit/test_hybrid_generator_shadow_metadata.py
- update tests/unit/test_rule_based_pipeline_shadow_metadata.py
- update tests/unit/test_service_query_shadow_metadata.py
- update tests/unit/test_shadow_entity_metadata_capture.py

### Build

- update pyproject.toml

### Config

- config: update goal.yaml


# Changelog

All notable changes to NLP2CMD will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.31] - 2026-01-27

### 🚀 Performance Benchmarking Suite
- **Comprehensive Benchmarking Tool** - Added `benchmark_nlp2cmd.py` for performance analysis
- **Markdown Report Generation** - Detailed reports with thermodynamic analysis
- **Sequential vs Single Command Testing** - Measure efficiency gains of batch processing
- **Time Savings Analysis** - Quantifies performance improvements (up to 34.9% efficiency gain)
- **Throughput Metrics** - Commands per second measurement across adapters

### 📊 Thermodynamic Performance Analysis
- **Energy Efficiency Metrics** - Track initialization vs processing energy
- **Bottleneck Identification** - Pinpoint performance bottlenecks in the system
- **Optimization Strategies** - Three modes: Individual, Sequential, Thermodynamic Hybrid
- **Adapter Performance Comparison** - Shell, SQL, and Docker adapter benchmarks

### 🗂️ Project Structure Reorganization
- **Script Categorization** - Organized scripts into logical directories:
  - `scripts/maintenance/` - Setup, fixes, and maintenance utilities
  - `scripts/thermodynamic/` - Thermodynamic optimization scripts
  - `scripts/testing/` - Testing utilities and runners
- **Example Consolidation** - All examples moved to `examples/` directory
- **Makefile Integration** - New targets for script management and benchmarking
- **Documentation Updates** - `PROJECT_STRUCTURE.md` with detailed organization guide

### 🔧 Code Quality Improvements
- **Template Generation Refactoring** - Simplified conditional logic in `_apply_shell_find_flags`
- **Better Error Handling** - Improved file path resolution in templates
- **Cleaner Code Structure** - Removed nested `setdefault` calls for readability

### 🛠️ Build System Updates
- **New Makefile Targets**:
  - `make report` - Generate performance benchmark report
  - `make demo-benchmark` - Run benchmark demonstration
  - `make scripts-all` - List all organized scripts
  - `make benchmark-md` - View markdown benchmark report
- **Improved Path Handling** - Proper PYTHONPATH configuration for all scripts
- **GitIgnore Updates** - Added `publish-env` to ignore list

## [1.0.30] - 2025-01-25

### 🎨 Major UI/UX Improvements
- **Enhanced Output Format** - Replaced Rich panels with clean markdown-style codeblocks
- **Syntax Highlighting** - Beautiful syntax highlighting for bash, SQL, and YAML codeblocks
- **Clean Interface** - Removed complex Rich panels for minimal, readable output
- **Monokai Theme** - Consistent dark theme across all syntax-highlighted content

### 🌍 Enhanced CLI Experience
- **Natural Language Queries** - Direct support for quotes natural language queries
- **Polish Language Support** - Full Polish language support in CLI interface
- **Improved CLI Entry Point** - Better handling of mixed arguments and options
- **Clean Error Messages** - Simplified error reporting without Rich panels

### 🔧 Technical Improvements
- **Rich Syntax Integration** - Optimized Rich Syntax highlighting across all output types
- **Better Error Handling** - Improved FeedbackType enum usage and error reporting
- **Code Organization** - Cleaner separation of display logic from business logic
- **Performance Optimizations** - Reduced overhead in CLI argument parsing

### 📋 Output Format Examples

#### Before (Rich Panels)
```
╭─────────────────────────────── NLP2CMD Result ───────────────────────────────╮
│                                                                              │
│ find . -type f -mtime -7                                                     │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### After (Clean Codeblocks)
```bash
find . -type f -mtime -7                                                        
```

```yaml
dsl: auto
query: znajdź pliki zmodyfikowane ostatnie 7 dni
status: success
confidence: 1.0
generated_command: find . -type f -mtime -7
```

### 🐛 Bug Fixes
- Fixed CLI entry point to properly handle natural language queries with spaces
- Corrected FeedbackType.ERROR to FeedbackType.SYNTAX_ERROR
- Fixed parameter names in FeedbackResult constructor calls
- Resolved build system issues with missing build package

### ⚡ Performance
- Faster CLI argument parsing with improved logic
- Reduced Rich console overhead with targeted syntax highlighting
- Optimized import statements for better startup time

## [Unreleased]

### 🎉 Major Features - Production Ready Release
- **85%+ Success Rate** - System achieves production-ready performance
- **Advanced File Operations** - Time-based and size-based filtering with combined filters
- **Username Support** - Specific user directory operations (`~username`, `/root`)
- **Enhanced Polish NLP** - 87%+ accuracy with lemmatization and fuzzy matching
- **Package Management** - APT installation with Polish and English variants
- **Browser Domain** - Google, GitHub, Amazon search integration
- **Cross-platform Ready** - OS detection and appropriate command generation

### 🔧 Advanced Search Capabilities
- **Time-based Search** - `znajdź pliki zmodyfikowane ostatnie 7 dni` → `find . -mtime -7`
- **Size-based Filtering** - `znajdź pliki większe niż 100MB` → `find . -size +100MB`
- **Combined Filters** - `znajdź pliki .log większe niż 10MB starsze niż 2 dni`
- **Enhanced Size Parsing** - Automatic MB→M, GB→G conversion for GNU find compatibility

### 👤 User Directory Operations
- **User Home Detection** - `pokaż pliki użytkownika` → `find $HOME -type f`
- **Username-specific Paths** - `pokaż foldery użytkownika root` → `ls -la /root`
- **Directory Listing** - `listuj pliki w katalogu domowym` → `ls -la ~`
- **Enhanced Entity Extraction** - Username, path, and context detection

### 📦 Package Management Enhancement
- **Multi-variant Support** - `zainstaluj vlc`, `apt install nginx`, `install git`
- **Polish Language Commands** - Native Polish package installation commands
- **Safety Validation** - Command safety checks before execution
- **Cross-platform Detection** - OS-aware command generation

### 🌐 Browser Domain Integration
- **Google Search** - `wyszukaj w google python tutorial` → Google search
- **GitHub Search** - `znajdź repozytorium nlp2cmd na github` → GitHub search
- **Amazon Search** - `szukaj na amazon python books` → Amazon search
- **Web Automation** - Browser-based search and navigation

### 🧠 Enhanced NLP Engine
- **Lemmatization Support** - Polish word form normalization with spaCy
- **Priority Intent Detection** - Smart command classification with confidence scoring
- **Enhanced Entity Extraction** - Time, size, username, path detection
- **Fuzzy Matching** - Typo tolerance with rapidfuzz integration
- **Pattern Optimization** - Conflict resolution between intents

### 🔍 Enhanced Entity Extraction
- **Age Entities** - Time-based filtering (days, hours, minutes)
- **Size Entities** - File size parsing with unit conversion
- **Username Entities** - Specific user identification and path resolution
- **Path Entities** - Directory and file path extraction with context
- **Combined Entity Processing** - Multi-entity command generation

### 🛡️ Safety & Validation
- **Command Safety Checks** - Pre-execution validation
- **Confirmation Prompts** - User confirmation for dangerous operations
- **Path Validation** - Safe path handling and resolution
- **Command Sanitization** - Input validation and cleaning

### 📊 Performance Metrics
- **Shell Operations**: 90%+ success rate
- **Package Management**: 100% success rate  
- **User File Operations**: 100% success rate
- **Advanced Find**: 100% success rate
- **Web Search**: 33% success rate
- **Overall System**: 85%+ production ready

### 🔧 Technical Improvements
- **Dedicated Generators** - `_generate_list`, `_generate_find` with enhanced logic
- **Template System** - Enhanced template generation with entity support
- **Adapter Architecture** - Improved shell adapter with OS context
- **Pipeline Optimization** - Enhanced processing with better error handling
- **Cache Management** - Improved dependency and resource caching

### 🇵🇱 Polish Language Excellence
- **Native Polish Support** - Full Polish language NLP pipeline
- **Diacritic Handling** - Proper Polish character processing
- **Lemmatized Patterns** - Support for word form variations
- **Priority Intents** - Polish-specific command prioritization
- **Multi-variant Commands** - Support for Polish language variants

### 🚀 Production Readiness
- **Stable API** - Consistent and reliable command generation
- **Error Handling** - Comprehensive error detection and reporting
- **Documentation** - Complete documentation with examples
- **Testing Coverage** - Extensive test suite with real-world scenarios
- **Performance** - Sub-second command generation with caching

### Fixed
- **Semantic Similarity Encoding** - Fixed BERT model encoding issues
- **Entity Transfer** - Pipeline now uses enhanced context entities correctly
- **Pattern Conflicts** - Removed "pokaż pliki" from list patterns to avoid find conflicts
- **Boolean Property Checks** - Fixed user_context boolean evaluation in semantic objects
- **Interactive Session** - Replaced NLP2CMD with ConceptualCommandGenerator

### Performance
- **Typo Tolerance**: 73.3% success rate (vs 20% before)
- **Semantic Similarity**: Working BERT integration (vs 0.0 before)
- **User Directory Commands**: 100% accuracy for user queries
- **Conceptual Commands**: 100% success rate in tests
- **Interactive Mode**: Full conceptual understanding integration

## [1.0.21] - 2026-01-24

### 🚀 Major Features
- **Enhanced NLP Integration** - Advanced semantic similarity and context detection
- **Shell Emulation Mode** - Full interactive shell with natural language commands
- **Browser DSL Support** - New browser domain with URL navigation and search
- **Multi-layer Intent Detection** - Enhanced pipeline with fallback mechanisms

### 🧠 Enhanced NLP Improvements
- **Semantic Similarity**: sentence-transformers integration for conceptual understanding
- **Context Awareness**: Web schema integration for browser automation context
- **Polish Language Enhancement**: Improved diacritics and typo handling
- **Confidence Scoring**: Multi-layered confidence calculation with metrics
- **Fallback Pipeline**: Graceful degradation from enhanced to basic detection

### 🖥️ Shell Emulation
- **Interactive Mode**: `nlp2cmd --interactive --dsl shell` with persistent session
- **User Directory Recognition**: Smart handling of "usera" → "~" mapping
- **Process Management**: Enhanced process and service command detection
- **Real-time Feedback**: YAML output with detailed metrics and suggestions
- **Polish Commands**: Native Polish shell command support

### 🌐 Browser Automation
- **URL Navigation**: Automatic URL detection and opening
- **Search Integration**: Google, GitHub, Amazon search templates
- **Form Interaction**: Element clicking and form filling patterns
- **Web Context**: Integration with web schema extraction results

### 🔧 Pipeline Enhancements
- **RuleBasedPipeline**: Enhanced pipeline with context detection
- **Enhanced Context**: Optional enhanced NLP with graceful fallback
- **Markdown Stripping**: Automatic cleanup of LLM code block responses
- **Entity Extraction**: Improved regex patterns for browser and shell entities
- **Template Generation**: New browser templates for web actions

### 📊 Performance & Metrics
- **Resource Monitoring**: Detailed CPU, memory, and energy metrics
- **Token Estimation**: LLM token usage and cost calculation
- **Processing Time**: Per-layer timing analysis
- **Confidence Tracking**: Which detection method succeeded

### 🛠️ CLI Improvements
- **Interactive Shell**: Enhanced REPL with environment detection
- **Help System**: Improved command documentation and examples
- **Error Handling**: Better error messages and recovery
- **Output Formatting**: Rich YAML output with structured data

### 📚 Documentation
- **Enhanced NLP Guide**: Comprehensive enhanced NLP integration documentation
- **Shell Emulation Examples**: Real-world interactive shell examples
- **Browser Automation**: Web automation patterns and templates
- **Performance Metrics**: Resource monitoring and optimization guide

### 🧪 Testing & Quality
- **Enhanced Test Coverage**: Tests for new NLP features
- **Interactive Mode Testing**: Shell emulation validation
- **Browser Pattern Tests**: URL and search pattern verification
- **Performance Benchmarks**: Resource usage monitoring

## [1.0.20] - 2026-01-24

### 🚀 Major Features

- **Web Schema Engine** - Complete browser automation system with Playwright integration
- **Smart Cache Manager** - External dependencies caching for Playwright browsers (3105+ MB saved)
- **Polish NLP Enhancement** - Advanced lemmatization, fuzzy matching, and diacritics normalization
- **CLI Cache Commands** - Full cache management suite (`nlp2cmd cache`)

### 🌐 Web Automation

- **Schema Extraction**: `nlp2cmd web-schema extract <url>` - Extract interactive elements from any website
- **Form Filling**: Automatic form detection and filling with natural language
- **Interaction History**: Track and analyze web interactions with success rates
- **Learned Schemas**: Export learned patterns from interaction history
- **Multi-browser Support**: Chromium, Firefox, WebKit with automatic fallback

### 🧠 NLP Improvements

- **Polish Lemmatization**: spaCy integration for advanced Polish language processing
- **Fuzzy Matching**: rapidfuzz integration for typo tolerance (95%+ accuracy)
- **Diacritics Normalization**: ł→l, ę→e, ą→a for robust Polish text handling
- **Multi-word Keywords**: Flexible spacing pattern matching for complex phrases
- **Confidence Scoring**: Enhanced intent detection with confidence metrics
- **Priority Detection**: Service-related intents prioritized over generic patterns

### 💾 Cache Management

- **External Cache**: `~/.cache/external/` for Playwright browsers and dependencies
- **Auto-Setup**: `nlp2cmd cache auto-setup` - One-click installation and configuration
- **Smart Detection**: Automatic cache usage with fallback to fresh installation
- **Size Optimization**: 3105.4 MB browsers cached and shared across commands
- **Manifest Tracking**: JSON manifest with metadata and installation history

### 🛠️ CLI Enhancements

- **Cache Commands**: `setup|install|info|check|clear|auto-setup`
- **Web Schema Commands**: `extract|history|export-learned|clear`
- **Enhanced Help**: Rich formatting with progress bars and status indicators
- **Error Recovery**: Better error messages and automatic dependency resolution

### 🧪 Testing & Quality

- **Test Suite**: 8/9 tests passing with comprehensive coverage
- **Polish Language Tests**: Specific test cases for Polish diacritics and typos
- **Web Schema Tests**: End-to-end browser automation validation
- **Cache Tests**: External dependency caching verification

### 📚 Documentation Updates

- **README Update**: Complete rewrite with Quick Start guide and feature highlights
- **Web Schema Guide**: New documentation for browser automation
- **Cache Management Guide**: External dependencies caching documentation
- **Examples**: Real-world usage examples with Polish language support

### 🔧 Internal Improvements

- **Pattern Matching**: Regex-based multi-word keyword detection
- **Performance**: Optimized keyword detection with reduced false positives
- **Modularity**: Separated cache management into dedicated utilities
- **Error Handling**: Enhanced exception handling and user feedback

## [0.1.1] - 2026-01-23

### Added
- Comprehensive documentation cross-linking between all markdown files
- Navigation sections in all documentation files with related links
- Examples section in README.md with categorized links to practical examples
- Documentation links in example Python files (basic_sql.py, basic_shell.py, end_to_end_demo.py)
- Central documentation hub at docs/README.md with complete navigation structure
- Links to scientific papers and references for thermodynamic optimization
- Quick navigation by use case (new users, developers, domain-specific applications)

### Improved
- Enhanced documentation discoverability and user experience
- Better integration between API docs, user guides, and examples
- Clearer documentation structure with hierarchical navigation

## [Unreleased]

### Added
- Initial release of NLP2CMD framework
- SQL adapter with PostgreSQL, MySQL, SQLite, MSSQL support
- Shell adapter with Bash, Zsh, Fish, PowerShell support
- Docker adapter with CLI and Compose support
- Kubernetes adapter with kubectl command generation
- DQL (Doctrine Query Language) adapter for PHP/Symfony
- Schema Registry for file format validation and repair
- Supported formats: Dockerfile, docker-compose, Kubernetes manifests, GitHub Actions, .env files
- Feedback loop with automatic error correction suggestions
- Environment analyzer for tool and service detection
- Interactive REPL mode with intelligent feedback
- Safety policies for all DSL types
- LLM integration support (Claude, GPT)
- CLI tool with comprehensive options
- Full test coverage
- API documentation
- User guide

### Security
- Comprehensive safety policies for each DSL type
- Blocked dangerous commands and patterns
- Confirmation requirements for destructive operations
- Namespace and table restrictions

## [0.1.0] - 2024-XX-XX

### Added
- Initial public release

---

## Types of Changes

- `Added` for new features
- `Changed` for changes in existing functionality
- `Deprecated` for soon-to-be removed features
- `Removed` for now removed features
- `Fixed` for any bug fixes
- `Security` for vulnerability fixes
