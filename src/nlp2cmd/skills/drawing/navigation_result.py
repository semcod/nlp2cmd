# NavigationResult - extracted from navigation.py
"""
DrawNavigationSkill — Vision-guided canvas discovery and browser navigation.

Uses Qwen VL (via LLM Router vision task) to:
1. Navigate to drawing sites with intelligent fallback
2. Verify canvas is visible and ready (vision confirmation)
3. Dismiss popups using both heuristic + vision strategies
4. Select drawing tools (pencil/brush) with vision guidance

Pipeline:
    navigate → vision_verify → dismiss_popups → select_tool → ready

Single Responsibility: Get the browser to a state where drawing can begin.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from nlp2cmd.skills.drawing.canvas_info import CanvasInfo
from nlp2cmd.skills.drawing.navigation_state import NavigationState
from nlp2cmd.skills.drawing.navigation_step import NavigationStep

@dataclass
class NavigationResult:
    """Full result of the navigation process."""
    state: NavigationState = NavigationState.IDLE
    canvas: CanvasInfo = field(default_factory=CanvasInfo)
    steps: list[NavigationStep] = field(default_factory=list)
    error: str = ""

    @property
    def success(self) -> bool:
        return self.state == NavigationState.READY

    @property
    def total_time_ms(self) -> float:
        return sum(s.duration_ms for s in self.steps)
