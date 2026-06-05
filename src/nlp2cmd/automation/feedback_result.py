# FeedbackResult - extracted from feedback_loop.py
"""
Declarative Schema-Driven Feedback Loop for browser automation.

Core algorithm:
  1. Execute step
  2. Validate result (page state, DOM, expected outcome)
  3. Classify failure: schema_error | handling_error | data_error | page_state_error
  4. Repair: local LLM → cloud LLM escalation
  5. Retry with repaired step (max N attempts)
  6. A solution is ALWAYS found — it's a matter of time, not algorithm limits

The feedback loop wraps each ActionPlan step execution with:
  - Pre-validation (are we on the right page? correct state?)
  - Post-validation (did the action achieve its goal?)
  - Error classification (WHY did it fail?)
  - Repair escalation (local → cloud LLM)
  - Page analysis (find correct selectors/sections via LLM)

Environment:
    LLM_VALIDATOR_MODEL     — local Ollama model for step validation
    LLM_REPAIR_MODEL        — cloud model for repair escalation
    FEEDBACK_LOOP_MAX_RETRIES — max repair attempts per step (default: 5)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

log = logging.getLogger("nlp2cmd.feedback_loop")
from nlp2cmd.automation.repair_attempt import RepairAttempt

@dataclass
class FeedbackResult:
    """Result of the feedback loop for a single step."""
    success: bool
    result_value: Optional[str] = None
    attempts: list[RepairAttempt] = field(default_factory=list)
    final_params: Optional[dict] = None
    total_elapsed_ms: float = 0.0
