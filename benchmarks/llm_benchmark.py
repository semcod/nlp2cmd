#!/usr/bin/env python3
"""
NLP2CMD LLM Benchmark — 4 local models (≤3B) across all 6 nlp2cmd domains.

Models tested:
  1. Bielik-1.5B  (Polish, via ollama from GGUF)
  2. qwen2.5:3b   (multilingual 3B)
  3. gemma2:2b     (Google 2B)
  4. deepseek-coder:1.3b (DeepSeek Coder)

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

import argparse
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
ERRORS_MD = RESULTS_DIR / "benchmark_command_errors.md"

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
# Use LITELLM_API_BASE as primary, fallback to OLLAMA_BASE_URL for compatibility
OLLAMA_BASE = os.environ.get("LITELLM_API_BASE") or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


OLLAMA_TIMEOUT = int(os.environ.get("NLP2CMD_OLLAMA_TIMEOUT", "5"))
OLLAMA_GENERATE_TIMEOUT = int(os.environ.get("NLP2CMD_OLLAMA_GENERATE_TIMEOUT", "120"))
OLLAMA_PULL_TIMEOUT = int(os.environ.get("NLP2CMD_OLLAMA_PULL_TIMEOUT", "300"))
OLLAMA_CREATE_TIMEOUT = int(os.environ.get("NLP2CMD_OLLAMA_CREATE_TIMEOUT", "120"))


def ollama_available() -> bool:
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=OLLAMA_TIMEOUT)
        return r.status_code == 200
    except Exception:
        return False


def ollama_model_exists(name: str) -> bool:
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=OLLAMA_TIMEOUT)
        models = [m["name"] for m in r.json().get("models", [])]
        # match both "name" and "name:latest"
        return any(name in m for m in models)
    except Exception:
        return False


def ollama_create_bielik() -> bool:
    """Create ollama model from local Bielik GGUF if not already present."""
    default_gguf_path = Path.home() / ".cache" / "bielik" / "bielik-1.5b.gguf"
    gguf_path = Path(os.environ.get("NLP2CMD_BIELIK_GGUF_PATH", default_gguf_path)).expanduser()
    if not gguf_path.exists():
        log.warning("Bielik GGUF not found at %s — skipping", gguf_path)
        return False

    bielik_temp = float(os.environ.get("NLP2CMD_BIELIK_TEMPERATURE", "0.2"))
    bielik_ctx = int(os.environ.get("NLP2CMD_BIELIK_NUM_CTX", "2048"))

    modelfile_content = f"""FROM {gguf_path}
PARAMETER temperature {bielik_temp}
PARAMETER num_ctx {bielik_ctx}
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
            timeout=OLLAMA_CREATE_TIMEOUT,
        )
        log.info("✅ bielik-1.5b created in ollama")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        log.error("Failed to create bielik-1.5b: %s", exc)
        return False


def ollama_generate(
    model: str, prompt: str, system: str = "",
    max_tokens: int = 200, thinking: bool = False,
) -> tuple[str, float]:
    """Call ollama /api/generate, return (text, duration_sec)."""
    # Thinking models (DeepSeek-R1) emit <think>...</think> blocks before the
    # actual command.  We must NOT use \n\n as a stop token for them because
    # the reasoning section contains many double-newlines.
    if thinking:
        stop = ["</assistant>", "<user>"]
    else:
        stop = ["\n\n", "```", "</assistant>", "<user>"]

    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": max_tokens,
            "stop": stop,
        },
    }
    if system:
        payload["system"] = system

    t0 = time.perf_counter()
    r = requests.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=OLLAMA_GENERATE_TIMEOUT)
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
        {"query": "wyszukaj pliki DOCX większe niż 5MB w katalogu /home",
         "expected_pattern": r"find.*\.docx.*-size", "description": "Find large DOCX files"},
        {"query": "sprawdź zajętość dysku w /tmp",
         "expected_pattern": r"(du|df).*(/tmp|tmp)", "description": "Disk usage /tmp"},
        {"query": "wyświetl 15 procesów zużywających najwięcej CPU",
         "expected_pattern": r"(ps.*sort|top|ps.*cpu)", "description": "Top CPU processes"},
    ],
    "docker": [
        {"query": "wyświetl wszystkie zatrzymane kontenery",
         "expected_pattern": r"docker\s+(ps|container\s+ls)", "description": "List containers"},
        {"query": "zbuduj obraz z tagiem webapp:v2.0",
         "expected_pattern": r"docker\s+build.*-t.*webapp", "description": "Build image"},
        {"query": "pokaż ostatnie 50 linii logów kontenera redis",
         "expected_pattern": r"docker\s+logs.*(redis|--tail|50)", "description": "Container logs"},
    ],
    "sql": [
        {"query": "wybierz klientów z Krakowa",
         "expected_pattern": r"SELECT.*FROM.*WHERE.*(Krak|city|miasto)", "description": "Select WHERE"},
        {"query": "policz sprzedaż pogrupowaną po tygodniu",
         "expected_pattern": r"(SELECT.*COUNT|GROUP\s+BY|count)", "description": "Count GROUP BY"},
        {"query": "stwórz tabelę klienci z polami id, email, telefon",
         "expected_pattern": r"CREATE\s+TABLE.*klient", "description": "CREATE TABLE"},
    ],
    "kubernetes": [
        {"query": "wyświetl pody w namespace staging",
         "expected_pattern": r"kubectl\s+get\s+pods.*(-n|namespace).*stag", "description": "Get pods ns"},
        {"query": "skaluj deployment api-server do 3 replik",
         "expected_pattern": r"kubectl\s+scale.*replicas.*3", "description": "Scale deployment"},
        {"query": "pokaż logi poda postgres-xyz789",
         "expected_pattern": r"kubectl\s+logs.*postgres", "description": "Pod logs"},
    ],
    "browser": [
        {"query": "otwórz stronę https://stackoverflow.com",
         "expected_pattern": r"(xdg-open|open|playwright|firefox|chrome|chromium|sensible-browser).*stackoverflow\.com",
         "description": "Open URL"},
        {"query": "wyszukaj w Google 'rust programming'",
         "expected_pattern": r"(google\.com/search\?q=|xdg-open.*google\.com/search\?q=|chrome.*google\.com/search\?q=|firefox.*google\.com/search\?q=)",
         "description": "Google search"},
    ],
    "git": [
        {"query": "wyświetl ostatnie 20 commitów",
         "expected_pattern": r"git\s+log.*(-n\s*20|--oneline|-20|-\d+|head|pretty)", "description": "Git log"},
        {"query": "stwórz branch bugfix/auth-error",
         "expected_pattern": r"git\s+(checkout\s+-b|branch|switch\s+-c).*bugfix.auth", "description": "Create branch"},
        {"query": "dodaj wszystko i commituj z opisem 'feat: dodaj API'",
         "expected_pattern": r"git\s+(add.*commit|commit.*-a)", "description": "Add & commit"},
    ],
    # === 10 new domains ===
    "devops": [
        {"query": "sprawdź czy działa usługa postgresql",
         "expected_pattern": r"(systemctl\s+status|service\s+.*status).*postgres", "description": "Service status"},
        {"query": "uruchom playbook setup.yml",
         "expected_pattern": r"ansible-playbook.*setup\.yml", "description": "Ansible playbook"},
        {"query": "zaplanuj zmiany w Terraform",
         "expected_pattern": r"terraform\s+(plan|init)", "description": "Terraform plan"},
    ],
    "api": [
        {"query": "wyślij GET do https://api.github.com/repos",
         "expected_pattern": r"curl.*https?://api\.github\.com/repos", "description": "GET request"},
        {"query": "wyślij POST z danymi JSON na /api/register",
         "expected_pattern": r"curl.*-X\s*POST.*(Content-Type:.*json|application/json).*(-d|--data)", "description": "POST JSON"},
        {"query": "sprawdź status HTTP strony https://google.com",
         "expected_pattern": r"curl.*(http_code|status|head|-I|-w)", "description": "HTTP status check"},
    ],
    "ffmpeg": [
        {"query": "przekonwertuj movie.avi na format mp4",
         "expected_pattern": r"ffmpeg.*-i.*(movie\.avi|input).*\.mp4", "description": "Convert to mp4"},
        {"query": "wyciągnij ścieżkę audio z recording.mkv do wav",
         "expected_pattern": r"ffmpeg.*-i.*(-vn|audio|wav)", "description": "Extract audio"},
        {"query": "zmień rozdzielczość na 1080p",
         "expected_pattern": r"ffmpeg.*(-vf\s+scale|1080|-1:1080|resize)", "description": "Resize 1080p"},
    ],
    "media": [
        {"query": "przeskaluj image.png do 1024x768",
         "expected_pattern": r"(convert|mogrify|ffmpeg).*(-resize|scale|1024).*768", "description": "Resize image"},
        {"query": "zamień wszystkie JPEG na PNG",
         "expected_pattern": r"(convert|mogrify|for).*(png|jpg|jpeg)", "description": "Batch convert"},
        {"query": "stwórz miniaturę 200x200 z logo.jpg",
         "expected_pattern": r"(convert|mogrify).*(thumbnail|resize|200)", "description": "Thumbnail"},
    ],
    "data": [
        {"query": "wyświetl statystyki pliku sales.csv",
         "expected_pattern": r"(csvstat|csvlook|pandas|describe|head).*sales\.csv", "description": "CSV stats"},
        {"query": "filtruj customers.json po salary powyżej 5000",
         "expected_pattern": r"jq.*select.*salary.*(>|gt).*5000", "description": "jq filter"},
        {"query": "policz unikalne wartości w kolumnie type z events.csv",
         "expected_pattern": r"((cut.*(type|\-f\s*2|\-f2).*events\.csv)|(awk.*type.*events\.csv)).*(sort|uniq)", "description": "Unique count"},
    ],
    "remote": [
        {"query": "zaloguj się przez SSH na 10.0.0.50 jako root",
         "expected_pattern": r"ssh\s+root@10\.0\.0\.50", "description": "SSH connect"},
        {"query": "prześlij archive.zip na serwer do /home/user",
         "expected_pattern": r"(scp|rsync).*archive\.zip.*(/home|user)", "description": "SCP upload"},
        {"query": "synchronizuj /opt/app na zdalną maszynę",
         "expected_pattern": r"rsync.*(/opt/app|opt|app)", "description": "Rsync sync"},
    ],
    "iot": [
        {"query": "sprawdź temperaturę procesora Raspberry Pi",
         "expected_pattern": r"(vcgencmd\s+measure_temp|temp|sensors|cpu)", "description": "RPi temperature"},
        {"query": "skanuj urządzenia I2C na szynie 0",
         "expected_pattern": r"i2cdetect.*(-y\s+)?0", "description": "I2C detect"},
        {"query": "opublikuj MQTT na topic home/humidity",
         "expected_pattern": r"mosquitto_pub.*(-t|topic).*(home|humidity)", "description": "MQTT publish"},
    ],
    "package_mgmt": [
        {"query": "zainstaluj python3-pip przez apt",
         "expected_pattern": r"(sudo\s+)?apt(-get)?\s+install.*python3-pip", "description": "apt install"},
        {"query": "zainstaluj numpy przez pip",
         "expected_pattern": r"pip\s+install.*numpy", "description": "pip install"},
        {"query": "wyświetl globalne pakiety yarn",
         "expected_pattern": r"(yarn|npm)\s+(list|ls|global list)", "description": "yarn list global"},
    ],
    "rag": [
        {"query": "przeszukaj Qdrant w poszukiwaniu 'deep learning'",
         "expected_pattern": r"(qdrant|query|search).*deep.?learning", "description": "Qdrant query"},
        {"query": "wygeneruj embeddingi przez model sentence-transformers",
         "expected_pattern": r"(sentence|transform|embed|python)", "description": "Sentence embeddings"},
        {"query": "zaindeksuj pliki Markdown z /content",
         "expected_pattern": r"(markdown|md|langchain|load|read).*(/content|content)", "description": "Index Markdown"},
    ],
    "presentation": [
        {"query": "przekonwertuj CHANGELOG.md na PDF",
         "expected_pattern": r"(pandoc|wkhtmltopdf|weasyprint|md).*CHANGELOG.*pdf", "description": "MD to PDF"},
        {"query": "stwórz wykres liniowy z data.csv",
         "expected_pattern": r"(matplotlib|plt|gnuplot|chart|plot|pandas).*data", "description": "Line chart from CSV"},
        {"query": "wyrenderuj PlantUML do SVG",
         "expected_pattern": r"(plantuml|puml).*svg", "description": "PlantUML render"},
    ],
}

# System prompts per domain
SYSTEM_PROMPTS: dict[str, str] = {
    "shell": """Jesteś ekspertem Linux. Przykłady:
Q: znajdź pliki PDF > 10MB -> find / -type f -name '*.pdf' -size +10M
Q: użycie dysku /var/log -> du -sh /var/log
Q: procesy po pamięci -> ps aux --sort=-%mem | head
Odpowiedz TYLKO komendą. Bez komentarzy.""",

    "docker": """Jesteś ekspertem Docker. Przykłady:
Q: uruchomione kontenery -> docker ps
Q: zbuduj obraz myapp -> docker build -t myapp:latest .
Q: logi kontenera nginx 100 linii -> docker logs --tail 100 nginx
Odpowiedz TYLKO komendą docker. Bez komentarzy.""",

    "sql": """Jesteś ekspertem SQL. Przykłady:
Q: użytkownicy z Warszawy -> SELECT * FROM users WHERE city = 'Warszawa';
Q: policz zamówienia po miesiącu -> SELECT DATE_TRUNC('month', created_at) AS m, COUNT(*) FROM orders GROUP BY m;
Q: utwórz tabelę produkty -> CREATE TABLE produkty (id SERIAL PRIMARY KEY, nazwa VARCHAR(255), cena DECIMAL(10,2));
Odpowiedz TYLKO poleceniem SQL. Bez komentarzy.""",

    "kubernetes": """Jesteś ekspertem Kubernetes. Przykłady:
Q: pody w namespace production -> kubectl get pods -n production
Q: skaluj deployment do 5 -> kubectl scale deployment webapp --replicas=5
Q: logi poda nginx-abc123 -> kubectl logs nginx-abc123
Odpowiedz TYLKO komendą kubectl. Bez komentarzy.""",

    "browser": """Jesteś ekspertem od otwierania stron w Linux. Używaj xdg-open. Przykłady:
Q: otwórz github.com -> xdg-open 'https://github.com'
Q: wyszukaj w Google python -> xdg-open 'https://www.google.com/search?q=python'
Odpowiedz TYLKO jedną komendą xdg-open. Bez komentarzy.""",

    "git": """Jesteś ekspertem Git. Przykłady:
Q: pokaż ostatnie 10 commitów -> git log -10 --oneline
Q: utwórz branch feature/login -> git checkout -b feature/login
Q: dodaj wszystko i commituj -> git add -A && git commit -m 'update'
Odpowiedz TYLKO komendą git. Bez komentarzy.""",

    "devops": """Jesteś ekspertem DevOps. Przykłady:
Q: sprawdź status nginx -> systemctl status nginx
Q: uruchom playbook -> ansible-playbook deploy.yml
Q: zastosuj terraform -> terraform apply
Odpowiedz TYLKO jedną komendą. Bez komentarzy.""",

    "api": """Jesteś ekspertem od curl. Przykłady:
Q: wyślij GET na URL -> curl -s https://api.example.com/users
Q: wyślij POST z JSON -> curl -s -X POST -H 'Content-Type: application/json' -d '{"key":"val"}' https://example.com/api
Q: sprawdź kod HTTP -> curl -o /dev/null -s -w '%{http_code}' https://example.com
Odpowiedz TYLKO komendą curl. Bez komentarzy.""",

    "ffmpeg": """Jesteś ekspertem FFmpeg. Przykłady:
Q: konwertuj mp4 do webm -> ffmpeg -i video.mp4 output.webm
Q: wyodrębnij audio -> ffmpeg -i film.mkv -vn -acodec libmp3lame audio.mp3
Q: zmień rozdzielczość 720p -> ffmpeg -i input.mp4 -vf scale=-1:720 output.mp4
Odpowiedz TYLKO komendą ffmpeg. Bez komentarzy.""",

    "media": """Jesteś ekspertem ImageMagick. Przykłady:
Q: zmień rozmiar na 800x600 -> convert photo.jpg -resize 800x600 output.jpg
Q: miniaturka 150x150 -> convert img.png -thumbnail 150x150 thumb.png
Q: konwertuj PNG na JPEG -> mogrify -format jpg *.png
Odpowiedz TYLKO komendą convert/mogrify. Bez komentarzy.""",

    "data": """Jesteś ekspertem od przetwarzania danych. Przykłady:
Q: statystyki CSV -> csvstat dane.csv
Q: filtruj JSON po age > 30 -> jq '.[] | select(.age > 30)' users.json
Q: unikalne wartości w kolumnie status -> cut -d',' -f3 log.csv | sort | uniq -c | sort -rn
Odpowiedz TYLKO komendą. Bez komentarzy.""",

    "remote": """Jesteś ekspertem SSH/SCP/rsync. Przykłady:
Q: połącz SSH jako admin -> ssh admin@192.168.1.100
Q: skopiuj plik na serwer -> scp backup.tar.gz admin@server:/tmp/
Q: zsynchronizuj katalog -> rsync -avz /var/www/ admin@server:/var/www/
Odpowiedz TYLKO komendą. Bez komentarzy.""",

    "iot": """Jesteś ekspertem IoT/Raspberry Pi. Przykłady:
Q: temperatura RPi -> vcgencmd measure_temp
Q: wykryj I2C -> i2cdetect -y 1
Q: wyślij MQTT -> mosquitto_pub -h localhost -t sensors/temperature -m '22.5'
Odpowiedz TYLKO komendą. Bez komentarzy.""",

    "package_mgmt": """Jesteś ekspertem od pakietów. Przykłady:
Q: zainstaluj nodejs -> sudo apt install nodejs
Q: zainstaluj requests pip -> pip install requests
Q: globalne pakiety npm -> npm list -g
Odpowiedz TYLKO komendą. Bez komentarzy.""",

    "rag": """Jesteś ekspertem RAG/vector DB. Przykłady:
Q: wyszukaj w ChromaDB -> python3 -c "import chromadb; c = chromadb.PersistentClient(); col = c.get_collection('docs'); print(col.query(query_texts=['machine learning'], n_results=5))"
Q: embeddingi Ollama -> curl -s http://localhost:11434/api/embed -d '{"model":"nomic-embed-text","input":"text"}'
Q: załaduj PDFy -> python3 -c "from langchain.document_loaders import DirectoryLoader; print(len(DirectoryLoader('/docs',glob='**/*.pdf').load()),'docs')"
Odpowiedz TYLKO komendą (python3 -c lub curl). Bez komentarzy.""",

    "presentation": """Jesteś ekspertem od dokumentów/wykresów. Przykłady:
Q: markdown do PDF -> pandoc README.md -o README.pdf
Q: wykres z CSV -> python3 -c "import pandas as pd,matplotlib.pyplot as plt;pd.read_csv('sales.csv').plot(kind='bar');plt.savefig('chart.png')"
Q: diagram Mermaid -> mmdc -i diagram.mmd -o diagram.png
Odpowiedz TYLKO komendą. Bez komentarzy.""",
}

# ---------------------------------------------------------------------------
# Models config - load from env or use defaults
# ---------------------------------------------------------------------------
def _get_benchmark_models() -> list[dict[str, str]]:
    """Load models from env or return defaults. Format: name:display:params,name2:display2:params2"""
    env_models = os.environ.get("NLP2CMD_BENCHMARK_MODELS", "")
    if env_models:
        models = []
        for model_spec in env_models.split(","):
            parts = model_spec.strip().split(":")
            if len(parts) >= 1:
                name = parts[0]
                display = parts[1] if len(parts) > 1 else name
                params = parts[2] if len(parts) > 2 else "?"
                models.append({"name": name, "display": display, "params": params})
        return models if models else _default_models()
    return _default_models()


def _default_models() -> list[dict[str, str]]:
    """Default benchmark models."""
    return [
        {"name": "bielik-1.5b", "display": "Bielik-1.5B (PL)", "params": "1.5B"},
        {"name": "qwen2.5:3b", "display": "Qwen2.5-3B", "params": "3B"},
        {"name": "gemma2:2b", "display": "Gemma2-2B", "params": "2B"},
        {"name": "qwen2.5-coder:3b", "display": "Qwen2.5-Coder-3B", "params": "3B"},
    ]


MODELS = _get_benchmark_models()



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
def _remove_inline_backticks(text: str) -> str:
    """Remove inline markdown code formatting: `command`."""
    if text.startswith("`") and text.endswith("`") and text.count("`") >= 2:
        return text.strip("`").strip()
    return text

def _remove_think_blocks(text: str) -> str:
    """Remove DeepSeek-R1 reasoning blocks."""
    # Remove complete  blocks
    text = re.sub(r".*?", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    # Handle unclosed  — remove everything from  to end
    if "" in text.lower():
        idx = text.lower().find("")
        think_end = text.lower().find("", idx)
        if think_end >= 0:
            text = text[:idx] + text[think_end + 8:]
        else:
            text = text[:idx]
        text = text.strip()
    return text

def _extract_fenced_code(text: str) -> str:
    """Remove markdown code blocks and extract content."""
    m = re.search(r"```(?:bash|shell|sql|sh)?\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text

def _is_explanation_line(line: str) -> bool:
    """Check if line is an explanation/conversational filler."""
    lower = line.lower()
    if lower.startswith(("sure", "ok", "okay", "i'm sorry", "im sorry", "i cannot", "i can't", "as an ai", "here's", "here is")):
        return True
    if line.startswith("#") or line.startswith("//"):
        return True
    # Skip lines that look like natural language (long sentences without shell operators)
    if len(line) > 120 and not any(c in line for c in ["|", "&&", ";", ">"]):
        return True
    return False

def _filter_command_lines(text: str) -> str:
    """Remove leading explanation lines, keep only command-looking lines."""
    lines = text.split("\n")
    cmd_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if not _is_explanation_line(line):
            cmd_lines.append(line)
    return " ".join(cmd_lines) if cmd_lines else text

# ---------------------------------------------------------------------------
def clean_command(raw: str) -> str:
    """Extract clean command from LLM response."""
    text = raw.strip()
    
    text = _remove_inline_backticks(text)
    text = _remove_think_blocks(text)
    text = _extract_fenced_code(text)
    text = _remove_inline_backticks(text)  # Re-check after extracting fenced code
    text = _filter_command_lines(text)
    
    return text


# ---------------------------------------------------------------------------
# Main benchmark runner
# ---------------------------------------------------------------------------
def _check_ollama_available() -> None:
    """Check if ollama is running and exit if not."""
    if not ollama_available():
        log.error("Ollama is not running at %s", OLLAMA_BASE)
        sys.exit(1)
    log.info("✅ Ollama available at %s", OLLAMA_BASE)


def _setup_bielik_model() -> None:
    """Ensure bielik-1.5b model exists in ollama."""
    if not ollama_model_exists("bielik-1.5b"):
        log.info("Bielik-1.5b not found in ollama — creating from GGUF …")
        if not ollama_create_bielik():
            log.warning("⚠️  Skipping Bielik-1.5B (GGUF not available)")
            MODELS[:] = [m for m in MODELS if m["name"] != "bielik-1.5b"]


def _verify_and_pull_models() -> None:
    """Verify all models exist and pull if needed."""
    for model_cfg in MODELS[:]:
        if not ollama_model_exists(model_cfg["name"]):
            log.warning("Model %s not in ollama — trying pull …", model_cfg["name"])
            try:
                subprocess.run(
                    ["ollama", "pull", model_cfg["name"]],
                    check=True, capture_output=True, text=True, timeout=OLLAMA_PULL_TIMEOUT,
                )
                log.info("✅ Pulled %s", model_cfg["name"])
            except Exception as exc:
                log.error("Cannot get model %s: %s — skipping", model_cfg["name"], exc)
                MODELS[:] = [m for m in MODELS if m["name"] != model_cfg["name"]]

    if not MODELS:
        log.error("No models available — aborting")
        sys.exit(1)


def _warmup_model(model_name: str) -> bool:
    """Warm up a model with a simple query."""
    try:
        ollama_generate(model_name, "hello", max_tokens=5)
        return True
    except Exception as exc:
        log.error("  Warmup failed: %s — skipping model", exc)
        return False


def _run_query(model_name: str, domain: str, query: dict[str, str], system_prompt: str) -> QueryResult:
    """Run a single benchmark query."""
    qr = QueryResult(
        model=model_name,
        domain=domain,
        query=query["query"],
        description=query["description"],
        raw_response="",
        cleaned_command="",
        expected_pattern=query["expected_pattern"],
        pattern_match=False,
        response_time_sec=0.0,
    )

    try:
        raw, elapsed = ollama_generate(
            model_name, query["query"], system=system_prompt,
            max_tokens=200,
        )
        qr.raw_response = raw
        qr.cleaned_command = clean_command(raw)
        qr.response_time_sec = round(elapsed, 3)

        if not qr.cleaned_command.strip():
            qr.error = "empty_response"

        qr.pattern_match = bool(
            re.search(query["expected_pattern"], qr.cleaned_command, re.IGNORECASE)
        )

        status = "✅" if qr.pattern_match else "⚠️"
        log.info("      %s %.2fs | %s", status, elapsed, qr.cleaned_command[:70])

    except Exception as exc:
        qr.error = str(exc)
        qr.response_time_sec = 0.0
        log.error("      ❌ Error: %s", exc)

    return qr


def _run_model_benchmark(model_cfg: dict[str, str], total_queries: int) -> list[dict[str, Any]]:
    """Run benchmark for a single model across all domains."""
    model_name = model_cfg["name"]
    log.info("-" * 60)
    log.info("🤖 Model: %s (%s)", model_cfg["display"], model_cfg["params"])
    log.info("-" * 60)

    if not _warmup_model(model_name):
        return []

    results = []
    query_num = 0

    for domain, queries in BENCHMARK_QUERIES.items():
        system_prompt = SYSTEM_PROMPTS.get(domain, "")
        log.info("  📂 Domain: %s (%d queries)", domain, len(queries))

        for q in queries:
            query_num += 1
            log.info("    [%d/%d] %s: %s", query_num, total_queries, domain, q["query"][:60])

            qr = _run_query(model_name, domain, q, system_prompt)
            results.append(asdict(qr))

    return results


def run_benchmark() -> BenchmarkResults:
    log.info("=" * 70)
    log.info("NLP2CMD LLM Benchmark")
    log.info("=" * 70)

    _check_ollama_available()
    _setup_bielik_model()
    _verify_and_pull_models()

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

    for model_cfg in MODELS:
        model_results = _run_model_benchmark(model_cfg, total_queries)
        results.results.extend(model_results)

    results.summary = build_summary(results)
    return results


def _calculate_model_stats(model_cfg: dict, results: list) -> dict[str, Any]:
    """Calculate statistics for a single model."""
    mname = model_cfg["name"]
    model_results = [r for r in results if r["model"] == mname]
    if not model_results:
        return None
    
    total = len(model_results)
    matched = sum(1 for r in model_results if r["pattern_match"])
    errors = sum(1 for r in model_results if r.get("error"))
    times = [r["response_time_sec"] for r in model_results if not r.get("error")]
    avg_time = round(sum(times) / len(times), 3) if times else 0
    
    return {
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

def _calculate_domain_model_stats(domain_results: list, models: list) -> dict[str, dict[str, Any]]:
    """Calculate per-model statistics for a domain."""
    per_model: dict[str, dict[str, Any]] = {}
    for model_cfg in models:
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
    return per_model

def _calculate_domain_stats(domain: str, results: list, models: list) -> dict[str, Any]:
    """Calculate statistics for a single domain."""
    domain_results = [r for r in results if r["domain"] == domain]
    if not domain_results:
        return None
    
    total = len(domain_results)
    matched = sum(1 for r in domain_results if r["pattern_match"])
    times = [r["response_time_sec"] for r in domain_results if not r.get("error")]
    per_model = _calculate_domain_model_stats(domain_results, models)
    
    return {
        "total": total,
        "matched": matched,
        "accuracy_pct": round(matched / total * 100, 1) if total else 0,
        "avg_response_sec": round(sum(times) / len(times), 3) if times else 0,
        "per_model": per_model,
    }

def _calculate_overall_stats(results: list) -> dict[str, Any]:
    """Calculate overall statistics across all results."""
    total = len(results)
    matched = sum(1 for r in results if r["pattern_match"])
    times = [r["response_time_sec"] for r in results if not r.get("error")]
    
    return {
        "total_queries": total,
        "total_matched": matched,
        "accuracy_pct": round(matched / total * 100, 1) if total else 0,
        "avg_response_sec": round(sum(times) / len(times), 3) if times else 0,
        "total_time_sec": round(sum(times), 1) if times else 0,
    }

def build_summary(results: BenchmarkResults) -> dict[str, Any]:
    """Aggregate per-model and per-domain stats."""
    summary: dict[str, Any] = {"models": {}, "domains": {}, "overall": {}}
    
    for model_cfg in results.models:
        model_stats = _calculate_model_stats(model_cfg, results.results)
        if model_stats:
            summary["models"][model_cfg["name"]] = model_stats
    
    for domain in results.domains:
        domain_stats = _calculate_domain_stats(domain, results.results, results.models)
        if domain_stats:
            summary["domains"][domain] = domain_stats
    
    summary["overall"] = _calculate_overall_stats(results.results)
    
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
    default_colors = "#4e79a7,#f28e2b,#e15759,#76b7b2,#59a14f"
    model_colors = os.environ.get("NLP2CMD_BENCHMARK_COLORS", default_colors).split(",")

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

    chart_cdn = os.environ.get("NLP2CMD_CHART_CDN_URL", "https://cdn.jsdelivr.net/npm/chart.js@4")

    html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NLP2CMD Benchmark — {len(results.models)} LLMs ≤3B</title>
<script src="{chart_cdn}"></script>
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
  <p class="subtitle">{len(results.models)} lokalne modele ≤3B • 6 domen nlp2cmd • {summary.get('overall',{}).get('total_queries',0)} zapytań • {results.timestamp[:19]}</p>

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


def generate_command_errors_report(results: BenchmarkResults) -> str:
    """Generate a Markdown report listing incorrect commands.

    Includes:
    - errors (e.g. empty_response)
    - pattern mismatches (pattern_match == False)
    """
    ts = results.timestamp
    lines: list[str] = []
    lines.append("# NLP2CMD Benchmark — Nieprawidłowe komendy (auto-report)")
    lines.append("")
    lines.append(f"Generated: `{ts}`")
    lines.append("")
    lines.append("Źródło: `benchmarks/llm_benchmark.py` + `benchmark_results.json`")
    lines.append("")

    failures = [
        r for r in results.results
        if (not r.get("pattern_match")) or bool(r.get("error"))
    ]

    total = len(results.results)
    total_fail = len(failures)
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total queries: **{total}**")
    lines.append(f"- Failed / errors: **{total_fail}**")
    lines.append("")

    if not failures:
        lines.append("## Failures")
        lines.append("")
        lines.append("Brak — wszystkie zapytania przeszły.")
        lines.append("")
        return "\n".join(lines)

    # Group failures by model -> domain
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for r in failures:
        model = r.get("model", "?")
        domain = r.get("domain", "?")
        grouped.setdefault(model, {}).setdefault(domain, []).append(r)

    lines.append("## Failures")
    lines.append("")
    for model in sorted(grouped.keys()):
        lines.append(f"### Model: `{model}`")
        lines.append("")
        domains = grouped[model]
        for domain in sorted(domains.keys()):
            items = domains[domain]
            lines.append(f"#### Domain: `{domain}` ({len(items)})")
            lines.append("")
            for i, r in enumerate(items, start=1):
                query = r.get("query", "")
                got = r.get("cleaned_command", "")
                expected = r.get("expected_pattern", "")
                err = r.get("error")
                lines.append(f"##### {i}. {r.get('description', '')}")
                lines.append("")
                lines.append(f"- Query: `{query}`")
                if err:
                    lines.append(f"- Error: `{err}`")
                lines.append(f"- Expected (regex): `{expected}`")
                lines.append("- Got:")
                lines.append("")
                lines.append("```bash")
                lines.append(got if got else "")
                lines.append("```")
                lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="NLP2CMD LLM Benchmark — test local models across all domains"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable cache during benchmark (forces fresh LLM calls for every query)"
    )
    args = parser.parse_args()
    
    if args.no_cache:
        log.info("🚫 Cache disabled — all queries will use fresh LLM calls")
        os.environ["NLP2CMD_DISABLE_CACHE"] = "1"
    
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

    # Save incorrect commands report (Markdown)
    errors_report = generate_command_errors_report(results)
    with open(ERRORS_MD, "w", encoding="utf-8") as f:
        f.write(errors_report)
    log.info("Command errors report saved: %s", ERRORS_MD)

    # Print summary
    print_summary(results)


if __name__ == "__main__":
    main()
