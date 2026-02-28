"""
LLM Repair for NLP2CMD.

When the local LLM_VALIDATOR marks a result as failed, this module sends the
full context to a larger cloud model via OpenRouter to get:
  1. A better shell command to retry.
  2. Optional JSON patches for data/patterns.json and data/templates.json
     so the local rule-based pipeline learns from the mistake.

Environment:
    LLM_REPAIR_ENABLED      — enable/disable (default: true)
    LLM_REPAIR_MODEL        — OpenRouter model (default: qwen/qwen-2.5-coder-32b-instruct)
    LLM_REPAIR_API_KEY      — OpenRouter API key (falls back to OPENROUTER_API_KEY)
    LLM_REPAIR_TIMEOUT      — request timeout seconds (default: 60)
    LLM_REPAIR_TEMPERATURE  — sampling temperature (default: 0.2)
    LLM_REPAIR_MAX_TOKENS   — max tokens in response (default: 1500)
    LLM_REPAIR_DATA_DIR     — path to data/ directory for patching JSON files
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

_DEBUG = os.environ.get("NLP2CMD_DEBUG", "").lower() in ("1", "true", "yes")


def _debug(msg: str) -> None:
    if _DEBUG:
        print(f"DEBUG [LLMRepair] {msg}", file=sys.stderr, flush=True)


@dataclass
class RepairResult:
    """Result from LLM repair."""
    success: bool
    improved_command: Optional[str] = None   # better command to try
    reason: str = ""
    patches_applied: list[str] = field(default_factory=list)  # files patched
    model: str = ""
    skipped: bool = False
    error: Optional[str] = None


_SYSTEM_PROMPT = """\
You are an expert shell command assistant and a self-improvement engine for a
rule-based NLP-to-command pipeline.

A user ran a shell command generated from their natural language request and the
validator decided the output did NOT satisfy the user's intent.

Your tasks:
1. Provide an improved shell command that WILL produce a correct result.
2. Optionally provide JSON patches for the pipeline's data files so that the
   local model learns from this failure (patterns.json, templates.json).

RESPONSE FORMAT — reply with ONLY valid JSON (no markdown fences, no prose):

{
  "improved_command": "<shell command string>",
  "reason": "<one sentence: why the original failed and what you changed>",
  "patterns_patch": {
    "domain": "shell",
    "intent": "<intent_name>",
    "add_keywords": ["<kw1>", "<kw2>"]
  },
  "templates_patch": {
    "intent": "<intent_name>",
    "template": "<new template string with {placeholders}>"
  }
}

Rules:
- "improved_command" is REQUIRED and must be a single executable shell command.
- "patterns_patch" and "templates_patch" are OPTIONAL — include them only when
  there is a clear improvement to make to the pipeline data files.
- Do NOT add "```" or any markdown.
- Keep "reason" under 200 characters.
"""

_USER_TEMPLATE = """\
User request: {query}

Original command: {command}

Validator verdict: {verdict}
Validator reason: {validator_reason}

Full command output (stdout + stderr):
{full_output}

Provide an improved command and optional data patches as JSON.
"""


class LLMRepair:
    """
    Repairs failed commands and optionally patches data files using OpenRouter.

    Usage:
        repair = LLMRepair()
        result = repair.repair(
            query="find cameras on local network",
            command="nmap -sn 192.168.1.0/24",
            full_output="Starting Nmap... 6 hosts up",
            verdict="fail",
            validator_reason="Output lists all hosts, not only cameras",
        )
        if result.improved_command:
            print(result.improved_command)
    """

    DEFAULT_MODEL = "qwen/qwen-2.5-coder-32b-instruct"
    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
    DEFAULT_TIMEOUT = 60
    DEFAULT_TEMPERATURE = 0.2
    DEFAULT_MAX_TOKENS = 1500
    MAX_OUTPUT_CHARS = 8000

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        enabled: Optional[bool] = None,
        data_dir: Optional[str] = None,
    ):
        self.enabled = enabled if enabled is not None else (
            os.environ.get("LLM_REPAIR_ENABLED", "true").lower() not in ("0", "false", "no")
        )
        self.model = model or os.environ.get("LLM_REPAIR_MODEL", self.DEFAULT_MODEL)
        self.api_key = (
            api_key
            or os.environ.get("LLM_REPAIR_API_KEY")
            or os.environ.get("OPENROUTER_API_KEY")
        )
        self.timeout = timeout or int(os.environ.get("LLM_REPAIR_TIMEOUT", str(self.DEFAULT_TIMEOUT)))
        self.temperature = temperature if temperature is not None else float(
            os.environ.get("LLM_REPAIR_TEMPERATURE", str(self.DEFAULT_TEMPERATURE))
        )
        self.max_tokens = max_tokens or int(
            os.environ.get("LLM_REPAIR_MAX_TOKENS", str(self.DEFAULT_MAX_TOKENS))
        )

        # Locate data directory for JSON patching
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            env_dir = os.environ.get("LLM_REPAIR_DATA_DIR", "")
            if env_dir:
                self.data_dir = Path(env_dir)
            else:
                # Use the same data-file lookup the rest of the app uses
                try:
                    from nlp2cmd.utils.data_files import find_data_file
                    p = find_data_file(explicit_path=None, default_filename="patterns.json")
                    self.data_dir = p.parent if p else Path("data")
                except Exception:
                    self.data_dir = Path("data")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def repair(
        self,
        query: str,
        command: str,
        full_output: str,
        verdict: str = "fail",
        validator_reason: str = "",
    ) -> RepairResult:
        """
        Ask the cloud LLM for an improved command and optional data patches.

        Args:
            query:            Original user natural-language request.
            command:          The shell command that was executed.
            full_output:      Full stdout + stderr from the command.
            verdict:          Validator verdict string ("fail" etc.).
            validator_reason: Reason from the local validator.

        Returns:
            RepairResult with improved_command and patches_applied.
        """
        if not self.enabled:
            _debug("Repair disabled via LLM_REPAIR_ENABLED=false")
            return RepairResult(success=False, skipped=True, reason="Repair disabled")

        if not self.api_key:
            _debug("LLM_REPAIR_API_KEY / OPENROUTER_API_KEY not set")
            return RepairResult(
                success=False,
                skipped=True,
                reason="LLM_REPAIR_API_KEY not configured",
            )

        trimmed = full_output[:self.MAX_OUTPUT_CHARS]
        if len(full_output) > self.MAX_OUTPUT_CHARS:
            trimmed += f"\n... [truncated, {len(full_output)} chars total]"

        user_message = _USER_TEMPLATE.format(
            query=query,
            command=command,
            verdict=verdict,
            validator_reason=validator_reason,
            full_output=trimmed,
        )

        _debug(f"Calling repair model={self.model}, output_len={len(full_output)}")

        raw = self._call_openrouter(user_message)
        if raw is None:
            return RepairResult(
                success=False,
                error="OpenRouter call failed",
                reason="Could not reach repair LLM",
            )

        return self._parse_and_apply(raw)

    def _call_openrouter(self, user_message: str) -> Optional[str]:
        """Call OpenRouter synchronously. Returns raw text or None on error."""
        try:
            import urllib.request

            # Strip LiteLLM prefix if present (e.g. "openrouter/foo" → "foo")
            model_name = self.model
            if model_name.startswith("openrouter/"):
                model_name = model_name[len("openrouter/"):]

            body = json.dumps({
                "model": model_name,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            }).encode()

            req = urllib.request.Request(
                self.OPENROUTER_URL,
                data=body,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/wronai/nlp2cmd",
                    "X-Title": "NLP2CMD",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read())
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                _debug(f"OpenRouter raw response: {content[:200]!r}")
                return content

        except Exception as e:
            _debug(f"OpenRouter call failed: {e}")
            return None

    def _parse_and_apply(self, raw: str) -> RepairResult:
        """Parse repair JSON and apply optional data patches."""
        try:
            text = raw.strip()
            if text.startswith("```"):
                lines = text.splitlines()
                text = "\n".join(
                    ln for ln in lines if not ln.strip().startswith("```")
                ).strip()

            data: dict[str, Any] = json.loads(text)
        except Exception as e:
            _debug(f"Failed to parse repair JSON: {e}, raw={raw[:200]!r}")
            # Try to extract a command from the text heuristically
            for line in raw.splitlines():
                line = line.strip()
                if line and not line.startswith(("{", "}", "#", "//")):
                    return RepairResult(
                        success=True,
                        improved_command=line,
                        reason="Extracted command from unstructured response",
                        model=self.model,
                    )
            return RepairResult(
                success=False,
                error=f"Could not parse repair response: {raw[:100]}",
                reason="Repair LLM returned unparseable response",
            )

        improved_command = data.get("improved_command", "").strip()
        reason = str(data.get("reason", ""))[:200]
        patches_applied: list[str] = []

        # Apply patterns patch
        patterns_patch = data.get("patterns_patch")
        if isinstance(patterns_patch, dict):
            applied = self._apply_patterns_patch(patterns_patch)
            if applied:
                patches_applied.append("patterns.json")

        # Apply templates patch
        templates_patch = data.get("templates_patch")
        if isinstance(templates_patch, dict):
            applied = self._apply_templates_patch(templates_patch)
            if applied:
                patches_applied.append("templates.json")

        return RepairResult(
            success=bool(improved_command),
            improved_command=improved_command or None,
            reason=reason,
            patches_applied=patches_applied,
            model=self.model,
        )

    def _apply_patterns_patch(self, patch: dict[str, Any]) -> bool:
        """Add keywords to an intent in patterns.json."""
        patterns_file = self.data_dir / "patterns.json"
        if not patterns_file.exists():
            _debug(f"patterns.json not found at {patterns_file}")
            return False

        intent = patch.get("intent", "")
        add_keywords = patch.get("add_keywords", [])
        if not intent or not isinstance(add_keywords, list) or not add_keywords:
            return False

        try:
            with open(patterns_file, encoding="utf-8") as f:
                patterns: dict[str, Any] = json.load(f)

            # Find the intent under any domain
            def _find_and_patch(obj: Any) -> bool:
                if isinstance(obj, dict):
                    if intent in obj and isinstance(obj[intent], list):
                        existing = set(obj[intent])
                        new_kws = [kw for kw in add_keywords if kw not in existing]
                        if new_kws:
                            obj[intent].extend(new_kws)
                            _debug(f"Added {new_kws} to patterns intent '{intent}'")
                        return True
                    for v in obj.values():
                        if _find_and_patch(v):
                            return True
                return False

            if _find_and_patch(patterns):
                with open(patterns_file, "w", encoding="utf-8") as f:
                    json.dump(patterns, f, ensure_ascii=False, indent=2)
                return True

            _debug(f"Intent '{intent}' not found in patterns.json")
            return False
        except Exception as e:
            _debug(f"Failed to patch patterns.json: {e}")
            return False

    def _apply_templates_patch(self, patch: dict[str, Any]) -> bool:
        """Update or add a template in templates.json."""
        templates_file = self.data_dir / "templates.json"
        if not templates_file.exists():
            _debug(f"templates.json not found at {templates_file}")
            return False

        intent = patch.get("intent", "")
        template = patch.get("template", "")
        if not intent or not template:
            return False

        try:
            with open(templates_file, encoding="utf-8") as f:
                templates: dict[str, Any] = json.load(f)

            def _find_and_patch(obj: Any) -> bool:
                if isinstance(obj, dict):
                    if intent in obj:
                        old = obj[intent]
                        if old != template:
                            obj[intent] = template
                            _debug(f"Updated template for '{intent}': {template!r}")
                        return True
                    for v in obj.values():
                        if isinstance(v, dict) and _find_and_patch(v):
                            return True
                return False

            if _find_and_patch(templates):
                with open(templates_file, "w", encoding="utf-8") as f:
                    json.dump(templates, f, ensure_ascii=False, indent=2)
                return True

            _debug(f"Intent '{intent}' not found in templates.json — adding at top level")
            templates[intent] = template
            with open(templates_file, "w", encoding="utf-8") as f:
                json.dump(templates, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            _debug(f"Failed to patch templates.json: {e}")
            return False
