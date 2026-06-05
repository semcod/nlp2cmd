# CorrectionPlan - extracted from correction_engine.py
"""
Correction Engine — iterative drawing repair based on visual validation feedback.

After VisualValidator identifies issues, this engine:
1. Interprets correction instructions
2. Maps corrections to drawing commands (clear, redraw, recolor, move)
3. Executes corrections via DrawingSkill + Renderer
4. Re-validates until correct or max iterations reached

Pipeline:
    ValidationResult.corrections → CorrectionPlan → execute → re-screenshot → re-validate

Single Responsibility: correction instructions → drawing command sequence → execution.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from nlp2cmd.skills.drawing.visual_validator import (
    DrawingCorrection,
    ValidationResult,
    ValidationVerdict,
    VisualValidator,
)
from nlp2cmd.skills.drawing.correction_step import CorrectionStep

@dataclass
class CorrectionPlan:
    """Plan of steps to correct a drawing."""
    steps: list[CorrectionStep] = field(default_factory=list)
    description: str = ""
    estimated_time_ms: float = 0.0
