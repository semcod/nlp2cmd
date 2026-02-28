#!/usr/bin/env python3
"""
Comprehensive test suite for LLM Validator and LLM Repair.

Tests edge cases:
  - Correct output → pass
  - Empty output → fail
  - Error output → fail
  - Partial output → pass with low score
  - Wrong output (unrelated) → fail
  - Counting accuracy (1 item vs many)
  - Polish language queries
  - Multi-line output parsing

Usage:
    python3 examples/08_llm_validation/test_validator.py
    # or with debug:
    NLP2CMD_DEBUG=1 python3 examples/08_llm_validation/test_validator.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "src"))

from nlp2cmd.llm.validator import LLMValidator, ValidationVerdict


@dataclass
class TestCase:
    """A single validator test case."""
    name: str
    query: str
    command: str
    output: str
    expected_verdict: str   # "pass" or "fail"
    description: str = ""
    # Optional: check that score is in a range
    min_score: Optional[float] = None
    max_score: Optional[float] = None


# ─── Test cases ──────────────────────────────────────────────────────────────

TESTS: list[TestCase] = [
    # ── PASS cases ───────────────────────────────────────────────────────────
    TestCase(
        name="camera_scan_1_device",
        query="znajdz kamery podłączone do sieci lokalnej",
        command="nmap -p 80,554 --open -sV 192.168.188.0/24 | grep -E '(camera|webcam|rtsp)'",
        output="554/tcp  open  rtsp    D-Link DCS-2130 or Pelco IDE10DN webcam rtspd\nService Info: Device: webcam; CPE: cpe:/h:pelco:ide10dn",
        expected_verdict="pass",
        description="One camera found — validator should say pass and count 1 device accurately",
        min_score=0.6,
    ),
    TestCase(
        name="list_files_success",
        query="pokaż pliki w bieżącym katalogu",
        command="ls -la .",
        output="total 128\ndrwxr-xr-x  5 tom tom  4096 Feb 28 14:00 .\ndrwxr-xr-x 12 tom tom  4096 Feb 28 13:00 ..\n-rw-r--r--  1 tom tom  1234 Feb 28 14:00 README.md\n-rw-r--r--  1 tom tom  5678 Feb 28 13:50 main.py",
        expected_verdict="pass",
        description="ls -la output with files — should pass",
        min_score=0.7,
    ),
    TestCase(
        name="find_large_files",
        query="znajdź pliki większe niż 100MB",
        command="find . -type f -size +100M",
        output="/var/log/syslog.1\n/home/tom/data/model.bin",
        expected_verdict="pass",
        description="Two large files found — should pass",
        min_score=0.7,
    ),
    TestCase(
        name="process_list",
        query="pokaż procesy zużywające pamięć",
        command="ps aux --sort=-%mem | head -5",
        output="USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\nroot         1  0.0  0.1 169536 13456 ?        Ss   Feb27   0:03 /sbin/init\ntom       1234 12.3 45.6 5234567 3456789 ?     Sl   14:00   5:23 python3 train.py\ntom       5678  8.1 12.3 2345678 1234567 ?     Sl   13:50   2:11 node server.js",
        expected_verdict="pass",
        description="Process list with memory usage — should pass",
        min_score=0.7,
    ),
    TestCase(
        name="ping_success",
        query="pinguj google.com",
        command="ping -c 4 google.com",
        output="PING google.com (142.250.74.206) 56(84) bytes of data.\n64 bytes from waw02s22-in-f14.1e100.net (142.250.74.206): icmp_seq=1 ttl=118 time=4.23 ms\n64 bytes: icmp_seq=2 ttl=118 time=3.98 ms\n64 bytes: icmp_seq=3 ttl=118 time=4.11 ms\n64 bytes: icmp_seq=4 ttl=118 time=4.05 ms\n--- google.com ping statistics ---\n4 packets transmitted, 4 received, 0% packet loss, time 3004ms",
        expected_verdict="pass",
        description="Ping successful — should pass",
        min_score=0.8,
    ),

    # ── FAIL cases ───────────────────────────────────────────────────────────
    TestCase(
        name="empty_output",
        query="znajdz kamery podłączone do sieci lokalnej",
        command="nmap -p 554 --open 192.168.1.0/24 | grep camera",
        output="",
        expected_verdict="fail",
        description="Empty output — no cameras found, should fail",
        max_score=0.2,
    ),
    TestCase(
        name="command_not_found",
        query="skanuj sieć",
        command="nmap -sn 192.168.1.0/24",
        output="bash: nmap: command not found",
        expected_verdict="fail",
        description="Command not found error — should fail",
        max_score=0.2,
    ),
    TestCase(
        name="permission_denied",
        query="pokaż pliki w /root",
        command="ls -la /root",
        output="ls: cannot open directory '/root': Permission denied",
        expected_verdict="fail",
        description="Permission denied — should fail",
        max_score=0.2,
    ),
    TestCase(
        name="unrelated_output",
        query="znajdz kamery podłączone do sieci lokalnej",
        command="ls -la /tmp",
        output="total 48\ndrwxrwxrwt 12 root root 4096 Feb 28 14:00 .\n-rw-r--r--  1 tom  tom   123 Feb 28 13:50 test.txt",
        expected_verdict="fail",
        description="ls output when asked for cameras — completely unrelated, should fail",
        max_score=0.3,
    ),
    TestCase(
        name="network_scan_no_cameras",
        query="znajdz kamery podłączone do sieci lokalnej",
        command="nmap -sn 192.168.1.0/24",
        output="Starting Nmap 7.95\nNmap scan report for 192.168.1.1\nHost is up (0.002s latency).\nNmap scan report for 192.168.1.50\nHost is up (0.005s latency).\nNmap done: 256 IP addresses (2 hosts up) scanned in 3.5s",
        expected_verdict="fail",
        description="Generic host scan without camera identification — should fail for camera query",
        max_score=0.4,
    ),
    TestCase(
        name="timeout_error",
        query="sprawdź połączenie z serwerem",
        command="curl -s http://192.168.1.100:8080",
        output="curl: (28) Connection timed out after 30001 milliseconds",
        expected_verdict="fail",
        description="Connection timeout — should fail",
        max_score=0.2,
    ),

    # ── EDGE CASES ───────────────────────────────────────────────────────────
    TestCase(
        name="partial_output_camera",
        query="znajdz kamery podłączone do sieci lokalnej",
        command="nmap -p 554 --open 192.168.188.0/24",
        output="Nmap scan report for 192.168.188.50\n554/tcp open rtsp\nNmap done: 256 addresses scanned",
        expected_verdict="pass",
        description="Camera port found but no service identification — partial match, should pass with lower score",
        min_score=0.4,
        max_score=0.95,
    ),
    TestCase(
        name="multiple_cameras",
        query="znajdz kamery podłączone do sieci lokalnej",
        command="nmap -p 554,80 --open -sV 192.168.188.0/24 | grep -E '(camera|webcam|rtsp)'",
        output="554/tcp open rtsp    Hikvision DS-2CD2042WD rtspd\n80/tcp  open http    Axis 210 Network Camera httpd\n554/tcp open rtsp    Foscam FI9821W V2 rtspd",
        expected_verdict="pass",
        description="3 cameras found — should pass with high score and count 3 accurately",
        min_score=0.8,
    ),
    TestCase(
        name="warning_but_success",
        query="pokaż użycie dysku",
        command="df -h",
        output="Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1       100G   75G   25G  75% /\ntmpfs           7.8G  1.2M  7.8G   1% /dev/shm\n/dev/sdb1       500G  450G   50G  90% /data",
        expected_verdict="pass",
        description="Disk usage with high usage warning level — should still pass",
        min_score=0.7,
    ),
    TestCase(
        name="polish_special_chars",
        query="znajdź pliki zmodyfikowane w ostatnich 7 dniach",
        command="find . -type f -mtime -7",
        output="./src/główny.py\n./docs/ąęśćżźół.txt\n./testy/test_główny.py",
        expected_verdict="pass",
        description="Polish filenames with diacritics — should pass",
        min_score=0.7,
    ),
]


def run_tests(validator: LLMValidator) -> dict:
    """Run all test cases and return summary stats."""
    results = []
    passed = 0
    failed = 0
    errors = 0

    print(f"\n{'='*80}")
    print(f"  LLM Validator Test Suite — model: {validator.model}")
    print(f"{'='*80}\n")

    for i, tc in enumerate(TESTS, 1):
        print(f"[{i:2d}/{len(TESTS)}] {tc.name}: ", end="", flush=True)
        start = time.time()

        try:
            verdict = validator.validate(
                query=tc.query,
                command=tc.command,
                output=tc.output,
            )
            elapsed = time.time() - start

            verdict_ok = verdict.verdict == tc.expected_verdict
            score_ok = True
            score_note = ""

            if tc.min_score is not None and verdict.score < tc.min_score:
                score_ok = False
                score_note += f" (score {verdict.score:.2f} < min {tc.min_score})"
            if tc.max_score is not None and verdict.score > tc.max_score:
                score_ok = False
                score_note += f" (score {verdict.score:.2f} > max {tc.max_score})"

            ok = verdict_ok and score_ok

            status = "✅ PASS" if ok else "❌ FAIL"
            if ok:
                passed += 1
            else:
                failed += 1

            print(f"{status}  verdict={verdict.verdict} (expected={tc.expected_verdict})  "
                  f"score={verdict.score:.2f}  {elapsed:.1f}s{score_note}")
            if not verdict_ok:
                print(f"       ↳ MISMATCH: got verdict={verdict.verdict}, expected={tc.expected_verdict}")
            print(f"       ↳ reason: {verdict.reason}")

            results.append({
                "name": tc.name,
                "ok": ok,
                "verdict": verdict.verdict,
                "expected": tc.expected_verdict,
                "verdict_match": verdict_ok,
                "score": verdict.score,
                "score_ok": score_ok,
                "reason": verdict.reason,
                "elapsed_s": round(elapsed, 2),
            })

        except Exception as e:
            errors += 1
            print(f"💥 ERROR: {e}")
            results.append({
                "name": tc.name,
                "ok": False,
                "error": str(e),
            })

    total = len(TESTS)
    accuracy = passed / total * 100 if total else 0

    print(f"\n{'='*80}")
    print(f"  Results: {passed}/{total} passed ({accuracy:.0f}%)  |  {failed} failed  |  {errors} errors")
    print(f"{'='*80}\n")

    summary = {
        "model": validator.model,
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "accuracy_pct": round(accuracy, 1),
        "results": results,
    }

    # Write results to JSON
    out_path = Path(__file__).parent / "test_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Results saved to {out_path}\n")

    return summary


def main():
    validator = LLMValidator()

    if not validator.is_available:
        print("ERROR: Ollama is not running. Start it with: ollama serve")
        sys.exit(1)

    print(f"Validator: model={validator.model}, enabled={validator.enabled}")
    summary = run_tests(validator)

    # Exit with error code if accuracy is below threshold
    if summary["accuracy_pct"] < 70:
        print(f"⚠️  Accuracy {summary['accuracy_pct']}% is below 70% threshold")
        sys.exit(1)
    else:
        print(f"✅ Accuracy {summary['accuracy_pct']}% meets threshold")


if __name__ == "__main__":
    main()
