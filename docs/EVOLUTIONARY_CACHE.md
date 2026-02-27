# Evolutionary Cache — Self-Learning Algorithm

> **nlp2cmd** uczy sie z kazdego zapytania. **93.6% trafnosc** (Qwen-Coder-3B),
> **19,524x speedup** z cache, **template pipeline** eliminuje 31% zapytan bez LLM.

## Architektura: 5-Tier Evolutionary Lookup

```
Zapytanie NL --> CACHE EXACT  --> (hit?) --> wynik (~0.01ms)
                     | miss
                     v
               CACHE FUZZY   --> (hit?) --> wynik (~0.02ms)
                     | miss
                     v
          CACHE SIMILAR (rapidfuzz) --> (hit?) --> wynik (~0.4ms)
                     | miss
                     v
           TEMPLATE PIPELINE (1615) --> (hit?) --> wynik (~5-15ms)
                     | miss
                     v
              LLM TEACHER   --> Qwen2.5-3B (~300ms) --> AUTO-CACHE
```

## Wyniki benchmarku — Standard (4 modele x 16 domen)

### Trafnosc per model

| Model | Przed few-shot | Po few-shot | Delta |
|-------|---------------|-------------|-------|
| **Qwen2.5-Coder-3B** | 79% | **93.6%** | +14.6pp |
| **Qwen2.5-3B** | 83% | **89.4%** | +6.4pp |
| **Gemma2-2B** | 28% | **53.2%** | +25.2pp |
| **Bielik-1.5B** | 26% | **53.2%** | +27.2pp |

### Trafnosc per domena (przed vs po few-shot)

| Domena | Przed | Po | Delta |
|--------|-------|-----|-------|
| **browser** | 50% | **100%** | +50pp |
| **api** | 25% | **67%** | +42pp |
| **rag** | 17% | **58%** | +41pp |
| **iot** | 42% | **75%** | +33pp |
| **presentation** | 42% | **75%** | +33pp |
| **devops** | 58% | **83%** | +25pp |
| **ffmpeg** | 50% | **75%** | +25pp |
| **remote** | 42% | **67%** | +25pp |
| **package_mgmt** | 75% | **92%** | +17pp |
| **kubernetes** | 83% | **92%** | +9pp |
| **media** | 75% | **83%** | +8pp |
| **shell** | 58% | **67%** | +9pp |
| data | 33% | 33% | 0pp |
| sql | 42% | 42% | 0pp |
| docker | 67% | 67% | 0pp |
| git | 100% | 92% | -8pp |

## Wyniki benchmarku — Learning (3 teachery x 3 rundy)

| Teacher | R1 cold | R3 hot | Speedup | Template hits R1 | LLM calls R1 |
|---------|---------|--------|---------|-----------------|-------------|
| **Qwen2.5-3B** | 187ms | 0.017ms | **10,995x** | 21/32 | 11 |
| **Qwen2.5-Coder-3B** | 187ms | 0.017ms | **10,995x** | 21/32 | 11 |
| **Gemma2-2B** | 233ms | 0.017ms | **13,697x** | 21/32 | 11 |

**Template pipeline eliminuje 66% zapytan** (21/32) bez potrzeby LLM.
Remaining 11 queries go to LLM teacher and are cached for future instant lookup.
Cold start average dropped from 314ms to 187ms thanks to template hits (~5ms vs ~300ms).

---

## Implementacja 5 Tierow

### Tier 1a: Cache Exact (~0.01ms)

MD5 fingerprint — O(1) dict lookup.

```python
def fingerprint(text: str) -> str:
    normalized = re.sub(r'\s+', ' ', text.lower().strip())
    return hashlib.md5(normalized.encode()).hexdigest()[:16]
```

### Tier 1b: Cache Fuzzy (~0.02ms)

Word-bag fingerprint — ignoruje stop words, sortuje slowa kluczowe.

### Tier 1c: Cache Similar — rapidfuzz (~0.4ms)

Biblioteka **rapidfuzz** (C++ backend) — `fuzz.WRatio` — kombinacja 4 algorytmow:

| Algorytm | Co lapie |
|----------|----------|
| Simple ratio (Levenshtein) | literowki: "znajdz" vs "znajdz" |
| Partial ratio | podciagi: "pliki PDF" w dluzszym zapytaniu |
| Token sort ratio | zmiana kolejnosci slow |
| Token set ratio | dodatkowe/brakujace slowa |

**Prog**: `NLP2CMD_SIMILARITY_THRESHOLD=88` (domyslnie 88%).

**Testy**: 22 testy w `tests/unit/test_similarity_cache.py`.

### Tier 2: Template Pipeline (~5-15ms)

Uzywa istniejacego `RuleBasedPipeline` (1615 szablonow):
1. Keyword intent detection
2. Regex entity extraction
3. Template generation

Lazy-loaded przy pierwszym wywolaniu. Wynik jest automatycznie cachowany.
**Eliminuje 31% zapytan** bez potrzeby LLM.

### Tier 3: LLM Teacher (~300ms)

Qwen2.5-3B lub Qwen2.5-Coder-3B z **few-shot promptami** per domena.
Kazdy prompt zawiera 2-3 konkretne przyklady Q->A.

Wynik automatycznie cachowany w `.nlp2cmd/learned_schemas.json`.

---

## Few-Shot Prompts — klucz do sukcesu

Dodanie 2-3 konkretnych przykladow do kazdego system prompt dalo:

- **+14.6pp** dla Qwen2.5-Coder (79% -> 93.6%)
- **+27.2pp** dla Bielik (26% -> 53.2%)
- **+50pp** dla domeny browser (50% -> 100%)
- **+42pp** dla domeny api (25% -> 67%)

Przyklad prompt przed/po:

```python
# PRZED (slaby):
"Generuj komende curl. Odpowiedz TYLKO komenda."

# PO (silny):
"""Jestes ekspertem od curl. Przyklady:
Q: wyslij GET -> curl -s https://api.example.com/users
Q: wyslij POST z JSON -> curl -s -X POST -H 'Content-Type: application/json' -d '{"key":"val"}' URL
Q: sprawdz kod HTTP -> curl -o /dev/null -s -w '%{http_code}' URL
Odpowiedz TYLKO komenda curl."""
```

---

## 16 Obslugiwanych Domen (1615 szablonow)

| # | Domena | Szablony | Trafnosc (avg) |
|---|--------|----------|----------------|
| 1 | shell | 648 | 67% |
| 2 | git | 125 | 92% |
| 3 | kubernetes | 94 | 92% |
| 4 | package_mgmt | 85 | 92% |
| 5 | docker | 87 | 67% |
| 6 | sql | 86 | 42% |
| 7 | devops | 60 | 83% |
| 8 | data | 56 | 33% |
| 9 | browser | 54 | 100% |
| 10 | ffmpeg | 48 | 75% |
| 11 | iot | 48 | 75% |
| 12 | remote | 48 | 67% |
| 13 | rag | 47 | 58% |
| 14 | media | 44 | 83% |
| 15 | presentation | 43 | 75% |
| 16 | api | 42 | 67% |

---

## Uzycie

### Python API

```python
from nlp2cmd.generation.evolutionary_cache import EvolutionaryCache

cache = EvolutionaryCache()

# 1. Cold start — template hit (~15ms) lub LLM teacher (~300ms)
r = cache.lookup("znajdz pliki PDF wieksze niz 10MB")

# 2. Hot cache — instant (~0.015ms)
r = cache.lookup("znajdz pliki PDF wieksze niz 10MB")

# 3. Typo — similarity hit (~0.4ms)
r = cache.lookup("znajdz pliki PDF wieksze niz 10MB")
print(r.source)      # "cache_similar"
print(r.confidence)  # 0.91

# 4. Stats
print(cache.get_stats())
```

### CLI / Makefile

```bash
make benchmark         # Standard: 4 modele x 16 domen
make benchmark-learn   # Learning: 3 teachery x 3 rundy
make benchmark-html    # Otworz HTML raport
```

### Zmienne srodowiskowe

```bash
export NLP2CMD_TEACHER_MODEL="qwen2.5:3b"
export NLP2CMD_SIMILARITY_THRESHOLD="88"
export OLLAMA_BASE_URL="http://localhost:11434"
export NLP2CMD_CACHE_DIR="~/.nlp2cmd"
export NLP2CMD_BENCHMARK_MODELS="qwen2.5:3b,gemma2:2b"  # custom model list
```

### Disabling Cache

For testing or benchmarking purposes, you can disable all cache tiers:

```bash
# Via environment variable
export NLP2CMD_DISABLE_CACHE="1"

# In Python
import os
os.environ["NLP2CMD_DISABLE_CACHE"] = "1"

from nlp2cmd.generation.evolutionary_cache import EvolutionaryCache
cache = EvolutionaryCache()
# All lookups will bypass cache and template pipeline

# Benchmark without cache
python3 examples/benchmark_nlp2cmd.py --no-cache
```

When cache is disabled:
- Tier 1 (exact/fuzzy/similarity) lookups are skipped
- Tier 2 (template pipeline) is skipped
- All queries go directly to LLM teacher (Tier 3)

---

## Roadmap

| Priorytet | Zadanie | Status |
|-----------|---------|--------|
| DONE | Evolutionary cache (exact+fuzzy) | 19,524x speedup |
| DONE | Similarity matching (rapidfuzz) | +14.6pp hit rate |
| DONE | Template-first pipeline | 31% queries bez LLM |
| DONE | Few-shot prompts (16 domen) | +14.6pp accuracy (Qwen-Coder) |
| DONE | Prefix-based domain detection | 9/9 accuracy |
| TODO | Few-shot dla sql/data (wciaz slabe) | est. +15-20pp |
| TODO | N-gram + TF-IDF scoring | est. +5% hit rate |
| TODO | Pre-warm cache z popularnymi zapytaniami | instant cold start |

---

## Pliki

| Plik | Opis |
|------|------|
| `src/nlp2cmd/generation/evolutionary_cache.py` | Silnik cache + similarity + template + LLM |
| `tests/unit/test_similarity_cache.py` | 22 testy |
| `examples/benchmark_learning.py` | Learning benchmark |
| `examples/benchmark_nlp2cmd.py` | Standard benchmark |
| `src/nlp2cmd/generation/templates/` | 16 plikow, 1615 szablonow |
| `src/nlp2cmd/generation/pipeline.py` | RuleBasedPipeline (template tier) |

## Powiazane dokumenty

- [Benchmarking](BENCHMARKING.md)
- [Cache Management](CACHE_MANAGEMENT.md)
- [Schema Systems](SCHEMA_SYSTEMS.md)
