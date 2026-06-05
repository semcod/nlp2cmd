"""Post-execution validation — stdout/stderr vs expectations (separate from Intract)."""

from nlp2cmd.post_execution.checker import (
    PostCheckResult,
    PostCheckViolation,
    check_plan_outputs,
    infer_post_check_spec,
    post_check_enabled,
)

__all__ = [
    "PostCheckResult",
    "PostCheckViolation",
    "check_plan_outputs",
    "infer_post_check_spec",
    "post_check_enabled",
]
