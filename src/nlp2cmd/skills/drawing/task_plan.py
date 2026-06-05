# TaskPlan - extracted from validation.py
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
@dataclass
class TaskPlan:
    """What the user wants drawn — the reference for validation."""
    description: str = ""
    objects: list[dict[str, str]] = field(default_factory=list)  # [{"name": "star", "color": "#FF0000"}]

    def add(self, name: str, color: str = ""):
        self.objects.append({"name": name, "color": color})

    @property
    def object_names(self) -> list[str]:
        return [o["name"] for o in self.objects]
