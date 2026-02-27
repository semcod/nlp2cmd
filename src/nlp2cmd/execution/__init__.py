"""
Execution module for NLP2CMD.

Contains executors for different DSL types:
- Shell commands
- Browser automation (Playwright)
- Keyboard shortcuts
- Interactive runner with error recovery
- Modular executors (Etap 3): base, shell_executor, media_recorder, registry
"""

from nlp2cmd.execution.base import BaseExecutor, ExecutorContext, ExecutorResult
from nlp2cmd.execution.browser import BrowserExecutor, open_url, search_web
from nlp2cmd.execution.executor_registry import (
    ExecutorRegistry,
    create_default_registry,
)
from nlp2cmd.execution.media_recorder import MediaRecorder
from nlp2cmd.execution.runner import ExecutionRunner, ExecutionResult, RecoveryContext
from nlp2cmd.execution.shell_executor import ShellExecutor

__all__ = [
    # Etap 3: modular executors
    "BaseExecutor",
    "ExecutorContext",
    "ExecutorResult",
    "ShellExecutor",
    "MediaRecorder",
    "ExecutorRegistry",
    "create_default_registry",
    # Legacy
    "BrowserExecutor",
    "open_url",
    "search_web",
    "ExecutionRunner",
    "ExecutionResult",
    "RecoveryContext",
]
