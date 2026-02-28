"""
Step validation for multi-step browser automation plans.

Provides pre/post condition checking, clipboard validation,
DOM state verification, and metrics collection for each step
in an ActionPlan execution.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Optional

log = logging.getLogger("nlp2cmd.step_validator")


@dataclass
class StepMetrics:
    """Metrics collected during step execution."""

    step_index: int
    action: str
    started_at: float = 0.0
    finished_at: float = 0.0
    elapsed_ms: float = 0.0
    status: str = "pending"  # pending, ok, failed, skipped, retried
    error: str = ""
    pre_conditions_met: bool = True
    post_conditions_met: bool = True
    clipboard_before: str = ""
    clipboard_after: str = ""
    dom_state: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of a pre/post condition check."""

    passed: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    suggestion: str = ""  # What to do if validation failed


class StepValidator:
    """Validates pre/post conditions for ActionPlan steps.

    Checks clipboard state, DOM elements, environment variables,
    and other conditions before/after each step execution.
    """

    def __init__(self) -> None:
        self._metrics: list[StepMetrics] = []
        self._clipboard_cache: Optional[str] = None

    @property
    def metrics(self) -> list[StepMetrics]:
        return self._metrics

    def start_step(self, step_index: int, action: str) -> StepMetrics:
        """Start tracking a step."""
        m = StepMetrics(step_index=step_index, action=action, started_at=time.time())
        self._metrics.append(m)
        return m

    def finish_step(self, m: StepMetrics, status: str = "ok", error: str = "") -> None:
        """Finish tracking a step."""
        m.finished_at = time.time()
        m.elapsed_ms = (m.finished_at - m.started_at) * 1000
        m.status = status
        m.error = error

    # ------------------------------------------------------------------
    # Clipboard helpers
    # ------------------------------------------------------------------
    @staticmethod
    def get_clipboard() -> str:
        """Read current clipboard content (X11/Wayland)."""
        # Try wl-paste (Wayland) first, then xclip (X11)
        for cmd in [["wl-paste", "--no-newline"], ["xclip", "-selection", "clipboard", "-o"]]:
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=2,
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return ""

    @staticmethod
    def set_clipboard(text: str) -> bool:
        """Write text to clipboard."""
        for cmd in [["wl-copy"], ["xclip", "-selection", "clipboard"]]:
            try:
                result = subprocess.run(
                    cmd, input=text, capture_output=True, text=True, timeout=2,
                )
                if result.returncode == 0:
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return False

    def snapshot_clipboard(self) -> str:
        """Take a snapshot of clipboard content."""
        self._clipboard_cache = self.get_clipboard()
        return self._clipboard_cache

    def clipboard_changed(self) -> tuple[bool, str, str]:
        """Check if clipboard changed since last snapshot."""
        before = self._clipboard_cache or ""
        after = self.get_clipboard()
        return (before != after, before, after)

    # ------------------------------------------------------------------
    # Pre-condition validators
    # ------------------------------------------------------------------
    def validate_pre_navigate(self, params: dict) -> ValidationResult:
        """Validate before navigation step."""
        url = params.get("url", "")
        if not url:
            return ValidationResult(False, "No URL specified", suggestion="Add url parameter")
        if not url.startswith(("http://", "https://")):
            return ValidationResult(False, f"Invalid URL: {url}", suggestion="Add https:// prefix")
        return ValidationResult(True, f"URL ok: {url}")

    def validate_pre_check_session(self, page: Any, params: dict) -> ValidationResult:
        """Validate before session check — page must be loaded."""
        if page is None:
            return ValidationResult(
                False, "No page available for session check",
                suggestion="Navigate to the service URL first",
            )
        try:
            url = page.url
            if url == "about:blank":
                return ValidationResult(
                    False, "Page is blank — navigate first",
                    suggestion="Navigate to the service keys URL",
                )
        except Exception:
            pass
        return ValidationResult(True, "Page ready for session check")

    def validate_pre_extract_key(self, page: Any, params: dict) -> ValidationResult:  # noqa: params used for keys_url
        """Validate before key extraction — must be on correct page."""
        if page is None:
            return ValidationResult(False, "No page for key extraction")
        try:
            url = page.url
            keys_url = params.get("keys_url", "")
            if keys_url and keys_url not in url:
                return ValidationResult(
                    False, f"Not on keys page. Current: {url}, Expected: {keys_url}",
                    suggestion="Navigate to the keys URL first",
                )
        except Exception:
            pass
        # Snapshot clipboard before extraction
        self.snapshot_clipboard()
        return ValidationResult(True, "Ready for key extraction")

    def validate_pre_prompt_secret(self, variables: dict, params: dict) -> ValidationResult:
        """Validate before prompting for secret — check if already available."""
        env_var = params.get("env_var", "")
        key_pattern = str(params.get("key_pattern") or "").strip()
        # Check if key is already in environment
        existing = os.environ.get(env_var, "")
        if existing:
            if key_pattern and not re.match(key_pattern, existing.strip()):
                return ValidationResult(
                    True,
                    f"{env_var} already set but does NOT match expected pattern",
                    details={"already_set_invalid": True, "length": len(existing)},
                    suggestion="Existing value looks stale/invalid — will prompt user",
                )
            return ValidationResult(
                True, f"{env_var} already set in environment ({len(existing)} chars)",
                details={"already_set": True, "length": len(existing)},
            )
        # Check if key is in variables from previous extraction
        for k, v in variables.items():
            if v and k in ("extracted_key", "api_key"):
                return ValidationResult(
                    True, f"Key already extracted in step variable ${k}",
                    details={"already_extracted": True, "var": k},
                )
        return ValidationResult(True, "No existing key found — will prompt user")

    # ------------------------------------------------------------------
    # Post-condition validators
    # ------------------------------------------------------------------
    def validate_post_navigate(self, page: Any, params: dict) -> ValidationResult:
        """Validate after navigation — page loaded?"""
        if page is None:
            return ValidationResult(False, "No page after navigation")
        try:
            url = page.url
            expected = params.get("url", "")
            if expected and expected not in url:
                return ValidationResult(
                    False, f"URL mismatch: expected={expected}, got={url}",
                    suggestion="Page may have redirected. Check login status.",
                )
            title = page.title()
            return ValidationResult(
                True, f"Page loaded: {url}",
                details={"url": url, "title": title},
            )
        except Exception as e:
            return ValidationResult(False, f"Page check failed: {e}")

    def validate_post_check_session(
        self, _page: Any, params: dict, result: Optional[str]
    ) -> ValidationResult:
        """Validate after session check — is user logged in?"""
        if result == "logged_in":
            return ValidationResult(True, "User is logged in")
        if result == "needs_login":
            login_url = params.get("login_url", "")
            return ValidationResult(
                False, "User is NOT logged in",
                suggestion=f"Navigate to login page: {login_url}",
                details={"needs_login": True, "login_url": login_url},
            )
        return ValidationResult(
            True, f"Session check returned: {result}",
            details={"session_status": result},
        )

    def validate_post_extract_key(
        self, params: dict, result: Optional[str]
    ) -> ValidationResult:
        """Validate after key extraction — did we get a valid key?"""
        key_pattern = params.get("key_pattern", "")
        if result:
            if key_pattern and re.match(key_pattern, result):
                return ValidationResult(
                    True, f"Extracted key matches pattern ({len(result)} chars)",
                    details={"valid": True, "length": len(result)},
                )
            elif key_pattern:
                return ValidationResult(
                    False, f"Extracted key does NOT match pattern: {key_pattern}",
                    suggestion="Key may be truncated or incorrect. Try clipboard extraction.",
                    details={"valid": False, "pattern": key_pattern},
                )
            return ValidationResult(
                True, f"Key extracted ({len(result)} chars, no pattern to validate)",
            )

        # Check if clipboard changed (user may have copied manually)
        changed, _, after = self.clipboard_changed()
        if changed and after:
            if key_pattern and re.match(key_pattern, after):
                return ValidationResult(
                    True, f"Key found in clipboard ({len(after)} chars, matches pattern)",
                    details={"source": "clipboard", "valid": True},
                )
            elif after and len(after) > 10:
                return ValidationResult(
                    True, f"Clipboard changed ({len(after)} chars, no pattern match)",
                    details={"source": "clipboard", "value_length": len(after)},
                )

        return ValidationResult(
            False, "No key extracted and clipboard unchanged",
            suggestion="Try clicking 'Create' to generate a new key, or copy existing key manually.",
        )

    def validate_post_save_env(self, params: dict) -> ValidationResult:
        """Validate after saving to .env — does file contain the variable?"""
        var_name = params.get("var_name", "")
        file_path = params.get("file", ".env")

        if not var_name:
            return ValidationResult(False, "No var_name specified")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            if f"{var_name}=" in content:
                # Verify it's not empty
                for line in content.splitlines():
                    if line.startswith(f"{var_name}="):
                        value = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if value:
                            return ValidationResult(
                                True, f"{var_name} saved to {file_path} ({len(value)} chars)",
                            )
                        return ValidationResult(
                            False, f"{var_name} is empty in {file_path}",
                            suggestion="Key value was not captured. Re-run the extraction.",
                        )
            return ValidationResult(
                False, f"{var_name} not found in {file_path}",
                suggestion=f"Manually add: {var_name}=<your-key> to {file_path}",
            )
        except FileNotFoundError:
            return ValidationResult(
                False, f"File {file_path} does not exist",
                suggestion=f"Create {file_path} and add {var_name}=<your-key>",
            )

    # ------------------------------------------------------------------
    # Generic dispatcher
    # ------------------------------------------------------------------
    def validate_pre(self, action: str, page: Any, params: dict, variables: dict) -> ValidationResult:
        """Dispatch pre-condition validation based on action type."""
        validators = {
            "navigate": lambda: self.validate_pre_navigate(params),
            "check_session": lambda: self.validate_pre_check_session(page, params),
            "extract_key": lambda: self.validate_pre_extract_key(page, params),
            "prompt_secret": lambda: self.validate_pre_prompt_secret(variables, params),
        }
        validator = validators.get(action)
        if validator:
            return validator()
        return ValidationResult(True)

    def validate_post(
        self, action: str, page: Any, params: dict, result: Optional[str],
    ) -> ValidationResult:
        """Dispatch post-condition validation based on action type."""
        validators = {
            "navigate": lambda: self.validate_post_navigate(page, params),
            "check_session": lambda: self.validate_post_check_session(page, params, result),
            "extract_key": lambda: self.validate_post_extract_key(params, result),
            "save_env": lambda: self.validate_post_save_env(params),
        }
        validator = validators.get(action)
        if validator:
            return validator()
        return ValidationResult(True)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    def summary(self) -> dict[str, Any]:
        """Produce execution summary with metrics."""
        total = len(self._metrics)
        ok = sum(1 for m in self._metrics if m.status in ("ok", "retried"))
        failed = sum(1 for m in self._metrics if m.status == "failed")
        total_ms = sum(m.elapsed_ms for m in self._metrics)
        return {
            "total_steps": total,
            "ok": ok,
            "failed": failed,
            "total_ms": round(total_ms),
            "steps": [
                {
                    "index": m.step_index,
                    "action": m.action,
                    "status": m.status,
                    "elapsed_ms": round(m.elapsed_ms),
                    "pre_ok": m.pre_conditions_met,
                    "post_ok": m.post_conditions_met,
                    "error": m.error or None,
                }
                for m in self._metrics
            ],
        }
