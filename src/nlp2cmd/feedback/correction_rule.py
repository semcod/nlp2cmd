# CorrectionRule - extracted from __init__.py
"""
Feedback Loop module for NLP2CMD.

Provides intelligent feedback analysis, error correction suggestions,
and iterative improvement capabilities.
"""
from __future__ import annotations
import logging
import re
import shlex
import shutil
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
logger = logging.getLogger(__name__)
@dataclass
class CorrectionRule:
    """Rule for automatic correction."""

    pattern: str
    replacement: str | Callable[[re.Match], str]
    description: str
    confidence: float = 0.9
    applies_to: list[str] = field(default_factory=list)  # DSL types

