"""
Command Line Interface for NLP2CMD.

Provides interactive REPL mode, file operations, and environment analysis.
"""

from __future__ import annotations

import json
import os
import sys
import time
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from nlp2cmd.execution import ExecutionRunner

# Import click with fallback stubs
try:
    import click
except Exception:  # pragma: no cover
    click = setup_click_stubs()

# Import rich with fallback stubs
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.syntax import Syntax
except Exception:  # pragma: no cover
    Console, Panel, Table, Text, Syntax = setup_rich_stubs()

# Fallback for console if rich is not available
try:
    from rich.console import Console
    console = Console()
except ImportError:
    console = get_console()

# Import environment loading
try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

# Import CLI modules
from nlp2cmd.cli.interactive_session import InteractiveSession
from nlp2cmd.cli.run_handlers import handle_run_mode, _handle_run_query
from nlp2cmd.cli.commands import repair_command, validate_command, analyze_env_command
from nlp2cmd.cli.utils import (
    _register_subcommands_for_args,
    get_adapter,
    get_console,
    get_measure_context,
    _interactive_followup,
    _is_playwright_error,
    _maybe_install_playwright,
    _fallback_open_url,
)
from nlp2cmd.cli.display import display_command_result
from nlp2cmd.cli.syntax_cache import get_cached_syntax
from nlp2cmd.generation.pipeline import RuleBasedPipeline
from nlp2cmd.web_schema.form_data_loader import FormDataLoader

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


# Stub commands for when click is not available
def repair(*args, **kwargs):
    pass

def validate(*args, **kwargs):
    pass

def analyze_env(*args, **kwargs):
    pass

def version(*args, **kwargs):
    pass


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
                    session = InteractiveSession(
                        dsl=dsl,
                        auto_repair=auto_repair,
                        appspec=str(appspec) if appspec else None,
                    )
                    feedback = session.process(query)
                    session.display_feedback(feedback, include_explanation=explain)
                    
                    if execute_web:
                        try:
                            from nlp2cmd import NLP2CMD
                            from nlp2cmd.adapters import AppSpecAdapter
                            from nlp2cmd.pipeline_runner import PipelineRunner

                            adapter = AppSpecAdapter(appspec_path=str(appspec))
                            nlp = NLP2CMD(adapter=adapter)
                            ir = nlp.transform_ir(query)
                            runner = PipelineRunner(headless=False)
                            res = runner.run(ir, dry_run=False, confirm=True)
                            if res.success:
                                console.print(f"\n✅ Executed web action in {res.duration_ms:.1f}ms")
                            else:
                                console.print(f"\n❌ Web execution failed: {res.error}")
                        except Exception as e:
                            console.print(f"\n❌ Web execution error: {e}")
                elif dsl == "auto":
                    # Fast path: for single-shot CLI queries we avoid spinning up the full
                    # InteractiveSession (env scan + thermo router), which saves seconds.
                    from nlp2cmd.generation.pipeline import RuleBasedPipeline
                    from nlp2cmd.monitoring import measure_resources, format_last_metrics

                    pipeline = RuleBasedPipeline()
                    _measure = str(os.environ.get("NLP2CMD_MEASURE_RESOURCES", "1") or "").strip().lower() not in {
                        "0",
                        "false",
                        "no",
                        "n",
                        "off",
                    }
                    with (measure_resources() if _measure else nullcontext()):
                        pipeline_result = pipeline.process(query)

                    if stdout_only:
                        cmd = (pipeline_result.command or "").strip()
                        if cmd:
                            sys.stdout.write(cmd + "\n")
                        if not pipeline_result.success:
                            for err in list(pipeline_result.errors or []):
                                sys.stderr.write(str(err).rstrip() + "\n")
                        return

                    metrics_str = format_last_metrics() if _measure else ""
                    out: dict[str, Any] = {
                        "dsl": "auto",
                        "query": query,
                        "status": "success" if pipeline_result.success else "error",
                        "confidence": float(pipeline_result.confidence),
                        "generated_command": (pipeline_result.command or "").strip() or None,
                        "errors": list(pipeline_result.errors or []),
                        "warnings": list(pipeline_result.warnings or []),
                        "suggestions": [],
                        "clarification_questions": [],
                    }

                    pipeline_meta = getattr(pipeline_result, "metadata", None)
                    if isinstance(pipeline_meta, dict) and pipeline_meta:
                        out.update(pipeline_meta)
                    if metrics_str:
                        try:
                            from nlp2cmd.monitoring.token_costs import parse_metrics_string
                            from nlp2cmd.monitoring import estimate_token_cost

                            metrics = parse_metrics_string(metrics_str)
                            if metrics:
                                out["resource_metrics"] = {
                                    "time_ms": metrics.get("time_ms"),
                                    "cpu_percent": metrics.get("cpu_percent"),
                                    "memory_mb": metrics.get("memory_mb"),
                                    "energy_mj": metrics.get("energy_mj"),
                                }
                                out["resource_metrics_parsed"] = metrics

                                if (
                                    metrics.get("time_ms") is not None
                                    and metrics.get("cpu_percent") is not None
                                    and metrics.get("memory_mb") is not None
                                ):
                                    token_estimate = estimate_token_cost(
                                        metrics["time_ms"],
                                        metrics["cpu_percent"],
                                        metrics["memory_mb"],
                                        metrics.get("energy_mj"),
                                    )
                                    out["token_estimate"] = {
                                        "total": int(token_estimate.total_tokens_estimate),
                                        "input": int(token_estimate.input_tokens_estimate),
                                        "output": int(token_estimate.output_tokens_estimate),
                                        "cost_usd": float(token_estimate.estimated_cost_usd),
                                        "model_tier": token_estimate.equivalent_model_tier,
                                        "tokens_per_ms": float(token_estimate.tokens_per_millisecond),
                                        "tokens_per_mj": float(token_estimate.tokens_per_mj),
                                    }
                        except Exception:
                            pass

                    if explain:
                        out.update(
                            {
                                "domain": pipeline_result.domain,
                                "intent": pipeline_result.intent,
                                "detection_confidence": pipeline_result.detection_confidence,
                                "template_used": pipeline_result.template_used,
                                "source": pipeline_result.source,
                                "entities": pipeline_result.entities,
                            }
                        )

                    # Calculate total execution time
                    script_start_time = ctx.obj.get("script_start_time", time.time())
                    total_time_ms = (time.time() - script_start_time) * 1000
                    
                    # Add total execution time to output
                    out["total_execution_time_ms"] = round(total_time_ms, 1)
                    
                    display_command_result(
                        command=out.get("generated_command", "") or "",
                        metadata=out,
                        metrics_str=metrics_str,
                        show_yaml=True,
                        title="NLP2CMD Result",
                    )
                    
                    if execute_web and dsl == "browser":
                        try:
                            from nlp2cmd import NLP2CMD
                            from nlp2cmd.adapters import BrowserAdapter
                            from nlp2cmd.pipeline_runner import PipelineRunner

                            adapter = BrowserAdapter()
                            nlp = NLP2CMD(adapter=adapter)
                            session = InteractiveSession(dsl=dsl, auto_repair=auto_repair)
                            ir = nlp.transform_ir(query, context=session.context)
                            runner = PipelineRunner(headless=False)
                            res = runner.run(ir, dry_run=False, confirm=True)
                            if res.success:
                                console.print(f"\n✅ Opened URL via Playwright in {res.duration_ms:.1f}ms")
                            else:
                                console.print(f"\n❌ Playwright execution failed: {res.error}")
                        except Exception as e:
                            console.print(f"\n❌ Playwright execution error: {e}")
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
    repair_command(ctx, file, backup)


@_command_decorator
@click.argument("file", type=click.Path(exists=True))
@click.pass_context
def validate(ctx, file: str):
    """Validate a configuration file."""
    validate_command(ctx, file)


@_command_decorator
@click.option("-o", "--output", type=click.Path(), help="Output file (JSON)")
@click.pass_context
def analyze_env(ctx, output: Optional[str]):
    """Analyze system environment."""
    analyze_env_command(ctx, output)


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
