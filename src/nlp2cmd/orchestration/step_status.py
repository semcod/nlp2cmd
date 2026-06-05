# StepStatus - extracted from engine.py
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
class StepStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REPAIRED = "repaired"
    SKIPPED = "skipped"
