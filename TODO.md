# TODO - NLP2CMD Project

> **Diagnostyka:** 2026-02-27 | **Wersja:** 1.0.89 | **Moduły:** ~140 | **Indeks funkcji:** ~1650+
>
> Źródło analizy: `project.toon` (2026-02-27) · 380 plików, 107,572 linii

---

## ✅ Ukończone — Desktop GUI Automation + Agentic Config (2026-02-27)

### Desktop GUI Automation via noVNC
- [x] `docker/novnc/Dockerfile` — full XFCE desktop in Docker (Ubuntu 22.04)
- [x] `docker/novnc/docker-compose.yml` — single-command start
- [x] `docker/novnc/start-vnc.sh` — VNC + noVNC startup
- [x] `docker/novnc/demos/demo_desktop_gui.py` — demo: terminal, calculator, editor, file manager, Firefox
- [x] `src/nlp2cmd/adapters/desktop.py` — `DesktopAdapter` (desktop_dql.v1 DSL)
- [x] Video recording via ffmpeg in Docker
- [x] `docs/DESKTOP_GUI_AUTOMATION.md` — full documentation

### BrowserConfigLoader (Phase 1 Agentic Refactoring)
- [x] `data/browser_config/selectors.yaml` — 16 dismiss + submit + type selectors
- [x] `data/browser_config/contact_paths.yaml` — 9 common paths + keywords
- [x] `data/browser_config/junk_field_patterns.yaml` — junk/contact indicators
- [x] `web_schema/browser_config.py` — `BrowserConfigLoader` + `DynamicSelectorGenerator`
- [x] `docs/AGENTIC_REFACTORING_PLAN.md` — 4-phase plan

### schema_based/ Cleanup
- [x] Removed 313 lines dead code from `schema_based/generator.py` and `adapter.py`
- [x] Clean shims: re-export only from `generation/schema/`
- [x] Testy: 1141 passed, 0 failed

---

## ✅ Ukończone — Screenshot + Video Recording (2026-02-27)

### Browser Automation Features
- [x] **Optional Screenshot Capture** (`ask_for_screenshot`, `take_screenshot`)
  - [x] Interactive prompt: "Zrobić zrzut ekranu? [T/n]"
  - [x] Custom save path or default: `./screenshots/form_YYYYMMDD_HHMMSS.png`
  - [x] Full-page screenshot support
  - [x] Respects `--auto-confirm` flag (skips prompt when auto-confirm enabled)
- [x] **Video Recording** (`VideoRecorder`, `ask_for_video_recording`)
  - [x] Interactive prompt: "Nagrać wideo z procesu? [T/n]"
  - [x] Custom output directory or default: `./recordings/`
  - [x] Playwright native video recording (WebM format, 1280x720)
  - [x] Respects `--auto-confirm` flag (skips prompt when auto-confirm enabled)
- [x] **Pipeline Integration**
  - [x] Video setup in `_run_dom_multi_action` before browser context creation
  - [x] Video teardown after actions complete (success or error)
  - [x] Optional screenshot after `fill_form` action (interactive mode only)
- [x] **Utilities Module** (`pipeline_runner_utils.py`)
  - [x] `get_timestamp()` — timestamp for filenames
  - [x] `ensure_dir()` — directory creation
  - [x] `ask_for_screenshot()` — interactive screenshot prompt
  - [x] `take_screenshot()` — capture and save screenshot
  - [x] `VideoRecorder` class — video recording manager
  - [x] `ask_for_video_recording()` — interactive video prompt
- [x] **Bug Fixes**
  - [x] Fixed missing `Path` import from `pathlib`
  - [x] Fixed `extract_companies` alias for `extract_company_websites_deep`
- [x] **Demo Script** (`examples/demo_screenshot_video.sh`)
  - [x] Automated demonstration of all features
  - [x] Logs results to `demo_results/`

---

## ✅ Ukończone — Oferteo.pl Deep Extraction (2026-02-27)

### Browser Automation Features
- [x] **Deep Company Extraction** (`extract_company_websites_deep`)
  - [x] Navigate to each company profile from catalog
  - [x] Extract external website URLs (filter social media)
  - [x] Return structured data: name, oferteo_url, website
- [x] **CSV Export** (`save_to_csv`)
  - [x] Auto-detect columns from data
  - [x] UTF-8 encoding with headers
- [x] **Form Field Filtering** (PipelineRunner)
  - [x] `_filter_form_fields()` - filters junk/comment forms
  - [x] `_is_junk_field()` - excludes search/cookie/captcha
  - [x] `_is_contact_relevant_field()` - contact form detection
- [x] **Intent Detection Fixes** (BrowserAdapter, run.py)
  - [x] Expanded keywords for deep extraction (plural forms)
  - [x] Auto-detect CSV from filename extension
  - [x] Save detection without explicit "plik" keyword

---

## 🔴 OCENA ARCHITEKTURY `generation/` (2026-02-23)

### Czy `generation/` to poprawna ścieżka?

**TAK** — pod warunkiem przejścia na **Schema-First Pipeline**.

Obecna architektura `generation/` (20 plików, ~12K linii) to multi-layer pipeline:

```
Detection → Extraction → Generation → Validation
(keywords/)  (regex.py)   (template_generator.py)  (validating.py)
    ↓            ↓              ↓
 fuzzy_schema  semantic     llm_simple/llm_multi
 ml_classifier  entities    thermodynamic
 semantic_matcher             hybrid
```

**Problem**: schemat jest "fallback chain" zamiast "schema-first". Inteligentna
analiza wymaga odwrócenia priorytetów:

| Obecnie | Docelowo |
|---------|----------|
| Keyword match → regex → template → LLM fallback | Schema match → Context build → Intelligent generation → Rule fallback |
| `generation/` jest zamknięte na siebie | `schema_based/` + `schema_extraction/` + `intelligent/` zintegrowane |

### Nieużywane/redundantne moduły

| Moduł | Status | Akcja |
|-------|--------|-------|
| ~~`semantic_matcher.py`~~ | ✅ Usunięty (Sprint 2) | — |
| ~~`concepts/`~~ (5 plików, 1759 ln) | ✅ Usunięty (Sprint 3) | — |
| ~~`contracts/`~~ | ✅ Usunięty (Sprint 3) | — |
| ~~`nlp/`~~ (stub interfaces) | ✅ Usunięty (Sprint 3) | — |
| ~~`interfaces/`~~ | ✅ Usunięty (Sprint 3) | — |
| ~~`keywords_old.py`~~ | ✅ Usunięty (Sprint 2) | — |
| ~~`core_old.py`~~ | ✅ Usunięty (Sprint 2) | — |
| ~~`shell_original.py`~~ (1926 ln) | ✅ Usunięty (Sprint 3) | — |
| ~~`main_original.py`~~ (1037 ln) | ✅ Usunięty (Sprint 3) | — |
| ~~`__init___original.py`~~ (1595 ln) | ✅ Usunięty (Sprint 3) | — |

---

## ✅ Ukończone — Sprint 2 (2026-02-23)

### Rozbicie monolitów (DONE)
- [x] `generation/templates.py` (94 fn) → pakiet `templates/` (6 plików per-domain + `template_generator.py`)
- [x] `generation/keywords.py` (46 fn) → pakiet `keywords/` (`keyword_detector.py` + `keyword_patterns.py`)
- [x] `core.py` (53 fn) → pakiet `core/` (`core_models.py` + `core_backends.py` + `core_transform.py`)
- [x] Zaktualizowano wszystkie importy w 15+ plikach (generation, cli, nlp_enhanced, nlp_light, tests)

### Naprawy CLI (DONE)
- [x] **Browser navigate URL fix**: fast-path zachowuje pełny URL z `https://` i ścieżką
- [x] **History disambiguation w --run**: wybór `dom_dql.v1` z historii odpala Playwright zamiast regenerować `navigate`
- [x] **Auto-confirm (-ac) + disambiguation**: `-ac` auto-wybiera komendę z historii jeśli similarity ≥ 0.95
- [x] **Confirm dla submit/press_enter**: retry z `confirm=True` gdy PipelineRunner blokuje akcję
- [x] **Playwright auto-install**: `ensure_playwright_installed()` w ścieżce historii dom_dql.v1
- [x] **`--auto-install` domyślnie ON**: `--auto-install/--no-auto-install` z `default=True`
- [x] **Fix `_handle_run_query` NameError**: dodany wrapper delegujący do `handle_run_mode()`

### Wcześniej ukończone (Sprint 1)
- [x] Zmiana klasyfikatora PyPI z Alpha na Beta
- [x] Przeniesienie JSON config do `data/`
- [x] Fix circular imports (lazy imports w cli, execution, service)

---

## ✅ Ukończone — Sprint 3 (2026-02-26)

### Bug Fix: Browser Automation
- [x] **Fix `transform_ir()` dsl_kind mapping**: `BrowserAdapter.DSL_NAME='browser'` → `dsl_kind='dom'`
- [x] **Prefer adapter's pre-built ActionIR**: `BrowserAdapter.last_action_ir` used directly in `transform_ir()`
- [x] **Root cause**: JSON DSL was executed as shell command via `subprocess.run()`, causing `[Errno 2]`
- [x] **Regression tests**: 2 tests in `TestBrowserAdapterTransformIR`

### Dead Code Cleanup (~4,543 lines removed)
- [x] Usuń `shell_original.py` (1926 ln), `main_original.py` (1037 ln), `__init___original.py` (1595 ln)
- [x] Usuń `concepts/` (5 plików, 1759 ln) — zero importów
- [x] Usuń `contracts/` (1 plik, 10 ln) — zero importów
- [x] Usuń `nlp/` (4 pliki, 145 ln) — stub interfaces, zero importów
- [x] Usuń `interfaces/` (4 pliki, 71 ln) — zero importów
- [x] Usuń `test_ollama_speed.py` (pusty), `test_conceptual_commands.py` (osierocony test)
- [x] Testy: 1072 passed, 0 failed

### Remaining Sprint 3 items
- [ ] Konsolidacja README (`README.md` + `ENHANCED_README.md` → jeden dokument)
- [ ] Konsolidacja JSON/YAML → TOON

---

## ✅ Ukończone — Sprint 4b (2026-02-27)

### Split `cli/main.py` (1901 → 393 lines, 79% reduction)
- [x] `cli/commands/run.py` — `handle_run_mode`, `_handle_run_query`, `_suggest_next_steps` (~460 ln)
- [x] `cli/commands/generate.py` — `handle_generate_query`, `handle_appspec_query` (~160 ln)
- [x] `cli/commands/interactive.py` — `InteractiveSession` REPL + `_interactive_followup` (~500 ln)
- [x] `cli/commands/tools.py` — `cmd_repair`, `cmd_validate`, `cmd_analyze_env` (~160 ln)
- [x] `cli/helpers.py` — shared utilities, adapter factory, browser/Playwright fallbacks (~250 ln)
- [x] Backward compatibility: all public symbols re-exported from `nlp2cmd.cli.main`
- [x] Testy: 1129 passed, 0 failed

### Docs
- [x] `docs/ROADMAP_SPRINT4.md` — full Sprint 4/4b/5 roadmap

---

## ✅ Ukończone — Sprint 4c (2026-02-27)

### Move `schema_based/` → `generation/schema/`
- [x] `generation/schema/__init__.py`, `generator.py`, `adapter.py` — canonical location
- [x] `schema_based/` → backward-compatible shim (re-exports)
- [x] Updated `intelligent/version_aware_generator.py` import

### Extract `pipeline_runner_utils.py` (1568 → 1336 lines)
- [x] `_debug`, `_with_epipe_retry`, form field filtering helpers
- [x] `_MarkdownConsoleWrapper`, `ShellExecutionPolicy`, `RunnerResult`
- [x] All re-exported via `pipeline_runner.py` imports

### Bug Fixes
- [x] Fix `pipeline_runner.py` SyntaxError (unclosed `try` in `fill_form`)
- [x] Fix `test_run_mode_sql` (missing `no_submit` parameter)

### Cleanup
- [x] Removed debug files from root: `minimal_test.py`, `debug_test*.py`
- [x] Testy: 1141 passed, 0 failed

---

## 🚀 High Priority (Sprint 4) — Schema-First Pipeline

### Architektura docelowa

```
User Query
    ↓
[1] Schema Registry Lookup (schema_extraction/ + schema_based/)
    → Czy query pasuje do znanego schematu komendy?
    → Jeśli TAK: generuj bezpośrednio z schematu (wysoka pewność)
    ↓ jeśli NIE
[2] Intelligent Context Builder (intelligent/)
    → Buduj kontekst: co user chce, jaki obiekt, jakie parametry
    → Semantic similarity do znanych wzorców
    ↓
[3] Generation Pipeline (generation/)
    → Keywords detection → Entity extraction → Template fill
    → LLM repair jeśli confidence < threshold
    ↓
[4] Validation + History + Auto-repair
    → Walidacja wygenerowanej komendy
    → Auto-repair błędnych komend (LLM-based)
    → Zapis do historii dla przyszłego schema-match
```

### Zadania
- [x] ~~Przenieś `schema_based/` do `generation/schema/`~~ ✅ Sprint 4c (2026-02-27)
- [ ] Zintegruj `intelligent/` z pipeline jako pre-processing
- [ ] Dodaj `SchemaRegistry.match(query)` jako pierwszy krok w `RuleBasedPipeline.process()`
- [x] ~~Split `cli/main.py` (~1900 ln) → modularny pakiet cli/~~ ✅ Sprint 4b (2026-02-27)
- [ ] **Auto-repair system**: LLM-based naprawa błędnych komend przed wykonaniem

### Unifikacja matcherów
- [ ] Jedno API: `IntentMatcher.match(text) → MatchResult`
- [ ] Implementacje: `KeywordMatcher`, `SchemaMatcher`, `SemanticMatcher`, `FuzzyMatcher`
- [ ] Pipeline decyduje o kolejności na podstawie dostępności i kosztu

---

## 🎯 Medium Priority (Sprint 5+)

### Browser & Form Automation
- [ ] **Form Automation**: Inteligentne wypełnianie formularzy z `.env` + `data/`
- [ ] **Multi-step Workflows**: Kompleksowe formularze wielostronicowe
- [ ] **Auto-detect form schema**: Ekstrakcja schematu formularza z DOM

### NLP & Learning
- [ ] **Real-time Learning**: Zapis sukces/porażka → auto-patch schematów
- [ ] **Custom Models**: Fine-tuning intent classifier per-user
- [ ] **Memory Optimization**: Lazy-unload modeli semantic po timeout

### CLI & UX
- [ ] **Tab completion**: Auto-completion dla komend i ścieżek
- [ ] **Plugin System**: Rozszerzenia per-domain

---

## 🔧 Backlog

- [ ] **Voice Input**: Integracja STT (powiązanie z projektem stts)
- [ ] **Multi-language**: Wsparcie EN, DE, FR (poza PL/EN)
- [ ] **CI/CD Pipeline**: GitHub Actions
- [ ] **API Documentation**: Pełne API reference
- [ ] **Desktop GUI — Windows (RDP)**: xfreerdp + noVNC bridge
- [ ] **Desktop GUI — macOS (VNC)**: Screen Sharing protocol
- [ ] **Desktop GUI — Agentic loop**: LLM decyduje o kolejnych krokach autonomicznie
- [ ] **BrowserConfigLoader Phase 2**: Zamień hardcode w site_explorer/form_data_loader → config lookups
- [ ] **BrowserConfigLoader Phase 3**: AgenticPipelineRunner z NavigatorAgent, FormAgent, ExtractorAgent
- [ ] **BrowserConfigLoader Phase 4**: SelfImprovingConfig — confidence tracking, auto-selector refresh

---

## 🐛 Znane problemy

| Problem | Wpływ | Status |
|---------|-------|--------|
| Polskie diakrytyki — edge cases | Średni | Fuzzy matching jako fallback |
| `pipeline_runner.py` 1336 ln | Średni | Utils extracted, dalszy split planned |
| Dynamic JS content — niekompletna ekstrakcja | Średni | Explicit waits + retry |
| Python 3.13 — brak `_posixsubprocess` | Wysoki | Użyj Python 3.12 |
| Dismiss selectors zduplikowane w 3 plikach | Niski | BrowserConfigLoader gotowy, Phase 2 wpiąć |

---

## 🏗️ Roadmap

### v1.1.0 ✅ (cleanup + refactor monolitów)
- [x] Rozbicie templates.py, keywords.py, core.py
- [x] Naprawy CLI (browser, history, auto-install)
- [x] Usunięcie dead code (~4.5K ln)
- [x] Fix browser automation
- [x] Split cli/main.py (1901 → 393 ln)
- [x] Move schema_based/ → generation/schema/
- [x] Extract pipeline_runner_utils.py

### v1.2.0 ← **TERAZ** (Schema-First + Desktop GUI)
- [x] Desktop GUI automation via noVNC Docker
- [x] BrowserConfigLoader + DynamicSelectorGenerator
- [ ] Integracja intelligent/ z generation/ pipeline
- [ ] Unified IntentMatcher API
- [ ] Rewrite pipeline.py do schema-first flow
- [ ] Konsolidacja README
- **ETA**: 2-3 tygodnie

### v2.0.0 (AI-Driven Autonomous Agent)
- [ ] Agentic pipeline: LLM decision loop
- [ ] Self-improving config per-domain
- [ ] Cross-OS GUI control (Windows RDP, macOS VNC)
- [ ] Real-time learning z historii
- **ETA**: 2-3 miesiące

---

## 📊 Statystyki projektu (2026-02-27)

- **~140 modułów** Python w `src/` · **380 plików** · **107,572 linii**
- **1,141 testów**: 0 failed, 385 deselected
- **Kluczowe metryki po refaktoryzacji**:
  - `cli/main.py`: 393 ln (było 1901, ↓79%)
  - `pipeline_runner.py`: 1336 ln (było 1568, ↓15%)
  - `schema_based/`: czyste shimy (313 ln dead code usunięte)
  - `pipeline_runner_utils.py`: 466 ln (nowy, extracted)
  - `web_schema/browser_config.py`: 237 ln (nowy, Phase 1)
  - `adapters/desktop.py`: nowy (noVNC GUI adapter)
- **Nowe capabilities**: desktop GUI control, browser config YAML, LLM selector generation