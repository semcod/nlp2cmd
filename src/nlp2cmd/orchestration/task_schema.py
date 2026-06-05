# TaskSchema - extracted from engine.py
"""
Dynamic Orchestration Engine — core module.

Replaces hardcoded template/pattern matching with LLM-driven:
1. Task planning (decompose NL prompt → step schema)
2. Step execution with retry + LLM repair
3. Reflection / result analysis
4. Adaptive re-planning on failure

This is the core version of the examples/_dynamic_orchestrator.py,
integrated into nlp2cmd's package structure.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from nlp2cmd.orchestration.reflection import (
    ResultAnalyzer,
    ReflectionResult,
    ReflectionVerdict,
    has_error_signals,
)
from nlp2cmd.orchestration.metrics import (
    MetricsCollector,
    PathOptimizer,
    FunctionCache,
)

logger = logging.getLogger(__name__)


# ── Data classes ─────────────────────────────────────────────────────
from nlp2cmd.orchestration.step_def import StepDef

@dataclass
class TaskSchema:
    """LLM-generated execution plan — a dynamic schema for the task."""
    goal: str
    domain: str = "general"  # "code_editor", "drawing", "shell", "web", "general"
    steps: list[StepDef] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
