# FeedbackResult - extracted from __init__.py
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
from nlp2cmd.feedback.feedback_type import FeedbackType

@dataclass
class FeedbackResult:
    """Result of feedback analysis."""

    type: FeedbackType
    original_input: str
    generated_output: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    auto_corrections: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0
    requires_user_input: bool = False
    clarification_questions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        """Check if feedback indicates success."""
        return self.type == FeedbackType.SUCCESS

    @property
    def can_auto_fix(self) -> bool:
        """Check if automatic fixes are available."""
        return len(self.auto_corrections) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "original_input": self.original_input,
            "generated_output": self.generated_output,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "auto_corrections": self.auto_corrections,
            "confidence": self.confidence,
            "requires_user_input": self.requires_user_input,
            "clarification_questions": self.clarification_questions,
            "metadata": self.metadata,
        }

