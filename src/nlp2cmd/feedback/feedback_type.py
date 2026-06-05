# FeedbackType - extracted from __init__.py
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
class FeedbackType(Enum):
    """Types of feedback from the system."""

    SUCCESS = "success"
    SYNTAX_ERROR = "syntax_error"
    SCHEMA_MISMATCH = "schema_mismatch"
    RUNTIME_ERROR = "runtime_error"
    AMBIGUOUS_INPUT = "ambiguous_input"
    PARTIAL_SUCCESS = "partial_success"
    SECURITY_VIOLATION = "security_violation"
