"""
Evolutionary Schema Cache for NLP2CMD.

Implements a 4-tier lookup strategy:
  1. CACHE   — instant lookup from .nlp2cmd/learned_schemas.json (~0ms)
  2. TEMPLATE — match against 1558 predefined templates (~1ms)
  3. REGEX   — regex entity extraction + template fill (~2ms)
  4. LLM     — Qwen2.5-3B teacher generates command, result cached (~200ms)

Each LLM-generated command is cached with its query fingerprint so
subsequent identical or similar queries are served from cache (tier 1).

Cache format (.nlp2cmd/learned_schemas.json):
{
  "version": 2,
  "entries": {
    "<fingerprint>": {
      "query": "original query text",
      "domain": "detected domain",
      "command": "generated command",
      "model": "qwen2.5:3b",
      "hits": 3,
      "created": "2026-02-26T20:00:00",
      "last_used": "2026-02-26T20:05:00"
    }
  },
  "stats": { "total_queries": 100, "cache_hits": 60, "llm_calls": 40 }
}
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import requests

try:
    from rapidfuzz import fuzz as _rfuzz
except ImportError:
    _rfuzz = None

log = logging.getLogger("nlp2cmd.cache")

SIMILARITY_THRESHOLD = float(os.environ.get("NLP2CMD_SIMILARITY_THRESHOLD", "88"))

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
default_cache_dir = Path.home() / ".nlp2cmd"
env_cache_dir = os.environ.get("NLP2CMD_CACHE_DIR", "")
CACHE_DIR = Path(env_cache_dir).expanduser() if env_cache_dir else default_cache_dir
CACHE_FILE = CACHE_DIR / "learned_schemas.json"
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
TEACHER_MODEL = os.environ.get("NLP2CMD_TEACHER_MODEL", "qwen2.5:3b")

# Domain keywords for fast routing
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "shell": ["find", "ls", "cat", "grep", "du", "df", "ps", "kill", "chmod", "chown", "tar", "gzip",
              "plik", "pliki", "katalog", "folder", "proces", "dysk", "uprawnienia", "archiwum"],
    "docker": ["docker", "kontener", "container", "image", "obraz", "compose", "volume", "network"],
    "sql": ["select", "insert", "update", "delete", "create table", "drop", "alter", "tabela", "kolumna",
            "sql", "baza danych", "database", "zapytanie"],
    "kubernetes": ["kubectl", "pod", "deployment", "service", "namespace", "helm", "k8s", "kubernetes",
                   "skaluj", "scale", "rollout"],
    "browser": ["otwórz", "open", "przeglądarka", "browser", "wyszukaj", "google", "strona", "url"],
    "git": ["git", "commit", "push", "pull", "branch", "merge", "rebase", "stash", "clone", "checkout"],
    "devops": ["ansible", "terraform", "systemctl", "service", "usługa", "jenkins", "ci/cd", "pipeline",
               "deploy", "cron", "nginx", "ssl", "certbot"],
    "api": ["curl", "api", "endpoint", "rest", "http", "get", "post", "put", "delete", "webhook",
            "żądanie", "request", "json"],
    "ffmpeg": ["ffmpeg", "ffprobe", "video", "wideo", "audio", "konwertuj", "codec", "mp4", "webm",
               "mkv", "mp3", "rozdzielczość", "resolution"],
    "media": ["convert", "mogrify", "imagemagick", "obraz", "image", "zdjęcie", "photo", "thumbnail",
              "miniaturka", "pdf", "sox"],
    "data": ["jq", "csv", "json", "awk", "sed", "sort", "uniq", "sqlite", "csvkit", "dane", "data",
             "filtruj", "filter", "kolumna"],
    "remote": ["ssh", "scp", "rsync", "tmux", "screen", "zdalny", "remote", "serwer", "server",
               "tunel", "tunnel", "vpn", "wireguard"],
    "iot": ["gpio", "raspberry", "rpi", "i2c", "spi", "mqtt", "czujnik", "sensor", "kamera", "camera",
            "bluetooth", "serial", "arduino"],
    "package_mgmt": ["install", "zainstaluj", "apt", "pip", "npm", "yarn", "snap", "flatpak", "brew",
                     "cargo", "pakiet", "package", "biblioteka"],
    "rag": ["embedding", "vector", "chroma", "qdrant", "rag", "llm", "ollama", "langchain",
            "llama_index", "indeks", "index", "wektorow"],
    "presentation": ["pandoc", "latex", "markdown", "wykres", "chart", "mermaid", "diagram", "pdf",
                     "prezentacja", "raport", "report", "jupyter", "slides"],
}

# System prompts per domain — few-shot examples for weak domains
TEACHER_PROMPTS: dict[str, str] = {
    "shell": """Generuj komendę Linux shell. Przykłady:
Q: znajdź pliki PDF większe niż 10MB -> find / -type f -name '*.pdf' -size +10M
Q: pokaż użycie dysku /var/log -> du -sh /var/log
Odpowiedz TYLKO komendą.""",

    "docker": """Generuj komendę Docker. Przykłady:
Q: pokaż uruchomione kontenery -> docker ps
Q: zbuduj obraz z tagiem myapp -> docker build -t myapp:latest .
Odpowiedz TYLKO komendą.""",

    "sql": """Generuj polecenie SQL. Przykłady:
Q: pokaż użytkowników z Warszawy -> SELECT * FROM users WHERE city = 'Warszawa';
Q: policz zamówienia po miesiącu -> SELECT EXTRACT(MONTH FROM created_at) AS month, COUNT(*) FROM orders GROUP BY month;
Q: utwórz tabelę produkty -> CREATE TABLE produkty (id SERIAL PRIMARY KEY, nazwa VARCHAR(255), cena DECIMAL(10,2));
Odpowiedz TYLKO poleceniem SQL.""",

    "kubernetes": """Generuj komendę kubectl. Przykłady:
Q: pokaż pody w namespace production -> kubectl get pods -n production
Q: przeskaluj deployment do 5 replik -> kubectl scale deployment webapp --replicas=5
Odpowiedz TYLKO komendą.""",

    "browser": """Generuj komendę do otwarcia strony w Linux (xdg-open). Przykłady:
Q: otwórz stronę github.com -> xdg-open 'https://github.com'
Q: wyszukaj w Google python tutorial -> xdg-open 'https://www.google.com/search?q=python+tutorial'
Q: otwórz YouTube -> xdg-open 'https://youtube.com'
Odpowiedz TYLKO komendą z xdg-open.""",

    "git": """Generuj komendę git. Przykłady:
Q: pokaż ostatnie 10 commitów -> git log -10 --oneline
Q: utwórz branch feature/login -> git checkout -b feature/login
Odpowiedz TYLKO komendą.""",

    "devops": """Generuj komendę DevOps. Przykłady:
Q: sprawdź status nginx -> systemctl status nginx
Q: uruchom playbook deploy.yml -> ansible-playbook deploy.yml
Q: zastosuj konfigurację terraform -> terraform apply
Odpowiedz TYLKO komendą.""",

    "api": """Generuj komendę curl do wywołania API. Przykłady:
Q: wyślij GET na https://api.example.com/users -> curl -s https://api.example.com/users
Q: wyślij POST z JSON na /api/login -> curl -s -X POST -H 'Content-Type: application/json' -d '{"user":"admin","pass":"secret"}' https://example.com/api/login
Q: sprawdź kod HTTP serwera -> curl -o /dev/null -s -w '%{http_code}' https://example.com
Odpowiedz TYLKO komendą curl.""",

    "ffmpeg": """Generuj komendę ffmpeg. Przykłady:
Q: konwertuj video.mp4 do webm -> ffmpeg -i video.mp4 output.webm
Q: wyodrębnij audio do mp3 -> ffmpeg -i film.mkv -vn -acodec libmp3lame audio.mp3
Q: zmień rozdzielczość do 720p -> ffmpeg -i input.mp4 -vf scale=-1:720 output.mp4
Odpowiedz TYLKO komendą ffmpeg.""",

    "media": """Generuj komendę ImageMagick/sox. Przykłady:
Q: zmień rozmiar obrazu na 800x600 -> convert photo.jpg -resize 800x600 output.jpg
Q: utwórz miniaturkę 150x150 -> convert header.png -thumbnail 150x150 thumb.png
Q: konwertuj PNG na JPEG -> mogrify -format jpg *.png
Odpowiedz TYLKO komendą.""",

    "data": """Generuj komendę do przetwarzania danych. Przykłady:
Q: pokaż statystyki CSV -> csvstat dane.csv
Q: filtruj JSON po age > 30 -> jq '.[] | select(.age > 30)' users.json
Q: policz unikalne wartości w kolumnie -> cut -d',' -f3 log.csv | sort | uniq -c | sort -rn
Q: pokaż pierwsze 5 wierszy CSV -> head -5 dane.csv
Odpowiedz TYLKO komendą.""",

    "remote": """Generuj komendę SSH/SCP/rsync. Przykłady:
Q: połącz SSH do serwera jako admin -> ssh admin@192.168.1.100
Q: skopiuj plik na serwer do /tmp -> scp backup.tar.gz admin@server:/tmp/
Q: zsynchronizuj katalog na serwer -> rsync -avz /var/www/ admin@server:/var/www/
Odpowiedz TYLKO komendą.""",

    "iot": """Generuj komendę IoT/Raspberry Pi. Przykłady:
Q: odczytaj temperaturę RPi -> vcgencmd measure_temp
Q: wykryj urządzenia I2C -> i2cdetect -y 1
Q: wyślij MQTT na temat sensors -> mosquitto_pub -h localhost -t sensors/temperature -m '22.5'
Odpowiedz TYLKO komendą.""",

    "package_mgmt": """Generuj komendę instalacji pakietu. Przykłady:
Q: zainstaluj nodejs przez apt -> sudo apt install nodejs
Q: zainstaluj requests przez pip -> pip install requests
Q: pokaż globalne pakiety npm -> npm list -g
Odpowiedz TYLKO komendą.""",

    "rag": """Generuj komendę RAG/embeddings/vector DB. Przykłady:
Q: wyszukaj w ChromaDB o machine learning -> python3 -c "import chromadb; c = chromadb.PersistentClient(); col = c.get_collection('docs'); print(col.query(query_texts=['machine learning'], n_results=5))"
Q: wygeneruj embeddingi przez Ollama -> curl -s http://localhost:11434/api/embed -d '{"model": "nomic-embed-text", "input": "machine learning"}'
Q: załaduj PDF z katalogu -> python3 -c "from langchain.document_loaders import DirectoryLoader; docs = DirectoryLoader('/docs', glob='**/*.pdf').load(); print(len(docs), 'documents loaded')"
Odpowiedz TYLKO komendą (python3 -c lub curl).""",

    "presentation": """Generuj komendę do generowania dokumentów/wykresów. Przykłady:
Q: konwertuj README.md do PDF -> pandoc README.md -o README.pdf
Q: wygeneruj wykres z CSV -> python3 -c "import pandas as pd, matplotlib.pyplot as plt; df = pd.read_csv('sales.csv'); df.plot(kind='bar'); plt.savefig('chart.png')"
Q: wyrenderuj diagram Mermaid do PNG -> mmdc -i diagram.mmd -o diagram.png
Odpowiedz TYLKO komendą.""",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class CacheEntry:
    query: str
    domain: str
    command: str
    model: str = ""
    hits: int = 1
    created: str = ""
    last_used: str = ""

    def touch(self):
        self.hits += 1
        self.last_used = datetime.now().isoformat()


@dataclass
class LookupResult:
    command: str
    domain: str
    source: str          # "cache", "template", "regex", "llm"
    elapsed_ms: float
    cached: bool = False
    confidence: float = 1.0


# ---------------------------------------------------------------------------
# Fingerprinting — normalize query for cache lookup
# ---------------------------------------------------------------------------
def fingerprint(text: str) -> str:
    """Create a stable fingerprint for a query (lowercase, stripped, hashed)."""
    normalized = re.sub(r'\s+', ' ', text.lower().strip())
    return hashlib.md5(normalized.encode()).hexdigest()[:16]


def fuzzy_fingerprint(text: str) -> str:
    """Create a looser fingerprint ignoring stop words and punctuation."""
    stop_words = {"a", "i", "w", "z", "na", "do", "po", "od", "dla", "ze", "the",
                  "to", "of", "in", "for", "on", "with", "from", "by", "an", "at",
                  "proszę", "please", "mi", "me", "jak", "how"}
    words = re.sub(r'[^\w\s]', '', text.lower()).split()
    filtered = [w for w in words if w not in stop_words and len(w) > 1]
    return hashlib.md5(' '.join(sorted(filtered)).encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Domain detection (fast keyword-based)
# ---------------------------------------------------------------------------
def detect_domain(text: str) -> str:
    """Detect domain from keywords. Returns best match or 'shell' as default."""
    text_lower = text.lower()
    # High-priority: if the query starts with a known tool name, return immediately
    _PREFIX_MAP = {
        "docker": "docker", "kubectl": "kubernetes", "git ": "git",
        "ffmpeg": "ffmpeg", "ffprobe": "ffmpeg", "curl": "api",
        "ssh ": "remote", "scp ": "remote", "rsync": "remote",
        "ansible": "devops", "terraform": "devops", "systemctl": "devops",
        "apt ": "package_mgmt", "pip ": "package_mgmt", "npm ": "package_mgmt",
        "convert ": "media", "mogrify": "media", "pandoc": "presentation",
        "jq ": "data", "mosquitto": "iot", "i2cdetect": "iot",
    }
    for prefix, domain in _PREFIX_MAP.items():
        if text_lower.startswith(prefix) or f" {prefix}" in text_lower:
            return domain
    # Fallback: keyword scoring
    scores: dict[str, int] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[domain] = score
    if scores:
        return max(scores, key=scores.get)
    return "shell"


# ---------------------------------------------------------------------------
# Cache manager
# ---------------------------------------------------------------------------
class EvolutionaryCache:
    """
    Manages the .nlp2cmd/ learned schema cache.

    Usage:
        cache = EvolutionaryCache()
        result = cache.lookup("znajdź pliki PDF większe niż 10MB")
        # First call: LLM generates, caches; subsequent calls: instant
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        teacher_model: Optional[str] = None,
        ollama_base: Optional[str] = None,
        enable_llm: bool = True,
        similarity_threshold: Optional[float] = None,
    ):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_file = self.cache_dir / "learned_schemas.json"
        self.teacher_model = teacher_model or TEACHER_MODEL
        self.ollama_base = ollama_base or OLLAMA_BASE
        self.enable_llm = enable_llm
        self.similarity_threshold = similarity_threshold if similarity_threshold is not None else SIMILARITY_THRESHOLD

        self.entries: dict[str, dict] = {}
        self.fuzzy_index: dict[str, str] = {}  # fuzzy_fp → exact_fp
        self.stats = {"total_queries": 0, "cache_hits": 0, "llm_calls": 0,
                      "template_hits": 0, "similarity_hits": 0, "total_saved_ms": 0.0}

        self._ensure_dir()
        self._load()

    # -- persistence --------------------------------------------------------
    def _ensure_dir(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _load(self):
        if self.cache_file.exists():
            try:
                data = json.loads(self.cache_file.read_text(encoding="utf-8"))
                self.entries = data.get("entries", {})
                self.stats.update(data.get("stats", {}))
                # Rebuild fuzzy index
                for fp, entry in self.entries.items():
                    ffp = fuzzy_fingerprint(entry.get("query", ""))
                    self.fuzzy_index[ffp] = fp
                log.debug("Loaded %d cached entries", len(self.entries))
            except Exception as exc:
                log.warning("Cache load failed: %s — starting fresh", exc)

    def save(self):
        data = {
            "version": 2,
            "entries": self.entries,
            "stats": self.stats,
            "updated": datetime.now().isoformat(),
        }
        self.cache_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # -- lookup -------------------------------------------------------------
    def lookup(self, query: str, domain: Optional[str] = None) -> LookupResult:
        """
        4-tier lookup: cache → template → regex → LLM teacher.
        Returns LookupResult with command and timing.
        """
        t0 = time.perf_counter()
        self.stats["total_queries"] = self.stats.get("total_queries", 0) + 1
        
        # Check if cache is disabled (for benchmarking)
        cache_disabled = os.environ.get("NLP2CMD_DISABLE_CACHE", "").lower() in ("1", "true", "yes")

        # Tier 1: EXACT cache hit
        fp = fingerprint(query)
        if not cache_disabled and fp in self.entries:
            entry = self.entries[fp]
            entry["hits"] = entry.get("hits", 0) + 1
            entry["last_used"] = datetime.now().isoformat()
            elapsed = (time.perf_counter() - t0) * 1000
            self.stats["cache_hits"] = self.stats.get("cache_hits", 0) + 1
            self.save()
            return LookupResult(
                command=entry["command"], domain=entry.get("domain", "shell"),
                source="cache_exact", elapsed_ms=round(elapsed, 3), cached=True,
            )

        # Tier 1b: FUZZY cache hit
        ffp = fuzzy_fingerprint(query)
        if not cache_disabled and ffp in self.fuzzy_index:
            exact_fp = self.fuzzy_index[ffp]
            if exact_fp in self.entries:
                entry = self.entries[exact_fp]
                entry["hits"] = entry.get("hits", 0) + 1
                entry["last_used"] = datetime.now().isoformat()
                elapsed = (time.perf_counter() - t0) * 1000
                self.stats["cache_hits"] = self.stats.get("cache_hits", 0) + 1
                self.save()
                return LookupResult(
                    command=entry["command"], domain=entry.get("domain", "shell"),
                    source="cache_fuzzy", elapsed_ms=round(elapsed, 3), cached=True,
                )

        # Tier 1c: SIMILARITY cache hit (rapidfuzz)
        sim_result = self._find_similar_cached(query) if not cache_disabled else None
        if sim_result:
            entry, score = sim_result
            entry["hits"] = entry.get("hits", 0) + 1
            entry["last_used"] = datetime.now().isoformat()
            elapsed = (time.perf_counter() - t0) * 1000
            self.stats["cache_hits"] = self.stats.get("cache_hits", 0) + 1
            self.stats["similarity_hits"] = self.stats.get("similarity_hits", 0) + 1
            self.save()
            return LookupResult(
                command=entry["command"], domain=entry.get("domain", "shell"),
                source="cache_similar", elapsed_ms=round(elapsed, 3),
                cached=True, confidence=round(score / 100, 3),
            )

        # Detect domain
        if not domain:
            domain = detect_domain(query)

        # Tier 2: TEMPLATE pipeline (1615 patterns, ~1-5ms)
        tpl_cmd = self._try_template_pipeline(query) if not cache_disabled else None
        if tpl_cmd:
            elapsed = (time.perf_counter() - t0) * 1000
            self.stats["template_hits"] = self.stats.get("template_hits", 0) + 1
            # Cache template result for future instant lookup
            now = datetime.now().isoformat()
            self.entries[fp] = {
                "query": query, "domain": domain, "command": tpl_cmd,
                "model": "template", "hits": 1,
                "created": now, "last_used": now,
            }
            self.fuzzy_index[ffp] = fp
            self.save()
            return LookupResult(
                command=tpl_cmd, domain=domain, source="template",
                elapsed_ms=round(elapsed, 3), cached=False, confidence=0.9,
            )

        # Tier 3: LLM teacher (generates + caches)
        if self.enable_llm:
            try:
                command = self._ask_teacher(query, domain)
                if command:
                    elapsed = (time.perf_counter() - t0) * 1000
                    self.stats["llm_calls"] = self.stats.get("llm_calls", 0) + 1
                    # Cache the result
                    now = datetime.now().isoformat()
                    self.entries[fp] = {
                        "query": query, "domain": domain, "command": command,
                        "model": self.teacher_model, "hits": 1,
                        "created": now, "last_used": now,
                    }
                    self.fuzzy_index[ffp] = fp
                    self.save()
                    return LookupResult(
                        command=command, domain=domain, source="llm_teacher",
                        elapsed_ms=round(elapsed, 3), cached=False,
                    )
            except Exception as exc:
                log.warning("LLM teacher failed: %s", exc)

        elapsed = (time.perf_counter() - t0) * 1000
        return LookupResult(
            command="", domain=domain, source="none",
            elapsed_ms=round(elapsed, 3), cached=False, confidence=0.0,
        )

    # -- LLM teacher --------------------------------------------------------
    # Models that emit <think>...</think> reasoning blocks
    THINKING_MODELS = {"deepseek-r1", "deepseek-r1:1.5b", "deepseek-r1:8b", "deepseek-r1:14b"}

    def _ask_teacher(self, query: str, domain: str) -> str:
        """Call teacher model via Ollama to generate a command."""
        system = TEACHER_PROMPTS.get(domain, TEACHER_PROMPTS["shell"])
        is_thinking = any(t in self.teacher_model for t in ("deepseek-r1",))
        # Use LITELLM_* as primary, fallback to NLP2CMD_LLM_*, then defaults
        temperature = float(
            os.environ.get("LITELLM_TEMPERATURE")
            or os.environ.get("NLP2CMD_LLM_TEMPERATURE", "0.1")
        )
        default_max_tokens = 1024 if is_thinking else 512
        max_tokens = int(
            os.environ.get("LITELLM_MAX_TOKENS")
            or os.environ.get("NLP2CMD_LLM_MAX_TOKENS", str(default_max_tokens))
        )
        timeout = int(
            os.environ.get("LITELLM_TIMEOUT")
            or os.environ.get("NLP2CMD_LLM_TIMEOUT", "30")
        )
        payload = {
            "model": self.teacher_model,
            "prompt": query,
            "system": system,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "stop": [] if is_thinking else ["\n\n"],
            },
        }
        r = requests.post(
            f"{self.ollama_base}/api/generate", json=payload, timeout=timeout
        )
        r.raise_for_status()
        raw = r.json().get("response", "").strip()
        return self._clean(raw)

    @staticmethod
    def _clean(raw: str) -> str:
        """Strip <think> blocks, markdown fences, NL lines, and comments."""
        # Remove <think>...</think> blocks (DeepSeek-R1 reasoning)
        raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL | re.IGNORECASE).strip()
        raw = re.sub(r'^<think>.*$', '', raw, flags=re.IGNORECASE).strip()
        # Extract from markdown code blocks
        m = re.search(r'```(?:\w+)?\s*(.*?)\s*```', raw, re.DOTALL)
        if m:
            raw = m.group(1).strip()
        skip_prefixes = (
            '#', '//', 'sure', 'ok', 'okay', "i'm sorry", 'im sorry',
            'i cannot', "i can't", 'as an ai', "here's", 'here is',
        )
        lines = []
        for l in raw.split('\n'):
            l = l.strip()
            if not l:
                continue
            if l.lower().startswith(skip_prefixes):
                continue
            if len(l.split()) > 12 and not l.startswith(('find ', 'docker ', 'kubectl ', 'git ', 'curl ', 'ffmpeg ', 'ssh ', 'rsync ', 'apt ', 'pip ', 'npm ')):
                continue
            lines.append(l)
        return lines[0] if lines else raw

    # -- template pipeline ---------------------------------------------------
    _pipeline = None
    _tpl_generator = None

    # Polish intent keywords → template intent mapping (keys match TemplateGenerator)
    _PL_INTENT_MAP: dict[str, list[tuple[str, str]]] = {
        "shell": [
            ("znajd", "find"), ("szukaj", "find"), ("wyszukaj", "find"),
            ("pokaż", "list"), ("wyświetl", "list"), ("lista", "list"),
            ("skompresuj", "compress"), ("rozpakuj", "decompress"),
            ("zmień uprawnienia", "chmod"), ("chmod", "chmod"),
            ("policz", "count_files"), ("grep", "grep"), ("użycie dysku", "disk_usage"),
            ("wolne miejsce", "disk_usage"), ("procesy", "process_list"),
            ("największ", "dir_size"),
        ],
        "docker": [
            ("uruchomione", "list"), ("kontenery", "list"),
            ("zbuduj", "build"), ("obraz", "build"),
            ("logi", "logs"), ("zatrzymaj", "stop"), ("usuń", "remove"),
            ("pull", "pull"), ("uruchom", "run"),
        ],
        "git": [
            ("commit", "log"), ("historia", "log"), ("log", "log"),
            ("branch", "branch"), ("status", "status"),
            ("cofnij", "reset"), ("różnice", "diff"),
            ("dodaj", "add_all"), ("push", "push"), ("pull", "pull"),
        ],
        "kubernetes": [
            ("pody", "get_pods"), ("pod", "get_pods"), ("serwisy", "get_services"),
            ("skaluj", "scale"), ("logi", "logs"),
        ],
        "sql": [
            ("pokaż", "select_all"), ("wybierz", "select"), ("znajdź", "select"),
            ("policz", "count"), ("grupuj", "aggregate"), ("pogrupowane", "aggregate"),
            ("utwórz tabelę", "create_table"),
        ],
        "browser": [
            ("otwórz", "navigate"), ("wyszukaj", "search_google"),
            ("google", "search_google"), ("youtube", "open_youtube"),
            ("github", "open_github"),
        ],
        "api": [
            ("get", "navigate"), ("post", "navigate"),
            ("wyślij", "navigate"), ("sprawdź", "navigate"),
        ],
        "ffmpeg": [
            ("konwertuj", "convert"), ("wyodrębnij", "extract_audio"),
            ("rozdzielczość", "resize_720p"), ("720", "resize_720p"),
            ("audio", "extract_audio_mp3"),
        ],
        "media": [
            ("rozmiar", "img_resize"), ("miniaturk", "img_thumbnail"),
            ("konwertuj", "img_batch_convert"),
        ],
        "data": [
            ("statystyk", "csv_info"), ("filtruj", "jq_filter"),
            ("policz", "awk_count"), ("json", "jq_pretty"),
        ],
        "remote": [
            ("ssh", "ssh_connect"), ("skopiuj", "scp_upload"),
            ("zsynchronizuj", "rsync_sync"), ("rsync", "rsync_sync"),
        ],
        "iot": [
            ("temperatur", "rpi_temp"), ("i2c", "i2c_detect"),
            ("mqtt", "mqtt_publish"), ("gpio", "gpio_read"),
            ("kamera", "camera_photo"),
        ],
        "package_mgmt": [
            ("zainstaluj", "apt_install"), ("install", "apt_install"),
            ("pokaż", "apt_list_installed"), ("usuń", "apt_remove"),
            ("aktualizuj", "apt_upgrade"), ("pip", "pip_install"),
            ("npm", "npm_install"),
        ],
        "rag": [
            ("embedding", "embed_ollama"), ("wyszukaj", "chroma_query"),
            ("chroma", "chroma_query"), ("załaduj", "pdf_extract"),
            ("ollama", "ollama_generate"),
        ],
        "presentation": [
            ("pdf", "md_to_pdf"), ("konwertuj", "md_to_pdf"),
            ("wykres", "chart_bar"), ("diagram", "mermaid_render"),
            ("html", "md_to_html"), ("latex", "latex_compile"),
        ],
        "devops": [
            ("status", "service_status"), ("playbook", "ansible_playbook"),
            ("terraform", "terraform_apply"), ("nginx", "service_status"),
            ("cron", "cron_list"),
        ],
    }

    def _try_template_pipeline(self, query: str) -> Optional[str]:
        """Try to match query against built-in templates (1615 patterns).

        Two-phase approach:
        1. RuleBasedPipeline (English keyword detection + regex + templates)
        2. Fallback: Polish domain detection + heuristic intent → TemplateGenerator

        Returns command string or None.
        """
        cmd = self._try_english_pipeline(query)
        if cmd:
            return cmd
        return self._try_polish_template(query)

    def _try_english_pipeline(self, query: str) -> Optional[str]:
        """Phase 1: Use RuleBasedPipeline (English keywords)."""
        try:
            if EvolutionaryCache._pipeline is None:
                from nlp2cmd.generation.pipeline import RuleBasedPipeline
                EvolutionaryCache._pipeline = RuleBasedPipeline(
                    confidence_threshold=0.4
                )
            result = EvolutionaryCache._pipeline.process(query)
            if result.success and result.command:
                cmd = result.command.strip()
                if cmd.startswith("echo ") or cmd.startswith("# "):
                    return None
                if "{" in cmd and "}" in cmd:
                    return None
                return cmd
        except Exception as exc:
            log.debug("English pipeline failed: %s", exc)
        return None

    def _try_polish_template(self, query: str) -> Optional[str]:
        """Phase 2: Polish domain detection + heuristic intent → TemplateGenerator."""
        try:
            domain = detect_domain(query)
            if domain == "shell" and not any(
                kw in query.lower() for kw in (
                    "znajd", "plik", "katalog", "dysk", "proces", "uprawni",
                    "grep", "policz", "skompresuj", "rozpakuj", "wolne",
                )
            ):
                return None  # Weak shell detection fallback

            if EvolutionaryCache._tpl_generator is None:
                from nlp2cmd.generation.template_generator import TemplateGenerator
                EvolutionaryCache._tpl_generator = TemplateGenerator()

            tpl = EvolutionaryCache._tpl_generator
            if domain not in tpl.templates:
                return None

            # Map Polish keywords to intent
            q_lower = query.lower()
            intent = None
            for kw, mapped_intent in self._PL_INTENT_MAP.get(domain, []):
                if kw in q_lower:
                    intent = mapped_intent
                    break

            if not intent:
                return None

            # Extract basic entities from query
            entities = self._extract_basic_entities(query)
            result = tpl.generate(intent=intent, entities=entities, domain=domain)
            if result.success and result.command:
                cmd = result.command.strip()
                if cmd.startswith("echo ") or cmd.startswith("# "):
                    return None
                if "{" in cmd and "}" in cmd:
                    return None
                return cmd
        except Exception as exc:
            log.debug("Polish template failed: %s", exc)
        return None

    @staticmethod
    def _extract_basic_entities(query: str) -> dict:
        """Extract entities from query text for template placeholder filling.

        Provides keys expected by TemplateGenerator templates:
        input, output, file, host, user, url, tag, width, height,
        limit, count, path, package, query, etc.
        """
        import re
        entities: dict = {}
        q = query

        # Files (input/output)
        files = re.findall(r'(\S+\.\w{1,5})', q)
        if files:
            entities["file"] = files[0]
            entities["filename"] = files[0]
            entities["input"] = files[0]
            if len(files) > 1:
                entities["output"] = files[1]
            else:
                # Generate output name
                base, ext = files[0].rsplit('.', 1)
                entities["output"] = f"{base}_out.{ext}"

        # IP addresses → host
        m = re.search(r'(\d{1,3}(?:\.\d{1,3}){3})', q)
        if m:
            entities["host"] = m.group(1)

        # URLs
        m = re.search(r'(https?://\S+)', q)
        if m:
            entities["url"] = m.group(1)

        # Dimensions (WxH)
        m = re.search(r'(\d{2,4})\s*[xX×]\s*(\d{2,4})', q)
        if m:
            entities["width"] = m.group(1)
            entities["height"] = m.group(2)

        # Numbers → limit, count, number
        nums = re.findall(r'(\d+)', q)
        if nums:
            entities["count"] = nums[0]
            entities["number"] = nums[0]
            entities["limit"] = nums[0]
            entities["n"] = nums[0]

        # Paths
        m = re.search(r'(/[\w/.-]+)', q)
        if m:
            entities["path"] = m.group(1)
            entities["directory"] = m.group(1)

        # User (jako/as user)
        m = re.search(r'(?:jako|as)\s+(?:user\s+)?(\w+)', q, re.I)
        if m:
            entities["user"] = m.group(1)
        elif "admin" in q.lower():
            entities["user"] = "admin"
        elif "root" in q.lower():
            entities["user"] = "root"
        else:
            entities["user"] = "user"

        # Tag (z tagiem / tag)
        m = re.search(r'(?:tagiem|tag)\s+(\S+)', q, re.I)
        if m:
            entities["tag"] = m.group(1)
        else:
            entities["tag"] = "latest"
            entities["context"] = "."

        # Package name (zainstaluj X / install X)
        m = re.search(r'(?:zainstaluj|install|zainstalować)\s+(\w[\w.-]*)', q, re.I)
        if m:
            entities["package"] = m.group(1)

        # Search query (for browser/rag)
        m = re.search(r"(?:wyszukaj|szukaj|search|query|o )['\"]?([^'\"]+)", q, re.I)
        if m:
            entities["query"] = m.group(1).strip()

        # Defaults for common template placeholders
        entities.setdefault("db_path", "./chroma_db")
        entities.setdefault("collection", "docs")
        entities.setdefault("query", "search query")
        entities.setdefault("n", "5")

        return entities

    # -- similarity search ---------------------------------------------------
    def _find_similar_cached(self, query: str) -> Optional[tuple[dict, float]]:
        """Find the most similar cached query using rapidfuzz.

        Returns (entry_dict, similarity_score) if score >= threshold, else None.
        Uses rapidfuzz.fuzz.WRatio which combines multiple fuzzy algorithms:
        - Simple ratio (Levenshtein)
        - Partial ratio (substring matching)
        - Token sort ratio (word-order independent)
        - Token set ratio (handles extra/missing words)
        """
        if _rfuzz is None or not self.entries:
            return None
        q_lower = query.lower().strip()
        best_score = 0.0
        best_entry = None
        for _fp, entry in self.entries.items():
            cached_q = entry.get("query", "").lower().strip()
            if not cached_q:
                continue
            score = _rfuzz.WRatio(q_lower, cached_q, score_cutoff=self.similarity_threshold)
            if score > best_score:
                best_score = score
                best_entry = entry
        if best_entry and best_score >= self.similarity_threshold:
            return best_entry, best_score
        return None

    # -- pre-warm cache ------------------------------------------------------
    #: Top-50 queries across all domains for instant cold start
    PREWARM_QUERIES: list[tuple[str, str, str]] = [
        # shell (10)
        ("znajdź pliki PDF większe niż 10MB", "shell", "find / -type f -name '*.pdf' -size +10M"),
        ("pokaż użycie dysku w katalogu /var/log", "shell", "du -sh /var/log"),
        ("pokaż procesy zużywające najwięcej pamięci", "shell", "ps aux --sort=-%mem | head"),
        ("pokaż wolne miejsce na dyskach", "shell", "df -h"),
        ("znajdź pliki zmienione w ostatnich 24h", "shell", "find . -type f -mtime -1"),
        ("skompresuj katalog /var/log do archiwum", "shell", "tar -czf log_backup.tar.gz /var/log"),
        ("pokaż 20 największych plików w katalogu", "shell", "du -ah . | sort -rh | head -20"),
        ("zmień uprawnienia pliku na 755", "shell", "chmod 755 script.sh"),
        ("znajdź tekst 'error' w plikach logów", "shell", "grep -rn 'error' /var/log/"),
        ("policz pliki w bieżącym katalogu rekurencyjnie", "shell", "find . -type f | wc -l"),
        # docker (5)
        ("pokaż uruchomione kontenery docker", "docker", "docker ps"),
        ("zbuduj obraz docker z tagiem myapp", "docker", "docker build -t myapp:latest ."),
        ("pokaż logi kontenera nginx", "docker", "docker logs --tail 100 nginx"),
        ("zatrzymaj wszystkie kontenery", "docker", "docker stop $(docker ps -q)"),
        ("usuń nieużywane obrazy docker", "docker", "docker image prune -f"),
        # git (5)
        ("pokaż ostatnie 10 commitów", "git", "git log -10 --oneline"),
        ("utwórz branch feature/login", "git", "git checkout -b feature/login"),
        ("pokaż status repozytorium", "git", "git status"),
        ("cofnij ostatni commit", "git", "git reset --soft HEAD~1"),
        ("pokaż różnice między branchami", "git", "git diff main..develop"),
        # kubernetes (4)
        ("pokaż pody w namespace production", "kubernetes", "kubectl get pods -n production"),
        ("przeskaluj deployment do 5 replik", "kubernetes", "kubectl scale deployment webapp --replicas=5"),
        ("pokaż logi poda", "kubernetes", "kubectl logs -f nginx-abc123"),
        ("pokaż wszystkie serwisy", "kubernetes", "kubectl get svc --all-namespaces"),
        # sql (4)
        ("pokaż użytkowników z Warszawy", "sql", "SELECT * FROM users WHERE city = 'Warszawa';"),
        ("policz zamówienia po miesiącu", "sql", "SELECT DATE_TRUNC('month', created_at) AS m, COUNT(*) FROM orders GROUP BY m;"),
        ("utwórz tabelę produkty", "sql", "CREATE TABLE produkty (id SERIAL PRIMARY KEY, nazwa VARCHAR(255), cena DECIMAL(10,2));"),
        ("pokaż top 10 klientów po wartości zamówień", "sql", "SELECT customer_id, SUM(total) AS s FROM orders GROUP BY customer_id ORDER BY s DESC LIMIT 10;"),
        # api (3)
        ("wyślij GET na api", "api", "curl -s https://api.example.com/users"),
        ("wyślij POST z JSON", "api", "curl -s -X POST -H 'Content-Type: application/json' -d '{\"key\":\"val\"}' https://example.com/api"),
        ("sprawdź kod HTTP serwera", "api", "curl -o /dev/null -s -w '%{http_code}' https://example.com"),
        # browser (2)
        ("otwórz stronę github.com", "browser", "xdg-open 'https://github.com'"),
        ("wyszukaj w google python tutorial", "browser", "xdg-open 'https://www.google.com/search?q=python+tutorial'"),
        # ffmpeg (3)
        ("konwertuj video.mp4 do webm", "ffmpeg", "ffmpeg -i video.mp4 output.webm"),
        ("wyodrębnij audio z pliku do mp3", "ffmpeg", "ffmpeg -i film.mkv -vn -acodec libmp3lame audio.mp3"),
        ("zmień rozdzielczość video do 720p", "ffmpeg", "ffmpeg -i input.mp4 -vf scale=-1:720 output.mp4"),
        # media (2)
        ("zmień rozmiar obrazu na 800x600", "media", "convert photo.jpg -resize 800x600 output.jpg"),
        ("konwertuj PNG na JPEG", "media", "mogrify -format jpg *.png"),
        # data (3)
        ("pokaż statystyki CSV", "data", "csvstat dane.csv"),
        ("filtruj JSON po polu age", "data", "jq '.[] | select(.age > 30)' users.json"),
        ("policz unikalne wartości w kolumnie", "data", "cut -d',' -f3 data.csv | sort | uniq -c | sort -rn"),
        # remote (2)
        ("połącz SSH do serwera", "remote", "ssh admin@192.168.1.100"),
        ("zsynchronizuj katalog na serwer", "remote", "rsync -avz /var/www/ admin@server:/var/www/"),
        # devops (2)
        ("sprawdź status nginx", "devops", "systemctl status nginx"),
        ("uruchom playbook ansible", "devops", "ansible-playbook deploy.yml"),
        # package_mgmt (2)
        ("zainstaluj nodejs", "package_mgmt", "sudo apt install nodejs"),
        ("zainstaluj requests przez pip", "package_mgmt", "pip install requests"),
        # rag (2)
        ("wygeneruj embeddingi przez ollama", "rag", "curl -s http://localhost:11434/api/embed -d '{\"model\":\"nomic-embed-text\",\"input\":\"text\"}'"),
        ("wyszukaj w chromadb", "rag", "python3 -c \"import chromadb; c = chromadb.PersistentClient(); col = c.get_collection('docs'); print(col.query(query_texts=['query'], n_results=5))\""),
        # presentation (1)
        ("konwertuj markdown do PDF", "presentation", "pandoc README.md -o README.pdf"),
    ]

    def prewarm(self) -> int:
        """Seed cache with top-50 popular queries. Returns count of new entries added."""
        added = 0
        for query, domain, command in self.PREWARM_QUERIES:
            fp = fingerprint(query)
            if fp not in self.entries:
                now = datetime.now().isoformat()
                self.entries[fp] = {
                    "query": query, "domain": domain, "command": command,
                    "model": "prewarm", "hits": 0,
                    "created": now, "last_used": now,
                }
                ffp = fuzzy_fingerprint(query)
                self.fuzzy_index[ffp] = fp
                added += 1
        if added:
            self.save()
            log.info("Pre-warmed cache with %d entries (total: %d)", added, len(self.entries))
        return added

    # -- stats --------------------------------------------------------------
    def get_stats(self) -> dict:
        total = self.stats.get("total_queries", 0)
        hits = self.stats.get("cache_hits", 0)
        return {
            **self.stats,
            "cached_entries": len(self.entries),
            "hit_rate_pct": round(hits / total * 100, 1) if total > 0 else 0,
        }

    def clear(self):
        """Clear the cache."""
        self.entries.clear()
        self.fuzzy_index.clear()
        self.stats = {"total_queries": 0, "cache_hits": 0, "llm_calls": 0,
                      "template_hits": 0, "total_saved_ms": 0.0}
        self.save()
        # Also clear multi-step cache if initialized
        if hasattr(self, "_multistep_loaded"):
            self._multistep_exact.clear()
            self._multistep_fuzzy.clear()
            self._save_multistep()

    # ═══ Multi-Step ActionPlan Cache ═══════════════════════════════════════

    MULTISTEP_CACHE_FILE = "action_plans.json"

    def _init_multistep(self):
        """Initialize multi-step cache (called lazily on first access)."""
        if hasattr(self, "_multistep_loaded"):
            return
        self._multistep_exact: dict[str, dict] = {}
        self._multistep_fuzzy: dict[str, dict] = {}
        self._multistep_loaded = True
        self._load_multistep()

    def lookup_multistep(self, query: str):
        """Look up a cached ActionPlan. Returns ActionPlan or None.

        3-tier: exact (MD5) → fuzzy (word-bag) → similar (rapidfuzz).
        """
        self._init_multistep()
        from nlp2cmd.automation.action_planner import ActionPlan

        # In dynamic schema mode, prefer regenerating schemas rather than
        # reusing fuzzy/similar cached plans (they can be stale or cross-service).
        dynamic_schema_only = os.environ.get(
            "NLP2CMD_DYNAMIC_SCHEMA_ONLY", "",
        ).strip().lower() in {"1", "true", "yes", "on"}

        # Infer intended service from the query (if any)
        wanted_service = None
        try:
            from nlp2cmd.automation.action_planner import ActionPlanner
            wanted_service, _ = ActionPlanner._resolve_service(str(query or "").lower())
        except Exception:
            wanted_service = None

        fp = fingerprint(query)

        # Tier 1a: exact
        if fp in self._multistep_exact:
            entry = self._multistep_exact[fp]
            if wanted_service and entry.get("service") and entry.get("service") != wanted_service:
                return None
            entry["hits"] = entry.get("hits", 0) + 1
            self._save_multistep()
            return ActionPlan.from_cache_dict(entry["plan"])

        if dynamic_schema_only:
            return None

        # Tier 1b: fuzzy
        ffp = fuzzy_fingerprint(query)
        if ffp in self._multistep_fuzzy:
            entry = self._multistep_fuzzy[ffp]
            if wanted_service and entry.get("service") and entry.get("service") != wanted_service:
                return None
            entry["hits"] = entry.get("hits", 0) + 1
            self._save_multistep()
            return ActionPlan.from_cache_dict(entry["plan"])

        # Tier 1c: similar (rapidfuzz)
        if _rfuzz is not None:
            best_score = 0.0
            best_plan = None
            for _fp, entry in self._multistep_exact.items():
                original = entry.get("original_query", "")
                score = _rfuzz.QRatio(query.lower(), original.lower())
                if score > best_score and score >= self.similarity_threshold:
                    best_score = score
                    best_plan = entry["plan"]

            if best_plan:
                # Find entry for best_plan to check service.
                try:
                    for _fp, entry in self._multistep_exact.items():
                        if entry.get("plan") == best_plan:
                            if wanted_service and entry.get("service") and entry.get("service") != wanted_service:
                                return None
                            break
                except Exception:
                    pass
                return ActionPlan.from_cache_dict(best_plan)

        return None

    def store_multistep(self, query: str, plan) -> None:
        """Store an ActionPlan in the multi-step cache."""
        self._init_multistep()

        fp = fingerprint(query)
        ffp = fuzzy_fingerprint(query)

        # Infer service name for cross-service cache safety
        svc_name = None
        try:
            from nlp2cmd.automation.action_planner import ActionPlanner
            svc_name, _ = ActionPlanner._resolve_service(str(query or "").lower())
        except Exception:
            svc_name = None

        entry = {
            "original_query": query,
            "plan": plan.to_cache_dict(),
            "created": time.time(),
            "hits": 0,
            "service": svc_name,
        }

        self._multistep_exact[fp] = entry
        self._multistep_fuzzy[ffp] = entry
        self._save_multistep()

    def _load_multistep(self):
        """Load multi-step cache from disk."""
        path = self.cache_dir / self.MULTISTEP_CACHE_FILE
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self._multistep_exact = data.get("exact", {})
                self._multistep_fuzzy = data.get("fuzzy", {})
                log.debug("Loaded %d multistep cache entries", len(self._multistep_exact))
            except Exception as exc:
                log.warning("Multistep cache load failed: %s", exc)

    def _save_multistep(self):
        """Save multi-step cache to disk."""
        path = self.cache_dir / self.MULTISTEP_CACHE_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(json.dumps({
                "exact": self._multistep_exact,
                "fuzzy": self._multistep_fuzzy,
            }, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            log.warning("Multistep cache save failed: %s", exc)
