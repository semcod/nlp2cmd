"""
LLM Validator for NLP2CMD.

Validates whether a command's output satisfies the user's original intent,
using a local Ollama model (default: qwen2.5:3b).

Input:  user_query + command + command_output
Output: verdict (pass/fail), reason, score

Environment:
    LLM_VALIDATOR_ENABLED   — enable/disable (default: true)
    LLM_VALIDATOR_MODEL     — Ollama model (default: qwen2.5:3b)
    LLM_VALIDATOR_BASE_URL  — Ollama base URL (default: http://localhost:11434)
    LLM_VALIDATOR_TIMEOUT   — request timeout seconds (default: 30)
    LLM_VALIDATOR_TEMPERATURE — sampling temperature (default: 0.1)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Optional

_DEBUG = os.environ.get("NLP2CMD_DEBUG", "").lower() in ("1", "true", "yes")


def _debug(msg: str) -> None:
    if _DEBUG:
        print(f"DEBUG [LLMValidator] {msg}", file=sys.stderr, flush=True)


@dataclass
class ValidationVerdict:
    """Result from LLM validator."""
    verdict: str          # "pass" or "fail"
    reason: str           # short explanation
    score: float          # 0.0 (complete failure) – 1.0 (perfect match)
    model: str = ""
    skipped: bool = False # True when validator is disabled or unavailable

    @property
    def passed(self) -> bool:
        return self.verdict == "pass"


_SYSTEM_PROMPT = """\
You are a strict output validator for a shell command assistant.
Your task: decide whether the command output satisfies the user's original intent.

Rules:
- Reply with ONLY valid JSON, no markdown, no explanation outside the JSON.
- "verdict" must be exactly "pass" or "fail".
- "score" must be a float between 0.0 and 1.0.
- "reason" must be a single factually accurate sentence (max 120 chars).
- Be precise: count items in the output carefully. Do NOT guess or hallucinate counts.
- "pass" means: the output clearly addresses what the user asked for.
- "fail" means: the output is empty, contains errors, or is unrelated to the user's request.
- If the command succeeded but the output is only partial, use score 0.5-0.8.

Runtime context:
- You will be given dynamic hints derived from the command and its stdout/stderr.
- Use those hints to judge relevance; do not rely on generic assumptions.

Response format (example only — do NOT copy these values, analyze the actual output):
{"verdict": "pass", "score": 0.85, "reason": "Command output contains relevant results matching the request."}
"""

_USER_TEMPLATE = """\
User request: {query}

Command executed: {command}

Command output (analyze carefully, count items precisely):
{output}

Context hints (derived from command + output):
{hints}

Instructions:
1. Read the output line by line. Each non-empty line with data is a result.
2. Check: does the output contain information related to the user's request?
3. If file paths, port numbers, process info, or other data rows appear, the command likely succeeded.
4. If error messages ("not found", "denied", "timeout") appear, the command failed.
5. Respond with JSON only — no markdown, no extra text.
"""


class LLMValidator:
    """
    Validates command output against user intent using a local Ollama model.

    Usage:
        validator = LLMValidator()
        verdict = validator.validate(
            query="find cameras on local network",
            command="nmap -p 80,554 --open 192.168.1.0/24",
            output="554/tcp open rtsp D-Link webcam",
        )
        if not verdict.passed:
            print(f"Validation failed: {verdict.reason}")
    """

    DEFAULT_MODEL = "qwen2.5:3b"
    DEFAULT_BASE_URL = "http://localhost:11434"
    DEFAULT_TIMEOUT = 30
    DEFAULT_TEMPERATURE = 0.1
    MAX_OUTPUT_CHARS = 4000  # trim very long outputs before sending
    _VERDICT_CACHE_MAX = 256
    _ERROR_INDICATORS = (
        "command not found", "permission denied", "no such file",
        "connection refused", "timed out", "error:", "fatal:",
        "traceback", "exception", "segfault", "core dumped",
    )
    _CAMERA_QUERY_WORDS = ("camera", "kamera", "kamery", "webcam")
    # Query signals that indicate a specific domain — used to detect mismatches
    # between what the user asked for and what the command actually does.
    _QUERY_DOMAIN_SIGNALS: dict[str, tuple[str, ...]] = {
        "network_scan": ("kamer", "camera", "webcam", "skan", "scan", "sieć", "siec", "network", "nmap", "port"),
        "file_listing": ("plik", "file", "katalog", "folder", "dir", "list", "pokaż plik", "pokaz plik"),
        "disk_usage": ("dysk", "disk", "miejsc", "space", "użyci", "uzyci", "usage"),
        "process": ("proces", "process", "pamięć", "pamiec", "memory", "cpu"),
    }
    _CMD_EXPECTED_DOMAINS: dict[str, tuple[str, ...]] = {
        "ls": ("file_listing",),
        "df": ("disk_usage",),
        "du": ("disk_usage",),
        "ps": ("process",),
    }

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        temperature: Optional[float] = None,
        enabled: Optional[bool] = None,
    ):
        self.enabled = enabled if enabled is not None else (
            os.environ.get("LLM_VALIDATOR_ENABLED", "true").lower() not in ("0", "false", "no")
        )
        self.model = model or os.environ.get("LLM_VALIDATOR_MODEL", self.DEFAULT_MODEL)
        self.base_url = (base_url or os.environ.get("LLM_VALIDATOR_BASE_URL", self.DEFAULT_BASE_URL)).rstrip("/")
        self.timeout = timeout or int(os.environ.get("LLM_VALIDATOR_TIMEOUT", str(self.DEFAULT_TIMEOUT)))
        self.temperature = temperature if temperature is not None else float(
            os.environ.get("LLM_VALIDATOR_TEMPERATURE", str(self.DEFAULT_TEMPERATURE))
        )
        self._verdict_cache: dict[str, ValidationVerdict] = {}

    @property
    def is_available(self) -> bool:
        """Quick check whether Ollama is reachable (no model pull required)."""
        try:
            import urllib.request
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=3) as r:
                return r.status == 200
        except Exception:
            return False

    def validate(
        self,
        query: str,
        command: str,
        output: str,
    ) -> ValidationVerdict:
        """
        Validate whether command output satisfies user intent.

        Args:
            query:   Original user natural-language request.
            command: The shell command that was executed.
            output:  Combined stdout + stderr from the command (trimmed internally).

        Returns:
            ValidationVerdict with verdict, reason, and score.
        """
        if not self.enabled:
            _debug("Validator disabled via LLM_VALIDATOR_ENABLED=false")
            return ValidationVerdict(verdict="pass", reason="Validator disabled", score=1.0, skipped=True)

        if not output.strip():
            return ValidationVerdict(
                verdict="fail",
                reason="Command produced no output",
                score=0.0,
                model=self.model,
            )

        trimmed_output = output[:self.MAX_OUTPUT_CHARS]
        if len(output) > self.MAX_OUTPUT_CHARS:
            trimmed_output += f"\n... [truncated, {len(output)} chars total]"

        # ── Cache check ──────────────────────────────────────────────────
        cache_key = self._cache_key(query, command, trimmed_output)
        if cache_key in self._verdict_cache:
            cached = self._verdict_cache[cache_key]
            _debug(f"Cache hit: {cached.verdict}/{cached.score}")
            return cached

        # ── Deterministic pre-check (skip LLM for clear-cut cases) ───────
        det = self._deterministic_pre_check(query, command, trimmed_output)
        if det is not None:
            _debug(f"Deterministic: {det.verdict}/{det.score} — {det.reason}")
            self._cache_put(cache_key, det)
            return det

        # ── LLM validation (fallback for ambiguous cases) ────────────────
        hints = self._build_dynamic_hints(query=query, command=command, output=trimmed_output)

        user_message = _USER_TEMPLATE.format(
            query=query,
            command=command,
            output=trimmed_output,
            hints=hints,
        )

        _debug(f"Validating via LLM: query={query!r}, command={command!r}, output_len={len(output)}")

        raw = self._call_ollama(user_message)
        if raw is None:
            _debug("Ollama unavailable, skipping validation")
            return ValidationVerdict(
                verdict="pass",
                reason="Validator unavailable (Ollama not running)",
                score=1.0,
                model=self.model,
                skipped=True,
            )

        verdict = self._parse_response(raw)

        # Sanity check: small LLMs sometimes score 0.0 on valid output
        if not verdict.passed and verdict.score < 0.1:
            verdict = self._sanity_check_verdict(verdict, trimmed_output)

        self._cache_put(cache_key, verdict)
        return verdict

    # ── Verdict cache helpers ────────────────────────────────────────────

    def _cache_key(self, query: str, command: str, output: str) -> str:
        blob = f"{query}||{command}||{output[:500]}"
        return hashlib.md5(blob.encode("utf-8", errors="replace")).hexdigest()

    def _cache_put(self, key: str, verdict: ValidationVerdict) -> None:
        if len(self._verdict_cache) >= self._VERDICT_CACHE_MAX:
            # Evict oldest entry (FIFO)
            oldest = next(iter(self._verdict_cache))
            del self._verdict_cache[oldest]
        self._verdict_cache[key] = verdict

    # ── Deterministic pre-check ──────────────────────────────────────────

    def _deterministic_pre_check(
        self, query: str, command: str, output: str,
    ) -> Optional[ValidationVerdict]:
        """Return a verdict without calling LLM for clear-cut cases.

        Returns None when uncertain — the caller should fall through to LLM.
        """
        out_lower = output.lower()
        cmd_lower = command.lower().strip()
        q_lower = query.lower()

        lines = [l.strip() for l in output.splitlines() if l.strip()]
        if not lines:
            return None  # empty already handled above

        has_errors = any(err in out_lower for err in self._ERROR_INDICATORS)

        # ── Auto-fail: output consists only of error messages ────────────
        if has_errors:
            non_error = [
                l for l in lines
                if not any(e in l.lower() for e in self._ERROR_INDICATORS)
            ]
            if not non_error:
                return ValidationVerdict(
                    verdict="fail",
                    reason="Output contains only error messages",
                    score=0.05,
                    model="deterministic",
                )
            return None  # mixed errors + data → uncertain

        # From here: no error indicators present
        _ca = lambda *needles: any(n in out_lower for n in needles)

        # ── ping ─────────────────────────────────────────────────────────
        if cmd_lower.startswith("ping ") or " ping " in f" {cmd_lower} ":
            if _ca("bytes from", "icmp_seq=", "ttl=", "packets transmitted"):
                return ValidationVerdict(
                    verdict="pass", reason="Ping reply received",
                    score=0.9, model="deterministic",
                )

        # ── nmap ─────────────────────────────────────────────────────────
        if cmd_lower.startswith("nmap ") or " nmap " in f" {cmd_lower} ":
            nmap_ok = _ca("/tcp", "open", "service info", "nmap scan report")
            is_camera_q = any(w in q_lower for w in self._CAMERA_QUERY_WORDS)
            if is_camera_q:
                camera_kw = _ca(
                    "rtsp", "webcam", "camera", "hikvision",
                    "axis", "foscam", "onvif", "dcs",
                )
                if nmap_ok and camera_kw:
                    return ValidationVerdict(
                        verdict="pass",
                        reason="Camera/webcam data found in nmap output",
                        score=0.85, model="deterministic",
                    )
                if nmap_ok and not camera_kw:
                    return ValidationVerdict(
                        verdict="fail",
                        reason="Nmap scan succeeded but no camera keywords in output",
                        score=0.2, model="deterministic",
                    )
            elif nmap_ok:
                return ValidationVerdict(
                    verdict="pass", reason="Nmap found open ports/services",
                    score=0.8, model="deterministic",
                )

        # ── find ─────────────────────────────────────────────────────────
        if cmd_lower.startswith("find ") or " find " in f" {cmd_lower} ":
            if lines and all(
                l.startswith("/") or l.startswith("./") for l in lines[:5]
            ):
                return ValidationVerdict(
                    verdict="pass",
                    reason=f"Found {len(lines)} matching path(s)",
                    score=0.85, model="deterministic",
                )

        # ── Generic commands: ls, df, du, ps ─────────────────────────
        # These always produce "valid" output, so we must also check that
        # the query intent matches the command type.
        cmd_base = cmd_lower.split()[0] if cmd_lower else ""
        # Strip leading path (e.g. /usr/bin/ls → ls) and sudo
        cmd_base = cmd_base.rsplit("/", 1)[-1]
        if cmd_base == "sudo" and len(cmd_lower.split()) > 1:
            cmd_base = cmd_lower.split()[1].rsplit("/", 1)[-1]

        if cmd_base in self._CMD_EXPECTED_DOMAINS:
            if not self._query_matches_cmd_domain(q_lower, cmd_base):
                return None  # mismatch → let LLM decide

        if cmd_base == "ls":
            if lines:
                return ValidationVerdict(
                    verdict="pass", reason="Directory listing produced",
                    score=0.85, model="deterministic",
                )

        if cmd_base in ("df", "du"):
            if _ca("filesystem", "size", "mounted on", "use%", "/dev/"):
                return ValidationVerdict(
                    verdict="pass", reason="Disk usage data shown",
                    score=0.85, model="deterministic",
                )

        if cmd_base == "ps":
            if _ca("pid", "%cpu", "%mem", "command", "stat"):
                return ValidationVerdict(
                    verdict="pass", reason="Process listing shown",
                    score=0.85, model="deterministic",
                )

        return None  # uncertain → fall through to LLM

    def _query_matches_cmd_domain(self, q_lower: str, cmd_base: str) -> bool:
        """Check if the query intent is compatible with the command type.

        Returns True (compatible) when:
          - The query contains signals for the command's expected domain, OR
          - The query has no strong domain signals at all (generic query).
        Returns False when the query clearly belongs to a *different* domain.
        """
        expected_domains = self._CMD_EXPECTED_DOMAINS.get(cmd_base, ())
        if not expected_domains:
            return True

        # Detect which domains the query mentions
        query_domains: set[str] = set()
        for domain, signals in self._QUERY_DOMAIN_SIGNALS.items():
            if any(s in q_lower for s in signals):
                query_domains.add(domain)

        if not query_domains:
            return True  # no strong signals → assume compatible

        # If any expected domain is in the query domains, it's a match
        return bool(query_domains & set(expected_domains))

    def _build_dynamic_hints(self, query: str, command: str, output: str) -> str:
        """Build context hints for the prompt from command + stdout/stderr.

        The base prompt should describe only the goal. All concrete heuristics should
        be injected dynamically based on what we actually executed and observed.
        """
        cmd = (command or "").strip()
        out = output or ""
        out_lower = out.lower()
        q_lower = (query or "").lower()

        hints: list[str] = []

        # --- High-signal error indicators present in output ---
        present_errors = [e for e in self._ERROR_INDICATORS if e in out_lower]
        if present_errors:
            hints.append(
                "Error indicators detected in output: " + ", ".join(sorted(set(present_errors))[:6])
            )
        else:
            hints.append("No common error indicators detected in output.")

        # --- Rough output shape ---
        lines = [l for l in out.splitlines() if l.strip()]
        hints.append(f"Non-empty output lines: {len(lines)}")

        # --- Command-type specific signals ---
        cmd_lower = cmd.lower()

        def _contains_any(*needles: str) -> bool:
            return any(n in out_lower for n in needles)

        # ping
        if cmd_lower.startswith("ping ") or " ping " in f" {cmd_lower} ":
            ping_ok = _contains_any("bytes from", "icmp_seq=", "ttl=", "packets transmitted")
            hints.append(
                "Command type: ping. Success signals: bytes from / icmp_seq / ttl / packets transmitted. "
                + ("Detected." if ping_ok else "Not detected.")
            )

        # nmap
        if cmd_lower.startswith("nmap ") or " nmap " in f" {cmd_lower} ":
            nmap_ok = _contains_any("/tcp", "open", "service info", "nmap scan report")
            camera_kw = _contains_any("rtsp", "webcam", "camera", "hikvision", "axis", "foscam", "onvif", "dcs")
            hints.append(
                "Command type: nmap. Success signals: Nmap scan report / open ports / service info. "
                + ("Detected." if nmap_ok else "Not detected.")
            )
            if "camera" in q_lower or "kamera" in q_lower or "kamery" in q_lower:
                hints.append(
                    "Query looks like camera scan. Relevant signals: rtsp/webcam/camera vendor keywords and port 554. "
                    + ("Detected in output." if camera_kw else "Not detected in output.")
                )

        # find
        if cmd_lower.startswith("find ") or " find " in f" {cmd_lower} ":
            hints.append(
                "Command type: find. Each output line is typically a matching file path; listed paths imply a match."
            )
            if "-size" in cmd_lower:
                hints.append(
                    "find uses -size filter; paths listed should be treated as matching the size criteria."
                )

        # ls
        if cmd_lower.startswith("ls ") or cmd_lower == "ls" or " ls " in f" {cmd_lower} ":
            hints.append("Command type: ls. Output usually lists files/dirs; that typically satisfies 'list files'.")

        # df/du
        if cmd_lower.startswith("df ") or cmd_lower.startswith("du "):
            hints.append("Command type: df/du. Output is disk usage/size table; satisfies 'disk usage' queries.")

        # ps
        if cmd_lower.startswith("ps "):
            hints.append("Command type: ps. Output is process list; satisfies 'show processes' queries.")

        # curl
        if cmd_lower.startswith("curl "):
            hints.append("Command type: curl. Success is indicated by HTTP response content; failures include timeout/refused.")

        # --- Minimal keyword overlap hint ---
        overlap_terms = []
        for w in re.findall(r"[a-zA-Z]{3,}", q_lower):
            if w in out_lower and w not in overlap_terms:
                overlap_terms.append(w)
            if len(overlap_terms) >= 6:
                break
        if overlap_terms:
            hints.append("Query terms seen in output: " + ", ".join(overlap_terms))

        return "\n".join(f"- {h}" for h in hints)

    def _sanity_check_verdict(
        self, verdict: ValidationVerdict, output: str,
    ) -> ValidationVerdict:
        """Override clearly wrong fail/0.0 verdicts when output has real data."""
        lines = [l.strip() for l in output.strip().splitlines() if l.strip()]
        if not lines:
            return verdict

        output_lower = output.lower()
        if any(err in output_lower for err in self._ERROR_INDICATORS):
            return verdict

        # Detect self-contradiction: LLM says "no X found" but X is in output
        reason_lower = verdict.reason.lower()
        m = re.search(
            r'no\s+(?:relevant\s+)?(.+?)(?:\s+results?)?\s+found', reason_lower,
        )
        if m:
            kw_str = m.group(1)
            keywords = re.split(r'[/,\s]+', kw_str)
            keywords = [k.strip() for k in keywords if len(k.strip()) >= 3]
            for kw in keywords:
                if kw in output_lower:
                    _debug(
                        f"Sanity override: reason says 'no {kw} found' "
                        f"but '{kw}' appears in output → pass 0.6"
                    )
                    return ValidationVerdict(
                        verdict="pass",
                        reason=(
                            f"Output contains '{kw}' "
                            f"(LLM contradicted: {verdict.reason[:60]})"
                        ),
                        score=0.6,
                        model=verdict.model,
                    )

        return verdict

    def _call_ollama(self, user_message: str) -> Optional[str]:
        """Call Ollama generate API synchronously. Returns raw text or None on error."""
        try:
            import urllib.request

            payload = json.dumps({
                "model": self.model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": 200,
                },
            }).encode()

            req = urllib.request.Request(
                f"{self.base_url}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read())
                content = data.get("message", {}).get("content", "").strip()
                _debug(f"Ollama raw response: {content!r}")
                return content

        except Exception as e:
            _debug(f"Ollama call failed: {e}")
            return None

    def _parse_response(self, raw: str) -> ValidationVerdict:
        """Parse JSON verdict from LLM response."""
        try:
            # Strip potential markdown fences
            text = raw.strip()
            if text.startswith("```"):
                lines = text.splitlines()
                text = "\n".join(
                    ln for ln in lines
                    if not ln.strip().startswith("```")
                ).strip()

            data = json.loads(text)
            verdict = str(data.get("verdict", "fail")).lower()
            if verdict not in ("pass", "fail"):
                verdict = "fail"
            score = float(data.get("score", 0.5))
            score = max(0.0, min(1.0, score))
            reason = str(data.get("reason", ""))[:200]
            return ValidationVerdict(
                verdict=verdict,
                reason=reason,
                score=score,
                model=self.model,
            )
        except Exception as e:
            _debug(f"Failed to parse validator response: {e}, raw={raw!r}")
            # Heuristic fallback: look for "pass" or "fail" in text
            lower = raw.lower()
            if '"verdict": "pass"' in lower or "'verdict': 'pass'" in lower:
                return ValidationVerdict(verdict="pass", reason="LLM indicated pass", score=0.7, model=self.model)
            return ValidationVerdict(
                verdict="fail",
                reason=f"Could not parse validator response: {raw[:80]}",
                score=0.0,
                model=self.model,
            )
