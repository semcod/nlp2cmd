#!/usr/bin/env python3
"""
NLP2CMD LLM Benchmark — 5 local models (≤3B) across all 6 nlp2cmd domains.

Models tested:
  1. Bielik-1.5B  (Polish, via ollama from GGUF)
  2. qwen2.5:3b   (multilingual 3B)
  3. gemma2:2b     (Google 2B)
  4. phi:latest    (Microsoft Phi, ~1.6GB, ~8-12 t/s)
  5. deepseek-r1:1.5b (DeepSeek R1, ~1.1GB, ~12-18 t/s)

Domains (all 16 nlp2cmd template domains):
  shell, docker, sql, kubernetes, browser, git,
  devops, api, ffmpeg, media, data, remote,
  iot, package_mgmt, rag, presentation

Outputs:
  - benchmark_results.json   — detailed per-query results
  - benchmark_results.html   — interactive chart visualisation
  - benchmark.log            — live execution log
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "benchmark_output"
RESULTS_JSON = RESULTS_DIR / "benchmark_results.json"
RESULTS_HTML = RESULTS_DIR / "benchmark_results.html"
LOG_FILE = RESULTS_DIR / "benchmark.log"

# ---------------------------------------------------------------------------
# Logging setup — log to file + stderr
# ---------------------------------------------------------------------------
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stderr),
    ],
)
log = logging.getLogger("benchmark")

# ---------------------------------------------------------------------------
# Ollama helpers
# ---------------------------------------------------------------------------
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


def ollama_available() -> bool:
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def ollama_model_exists(name: str) -> bool:
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        # match both "name" and "name:latest"
        return any(name in m for m in models)
    except Exception:
        return False


def ollama_create_bielik() -> bool:
    """Create ollama model from local Bielik GGUF if not already present."""
    gguf_path = Path.home() / ".cache" / "bielik" / "bielik-1.5b.gguf"
    if not gguf_path.exists():
        log.warning("Bielik GGUF not found at %s — skipping", gguf_path)
        return False

    modelfile_content = f"""FROM {gguf_path}
PARAMETER temperature 0.2
PARAMETER num_ctx 2048
SYSTEM \"\"\"Jesteś ekspertem od komend Linux, Docker, Kubernetes, SQL, Git i automatyzacji przeglądarki.
Odpowiadaj TYLKO komendą shell/sql/kubectl/docker/git. Nie dodawaj komentarzy ani wyjaśnień.\"\"\"
"""
    modelfile_path = RESULTS_DIR / "Modelfile.bielik"
    modelfile_path.write_text(modelfile_content)

    log.info("Creating ollama model 'bielik-1.5b' from GGUF …")
    try:
        subprocess.run(
            ["ollama", "create", "bielik-1.5b", "-f", str(modelfile_path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        log.info("✅ bielik-1.5b created in ollama")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        log.error("Failed to create bielik-1.5b: %s", exc)
        return False


def ollama_generate(model: str, prompt: str, system: str = "", max_tokens: int = 200) -> tuple[str, float]:
    """Call ollama /api/generate, return (text, duration_sec)."""
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": max_tokens,
            "stop": ["\n\n", "```", "</assistant>", "<user>"],
        },
    }
    if system:
        payload["system"] = system

    t0 = time.perf_counter()
    r = requests.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=120)
    elapsed = time.perf_counter() - t0
    r.raise_for_status()
    text = r.json().get("response", "").strip()
    return text, elapsed


# ---------------------------------------------------------------------------
# Test queries — 2-3 per domain, all 16 nlp2cmd domains
# ---------------------------------------------------------------------------
BENCHMARK_QUERIES: dict[str, list[dict[str, str]]] = {
    # === Original 6 domains ===
    "shell": [
        {"query": "znajdź wszystkie pliki PDF większe niż 10MB",
         "expected_pattern": r"find.*\.pdf.*-size", "description": "Find large PDF files"},
        {"query": "pokaż użycie dysku w katalogu /var/log",
         "expected_pattern": r"(du|df).*(/var/log|var.log)", "description": "Disk usage /var/log"},
        {"query": "pokaż procesy zużywające najwięcej pamięci",
         "expected_pattern": r"(ps.*sort|top|ps.*mem)", "description": "Top memory processes"},
    ],
    "docker": [
        {"query": "pokaż wszystkie uruchomione kontenery Docker",
         "expected_pattern": r"docker\s+(ps|container\s+ls)", "description": "List containers"},
        {"query": "zbuduj obraz Docker z tagiem myapp:latest",
         "expected_pattern": r"docker\s+build.*-t.*myapp", "description": "Build image"},
        {"query": "pokaż logi kontenera nginx z ostatnich 100 linii",
         "expected_pattern": r"docker\s+logs.*(nginx|--tail|100)", "description": "Container logs"},
    ],
    "sql": [
        {"query": "pokaż wszystkich użytkowników z Warszawy",
         "expected_pattern": r"SELECT.*FROM.*WHERE.*(Warszaw|Warsaw|miasto|city)", "description": "Select WHERE"},
        {"query": "policz zamówienia pogrupowane po miesiącu",
         "expected_pattern": r"(SELECT.*COUNT|GROUP\s+BY|count)", "description": "Count GROUP BY"},
        {"query": "utwórz tabelę produkty z kolumnami id, nazwa, cena",
         "expected_pattern": r"CREATE\s+TABLE.*produkt", "description": "CREATE TABLE"},
    ],
    "kubernetes": [
        {"query": "pokaż wszystkie pody w namespace production",
         "expected_pattern": r"kubectl\s+get\s+pods.*(-n|namespace).*production", "description": "Get pods ns"},
        {"query": "przeskaluj deployment webapp do 5 replik",
         "expected_pattern": r"kubectl\s+scale.*replicas.*5", "description": "Scale deployment"},
        {"query": "pokaż logi poda nginx-abc123",
         "expected_pattern": r"kubectl\s+logs.*nginx", "description": "Pod logs"},
    ],
    "browser": [
        {"query": "otwórz stronę https://github.com",
         "expected_pattern": r"(xdg-open|open|playwright|firefox|chrome|chromium|sensible-browser).*github\.com",
         "description": "Open URL"},
        {"query": "wyszukaj w Google 'python tutorial'",
         "expected_pattern": r"(google\.com.*(search|q=)|xdg-open.*google|chrome.*google|firefox.*google)",
         "description": "Google search"},
    ],
    "git": [
        {"query": "pokaż historię ostatnich 10 commitów",
         "expected_pattern": r"git\s+log.*(-n\s*10|--oneline|-10|-\d+|head|pretty)", "description": "Git log"},
        {"query": "utwórz nowy branch o nazwie feature/login",
         "expected_pattern": r"git\s+(checkout\s+-b|branch|switch\s+-c).*feature.login", "description": "Create branch"},
        {"query": "dodaj wszystkie zmiany i zrób commit z wiadomością 'fix: napraw błąd'",
         "expected_pattern": r"git\s+(add.*commit|commit.*-a)", "description": "Add & commit"},
    ],
    # === 10 new domains ===
    "devops": [
        {"query": "sprawdź status usługi nginx",
         "expected_pattern": r"(systemctl\s+status|service\s+.*status).*nginx", "description": "Service status"},
        {"query": "uruchom playbook Ansible deploy.yml na serwerach web",
         "expected_pattern": r"ansible-playbook.*deploy\.yml", "description": "Ansible playbook"},
        {"query": "zainicjalizuj Terraform i zastosuj konfigurację",
         "expected_pattern": r"terraform\s+(init|apply)", "description": "Terraform init/apply"},
    ],
    "api": [
        {"query": "wyślij żądanie GET na https://api.example.com/users",
         "expected_pattern": r"curl.*https?://api\.example\.com/users", "description": "GET request"},
        {"query": "wyślij POST z JSON danymi na endpoint /api/login",
         "expected_pattern": r"curl.*-X\s*POST.*(-d|--data).*json", "description": "POST JSON"},
        {"query": "sprawdź kod odpowiedzi HTTP serwera https://example.com",
         "expected_pattern": r"curl.*(http_code|status|head|-I|-w)", "description": "HTTP status check"},
    ],
    "ffmpeg": [
        {"query": "konwertuj plik video.mp4 do formatu webm",
         "expected_pattern": r"ffmpeg.*-i.*(video\.mp4|input).*\.webm", "description": "Convert to webm"},
        {"query": "wyodrębnij audio z pliku film.mkv do mp3",
         "expected_pattern": r"ffmpeg.*-i.*(-vn|audio|mp3|libmp3lame)", "description": "Extract audio"},
        {"query": "zmniejsz rozdzielczość video do 720p",
         "expected_pattern": r"ffmpeg.*(-vf\s+scale|720|-1:720|resize)", "description": "Resize 720p"},
    ],
    "media": [
        {"query": "zmień rozmiar obrazu photo.jpg na 800x600",
         "expected_pattern": r"(convert|mogrify|ffmpeg).*(-resize|scale|800).*600", "description": "Resize image"},
        {"query": "konwertuj wszystkie pliki PNG na JPEG",
         "expected_pattern": r"(convert|mogrify|for).*png.*(jpg|jpeg)", "description": "Batch convert"},
        {"query": "utwórz miniaturkę 150x150 z obrazu header.png",
         "expected_pattern": r"(convert|mogrify).*(thumbnail|resize|150)", "description": "Thumbnail"},
    ],
    "data": [
        {"query": "pokaż statystyki pliku CSV dane.csv",
         "expected_pattern": r"(csvstat|csvlook|pandas|describe|head).*dane\.csv", "description": "CSV stats"},
        {"query": "przefiltruj plik JSON users.json po polu age większym niż 30",
         "expected_pattern": r"jq.*select.*age.*(>|gt).*30", "description": "jq filter"},
        {"query": "policz unikalne wartości w kolumnie status pliku log.csv",
         "expected_pattern": r"(awk|sort|uniq|csvkit|cut).*status", "description": "Unique count"},
    ],
    "remote": [
        {"query": "połącz się przez SSH do serwera 192.168.1.100 jako user admin",
         "expected_pattern": r"ssh\s+admin@192\.168\.1\.100", "description": "SSH connect"},
        {"query": "skopiuj plik backup.tar.gz na zdalny serwer do /tmp",
         "expected_pattern": r"(scp|rsync).*backup\.tar\.gz.*(/tmp|remote)", "description": "SCP upload"},
        {"query": "zsynchronizuj katalog /var/www na zdalny serwer",
         "expected_pattern": r"rsync.*(/var/www|www)", "description": "Rsync sync"},
    ],
    "iot": [
        {"query": "odczytaj temperaturę z Raspberry Pi",
         "expected_pattern": r"(vcgencmd\s+measure_temp|temp|sensors|DHT)", "description": "RPi temperature"},
        {"query": "wykryj urządzenia I2C na magistrali 1",
         "expected_pattern": r"i2cdetect.*(-y\s+)?1", "description": "I2C detect"},
        {"query": "wyślij wiadomość MQTT na temat sensors/temperature",
         "expected_pattern": r"mosquitto_pub.*(-t|topic).*sensor", "description": "MQTT publish"},
    ],
    "package_mgmt": [
        {"query": "zainstaluj pakiet nodejs przez apt",
         "expected_pattern": r"(sudo\s+)?apt(-get)?\s+install.*nodejs", "description": "apt install"},
        {"query": "zainstaluj bibliotekę requests przez pip",
         "expected_pattern": r"pip\s+install.*requests", "description": "pip install"},
        {"query": "pokaż zainstalowane pakiety npm globalnie",
         "expected_pattern": r"npm\s+(list|ls).*(-g|global)", "description": "npm list global"},
    ],
    "rag": [
        {"query": "wyszukaj w bazie wektorowej ChromaDB dokumenty o 'machine learning'",
         "expected_pattern": r"(chroma|chromadb|query|search).*machine.?learning", "description": "ChromaDB query"},
        {"query": "wygeneruj embeddingi tekstu przez Ollama",
         "expected_pattern": r"(ollama|curl).*(embed|api/embed)", "description": "Ollama embeddings"},
        {"query": "załaduj i poindeksuj dokumenty PDF z katalogu /docs",
         "expected_pattern": r"(pdf|PyPDF|langchain|llama.?index|load|read).*(/docs|docs)", "description": "Index PDFs"},
    ],
    "presentation": [
        {"query": "konwertuj plik README.md do PDF",
         "expected_pattern": r"(pandoc|wkhtmltopdf|weasyprint|md).*README.*pdf", "description": "MD to PDF"},
        {"query": "wygeneruj wykres słupkowy z danych CSV sales.csv",
         "expected_pattern": r"(matplotlib|plt|gnuplot|chart|plot|pandas).*sales", "description": "Bar chart from CSV"},
        {"query": "wyrenderuj diagram Mermaid do pliku PNG",
         "expected_pattern": r"(mmdc|mermaid).*png", "description": "Mermaid render"},
    ],
}

# System prompts per domain
SYSTEM_PROMPTS: dict[str, str] = {
    "shell": """Jesteś ekspertem od komend Linux/shell. Użytkownik opisuje zadanie, a ty generujesz odpowiednią komendę shell.
Odpowiedz TYLKO jedną komendą shell. Bez komentarzy, bez wyjaśnień.""",

    "docker": """Jesteś ekspertem Docker. Użytkownik opisuje zadanie, a ty generujesz odpowiednią komendę docker.
Odpowiedz TYLKO jedną komendą docker. Bez komentarzy, bez wyjaśnień.""",

    "sql": """Jesteś ekspertem SQL. Użytkownik opisuje zapytanie, a ty generujesz odpowiednie polecenie SQL.
Odpowiedz TYLKO jednym poleceniem SQL. Bez komentarzy, bez wyjaśnień.""",

    "kubernetes": """Jesteś ekspertem Kubernetes. Użytkownik opisuje zadanie, a ty generujesz odpowiednią komendę kubectl.
Odpowiedz TYLKO jedną komendą kubectl. Bez komentarzy, bez wyjaśnień.""",

    "browser": """Jesteś ekspertem od automatyzacji przeglądarki w Linux. Użytkownik opisuje co chce otworzyć/zrobić, a ty generujesz odpowiednią komendę.
Odpowiedz TYLKO jedną komendą shell do otwarcia/przeszukania strony. Bez komentarzy, bez wyjaśnień.""",

    "git": """Jesteś ekspertem Git. Użytkownik opisuje zadanie, a ty generujesz odpowiednią komendę git.
Odpowiedz TYLKO jedną komendą git (lub potok komend). Bez komentarzy, bez wyjaśnień.""",

    "devops": """Jesteś ekspertem DevOps (systemctl, Ansible, Terraform, CI/CD). Generuj komendy systemctl, ansible-playbook, terraform itp.
Odpowiedz TYLKO jedną komendą. Bez komentarzy, bez wyjaśnień.""",

    "api": """Jesteś ekspertem od wywołań API (curl, httpie, wget). Użytkownik opisuje zapytanie HTTP, a ty generujesz komendę curl.
Odpowiedz TYLKO jedną komendą curl/wget/http. Bez komentarzy, bez wyjaśnień.""",

    "ffmpeg": """Jesteś ekspertem od FFmpeg. Użytkownik opisuje operację na video/audio, a ty generujesz komendę ffmpeg.
Odpowiedz TYLKO jedną komendą ffmpeg/ffprobe. Bez komentarzy, bez wyjaśnień.""",

    "media": """Jesteś ekspertem od przetwarzania obrazów (ImageMagick, sox). Użytkownik opisuje operację na obrazie/audio.
Odpowiedz TYLKO jedną komendą convert/mogrify/sox. Bez komentarzy, bez wyjaśnień.""",

    "data": """Jesteś ekspertem od przetwarzania danych (jq, csvkit, awk, sed, sort, sqlite). Użytkownik opisuje operację na danych.
Odpowiedz TYLKO jedną komendą/potokiem komend. Bez komentarzy, bez wyjaśnień.""",

    "remote": """Jesteś ekspertem od zdalnego zarządzania (SSH, SCP, rsync, tmux). Użytkownik opisuje zadanie zdalne.
Odpowiedz TYLKO jedną komendą ssh/scp/rsync. Bez komentarzy, bez wyjaśnień.""",

    "iot": """Jesteś ekspertem od IoT i Raspberry Pi (GPIO, I2C, MQTT, czujniki, kamery). Użytkownik opisuje zadanie IoT/embedded.
Odpowiedz TYLKO jedną komendą shell/python. Bez komentarzy, bez wyjaśnień.""",

    "package_mgmt": """Jesteś ekspertem od zarządzania pakietami (apt, pip, npm, yarn, snap, flatpak, brew, cargo).
Użytkownik opisuje co chce zainstalować/usunąć/zaktualizować, a ty generujesz odpowiednią komendę.
Odpowiedz TYLKO jedną komendą. Bez komentarzy, bez wyjaśnień.""",

    "rag": """Jesteś ekspertem od RAG (Retrieval-Augmented Generation), wektorowych baz danych (ChromaDB, Qdrant), embeddingów i pipeline'ów LLM.
Użytkownik opisuje zadanie RAG/embeddingów, a ty generujesz odpowiednią komendę (curl, python, ollama).
Odpowiedz TYLKO jedną komendą. Bez komentarzy, bez wyjaśnień.""",

    "presentation": """Jesteś ekspertem od generowania prezentacji, raportów i wizualizacji (pandoc, matplotlib, gnuplot, mermaid, LaTeX, Jupyter).
Użytkownik opisuje co chce wygenerować, a ty generujesz odpowiednią komendę.
Odpowiedz TYLKO jedną komendą. Bez komentarzy, bez wyjaśnień.""",
}

# ---------------------------------------------------------------------------
# Models config
# ---------------------------------------------------------------------------
MODELS = [
    {"name": "bielik-1.5b", "display": "Bielik-1.5B (PL)", "params": "1.5B"},
    {"name": "qwen2.5:3b", "display": "Qwen2.5-3B", "params": "3B"},
    {"name": "gemma2:2b", "display": "Gemma2-2B", "params": "2B"},
    {"name": "phi:latest", "display": "Phi (latest)", "params": "1.6GB"},
    {"name": "deepseek-r1:1.5b", "display": "DeepSeek-R1-1.5B", "params": "1.1GB"},
]


# ---------------------------------------------------------------------------
# Result data classes
# ---------------------------------------------------------------------------
@dataclass
class QueryResult:
    model: str
    domain: str
    query: str
    description: str
    raw_response: str
    cleaned_command: str
    expected_pattern: str
    pattern_match: bool
    response_time_sec: float
    error: Optional[str] = None


@dataclass
class BenchmarkResults:
    timestamp: str
    models: list[dict[str, str]]
    domains: list[str]
    total_queries: int
    results: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Cleaning helper
# ---------------------------------------------------------------------------
def clean_command(raw: str) -> str:
    """Extract clean command from LLM response."""
    text = raw.strip()

    # Remove markdown code blocks
    m = re.search(r"```(?:bash|shell|sql|sh)?\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()

    # Remove leading explanation lines (keep only command-looking lines)
    lines = text.split("\n")
    cmd_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith("//"):
            continue
        # Skip lines that look like natural language (long sentences)
        if len(line) > 120 and not any(c in line for c in ["|", "&&", ";", ">"]):
            continue
        cmd_lines.append(line)

    return " ".join(cmd_lines) if cmd_lines else text


# ---------------------------------------------------------------------------
# Main benchmark runner
# ---------------------------------------------------------------------------
def run_benchmark() -> BenchmarkResults:
    log.info("=" * 70)
    log.info("NLP2CMD LLM Benchmark")
    log.info("=" * 70)

    # Check ollama
    if not ollama_available():
        log.error("Ollama is not running at %s", OLLAMA_BASE)
        sys.exit(1)
    log.info("✅ Ollama available at %s", OLLAMA_BASE)

    # Ensure bielik-1.5b exists in ollama
    if not ollama_model_exists("bielik-1.5b"):
        log.info("Bielik-1.5b not found in ollama — creating from GGUF …")
        if not ollama_create_bielik():
            log.warning("⚠️  Skipping Bielik-1.5B (GGUF not available)")
            MODELS[:] = [m for m in MODELS if m["name"] != "bielik-1.5b"]

    # Verify other models
    for model_cfg in MODELS[:]:
        if not ollama_model_exists(model_cfg["name"]):
            log.warning("Model %s not in ollama — trying pull …", model_cfg["name"])
            try:
                subprocess.run(
                    ["ollama", "pull", model_cfg["name"]],
                    check=True, capture_output=True, text=True, timeout=300,
                )
                log.info("✅ Pulled %s", model_cfg["name"])
            except Exception as exc:
                log.error("Cannot get model %s: %s — skipping", model_cfg["name"], exc)
                MODELS[:] = [m for m in MODELS if m["name"] != model_cfg["name"]]

    if not MODELS:
        log.error("No models available — aborting")
        sys.exit(1)

    log.info("Models to benchmark: %s", [m["display"] for m in MODELS])
    log.info("Domains: %s", list(BENCHMARK_QUERIES.keys()))

    total_queries = sum(len(qs) for qs in BENCHMARK_QUERIES.values()) * len(MODELS)
    log.info("Total queries: %d", total_queries)

    results = BenchmarkResults(
        timestamp=datetime.now().isoformat(),
        models=[dict(m) for m in MODELS],
        domains=list(BENCHMARK_QUERIES.keys()),
        total_queries=total_queries,
    )

    query_num = 0
    for model_cfg in MODELS:
        model_name = model_cfg["name"]
        log.info("-" * 60)
        log.info("🤖 Model: %s (%s)", model_cfg["display"], model_cfg["params"])
        log.info("-" * 60)

        # Warm up model
        log.info("  Warming up %s …", model_name)
        try:
            ollama_generate(model_name, "hello", max_tokens=5)
        except Exception as exc:
            log.error("  Warmup failed: %s — skipping model", exc)
            continue

        for domain, queries in BENCHMARK_QUERIES.items():
            system_prompt = SYSTEM_PROMPTS.get(domain, "")
            log.info("  📂 Domain: %s (%d queries)", domain, len(queries))

            for q in queries:
                query_num += 1
                log.info(
                    "    [%d/%d] %s: %s",
                    query_num, total_queries, domain, q["query"][:60],
                )

                qr = QueryResult(
                    model=model_name,
                    domain=domain,
                    query=q["query"],
                    description=q["description"],
                    raw_response="",
                    cleaned_command="",
                    expected_pattern=q["expected_pattern"],
                    pattern_match=False,
                    response_time_sec=0.0,
                )

                try:
                    raw, elapsed = ollama_generate(
                        model_name, q["query"], system=system_prompt, max_tokens=200
                    )
                    qr.raw_response = raw
                    qr.cleaned_command = clean_command(raw)
                    qr.response_time_sec = round(elapsed, 3)

                    # Check pattern match
                    qr.pattern_match = bool(
                        re.search(q["expected_pattern"], qr.cleaned_command, re.IGNORECASE)
                    )

                    status = "✅" if qr.pattern_match else "⚠️"
                    log.info(
                        "      %s %.2fs | %s",
                        status, elapsed, qr.cleaned_command[:70],
                    )

                except Exception as exc:
                    qr.error = str(exc)
                    qr.response_time_sec = 0.0
                    log.error("      ❌ Error: %s", exc)

                results.results.append(asdict(qr))

    # Build summary
    results.summary = build_summary(results)
    return results


def build_summary(results: BenchmarkResults) -> dict[str, Any]:
    """Aggregate per-model and per-domain stats."""
    summary: dict[str, Any] = {"models": {}, "domains": {}, "overall": {}}

    for model_cfg in results.models:
        mname = model_cfg["name"]
        model_results = [r for r in results.results if r["model"] == mname]
        if not model_results:
            continue
        total = len(model_results)
        matched = sum(1 for r in model_results if r["pattern_match"])
        errors = sum(1 for r in model_results if r.get("error"))
        times = [r["response_time_sec"] for r in model_results if not r.get("error")]
        avg_time = round(sum(times) / len(times), 3) if times else 0

        summary["models"][mname] = {
            "display": model_cfg["display"],
            "params": model_cfg["params"],
            "total": total,
            "matched": matched,
            "accuracy_pct": round(matched / total * 100, 1) if total else 0,
            "errors": errors,
            "avg_response_sec": avg_time,
            "min_response_sec": round(min(times), 3) if times else 0,
            "max_response_sec": round(max(times), 3) if times else 0,
        }

    for domain in results.domains:
        domain_results = [r for r in results.results if r["domain"] == domain]
        if not domain_results:
            continue
        total = len(domain_results)
        matched = sum(1 for r in domain_results if r["pattern_match"])
        times = [r["response_time_sec"] for r in domain_results if not r.get("error")]

        per_model: dict[str, dict[str, Any]] = {}
        for model_cfg in results.models:
            mname = model_cfg["name"]
            mr = [r for r in domain_results if r["model"] == mname]
            if mr:
                m_matched = sum(1 for r in mr if r["pattern_match"])
                m_times = [r["response_time_sec"] for r in mr if not r.get("error")]
                per_model[mname] = {
                    "matched": m_matched,
                    "total": len(mr),
                    "accuracy_pct": round(m_matched / len(mr) * 100, 1),
                    "avg_time": round(sum(m_times) / len(m_times), 3) if m_times else 0,
                }

        summary["domains"][domain] = {
            "total": total,
            "matched": matched,
            "accuracy_pct": round(matched / total * 100, 1) if total else 0,
            "avg_response_sec": round(sum(times) / len(times), 3) if times else 0,
            "per_model": per_model,
        }

    all_results = results.results
    total = len(all_results)
    matched = sum(1 for r in all_results if r["pattern_match"])
    times = [r["response_time_sec"] for r in all_results if not r.get("error")]
    summary["overall"] = {
        "total_queries": total,
        "total_matched": matched,
        "accuracy_pct": round(matched / total * 100, 1) if total else 0,
        "avg_response_sec": round(sum(times) / len(times), 3) if times else 0,
        "total_time_sec": round(sum(times), 1) if times else 0,
    }

    return summary


# ---------------------------------------------------------------------------
# HTML report generator
# ---------------------------------------------------------------------------
def generate_html(results: BenchmarkResults) -> str:
    """Generate interactive HTML with Chart.js visualisations."""
    summary = results.summary
    models_json = json.dumps(summary.get("models", {}), indent=2, ensure_ascii=False)
    domains_json = json.dumps(summary.get("domains", {}), indent=2, ensure_ascii=False)
    all_results_json = json.dumps(results.results, indent=2, ensure_ascii=False)
    overall_json = json.dumps(summary.get("overall", {}), indent=2, ensure_ascii=False)

    # Prepare chart data
    model_names = []
    model_accuracy = []
    model_avg_time = []
    model_colors = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f"]

    for i, mcfg in enumerate(results.models):
        mdata = summary.get("models", {}).get(mcfg["name"], {})
        model_names.append(mcfg["display"])
        model_accuracy.append(mdata.get("accuracy_pct", 0))
        model_avg_time.append(mdata.get("avg_response_sec", 0))

    domain_names = list(summary.get("domains", {}).keys())
    # Per-model accuracy per domain
    domain_datasets = []
    for i, mcfg in enumerate(results.models):
        data = []
        for d in domain_names:
            dinfo = summary.get("domains", {}).get(d, {}).get("per_model", {}).get(mcfg["name"], {})
            data.append(dinfo.get("accuracy_pct", 0))
        domain_datasets.append({
            "label": mcfg["display"],
            "data": data,
            "backgroundColor": model_colors[i % len(model_colors)],
        })

    # Per-model time per domain
    time_datasets = []
    for i, mcfg in enumerate(results.models):
        data = []
        for d in domain_names:
            dinfo = summary.get("domains", {}).get(d, {}).get("per_model", {}).get(mcfg["name"], {})
            data.append(dinfo.get("avg_time", 0))
        time_datasets.append({
            "label": mcfg["display"],
            "data": data,
            "backgroundColor": model_colors[i % len(model_colors)],
        })

    html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NLP2CMD Benchmark — 5 LLMs ≤3B</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; line-height: 1.6; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem; }}
  h1 {{ font-size: 2rem; color: #38bdf8; margin-bottom: 0.5rem; }}
  h2 {{ font-size: 1.4rem; color: #7dd3fc; margin: 2rem 0 1rem; border-bottom: 1px solid #334155; padding-bottom: 0.5rem; }}
  .subtitle {{ color: #94a3b8; margin-bottom: 2rem; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
  .card {{ background: #1e293b; border-radius: 12px; padding: 1.5rem; border: 1px solid #334155; }}
  .card .label {{ color: #94a3b8; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }}
  .card .value {{ font-size: 2rem; font-weight: 700; color: #38bdf8; margin: 0.25rem 0; }}
  .card .detail {{ color: #64748b; font-size: 0.85rem; }}
  .chart-container {{ background: #1e293b; border-radius: 12px; padding: 1.5rem; border: 1px solid #334155; margin-bottom: 1.5rem; }}
  .chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }}
  @media (max-width: 768px) {{ .chart-row {{ grid-template-columns: 1fr; }} }}
  canvas {{ max-height: 350px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
  th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #334155; }}
  th {{ color: #94a3b8; font-weight: 600; font-size: 0.85rem; text-transform: uppercase; }}
  td {{ font-size: 0.9rem; }}
  .badge {{ display: inline-block; padding: 0.15rem 0.5rem; border-radius: 6px; font-size: 0.8rem; font-weight: 600; }}
  .badge-ok {{ background: #065f46; color: #6ee7b7; }}
  .badge-fail {{ background: #7f1d1d; color: #fca5a5; }}
  .cmd {{ font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #a5f3fc; background: #0f172a; padding: 0.25rem 0.5rem; border-radius: 4px; word-break: break-all; }}
  .footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #334155; color: #64748b; font-size: 0.8rem; text-align: center; }}
  details {{ margin-top: 1rem; }}
  summary {{ cursor: pointer; color: #7dd3fc; font-weight: 600; }}
  pre {{ background: #0f172a; padding: 1rem; border-radius: 8px; overflow-x: auto; font-size: 0.8rem; margin-top: 0.5rem; }}
</style>
</head>
<body>
<div class="container">
  <h1>🧪 NLP2CMD LLM Benchmark</h1>
  <p class="subtitle">5 lokalne modele ≤3B • 6 domen nlp2cmd • {summary.get('overall',{}).get('total_queries',0)} zapytań • {results.timestamp[:19]}</p>

  <!-- Summary cards -->
  <div class="cards">
    <div class="card">
      <div class="label">Łącznie zapytań</div>
      <div class="value">{summary.get('overall',{}).get('total_queries',0)}</div>
      <div class="detail">{len(results.models)} modele × {len(domain_names)} domen</div>
    </div>
    <div class="card">
      <div class="label">Trafność ogólna</div>
      <div class="value">{summary.get('overall',{}).get('accuracy_pct',0)}%</div>
      <div class="detail">{summary.get('overall',{}).get('total_matched',0)} / {summary.get('overall',{}).get('total_queries',0)} trafień wzorca</div>
    </div>
    <div class="card">
      <div class="label">Średni czas odpowiedzi</div>
      <div class="value">{summary.get('overall',{}).get('avg_response_sec',0)}s</div>
      <div class="detail">Łączny czas: {summary.get('overall',{}).get('total_time_sec',0)}s</div>
    </div>
  </div>

  <!-- Model comparison cards -->
  <h2>📊 Porównanie modeli</h2>
  <div class="cards">
"""
    for mcfg in results.models:
        mdata = summary.get("models", {}).get(mcfg["name"], {})
        html += f"""    <div class="card">
      <div class="label">{mcfg['display']} ({mcfg['params']})</div>
      <div class="value">{mdata.get('accuracy_pct', 0)}%</div>
      <div class="detail">Śr. czas: {mdata.get('avg_response_sec', 0)}s · Min: {mdata.get('min_response_sec', 0)}s · Max: {mdata.get('max_response_sec', 0)}s</div>
    </div>
"""

    html += f"""  </div>

  <!-- Charts -->
  <div class="chart-row">
    <div class="chart-container">
      <h2 style="margin-top:0">🎯 Trafność wg modelu</h2>
      <canvas id="chartAccuracy"></canvas>
    </div>
    <div class="chart-container">
      <h2 style="margin-top:0">⏱ Średni czas odpowiedzi</h2>
      <canvas id="chartTime"></canvas>
    </div>
  </div>

  <div class="chart-row">
    <div class="chart-container">
      <h2 style="margin-top:0">📂 Trafność wg domeny</h2>
      <canvas id="chartDomainAccuracy"></canvas>
    </div>
    <div class="chart-container">
      <h2 style="margin-top:0">📂 Czas wg domeny</h2>
      <canvas id="chartDomainTime"></canvas>
    </div>
  </div>

  <!-- Detailed results table -->
  <h2>📋 Szczegółowe wyniki</h2>
  <div style="overflow-x:auto">
  <table>
    <thead>
      <tr><th>Model</th><th>Domena</th><th>Zapytanie</th><th>Komenda</th><th>Trafność</th><th>Czas (s)</th></tr>
    </thead>
    <tbody>
"""
    for r in results.results:
        badge = '<span class="badge badge-ok">✅ TAK</span>' if r["pattern_match"] else '<span class="badge badge-fail">❌ NIE</span>'
        cmd_display = r["cleaned_command"][:80] + ("…" if len(r["cleaned_command"]) > 80 else "")
        model_display = next((m["display"] for m in results.models if m["name"] == r["model"]), r["model"])
        html += f'      <tr><td>{model_display}</td><td>{r["domain"]}</td><td>{r["query"][:50]}</td><td><span class="cmd">{cmd_display}</span></td><td>{badge}</td><td>{r["response_time_sec"]}</td></tr>\n'

    html += f"""    </tbody>
  </table>
  </div>

  <!-- Raw JSON -->
  <details>
    <summary>📄 Surowe dane JSON (kliknij aby rozwinąć)</summary>
    <pre>{json.dumps({"summary": results.summary, "results_count": len(results.results)}, indent=2, ensure_ascii=False)}</pre>
  </details>

  <div class="footer">
    NLP2CMD Benchmark · wygenerowany {results.timestamp[:19]} · Python {sys.version.split()[0]}
  </div>
</div>

<script>
const chartColors = {json.dumps(model_colors)};

// 1. Model accuracy bar chart
new Chart(document.getElementById('chartAccuracy'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(model_names)},
    datasets: [{{
      label: 'Trafność (%)',
      data: {json.dumps(model_accuracy)},
      backgroundColor: chartColors,
      borderRadius: 6,
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      y: {{ beginAtZero: true, max: 100, ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#334155' }} }},
      x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ display: false }} }}
    }}
  }}
}});

// 2. Model avg response time
new Chart(document.getElementById('chartTime'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(model_names)},
    datasets: [{{
      label: 'Czas (s)',
      data: {json.dumps(model_avg_time)},
      backgroundColor: chartColors,
      borderRadius: 6,
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      y: {{ beginAtZero: true, ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#334155' }} }},
      x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ display: false }} }}
    }}
  }}
}});

// 3. Domain accuracy grouped bar
new Chart(document.getElementById('chartDomainAccuracy'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(domain_names)},
    datasets: {json.dumps(domain_datasets)}
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }},
    scales: {{
      y: {{ beginAtZero: true, max: 100, ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#334155' }} }},
      x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ display: false }} }}
    }}
  }}
}});

// 4. Domain time grouped bar
new Chart(document.getElementById('chartDomainTime'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(domain_names)},
    datasets: {json.dumps(time_datasets)}
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }},
    scales: {{
      y: {{ beginAtZero: true, ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#334155' }} }},
      x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ display: false }} }}
    }}
  }}
}});
</script>
</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# CLI summary printer
# ---------------------------------------------------------------------------
def print_summary(results: BenchmarkResults) -> None:
    s = results.summary
    overall = s.get("overall", {})
    print()
    print("=" * 60)
    print("📊 NLP2CMD BENCHMARK — PODSUMOWANIE")
    print("=" * 60)
    print(f"  Łącznie zapytań:       {overall.get('total_queries', 0)}")
    print(f"  Trafność ogólna:       {overall.get('accuracy_pct', 0)}%")
    print(f"  Średni czas odp.:      {overall.get('avg_response_sec', 0)}s")
    print(f"  Łączny czas:           {overall.get('total_time_sec', 0)}s")
    print()

    print("  Model                  Trafność    Śr. czas")
    print("  " + "-" * 50)
    for mcfg in results.models:
        mdata = s.get("models", {}).get(mcfg["name"], {})
        print(
            f"  {mcfg['display']:<22} {mdata.get('accuracy_pct',0):>6.1f}%    {mdata.get('avg_response_sec',0):>6.3f}s"
        )
    print()

    print("  Domena        Trafność    Śr. czas")
    print("  " + "-" * 40)
    for d, ddata in s.get("domains", {}).items():
        print(f"  {d:<14} {ddata.get('accuracy_pct',0):>6.1f}%    {ddata.get('avg_response_sec',0):>6.3f}s")
    print()

    print(f"  Wyniki JSON:  {RESULTS_JSON}")
    print(f"  Raport HTML:  {RESULTS_HTML}")
    print(f"  Log:          {LOG_FILE}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Refactoring plan generator
# ---------------------------------------------------------------------------
def generate_refactoring_notes(results: BenchmarkResults) -> str:
    """Generate refactoring recommendations based on benchmark data."""
    s = results.summary
    lines = [
        "# NLP2CMD Refactoring Plan — based on benchmark results",
        f"# Generated: {results.timestamp}",
        "",
    ]

    # Identify weak domains
    weak_domains = []
    strong_domains = []
    for d, ddata in s.get("domains", {}).items():
        if ddata.get("accuracy_pct", 0) < 50:
            weak_domains.append((d, ddata))
        else:
            strong_domains.append((d, ddata))

    lines.append("## Domain Analysis")
    if weak_domains:
        lines.append("### Weak domains (accuracy < 50%) — priority for refactoring:")
        for d, ddata in weak_domains:
            lines.append(f"  - **{d}**: {ddata['accuracy_pct']}% accuracy, {ddata['avg_response_sec']}s avg time")
            lines.append(f"    → Improve system prompts, add few-shot examples, better entity extraction")
    if strong_domains:
        lines.append("### Strong domains:")
        for d, ddata in strong_domains:
            lines.append(f"  - **{d}**: {ddata['accuracy_pct']}% accuracy, {ddata['avg_response_sec']}s avg time")

    lines.append("")
    lines.append("## Model Analysis")
    for mcfg in results.models:
        mdata = s.get("models", {}).get(mcfg["name"], {})
        lines.append(f"### {mcfg['display']} ({mcfg['params']})")
        lines.append(f"  - Accuracy: {mdata.get('accuracy_pct', 0)}%")
        lines.append(f"  - Avg time: {mdata.get('avg_response_sec', 0)}s")
        lines.append(f"  - Errors: {mdata.get('errors', 0)}")

    lines.append("")
    lines.append("## Recommendations")
    lines.append("1. **System prompts**: Optimize per-domain prompts based on failure patterns")
    lines.append("2. **Few-shot examples**: Add domain-specific examples to prompts (especially weak domains)")
    lines.append("3. **Entity extraction**: Improve regex patterns for domains with low accuracy")
    lines.append("4. **Fallback chain**: template → regex → LLM (use fastest method first)")
    lines.append("5. **Caching**: Cache common queries to reduce LLM calls")
    lines.append("6. **Polish language**: Add more Polish-specific patterns and keywords")

    # Per-query failure analysis
    lines.append("")
    lines.append("## Failed Queries (for targeted improvements)")
    for r in results.results:
        if not r["pattern_match"]:
            lines.append(f"  - [{r['domain']}] {r['model']}: \"{r['query'][:60]}\"")
            lines.append(f"    Got: {r['cleaned_command'][:80]}")
            lines.append(f"    Expected pattern: {r['expected_pattern']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    log.info("Starting NLP2CMD benchmark …")
    results = run_benchmark()

    # Save JSON
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(
            {"summary": results.summary, "results": results.results,
             "models": [dict(m) for m in results.models], "timestamp": results.timestamp},
            f, indent=2, ensure_ascii=False,
        )
    log.info("JSON saved: %s", RESULTS_JSON)

    # Save HTML
    html = generate_html(results)
    with open(RESULTS_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    log.info("HTML saved: %s", RESULTS_HTML)

    # Save refactoring notes
    refactoring_path = RESULTS_DIR / "refactoring_plan.md"
    refactoring_notes = generate_refactoring_notes(results)
    with open(refactoring_path, "w", encoding="utf-8") as f:
        f.write(refactoring_notes)
    log.info("Refactoring plan saved: %s", refactoring_path)

    # Print summary
    print_summary(results)


if __name__ == "__main__":
    main()
