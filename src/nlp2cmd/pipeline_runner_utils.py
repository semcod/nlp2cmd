"""
Pipeline Runner utility functions and classes.

DEPRECATED: This module now re-exports from split modules for backward compatibility.
Use the specific modules directly for new code:
- nlp2cmd.utils.debug_helpers: _debug, _with_epipe_retry
- nlp2cmd.utils.form_field_filters: form field filtering functions
- nlp2cmd.utils.console_wrapper: _MarkdownConsoleWrapper
- nlp2cmd.utils.execution_policy: ShellExecutionPolicy
- nlp2cmd.utils.runner_result: RunnerResult
- nlp2cmd.utils.media_utils: screenshot/video utilities
"""

from __future__ import annotations

# Debug helpers
from nlp2cmd.utils.debug_helpers import _DEBUG, _debug, _with_epipe_retry

# Form field filtering
from nlp2cmd.utils.form_field_filters import (
    _field_attrs,
    _is_junk_field,
    _is_contact_relevant_field,
    _looks_like_comment_form,
    _filter_form_fields,
)

# Console wrapper
from nlp2cmd.utils.console_wrapper import _MarkdownConsoleWrapper

# Dataclasses
from nlp2cmd.utils.execution_policy import ShellExecutionPolicy
from nlp2cmd.utils.runner_result import RunnerResult

# Media utilities
from nlp2cmd.utils.media_utils import (
    get_timestamp,
    ensure_dir,
    ask_for_screenshot,
    take_screenshot,
    VideoRecorder,
    ask_for_video_recording,
)

__all__ = [
    # Debug helpers
    "_DEBUG",
    "_debug",
    "_with_epipe_retry",
    # Form field filtering
    "_field_attrs",
    "_is_junk_field",
    "_is_contact_relevant_field",
    "_looks_like_comment_form",
    "_filter_form_fields",
    # Console wrapper
    "_MarkdownConsoleWrapper",
    # Dataclasses
    "ShellExecutionPolicy",
    "RunnerResult",
    # Media utilities
    "get_timestamp",
    "ensure_dir",
    "ask_for_screenshot",
    "take_screenshot",
    "VideoRecorder",
    "ask_for_video_recording",
]
