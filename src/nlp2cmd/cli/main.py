"""
Command Line Interface for NLP2CMD.

Provides interactive REPL mode, file operations, and environment analysis.

This module is the slim entry point. Heavy implementations are in:
- cli/commands/run.py       — --run mode with error recovery
- cli/commands/generate.py  — single-query generation (fast path)
- cli/commands/interactive.py — InteractiveSession REPL
- cli/commands/tools.py     — repair, validate, analyze_env subcommands
- cli/helpers.py            — shared utilities, adapter factory, browser fallbacks
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

# Import click with fallback stubs
try:
    import click
except Exception:  # pragma: no cover
    click = None  # type: ignore

# Import rich console
try:
    from rich.console import Console
    console = Console()
except ImportError:  # pragma: no cover
    console = None  # type: ignore

# Import environment loading
try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

# ---------------------------------------------------------------------------
# Backward-compatible re-exports (tests & external code import from here)
# ---------------------------------------------------------------------------
# Re-export InteractiveSession from its new location
from nlp2cmd.cli.commands.interactive import InteractiveSession  # noqa: F401

# Re-export handle_run_mode and _handle_run_query
from nlp2cmd.cli.commands.run import (  # noqa: F401
    handle_run_mode,
    _handle_run_query,
    _suggest_next_steps,
)

# Re-export helpers used by the main() dispatcher
from nlp2cmd.cli.helpers import (  # noqa: F401
    get_adapter,
    _looks_like_log_input,
    _system_beep,
    _timed_default_yes,
    _shell_env_context,
    _is_playwright_error,
    _maybe_install_playwright,
    _fallback_open_url,
    _fallback_open_url_from_query,
    ExecutionRunner,
)


# ---------------------------------------------------------------------------
# Lazy subcommand registration
# ---------------------------------------------------------------------------
def _register_subcommands_for_args(argv: list[str]) -> None:
    """Register Click subcommands lazily based on argv.

    This avoids importing heavy optional subsystems (e.g. service/FastAPI) for
    the common case of single-query command generation.
    """
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
            main.add_command(web_schema_group)
    except Exception:
        pass

    try:
        if wants_help or subcmd in {"history"}:
            from nlp2cmd.cli.history import history_group
            main.add_command(history_group)
    except Exception:
        pass

    try:
        if wants_help or subcmd in {"cache"}:
            from nlp2cmd.cli.cache import cache_group
            main.add_command(cache_group)
    except Exception:
        pass

    # Service commands are the heaviest (can pull FastAPI/uvicorn). Register only on demand.
    try:
        if wants_help or subcmd in {"service", "config-service"}:
            from nlp2cmd.service.cli import add_service_command
            add_service_command(main)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Click group — main entry point
# ---------------------------------------------------------------------------

# Stub commands for when click is not available
def repair(*args, **kwargs):
    pass

def validate(*args, **kwargs):
    pass

def analyze_env(*args, **kwargs):
    pass

def version(*args, **kwargs):
    pass

# Add command methods to main when click is not available
if not hasattr(click, 'Group'):
    def _stub_command(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    # Apply the stub command method immediately after main function is defined


@click.group(invoke_without_command=True)
@click.option("-i", "--interactive", is_flag=True, help="Start interactive mode")
@click.option(
    "-d", "--dsl",
    type=click.Choice(["auto", "sql", "shell", "docker", "kubernetes", "dql", "appspec", "browser"]),
    default="auto",
    help="DSL type"
)
@click.option(
    "--appspec",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to an app2schema.appspec JSON file (required for --dsl appspec)",
)
@click.option("-q", "--query", help="Single query to process")
@click.option(
    "--stdin",
    "stdin_mode",
    is_flag=True,
    help="Read query text from stdin (usually automatic when piped; e.g. echo 'list files' | nlp2cmd)",
)
@click.option(
    "--stdout",
    "stdout_only",
    is_flag=True,
    help="Print only the generated command to stdout (no extra formatting)",
)
@click.option(
    "-oo",
    "--only-output",
    "only_output",
    is_flag=True,
    help="In --run mode, print only the executed command output (suppress generation/execution UI)",
)
@click.option("-r", "--run", is_flag=True, help="Execute query immediately with interactive error recovery")
@click.option("--auto-repair", is_flag=True, help="Auto-apply repairs")
@click.option("--explain", is_flag=True, help="Explain how the result was produced")
@click.option("--execute-web", is_flag=True, help="Execute dom_dql.v1 actions via Playwright (requires playwright)")
@click.option("-ac", "--auto-confirm", is_flag=True, help="Skip confirmation prompts when using --run")
@click.option(
    "--auto-install/--no-auto-install",
    default=True,
    help="Auto-install missing Python deps/tools when using --run (e.g. playwright)",
)
@click.option("-v", "--version", is_flag=True, help="Show version information")
@click.pass_context
def main(
    ctx,
    interactive: bool,
    dsl: str,
    appspec: Optional[Path],
    query: Optional[str],
    stdin_mode: bool,
    stdout_only: bool,
    only_output: bool,
    run: bool,
    auto_repair: bool,
    explain: bool,
    execute_web: bool,
    auto_confirm: bool,
    auto_install: bool,
    version: bool,
):
    """NLP2CMD - Natural Language to Domain-Specific Commands."""
    # Start timing from the very beginning
    script_start_time = time.time()
    
    if load_dotenv is not None:
        try:
            load_dotenv()
        except Exception:
            pass
    ctx.ensure_object(dict)
    ctx.obj["dsl"] = dsl
    ctx.obj["auto_repair"] = auto_repair
    ctx.obj["script_start_time"] = script_start_time

    if ctx.invoked_subcommand is None:
        auto_stdin = (not stdin_mode) and (not query) and (not sys.stdin.isatty())
        if (stdin_mode or auto_stdin) and not query:
            try:
                stdin_text = sys.stdin.read()
            except Exception:
                stdin_text = ""
            stdin_text = (stdin_text or "").strip()
            if stdin_text:
                query = stdin_text

    if stdout_only:
        run = False
        explain = False
        interactive = False
        execute_web = False

    if ctx.invoked_subcommand is None:
        if version:
            from nlp2cmd import __version__
            console.print(f"nlp2cmd version {__version__}")
            return
        if run and query:
            _handle_run_query(
                query,
                dsl=dsl,
                appspec=appspec,
                auto_confirm=auto_confirm,
                execute_web=execute_web,
                auto_install=auto_install,
                auto_repair=auto_repair,
                only_output=only_output,
            )
        elif query:
            if dsl == "appspec":
                from nlp2cmd.cli.commands.generate import handle_appspec_query
                handle_appspec_query(
                    query,
                    dsl=dsl,
                    appspec=appspec,
                    auto_repair=auto_repair,
                    explain=explain,
                    execute_web=execute_web,
                )
            elif dsl == "auto":
                from nlp2cmd.cli.commands.generate import handle_generate_query
                handle_generate_query(
                    query,
                    dsl=dsl,
                    appspec=appspec,
                    explain=explain,
                    execute_web=execute_web,
                    stdout_only=stdout_only,
                    script_start_time=ctx.obj.get("script_start_time", time.time()),
                )
        elif interactive:
            session = InteractiveSession(
                dsl=dsl,
                auto_repair=auto_repair,
                appspec=str(appspec) if appspec else None,
            )
            session.run()
        else:
            console.print(ctx.get_help())

# Apply command method stub after main function definition
if not hasattr(click, 'Group'):
    def _stub_command(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    main.command = _stub_command
    main.add_command = lambda cmd: None

# Stub command decorators for when click is not available
_command_decorator = main.command if hasattr(main, 'command') else lambda *args, **kwargs: lambda func: func


@_command_decorator
@click.argument("file", type=click.Path(exists=True))
@click.option("--backup", is_flag=True, help="Create backup before repair")
@click.pass_context
def repair(ctx, file: str, backup: bool):
    """Repair a configuration file."""
    from nlp2cmd.cli.commands.tools import cmd_repair
    cmd_repair(file, backup)


@_command_decorator
@click.argument("file", type=click.Path(exists=True))
@click.pass_context
def validate(ctx, file: str):
    """Validate a configuration file."""
    from nlp2cmd.cli.commands.tools import cmd_validate
    cmd_validate(file)


@_command_decorator
@click.option("-o", "--output", type=click.Path(), help="Output file (JSON)")
@click.pass_context
def analyze_env(ctx, output: Optional[str]):
    """Analyze system environment."""
    from nlp2cmd.cli.commands.tools import cmd_analyze_env
    cmd_analyze_env(output)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def cli_entry_point():
    """Entry point that handles natural language queries before Click."""
    import sys
    
    # Get command line arguments
    args = sys.argv[1:]  # Skip the script name
    
    # Lazily register subcommands depending on argv
    _register_subcommands_for_args(args)
    
    # Check if this looks like a natural language query
    # Look for text that contains spaces after flags
    has_text_with_spaces = any(' ' in arg and not arg.startswith('-') for arg in args)
    
    # Also check if we have exactly one argument that contains spaces (single query)
    is_single_query = len(args) == 1 and ' ' in args[0] and not args[0].startswith('-')
    
    # Check if --query flag is already present
    has_query_flag = '--query' in args or '-q' in args
    
    if ((len(args) >= 2 and has_text_with_spaces and
        not any(arg.startswith('-') and '=' in arg for arg in args) and  # Avoid flags with values
        not has_query_flag) or  # Don't process if --query is already there
        is_single_query):
        
        # Parse and rewrite args
        text_parts = []
        option_parts = []
        
        for i, a in enumerate(args):
            if a.startswith("-"):
                option_parts.append(a)
            elif ' ' in a:
                # This looks like natural language text
                text_parts.append(a)
            else:
                # Single word, could be option value or text
                # If we don't have any text parts yet and this isn't a known option, treat it as text
                if not text_parts and i == len(args) - 1:
                    text_parts.append(a)
                else:
                    option_parts.append(a)
        
        query_text = " ".join(text_parts).strip()
        
        # Build new args
        new_args = option_parts.copy()
        
        # If we have a query, add --query
        if query_text:
            new_args.extend(["--query", query_text])
        
        # Replace sys.argv
        sys.argv[1:] = new_args
    
    # Call the main Click function
    main()


if __name__ == "__main__":
    cli_entry_point()
