"""
Reflection & Result Analysis for the Orchestration Engine.

Provides LLM-driven analysis of execution results with:
- Output validation (is the result correct for the goal?)
- Error classification (what went wrong and why?)
- Repair suggestions (how to fix it?)
- Confidence scoring

This replaces hardcoded validation patterns with dynamic LLM reasoning.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ReflectionVerdict(Enum):
    """Outcome of result analysis."""
    VALID = "valid"
    INVALID = "invalid"
    ERROR = "error"
    PARTIAL = "partial"
    INCONCLUSIVE = "inconclusive"


@dataclass
class ReflectionResult:
    """Result of LLM-driven reflection on execution output."""
    verdict: ReflectionVerdict
    reason: str = ""
    confidence: float = 0.0
    suggestions: list[str] = field(default_factory=list)
    error_type: Optional[str] = None  # e.g. "syntax_error", "runtime_error"
    should_retry: bool = False
    retry_strategy: Optional[str] = None  # e.g. "regenerate_code", "fix_selector"


# ── Error signal detection (fast, no LLM needed) ────────────────────

_ERROR_SIGNALS = [
    "traceback (most recent call last)",
    "syntaxerror:", "indentationerror:", "nameerror:",
    "typeerror:", "valueerror:", "importerror:",
    "runtimeerror:", "zerodivisionerror:", "attributeerror:",
    "exit code 1", "exit code 2",
    "compilation error", "compile error",
    "segmentation fault", "core dumped",
    "uncaught exception", "referenceerror:",
    "fatal error",
    # Browser/page errors
    "404 not found", "page not found",
    "timed out", "connection timed out",
    "net::err_", "connection refused",
    "permission denied",
]


def has_error_signals(text: str) -> bool:
    """Fast check: does the text contain error patterns?"""
    if not text:
        return False
    tl = text.lower()
    return any(sig in tl for sig in _ERROR_SIGNALS)


def classify_error(text: str) -> Optional[str]:
    """Classify an error from output text (fast, no LLM)."""
    if not text:
        return None
    tl = text.lower()
    if "syntaxerror" in tl or "indentationerror" in tl:
        return "syntax_error"
    if "nameerror" in tl or "attributeerror" in tl:
        return "reference_error"
    if "typeerror" in tl or "valueerror" in tl:
        return "type_error"
    if "importerror" in tl or "modulenotfounderror" in tl:
        return "import_error"
    if "compilation error" in tl or "compile error" in tl:
        return "compilation_error"
    if "segmentation fault" in tl or "core dumped" in tl:
        return "crash"
    if "exit code 1" in tl or "exit code 2" in tl:
        return "nonzero_exit"
    if "traceback" in tl:
        return "runtime_error"
    # Browser/page errors
    if "404" in tl or "not found" in tl:
        return "page_not_found"
    if "timeout" in tl or "timed out" in tl:
        return "timeout"
    if "net::err" in tl or "connection refused" in tl:
        return "network_error"
    if "login" in tl and ("required" in tl or "sign in" in tl):
        return "login_required"
    if "captcha" in tl:
        return "captcha_blocked"
    if "permission" in tl and "denied" in tl:
        return "permission_denied"
    return None


# ── Retry strategy recommender ───────────────────────────────────────

_RETRY_STRATEGIES: dict[str, str] = {
    "syntax_error": "regenerate_code",
    "reference_error": "regenerate_code",
    "type_error": "regenerate_code",
    "import_error": "regenerate_code",
    "compilation_error": "regenerate_code",
    "runtime_error": "regenerate_code",
    "crash": "regenerate_code",
    "nonzero_exit": "rerun",
    "page_not_found": "discover_url",
    "timeout": "wait_longer",
    "network_error": "retry_with_backoff",
    "login_required": "switch_site",
    "captcha_blocked": "switch_site",
    "permission_denied": "switch_site",
}


def suggest_retry_strategy(error_type: Optional[str]) -> str:
    """Suggest a retry strategy based on error classification."""
    if not error_type:
        return "rerun"
    return _RETRY_STRATEGIES.get(error_type, "rerun")


# ── ResultAnalyzer (LLM-driven reflection) ───────────────────────────

class ResultAnalyzer:
    """Analyzes execution results using LLM for intelligent reflection.

    Replaces hardcoded FeedbackLoop correction rules with dynamic reasoning.
    Falls back to heuristic analysis when LLM is unavailable.
    """

    def __init__(self, router=None):
        """
        Args:
            router: LLMRouter instance (lazy-loaded if None).
        """
        self._router = router
        self._auto_init_router = router is None

    @property
    def router(self):
        if self._router is None and self._auto_init_router:
            try:
                from nlp2cmd.llm.router import LLMRouter
                self._router = LLMRouter()
            except Exception:
                pass
            self._auto_init_router = False  # only try once
        return self._router

    async def analyze(
        self,
        goal: str,
        output: str,
        context: Optional[dict[str, Any]] = None,
    ) -> ReflectionResult:
        """Analyze execution output against the original goal.

        Args:
            goal: What the user wanted to achieve.
            output: Captured execution output.
            context: Additional context (generated code, page schema, etc.)

        Returns:
            ReflectionResult with verdict, reason, and repair suggestions.
        """
        # Fast path: detect obvious errors without LLM
        if has_error_signals(output):
            err_type = classify_error(output)
            strategy = suggest_retry_strategy(err_type)
            return ReflectionResult(
                verdict=ReflectionVerdict.ERROR,
                reason=f"Error detected in output: {err_type or 'unknown'}",
                confidence=0.95,
                error_type=err_type,
                should_retry=True,
                retry_strategy=strategy,
            )

        # No output when expected
        if not output.strip():
            return ReflectionResult(
                verdict=ReflectionVerdict.INVALID,
                reason="Empty output",
                confidence=0.8,
                should_retry=True,
                retry_strategy="wait_longer",
            )

        # LLM validation
        if self.router:
            return await self._llm_validate(goal, output, context)

        # Heuristic fallback
        return self._heuristic_validate(goal, output)

    async def suggest_repair(
        self,
        goal: str,
        output: str,
        code: str = "",
        error_type: Optional[str] = None,
    ) -> Optional[str]:
        """Ask LLM to suggest a repair strategy.

        Returns a natural-language description of what to fix.
        """
        if not self.router:
            return None

        prompt = (
            f"A program failed. Goal: \"{goal}\"\n"
            f"Error type: {error_type or 'unknown'}\n"
            f"Output:\n{output[:1000]}\n"
        )
        if code:
            prompt += f"Code:\n{code[:1000]}\n"
        prompt += (
            "\nSuggest ONE specific fix. Be concise (1-2 sentences). "
            "Respond with ONLY the suggestion."
        )

        try:
            resp = await self.router.completion(
                prompt, task="repair", max_tokens=200, temperature=0.2,
            )
            if resp.success:
                return resp.content.strip()
        except Exception as exc:
            logger.debug("Repair suggestion failed: %s", exc)
        return None

    # ── Private ──────────────────────────────────────────────────────

    async def _llm_validate(
        self,
        goal: str,
        output: str,
        context: Optional[dict[str, Any]],
    ) -> ReflectionResult:
        """Use LLM to validate output against goal."""
        prompt = (
            "You are validating program output. Be lenient.\n\n"
            f'Goal: "{goal}"\n'
            f"Output:\n{output[:2000]}\n\n"
            "Rules:\n"
            "- Output related to the goal with no error → valid\n"
            "- Error traceback or crash → error\n"
            "- Partially correct → partial\n"
            "- Empty when output expected → invalid\n\n"
            'Respond ONLY with JSON: '
            '{"verdict":"valid|invalid|error|partial",'
            '"reason":"...","confidence":0.0-1.0}'
        )

        try:
            resp = await self.router.completion(
                prompt, task="validation", max_tokens=300, temperature=0.1,
            )
            if resp.success:
                data = _parse_json_safe(resp.content)
                if data:
                    verdict_str = data.get("verdict", "inconclusive")
                    try:
                        verdict = ReflectionVerdict(verdict_str)
                    except ValueError:
                        verdict = ReflectionVerdict.INCONCLUSIVE

                    should_retry = verdict in (
                        ReflectionVerdict.ERROR,
                        ReflectionVerdict.INVALID,
                    )
                    return ReflectionResult(
                        verdict=verdict,
                        reason=data.get("reason", ""),
                        confidence=float(data.get("confidence", 0.5)),
                        should_retry=should_retry,
                    )
        except Exception as exc:
            logger.debug("LLM validation failed: %s", exc)

        return self._heuristic_validate(goal, output)

    @staticmethod
    def _heuristic_validate(goal: str, output: str) -> ReflectionResult:
        """Fallback validation without LLM."""
        # If output is non-empty and has no error signals, assume valid
        if output.strip() and not has_error_signals(output):
            return ReflectionResult(
                verdict=ReflectionVerdict.VALID,
                reason="Output present, no errors detected (heuristic)",
                confidence=0.6,
            )
        return ReflectionResult(
            verdict=ReflectionVerdict.INCONCLUSIVE,
            reason="Cannot determine validity without LLM",
            confidence=0.3,
        )


def _parse_json_safe(text: str) -> Optional[dict]:
    """Try to parse JSON from LLM response, tolerating preamble."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Find first { and match
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        if depth == 0:
            try:
                return json.loads(text[start:i + 1])
            except json.JSONDecodeError:
                return None
    return None
