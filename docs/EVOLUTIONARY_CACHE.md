# Evolutionary Cache — Self-Learning Algorithm

> **nlp2cmd** uczy się z każdego zapytania. Pierwsze wywołanie trwa ~300ms (LLM teacher),
> każde kolejne identyczne zapytanie: **~0.01ms** (cache). Przyspieszenie: **37×**.

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
              LLM TEACHER   ──► Qwen2.5-3B generuje komendę (~200-400ms)
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

## Tier 4: LLM Teacher (~200-400ms)

Qwen2.5-3B generuje komendę przez Ollama API. Wynik jest automatycznie
cachowany w `.nlp2cmd/learned_schemas.json`.

Każda domena ma dedykowany system prompt:
```
"shell": "Generuj komendę Linux shell. Odpowiedz TYLKO komendą."
"docker": "Generuj komendę Docker. Odpowiedz TYLKO komendą."
...
```

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

## Wyniki benchmarku

| Round | Typ | Śr. czas | Cache hits | LLM calls |
|-------|-----|----------|------------|-----------|
| 1 | ❄️ COLD (LLM teacher) | 339ms | 0 | 27 |
| 2 | 🔥 WARM (mixed) | 8ms | 27 | 0 |
| 3 | ⚡ HOT (all cached) | 9ms | 27 | 0 |

**Przyspieszenie: 37.4×** | Cache hit rate: 56.2% | Zaoszczędzony czas: 10.5s

## 16 Obsługiwanych Domen

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

**Łącznie: 1558 szablonów**

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

# Drugie wywołanie — cache instant (~0.01ms)
r2 = cache.lookup("znajdź pliki PDF większe niż 10MB")
print(r2.source)    # "cache_exact"
print(r2.elapsed_ms)  # ~0.01
```

### CLI / Makefile

```bash
make benchmark-learn   # Run learning benchmark (3 rounds × 16 domains)
make benchmark         # Run standard multi-model benchmark
make benchmark-html    # Open HTML report
```

## Konfiguracja

```bash
# Model nauczyciela (domyślnie: qwen2.5:3b)
export NLP2CMD_TEACHER_MODEL="qwen2.5:3b"

# Ollama endpoint
export OLLAMA_BASE_URL="http://localhost:11434"

# Katalog cache (domyślnie: ~/.nlp2cmd/)
# Programowo: EvolutionaryCache(cache_dir=Path("/custom/path"))
```

## Pliki

- [`src/nlp2cmd/generation/evolutionary_cache.py`](../src/nlp2cmd/generation/evolutionary_cache.py) — silnik cache
- [`examples/benchmark_learning.py`](../examples/benchmark_learning.py) — learning benchmark
- [`examples/benchmark_nlp2cmd.py`](../examples/benchmark_nlp2cmd.py) — multi-model benchmark
- [`docs/EVOLUTIONARY_CACHE.md`](EVOLUTIONARY_CACHE.md) — ta dokumentacja

## Powiązane dokumenty

- [Benchmarking](BENCHMARKING.md) — ogólne testy wydajności
- [Cache Management](CACHE_MANAGEMENT.md) — zarządzanie cache CLI
- [Schema Systems](SCHEMA_SYSTEMS.md) — system schematów
