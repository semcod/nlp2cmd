#!/usr/bin/env python3
"""
Benchmark for LLM Validator effectiveness.

Measures:
  - Accuracy: does the validator give the correct verdict?
  - Consistency: running 3x on the same input, how stable is the verdict?
  - Latency: how fast is each validation call?
  - Deterministic bypass rate: how many cases skip the LLM entirely?

Usage:
    python3 examples/08_llm_validation/benchmark_validator.py
    # With debug:
    NLP2CMD_DEBUG=1 python3 examples/08_llm_validation/benchmark_validator.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "src"))

from nlp2cmd.llm.validator import LLMValidator, ValidationVerdict


@dataclass
class BenchmarkCase:
    """A single benchmark test case."""
    name: str
    query: str
    command: str
    output: str
    expected_verdict: str   # "pass" or "fail"
    category: str = "general"
    min_score: Optional[float] = None
    max_score: Optional[float] = None


@dataclass
class CaseResult:
    name: str
    expected: str
    verdicts: list[str] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    latencies_ms: list[float] = field(default_factory=list)
    score_ok: bool = True

    @property
    def verdict_correct(self) -> bool:
        return all(v == self.expected for v in self.verdicts)

    @property
    def consistent(self) -> bool:
        return len(set(self.verdicts)) <= 1

    @property
    def avg_latency_ms(self) -> float:
        return sum(self.latencies_ms) / len(self.latencies_ms) if self.latencies_ms else 0

    @property
    def deterministic(self) -> bool:
        return all(m == "deterministic" for m in self.models)


# ─── Test cases covering key scenarios ────────────────────────────────────

BENCHMARK_CASES: list[BenchmarkCase] = [
    # ── PASS cases (command succeeded, output matches intent) ─────────────
    BenchmarkCase(
        name="nmap_camera_found",
        category="nmap",
        query="znajdz kamery podłączone do sieci lokalnej",
        command="nmap -p 80,554 --open -sV 192.168.188.0/24 | grep -E '(camera|webcam|rtsp)'",
        output="554/tcp  open  rtsp    D-Link DCS-2130 or Pelco IDE10DN webcam rtspd\n"
               "Service Info: Device: webcam; CPE: cpe:/h:pelco:ide10dn",
        expected_verdict="pass",
        min_score=0.6,
    ),
    BenchmarkCase(
        name="nmap_multiple_cameras",
        category="nmap",
        query="znajdz kamery podłączone do sieci lokalnej",
        command="nmap -p 554,80 --open -sV 192.168.188.0/24 | grep -E '(camera|webcam|rtsp)'",
        output="554/tcp open rtsp    Hikvision DS-2CD2042WD rtspd\n"
               "80/tcp  open http    Axis 210 Network Camera httpd\n"
               "554/tcp open rtsp    Foscam FI9821W V2 rtspd",
        expected_verdict="pass",
        min_score=0.8,
    ),
    BenchmarkCase(
        name="ping_success",
        category="ping",
        query="pinguj google.com",
        command="ping -c 4 google.com",
        output="PING google.com (142.250.74.206) 56(84) bytes of data.\n"
               "64 bytes from waw02s22-in-f14.1e100.net (142.250.74.206): icmp_seq=1 ttl=118 time=4.23 ms\n"
               "64 bytes: icmp_seq=2 ttl=118 time=3.98 ms\n"
               "--- google.com ping statistics ---\n"
               "4 packets transmitted, 4 received, 0% packet loss, time 3004ms",
        expected_verdict="pass",
        min_score=0.7,
    ),
    BenchmarkCase(
        name="find_large_files",
        category="find",
        query="znajdź pliki większe niż 100MB",
        command="find . -type f -size +100M",
        output="/var/log/syslog.1\n/home/tom/data/model.bin",
        expected_verdict="pass",
        min_score=0.7,
    ),
    BenchmarkCase(
        name="ls_files",
        category="ls",
        query="pokaż pliki w bieżącym katalogu",
        command="ls -la .",
        output="total 128\ndrwxr-xr-x  5 tom tom  4096 Feb 28 14:00 .\n"
               "-rw-r--r--  1 tom tom  1234 Feb 28 14:00 README.md\n"
               "-rw-r--r--  1 tom tom  5678 Feb 28 13:50 main.py",
        expected_verdict="pass",
        min_score=0.7,
    ),
    BenchmarkCase(
        name="df_disk_usage",
        category="df",
        query="pokaż użycie dysku",
        command="df -h",
        output="Filesystem      Size  Used Avail Use% Mounted on\n"
               "/dev/sda1       100G   75G   25G  75% /\n"
               "tmpfs           7.8G  1.2M  7.8G   1% /dev/shm",
        expected_verdict="pass",
        min_score=0.7,
    ),
    BenchmarkCase(
        name="ps_processes",
        category="ps",
        query="pokaż procesy zużywające pamięć",
        command="ps aux --sort=-%mem | head -5",
        output="USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\n"
               "tom       1234 12.3 45.6 5234567 3456789 ?     Sl   14:00   5:23 python3 train.py\n"
               "tom       5678  8.1 12.3 2345678 1234567 ?     Sl   13:50   2:11 node server.js",
        expected_verdict="pass",
        min_score=0.7,
    ),
    BenchmarkCase(
        name="nmap_partial_camera",
        category="nmap",
        query="znajdz kamery podłączone do sieci lokalnej",
        command="nmap -p 554 --open 192.168.188.0/24",
        output="Nmap scan report for 192.168.188.50\n554/tcp open rtsp\nNmap done: 256 addresses scanned",
        expected_verdict="pass",
        min_score=0.4,
        max_score=0.95,
    ),

    # ── FAIL cases (command failed or output is unrelated) ────────────────
    BenchmarkCase(
        name="empty_output",
        category="empty",
        query="znajdz kamery podłączone do sieci lokalnej",
        command="nmap -p 554 --open 192.168.1.0/24 | grep camera",
        output="",
        expected_verdict="fail",
        max_score=0.2,
    ),
    BenchmarkCase(
        name="command_not_found",
        category="error",
        query="skanuj sieć",
        command="nmap -sn 192.168.1.0/24",
        output="bash: nmap: command not found",
        expected_verdict="fail",
        max_score=0.2,
    ),
    BenchmarkCase(
        name="permission_denied",
        category="error",
        query="pokaż pliki w /root",
        command="ls -la /root",
        output="ls: cannot open directory '/root': Permission denied",
        expected_verdict="fail",
        max_score=0.2,
    ),
    BenchmarkCase(
        name="timeout_error",
        category="error",
        query="sprawdź połączenie z serwerem",
        command="curl -s http://192.168.1.100:8080",
        output="curl: (28) Connection timed out after 30001 milliseconds",
        expected_verdict="fail",
        max_score=0.2,
    ),
    BenchmarkCase(
        name="unrelated_output",
        category="unrelated",
        query="znajdz kamery podłączone do sieci lokalnej",
        command="ls -la /tmp",
        output="total 48\ndrwxrwxrwt 12 root root 4096 Feb 28 14:00 .\n"
               "-rw-r--r--  1 tom  tom   123 Feb 28 13:50 test.txt",
        expected_verdict="fail",
        max_score=0.4,
    ),
    BenchmarkCase(
        name="nmap_no_cameras",
        category="unrelated",
        query="znajdz kamery podłączone do sieci lokalnej",
        command="nmap -sn 192.168.1.0/24",
        output="Starting Nmap 7.95\nNmap scan report for 192.168.1.1\n"
               "Host is up (0.002s latency).\nNmap done: 256 IP addresses (2 hosts up)",
        expected_verdict="fail",
        max_score=0.4,
    ),
    BenchmarkCase(
        name="polish_find_files",
        category="find",
        query="znajdź pliki zmodyfikowane w ostatnich 7 dniach",
        command="find . -type f -mtime -7",
        output="./src/główny.py\n./docs/ąęśćżźół.txt\n./testy/test_główny.py",
        expected_verdict="pass",
        min_score=0.7,
    ),
]


def run_benchmark(
    validator: LLMValidator,
    runs_per_case: int = 3,
    label: str = "benchmark",
) -> dict:
    """Run benchmark: each case N times, collect accuracy/consistency/latency."""
    results: list[CaseResult] = []

    total = len(BENCHMARK_CASES)
    print(f"\n{'='*80}")
    print(f"  Validator Benchmark — {label}")
    print(f"  model={validator.model}, runs_per_case={runs_per_case}, cases={total}")
    print(f"{'='*80}\n")

    for i, tc in enumerate(BENCHMARK_CASES, 1):
        cr = CaseResult(name=tc.name, expected=tc.expected_verdict)
        print(f"[{i:2d}/{total}] {tc.name} (expect={tc.expected_verdict}): ", end="", flush=True)

        for run in range(runs_per_case):
            t0 = time.time()
            verdict = validator.validate(query=tc.query, command=tc.command, output=tc.output)
            elapsed_ms = (time.time() - t0) * 1000

            cr.verdicts.append(verdict.verdict)
            cr.scores.append(verdict.score)
            cr.reasons.append(verdict.reason)
            cr.models.append(verdict.model)
            cr.latencies_ms.append(elapsed_ms)

            # Score range check
            if tc.min_score is not None and verdict.score < tc.min_score:
                cr.score_ok = False
            if tc.max_score is not None and verdict.score > tc.max_score:
                cr.score_ok = False

        # Print summary
        ok_mark = "✅" if cr.verdict_correct and cr.score_ok else "❌"
        cons_mark = "🔄" if cr.consistent else "⚠️"
        det_mark = "⚡" if cr.deterministic else "🤖"
        avg_lat = cr.avg_latency_ms
        verdicts_str = "/".join(cr.verdicts)
        scores_str = "/".join(f"{s:.2f}" for s in cr.scores)
        print(f"{ok_mark}{cons_mark}{det_mark}  v=[{verdicts_str}]  s=[{scores_str}]  {avg_lat:.0f}ms")
        if not cr.verdict_correct:
            print(f"       ↳ reasons: {cr.reasons}")

        results.append(cr)

    # ── Summary ───────────────────────────────────────────────────────────
    n = len(results)
    correct = sum(1 for r in results if r.verdict_correct and r.score_ok)
    consistent = sum(1 for r in results if r.consistent)
    deterministic = sum(1 for r in results if r.deterministic)
    avg_latency = sum(r.avg_latency_ms for r in results) / n if n else 0

    accuracy_pct = correct / n * 100 if n else 0
    consistency_pct = consistent / n * 100 if n else 0
    deterministic_pct = deterministic / n * 100 if n else 0

    print(f"\n{'='*80}")
    print(f"  RESULTS: {label}")
    print(f"  Accuracy:      {correct}/{n} ({accuracy_pct:.0f}%)")
    print(f"  Consistency:   {consistent}/{n} ({consistency_pct:.0f}%)")
    print(f"  Deterministic: {deterministic}/{n} ({deterministic_pct:.0f}%)")
    print(f"  Avg latency:   {avg_latency:.0f}ms")
    print(f"{'='*80}\n")

    summary = {
        "label": label,
        "model": validator.model,
        "total_cases": n,
        "runs_per_case": runs_per_case,
        "accuracy": correct,
        "accuracy_pct": round(accuracy_pct, 1),
        "consistency": consistent,
        "consistency_pct": round(consistency_pct, 1),
        "deterministic": deterministic,
        "deterministic_pct": round(deterministic_pct, 1),
        "avg_latency_ms": round(avg_latency, 1),
        "results": [
            {
                "name": r.name,
                "expected": r.expected,
                "verdicts": r.verdicts,
                "scores": r.scores,
                "reasons": r.reasons,
                "models": r.models,
                "latencies_ms": [round(l, 1) for l in r.latencies_ms],
                "correct": r.verdict_correct and r.score_ok,
                "consistent": r.consistent,
                "deterministic": r.deterministic,
            }
            for r in results
        ],
    }

    # Save to file
    out_path = Path(__file__).parent / f"benchmark_{label}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Saved to {out_path}\n")

    return summary


def compare_benchmarks(before: dict, after: dict) -> None:
    """Print comparison of two benchmark runs."""
    print(f"\n{'='*80}")
    print(f"  COMPARISON: {before['label']} → {after['label']}")
    print(f"{'='*80}")

    metrics = [
        ("Accuracy", "accuracy_pct", "%", True),
        ("Consistency", "consistency_pct", "%", True),
        ("Deterministic", "deterministic_pct", "%", True),
        ("Avg latency", "avg_latency_ms", "ms", False),
    ]

    for name, key, unit, higher_better in metrics:
        b = before[key]
        a = after[key]
        delta = a - b
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "=")
        good = (delta > 0) == higher_better if delta != 0 else True
        color = "+" if good else "-"
        print(f"  {name:15s}: {b:6.1f}{unit} → {a:6.1f}{unit}  ({color}{abs(delta):.1f}{unit} {arrow})")

    # Per-case comparison
    before_map = {r["name"]: r for r in before["results"]}
    after_map = {r["name"]: r for r in after["results"]}

    changed = []
    for name in before_map:
        if name in after_map:
            b = before_map[name]
            a = after_map[name]
            if b["correct"] != a["correct"] or b["consistent"] != a["consistent"]:
                changed.append((name, b, a))

    if changed:
        print(f"\n  Changed cases:")
        for name, b, a in changed:
            bc = "✅" if b["correct"] else "❌"
            ac = "✅" if a["correct"] else "❌"
            print(f"    {name}: {bc}→{ac}  consistency: {b['consistent']}→{a['consistent']}")

    print(f"{'='*80}\n")


def main():
    validator = LLMValidator()

    if not validator.is_available:
        print("⚠️  Ollama not running — benchmark will test deterministic path only")

    label = sys.argv[1] if len(sys.argv) > 1 else "current"
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    summary = run_benchmark(validator, runs_per_case=runs, label=label)

    # Auto-compare if both before/after files exist
    before_path = Path(__file__).parent / "benchmark_before.json"
    after_path = Path(__file__).parent / "benchmark_after.json"
    if before_path.exists() and after_path.exists():
        with open(before_path) as f:
            before = json.load(f)
        with open(after_path) as f:
            after = json.load(f)
        compare_benchmarks(before, after)

    if summary["accuracy_pct"] < 70:
        print(f"⚠️  Accuracy {summary['accuracy_pct']}% is below 70% threshold")
        sys.exit(1)


if __name__ == "__main__":
    main()
