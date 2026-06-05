# ObjectAssessment - extracted from validation.py
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
from nlp2cmd.skills.drawing.object_status import ObjectStatus


@dataclass
class ObjectAssessment:
    """Vision assessment of a single requested object."""
    name: str
    status: ObjectStatus = ObjectStatus.PENDING
    requested_color: str = ""
    actual_color: str = ""
    issue: str = ""            # Description of what's wrong
    suggestion: str = ""       # What to do to fix it
    confidence: float = 0.0
