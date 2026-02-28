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

import json
import os
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
- "reason" must be a single concise sentence (max 120 chars).
- "pass" means: the output clearly addresses what the user asked for.
- "fail" means: the output is empty, contains errors, or is unrelated to the user's request.

Response format:
{"verdict": "pass", "score": 0.9, "reason": "Found 2 cameras on the local network."}
"""

_USER_TEMPLATE = """\
User request: {query}

Command executed: {command}

Command output:
{output}

Does the output satisfy the user's request? Respond with JSON only.
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

        user_message = _USER_TEMPLATE.format(
            query=query,
            command=command,
            output=trimmed_output,
        )

        _debug(f"Validating: query={query!r}, command={command!r}, output_len={len(output)}")

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

        return self._parse_response(raw)

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
