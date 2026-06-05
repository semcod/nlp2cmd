"""StepStatus - extracted from __init__.py."""

from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
from nlp2cmd.registry import ActionRegistry, ActionResult, get_registry

class StepStatus(Enum):
    """Status of a plan step."""
    
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

