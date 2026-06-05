# ToolInfo - extracted from __init__.py
"""
Environment Analysis module for NLP2CMD.

Provides system environment detection, tool availability checking,
and context-aware command validation.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
@dataclass
class ToolInfo:
    """Information about an installed tool."""

    name: str
    available: bool
    version: Optional[str] = None
    path: Optional[str] = None
    config_files: list[str] = field(default_factory=list)
