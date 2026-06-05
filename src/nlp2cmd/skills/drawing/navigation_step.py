# NavigationStep - extracted from navigation.py
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


@dataclass
class NavigationStep:
    """A single step in the navigation process."""
    action: str
    success: bool = False
    detail: str = ""
    duration_ms: float = 0
    vision_used: bool = False
