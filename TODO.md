# TODO - NLP2CMD Project

> **Diagnostyka:** 2026-02-23 | **Wersja:** 1.1.0-dev | **Moduły:** 129 | **Indeks funkcji:** ~1400+
>
> Źródło analizy: `project.functions.toon` (2026-02-23T20:35)

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
| `concepts/` (1759 ln) odłączone od pipeline | Koncepty jako warstwa kontekstu w pipeline |

### Nieużywane/redundantne moduły

| Moduł | Status | Akcja |
|-------|--------|-------|
| `semantic_matcher.py` (379 ln) | Nadpisany przez `semantic_matcher_optimized.py` (750 ln) | Usunąć |
| `concepts/` (5 plików, 1759 ln) | Zero importów w reszcie projektu | Zintegrować lub usunąć |
| `keywords_old.py` (1715 ln) | Zastąpiony przez `keywords/` pakiet | Usunąć |
| `core_old.py` (1025 ln) | Zastąpiony przez `core/` pakiet | Usunąć |

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

## 🔥 NATYCHMIASTOWE (Sprint 3 — teraz)

### 1. Cleanup plików _old
- [ ] Usuń `core_old.py`, `keywords_old.py`
- [ ] Zweryfikuj `py_compile` i testy po usunięciu

### 2. Usuń redundantny `semantic_matcher.py`
- [ ] Zamień importy na `semantic_matcher_optimized`
- [ ] Usuń `generation/semantic_matcher.py` (379 ln)

### 3. Konsolidacja README
- [ ] Połącz `README.md` + `ENHANCED_README.md` → jeden dokument < 400 ln
- [ ] Przenieś szczegóły do `docs/architecture.md`

### 4. Konsolidacja JSON/YAML → TOON
- [ ] Zdefiniuj `project.unified.toon` z sekcjami: patterns, templates, config
- [ ] Przenieś `patterns.json`, `keyword_intent_detector_config.json`, `template_defaults.json`
- [ ] Użyj istniejącego `parsing/toon_parser.py` (22 fn) do ładowania

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
[2] Intelligent Context Builder (concepts/ + intelligent/)
    → Buduj kontekst: co user chce, jaki obiekt, jakie parametry
    → Semantic similarity do znanych wzorców
    ↓
[3] Generation Pipeline (generation/)
    → Keywords detection → Entity extraction → Template fill
    → LLM repair jeśli confidence < threshold
    ↓
[4] Validation + History
    → Walidacja wygenerowanej komendy
    → Zapis do historii dla przyszłego schema-match
```

### Zadania
- [ ] Przenieś `schema_based/` do `generation/schema/` (bliskość z pipeline)
- [ ] Zintegruj `intelligent/` z pipeline jako pre-processing
- [ ] Dodaj `SchemaRegistry.match(query)` jako pierwszy krok w `RuleBasedPipeline.process()`
- [ ] `concepts/` — zintegruj `semantic_objects` i `dependency_resolver` jako context layer
- [ ] Usuń lub zarchiwizuj nieużywane: `concepts/virtual_objects.py`, `concepts/environment.py`

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
- [ ] **Docker Images**: Oficjalne obrazy
- [ ] **CI/CD Pipeline**: GitHub Actions
- [ ] **API Documentation**: Pełne API reference

---

## 🐛 Znane problemy

| Problem | Wpływ | Status |
|---------|-------|--------|
| Polskie diakrytyki — edge cases | Średni | Fuzzy matching jako fallback |
| `cli/main.py` ~1700 linii po cleanup | Średni | Dalszy refactor w Sprint 4 |
| Dynamic JS content — niekompletna ekstrakcja | Średni | Explicit waits + retry |
| Python 3.13 — brak `_posixsubprocess` | Wysoki | Użyj Python 3.12 |

---

## 🏗️ Roadmap

### v1.1.0 ← **TERAZ** (cleanup + refactor monolitów)
- [x] Rozbicie templates.py, keywords.py, core.py
- [x] Naprawy CLI (browser, history, auto-install)
- [ ] Usunięcie _old.py, redundantnych matcherów
- [ ] Konsolidacja README
- [ ] Konsolidacja JSON → TOON

### v1.2.0 (Schema-First Pipeline)
- [ ] Integracja schema_based/ + intelligent/ z generation/
- [ ] Unified IntentMatcher API
- [ ] Rewrite pipeline.py do schema-first flow
- **ETA**: 2-3 tygodnie

### v2.0.0 (AI-Driven)
- [ ] Real-time learning z historii
- [ ] CQRS + Event Sourcing
- [ ] Full Playwright automation
- **ETA**: 2-3 miesiące

---

## 📊 Statystyki projektu (2026-02-23)

- **129 modułów** Python w `src/`
- **~12,300 linii** w `generation/` (20 plików)
- **~7,800 linii** w schema/intelligent/concepts (odłączone)
- **Kluczowe metryki**:
  - `pipeline.py`: 32 fn, CC do 34
  - `template_generator.py`: 38 fn
  - `keyword_detector.py`: 18 fn (po split z 46)
  - `adapters/shell.py`: 120 fn (2311 ln) — kandydat do split w v1.2.0
