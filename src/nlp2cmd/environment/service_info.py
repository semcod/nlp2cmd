# ServiceInfo - extracted from __init__.py
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
class ServiceInfo:
    """Information about a running service."""

    name: str
    running: bool
    port: Optional[int] = None
    reachable: bool = False
