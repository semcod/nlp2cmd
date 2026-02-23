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
    console = None  # type: ignore

# Import environment loading
try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

try:
    from nlp2cmd.generation.pipeline import RuleBasedPipeline
except Exception:  # pragma: no cover
    RuleBasedPipeline = None  # type: ignore

try:
    from nlp2cmd.web_schema.form_data_loader import FormDataLoader
except Exception:  # pragma: no cover
    FormDataLoader = None  # type: ignore

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


class InteractiveSession:
    """Interactive REPL session with feedback loop."""

    def __init__(
        self,
        dsl: str = "auto",
        auto_repair: bool = False,
        appspec: Optional[str] = None,
    ):
        self.dsl = dsl
        self.auto_repair = auto_repair
        self.appspec = appspec

        # Initialize components
        from nlp2cmd.environment import EnvironmentAnalyzer
        from nlp2cmd.feedback import FeedbackAnalyzer
        from nlp2cmd.schemas import SchemaRegistry

        self.env_analyzer = EnvironmentAnalyzer()
        self.feedback_analyzer = FeedbackAnalyzer()
        self.schema_registry = SchemaRegistry()

        # Session state
        self.history: list[dict[str, Any]] = []
        self.context: dict[str, Any] = {}

        # Analyze environment
        self._analyze_environment()

    def _analyze_environment(self):
        """Analyze current environment."""
        self.context["environment"] = self.env_analyzer.analyze()

        # Detect tools
        tools = self.env_analyzer.detect_tools()
        self.context["available_tools"] = {
            name: info for name, info in tools.items() if info.available
        }

        # Find config files
        self.context["config_files"] = self.env_analyzer.find_config_files(Path.cwd())

        # Check services
        self.context["services"] = self.env_analyzer.check_services()

    def process(self, user_input: str) -> FeedbackResult:
        """Process user input and return feedback."""
        from nlp2cmd.feedback import FeedbackResult, FeedbackType
        from nlp2cmd.monitoring import measure_resources

        # Use HybridThermodynamicGenerator for intelligent routing between DSL and thermodynamic
        from nlp2cmd.generation.thermodynamic import HybridThermodynamicGenerator
        
        # Initialize hybrid generator
        hybrid_generator = HybridThermodynamicGenerator()
        
        # Generate with hybrid routing
        with measure_resources():
            result = asyncio.run(hybrid_generator.generate(user_input))
        
        # Convert hybrid result to expected format
        if result.get('source') == 'thermodynamic':
            thermo_result = result.get('result')
            if thermo_result and thermo_result.decoded_output:
                # Create mock result for thermodynamic
                class MockResult:
                    def __init__(self, command, plan, status, dependencies, thermo_result):
                        self.command = command
                        self.plan = plan
                        self.status = status
                        self.errors = thermo_result.errors
                        self.warnings = []
                        # Add dependency warnings (empty for thermo)
                        unsatisfied_deps = []
                        if unsatisfied_deps:
                            self.warnings = [f"Missing dependency: {d}" for d in unsatisfied_deps]
                        self.thermo_result = thermo_result
            
                mock_result = MockResult(
                    thermo_result.decoded_output, 
                    None,  # No plan for thermo
                    "success",
                    [],  # No dependencies
                    thermo_result
                )
                
                # Create feedback
                feedback_metadata = {
                    'reasoning': f'Thermodynamic optimization completed in {thermo_result.latency_ms:.1f}ms',
                    'source': 'thermodynamic',
                    'energy_estimate': thermo_result.energy_estimate,
                    'converged': thermo_result.converged,
                    'solution_quality': thermo_result.solution_quality.__dict__ if thermo_result.solution_quality else None,
                    'n_samples': thermo_result.n_samples,
                    'entropy_production': thermo_result.entropy_production,
                }
                feedback = FeedbackResult(
                    type=FeedbackType.SUCCESS,
                    original_input=user_input,
                    generated_output=thermo_result.decoded_output,
                    errors=[],
                    warnings=mock_result.warnings,
                    confidence=1.0,
                    metadata=feedback_metadata,
                )
            else:
                # Thermodynamic failed
                mock_result = type('MockResult', (), {
                    'command': '# Thermodynamic optimization failed',
                    'status': 'error',
                    'errors': thermo_result.errors if thermo_result else ['Unknown error'],
                    'warnings': []
                })()
                
                feedback = FeedbackResult(
                    type=FeedbackType.SYNTAX_ERROR,
                    original_input=user_input,
                    generated_output='# Thermodynamic optimization failed',
                    errors=thermo_result.errors if thermo_result else ['Unknown thermodynamic error'],
                    warnings=[],
                )
        else:
            # DSL result - use existing pipeline as fallback
            from nlp2cmd.generation.pipeline import RuleBasedPipeline
            
            pipeline = RuleBasedPipeline()
            with measure_resources():
                pipeline_result = pipeline.process(user_input)
            
            if pipeline_result.success and pipeline_result.command and not pipeline_result.command.startswith('#'):
                # Create ExecutionPlan from PipelineResult
                from nlp2cmd.core.core_models import ExecutionPlan
                
                # Create a simple plan
                plan = ExecutionPlan(
                    intent=pipeline_result.intent,
                    entities=pipeline_result.entities,
                    confidence=pipeline_result.confidence,
                    metadata=dict(getattr(pipeline_result, "metadata", {}) or {}),
                    text=user_input
                )
                
                # Create result similar to NLP2CMD.transform
                class MockResult:
                    def __init__(self, command, plan, status, dependencies):
                        self.command = command
                        self.plan = plan
                        self.status = status
                        self.errors = []
                        self.warnings = []
                        # Add dependency warnings (empty for pipeline)
                        unsatisfied_deps = []  # Pipeline doesn't track dependencies
                        if unsatisfied_deps:
                            self.warnings = [f"Missing dependency: {d}" for d in unsatisfied_deps]
                
                mock_result = MockResult(
                    pipeline_result.command, 
                    plan, 
                    "success",
                    []  # No dependencies from pipeline
                )
                
                # Analyze feedback
                feedback = self.feedback_analyzer.analyze(
                    original_input=user_input,
                    generated_output=pipeline_result.command,
                    validation_errors=[],
                    validation_warnings=mock_result.warnings,
                    dsl_type=self.dsl,
                    context=self.context,
                )
                
                # Add pipeline metadata to feedback
                feedback_meta: dict[str, Any] = {
                    'reasoning': f'Generated by RuleBasedPipeline with confidence {pipeline_result.confidence:.2f}',
                    'entities': pipeline_result.entities,
                    'domain': pipeline_result.domain,
                    'intent': pipeline_result.intent,
                    'detection_confidence': pipeline_result.detection_confidence,
                    'template_used': pipeline_result.template_used,
                    'source': pipeline_result.source
                }
                pipeline_meta = getattr(pipeline_result, "metadata", None)
                if isinstance(pipeline_meta, dict) and pipeline_meta:
                    feedback_meta.update(pipeline_meta)
                feedback.metadata = feedback_meta
            else:
                # Handle failure case
                class MockResult:
                    def __init__(self, command, errors):
                        self.command = command
                        self.errors = errors
                        self.status = "error"
                
                mock_result = MockResult(pipeline_result.command, pipeline_result.errors)
                
                feedback = FeedbackResult(
                    type=FeedbackType.SYNTAX_ERROR,
                    original_input=user_input,
                    generated_output=pipeline_result.command,
                    errors=pipeline_result.errors,
                    warnings=[],
                )
        
        # Store in history
        self.history.append({
            "input": user_input,
            "result": mock_result,
            "feedback": feedback,
        })
        
        return feedback

    def display_feedback(self, feedback: FeedbackResult, include_explanation: bool = False):
        """Display feedback result with formatting."""
        from nlp2cmd.monitoring import format_last_metrics, estimate_token_cost

        # Build output data
        out: dict[str, Any] = {
            "dsl": getattr(self, "dsl", None),
            "query": feedback.original_input,
            "status": feedback.type.value,
            "confidence": float(feedback.confidence),
            "generated_command": (feedback.generated_output or "").strip() or None,
            "errors": list(feedback.errors or []),
            "warnings": list(feedback.warnings or []),
            "suggestions": list(feedback.suggestions or []),
            "clarification_questions": list(feedback.clarification_questions or []),
        }

        # Add explanation metadata if requested
        if include_explanation and feedback.metadata:
            out["reasoning"] = feedback.metadata.get('reasoning', 'N/A')
            out["domain"] = feedback.metadata.get('domain', 'N/A')
            out["intent"] = feedback.metadata.get('intent', 'N/A')
            out["detection_confidence"] = feedback.metadata.get('detection_confidence', 'N/A')
            out["template_used"] = feedback.metadata.get('template_used', 'N/A')
            out["source"] = feedback.metadata.get('source', 'N/A')
            
            # Add entities if available
            entities = feedback.metadata.get('entities', {})
            if entities:
                out["extracted_entities"] = entities

        if feedback.auto_corrections:
            out["auto_corrections"] = dict(feedback.auto_corrections)

        # Add metrics if available
        metrics_str = format_last_metrics()
        if metrics_str:
            try:
                from nlp2cmd.monitoring.token_costs import parse_metrics_string

                metrics = parse_metrics_string(metrics_str)
                if metrics:
                    out["resource_metrics"] = {
                        "time_ms": metrics.get("time_ms"),
                        "cpu_percent": metrics.get("cpu_percent"),
                        "memory_mb": metrics.get("memory_mb"),
                        "energy_mj": metrics.get("energy_mj")
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

        # Use centralized display function
        display_command_result(
            command=out.get("generated_command", ""),
            metadata=out,
            metrics_str=metrics_str,
            show_yaml=True,
            title="NLP2CMD Result"
        )

    def run(self):
        """Run interactive REPL."""
        print("```bash")
        # Use cached syntax highlighting for better performance
        syntax = get_cached_syntax("# NLP2CMD Interactive Mode\n# Type 'help' for commands, 'exit' to quit", "bash", theme="monokai", line_numbers=False)
        console.print(syntax)
        print("```")
        print()

        # Show environment info
        env = self.context["environment"]
        tools = self.context["available_tools"]
        config_count = len(self.context["config_files"])

        console.print(f"\n🔍 Environment: {env['os']['system']} ({env['os'].get('release', '')})")
        console.print(f"🛠️  Tools: {', '.join(tools.keys()) or 'none detected'}")
        console.print(f"📁 Config files: {config_count}")
        console.print()

        while True:
            try:
                user_input = console.input("[bold green]nlp2cmd>[/bold green] ").strip()

                if not user_input:
                    continue

                if user_input.lower() == "exit":
                    console.print("👋 Goodbye!")
                    break

                if user_input.lower() == "help":
                    self._show_help()
                    continue

                if user_input.startswith("!"):
                    self._handle_command(user_input[1:])
                    continue

                # Process input
                feedback = self.process(user_input)
                self.display_feedback(feedback)

                # Interactive correction loop
                if feedback.type != FeedbackType.SUCCESS:
                    self._correction_loop(feedback)

            except KeyboardInterrupt:
                console.print("\n👋 Interrupted. Type 'exit' to quit.")
            except EOFError:
                break

    def _show_help(self):
        """Display help information."""
        help_text = """
[bold]Commands:[/bold]
  !env          Show environment info
  !tools        List detected tools
  !files        List config files
  !history      Show command history
  !clear        Clear history

[bold]Examples:[/bold]
  Find files larger than 100MB
  Show all Docker containers
  Get users from database where city = 'Warsaw'
  Scale deployment nginx to 5 replicas
        """
        console.print(help_text)

    def _handle_command(self, cmd: str):
        """Handle special commands."""
        parts = cmd.split()
        command = parts[0] if parts else ""

        if command == "env":
            env = self.context["environment"]
            table = Table(title="Environment")
            table.add_column("Property", style="cyan")
            table.add_column("Value")

            table.add_row("OS", f"{env['os']['system']} {env['os'].get('release', '')}")
            table.add_row("Shell", env['shell'].get('name', 'unknown'))
            table.add_row("User", env['user'].get('name', 'unknown'))
            table.add_row("CWD", env.get('cwd', ''))

            console.print(table)

        elif command == "tools":
            tools = self.context["available_tools"]
            table = Table(title="Available Tools")
            table.add_column("Tool", style="cyan")
            table.add_column("Version")
            table.add_column("Path")

            for name, info in tools.items():
                table.add_row(name, info.version or "?", info.path or "")

            console.print(table)

        elif command == "files":
            files = self.context["config_files"]
            table = Table(title="Config Files")
            table.add_column("File", style="cyan")
            table.add_column("Size")

            for f in files:
                size = f.get("size", 0)
                size_str = f"{size / 1024:.1f} KB" if size > 1024 else f"{size} B"
                table.add_row(f.get("name", ""), size_str)

            console.print(table)

        elif command == "history":
            if not self.history:
                console.print("No history yet.")
            else:
                for i, item in enumerate(self.history[-10:], 1):
                    console.print(f"{i}. {item['input'][:50]}...")

        elif command == "clear":
            self.history.clear()
            console.print("History cleared.")

        else:
            console.print(f"Unknown command: {command}")

    def _correction_loop(self, feedback: FeedbackResult):
        """Interactive correction loop."""
        if feedback.type == FeedbackType.SUCCESS:
            return

        if feedback.requires_user_input:
            answers: list[str] = []
            questions = list(feedback.clarification_questions or [])
            if not questions:
                questions = ["Please clarify the request."]

            max_questions = 5
            for q in questions[:max_questions]:
                response = console.input(f"\n[yellow]{q}[/yellow] ").strip()
                if response:
                    answers.append(response)

            # Check if user declined installation instructions
            if answers and any(a.lower() in ['n', 'no'] for a in answers) and any("want" in q.lower() for q in questions):
                console.print("Installation instructions skipped.")
                return

            if answers:
                combined = " ".join(answers)
                self.context["user_clarification"] = combined
                new_feedback = self.process(f"{feedback.original_input}. {combined}")
                self.display_feedback(new_feedback)
                if new_feedback.type != FeedbackType.SUCCESS:
                    if new_feedback.requires_user_input:
                        self._correction_loop(new_feedback)
                return

        elif feedback.can_auto_fix and self.auto_repair:
            console.print("\n[cyan]Apply auto-corrections? [y/N]:[/cyan] ", end="")
            if console.input().strip().lower() == "y":
                for original, fixed in feedback.auto_corrections.items():
                    console.print(f"Applied: {fixed[:60]}...")

        missing_tool = feedback.metadata.get("missing_tool") if isinstance(feedback.metadata, dict) else None
        if isinstance(missing_tool, str) and missing_tool:
            console.print(f"\n[yellow]Missing tool detected:[/yellow] {missing_tool}")
            console.print("[cyan]Show installation hints? [y/N]:[/cyan] ", end="")
            if console.input().strip().lower() == "y":
                console.print("Which package manager do you use? (apt/dnf/yum/pacman/brew/other)")
                pm = console.input("[bold green]pm>[/bold green] ").strip().lower()
                hints = {
                    "apt": f"sudo apt-get update && sudo apt-get install -y {missing_tool}",
                    "dnf": f"sudo dnf install -y {missing_tool}",
                    "yum": f"sudo yum install -y {missing_tool}",
                    "pacman": f"sudo pacman -S {missing_tool}",
                    "brew": f"brew install {missing_tool}",
                }
                cmd = hints.get(pm)
                if cmd:
                    print(f"```bash")
                    # Use cached syntax highlighting for better performance
                    syntax = get_cached_syntax(cmd, "bash", theme="monokai", line_numbers=False)
                    console.print(syntax)
                    print(f"```")
                    print()
                else:
                    console.print(f"Install '{missing_tool}' using your system package manager or official docs.")


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


def _interactive_followup(session: InteractiveSession, feedback: FeedbackResult) -> FeedbackResult:
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


def handle_run_mode(
    query: str,
    dsl: str,
    appspec: Optional[Path],
    auto_confirm: bool,
    execute_web: bool,
    auto_install: bool,
    auto_repair: bool,
    only_output: bool = False,
):
    """
    Handle --run option: generate and execute command with error recovery.
    
    Features:
    - Generate command from natural language
    - Execute with real-time output
    - Detect errors and suggest recovery
    - Interactive retry loop with LLM assistance
    - Context-aware disambiguation from history
    """
    from nlp2cmd.generation.pipeline import RuleBasedPipeline
    from nlp2cmd import NLP2CMD
    from nlp2cmd.adapters import (
        SQLAdapter,
        ShellAdapter,
        DockerAdapter,
        KubernetesAdapter,
        DQLAdapter,
        AppSpecAdapter,
        BrowserAdapter,
    )
    from nlp2cmd import NLP2CMD, AppSpecAdapter, BrowserAdapter
    from nlp2cmd.web_schema.form_data_loader import FormDataLoader

    history_selected_command: str | None = None

    if not only_output:
        print(f"```bash")
        # Use cached syntax highlighting for better performance
        syntax = get_cached_syntax(f"# 🚀 Run Mode: {query}", "bash", theme="monokai", line_numbers=False)
        console.print(syntax)
        print(f"```")
        print()
    
    # Step 0: Check for similar queries in history (disambiguation)
    # - interactive mode: ask user to pick an option
    # - auto-confirm mode: auto-select only if similarity is very high
    try:
        from nlp2cmd.context.disambiguator import CommandDisambiguator

        disambiguator = CommandDisambiguator(console=console)
        result = disambiguator.disambiguate(query, auto_select=auto_confirm)

        if result.from_history and result.selected_command:
            if not only_output:
                print_yaml_block(
                    {
                        "status": "using_previous_command_from_history",
                        "selected_query": result.selected_query,
                    },
                    console=console,
                )
            query = result.selected_query
            history_selected_command = result.selected_command
    except Exception:
        pass

    # If the user selected a previous command from history, execute it directly.
    # This avoids regenerating a simpler command (e.g., browser/navigate) and losing
    # multi-step dom_dql.v1 sequences (fill_form/submit/etc.).
    if history_selected_command:
        cmd = history_selected_command.strip()

        # If it's dom_dql.v1 JSON, prefer executing via Playwright PipelineRunner.
        try:
            import json

            payload = json.loads(cmd)
        except Exception:
            payload = None

        if isinstance(payload, dict) and payload.get("dsl") == "dom_dql.v1":
            requires_web_execution = True

            confirmed_for_web = bool(auto_confirm or execute_web)

            if requires_web_execution and not execute_web and not auto_confirm:
                console.print(
                    "\n[yellow]Selected history command is dom_dql.v1 and requires browser automation (Playwright).[/yellow]"
                )
                resp = console.input("[yellow]Execute via Playwright now? [Y/n]: [/yellow]").strip().lower()
                if resp in {"n", "no", "nie"}:
                    console.print("[yellow]Cancelled by user[/yellow]")
                    return
                confirmed_for_web = True

            if not only_output:
                print(f"```bash")
                syntax = get_cached_syntax("# Using command from history\n " + cmd, "bash", theme="monokai", line_numbers=False)
                console.print(syntax)
                print(f"```")
                print()

            try:
                from nlp2cmd.ir import ActionIR
                from nlp2cmd.pipeline_runner import PipelineRunner

                # Ensure Playwright (and browsers) are installed.
                from nlp2cmd.utils.playwright_installer import ensure_playwright_installed

                if not ensure_playwright_installed(console=console, auto_install=auto_install):
                    if not only_output:
                        print_yaml_block(
                            {
                                "status": "browser_automation_skipped",
                                "reason": "playwright_not_available",
                            },
                            console=console,
                        )
                    _fallback_open_url_from_query(query)
                    return

                ir = ActionIR(
                    action_id=str(payload.get("action") or payload.get("actions") or "history.dom"),
                    dsl=cmd,
                    dsl_kind="dom",  # type: ignore[arg-type]
                    params={},
                    output_format="raw",  # type: ignore[arg-type]
                    confidence=1.0,
                    explanation="history command: dom_dql.v1",
                    metadata={},
                )

                runner = PipelineRunner(headless=False)
                res = runner.run(ir, dry_run=False, confirm=confirmed_for_web)
                if res.success:
                    if not only_output:
                        console.print(f"\n✅ Executed history web action in {res.duration_ms:.1f}ms")
                    return

                # Retry with explicit confirmation if required.
                if (not res.success) and isinstance(res.data, dict) and res.data.get("requires_confirmation"):
                    res2 = runner.run(ir, dry_run=False, confirm=True)
                    if res2.success:
                        if not only_output:
                            console.print(f"\n✅ Executed history web action in {res2.duration_ms:.1f}ms")
                        return
                    res = res2

                if not only_output:
                    console.print(f"\n[red]✗ Failed to execute history command: {res.error}[/red]")
                return
            except Exception as e:
                if not only_output:
                    console.print(f"\n[red]✗ Failed to execute history command: {e}[/red]")
                return

        # Otherwise treat it as a shell command and execute via existing runner.
        if cmd:
            if not only_output:
                print(f"```bash")
                syntax = get_cached_syntax("# Using command from history\n " + cmd, "bash", theme="monokai", line_numbers=False)
                console.print(syntax)
                print(f"```")
                print()

            if ExecutionRunner is None:
                from nlp2cmd.execution import ExecutionRunner as _ExecutionRunner
                runner_cls = _ExecutionRunner
            else:
                runner_cls = ExecutionRunner

            runner = runner_cls(
                console=console,
                auto_confirm=auto_confirm,
                max_retries=3,
                plain_output=only_output,
            )
            runner.run_with_recovery(cmd, query)
            return
    
    # Step 1: Generate command
    if not only_output:
        console.print("\n[dim]Generating command...[/dim]")
    
    adapter_map = {
        "sql": lambda: SQLAdapter(),
        "shell": lambda: ShellAdapter(),
        "docker": lambda: DockerAdapter(),
        "kubernetes": lambda: KubernetesAdapter(),
        "dql": lambda: DQLAdapter(),
        "appspec": lambda: AppSpecAdapter(appspec_path=str(appspec) if appspec else None),
        "browser": lambda: BrowserAdapter(),
    }

    # Step 2: Detect domain/intent and generate command
    command = None
    detected_domain = "unknown"
    detected_intent = "unknown"

    if dsl == "auto":
        pipeline = RuleBasedPipeline()
        result = pipeline.process(query)

        if (not _looks_like_log_input(query)) and (not result.success) and auto_repair:
            try:
                from nlp2cmd.generation.llm_simple import LiteLLMClient
                import asyncio

                llm = LiteLLMClient()
                result = pipeline.process_with_llm_repair(
                    query, llm_client=llm, persist=True, max_repairs=1,
                )
            except Exception:
                pass

        if result.success:
            command = result.command
            detected_domain = result.domain
            detected_intent = result.intent
        else:
            if only_output:
                sys.stderr.write("nlp2cmd: could not generate executable command\n")
                raise SystemExit(1)
            console.print(f"[red]✗ Could not generate command: {result.errors}[/red]")
            return
    else:
        adapter = adapter_map.get(dsl, lambda: ShellAdapter())()
        nlp = NLP2CMD(adapter=adapter)
        transform_result = nlp.transform(query)
        command = transform_result.command
        detected_domain = dsl
        detected_intent = getattr(getattr(transform_result, "plan", None), "intent", "unknown")

    if not only_output:
        print_yaml_block(
            {"status": "detected", "domain": detected_domain, "intent": detected_intent},
            console=console,
        )

    # Step 3: Handle SQL (no execution)
    if detected_domain == "sql":
        if only_output:
            sql_text = (command or "").rstrip() + "\n"
            if sql_text.strip():
                sys.stdout.write(sql_text)
            sys.stderr.write("Run Mode executes shell commands; SQL is not executed automatically.\n")
        else:
            print(f"```sql")
            syntax = get_cached_syntax(command, "sql", theme="monokai", line_numbers=False)
            console.print(syntax)
            print(f"```")
            console.print("[yellow]SQL is not executed automatically. Use your database client.[/yellow]")
        return

    # Step 4: Detect browser commands with typing/form actions
    is_browser_command = False
    detected_has_typing = False

    loader = FormDataLoader()
    typing_keywords = loader.get_nlp_keywords("typing")
    clicking_keywords = loader.get_nlp_keywords("clicking")
    form_keywords = FormDataLoader.dedupe_selectors([
        *loader.get_nlp_keywords("form"),
        *loader.get_nlp_keywords("submit"),
        *loader.get_nlp_keywords("fill_form_phrases"),
        *loader.get_nlp_keywords("press_enter"),
    ])

    query_lower = query.lower()
    has_typing = any(kw in query_lower for kw in typing_keywords)
    has_clicking = any(kw in query_lower for kw in clicking_keywords)
    has_form = any(kw in query_lower for kw in form_keywords)

    if dsl == "auto":
        if detected_domain == "shell" and detected_intent in ("open_url", "search_web"):
            is_browser_command = True
            detected_has_typing = has_typing or has_clicking or has_form
            if detected_has_typing and not execute_web:
                if not only_output:
                    print_yaml_block(
                        {"status": "browser_automation_auto_enabled", "reason": "detected_typing_clicking_or_form_action"},
                        console=console,
                    )
                execute_web = True
    elif dsl == "browser":
        is_browser_command = True
        detected_has_typing = True
        if not execute_web:
            execute_web = True

    # Step 5: Execute
    if ExecutionRunner is None:
        from nlp2cmd.execution import ExecutionRunner as _ExecutionRunner
        runner_cls = _ExecutionRunner
    else:
        runner_cls = ExecutionRunner

    runner = runner_cls(
        console=console,
        auto_confirm=auto_confirm,
        max_retries=3,
        plain_output=only_output,
    )

    if is_browser_command and execute_web and detected_has_typing:
        if not only_output:
            console.print("\n[cyan]Using Playwright for browser automation...[/cyan]")

        from nlp2cmd.utils.playwright_installer import ensure_playwright_installed

        if not ensure_playwright_installed(console=console, auto_install=auto_install):
            if not only_output:
                print_yaml_block({"status": "browser_automation_skipped", "reason": "playwright_not_available"}, console=console)
            _fallback_open_url_from_query(query)
            return

        try:
            browser_adapter = BrowserAdapter()
            nlp_browser = NLP2CMD(adapter=browser_adapter)
            ir = nlp_browser.transform_ir(query)

            if not only_output:
                import json as _json
                payload_info: dict[str, Any] = {
                    "status": "actions",
                    "action_id": getattr(ir, "action_id", ""),
                    "dsl_kind": getattr(ir, "dsl_kind", ""),
                    "confidence": getattr(ir, "confidence", 0.0),
                    "explanation": getattr(ir, "explanation", ""),
                }
                try:
                    dsl_payload = _json.loads(getattr(ir, "dsl", "") or "")
                    if isinstance(dsl_payload, dict):
                        if isinstance(dsl_payload.get("url"), str):
                            payload_info["url"] = dsl_payload["url"]
                        actions = dsl_payload.get("actions")
                        if isinstance(actions, list):
                            payload_info["actions_count"] = len(actions)
                            payload_info["actions"] = [a.get("action") for a in actions if isinstance(a, dict)]
                except Exception:
                    pass
                print_yaml_block(payload_info, console=console)

            from nlp2cmd.pipeline_runner import PipelineRunner
            pw_runner = PipelineRunner(headless=False)
            pw_result = pw_runner.run(ir, dry_run=False, confirm=auto_confirm)

            if (not pw_result.success) and isinstance(pw_result.data, dict) and pw_result.data.get("requires_confirmation"):
                reason = str(pw_result.data.get("confirmation_reason") or "unknown")
                url_for_confirm = str(pw_result.data.get("url") or "")
                data_loader_for_confirm = FormDataLoader(site=url_for_confirm) if url_for_confirm else FormDataLoader()

                approved = False
                if reason in {"submit", "press_enter"}:
                    approved = data_loader_for_confirm.get_site_approval(reason)

                if not approved and not auto_confirm:
                    if reason == "submit":
                        timed_prompt = "\n[yellow]This action will submit a form. Proceed? (auto-Y in 1s; Enter=choose):[/yellow] "
                        full_prompt = "\n[yellow]This action will submit a form. Proceed? [[y/N/a(always)]]:[/yellow] "
                    elif reason == "press_enter":
                        timed_prompt = "\n[yellow]Press Enter action. Proceed? (auto-Y in 1s; Enter=choose):[/yellow] "
                        full_prompt = "\n[yellow]Press Enter action. Proceed? [[y/N/a(always)]]:[/yellow] "
                    else:
                        timed_prompt = "\n[yellow]Confirm action? (auto-Y in 1s):[/yellow] "
                        full_prompt = "\n[yellow]Confirm action? [[y/N]]:[/yellow] "

                    resp = _timed_default_yes(timed_prompt=timed_prompt, full_prompt=full_prompt)
                    if resp in {"a", "always"} and reason in {"submit", "press_enter"}:
                        data_loader_for_confirm.set_site_approval(reason, True)
                        approved = True
                    elif resp in {"y", "yes", "tak"}:
                        approved = True

                if not approved and not auto_confirm:
                    if not only_output:
                        console.print("[yellow]Cancelled by user[/yellow]")
                    return

                pw_result = pw_runner.run(ir, dry_run=False, confirm=True)

            if pw_result.success:
                if not only_output:
                    print_yaml_block(
                        {
                            "status": "browser_automation_completed",
                            "success": True,
                            "duration_ms": float(pw_result.duration_ms),
                        },
                        console=console,
                    )
                return

            if not only_output:
                print_yaml_block({"status": "browser_automation_failed", "error": str(pw_result.error or "")}, console=console)
            _fallback_open_url_from_query(query)
            return
        except Exception as e:
            if not only_output:
                print_yaml_block({"status": "playwright_error", "error": str(e)}, console=console)
            _fallback_open_url_from_query(query)
            return
    else:
        # Execute shell command with recovery
        if not only_output:
            print(f"```bash")
            syntax = get_cached_syntax(command, "bash", theme="monokai", line_numbers=False)
            console.print(syntax)
            print(f"```")
            print()

        exec_result = runner.run_with_recovery(command, query)

        if not exec_result.success:
            if exec_result.error_context:
                _suggest_next_steps(query, command, exec_result, runner)


def _handle_run_query(
    query: str,
    *,
    dsl: str,
    appspec: Optional[Path],
    auto_confirm: bool,
    execute_web: bool,
    auto_install: bool,
    auto_repair: bool,
    only_output: bool = False,
) -> None:
    handle_run_mode(
        query,
        dsl=dsl,
        appspec=appspec,
        auto_confirm=auto_confirm,
        execute_web=execute_web,
        auto_install=auto_install,
        auto_repair=auto_repair,
        only_output=only_output,
    )
    return


def _suggest_next_steps(
    original_query: str,
    command: str,
    result,
    runner: ExecutionRunner,
):
    """Suggest next steps based on error context."""
    error = (result.stderr or result.stdout or "").lower()
    
    suggestions = []
    
    if "command not found" in error:
        cmd_parts = command.split()
        if cmd_parts:
            tool = cmd_parts[0]
            suggestions.append(f"Install missing tool: {tool}")
            suggestions.append("Check if the tool is in your PATH")
    
    if "permission denied" in error:
        suggestions.append(f"Try with sudo: sudo {command}")
    
    if "connection refused" in error or "could not connect" in error:
        suggestions.append("Check if the target service is running")
        suggestions.append("Verify the hostname/port is correct")
    
    if "no such file" in error:
        suggestions.append("Verify the file/directory path exists")
    
    if "playwright" in error:
        suggestions.append("Install Playwright: pip install playwright && playwright install")
    
    if suggestions:
        console.print("\n[yellow]💡 Suggestions:[/yellow]")
        for i, s in enumerate(suggestions, 1):
            console.print(f"  {i}. {s}")
        
        console.print("\n[cyan]Would you like to try another command? [y/N]:[/cyan] ", end="")
        response = console.input().strip().lower()
        
        if response in ("y", "yes", "tak"):
            new_query = console.input("[bold green]Enter new query or command: [/bold green]").strip()
            if new_query:
                if new_query.startswith("!"):
                    # Direct command execution
                    runner.run_with_recovery(new_query[1:].strip(), original_query)
                else:
                    # Generate new command from query
                    from nlp2cmd.generation.pipeline import RuleBasedPipeline
                    pipeline = RuleBasedPipeline()
                    new_result = pipeline.process(new_query)
                    if new_result.success:
                        runner.run_with_recovery(new_result.command, new_query)
                    else:
                        console.print(f"[red]Could not generate command from: {new_query}[/red]")


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
    file_path = Path(file)
    registry = SchemaRegistry()

    # Detect format
    schema = registry.detect_format(file_path)
    if not schema:
        console.print(f"[red]Unknown file format: {file}[/red]")
        return

    console.print(f"🔍 Detected format: [cyan]{schema.name}[/cyan]")

    # Read content
    content = file_path.read_text()

    # Validate
    validation = registry.validate(content, schema.name.lower())

    if validation.get("errors"):
        console.print("\n[red]Errors found:[/red]")
        for error in validation["errors"]:
            console.print(f"  • {error}")

    if validation.get("warnings"):
        console.print("\n[yellow]Warnings:[/yellow]")
        for warning in validation["warnings"]:
            console.print(f"  • {warning}")

    # Repair
    result = registry.repair(content, schema.name.lower(), auto_fix=True)

    if result["changes"]:
        console.print("\n[cyan]Changes:[/cyan]")
        for change in result["changes"]:
            if change.get("type") == "fixed":
                console.print(f"  ✅ {change.get('reason', 'Fixed')}")
            else:
                console.print(f"  ⚠️  {change.get('reason', 'Warning')}")

        if result["repaired"]:
            if backup:
                backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                backup_path.write_text(content)
                console.print(f"\n💾 Backup: {backup_path}")

            file_path.write_text(result["content"])
            console.print(f"✅ Saved: {file}")
    else:
        console.print("\n✅ No issues found!")


@_command_decorator
@click.argument("file", type=click.Path(exists=True))
@click.pass_context
def validate(ctx, file: str):
    """Validate a configuration file."""
    file_path = Path(file)
    registry = SchemaRegistry()

    schema = registry.detect_format(file_path)
    if not schema:
        console.print(f"[red]Unknown file format: {file}[/red]")
        return

    console.print(f"🔍 Format: [cyan]{schema.name}[/cyan]")

    content = file_path.read_text()
    result = registry.validate(content, schema.name.lower())

    if result.get("valid"):
        console.print("✅ [green]Valid![/green]")
    else:
        console.print("❌ [red]Invalid[/red]")

    if result.get("errors"):
        for error in result["errors"]:
            console.print(f"  [red]• {error}[/red]")

    if result.get("warnings"):
        for warning in result["warnings"]:
            console.print(f"  [yellow]• {warning}[/yellow]")


@_command_decorator
@click.option("-o", "--output", type=click.Path(), help="Output file (JSON)")
@click.pass_context
def analyze_env(ctx, output: Optional[str]):
    """Analyze system environment."""
    analyzer = EnvironmentAnalyzer()
    report = analyzer.full_report()

    if output:
        # Convert to dict for JSON serialization
        report_dict = {
            "os": report.os_info,
            "tools": {
                name: {
                    "available": info.available,
                    "version": info.version,
                    "path": info.path,
                }
                for name, info in report.tools.items()
            },
            "services": {
                name: {
                    "running": info.running,
                    "port": info.port,
                    "reachable": info.reachable,
                }
                for name, info in report.services.items()
            },
            "config_files": report.config_files,
            "resources": report.resources,
            "recommendations": report.recommendations,
        }

        with open(output, "w") as f:
            json.dump(report_dict, f, indent=2)

        console.print(f"📄 Report saved: {output}")
    else:
        # Display in terminal
        console.print(Panel.fit(
            f"[bold]System:[/bold] {report.os_info['system']} {report.os_info.get('release', '')}",
            title="Environment Report",
        ))

        # Tools table
        table = Table(title="Tools")
        table.add_column("Tool")
        table.add_column("Version")
        table.add_column("Status")

        for name, info in report.tools.items():
            status = "✅" if info.available else "❌"
            table.add_row(name, info.version or "-", status)

        console.print(table)

        # Services table
        table = Table(title="Services")
        table.add_column("Service")
        table.add_column("Port")
        table.add_column("Status")

        for name, info in report.services.items():
            status = "🟢" if info.running else "🔴"
            port = str(info.port) if info.port else "-"
            table.add_row(name, port, status)

        console.print(table)

        if report.recommendations:
            console.print("\n[yellow]Recommendations:[/yellow]")
            for rec in report.recommendations:
                console.print(f"  • {rec}")


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
