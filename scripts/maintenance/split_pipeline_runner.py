#!/usr/bin/env python3
"""Split pipeline_runner.py into mixin modules.

This script extracts logical sections from the monolithic pipeline_runner.py
into separate mixin files, then rewrites the main file to compose them.

Mixin files created:
- pipeline_runner_shell.py   — ShellExecutionMixin
- pipeline_runner_browser.py — BrowserExecutionMixin
- pipeline_runner_desktop.py — DesktopExecutionMixin
- pipeline_runner_plans.py   — PlanExecutionMixin
"""

from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "nlp2cmd"
RUNNER = SRC / "pipeline_runner.py"

lines = RUNNER.read_text().splitlines(keepends=True)


def find_line(pattern, start=0):
    for i in range(start, len(lines)):
        if pattern in lines[i]:
            return i
    raise ValueError(f"Pattern not found: {pattern}")


# Key boundary lines (0-indexed)
shell_start = find_line("    def _run_shell(")
browser_start = find_line("    def _run_dom_dql(")
# _dismiss_popups is preceded by @staticmethod decorator on previous line
dismiss_static_line = find_line("    @staticmethod", browser_start + 100)
# Verify this is the _dismiss_popups static
while "_dismiss_popups" not in lines[dismiss_static_line + 1]:
    dismiss_static_line = find_line("    @staticmethod", dismiss_static_line + 1)
desktop_start = dismiss_static_line  # starts at @staticmethod before _dismiss_popups

# Plans start at the comment separator
plans_start = find_line("    # ═══ Multi-Step ActionPlan Execution")

print(f"Boundaries: shell={shell_start}, browser={browser_start}, "
      f"desktop={desktop_start}, plans={plans_start}")

# Common imports
COMMON_IMPORTS = '''\
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from rich.console import Console

from nlp2cmd.pipeline_runner_utils import (
    _debug,
    _DEBUG,
    _with_epipe_retry,
    _field_attrs,
    _is_junk_field,
    _is_contact_relevant_field,
    _looks_like_comment_form,
    _filter_form_fields,
    _MarkdownConsoleWrapper,
    ShellExecutionPolicy,
    RunnerResult,
    get_timestamp,
    ensure_dir,
    ask_for_screenshot,
    take_screenshot,
    VideoRecorder,
    ask_for_video_recording,
)
from nlp2cmd.utils.yaml_compat import yaml
'''


def write_mixin(filename, classname, docstring, body_lines, extra_imports=""):
    """Write a mixin file. body_lines are already indented with 4 spaces (class methods)."""
    body = "".join(body_lines)
    content = f'''{COMMON_IMPORTS}{extra_imports}

class {classname}:
    """{docstring}"""

{body}'''
    path = SRC / filename
    path.write_text(content)
    print(f"Created {filename} ({len(body_lines)} lines)")


# ====== 1. Shell mixin ======
write_mixin(
    "pipeline_runner_shell.py",
    "ShellExecutionMixin",
    "Shell command execution methods for PipelineRunner.",
    lines[shell_start:browser_start],
    extra_imports="\nfrom nlp2cmd.adapters.base import SafetyPolicy\n",
)

# ====== 2. Browser mixin ======
write_mixin(
    "pipeline_runner_browser.py",
    "BrowserExecutionMixin",
    "DOM/browser execution methods for PipelineRunner.",
    lines[browser_start:desktop_start],
)

# ====== 3. Desktop mixin ======
write_mixin(
    "pipeline_runner_desktop.py",
    "DesktopExecutionMixin",
    "Desktop automation and static utility methods for PipelineRunner.",
    lines[desktop_start:plans_start],
)

# ====== 4. Plans mixin ======
write_mixin(
    "pipeline_runner_plans.py",
    "PlanExecutionMixin",
    "Multi-step ActionPlan execution methods for PipelineRunner.",
    lines[plans_start:],
    extra_imports="\nfrom nlp2cmd.adapters.base import SafetyPolicy\n",
)

# ====== 5. Rewrite main pipeline_runner.py ======
# Keep everything up to _run_shell: imports + PipelineRunner.__init__ + run
core = "".join(lines[:shell_start])

new_main = f'''{core.rstrip()}

    # --- Method bodies are in mixin modules ---
    # See: pipeline_runner_shell.py, pipeline_runner_browser.py,
    #      pipeline_runner_desktop.py, pipeline_runner_plans.py


# Compose PipelineRunner from mixins via class re-definition.
# This preserves backward compatibility: all imports of PipelineRunner still work.
from nlp2cmd.pipeline_runner_shell import ShellExecutionMixin  # noqa: E402
from nlp2cmd.pipeline_runner_browser import BrowserExecutionMixin  # noqa: E402
from nlp2cmd.pipeline_runner_desktop import DesktopExecutionMixin  # noqa: E402
from nlp2cmd.pipeline_runner_plans import PlanExecutionMixin  # noqa: E402

_BasePipelineRunner = PipelineRunner


class PipelineRunner(  # type: ignore[no-redef]
    ShellExecutionMixin,
    BrowserExecutionMixin,
    DesktopExecutionMixin,
    PlanExecutionMixin,
    _BasePipelineRunner,
):
    """PipelineRunner composed from execution mixins.

    Mixins:
    - ShellExecutionMixin: _run_shell, _parse_shell_command, _check_against_safety_policy
    - BrowserExecutionMixin: _run_dom_dql, _run_dom_multi_action
    - DesktopExecutionMixin: _dismiss_popups, _detect_desktop_backend,
      _execute_desktop_plan_step, _xdotool_keys_to_ydotool, etc.
    - PlanExecutionMixin: execute_action_plan, _execute_plan_step,
      _resolve_plan_variables, _do_verify_env, _llm_suggest_article_selectors
    """
    pass
'''

RUNNER.write_text(new_main)
print(f"Rewrote pipeline_runner.py ({len(new_main.splitlines())} lines)")
print("Done!")
