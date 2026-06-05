# CorrectionEngine - extracted from __init__.py
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
from nlp2cmd.feedback.correction_rule import CorrectionRule

class CorrectionEngine:
    """
    Engine for applying corrections to generated content.

    Provides intelligent correction capabilities based on
    error analysis and predefined rules.
    """

    def __init__(self):
        self.corrections: dict[str, list[CorrectionRule]] = {}

    def register_correction(self, dsl_type: str, rule: CorrectionRule):
        """Register a correction rule for a DSL type."""
        if dsl_type not in self.corrections:
            self.corrections[dsl_type] = []
        self.corrections[dsl_type].append(rule)

    def suggest(
        self,
        error: str,
        content: str,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Suggest a correction for an error.

        Args:
            error: Error message
            content: Content with error
            context: Additional context

        Returns:
            Dictionary with correction suggestion
        """
        # Analyze error type
        error_lower = error.lower()

        # Pattern-based suggestions
        if "unbalanced" in error_lower:
            return self._suggest_balance_fix(content, error)

        if "unclosed" in error_lower:
            return self._suggest_quote_fix(content, error)

        if "not found" in error_lower:
            return self._suggest_missing_element(content, error, context)

        # Default: ask for clarification
        return {
            "confidence": 0.3,
            "description": "Could not determine automatic fix",
            "fix": content,
            "question": "Can you provide more details about the error?",
        }

    def _suggest_balance_fix(self, content: str, error: str) -> dict[str, Any]:
        """Suggest fix for unbalanced brackets/parentheses."""
        if "parenthes" in error.lower():
            open_count = content.count("(")
            close_count = content.count(")")

            if open_count > close_count:
                return {
                    "confidence": 0.8,
                    "description": f"Add {open_count - close_count} closing parenthesis",
                    "fix": content + ")" * (open_count - close_count),
                }
            else:
                return {
                    "confidence": 0.5,
                    "description": "Extra closing parenthesis - review needed",
                    "fix": content,
                    "question": "Where should the opening parenthesis be added?",
                }

        return {"confidence": 0.3, "fix": content, "description": "Balance issue detected"}

    def _suggest_quote_fix(self, content: str, error: str) -> dict[str, Any]:
        """Suggest fix for unclosed quotes."""
        if "single quote" in error.lower():
            return {
                "confidence": 0.7,
                "description": "Add closing single quote",
                "fix": content + "'",
            }
        elif "double quote" in error.lower():
            return {
                "confidence": 0.7,
                "description": "Add closing double quote",
                "fix": content + '"',
            }

        return {"confidence": 0.3, "fix": content, "description": "Quote issue detected"}

    def _suggest_missing_element(
        self,
        content: str,
        error: str,
        context: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        """Suggest fix for missing elements."""
        return {
            "confidence": 0.4,
            "description": "Missing element detected",
            "fix": content,
            "question": "What is the correct name or value?",
        }

    def apply_correction(
        self,
        content: str,
        correction: dict[str, Any],
    ) -> str:
        """Apply a correction to content."""
        return correction.get("fix", content)
