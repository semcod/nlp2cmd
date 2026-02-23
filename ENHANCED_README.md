# NLP2CMD — Stan projektu i architektura

> **Wersja:** 1.0.69 | **Data diagnozy:** 2026-02-23 | **Python:** ≥3.10
>
> Źródło: analiza `project.functions.toon` (256KB, 125 modułów, ~1400+ funkcji)

[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyPI Version](https://img.shields.io/pypi/v/nlp2cmd.svg)](https://pypi.org/project/nlp2cmd/)

---

## Przegląd modułów (z project.functions.toon)

### Core (rdzeń transformacji)

| Moduł | Funkcje | Opis |
|-------|---------|------|
| `core.py` | 53 | Główna klasa `NLP2CMD` — transform, normalize, entity extraction |
| `pipeline_runner.py` | 12 | Executor: shell, DOM/DQL, multi-action browser |
| `schema_driven.py` | 8 | `SchemaDrivenNLP2CMD` — transformacja na bazie AppSpec |
| `ir.py` | 1 | `ActionIR` — intermediate representation |
| `appspec_runtime.py` | 2 | Ładowanie i parsowanie AppSpec |

### Generation (generowanie komend)

| Moduł | Funkcje | Opis |
|-------|---------|------|
| `generation/templates.py` | 94 | Generatory szablonów per-domain (shell, sql, docker, k8s, browser) |
| `generation/keywords.py` | 46 | `KeywordIntentDetector` — 11-warstwowy pipeline detekcji |
| `generation/pipeline.py` | 32 | `RuleBasedPipeline` — orchestrator procesowania |
| `generation/thermodynamic.py` | 31 | `ThermodynamicGenerator` — optymalizacja Langevin |
| `generation/semantic_matcher_optimized.py` | 31 | Semantic matching z FP16, cache, Polish model |
| `generation/data_loader.py` | 28 | `PhraseDatabase` — JSON/msgpack/pickle loader |
| `generation/fuzzy_schema_matcher.py` | 23 | Fuzzy matching: Levenshtein, Jaro-Winkler, n-gram |
| `generation/llm_simple.py` | 19 | LLM fallback (Claude/GPT) |
| `generation/ml_intent_classifier.py` | 15 | ML classifier (sklearn + spaCy) |
| `generation/hybrid.py` | 15 | `HybridThermodynamicGenerator` |
| `generation/semantic_matcher.py` | 14 | Bazowy semantic matcher |
| `generation/enhanced_context.py` | 14 | Enhanced context detection |
| `generation/regex.py` | 11 | `RegexEntityExtractor` |

### Adaptery DSL

| Moduł | Funkcje | Domeny |
|-------|---------|--------|
| `adapters/shell.py` | 120 | Bash, Zsh, Fish, PowerShell |
| `adapters/kubernetes.py` | 23 | kubectl |
| `adapters/docker.py` | 19 | Docker CLI, Compose |
| `adapters/sql.py` | 15 | PostgreSQL, MySQL, SQLite, MSSQL |
| `adapters/dql.py` | 13 | Doctrine Query Language |
| `adapters/dynamic.py` | 21 | Dynamiczne adaptery z extracted schemas |
| `adapters/browser.py` | 10 | Playwright browser automation |

### Schemas & Validation

| Moduł | Funkcje | Opis |
|-------|---------|------|
| `schemas/__init__.py` | 43 | `SchemaRegistry` — 11 formatów plików |
| `validators/__init__.py` | 25 | Walidacja komend i schematów |
| `schema_extraction/__init__.py` | 45 | Dynamic schema extraction |

### NLP & Polish

| Moduł | Funkcje | Opis |
|-------|---------|------|
| `polish_support.py` | 13 | Normalizacja, STT errors, fuzzy matching |
| `nlp_enhanced/__init__.py` | 14 | `HybridNLPBackend` |
| `nlp_light/semantic_shell.py` | 14 | Lightweight semantic backend |

### Web & Browser

| Moduł | Funkcje | Opis |
|-------|---------|------|
| `web_schema/form_data_loader.py` | 38 | Ładowanie danych formularzy |
| `web_schema/history.py` | 15 | Historia interakcji web |
| `web_schema/extractor.py` | 10 | Ekstrakcja elementów DOM |
| `web_schema/form_handler.py` | 9 | Obsługa formularzy |
| `execution/browser.py` | 10 | Browser execution |

### Inne kluczowe moduły

| Moduł | Funkcje | Opis |
|-------|---------|------|
| `concepts/virtual_objects.py` | 20 | Wirtualne obiekty konceptualne |
| `concepts/dependency_resolver.py` | 18 | Resolver zależności |
| `concepts/environment.py` | 16 | Kontekst środowiskowy |
| `feedback/__init__.py` | 21 | Analiza feedbacku i auto-korekta |
| `registry/__init__.py` | 22 | Rejestr akcji (19+ typed actions) |
| `parsing/toon_parser.py` | 22 | Parser formatu TOON |
| `history/tracker.py` | 18 | Śledzenie historii transformacji |

---

## Architektura — Pipeline

```text
User Query (PL/EN)
    │
    ▼
┌──────────────────────┐
│ Text Normalization    │ → polish_support.py (STT fix, diacritics, lemmatization)
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Intent Detection      │ → keywords.py (11 warstw: fast path → ML → semantic → fuzzy)
│ (KeywordIntentDetector)│
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Entity Extraction     │ → regex.py + semantic_entities.py
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Template Generation   │ → templates.py (94 fn, per-domain)
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Command Validation    │ → validators/, schemas/
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Execution             │ → pipeline_runner.py (shell/browser/DQL)
└──────────────────────┘
```

### Detection Pipeline (11 warstw w keywords.py)

1. Text Normalization — Polish diacritics, typo corrections
2. Fast Path — Quick browser/search detection
3. SQL Context — SQL keyword identification
4. SQL DROP — High-priority dangerous ops
5. Docker Detection — Explicit Docker commands
6. Kubernetes Detection — K8s-specific commands
7. Service Restart — Service management priority
8. Priority Intents — Configured high-priority patterns
9. General Pattern Matching — Full keyword matching
10. Fuzzy Matching — rapidfuzz (85% threshold)
11. Final Fallback — Always returns `unknown/unknown`

---

## Dynamic Schema Extraction

```python
from nlp2cmd.schema_extraction import DynamicSchemaRegistry

registry = DynamicSchemaRegistry()

# Z OpenAPI
schema = registry.register_openapi_schema("https://api.example.com/openapi.json")

# Z shell --help
schema = registry.register_shell_help("find")

# Z kodu Python (Click)
schema = registry.register_python_code("my_cli.py")
```

```python
from nlp2cmd.enhanced import EnhancedNLP2CMD

nlp2cmd = EnhancedNLP2CMD()
result = nlp2cmd.transform("find all Python files in current directory")
print(result.command)  # find . -name "*.py" -type f
```

---

## Instalacja

```bash
pip install nlp2cmd[all]        # Pełna instalacja
pip install nlp2cmd[nlp,browser] # NLP + browser automation
```

```bash
# Opcjonalne: API keys dla LLM fallback
export ANTHROPIC_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
```

## Testowanie

```bash
pytest tests/ -v                # Pełny test suite
nlp2cmd --version               # Weryfikacja wersji
nlp2cmd "pokaż procesy"         # Szybki test
```

---

## Znane problemy techniczne (do rozwiązania)

- **10 plików backup/patched** — `core_backup.py`, `core_patched.py`, 8 adapter copies
- **Monolityczne moduły** — `templates.py` (94fn), `keywords.py` (46fn), `core.py` (53fn)
- **Circular imports** — cli ↔ execution ↔ service (workaround: importy wewnątrz funkcji)
- **Python 3.13** — `_posixsubprocess` / `_opcode` missing → użyj Python 3.12

Szczegóły w [TODO.md](TODO.md) — sekcja "Diagnoza stanu projektu".
