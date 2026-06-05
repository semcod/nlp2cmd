# ValidationReport - extracted from validation.py
"""
DrawValidationSkill — Task-aware vision validation for drawing operations.

Goes beyond simple "does it match?" validation to provide:
1. Task tracking: what was requested, what's done, what remains
2. Per-object status: drawn/missing/wrong/partial
3. Overall scene assessment with Qwen VL
4. Actionable next-step suggestions

Pipeline:
    screenshot → vision_analyze → compare_to_plan → status_report

Single Responsibility: Know what's been drawn and what still needs doing.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from nlp2cmd.skills.drawing.object_assessment import ObjectAssessment
from nlp2cmd.skills.drawing.object_status import ObjectStatus
from nlp2cmd.skills.drawing.task_plan import TaskPlan

@dataclass
class ValidationReport:
    """Full validation report: what's done, what remains, what's wrong."""
    plan: TaskPlan
    assessments: list[ObjectAssessment] = field(default_factory=list)
    scene_description: str = ""     # What the vision model sees overall
    overall_match: float = 0.0      # 0..1 how well scene matches plan
    model_used: str = ""
    validation_time_ms: float = 0
    screenshot_path: str = ""

    @property
    def done(self) -> list[ObjectAssessment]:
        return [a for a in self.assessments if a.status == ObjectStatus.DRAWN]

    @property
    def remaining(self) -> list[ObjectAssessment]:
        return [a for a in self.assessments
                if a.status in (ObjectStatus.PENDING, ObjectStatus.MISSING)]

    @property
    def wrong(self) -> list[ObjectAssessment]:
        return [a for a in self.assessments
                if a.status in (ObjectStatus.WRONG, ObjectStatus.PARTIAL)]

    @property
    def all_done(self) -> bool:
        return len(self.remaining) == 0 and len(self.wrong) == 0

    @property
    def progress_pct(self) -> float:
        if not self.assessments:
            return 0.0
        done_count = len(self.done)
        return done_count / len(self.assessments)

    def summary(self) -> str:
        total = len(self.assessments)
        done = len(self.done)
        remaining = len(self.remaining)
        wrong = len(self.wrong)
        pct = self.progress_pct * 100
        return (f"{done}/{total} done ({pct:.0f}%), "
                f"{remaining} remaining, {wrong} need fixing")

    def next_actions(self) -> list[str]:
        """Suggest what to do next."""
        actions = []
        for a in self.assessments:
            if a.status == ObjectStatus.MISSING:
                actions.append(f"draw {a.name}" + (f" in {a.requested_color}" if a.requested_color else ""))
            elif a.status == ObjectStatus.WRONG:
                actions.append(a.suggestion or f"fix {a.name}: {a.issue}")
            elif a.status == ObjectStatus.PARTIAL:
                actions.append(a.suggestion or f"complete {a.name}: {a.issue}")
        return actions
