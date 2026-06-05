# CorrectionStep - extracted from correction_engine.py
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
@dataclass
class CorrectionStep:
    """A single step in a correction plan."""
    action: str           # "clear", "set_color", "draw_shape", "screenshot"
    params: dict[str, Any] = field(default_factory=dict)
    source_correction: Optional[DrawingCorrection] = None
