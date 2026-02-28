#!/usr/bin/env python3
"""Split pipeline_runner.py into mixin modules.

This script extracts logical sections from the monolithic pipeline_runner.py
into separate mixin files, then rewrites the main file to compose them.

Mixin files created:
- pipeline_runner_shell.py   — ShellExecutionMixin  (lines 138-311)
- pipeline_runner_browser.py — BrowserExecutionMixin (lines 312-1831)
- pipeline_runner_desktop.py — DesktopExecutionMixin (lines 1832-2179)
- pipeline_runner_plans.py   — PlanExecutionMixin    (lines 2180-4414)
"""

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "nlp2cmd"
RUNNER = SRC / "pipeline_runner.py"

lines = RUNNER.read_text().splitlines(keepends=True)

# --- Identify method boundaries (0-indexed) ---
# Shell: _run_shell .. _check_against_safety_policy (ends before _run_dom_dql)
# Browser: _run_dom_dql .. _dismiss_popups end (ends before _extract_json_from_llm_response)
# Desktop: _extract_json_from_llm_response .. _collect_page_links_for_llm end
# Plans: execute_action_plan .. end of file

def find_line(pattern, start=0):
    for i in range(start, len(lines)):
        if pattern in lines[i]:
            return i
    raise ValueError(f"Pattern not found: {pattern}")

# Key boundary lines (0-indexed)
shell_start = find_line("def _run_shell(")
browser_start = find_line("def _run_dom_dql(")
desktop_start = find_line("def _dismiss_popups(")
plans_start = find_line("# ═══ Multi-Step ActionPlan Execution")

# Common imports needed across mixins
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

# ====== 1. Shell mixin ======
shell_body = "".join(lines[shell_start:browser_start])
# Dedent one level (remove 4 spaces from method bodies to keep as mixin methods)
shell_file = f'''{COMMON_IMPORTS}
from nlp2cmd.adapters.base import SafetyPolicy


class ShellExecutionMixin:
    """Mixin providing shell command execution for PipelineRunner."""

{shell_body}'''

(SRC / "pipeline_runner_shell.py").write_text(shell_file)
print(f"Created pipeline_runner_shell.py ({len(shell_body.splitlines())} lines body)")

# ====== 2. Browser mixin ======
browser_body = "".join(lines[browser_start:desktop_start])
browser_file = f'''{COMMON_IMPORTS}


class BrowserExecutionMixin:
    """Mixin providing DOM/browser execution for PipelineRunner."""

{browser_body}'''

(SRC / "pipeline_runner_browser.py").write_text(browser_file)
print(f"Created pipeline_runner_browser.py ({len(browser_body.splitlines())} lines body)")

# ====== 3. Desktop mixin ======
desktop_body = "".join(lines[desktop_start:plans_start])
desktop_file = f'''{COMMON_IMPORTS}


class DesktopExecutionMixin:
    """Mixin providing desktop automation and static utilities for PipelineRunner."""

{desktop_body}'''

(SRC / "pipeline_runner_desktop.py").write_text(desktop_file)
print(f"Created pipeline_runner_desktop.py ({len(desktop_body.splitlines())} lines body)")

# ====== 4. Plans mixin ======
plans_body = "".join(lines[plans_start:])
plans_file = f'''{COMMON_IMPORTS}

from nlp2cmd.adapters.base import SafetyPolicy


class PlanExecutionMixin:
    """Mixin providing multi-step ActionPlan execution for PipelineRunner."""

{plans_body}'''

(SRC / "pipeline_runner_plans.py").write_text(plans_file)
print(f"Created pipeline_runner_plans.py ({len(plans_body.splitlines())} lines body)")

# ====== 5. Rewrite main pipeline_runner.py ======
# Keep: imports, class definition, __init__, run method
core_body = "".join(lines[:shell_start])

new_main = f'''{core_body.rstrip()}

# --- Mixin imports ---
from nlp2cmd.pipeline_runner_shell import ShellExecutionMixin  # noqa: E402
from nlp2cmd.pipeline_runner_browser import BrowserExecutionMixin  # noqa: E402
from nlp2cmd.pipeline_runner_desktop import DesktopExecutionMixin  # noqa: E402
from nlp2cmd.pipeline_runner_plans import PlanExecutionMixin  # noqa: E402


# Re-open the class to add mixin methods via multiple inheritance
# We use a wrapper pattern to preserve backward compatibility
class PipelineRunner(  # type: ignore[no-redef]
    ShellExecutionMixin,
    BrowserExecutionMixin,
    DesktopExecutionMixin,
    PlanExecutionMixin,
    PipelineRunner,
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
