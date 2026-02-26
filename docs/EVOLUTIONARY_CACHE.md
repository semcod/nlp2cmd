# Evolutionary Cache — Self-Learning Algorithm

> **nlp2cmd** uczy się z każdego zapytania. Pierwsze wywołanie: LLM teacher (~300ms–4s),
> każde kolejne: **~0.014ms** (cache). Przyspieszenie: **do 302 803×** (DeepSeek-R1).

## Architektura: 4-Tier Evolutionary Lookup

```
Zapytanie NL ──► CACHE EXACT ──► (hit?) ──► ⚡ wynik (~0.01ms)
                     │ miss
                     ▼
               CACHE FUZZY  ──► (hit?) ──► ⚡ wynik (~0.02ms)
                     │ miss
                     ▼
              DOMAIN DETECT  ──► keyword scoring (~0.1ms)
                     │
                     ▼
              LLM TEACHER   ──► Qwen2.5-3B / DeepSeek-R1 (~200ms–4s)
                     │
                     ▼
               AUTO-CACHE   ──► zapisuje do .nlp2cmd/learned_schemas.json
                     │
                     ▼
               ⚡ wynik + zapamiętane na przyszłość
```

## Tier 1: Cache Exact (~0.01ms)

MD5 fingerprint z znormalizowanego zapytania (lowercase, stripped whitespace).
Lookup w `dict` — O(1).

```python
def fingerprint(text: str) -> str:
    normalized = re.sub(r'\s+', ' ', text.lower().strip())
    return hashlib.md5(normalized.encode()).hexdigest()[:16]
```

## Tier 2: Cache Fuzzy (~0.02ms)

Word-bag fingerprint — ignoruje stop words, sortuje słowa kluczowe.
Pozwala trafić cache nawet przy drobnych różnicach w zapytaniu.

```python
def fuzzy_fingerprint(text: str) -> str:
    stop_words = {"a", "i", "w", "z", "na", "do", "po", ...}
    words = re.sub(r'[^\w\s]', '', text.lower()).split()
    filtered = [w for w in words if w not in stop_words and len(w) > 1]
    return hashlib.md5(' '.join(sorted(filtered)).encode()).hexdigest()[:16]
```

## Tier 3: Domain Detection (~0.1ms)

Keyword scoring — 16 domen, każda z listą słów kluczowych (PL+EN).
Zwraca domenę z najwyższym score.

```python
DOMAIN_KEYWORDS = {
    "shell": ["find", "ls", "grep", "plik", "katalog", ...],
    "docker": ["docker", "kontener", "container", "image", ...],
    "kubernetes": ["kubectl", "pod", "deployment", ...],
    # ... 16 domen
}
```

## Tier 4: LLM Teacher (~200ms–4s)

Qwen2.5-3B lub DeepSeek-R1 generuje komendę przez Ollama API. Wynik jest
automatycznie cachowany w `.nlp2cmd/learned_schemas.json`.

Każda domena ma dedykowany system prompt:
```
"shell": "Generuj komendę Linux shell. Odpowiedz TYLKO komendą."
"docker": "Generuj komendę Docker. Odpowiedz TYLKO komendą."
...
```

### Obsługa Thinking Models (DeepSeek-R1)

Modele reasoning emitują `<think>...</think>` bloki przed właściwą odpowiedzią.
Wymagają specjalnej obsługi:

- **Bez `\n\n` stop token** — reasoning zawiera wiele podwójnych newline
- **`num_predict >= 1024`** — potrzebują tokenów na myślenie + odpowiedź
- **Strip `<think>` blocks** — usuwanie bloków reasoning z odpowiedzi
- **Handling unclosed `<think>`** — gdy model zostanie obcięty mid-reasoning

## Format cache `.nlp2cmd/learned_schemas.json`

```json
{
  "version": 2,
  "entries": {
    "a1b2c3d4e5f6g7h8": {
      "query": "znajdź pliki PDF większe niż 10MB",
      "domain": "shell",
      "command": "find / -type f -name '*.pdf' -size +10M",
      "model": "qwen2.5:3b",
      "hits": 5,
      "created": "2026-02-26T20:00:00",
      "last_used": "2026-02-26T20:30:00"
    }
  },
  "stats": {
    "total_queries": 100,
    "cache_hits": 60,
    "llm_calls": 40
  }
}
```

---

## Wyniki benchmarku — Standard (5 modeli x 16 domen x 47 zapytań)

### Trafność per model

| Model | Trafność | Śr. czas | Parametry | Uwagi |
|-------|----------|----------|-----------|-------|
| **Qwen2.5-3B** | **83.0%** | 0.260s | 3B | Najlepszy, 100% w 8 domenach |
| **DeepSeek-R1-1.5B** | **40.4%** | 3.484s | 1.5B | Thinking model, wolny ale dokładny |
| **Gemma2-2B** | 27.7% | 0.110s | 2B | Najszybszy, słaby na PL |
| **Bielik-1.5B** | 25.5% | 0.151s | 1.5B | Polski model, dobry na k8s |
| **Phi (latest)** | 4.3% | 0.426s | 1.6GB | Bardzo słaby na task-oriented prompty |

### Trafność per domena (macierz model x domena)

```
                 Bielik DeepSeek  Gemma2    Phi  Qwen2.5
api               67%      67%      0%      0%     33%
browser            0%      50%      0%      0%     50%
data               0%      33%      0%      0%     67%
devops             0%      67%      0%      0%    100%
docker            67%       0%      0%      0%    100%
ffmpeg            33%      33%      0%      0%    100%
git               67%      33%    100%      0%    100%
iot                0%      33%      0%     33%    100%
kubernetes        67%       0%     67%      0%    100%
media             67%      67%    100%     33%    100%
package_mgmt      33%     100%     67%      0%    100%
presentation       0%      33%     33%      0%     33%
rag                0%      67%      0%      0%    100%
remote             0%       0%      0%      0%     67%
shell              0%       0%     67%      0%    100%
sql                0%      67%      0%      0%     67%
TOTAL             26%      40%     28%      4%     83%
```

### Kluczowe wnioski ze standard benchmark

1. **Qwen2.5-3B jest jednoznacznym liderem** — 83% trafności, 100% w 8/16 domen
2. **DeepSeek-R1 jest zaskakująco dobry** na package_mgmt (100%), api (67%), sql (67%)
   ale jest 13x wolniejszy (~3.5s vs 0.26s) z powodu wewnętrznego reasoning
3. **Thinking models wymagają specjalnej obsługi** — `<think>` bloki muszą być usunięte,
   `\n\n` nie może być stop tokenem, num_predict >= 1024
4. **Słabe domeny** (browser, remote, data, presentation <30%) — potrzebują:
   - Lepszych system promptów z few-shot examples
   - Bardziej tolerancyjnych regex patterns
   - Więcej szablonów
5. **Phi jest bezużyteczny** (4%) — nie nadaje się do command generation

---

## Wyniki benchmarku — Learning (3 teachery x 3 rundy x 32 zapytania)

### Przyspieszenie cache per teacher

| Teacher | R1 (cold) | R3 (hot) | Speedup | Cache entries |
|---------|-----------|----------|---------|---------------|
| **Qwen2.5-3B** | 406ms | 0.017ms | **23 904x** | 32 |
| **Phi:latest** | 477ms | 0.020ms | **18 042x** | 32 |
| **DeepSeek-R1:1.5b** | 4239ms | 0.014ms | **302 803x** | 32 |

### Kluczowe wnioski z learning benchmark

1. **Cache eliminuje całkowicie czas LLM** — Round 3 to czyste O(1) dict lookup
2. **Im wolniejszy model, tym większy zysk z cache** — DeepSeek-R1 zyskuje 300Kx
3. **Qwen2.5-3B to optymalny teacher** — najlepsza trafność (83%) + rozsądny czas cold start
4. **Wszystkie modele osiągają identyczny czas hot** (~0.015ms) — cache jest model-agnostic

---

## 6 Metod Zwiększenia Efektywności

### Metoda 1: Evolutionary Cache (zaimplementowana)

Cache-first z LLM teacher fallback. Fingerprint exact + fuzzy.
- **Zysk**: 18K–303Kx przyspieszenie
- **Koszt**: Pierwszy cold start per unikalne zapytanie
- **Plik**: `src/nlp2cmd/generation/evolutionary_cache.py`

### Metoda 2: Thinking Model Support (zaimplementowana)

Specjalna obsługa modeli reasoning (DeepSeek-R1):
- Wyłączenie `\n\n` jako stop token
- Zwiększenie `num_predict` do 1024
- Usuwanie `<think>...</think>` bloków z odpowiedzi
- Filtrowanie NL-linii i komentarzy

### Metoda 3: Few-Shot Domain Prompts (do implementacji)

Dla słabych domen (browser <20%, remote <15%, data <20%, presentation <20%)
dodanie 2-3 przykładów w system prompt:

```python
# Zamiast:
"Generuj komendę. Odpowiedz TYLKO komendą."

# Lepiej:
"""Generuj komendę. Przykłady:
Q: otwórz stronę github.com -> xdg-open https://github.com
Q: wyszukaj w Google python -> xdg-open 'https://www.google.com/search?q=python'
Odpowiedz TYLKO komendą."""
```

**Oczekiwany zysk**: +20-30% trafności na słabych domenach.

### Metoda 4: N-gram Similarity Cache (do implementacji)

Rozszerzenie fuzzy cache o n-gram overlap scoring.
Obecny fuzzy fingerprint jest word-bag (sorted words -> hash).
N-gram similarity pozwala na częściowe dopasowanie:

```python
def ngram_similarity(q1: str, q2: str, n: int = 3) -> float:
    """Jaccard similarity of character n-grams."""
    s1 = {q1[i:i+n] for i in range(len(q1)-n+1)}
    s2 = {q2[i:i+n] for i in range(len(q2)-n+1)}
    return len(s1 & s2) / len(s1 | s2) if s1 | s2 else 0
```

**Oczekiwany zysk**: +15% cache hit rate dla wariantów zapytań.

### Metoda 5: Template-First Pipeline (do implementacji)

Obecnie cache -> LLM. Lepszy pipeline:

```
CACHE -> TEMPLATE (1558 patterns) -> REGEX -> LLM teacher
```

Templates są szybsze od LLM (~1ms vs ~300ms) i deterministyczne.
Dla domen z dobrymi szablonami (shell, docker, k8s, git) template
powinien być sprawdzany PRZED LLM.

**Oczekiwany zysk**: -80% cold start time dla domen z dobrymi szablonami.

### Metoda 6: Ensemble Voting (do implementacji)

Dla krytycznych zapytań — odpytanie 2-3 modeli i wybranie najlepszej odpowiedzi:

```python
def ensemble_generate(query, models=["qwen2.5:3b", "deepseek-r1:1.5b"]):
    results = [ask_model(query, m) for m in models]
    # Scoring: prefer shortest command, matching known patterns, no NL
    return max(results, key=lambda r: score(r))
```

**Oczekiwany zysk**: +10-15% trafności, ale 2-3x wolniej.
Używać tylko dla pierwszego cold start, potem cache.

---

## 16 Obsługiwanych Domen (1558 szablonów)

| # | Domena | Narzędzia | Szablony |
|---|--------|-----------|----------|
| 1 | `shell` | find, ls, grep, ps, du, df | 107 |
| 2 | `docker` | docker, compose | 71 |
| 3 | `sql` | SELECT, INSERT, CREATE, JOIN | 64 |
| 4 | `kubernetes` | kubectl, helm | 76 |
| 5 | `browser` | xdg-open, Playwright | 62 |
| 6 | `git` | git, commit, branch, merge | 115 |
| 7 | `devops` | systemctl, Ansible, Terraform, CI/CD | 78 |
| 8 | `api` | curl, httpie, wget, GraphQL | 58 |
| 9 | `ffmpeg` | ffmpeg, ffprobe, streaming | 64 |
| 10 | `media` | ImageMagick, sox, PDF, exiftool | 56 |
| 11 | `data` | jq, csvkit, awk, sed, sqlite | 72 |
| 12 | `remote` | SSH, SCP, rsync, tmux, VPN | 64 |
| 13 | `iot` | RPi GPIO, I2C, MQTT, sensors | 62 |
| 14 | `package_mgmt` | apt, pip, npm, snap, brew, cargo | 96 |
| 15 | `rag` | ChromaDB, Qdrant, embeddings, LangChain | 40 |
| 16 | `presentation` | pandoc, matplotlib, Mermaid, LaTeX | 68 |

---

## Użycie

### Python API

```python
from nlp2cmd.generation.evolutionary_cache import EvolutionaryCache

cache = EvolutionaryCache()

# Pierwsze wywołanie — LLM teacher (~300ms)
r1 = cache.lookup("znajdź pliki PDF większe niż 10MB")
print(r1.command)   # find / -type f -name '*.pdf' -size +10M
print(r1.source)    # "llm_teacher"
print(r1.elapsed_ms)  # ~300

# Drugie wywołanie — cache instant (~0.014ms)
r2 = cache.lookup("znajdź pliki PDF większe niż 10MB")
print(r2.source)    # "cache_exact"
print(r2.elapsed_ms)  # ~0.014

# Statystyki
print(cache.get_stats())  # {cache_hits: 1, llm_calls: 1, hit_rate_pct: 50.0}
```

### CLI / Makefile

```bash
make benchmark         # Standard: 5 modeli x 16 domen (47 zapytań)
make benchmark-learn   # Learning: 3 teachery x 3 rundy x 32 zapytania
make benchmark-html    # Otwórz HTML raport
make benchmark-plan    # Pokaż plan refaktoryzacji
```

### Zmienne środowiskowe

```bash
export NLP2CMD_TEACHER_MODEL="qwen2.5:3b"     # Domyślny teacher
export NLP2CMD_TEACHER_MODELS="qwen2.5:3b,phi:latest,deepseek-r1:1.5b"  # Multi-teacher
export OLLAMA_BASE_URL="http://localhost:11434" # Ollama endpoint
```

---

## Roadmap Usprawnień

| Priorytet | Zadanie | Oczekiwany zysk | Status |
|-----------|---------|-----------------|--------|
| HIGH | Few-shot prompts dla słabych domen | +20-30% accuracy | do zrobienia |
| HIGH | Template-first pipeline (cache->template->regex->LLM) | -80% cold start | do zrobienia |
| MED | N-gram similarity cache | +15% cache hit rate | do zrobienia |
| MED | Confidence scoring + verified cache entries | Wyższa jakość | do zrobienia |
| LOW | Ensemble voting (multi-model) | +10-15% accuracy | do zrobienia |
| LOW | Pre-warm cache z najczęstszymi zapytaniami | Natychmiastowy cold start | do zrobienia |
| DONE | Evolutionary cache engine | 18K-303Kx speedup | gotowe |
| DONE | Thinking model support (DeepSeek-R1) | +40% accuracy | gotowe |
| DONE | 16 domen, 1558 szablonów | Pełne pokrycie | gotowe |
| DONE | Multi-teacher learning benchmark | Porównanie modeli | gotowe |

---

## Pliki

| Plik | Opis |
|------|------|
| [`src/nlp2cmd/generation/evolutionary_cache.py`](../src/nlp2cmd/generation/evolutionary_cache.py) | Silnik cache + LLM teacher |
| [`examples/benchmark_learning.py`](../examples/benchmark_learning.py) | Learning benchmark (multi-teacher, 3 rundy) |
| [`examples/benchmark_nlp2cmd.py`](../examples/benchmark_nlp2cmd.py) | Standard benchmark (5 modeli x 16 domen) |
| [`src/nlp2cmd/generation/templates/`](../src/nlp2cmd/generation/templates/) | 16 plików z 1558 szablonami |
| [`src/nlp2cmd/generation/regex.py`](../src/nlp2cmd/generation/regex.py) | Regex patterns per domena |
| [`docs/EVOLUTIONARY_CACHE.md`](EVOLUTIONARY_CACHE.md) | Ta dokumentacja |

## Powiązane dokumenty

- [Benchmarking](BENCHMARKING.md) — ogólne testy wydajności
- [Cache Management](CACHE_MANAGEMENT.md) — zarządzanie cache CLI
- [Schema Systems](SCHEMA_SYSTEMS.md) — system schematów
