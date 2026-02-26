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

log = logging.getLogger("nlp2cmd.cache")

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

# System prompts per domain (compact)
TEACHER_PROMPTS: dict[str, str] = {
    "shell": "Generuj komendę Linux shell. Odpowiedz TYLKO komendą.",
    "docker": "Generuj komendę Docker. Odpowiedz TYLKO komendą.",
    "sql": "Generuj polecenie SQL. Odpowiedz TYLKO poleceniem SQL.",
    "kubernetes": "Generuj komendę kubectl. Odpowiedz TYLKO komendą.",
    "browser": "Generuj komendę do otwarcia/przeszukania strony w Linux. Odpowiedz TYLKO komendą.",
    "git": "Generuj komendę git. Odpowiedz TYLKO komendą.",
    "devops": "Generuj komendę DevOps (systemctl/ansible/terraform). Odpowiedz TYLKO komendą.",
    "api": "Generuj komendę curl/wget do wywołania API. Odpowiedz TYLKO komendą.",
    "ffmpeg": "Generuj komendę ffmpeg. Odpowiedz TYLKO komendą.",
    "media": "Generuj komendę ImageMagick/sox do przetwarzania mediów. Odpowiedz TYLKO komendą.",
    "data": "Generuj komendę do przetwarzania danych (jq/awk/csvkit/sqlite). Odpowiedz TYLKO komendą.",
    "remote": "Generuj komendę ssh/scp/rsync. Odpowiedz TYLKO komendą.",
    "iot": "Generuj komendę IoT/Raspberry Pi (GPIO/I2C/MQTT). Odpowiedz TYLKO komendą.",
    "package_mgmt": "Generuj komendę instalacji pakietu (apt/pip/npm). Odpowiedz TYLKO komendą.",
    "rag": "Generuj komendę RAG/embeddings/vector DB (python/curl/ollama). Odpowiedz TYLKO komendą.",
    "presentation": "Generuj komendę do generowania prezentacji/wykresu (pandoc/matplotlib/mermaid). Odpowiedz TYLKO komendą.",
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
    ):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_file = self.cache_dir / "learned_schemas.json"
        self.teacher_model = teacher_model or TEACHER_MODEL
        self.ollama_base = ollama_base or OLLAMA_BASE
        self.enable_llm = enable_llm

        self.entries: dict[str, dict] = {}
        self.fuzzy_index: dict[str, str] = {}  # fuzzy_fp → exact_fp
        self.stats = {"total_queries": 0, "cache_hits": 0, "llm_calls": 0,
                      "template_hits": 0, "total_saved_ms": 0.0}

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

        # Tier 1: EXACT cache hit
        fp = fingerprint(query)
        if fp in self.entries:
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
        if ffp in self.fuzzy_index:
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

        # Detect domain
        if not domain:
            domain = detect_domain(query)

        # Tier 4: LLM teacher (generates + caches)
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
        temperature = float(os.environ.get("NLP2CMD_LLM_TEMPERATURE", "0.1"))
        default_max_tokens = 1024 if is_thinking else 512
        max_tokens = int(os.environ.get("NLP2CMD_LLM_MAX_TOKENS", str(default_max_tokens)))
        timeout = int(os.environ.get("NLP2CMD_LLM_TIMEOUT", "30"))
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
