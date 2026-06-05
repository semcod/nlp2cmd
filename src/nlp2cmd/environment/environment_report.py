# EnvironmentReport - extracted from __init__.py
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
from nlp2cmd.environment.service_info import ServiceInfo
from nlp2cmd.environment.tool_info import ToolInfo


@dataclass
class EnvironmentReport:
    """Complete environment analysis report."""

    os_info: dict[str, str]
    tools: dict[str, ToolInfo]
    services: dict[str, ServiceInfo]
    config_files: list[dict[str, Any]]
    resources: dict[str, Any]
    recommendations: list[str]
