"""
Helper utilities for the NLP2CMD CLI.

Contains shared functions used across CLI commands:
- Console/output helpers
- Adapter factory
- Browser/Playwright fallback helpers
"""

from __future__ import annotations

import re
import select
import shlex
import sys
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from nlp2cmd.execution import ExecutionRunner

# Import rich with fallback stubs
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.syntax import Syntax
except Exception:  # pragma: no cover
    Console = Panel = Table = Text = Syntax = None  # type: ignore

# Fallback for console if rich is not available
try:
    from rich.console import Console
    console = Console()
except ImportError:
    console = None  # type: ignore

try:
    from nlp2cmd.cli.syntax_cache import get_cached_syntax
except Exception:  # pragma: no cover
    def get_cached_syntax(code: str, lexer: str, theme: str = "monokai", line_numbers: bool = False):  # type: ignore
        try:
            from rich.syntax import Syntax
            return Syntax(code, lexer, theme=theme, line_numbers=line_numbers)
        except Exception:
            return code

try:
    from nlp2cmd.cli.display import display_command_result
except Exception:  # pragma: no cover
    def display_command_result(command: str, metadata=None, metrics_str=None, show_yaml=True, title=None) -> None:  # type: ignore
        print(command)

try:
    from nlp2cmd.cli.markdown_output import print_yaml_block
except Exception:  # pragma: no cover
    def print_yaml_block(data: Any, *, console: Optional[Console] = None) -> None:  # type: ignore
        try:
            (console or Console()).print(str(data))
        except Exception:
            return

# Expose ExecutionRunner for unit tests (monkeypatching) while keeping
# heavy imports lazy and avoiding circular dependencies.
try:
    from nlp2cmd.execution import ExecutionRunner  # type: ignore
except Exception:  # pragma: no cover
    ExecutionRunner = None  # type: ignore


def _system_beep() -> None:
    try:
        sys.stdout.write("\a")
        sys.stdout.flush()
    except Exception:
        return


def _timed_default_yes(
    *,
    timed_prompt: str,
    full_prompt: str,
    timeout_s: float = 1.0,
) -> str:
    if not sys.stdin.isatty():
        return "y"

    console.print(timed_prompt, end="")
    _system_beep()
    try:
        ready, _, _ = select.select([sys.stdin], [], [], timeout_s)
    except Exception:
        ready = []

    if not ready:
        console.print("y")
        return "y"

    try:
        line = sys.stdin.readline()
    except Exception:
        line = ""

    resp = (line or "").strip().lower()
    if resp:
        return resp

    resp = console.input(full_prompt).strip().lower()
    return resp or "y"


def _timed_default_no(
    *,
    timed_prompt: str,
    full_prompt: str,
    timeout_s: float = 1.0,
) -> str:
    if not sys.stdin.isatty():
        return "n"

    console.print(timed_prompt, end="")
    _system_beep()
    try:
        ready, _, _ = select.select([sys.stdin], [], [], timeout_s)
    except Exception:
        ready = []

    if not ready:
        console.print("n")
        return "n"

    try:
        line = sys.stdin.readline()
    except Exception:
        line = ""

    resp = (line or "").strip().lower()
    if resp:
        return resp

    resp = console.input(full_prompt).strip().lower()
    return resp or "n"


def _shell_env_context(context: dict[str, Any]) -> dict[str, Any]:
    os_info = context.get("os") or {}
    shell_info = context.get("shell") or {}
    env_vars = context.get("env_vars") or {}

    os_name = os_info.get("system")
    if isinstance(os_name, str):
        os_name = os_name.lower()
    else:
        os_name = "linux"

    return {
        "os": os_name,
        "distro": os_info.get("release", ""),
        "shell": shell_info.get("name", "bash"),
        "available_tools": [],
        "environment_variables": env_vars,
    }


def get_adapter(dsl: str, context: dict[str, Any]):
    """Get the appropriate adapter for the DSL type."""
    from nlp2cmd.adapters import (
        DockerAdapter,
        DQLAdapter,
        KubernetesAdapter,
        ShellAdapter,
        SQLAdapter,
        AppSpecAdapter,
        BrowserAdapter,
    )

    adapters = {
        "sql": lambda: SQLAdapter(dialect="postgresql"),
        "shell": lambda: ShellAdapter(environment_context=_shell_env_context(context)),
        "docker": lambda: DockerAdapter(),
        "kubernetes": lambda: KubernetesAdapter(),
        "dql": lambda: DQLAdapter(),
        "appspec": lambda: AppSpecAdapter(),
        "browser": lambda: BrowserAdapter(),
    }

    if dsl == "auto":
        # Default to shell for auto mode
        return ShellAdapter(environment_context=_shell_env_context(context))

    factory = adapters.get(dsl)
    if factory:
        return factory()

    raise ValueError(f"Unknown DSL: {dsl}")


def _looks_like_log_input(text: str) -> bool:
    if not text:
        return False

    if "\n" not in text:
        return False

    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 3:
        return False

    score = 0
    for ln in lines[:40]:
        ll = ln.lower()

        if "traceback (most recent call last)" in ll:
            score += 4
        if re.search(r"file \".+\", line \d+", ln):
            score += 3
        if re.search(r"\b(exception|error|fatal|stack trace)\b", ll):
            score += 1
        if re.search(r"^\d{4}-\d{2}-\d{2}[ t]\d{2}:\d{2}:\d{2}", ln):
            score += 1
        if re.search(r"^\[(info|warn|warning|error|debug|trace)\]", ll):
            score += 1
        if "command not found" in ll:
            score += 2

    return score >= 4


def _is_playwright_error(msg: str) -> bool:
    m = (msg or "").lower()
    if not m:
        return False
    return (
        "no module named 'playwright'" in m
        or "playwright not available" in m
        or "looks like playwright" in m
        or "playwright install" in m
        or "browsertype.launch" in m
        or "executable doesn't exist" in m
        or "executable doesn't exist" in m
    )


def _maybe_install_playwright(msg: str, runner: ExecutionRunner, *, auto_install: bool) -> bool:
    if not _is_playwright_error(msg):
        return False

    if not auto_install:
        console.print("\n[yellow]Playwright is required for browser automation. Install it now? [y/N][/yellow] ", end="")
        if console.input().strip().lower() not in {"y", "yes", "tak"}:
            return False

    py = shlex.quote(sys.executable)
    pip_cmd = f"{py} -m pip install -U playwright"
    install_cmd = f"{py} -m playwright install chromium"

    if not auto_install:
        if not runner.confirm_execution(pip_cmd):
            return False

    res1 = runner.run_command(pip_cmd, stream_output=True)
    if not res1.success:
        return False

    if not auto_install:
        if not runner.confirm_execution(install_cmd):
            return False

    res2 = runner.run_command(install_cmd, stream_output=True)
    return bool(res2.success)


def _fallback_open_url(ir) -> None:
    from nlp2cmd.execution import open_url

    url = None
    type_text = None

    try:
        params = getattr(ir, "params", None)
        if isinstance(params, dict):
            url = params.get("url")
            type_text = params.get("type_text")
    except Exception:
        url = None

    if isinstance(url, str) and url:
        res = open_url(url, use_webbrowser=False)
        if res.success:
            console.print(f"\n[yellow]Opened URL without Playwright: {url}[/yellow]")
            if isinstance(type_text, str) and type_text:
                console.print(f"[yellow]Type manually: {type_text}[/yellow]")


def _fallback_open_url_from_query(query: str) -> None:
    from nlp2cmd.adapters import BrowserAdapter
    from nlp2cmd.execution import open_url

    try:
        url = BrowserAdapter._extract_url(query)
    except Exception:
        url = None
    if isinstance(url, str) and url:
        res = open_url(url, use_webbrowser=False)
        if res.success:
            console.print(f"\n[yellow]Opened URL without Playwright: {url}[/yellow]")
