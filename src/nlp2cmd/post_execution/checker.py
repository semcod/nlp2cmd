"""Compare execution stdout/stderr against expected outcomes."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any


def post_check_enabled() -> bool:
    return os.getenv("NLP2CMD_POST_CHECK", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def post_check_strict() -> bool:
    return os.getenv("NLP2CMD_POST_CHECK_STRICT", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


@dataclass
class PostCheckResult:
    step_id: str
    action: str
    passed: bool
    skipped: bool = False
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    spec: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "action": self.action,
            "passed": self.passed,
            "skipped": self.skipped,
            "violations": self.violations,
            "warnings": self.warnings,
            "spec": self.spec,
            "metadata": self.metadata,
        }


class PostCheckViolation(Exception):
    """Raised when post-execution validation fails in strict mode."""

    def __init__(self, results: list[PostCheckResult]) -> None:
        self.results = results
        failed = [item for item in results if not item.passed and not item.skipped]
        messages = [
            f"{item.step_id}: {'; '.join(item.violations) or 'post-check failed'}"
            for item in failed
        ]
        super().__init__("; ".join(messages) or "post-execution check failed")


def infer_post_check_spec(step: Any, *, intent_name: str = "") -> dict[str, Any]:
    """Build default post-check spec from PlanStep action/params."""
    explicit = dict(getattr(step, "metadata", None) or {}).get("post_check") or {}
    if explicit:
        return explicit

    action = str(getattr(step, "action", "") or "")
    params = dict(getattr(step, "params", None) or {})

    if action == "shell_find":
        spec: dict[str, Any] = {"returncode": 0, "min_lines": 0}
        pattern = str(params.get("name") or params.get("pattern") or "")
        if pattern.startswith("*."):
            spec["line_regex"] = re.escape(pattern[1:]) + r"$"
        elif pattern and pattern != "*":
            spec["contains_any"] = [pattern.replace("*", "")]
        return spec

    if action == "shell_list":
        return {"returncode": 0, "min_lines": 0}

    if action in {"shell_read_file", "shell_count_pattern"}:
        return {"returncode": 0}

    if intent_name in {"file_search", "find", "search"}:
        return {"returncode": 0, "min_lines": 0}

    if intent_name in {"list", "ls", "dir"}:
        return {"returncode": 0, "min_lines": 0}

    return {}


def _check_output(
    *,
    spec: dict[str, Any],
    stdout: str,
    stderr: str,
    returncode: int | None,
) -> tuple[list[str], list[str]]:
    violations: list[str] = []
    warnings: list[str] = []

    if not spec:
        return violations, warnings

    expected_rc = spec.get("returncode")
    if expected_rc is not None and returncode is not None and returncode != expected_rc:
        violations.append(f"returncode {returncode} != expected {expected_rc}")

    lines = [line for line in stdout.splitlines() if line.strip()]

    min_lines = spec.get("min_lines")
    if min_lines is not None and len(lines) < int(min_lines):
        violations.append(f"stdout line count {len(lines)} < min_lines {min_lines}")

    max_lines = spec.get("max_lines")
    if max_lines is not None and len(lines) > int(max_lines):
        violations.append(f"stdout line count {len(lines)} > max_lines {max_lines}")

    line_regex = spec.get("line_regex")
    if line_regex and lines:
        pattern = re.compile(str(line_regex))
        if not any(pattern.search(line) for line in lines):
            violations.append(f"no stdout line matches regex {line_regex!r}")

    for needle in spec.get("contains", []) or []:
        if needle and needle not in stdout:
            violations.append(f"stdout missing required substring {needle!r}")

    contains_any = spec.get("contains_any", []) or []
    if contains_any and not any(needle in stdout for needle in contains_any if needle):
        violations.append(f"stdout missing any of {contains_any!r}")

    for forbidden in spec.get("not_contains", []) or []:
        if forbidden and forbidden in stdout:
            violations.append(f"stdout contains forbidden substring {forbidden!r}")
        if forbidden and forbidden in stderr:
            violations.append(f"stderr contains forbidden substring {forbidden!r}")

    for needle in spec.get("warn_if_missing", []) or []:
        if needle and needle not in stdout:
            warnings.append(f"stdout missing optional substring {needle!r}")

    if spec.get("non_empty") and not stdout.strip():
        violations.append("stdout is empty")

    return violations, warnings


def check_step_output(
    step: Any,
    *,
    stdout: str,
    stderr: str = "",
    returncode: int | None = 0,
    intent_name: str = "",
    success: bool | None = None,
) -> PostCheckResult:
    """Validate one step's captured output."""
    spec = infer_post_check_spec(step, intent_name=intent_name)
    if not spec:
        return PostCheckResult(
            step_id=str(getattr(step, "id", "")),
            action=str(getattr(step, "action", "")),
            passed=True,
            skipped=True,
            metadata={"reason": "no post_check spec"},
        )

    if success is False:
        return PostCheckResult(
            step_id=str(getattr(step, "id", "")),
            action=str(getattr(step, "action", "")),
            passed=False,
            spec=spec,
            violations=["step execution reported success=false"],
        )

    violations, warnings = _check_output(
        spec=spec,
        stdout=stdout,
        stderr=stderr,
        returncode=returncode,
    )

    if warnings and post_check_strict():
        violations.extend(warnings)
        warnings = []

    return PostCheckResult(
        step_id=str(getattr(step, "id", "")),
        action=str(getattr(step, "action", "")),
        passed=not violations,
        spec=spec,
        violations=violations,
        warnings=warnings,
        metadata={
            "line_count": len([line for line in stdout.splitlines() if line.strip()]),
            "returncode": returncode,
        },
    )


def check_plan_outputs(
    plan: Any,
    intent: Any,
    execution_result: Any,
    *,
    raise_on_failure: bool | None = None,
) -> dict[str, Any]:
    """Validate all plan steps against execution metadata."""
    intent_name = str(getattr(intent, "intent", "") or "")
    step_meta = list((getattr(execution_result, "metadata", None) or {}).get("steps") or [])
    results: list[PostCheckResult] = []

    for index, step in enumerate(getattr(plan, "steps", []) or []):
        meta = step_meta[index] if index < len(step_meta) else {}
        inner = dict(meta.get("metadata") or {})
        results.append(
            check_step_output(
                step,
                stdout=str(meta.get("stdout") or getattr(execution_result, "stdout", "") or ""),
                stderr=str(meta.get("stderr") or getattr(execution_result, "stderr", "") or ""),
                returncode=inner.get("returncode"),
                intent_name=intent_name,
                success=meta.get("success"),
            )
        )

    payload = {
        "enabled": True,
        "passed": all(item.passed or item.skipped for item in results),
        "strict": post_check_strict(),
        "steps": [item.to_dict() for item in results],
    }

    should_raise = post_check_strict() if raise_on_failure is None else raise_on_failure
    if should_raise and not payload["passed"]:
        raise PostCheckViolation(results)

    return payload


def validate_plan_outputs_if_enabled(
    plan: Any,
    intent: Any,
    execution_result: Any,
) -> dict[str, Any] | None:
    if not post_check_enabled():
        return None
    return check_plan_outputs(plan, intent, execution_result)
