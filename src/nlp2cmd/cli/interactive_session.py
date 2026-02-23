"""
Interactive session module for NLP2CMD CLI.

Provides REPL functionality with feedback loop and environment analysis.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
except Exception:  # pragma: no cover
    class Console:  # type: ignore
        def print(self, *args, **kwargs):
            print(*args, **kwargs)

        def input(self, *args, **kwargs):
            return ""

    class Panel:  # type: ignore
        def __init__(self, renderable, *args, **kwargs):
            self.renderable = renderable

    class Table:  # type: ignore
        def __init__(self, *args, **kwargs):
            return

from nlp2cmd.cli.display import display_command_result
from nlp2cmd.cli.syntax_cache import get_cached_syntax
from nlp2cmd.feedback import FeedbackResult, FeedbackType


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
        console = Console()
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
        console = Console()
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
        console = Console()
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
        console = Console()
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
                    from nlp2cmd.cli.syntax_cache import get_cached_syntax
                    syntax = get_cached_syntax(cmd, "bash", theme="monokai", line_numbers=False)
                    console.print(syntax)
                    print(f"```")
                    print()
                else:
                    console.print(f"Install '{missing_tool}' using your system package manager or official docs.")
