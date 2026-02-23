# TODO - NLP2CMD Project

> **Diagnostyka:** 2026-02-23 | **Wersja:** 1.0.69 | **Moduły:** 125 | **Indeks funkcji:** ~1400+
>
> Źródło analizy: `project.functions.toon` (256KB, 2026-02-23T19:33)

---

## 🔴 DIAGNOZA STANU PROJEKTU (2026-02-23)

### Krytyczny dług techniczny

| Problem | Skala | Wpływ |
|---------|-------|-------|
| 10 plików `*_backup.py` / `*_patched.py` w `src/` | core + 4 adaptery × 2 | Duplikacja kodu, ryzyko rozbieżności |
| 19 plików tymczasowych w root | JSON wyniki testów, logi, CSV | Bałagan w katalogu głównym |
| Monolityczne pliki | templates.py=94fn, keywords.py=46fn, core.py=53fn | Trudność utrzymania |
| Rozproszona konfiguracja | 5 plików JSON w root (polish_*, domain_weights) | Powinny być w `data/` |
| Circular imports | cli ↔ execution ↔ service | Workaround: importy wewnątrz funkcji |
| Klasyfikator PyPI = "Alpha" | `pyproject.toml` vs "production ready" w README | Niespójność |
| README.md = 1031 linii | + ENHANCED_README.md + nakładające się docs | Redundancja |
| `termo2/` + `experiments/` | Puste/nieużywane katalogi | Martwy kod |

### Statystyki z project.functions.toon

- **125 modułów** Python w `src/`
- **Największe moduły** (po liczbie funkcji):
  - `generation/templates.py` — 94 funkcje (CC do 31)
  - `core.py` — 53 funkcje (CC do 64 w `_normalize_entities`)
  - `generation/keywords.py` — 46 funkcje (CC do 47)
  - `schemas/__init__.py` — 43 funkcje
  - `core_patched.py` — 33 fn (≈kopia core.py)
  - `core_backup.py` — 33 fn (≈kopia core.py)
- **Pliki backup/patched do usunięcia:**
  - `core_backup.py`, `core_patched.py`
  - `adapters/shell_backup.py`, `adapters/shell_patched.py`
  - `adapters/docker_backup.py`, `adapters/docker_patched.py`
  - `adapters/sql_backup.py`, `adapters/sql_patched.py`
  - `adapters/kubernetes_backup.py`, `adapters/kubernetes_patched.py`
- **Pliki tymczasowe w root do przeniesienia/usunięcia:**
  - `benchmark_report.json`, `benchmark_results.csv`, `sequential_benchmark_results.json` → `artifacts/`
  - `ci_test_results.json`, `comprehensive_test_results.json`, `test_results.log` → `artifacts/`
  - `enhanced_context_test_results.json`, `multi_site_test_results.json`, `web_schema_test_results.json` → `artifacts/`
  - `nlp2cmd_monitoring_log.json`, `nlp2cmd_test.log` → `artifacts/`
  - `domain_weights.json`, `enhanced_domain_patterns.json`, `enhanced_intents.json` → `data/`
  - `polish_intent_mappings.json`, `polish_shell_patterns.json`, `polish_table_mappings.json` → `data/`

---

## 🔥 NATYCHMIASTOWE DZIAŁANIA (Sprint 1 — ten tydzień)

### 1. Oczyszczenie katalogu głównego
- [ ] Przenieś 6 plików wynikowych testów/benchmarków do `artifacts/`
- [ ] Przenieś 6 plików konfiguracyjnych (polish_*, domain_*, enhanced_*) do `data/`
- [ ] Zaktualizuj importy/ścieżki w kodzie po przeniesieniu
- [ ] Usuń puste katalogi: `termo2/`, `experiments/`, `publish-env/`

### 2. Eliminacja plików backup/patched
- [ ] Porównaj `core.py` vs `core_patched.py` vs `core_backup.py` — zachowaj tylko `core.py`
- [ ] Porównaj adaptery (shell, docker, sql, kubernetes) — zachowaj tylko główne wersje
- [ ] Usuń 10 zbędnych plików po weryfikacji
- [ ] Uruchom testy po usunięciu — potwierdź brak regresji

### 3. Napraw klasyfikator PyPI
- [ ] Zmień `Development Status :: 3 - Alpha` na `4 - Beta` w `pyproject.toml`

### 4. Uruchom i zweryfikuj testy
- [ ] `pytest tests/ -v` — ustal aktualny baseline
- [ ] Napraw ewentualne broken testy
- [ ] Dodaj do CI (jeśli brak)

---

## 🚀 High Priority (Sprint 2)

### Rozwiązanie circular imports (właściwe)
- [ ] Zidentyfikuj pełny graf zależności: cli → execution → service → cli
- [ ] Wydziel interfejsy/protokoły do `nlp2cmd/interfaces/`
- [ ] Usuń workaround-owe importy wewnątrz funkcji
- [ ] Przetestuj poprawność po refactorze

### Konsolidacja konfiguracji do formatu TOON
- [ ] Zdefiniuj schemat `project.unified.toon` z kategoriami: schema, data, config
- [ ] Przenieś zawartość JSON/YAML do zunifikowanego pliku TOON
- [ ] Zaimplementuj loader współdzielony (`parsing/toon_parser.py` — już istnieje, 22 fn)
- [ ] Testy parsera TOON z nowymi danymi

### Rozbicie monolitycznych plików
- [ ] `generation/templates.py` (94 fn) → wydziel per-domain: `templates_shell.py`, `templates_docker.py`, `templates_sql.py`, `templates_k8s.py`
- [ ] `generation/keywords.py` (46 fn) → wydziel `keywords_detection.py` (logika detect) i `keywords_patterns.py` (wzorce)
- [ ] `core.py` (53 fn) → wydziel `core/normalize.py` (entity normalization) i `core/transform.py`

### Konsolidacja dokumentacji
- [ ] Połącz `README.md` (1031 ln) i `ENHANCED_README.md` w jeden spójny dokument
- [ ] Przenieś szczegóły techniczne do `docs/`
- [ ] Zachowaj README < 300 linii (quick start + linki do docs)

---

## ✅ Ukończone (historia)

### v1.0.31 (2026-01-27) — Performance & Benchmarking
- [x] **Performance Benchmarking Suite**: Benchmark tool z analizą termodynamiczną
- [x] **Markdown Report Generation**: Raporty wydajności
- [x] **Sequential vs Single Testing**: Efektywność batch processing
- [x] **Project Structure Reorganization**: Skrypty w logicznych katalogach
- [x] **Makefile Enhancement**: Nowe targety
- [x] **Template Refactoring**: Uproszczona logika conditional
- [x] **Import Path Fixes**: Poprawione importy
- [x] **Documentation Updates**: PROJECT_STRUCTURE.md

### v1.0.21 (2026-01-24) — Enhanced NLP
- [x] **Semantic Similarity**: sentence-transformers
- [x] **Multi-layer Pipeline**: Enhanced context detection
- [x] **Interactive Mode**: Full REPL z persistent session
- [x] **User Directory Recognition**: "usera" → "~"
- [x] **URL Navigation**: Detekcja URL i otwieranie
- [x] **Search Integration**: Google, GitHub, Amazon

### v1.0.20 (2026-01-24) — Web Schema
- [x] **Schema Extraction**: Ekstrakcja elementów
- [x] **Cache Integration**: Playwright browser caching
- [x] **Benchmarking Tool**: Analiza wydajności
- [x] **Cache Warming**: Pre-warm dla common domains
- [x] **Lazy Loading**: On-demand loading modeli NLP

## 🎯 Medium Priority (Sprint 3+)

### Nowe funkcjonalności NLP
- [ ] **Performance Optimization**: Zmniejsz zużycie pamięci enhanced NLP
- [ ] **Custom Models**: Fine-tuning dla specjalistycznych domen
- [ ] **Real-time Learning**: Integracja feedbacku użytkowników

### Shell & Browser
- [ ] **Command History**: Persistent historia komend i ulubione
- [ ] **Auto-completion**: Tab completion dla komend i ścieżek
- [ ] **Form Automation**: Zaawansowane wypełnianie formularzy (form_handler.py — 9 fn)
- [ ] **Multi-tab Management**: Zarządzanie zakładkami przeglądarki
- [ ] **Multi-step Workflows**: Kompleksowe formularze wielostronicowe

### CLI & UX
- [ ] **Interactive Mode Enhancement**: Rich interactive z auto-completion
- [ ] **Configuration Wizard**: Guided setup dla nowych użytkowników
- [ ] **Plugin System**: System wtyczek

### Performance & Monitoring
- [ ] **Parallel Processing**: Multi-threaded intent detection
- [ ] **Memory Optimization**: Zmniejszenie footprintu pamięci
- [ ] **Benchmark Automation**: CI/CD integration

---

## 🔧 Low Priority (Backlog)

### Zaawansowane funkcje
- [ ] **Voice Input**: Integracja STT (powiązanie z projektem stts)
- [ ] **Multi-language**: Wsparcie English, German, French
- [ ] **Custom DSL Creation**: Narzędzia do tworzenia nowych DSL

### Infrastruktura
- [ ] **Docker Images**: Oficjalne obrazy Docker
- [ ] **CI/CD Pipeline**: GitHub Actions + automated tests
- [ ] **Monitoring Integration**: Prometheus/Grafana

### Dokumentacja
- [ ] **API Documentation**: Pełne API reference z przykładami
- [ ] **Architecture Guide**: Decyzje architektoniczne
- [ ] **Troubleshooting Guide**: Rozwiązywanie problemów

---

## 🐛 Znane problemy

| Problem | Wpływ | Workaround |
|---------|-------|------------|
| Polskie diakrytyki — edge cases w normalizacji | Średni | Fuzzy matching jako fallback |
| Dynamic JS content — niekompletna ekstrakcja | Średni | Explicit waits + retry |
| Cache size — niedokładna kalkulacja na niektórych systemach | Niski | Manualna weryfikacja |
| Circular imports (cli ↔ execution ↔ service) | Wysoki | Importy wewnątrz funkcji (tymczasowe) |
| Python 3.13 — brak `_posixsubprocess`, `_opcode` | Wysoki | Użyj Python 3.12 |

---

## 🏗️ Architektura — Roadmap

### Faza 1: Cleanup (v1.1.0) ← **TERAZ**
- Eliminacja backup/patched, porządek w root, konsolidacja docs
- **Status**: Zdiagnozowane, gotowe do wykonania

### Faza 2: Refactor (v1.2.0)
- Rozbicie monolitów (templates, keywords, core)
- Właściwe rozwiązanie circular imports
- Konsolidacja TOON format

### Faza 3: CQRS & Event Sourcing (v2.0.0)
- [ ] **CQRS**: Separacja modeli read/write
- [ ] **Event Store**: Immutable log zdarzeń systemowych
- [ ] **Event Sourcing**: Odbudowa stanu z event stream

### Unified TOON Format
- [ ] **Schema Consolidation**: Merge JSON/YAML → TOON
- [ ] **Deep Context Encoding**: Optymalna struktura dla LLM
- [ ] **Category-based Organization**: schema, data, metadata osobno
- [ ] **Shared Access Patterns**: Współdzielony dostęp do danych

### Command Discovery & Schema Generation
- [ ] **API Structure Analysis**: Generowanie schematów z testowania komend
- [ ] **Complete Command Inventory**: Lista wszystkich komend w systemie
- [ ] **Dynamic Schema Updates**: Real-time aktualizacje schematów

---

## 📊 Progress Tracking

### v1.0.69 (Aktualny — 2026-02-23)
- **Status**: Stabilny, wymaga cleanup
- **125 modułów**, ~1400+ funkcji zaindeksowanych
- **Kluczowy dług**: 10 backup files, 19 temp files, monolityczne moduły

### v1.1.0 (Następny release)
- **Target**: Cleanup + konsolidacja + eliminacja długu technicznego
- **Status**: Zaplanowany (ten sprint)

### v1.2.0 (Planowany)
- **Target**: Refactor monolitów + circular imports + TOON consolidation
- **ETA**: 2-3 tygodnie po v1.1.0

### v2.0.0 (Długoterminowy)
- **Target**: CQRS, Event Sourcing, pełna integracja AI/ML
- **ETA**: 2-3 miesiące

---

## 🤝 Contributing

Patrz [CONTRIBUTING.md](CONTRIBUTING.md).

### Obszary wymagające pomocy
- **Cleanup**: Usuwanie backup/patched, porządkowanie root
- **Testing**: Rozszerzenie pokrycia testami
- **Performance**: Optymalizacja pamięci i szybkości
- **Documentation**: Konsolidacja i ulepszenie docs
- **Internationalization**: Wsparcie dla nowych języków
