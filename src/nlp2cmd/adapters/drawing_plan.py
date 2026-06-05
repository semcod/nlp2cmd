# DrawingPlan - extracted from canvas.py
"""
Canvas drawing adapter for NLP2CMD.

Enables drawing on web-based canvas applications (jspaint.app, Excalidraw, etc.)
via Playwright mouse control. Supports tool selection, color picking, and
geometric shape drawing through natural language commands.

Supported apps:
- jspaint.app — MS Paint clone with full tool palette
- Excalidraw — diagram/whiteboard tool
- Generic canvas — fallback for any <canvas> element

Usage:
    adapter = CanvasAdapter()
    plan = adapter.generate({"text": "narysuj czerwone koło na jspaint.app"})
"""
from __future__ import annotations
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Optional
from nlp2cmd.adapters.base import AdapterConfig, BaseDSLAdapter, SafetyPolicy
from nlp2cmd.ir import ActionIR
_DEBUG = os.environ.get("NLP2CMD_DEBUG", "").lower() in ("1", "true", "yes")
from nlp2cmd.adapters.drawing_step import DrawingStep

@dataclass
class DrawingPlan:
    """Complete drawing plan for canvas operations."""
    url: str = "https://jspaint.app"
    app: str = "jspaint"
    steps: list[DrawingStep] = field(default_factory=list)

