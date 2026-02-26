#!/usr/bin/env python3
"""
NLP2CMD Learning-Mode Benchmark.

Tests the evolutionary cache system:
  - Round 1: Cold start (all queries go to LLM teacher)
  - Round 2: Warm cache (most queries served from cache)
  - Round 3: Hot cache (all queries instant from cache)

Measures speed improvement across all 16 domains with 3x repeated
pseudo-random queries per domain. Outputs JSON + HTML report.
"""

from __future__ import annotations

import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure project imports work
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from nlp2cmd.generation.evolutionary_cache import (
    EvolutionaryCache,
    LookupResult,
    detect_domain,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
RESULTS_DIR = PROJECT_ROOT / "benchmark_output"
RESULTS_JSON = RESULTS_DIR / "learning_benchmark.json"
RESULTS_HTML = RESULTS_DIR / "learning_benchmark.html"
LOG_FILE = RESULTS_DIR / "learning_benchmark.log"
CACHE_DIR = RESULTS_DIR / ".nlp2cmd_bench"  # Isolated cache for benchmark

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stderr),
    ],
)
log = logging.getLogger("learning_bench")

# ---------------------------------------------------------------------------
# Test queries — 2 per domain across all 16 domains = 32 base queries
# ---------------------------------------------------------------------------
QUERIES: dict[str, list[str]] = {
    "shell": [
        "znajdź wszystkie pliki PDF większe niż 10MB",
        "pokaż procesy zużywające najwięcej pamięci",
    ],
    "docker": [
        "pokaż wszystkie uruchomione kontenery Docker",
        "zbuduj obraz Docker z tagiem myapp:latest",
    ],
    "sql": [
        "pokaż użytkowników z Warszawy",
        "utwórz tabelę produkty z kolumnami id, nazwa, cena",
    ],
    "kubernetes": [
        "pokaż pody w namespace production",
        "przeskaluj deployment webapp do 5 replik",
    ],
    "browser": [
        "otwórz stronę https://github.com",
        "wyszukaj w Google 'python tutorial'",
    ],
    "git": [
        "pokaż historię ostatnich 10 commitów",
        "utwórz branch feature/login",
    ],
    "devops": [
        "sprawdź status usługi nginx",
        "uruchom playbook Ansible deploy.yml",
    ],
    "api": [
        "wyślij GET na https://api.example.com/users",
        "sprawdź kod HTTP serwera https://example.com",
    ],
    "ffmpeg": [
        "konwertuj video.mp4 do webm",
        "wyodrębnij audio z film.mkv do mp3",
    ],
    "media": [
        "zmień rozmiar photo.jpg na 800x600",
        "utwórz miniaturkę 150x150 z header.png",
    ],
    "data": [
        "pokaż statystyki pliku CSV dane.csv",
        "przefiltruj JSON users.json po age > 30",
    ],
    "remote": [
        "połącz SSH do 192.168.1.100 jako admin",
        "zsynchronizuj /var/www na zdalny serwer",
    ],
    "iot": [
        "odczytaj temperaturę z Raspberry Pi",
        "wykryj urządzenia I2C na magistrali 1",
    ],
    "package_mgmt": [
        "zainstaluj nodejs przez apt",
        "zainstaluj requests przez pip",
    ],
    "rag": [
        "wyszukaj w ChromaDB dokumenty o machine learning",
        "wygeneruj embeddingi przez Ollama",
    ],
    "presentation": [
        "konwertuj README.md do PDF",
        "wyrenderuj diagram Mermaid do PNG",
    ],
}

NUM_ROUNDS = int(os.environ.get("NLP2CMD_BENCHMARK_ROUNDS", "3"))  # How many times each query is repeated


def _teacher_models() -> list[str]:
    raw = os.environ.get("NLP2CMD_TEACHER_MODELS", "").strip()
    if raw:
        models = [m.strip() for m in raw.split(",") if m.strip()]
        return models
    return [
        os.environ.get("NLP2CMD_TEACHER_MODEL", "qwen2.5:3b"),
        "qwen2.5-coder:3b",
        "gemma2:2b",
    ]


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------
def run_learning_benchmark(*, teacher_model: str, cache_dir: Path) -> dict[str, Any]:
    log.info("=" * 70)
    log.info("NLP2CMD Learning-Mode Benchmark")
    log.info("=" * 70)

    # Use isolated cache directory for reproducible results
    if cache_dir.exists():
        import shutil
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache = EvolutionaryCache(
        cache_dir=cache_dir,
        teacher_model=teacher_model,
        enable_llm=True,
    )

    all_queries = []
    for domain, qs in QUERIES.items():
        for q in qs:
            all_queries.append((domain, q))

    log.info("Domains: %d, Base queries: %d, Rounds: %d, Total: %d",
             len(QUERIES), len(all_queries), NUM_ROUNDS,
             len(all_queries) * NUM_ROUNDS)

    results: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "domains": len(QUERIES),
            "queries_per_domain": 2,
            "rounds": NUM_ROUNDS,
            "total_queries": len(all_queries) * NUM_ROUNDS,
            "teacher_model": cache.teacher_model,
            "cache_dir": str(cache_dir),
        },
        "rounds": [],
        "per_query": [],
    }

    # Run rounds
    for round_num in range(1, NUM_ROUNDS + 1):
        round_label = {1: "COLD (LLM teacher)", 2: "WARM (mixed)", 3: "HOT (all cached)"}
        log.info("-" * 60)
        log.info("🔄 Round %d: %s", round_num, round_label.get(round_num, f"Round {round_num}"))
        log.info("-" * 60)

        # Shuffle queries for pseudo-random order
        shuffled = list(all_queries)
        random.seed(int(os.environ.get("NLP2CMD_BENCHMARK_SEED", "42")) + round_num)  # Deterministic but different per round
        random.shuffle(shuffled)

        round_results = {
            "round": round_num,
            "label": round_label.get(round_num, f"Round {round_num}"),
            "queries": [],
            "total_time_ms": 0,
            "cache_hits": 0,
            "llm_calls": 0,
            "avg_time_ms": 0,
        }

        for domain, query in shuffled:
            lr = cache.lookup(query, domain=domain)

            entry = {
                "round": round_num,
                "domain": domain,
                "query": query,
                "command": lr.command[:100],
                "source": lr.source,
                "elapsed_ms": lr.elapsed_ms,
                "cached": lr.cached,
            }
            round_results["queries"].append(entry)
            results["per_query"].append(entry)

            if lr.cached:
                round_results["cache_hits"] += 1
            elif lr.source == "llm_teacher":
                round_results["llm_calls"] += 1

            round_results["total_time_ms"] += lr.elapsed_ms

            status = "⚡" if lr.cached else "🤖"
            log.info("  %s [%s] %.1fms %s | %s",
                     status, lr.source[:10], lr.elapsed_ms, domain,
                     lr.command[:60] if lr.command else "(empty)")

        n = len(shuffled)
        round_results["avg_time_ms"] = round(round_results["total_time_ms"] / n, 3) if n else 0
        round_results["total_time_ms"] = round(round_results["total_time_ms"], 1)
        results["rounds"].append(round_results)

        log.info("  📊 Round %d: total=%.1fms avg=%.1fms cache=%d llm=%d",
                 round_num, round_results["total_time_ms"],
                 round_results["avg_time_ms"],
                 round_results["cache_hits"], round_results["llm_calls"])

    # Final stats
    cache_stats = cache.get_stats()
    results["cache_stats"] = cache_stats

    # Compute speedup
    r1 = results["rounds"][0] if results["rounds"] else {}
    r3 = results["rounds"][-1] if len(results["rounds"]) >= 3 else {}
    if r1.get("avg_time_ms", 0) > 0 and r3.get("avg_time_ms", 0) > 0:
        speedup = r1["avg_time_ms"] / r3["avg_time_ms"]
    else:
        speedup = 1.0

    results["summary"] = {
        "round1_avg_ms": r1.get("avg_time_ms", 0),
        "round3_avg_ms": r3.get("avg_time_ms", 0),
        "speedup_factor": round(speedup, 1),
        "cache_hit_rate_pct": cache_stats.get("hit_rate_pct", 0),
        "cached_entries": cache_stats.get("cached_entries", 0),
        "total_time_saved_ms": round(
            r1.get("total_time_ms", 0) - r3.get("total_time_ms", 0), 1
        ),
    }

    return results


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------
def _generate_single_teacher_fragment(results: dict, *, chart_id_prefix: str) -> str:
    summary = results.get("summary", {})
    rounds = results.get("rounds", [])

    round_labels = json.dumps([r.get("label", f"R{r['round']}") for r in rounds])
    round_avg_times = json.dumps([r.get("avg_time_ms", 0) for r in rounds])
    round_total_times = json.dumps([r.get("total_time_ms", 0) for r in rounds])
    round_cache_hits = json.dumps([r.get("cache_hits", 0) for r in rounds])
    round_llm_calls = json.dumps([r.get("llm_calls", 0) for r in rounds])

    # Per-domain avg time per round
    domains = list(QUERIES.keys())
    domain_datasets_time = []
    colors_env = os.environ.get("NLP2CMD_BENCHMARK_COLORS", "#ef4444,#f59e0b,#22c55e")
    colors = colors_env.split(",")
    for i, rd in enumerate(rounds):
        data = []
        for d in domains:
            dqs = [q for q in rd.get("queries", []) if q["domain"] == d]
            avg = sum(q["elapsed_ms"] for q in dqs) / len(dqs) if dqs else 0
            data.append(round(avg, 2))
        domain_datasets_time.append({
            "label": rd.get("label", f"Round {rd['round']}"),
            "data": data,
            "backgroundColor": colors[i % len(colors)],
        })

    html = f"""
  <div class="cards">
    <div class="card green">
      <div class="label">Przyspieszenie</div>
      <div class="value">{summary.get('speedup_factor',1)}×</div>
      <div class="detail">Round 1 vs Round 3</div>
    </div>
    <div class="card">
      <div class="label">Śr. czas Round 1 (cold)</div>
      <div class="value">{summary.get('round1_avg_ms',0):.1f}ms</div>
      <div class="detail">LLM teacher generuje</div>
    </div>
    <div class="card green">
      <div class="label">Śr. czas Round 3 (hot)</div>
      <div class="value">{summary.get('round3_avg_ms',0):.3f}ms</div>
      <div class="detail">Cache instant lookup</div>
    </div>
    <div class="card yellow">
      <div class="label">Zaoszczędzony czas</div>
      <div class="value">{summary.get('total_time_saved_ms',0):.0f}ms</div>
      <div class="detail">Cache hit rate: {summary.get('cache_hit_rate_pct',0)}%</div>
    </div>
  </div>

  <h2>📐 Algorytm: 4-Tier Evolutionary Lookup</h2>
  <div class="algo">
    <div class="step fast">1. <b>CACHE EXACT</b> — MD5 fingerprint → instant lookup (~0.01ms) ⚡</div>
    <div class="step fast">2. <b>CACHE FUZZY</b> — normalized word-bag fingerprint → similar query match (~0.02ms) ⚡</div>
    <div class="step">3. <b>DOMAIN DETECT</b> — keyword scoring → identify domain (shell/docker/k8s/...) (~0.1ms)</div>
    <div class="step slow">4. <b>LLM TEACHER</b> — Qwen2.5-3B generates command → auto-cached for future (~200ms) 🤖</div>
  </div>

  <div class="chart-row">
    <div class="chart-container">
      <h2 style="margin-top:0">⏱ Średni czas per round</h2>
      <canvas id="{chart_id_prefix}_chartAvgTime"></canvas>
    </div>
    <div class="chart-container">
      <h2 style="margin-top:0">📊 Cache hits vs LLM calls</h2>
      <canvas id="{chart_id_prefix}_chartHitsVsLLM"></canvas>
    </div>
  </div>

  <div class="chart-container">
    <h2 style="margin-top:0">📂 Czas per domena per round</h2>
    <canvas id="{chart_id_prefix}_chartDomainTime"></canvas>
  </div>

  <div class="footer">
    NLP2CMD Learning Benchmark · {results.get('timestamp','')[:19]} · Teacher: {results.get('config',{}).get('teacher_model','')}
  </div>
</div>

<script>
new Chart(document.getElementById('{chart_id_prefix}_chartAvgTime'), {{
  type: 'bar',
  data: {{
    labels: {round_labels},
    datasets: [{{
      label: 'Avg time (ms)',
      data: {round_avg_times},
      backgroundColor: {json.dumps(colors_env.split(','))},
      borderRadius: 6,
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      y: {{ beginAtZero: true, title: {{ display: true, text: 'ms', color:'#94a3b8' }}, ticks: {{ color:'#94a3b8' }}, grid: {{ color:'#334155' }} }},
      x: {{ ticks: {{ color:'#94a3b8' }}, grid: {{ display: false }} }}
    }}
  }}
}});

new Chart(document.getElementById('{chart_id_prefix}_chartHitsVsLLM'), {{
  type: 'bar',
  data: {{
    labels: {round_labels},
    datasets: [
      {{ label: 'Cache hits', data: {round_cache_hits}, backgroundColor: '#22c55e', borderRadius: 6 }},
      {{ label: 'LLM calls', data: {round_llm_calls}, backgroundColor: '#ef4444', borderRadius: 6 }},
    ]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ labels: {{ color:'#94a3b8' }} }} }},
    scales: {{
      y: {{ beginAtZero: true, ticks: {{ color:'#94a3b8' }}, grid: {{ color:'#334155' }} }},
      x: {{ ticks: {{ color:'#94a3b8' }}, grid: {{ display: false }} }}
    }}
  }}
}});

new Chart(document.getElementById('{chart_id_prefix}_chartDomainTime'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(domains)},
    datasets: {json.dumps(domain_datasets_time)}
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ labels: {{ color:'#94a3b8' }} }} }},
    scales: {{
      y: {{ beginAtZero: true, title: {{ display: true, text: 'ms', color:'#94a3b8' }}, ticks: {{ color:'#94a3b8' }}, grid: {{ color:'#334155' }} }},
      x: {{ ticks: {{ color:'#94a3b8', maxRotation: 45 }}, grid: {{ display: false }} }}
    }}
  }}
}});
</script>
"""
    return html


def generate_html(results: dict) -> str:
    chart_cdn = os.environ.get("NLP2CMD_CHART_CDN_URL", "https://cdn.jsdelivr.net/npm/chart.js@4")
    if "teachers" in results:
        teachers = results.get("teachers", {})
        teacher_sections = []
        for idx, (teacher_model, teacher_result) in enumerate(teachers.items()):
            chart_id_prefix = f"t{idx}"
            teacher_sections.append(
                "<details open>"
                f"<summary>Teacher: {teacher_model}</summary>"
                + _generate_single_teacher_fragment(teacher_result, chart_id_prefix=chart_id_prefix)
                + "</details>"
            )

        return f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NLP2CMD Learning Benchmark (multi-teacher)</title>
<script src="{chart_cdn}"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Segoe UI',system-ui,sans-serif; background:#0f172a; color:#e2e8f0; line-height:1.6; }}
  .container {{ max-width:1200px; margin:0 auto; padding:2rem; }}
  h1 {{ font-size:2rem; color:#38bdf8; margin-bottom:.5rem; }}
  h2 {{ font-size:1.3rem; color:#7dd3fc; margin:2rem 0 1rem; border-bottom:1px solid #334155; padding-bottom:.5rem; }}
  .subtitle {{ color:#94a3b8; margin-bottom:2rem; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:1rem; margin-bottom:2rem; }}
  .card {{ background:#1e293b; border-radius:12px; padding:1.5rem; border:1px solid #334155; }}
  .card .label {{ color:#94a3b8; font-size:.85rem; text-transform:uppercase; letter-spacing:.05em; }}
  .card .value {{ font-size:2rem; font-weight:700; color:#38bdf8; margin:.25rem 0; }}
  .card .detail {{ color:#64748b; font-size:.85rem; }}
  .card.green .value {{ color:#22c55e; }}
  .card.yellow .value {{ color:#f59e0b; }}
  .chart-container {{ background:#1e293b; border-radius:12px; padding:1.5rem; border:1px solid #334155; margin-bottom:1.5rem; }}
  .chart-row {{ display:grid; grid-template-columns:1fr 1fr; gap:1.5rem; }}
  @media (max-width:768px) {{ .chart-row {{ grid-template-columns:1fr; }} }}
  canvas {{ max-height:350px; }}
  .algo {{ background:#1e293b; border-radius:12px; padding:1.5rem; border:1px solid #334155; margin-bottom:1.5rem; font-family:'JetBrains Mono',monospace; font-size:.85rem; }}
  .algo .step {{ margin:.5rem 0; padding:.5rem 1rem; border-left:3px solid #334155; }}
  .algo .step.fast {{ border-color:#22c55e; }}
  .algo .step.slow {{ border-color:#ef4444; }}
  .footer {{ margin-top:3rem; padding-top:1rem; border-top:1px solid #334155; color:#64748b; font-size:.8rem; text-align:center; }}
  details {{ background:#0b1220; border:1px solid #334155; border-radius:12px; padding:1rem 1.25rem; margin-bottom:1rem; max-width:1200px; margin-left:auto; margin-right:auto; }}
  summary {{ cursor:pointer; color:#7dd3fc; font-weight:600; }}
</style>
</head>
<body>
<div class="container">
  <h1>🧠 NLP2CMD Learning Benchmark</h1>
  <p class="subtitle">Multi-teacher • %d modele • %s</p>
  %s
</div>
</body>
</html>""" % (
            len(teachers),
            results.get("timestamp", "")[:19],
            "\n".join(teacher_sections),
        )

    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NLP2CMD Learning Benchmark</title>
<script src="{chart_cdn}"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Segoe UI',system-ui,sans-serif; background:#0f172a; color:#e2e8f0; line-height:1.6; }}
  .container {{ max-width:1200px; margin:0 auto; padding:2rem; }}
  h1 {{ font-size:2rem; color:#38bdf8; margin-bottom:.5rem; }}
  h2 {{ font-size:1.3rem; color:#7dd3fc; margin:2rem 0 1rem; border-bottom:1px solid #334155; padding-bottom:.5rem; }}
  .subtitle {{ color:#94a3b8; margin-bottom:2rem; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:1rem; margin-bottom:2rem; }}
  .card {{ background:#1e293b; border-radius:12px; padding:1.5rem; border:1px solid #334155; }}
  .card .label {{ color:#94a3b8; font-size:.85rem; text-transform:uppercase; letter-spacing:.05em; }}
  .card .value {{ font-size:2rem; font-weight:700; color:#38bdf8; margin:.25rem 0; }}
  .card .detail {{ color:#64748b; font-size:.85rem; }}
  .card.green .value {{ color:#22c55e; }}
  .card.yellow .value {{ color:#f59e0b; }}
  .chart-container {{ background:#1e293b; border-radius:12px; padding:1.5rem; border:1px solid #334155; margin-bottom:1.5rem; }}
  .chart-row {{ display:grid; grid-template-columns:1fr 1fr; gap:1.5rem; }}
  @media (max-width:768px) {{ .chart-row {{ grid-template-columns:1fr; }} }}
  canvas {{ max-height:350px; }}
  .algo {{ background:#1e293b; border-radius:12px; padding:1.5rem; border:1px solid #334155; margin-bottom:1.5rem; font-family:'JetBrains Mono',monospace; font-size:.85rem; }}
  .algo .step {{ margin:.5rem 0; padding:.5rem 1rem; border-left:3px solid #334155; }}
  .algo .step.fast {{ border-color:#22c55e; }}
  .algo .step.slow {{ border-color:#ef4444; }}
  .footer {{ margin-top:3rem; padding-top:1rem; border-top:1px solid #334155; color:#64748b; font-size:.8rem; text-align:center; }}
</style>
</head>
<body>
<div class="container">
  <h1>🧠 NLP2CMD Learning Benchmark</h1>
  <p class="subtitle">Evolutionary cache: cold → warm → hot • %d zapytań • %s</p>
  %s
</div>
</body>
</html>""" % (
        results.get("config", {}).get("total_queries", 0),
        results.get("timestamp", "")[:19],
        _generate_single_teacher_fragment(results, chart_id_prefix="single"),
    )


# ---------------------------------------------------------------------------
# Print summary
# ---------------------------------------------------------------------------
def print_summary(results: dict):
    s = results.get("summary", {})
    rounds = results.get("rounds", [])
    print()
    print("=" * 65)
    print("🧠 NLP2CMD LEARNING BENCHMARK — PODSUMOWANIE")
    print("=" * 65)

    for rd in rounds:
        emoji = {"COLD": "❄️", "WARM": "🔥", "HOT": "⚡"}.get(rd["label"].split()[0], "🔄")
        print(f"  {emoji} {rd['label']:<24} avg={rd['avg_time_ms']:>8.3f}ms  "
              f"cache={rd['cache_hits']:>2}  llm={rd['llm_calls']:>2}  "
              f"total={rd['total_time_ms']:>8.1f}ms")

    print()
    print(f"  🚀 Przyspieszenie:       {s.get('speedup_factor',1)}×")
    print(f"  ⚡ Cache hit rate:        {s.get('cache_hit_rate_pct',0)}%")
    print(f"  💾 Zapamiętane wzorce:   {s.get('cached_entries',0)}")
    print(f"  ⏱  Zaoszczędzony czas:  {s.get('total_time_saved_ms',0):.0f}ms")
    print()
    print(f"  📊 JSON: {RESULTS_JSON}")
    print(f"  📊 HTML: {RESULTS_HTML}")
    print(f"  📋 Log:  {LOG_FILE}")
    print("=" * 65)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    teachers = _teacher_models()

    combined: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "teacher_models": teachers,
            "domains": len(QUERIES),
            "queries_per_domain": 2,
            "rounds": NUM_ROUNDS,
        },
        "teachers": {},
    }

    for teacher_model in teachers:
        safe_name = teacher_model.replace(":", "_").replace("/", "_")
        cache_dir = CACHE_DIR / safe_name
        log.info("Teacher model: %s", teacher_model)
        res = run_learning_benchmark(teacher_model=teacher_model, cache_dir=cache_dir)
        combined["teachers"][teacher_model] = res

    # Save JSON
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    log.info("JSON: %s", RESULTS_JSON)

    # Save HTML
    html = generate_html(combined)
    with open(RESULTS_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    log.info("HTML: %s", RESULTS_HTML)

    for teacher_model, res in combined.get("teachers", {}).items():
        print("\n" + "-" * 65)
        print(f"Teacher: {teacher_model}")
        print("-" * 65)
        print_summary(res)


if __name__ == "__main__":
    main()
