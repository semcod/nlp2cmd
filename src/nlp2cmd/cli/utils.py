"""
Utility functions for NLP2CMD CLI.

Provides helper functions for adapters, environment context, and CLI setup.
"""

from __future__ import annotations

import os
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Optional


def _shell_env_context(context: dict[str, Any]) -> dict[str, Any]:
    """Extract shell environment context from analysis results."""
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


def _register_subcommands_for_args(argv: list[str]) -> None:
    """Register Click subcommands lazily based on argv.

    This avoids importing heavy optional subsystems (e.g. service/FastAPI) for
    the common case of single-query command generation.
    """
    try:
        import click
    except Exception:
        return

    if not hasattr(click, "Group"):
        return

    # If user asks for help, register everything so commands show up.
    wants_help = any(a in {"--help", "-h"} for a in argv)

    # Find first non-flag token (potential subcommand)
    subcmd = None
    for a in argv:
        if a.startswith("-"):
            continue
        subcmd = a
        break

    try:
        if wants_help or subcmd in {"web-schema"}:
            from nlp2cmd.cli.web_schema import web_schema_group
            # This will be added to main group later
            import nlp2cmd.cli.main
            nlp2cmd.cli.main.main.add_command(web_schema_group)
    except Exception:
        pass

    try:
        if wants_help or subcmd in {"history"}:
            from nlp2cmd.cli.history import history_group
            import nlp2cmd.cli.main
            nlp2cmd.cli.main.main.add_command(history_group)
    except Exception:
        pass

    try:
        if wants_help or subcmd in {"cache"}:
            from nlp2cmd.cli.cache import cache_group
            import nlp2cmd.cli.main
            nlp2cmd.cli.main.main.add_command(cache_group)
    except Exception:
        pass

    # Service commands are the heaviest (can pull FastAPI/uvicorn). Register only on demand.
    try:
        if wants_help or subcmd in {"service", "config-service"}:
            from nlp2cmd.service.cli import add_service_command
            import nlp2cmd.cli.main
            add_service_command(nlp2cmd.cli.main.main)
    except Exception:
        pass


def setup_click_stubs():
    """Setup stub classes when click is not available."""
    try:
        import click
        return click
    except Exception:  # pragma: no cover
        class _ClickStub:
            class Group:
                def parse_args(self, ctx, args):
                    return args

                def get_command(self, ctx, name):
                    return None

            class Context:
                pass

            class Choice:
                def __init__(self, choices):
                    self.choices = choices

            class Path:
                def __init__(
                    self,
                    exists: bool = False,
                    dir_okay: bool = True,
                    file_okay: bool = True,
                    path_type=None,
                ):
                    self.exists = exists
                    self.dir_okay = dir_okay
                    self.file_okay = file_okay
                    self.path_type = path_type

            @staticmethod
            def _decorator(*_args, **_kwargs):
                def _wrap(func):
                    return func

                return _wrap

            group = _decorator
            option = _decorator
            argument = _decorator
            command = _decorator

            @staticmethod
            def pass_context(func):
                return func

            @staticmethod
            def Choice(choices):
                class _Choice:
                    def __init__(self, choices):
                        self.choices = choices
                return _Choice(choices)

            @staticmethod
            def Path(**kwargs):
                class _Path:
                    def __init__(self, **kwargs):
                        for k, v in kwargs.items():
                            setattr(self, k, v)
                return _Path(**kwargs)

        return _ClickStub()


def setup_rich_stubs():
    """Setup stub classes when rich is not available."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
        from rich.syntax import Syntax
        return Console, Panel, Table, Text, Syntax
    except Exception:  # pragma: no cover
        class Console:  # type: ignore
            def print(self, *args, **kwargs):
                try:
                    builtins_print = __builtins__["print"] if isinstance(__builtins__, dict) else print
                    builtins_print(*args)
                except Exception:
                    return

            def input(self, *args, **kwargs):
                return ""

        class Panel:  # type: ignore
            def __init__(self, renderable, *args, **kwargs):
                self.renderable = renderable

        class Table:  # type: ignore
            def __init__(self, *args, **kwargs):
                return

        class Text(str):  # type: ignore
            pass

        class Syntax:  # type: ignore
            def __init__(self, code, *args, **kwargs):
                self.code = code

        return Console, Panel, Table, Text, Syntax


def get_console():
    """Get console instance with fallback."""
    try:
        from rich.console import Console
        return Console()
    except ImportError:
        class Console:
            def print(self, *args, **kwargs):
                print(*args, **kwargs)
        return Console()


def get_measure_context():
    """Get resource measurement context."""
    _measure = str(os.environ.get("NLP2CMD_MEASURE_RESOURCES", "1") or "").strip().lower() not in {
        "0",
        "false",
        "no",
        "n",
        "off",
    }
    
    if _measure:
        try:
            from nlp2cmd.monitoring import measure_resources
            return measure_resources()
        except Exception:
            pass
    
    return nullcontext()


def _interactive_followup(session, feedback):
    """Handle interactive followup for feedback requiring user input."""
    console = get_console()
    
    if not feedback.requires_user_input:
        return feedback

    questions = list(feedback.clarification_questions or [])
    if not questions:
        questions = ["Please clarify the request."]

    answers: list[str] = []
    for q in questions[:5]:
        response = console.input(f"\n[yellow]{q}[/yellow] ").strip()
        if response:
            answers.append(response)

    if not answers:
        return feedback

    combined = " ".join(answers)
    return session.process(f"{feedback.original_input}. {combined}")


def _is_playwright_error(msg: str) -> bool:
    """Check if error message indicates Playwright issues."""
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


def _maybe_install_playwright(msg: str, runner, *, auto_install: bool) -> bool:
    """Install Playwright if needed and requested."""
    import shlex
    
    console = get_console()
    
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
    """Fallback URL opening without Playwright."""
    from nlp2cmd.execution import open_url

    console = get_console()

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
