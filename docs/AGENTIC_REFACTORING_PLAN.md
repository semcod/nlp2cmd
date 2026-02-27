# Agentic Refactoring Plan — PipelineRunner Evolution

**Data:** 2026-02-27 · **Status:** Phase 1 In Progress

---

## Problem

`PipelineRunner` i powiązane moduły (`form_data_loader`, `site_explorer`, `form_handler`)
zawierają ~200+ linii hardkodowanych selektorów CSS, ścieżek URL, słów kluczowych i polityk.
Te same wartości (np. dismiss selectors) zduplikowane w 3 plikach.

System powinien autonomicznie nawigować po stronach, ale dziś wymaga ręcznego kodowania
selektorów dla każdej nowej domeny.

---

## Docelowa Architektura: Agent-Based Pipeline

```
User Goal ("znajdź firmę X i zapisz dane")
    ↓
[1] GoalParser (LLM) → structured plan
    ↓
[2] AgenticPipelineRunner
    ├── NavigatorAgent    — decyduje: goto/explore/click
    ├── FormAgent         — fill_form → LLM maps fields dynamically
    ├── ExtractorAgent    — extract_* → LLM strukturyzuje dane
    └── SafetyAgent       — waliduje decyzje (policy-based + LLM)
    ↓
[3] SelfImprovingConfig
    → learn_from_success() — wzmocnij udane selektory
    → learn_from_failure() — obniż confidence + generuj nowe
```

---

## Phase 1: Config Extraction + DynamicSelectorGenerator (1 tydzień)

### 1a. Utwórz `data/browser_config/`

```
data/browser_config/
├── selectors.yaml          # Globalne selektory (dismiss, submit, search)
├── contact_paths.yaml      # Wspólne ścieżki kontaktowe
├── junk_field_patterns.yaml # Wzorce pól junk (cookie/captcha/comment)
├── safety_policy.yaml      # Shell execution policy
└── domains/
    ├── _default.yaml       # Domyślna konfiguracja per-domena
    ├── oferteo.pl.yaml     # Specyficzne selektory dla Oferteo
    └── google.com.yaml     # etc.
```

### 1b. `BrowserConfigLoader` — single source of truth

Zastępuje zduplikowane hardkodowane listy w 3+ plikach.

### 1c. `DynamicSelectorGenerator` — LLM fallback

Gdy żaden statyczny selektor nie działa, pyta LLM o sugestię
na podstawie HTML strony. Sukces zapisuje do config per-domena.

---

## Phase 2: Eliminate Hardcode (2 tygodnie)

- Zamień `site_explorer._dismiss_popups()` → `BrowserConfigLoader.get_dismiss_selectors()`
- Zamień `form_data_loader.get_dismiss_selectors()` → `BrowserConfigLoader`
- Zamień `pipeline_runner_utils._is_junk_field()` → config lookup
- Zamień `site_explorer.CONTACT_KEYWORDS` → config
- Zamień hardkodowane `/kontakt`, `/contact` paths → config
- Usuń duplikaty (dismiss selectors w 3 plikach → 1 źródło)

---

## Phase 3: Agentic Runner (3 tygodnie)

- `NavigatorAgent` — LLM decide: goto/explore/back/click
- `FormAgent` — LLM map form fields to data
- `ExtractorAgent` — LLM extract structured data
- `SafetyAgent` — policy + LLM validation

---

## Phase 4: Self-Improving Config (2 tygodnie)

- `SelectorConfidence` tracking per-domain
- `learn_from_success()` / `learn_from_failure()`
- Automatic selector refresh when confidence drops
- Evolutionary cache for selectors (similar to `EvolutionaryCache`)

---

## Hardcoded Audit (2026-02-27)

### Dismiss Selectors (duplicated in 3 places)
- `data/form_schema.json` lines 100-113
- `form_data_loader.py` lines 713-726 (defaults)
- `site_explorer.py` lines 1145-1159

### Contact Paths (duplicated in 2 places)
- `site_explorer.py` lines 411-417 (explore())
- `site_explorer.py` lines 610-616 (find_form())

### Contact Keywords
- `site_explorer.py` lines 99-103 (CONTACT_KEYWORDS)

### Junk Field Patterns
- `pipeline_runner_utils.py` lines 90-115 (_is_junk_field)
- `pipeline_runner_utils.py` lines 118-134 (_is_contact_relevant_field)

### Type/Search Selectors
- `data/form_schema.json` lines 81-97
- `form_data_loader.py` lines 738-752 (get_type_selectors)
