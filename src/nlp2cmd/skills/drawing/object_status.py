# ObjectStatus - extracted from validation.py
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
class ObjectStatus(Enum):
    """Status of a single requested object."""
    PENDING = "pending"       # Not yet attempted
    DRAWN = "drawn"           # Appears to be drawn
    MISSING = "missing"       # Not visible on canvas
    WRONG = "wrong"           # Drawn but incorrect (wrong color, shape, position)
    PARTIAL = "partial"
