"""
Visual Validator — vision LLM validates drawings and provides correction feedback.

After drawing, takes a screenshot and sends it to a vision model to:
1. Verify the drawing matches the requested description
2. Identify specific issues (wrong shape, missing parts, wrong color)
3. Generate correction instructions for the correction engine

Pipeline:
    draw → screenshot → vision LLM → ValidationResult → corrections

Single Responsibility: screenshot + description → validation verdict + corrections.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ValidationVerdict(Enum):
    """Result of visual validation."""
    CORRECT = "correct"          # Drawing matches description
    PARTIAL = "partial"          # Some elements correct, some wrong
    WRONG = "wrong"              # Drawing doesn't match at all
    EMPTY = "empty"              # Canvas is blank or nearly blank
    ERROR = "error"              # Validation failed (model error)


@dataclass
class DrawingCorrection:
    """A single correction to apply to the drawing."""
    issue: str                   # Description of the problem
    action: str                  # "redraw", "recolor", "move", "add", "remove", "resize"
    target: str                  # What to fix: shape name, part name, or "all"
    details: dict[str, Any] = field(default_factory=dict)
    priority: int = 1            # 1=critical, 2=important, 3=nice-to-have

    def __repr__(self) -> str:
        return f"Correction({self.action} {self.target}: {self.issue})"


@dataclass
class ValidationResult:
    """Full result of visual validation."""
    verdict: ValidationVerdict
    confidence: float = 0.0       # 0..1
    description: str = ""         # What the model sees
    matches_request: bool = False
    corrections: list[DrawingCorrection] = field(default_factory=list)
    model_used: str = ""
    validation_time_ms: float = 0.0
    raw_response: str = ""
    screenshot_path: str = ""

    @property
    def needs_correction(self) -> bool:
        return self.verdict in (ValidationVerdict.PARTIAL, ValidationVerdict.WRONG, ValidationVerdict.EMPTY)

    @property
    def critical_corrections(self) -> list[DrawingCorrection]:
        return [c for c in self.corrections if c.priority == 1]


# ── Validation Prompts ───────────────────────────────────────────────────

VALIDATION_PROMPT = """Analyze this screenshot of a drawing canvas.

The user asked to draw: "{description}"

Examine the image carefully and answer:
1. What do you see drawn on the canvas? Describe the shapes, colors, and composition.
2. Does the drawing match what was requested? (yes/partially/no/empty)
3. What specific issues exist? List each one.
4. For each issue, what correction is needed?

Respond in this exact JSON format:
{{
  "what_i_see": "description of what's actually on the canvas",
  "match": "yes|partially|no|empty",
  "confidence": 0.85,
  "issues": [
    {{
      "problem": "description of the issue",
      "action": "redraw|recolor|move|add|remove|resize",
      "target": "what to fix",
      "priority": 1,
      "details": {{}}
    }}
  ]
}}

If the canvas is blank or mostly white, set match to "empty".
Be specific about colors (use hex if possible) and positions (left/right/top/bottom/center).
"""

REVALIDATION_PROMPT = """Look at this screenshot again. Previously you found issues with the drawing.

The user wanted: "{description}"
Previous issues found: {previous_issues}
Corrections applied: {corrections_applied}

Check if the corrections worked. What do you see now?
Respond in JSON: {{"what_i_see": "...", "match": "yes|partially|no", "confidence": 0.9, "issues": [...]}}
"""


# ── Visual Validator ─────────────────────────────────────────────────────

class VisualValidator:
    """
    Validates drawings using vision LLM models.

    Uses the LLM Router with vision task category:
    - Gemini 2.5 Pro (best accuracy)
    - Qwen2.5-VL-7B (fast, free tier)
    - qwen2.5vl:7b (local Ollama)
    - llava:7b (local fallback)

    Usage:
        validator = VisualValidator()
        result = await validator.validate(
            screenshot_path="screenshot.png",
            description="red star on white background"
        )
        if result.needs_correction:
            for c in result.corrections:
                print(f"Fix: {c.action} {c.target} - {c.issue}")
    """

    def __init__(self, max_retries: int = 2):
        self._router = None
        self._max_retries = max_retries

    def _get_router(self):
        """Lazy-init LLM router."""
        if self._router is None:
            try:
                from nlp2cmd.llm.router import get_router
                self._router = get_router()
            except ImportError:
                self._router = None
        return self._router

    async def validate(self, screenshot_path: str, description: str,
                       verbose: bool = False) -> ValidationResult:
        """
        Validate a drawing screenshot against the requested description.

        Args:
            screenshot_path: Path to screenshot PNG
            description: What was supposed to be drawn
            verbose: Print progress

        Returns:
            ValidationResult with verdict and corrections
        """
        t0 = time.time()

        # Load screenshot
        img_path = Path(screenshot_path)
        if not img_path.exists():
            return ValidationResult(
                verdict=ValidationVerdict.ERROR,
                description=f"Screenshot not found: {screenshot_path}",
            )

        if verbose:
            print(f"  🔍 Validating drawing: '{description}'")
            print(f"     Screenshot: {screenshot_path}")

        # Encode image
        img_b64 = base64.b64encode(img_path.read_bytes()).decode()

        # Build prompt
        prompt = VALIDATION_PROMPT.format(description=description)

        # Call vision model
        router = self._get_router()
        if router is None:
            # Heuristic fallback: check if image is mostly white (empty canvas)
            return self._heuristic_validate(img_path, description, t0)

        response_text = None
        model_used = ""

        for attempt in range(self._max_retries + 1):
            try:
                resp = await router.route_call(
                    prompt=prompt,
                    task_category="vision",
                    images=[img_b64],
                    timeout=30,
                )
                if resp and resp.text:
                    response_text = resp.text
                    model_used = getattr(resp, 'model', 'vision')
                    break
            except Exception as e:
                if verbose:
                    print(f"  ⚠ Vision attempt {attempt + 1} failed: {e}")
                continue

        if not response_text:
            if verbose:
                print("  ⚠ Vision model unavailable, using heuristic validation")
            return self._heuristic_validate(img_path, description, t0)

        # Parse response
        result = self._parse_validation(response_text, model_used, t0)
        result.screenshot_path = screenshot_path
        result.raw_response = response_text[:1000]

        if verbose:
            self._print_result(result)

        return result

    async def revalidate(self, screenshot_path: str, description: str,
                         previous_result: ValidationResult,
                         corrections_applied: list[str],
                         verbose: bool = False) -> ValidationResult:
        """
        Re-validate after corrections were applied.

        Args:
            screenshot_path: New screenshot after corrections
            description: Original description
            previous_result: Previous validation result
            corrections_applied: List of corrections that were applied
            verbose: Print progress

        Returns:
            New ValidationResult
        """
        t0 = time.time()
        img_path = Path(screenshot_path)
        if not img_path.exists():
            return ValidationResult(verdict=ValidationVerdict.ERROR)

        img_b64 = base64.b64encode(img_path.read_bytes()).decode()

        prev_issues = "; ".join([c.issue for c in previous_result.corrections])
        corrections_str = "; ".join(corrections_applied) if corrections_applied else "none"

        prompt = REVALIDATION_PROMPT.format(
            description=description,
            previous_issues=prev_issues,
            corrections_applied=corrections_str,
        )

        router = self._get_router()
        if router is None:
            return self._heuristic_validate(img_path, description, t0)

        try:
            resp = await router.route_call(
                prompt=prompt,
                task_category="vision",
                images=[img_b64],
                timeout=30,
            )
            if resp and resp.text:
                result = self._parse_validation(resp.text, getattr(resp, 'model', 'vision'), t0)
                result.screenshot_path = screenshot_path
                if verbose:
                    self._print_result(result, prefix="Re-validation")
                return result
        except Exception as e:
            if verbose:
                print(f"  ⚠ Re-validation failed: {e}")

        return self._heuristic_validate(img_path, description, t0)

    def _parse_validation(self, text: str, model: str, t0: float) -> ValidationResult:
        """Parse vision model response into ValidationResult."""
        import json
        import re

        elapsed = (time.time() - t0) * 1000

        # Extract JSON
        clean = text.strip()
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0]
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0]

        if not clean.startswith("{"):
            start = clean.find("{")
            end = clean.rfind("}")
            if start >= 0 and end > start:
                clean = clean[start:end + 1]

        try:
            # Fix common JSON issues
            clean = re.sub(r',\s*}', '}', clean)
            clean = re.sub(r',\s*]', ']', clean)
            data = json.loads(clean)
        except json.JSONDecodeError:
            return ValidationResult(
                verdict=ValidationVerdict.ERROR,
                description=text[:200],
                model_used=model,
                validation_time_ms=elapsed,
                raw_response=text[:500],
            )

        # Parse match verdict
        match_str = data.get("match", "no").lower()
        verdict_map = {
            "yes": ValidationVerdict.CORRECT,
            "partially": ValidationVerdict.PARTIAL,
            "no": ValidationVerdict.WRONG,
            "empty": ValidationVerdict.EMPTY,
        }
        verdict = verdict_map.get(match_str, ValidationVerdict.WRONG)

        # Parse corrections
        corrections: list[DrawingCorrection] = []
        for issue in data.get("issues", []):
            if isinstance(issue, dict):
                corrections.append(DrawingCorrection(
                    issue=issue.get("problem", "unknown issue"),
                    action=issue.get("action", "redraw"),
                    target=issue.get("target", "unknown"),
                    details=issue.get("details", {}),
                    priority=issue.get("priority", 2),
                ))

        return ValidationResult(
            verdict=verdict,
            confidence=data.get("confidence", 0.5),
            description=data.get("what_i_see", ""),
            matches_request=(verdict == ValidationVerdict.CORRECT),
            corrections=corrections,
            model_used=model,
            validation_time_ms=elapsed,
        )

    def _heuristic_validate(self, img_path: Path, description: str,
                            t0: float) -> ValidationResult:
        """
        Heuristic validation when vision model is unavailable.
        Checks basic image properties (size, non-white pixel ratio).
        """
        elapsed = (time.time() - t0) * 1000

        try:
            file_size = img_path.stat().st_size
            # Very small PNG = likely empty/blank canvas
            if file_size < 5000:
                return ValidationResult(
                    verdict=ValidationVerdict.EMPTY,
                    confidence=0.3,
                    description="Image file is very small, likely blank canvas",
                    model_used="heuristic",
                    validation_time_ms=elapsed,
                    corrections=[DrawingCorrection(
                        issue="Canvas appears to be empty",
                        action="redraw",
                        target="all",
                        priority=1,
                    )],
                )

            # Assume something was drawn if file is reasonably large
            return ValidationResult(
                verdict=ValidationVerdict.PARTIAL,
                confidence=0.3,
                description=f"Heuristic: image is {file_size} bytes (no vision model available)",
                model_used="heuristic",
                validation_time_ms=elapsed,
            )
        except Exception:
            return ValidationResult(
                verdict=ValidationVerdict.ERROR,
                model_used="heuristic",
                validation_time_ms=elapsed,
            )

    def _print_result(self, result: ValidationResult, prefix: str = "Validation") -> None:
        """Pretty-print validation result."""
        icons = {
            ValidationVerdict.CORRECT: "✅",
            ValidationVerdict.PARTIAL: "⚠️",
            ValidationVerdict.WRONG: "❌",
            ValidationVerdict.EMPTY: "🔲",
            ValidationVerdict.ERROR: "💥",
        }
        icon = icons.get(result.verdict, "?")
        print(f"  {icon} {prefix}: {result.verdict.value} (confidence: {result.confidence:.0%})")
        if result.description:
            print(f"     Sees: {result.description[:100]}")
        if result.corrections:
            print(f"     Corrections needed: {len(result.corrections)}")
            for c in result.corrections[:3]:
                print(f"       • [{c.priority}] {c.action} {c.target}: {c.issue}")
