# Repository Split Plan

This document describes what has been prepared for the planned extraction of
`nlp2cmd-examples` and `nlp2cmd-benchmark` as separate repositories.

---

## nlp2cmd-benchmark

**Source directory:** `benchmarks/`

| File | Description |
|------|-------------|
| `llm_benchmark.py` | LLM accuracy benchmark — 4 models × 16 domains, HTML/JSON output |
| `learning_benchmark.py` | Evolutionary cache benchmark — 3 rounds (cold→warm→hot) |
| `thermodynamic_benchmark.py` | Thermodynamic computing energy/performance benchmark |
| `README.md` | Usage and run instructions |

**What it needs from the main repo:**
- `src/nlp2cmd` package (install via `pip install nlp2cmd`)
- Running `ollama` instance for LLM benchmarks
- `benchmark_output/` directory (auto-created at runtime)

**Status:** All three scripts use `PROJECT_ROOT = Path(__file__).resolve().parents[1]`
and write output to `benchmark_output/` — path-independent once `nlp2cmd` is installed.

---

## nlp2cmd-examples

**Source directories:**
- `examples/` (entire tree)

Key reorganized areas:

| Directory | Contents |
|-----------|----------|
| `examples/01_basics/` | Getting-started and fundamental usage |
| `examples/02_benchmarks/` | Lightweight performance examples (adapter-level timing) |
| `examples/03_integrations/` | External system integrations |
| `examples/04_domain_specific/` | Shell, Docker, SQL, K8s, browser, git |
| `examples/05_advanced_features/dynamic_schemas/` | Dynamic schema extraction, version-aware generation, persistent storage |
| `examples/06_tools_and_utilities/migration_tools/` | JSON/YAML→TOON migration guide, versioned schema demo |

**What it needs from the main repo:**
- `src/nlp2cmd` package (install via `pip install nlp2cmd`)
- `command_schemas/exports/validated_schemas.json` (bundled or generated on first run)

**Status:** All moved example scripts use:
```python
PROJECT_ROOT = Path(__file__).resolve().parents[N]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
```
where `N` matches the directory depth. After `pip install nlp2cmd` the `sys.path`
manipulation can be dropped entirely.

---

## Changes made during reorganization

- `demos/*.py` (7 files) → `examples/05_advanced_features/dynamic_schemas/`
- `demos/demo_versioned_schemas.py` → `examples/06_tools_and_utilities/migration_tools/`
- `examples/benchmark_nlp2cmd.py.deprecated` → `benchmarks/llm_benchmark.py`
- `examples/benchmark_learning.py.deprecated` → `benchmarks/learning_benchmark.py`
- `demos/` directory removed (empty after moves)
- All `sys.path.insert(0, './src')` patterns replaced with repo-root-relative paths
- Runtime output directories moved from `./` to `PROJECT_ROOT/generated/`
- `Makefile` targets `benchmark`, `benchmark-no-cache`, `benchmark-learn`, `demo-benchmark` updated to `benchmarks/`
- `docs/development/BENCHMARKING.md` updated
- `docs/reference/examples-guide.md` updated
- `examples/README.md`, `examples/02_benchmarks/README.md` updated
- `src/nlp2cmd/generation/schema/adapter.py` updated to find `validated_schemas.json` via repo root before cwd fallback
