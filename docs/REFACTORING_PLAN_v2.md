# NLP2CMD — Plan Refaktoryzacji v2: Od Regex do NLP

**Projekt:** [nlp2cmd](https://github.com/wronai/nlp2cmd) · **Wersja:** 1.0.85 · **Data:** 2026-02-27

---

## Diagnoza: Co jest źle w obecnej architekturze

### 1. Hardkodowane regex zamiast NLP (~4 200 linii regex)

| Plik | Linie | Problem |
|------|-------|---------|
| `keyword_detector.py` | 1 110 | 500+ hardkodowanych stringów polskich/angielskich, substring matching |
| `regex.py` | 906 | Entity extraction oparta wyłącznie na regex |
| `template_generator.py` | 1 151 | 1 558 szablonów z hardkodowanymi wzorcami |
| `complex_detector.py` | 140 | Nowy moduł, ale wciąż regex-only |
| `pipeline_runner.py` | 2 168 | Cognitive Complexity 769 (!) w jednej funkcji |

**Skutek:** Każdy nowy język / nowy synonim wymaga ręcznego dodawania stringów. Zero generalizacji.

### 2. Brak separacji warstw

```
OBECNA ARCHITEKTURA (monolityczna):

User Query → keyword_detector (1100 ln, CC=106)
           → regex extractor (906 ln)  
           → template_generator (1151 ln)
           → pipeline_runner (2168 ln, CC=769!)
           
Problem: Każdy moduł zna zbyt dużo o innych. Pipeline_runner
obsługuje shell, DOM, forms, video, CSV, articles, exploration
w JEDNEJ funkcji 2168 linii.
```

### 3. Brak wielojęzyczności systemowej

- Polskie frazy hardkodowane jako stringi: `"otwórz przeglądarkę"`, `"pokaż pliki"`
- Angielskie frazy osobno: `"show files"`, `"open browser"`
- Zero wsparcia dla: DE, FR, ES, UK, CZ, ...
- Każda literówka wymaga osobnego wpisu: `"dokcer"`, `"doker"`, `"docker"`

### 4. God Object: `pipeline_runner.py`

- **2 168 linii** w jednym pliku
- Jedna metoda `_run_dom_multi_action` ma **CC=769**
- Obsługuje: shell, DOM, forms, video, CSV export, article extraction, company scraping, site exploration — wszystko w jednym

### 5. Brak confidence calibration

- Confidence 0.92 dla "otwórz przeglądarkę" vs 0.95 dla "docker ps" — wartości arbitralne
- Brak walidacji: czy 0.85 jest naprawdę lepsze niż 0.80?

---

## Docelowa Architektura: 5-warstwowa z NLP

```
┌──────────────────────────────────────────────────────────┐
│                    User NL Query                          │
│ "otwórz przeglądarkę i stronę openrouter.ai, wyciągnij  │
│  klucz API i zapisz do .env"                             │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ WARSTWA 1: Language Detection + Normalization             │
│                                                          │
│ • lingua-py / langdetect → wykrycie PL/EN/DE/...         │
│ • Unicode normalization (NFC/NFKD)                       │
│ • Accent folding: "stronę" → "strone"                    │
│ • Typo correction: rapidfuzz + SymSpell                  │
│ • Tokenization: stanza/spaCy (multilingual)              │
│                                                          │
│ Output: NormalizedQuery(lang="pl", tokens=[...],         │
│         corrected_text="...", original="...")             │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ WARSTWA 2: Intent Classification (zamiast regex!)         │
│                                                          │
│ Option A: Lightweight ML (setfit/fasttext, ~5ms)         │
│   • Trenowany na 2000+ przykładach PL+EN+DE              │
│   • Klasy: shell, docker, k8s, sql, browser,             │
│     browser_multi, git, devops, api, ...                 │
│   • Fine-tune na danych użytkownika (active learning)    │
│                                                          │
│ Option B: Sentence Transformers + kNN (~10ms)            │
│   • multilingual-e5-small (384d, 100MB)                  │
│   • Lookup w wektorowej bazie wzorcowych zapytań         │
│   • Zero-shot: nowy język = nowe embeddingi, zero kodu   │
│                                                          │
│ Output: IntentResult(domain="browser",                   │
│         intent="multi_step_automation",                  │
│         confidence=0.94, is_complex=True)                │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ WARSTWA 3: Entity Extraction (zamiast regex!)             │
│                                                          │
│ Option A: GLiNER (zero-shot NER, multilingual)           │
│   • Ekstrakcja: URL, service_name, file_path, env_var   │
│   • Bez trenowania — definiujesz labele, model wyciąga  │
│                                                          │
│ Option B: spaCy + custom NER pipeline                    │
│   • Szybsze (~2ms), ale wymaga trenowania na danych      │
│   • Dedykowane entity types dla CLI/DevOps               │
│                                                          │
│ Option C: Regex fallback (obecny system jako backup)     │
│   • Zachowany jako ostatnia deska ratunku                │
│                                                          │
│ Output: Entities(url="openrouter.ai",                    │
│         service="openrouter", action="extract_key",      │
│         target_file=".env")                              │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ WARSTWA 4: Command Planning + Generation                  │
│                                                          │
│ • Single command: TemplateEngine (istniejący, ulepszony) │
│ • Multi-step: ActionPlanner (rule → LLM fallback)       │
│ • Parametric templates: Jinja2 zamiast f-strings         │
│ • Schema-driven: YAML/JSON schemas per domain            │
│                                                          │
│ Output: ActionPlan | ShellCommand | DQL                   │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ WARSTWA 5: Execution Engine (rozbity pipeline_runner)     │
│                                                          │
│ • ShellExecutor      (shell commands)                    │
│ • BrowserExecutor    (Playwright navigation)             │
│ • FormExecutor       (form filling)                      │
│ • DataExtractor      (scraping, API keys)                │
│ • MediaRecorder      (video, screenshots)                │
│                                                          │
│ Każdy executor: <200 linii, Single Responsibility        │
└──────────────────────────────────────────────────────────┘
```

---

## Etapy Refaktoryzacji

### Etap 1: Normalizacja + Detekcja Języka (1 tydzień)

**Cel:** Każde query przechodzi przez normalizację ZANIM trafi do detektora.

**Nowy moduł:** `src/nlp2cmd/nlp/normalizer.py`

```python
# Propozycja API:
class QueryNormalizer:
    def normalize(self, raw: str) -> NormalizedQuery:
        lang = detect_language(raw)        # lingua-py
        corrected = correct_typos(raw)     # symspellpy / rapidfuzz
        tokens = tokenize(raw, lang)       # stanza lub basic
        lemmas = lemmatize(tokens, lang)   # stanza (opcjonalnie)
        return NormalizedQuery(
            original=raw,
            text=corrected,
            lang=lang,
            tokens=tokens,
            lemmas=lemmas,
        )
```

**Zależności:**
- `lingua-language-detector` (~1MB, szybki, 75 języków)
- `symspellpy` (korekta literówek, zero deps)
- Opcjonalnie: `stanza` (tokenizacja/lematyzacja multilingual)

**Co zastępuje:**
- Hardkodowane `text.lower().strip()` w keyword_detector
- Ręczne mapowania literówek: `"dokcer"→"docker"`, `"doker"→"docker"`
- Brak normalizacji Unicode

### Etap 2: ML Intent Classification (2 tygodnie)

**Cel:** Zastąpić 500+ hardkodowanych stringów w `keyword_detector.py` modelem ML.

**Opcja A — SetFit (rekomendowana):**
```python
# Trenowanie:
from setfit import SetFitModel, SetFitTrainer
model = SetFitModel.from_pretrained("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
trainer = SetFitTrainer(model=model, train_dataset=train_ds)
trainer.train()
model.save_pretrained("models/intent_classifier")

# Inference (~5ms):
model = SetFitModel.from_pretrained("models/intent_classifier")
predictions = model.predict(["otwórz przeglądarkę i stronę X"])
# → "browser_multi_step"
```

**Dane treningowe:** Wyeksportować z istniejących hardkodowanych wzorców:
- `keyword_detector.py`: 500+ wzorców → 500+ training examples
- `template_generator.py`: 1558 szablonów → metadata per intent
- Rozszerzyć o DE/FR/ES tłumaczenia (ChatGPT batch translation)

**Opcja B — FastText:**
- Mniejszy (~5MB), szybszy (~1ms), ale mniej dokładny
- Łatwy fallback jeśli SetFit za wolny w produkcji

**Co zastępuje:**
- `_fast_path_detection()` — 500 linii regex → 5ms ML prediction
- `_keyword_detection()` — 100 linii score matching → 1 ML call
- `_EXPLICIT_OVERRIDES` — 170 wpisów → training data

### Etap 3: NER zamiast Regex Entity Extraction (2 tygodnie)

**Cel:** Zastąpić `regex.py` (906 ln) modelem NER.

**GLiNER (zero-shot, rekomendowany):**
```python
from gliner import GLiNER
model = GLiNER.from_pretrained("urchade/gliner_multi-v2.1")

text = "otwórz openrouter.ai i wyciągnij klucz API, zapisz do .env"
labels = ["url", "service_name", "file_path", "api_key_pattern", "env_variable"]

entities = model.predict_entities(text, labels)
# → [("openrouter.ai", "url"), (".env", "file_path"), ("klucz API", "api_key_pattern")]
```

**Zalety GLiNER:**
- Zero training data needed — definiujesz labele, model wyciąga
- Multilingual out of the box
- ~50ms per query (akceptowalne)

**Fallback:** Zachować istniejący `RegexEntityExtractor` jako backup.

### Etap 4: Rozbicie pipeline_runner.py (2 tygodnie)

**Cel:** Rozbić God Object (2168 ln, CC=769) na osobne executory.

```
src/nlp2cmd/execution/
├── __init__.py
├── base.py              # BaseExecutor, ExecutorResult
├── shell_executor.py    # ShellExecutor (<200 ln)
├── browser_executor.py  # BrowserExecutor (<300 ln)  
├── form_executor.py     # FormExecutor (<200 ln)
├── data_extractor.py    # DataExtractor (<200 ln)
├── media_recorder.py    # MediaRecorder (video/screenshot, <150 ln)
├── action_plan_executor.py  # ActionPlanExecutor (<200 ln)
└── executor_registry.py # maps domain → executor
```

**Zasada:** Każdy executor:
- < 200 linii
- Single Responsibility
- Testowalne w izolacji
- Wspólny interfejs `BaseExecutor.execute(plan) → ExecutorResult`

### Etap 5: Konfiguracja zamiast Hardcode (1 tydzień)

**Cel:** Przenieść hardkodowane wartości do plików konfiguracyjnych.

```yaml
# config/services.yaml
services:
  openrouter:
    base_url: https://openrouter.ai
    keys_url: https://openrouter.ai/settings/keys
    key_pattern: sk-or-v1-[a-f0-9]{64}
    env_var: OPENROUTER_API_KEY
    selectors: [code, .api-key-value]
  anthropic:
    base_url: https://console.anthropic.com
    keys_url: https://console.anthropic.com/settings/keys
    key_pattern: sk-ant-[a-zA-Z0-9-]{40,}
    env_var: ANTHROPIC_API_KEY
```

```yaml
# config/intents.yaml  
browser:
  navigate:
    examples:
      pl: [otwórz stronę, wejdź na stronę, przejdź do]
      en: [open page, go to, navigate to]
      de: [öffne Seite, gehe zu]
    confidence_base: 0.9
  extract_data:
    examples:
      pl: [wyciągnij, skopiuj, pobierz]
      en: [extract, copy, get]
```

**Co zastępuje:**
- `KNOWN_SERVICES` dict w `action_planner.py`
- `_BROWSER_PHRASE_PATTERNS` w `keyword_detector.py`
- `_EXPLICIT_OVERRIDES` (170+ wpisów)
- Hardkodowane URL-e, wzorce kluczy, nazwy zmiennych

### Etap 6: Active Learning + User Feedback (2 tygodnie)

**Cel:** System uczy się z interakcji użytkownika.

```python
class FeedbackCollector:
    def record_correction(self, query, predicted, corrected):
        """User poprawił wynik → dane treningowe."""
        self.training_buffer.append({
            "text": query,
            "label": corrected.domain + "/" + corrected.intent,
        })
        if len(self.training_buffer) >= 50:
            self.retrain_model()  # incremental fine-tune
```

**Cykl:**
1. User query → model predicts
2. User corrects (jeśli błąd)
3. Korekta zapisana do `~/.nlp2cmd/feedback.jsonl`
4. Po 50 korektach → automatyczny retrain
5. Nowy model → lepsze predykcje

---

## Harmonogram

| Etap | Zakres | Czas | Priorytet |
|------|--------|------|-----------|
| **1** | Normalizacja + Language Detection | 1 tydzień | 🔴 Krytyczny |
| **2** | ML Intent Classification (SetFit) | 2 tygodnie | 🔴 Krytyczny |
| **3** | NER Entity Extraction (GLiNER) | 2 tygodnie | 🟡 Wysoki |
| **4** | Rozbicie pipeline_runner | 2 tygodnie | 🔴 Krytyczny |
| **5** | Konfiguracja YAML zamiast hardcode | 1 tydzień | 🟡 Wysoki |
| **6** | Active Learning + Feedback | 2 tygodnie | 🟢 Średni |

**Łącznie:** ~10 tygodni (2.5 miesiąca)

---

## Metryki Sukcesu

| Metryka | Obecna | Cel |
|---------|--------|-----|
| Obsługiwane języki | 2 (PL+EN, hardkoded) | 10+ (zero-shot via embeddingi) |
| Hardkodowane stringi w detektorze | ~500 | <50 (reszta w YAML) |
| CC pipeline_runner | 769 | <30 per executor |
| Czas dodania nowego języka | ~1 tydzień (ręczne stringi) | ~1 godzina (tłumaczenie YAML) |
| Czas dodania nowej komendy | ~30 min (regex + template) | ~5 min (1 YAML entry) |
| Intent accuracy (PL) | ~85% | >95% |
| Intent accuracy (EN) | ~80% | >95% |
| Intent accuracy (DE/FR/ES) | 0% | >85% |
| Typo tolerance | ~10% | >90% (SymSpell) |

---

## Zasady Migracji

1. **Backward compatible** — nowe moduły obok starych, feature flag per warstwa
2. **Incremental** — każdy etap deployowalny osobno
3. **Testable** — każdy nowy moduł ma testy PRZED implementacją
4. **Measurable** — benchmark per etap vs baseline
5. **Fallback** — regex jako last resort, nigdy jako first choice

```python
# Feature flags:
NLP2CMD_USE_ML_INTENT=1      # Etap 2: ML zamiast regex
NLP2CMD_USE_NER=1             # Etap 3: GLiNER zamiast regex
NLP2CMD_USE_NORMALIZER=1      # Etap 1: normalizacja
NLP2CMD_USE_YAML_CONFIG=1     # Etap 5: YAML config
```

---

*Plan stworzony na podstawie analizy 54 932 linii kodu źródłowego w 120 plikach.*
