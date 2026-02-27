# NLP2CMD — Kolejne Kroki Refaktoryzacji (Sprint 4+)

**Projekt:** [nlp2cmd](https://github.com/wronai/nlp2cmd) · **Wersja:** 1.0.84 · **Data:** 2026-02-27

---

## Gdzie jesteśmy

NLP2CMD przeszedł intensywny cykl refaktoryzacji w trzech sprintach (styczeń–luty 2026). Projekt startował z monolityczną architekturą (~129 modułów, ponad 16K linii w samym `generation/`), a dziś ma czytelniejszą strukturę: ~115 modułów, 1072 testów (0 failed), ~4 543 linie martwego kodu usunięte i rozbite monolity (`templates.py` 94→6 plików, `keywords.py` 46→2, `core.py` 53→3).

Kluczowe osiągnięcia dotychczasowe:

- **Sprint 1** — fix circular imports, migracja JSON config do `data/`, zmiana klasyfikatora PyPI na Beta.
- **Sprint 2** — rozbicie monolitów (`templates/`, `keywords/`, `core/`), naprawy CLI (browser navigate, history, auto-install, auto-confirm).
- **Sprint 3** — usunięcie dead code (`concepts/`, `contracts/`, `nlp/`, `interfaces/`, `*_original.py` — łącznie ~4.5K linii), fix browser automation (`transform_ir` dsl_kind mapping), Evolutionary Cache z 93.6% trafnością i 19 524× speedup.

---

## Sprint 4: Schema-First Pipeline (v1.2.0)

To najważniejszy krok architektoniczny. Obecny pipeline działa jako **fallback chain** (keyword → regex → template → LLM), co oznacza, że inteligentna analiza schematu jest ostatnim, a nie pierwszym krokiem. Docelowo pipeline musi działać odwrotnie: **schema-first**.

### Docelowa architektura

```
User Query
    ↓
[1] Schema Registry Lookup (schema_extraction/ + schema_based/)
    → Czy query pasuje do znanego schematu komendy?
    → Jeśli TAK: generuj bezpośrednio z schematu (wysoka pewność)
    ↓ jeśli NIE
[2] Intelligent Context Builder (intelligent/)
    → Semantic similarity do znanych wzorców
    → Budowanie kontekstu: obiekt, parametry, intencja
    ↓
[3] Generation Pipeline (generation/)
    → Keywords detection → Entity extraction → Template fill
    → LLM repair jeśli confidence < threshold
    ↓
[4] Validation + History
    → Walidacja wygenerowanej komendy
    → Zapis do historii dla przyszłego schema-match
```

### Konkretne zadania

1. **Przenieś `schema_based/` do `generation/schema/`** — bliskość z pipeline, mniej indirekcji w importach.
2. **Zintegruj `intelligent/` z pipeline jako pre-processing** — kontekst budowany raz, dostępny dla wszystkich tierów.
3. **Dodaj `SchemaRegistry.match(query)` jako pierwszy krok w `RuleBasedPipeline.process()`** — jeśli schema match z confidence ≥ 0.85, pomiń resztę pipeline.
4. **Ujednolicenie matcherów** — jedno API: `IntentMatcher.match(text) → MatchResult` z implementacjami `KeywordMatcher`, `SchemaMatcher`, `SemanticMatcher`, `FuzzyMatcher`. Pipeline decyduje o kolejności na podstawie dostępności i kosztu.

**ETA:** 2–3 tygodnie.

---

## Sprint 4b: Split `cli/main.py` ✅

Plik `cli/main.py` ma ~1900 linii — to ostatni duży monolit w projekcie. Plan podziału:

- `cli/main.py` → entry point + argument parsing (~200 ln)
- `cli/commands/run.py` → tryb `--run` z obsługą historii i Playwright
- `cli/commands/generate.py` → domyślny tryb generacji
- `cli/commands/interactive.py` → InteractiveSession REPL
- `cli/commands/tools.py` → repair, validate, analyze_env
- `cli/output.py` → helper functions (output formatting, fallbacks, browser helpers)

To poprawi testowalność poszczególnych trybów i umożliwi równoległy rozwój funkcji CLI.

---

## Sprint 5: Browser & Form Automation

Playwright automation działa, ale wymaga rozbudowy:

- **Inteligentne wypełnianie formularzy** — mapowanie `.env` + `data/form_schema.json` na pola formularza.
- **Multi-step workflows** — formularze wielostronicowe z walidacją między krokami.
- **Auto-detect form schema** — ekstrakcja schematu formularza z DOM przed wypełnieniem (już częściowo zaimplementowane w `web-schema extract`).

---

## Sprint 5+: NLP & Learning

- **Real-time learning** — zapis sukces/porażka każdego zapytania → automatyczna korekta schematów i szablonów.
- **N-gram + TF-IDF scoring** w Evolutionary Cache — szacowany +5% hit rate.
- **Few-shot dla słabych domen** — `sql` (42%) i `data` (33%) wymagają lepszych promptów; szacowany zysk +15–20pp.
- **Custom models** — fine-tuning intent classifier per-user na bazie historii.
- **Memory optimization** — lazy-unload modeli semantic po timeout.

---

## Backlog

| Zadanie | Priorytet | Status |
|---------|-----------|--------|
| Konsolidacja README (README + ENHANCED_README → 1 plik) | Średni | Otwarte |
| Konsolidacja JSON/YAML → TOON | Niski | Otwarte |
| Voice input (integracja STT z projektem stts) | Niski | Backlog |
| Tab completion dla CLI | Średni | Backlog |
| Plugin system per-domain | Niski | Backlog |
| Docker images | Średni | Backlog |
| CI/CD Pipeline (GitHub Actions) | Wysoki | Backlog |
| Multi-language (DE, FR) | Niski | Backlog |

---

## Znane problemy

| Problem | Wpływ | Workaround |
|---------|-------|------------|
| Polskie diakrytyki — edge cases | Średni | Fuzzy matching jako fallback |
| Dynamic JS content — niekompletna ekstrakcja | Średni | Explicit waits + retry |
| Python 3.13 — brak `_posixsubprocess` | Wysoki | Używaj Python 3.12 |
| `pipeline.py` CC do 34 | Średni | Refactor w ramach Sprint 4 |

---

## Metryki sukcesu

Mierzenie postępów refaktoryzacji:

- **Trafność generacji**: 93.6% → cel 97%+ (po schema-first)
- **Średni czas odpowiedzi**: 0.015ms (hot cache) — utrzymać
- **Pokrycie testami**: 1072 testów — cel 1200+ po Sprint 4
- **Cyclomatic Complexity**: `pipeline.py` CC 34 → cel < 15
- **Linie w największym pliku**: `cli/main.py` 1900 → cel < 400
