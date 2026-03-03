"""
NLP2CMD Examples Launcher - Preconfigured scenario runner.

Provides unified interface for running all examples with preconfiguration:
nlp2cmd examples list              # Show all available examples
nlp2cmd examples run 01_draw_chat   # Run specific example
nlp2cmd examples draw "red star"    # Quick draw command
nlp2cmd examples autonomous "cat"     # Run autonomous pipeline

Each example scenario has:
- Preconfigured dependencies (auto-install)
- Preconfigured browser settings
- Preconfigured logging
- Unified error handling
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

try:
    import click
except ImportError:
    click = None  # type: ignore

try:
    from rich.console import Console
    from rich.table import Table
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    Console = None  # type: ignore

# Import evolutionary orchestrator for autonomous recovery
try:
    from nlp2cmd.evolutionary_orchestrator import AutonomousExampleRunner
    HAS_EVOLUTIONARY = True
except ImportError:
    HAS_EVOLUTIONARY = False


@dataclass
class ExampleScenario:
    """Definition of an example scenario."""
    id: str
    name: str
    description: str
    category: str
    script_path: Path
    needs_playwright: bool = True
    needs_llm: bool = False
    args_template: list[str] = field(default_factory=list)
    env_setup: dict[str, str] = field(default_factory=dict)
    pre_check: Optional[callable] = None


class ExamplesRegistry:
    """Registry of all available example scenarios."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.scenarios: dict[str, ExampleScenario] = {}
        self._discover()

    def _discover(self):
        """Auto-discover examples from examples/09_online_drawing."""
        drawing_dir = self.base_dir.parent / "examples" / "09_online_drawing"

        scenarios = [
            ExampleScenario(
                id="01_draw_chat",
                name="Draw Chat",
                description="Draw shapes on draw.chat whiteboard",
                category="drawing",
                script_path=drawing_dir / "01_draw_chat" / "run.py",
                needs_playwright=True,
                args_template=["--shape", "house", "--color", "blue"],
            ),
            ExampleScenario(
                id="02_picsart",
                name="Picsart",
                description="Paint patterns on Picsart/Kleki",
                category="drawing",
                script_path=drawing_dir / "02_picsart" / "run.py",
                needs_playwright=True,
            ),
            ExampleScenario(
                id="03_adaptive",
                name="Adaptive Drawing",
                description="LLM-guided drawing with adaptive routing",
                category="drawing",
                script_path=drawing_dir / "03_adaptive" / "run.py",
                needs_playwright=True,
                needs_llm=True,
                args_template=["--query", "draw a blue star"],
            ),
            ExampleScenario(
                id="04_object_database",
                name="Object Database",
                description="Multi-object drawing from online databases",
                category="drawing",
                script_path=drawing_dir / "04_object_database" / "run.py",
                needs_playwright=True,
            ),
            ExampleScenario(
                id="05_autonomous",
                name="Autonomous Pipeline",
                description="Full autonomous pipeline with validation",
                category="drawing",
                script_path=drawing_dir / "05_autonomous" / "run.py",
                needs_playwright=True,
                needs_llm=True,
            ),
            ExampleScenario(
                id="06_visual_validator",
                name="Visual Validator",
                description="Vision-based drawing validation",
                category="validation",
                script_path=drawing_dir / "06_visual_validator" / "run.py",
                needs_playwright=True,
                needs_llm=True,
            ),
            ExampleScenario(
                id="07_shape_gallery",
                name="Shape Gallery",
                description="Browse all available shapes",
                category="drawing",
                script_path=drawing_dir / "07_shape_gallery" / "run.py",
                needs_playwright=True,
            ),
            ExampleScenario(
                id="08_search_demo",
                name="Search Demo",
                description="Open source internet search (DuckDuckGo/SearXNG)",
                category="search",
                script_path=drawing_dir / "08_search_demo" / "run.py",
                needs_playwright=False,
            ),
        ]

        for s in scenarios:
            self.scenarios[s.id] = s

    def list(self, category: Optional[str] = None) -> list[ExampleScenario]:
        """List all scenarios, optionally filtered by category."""
        result = list(self.scenarios.values())
        if category:
            result = [s for s in result if s.category == category]
        return result

    def get(self, scenario_id: str) -> Optional[ExampleScenario]:
        """Get scenario by ID."""
        return self.scenarios.get(scenario_id)


class ExamplesRunner:
    """Runner for example scenarios with preconfiguration."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console
        self.src_dir = Path(__file__).resolve().parents[3]  # src/nlp2cmd/cli/commands
        self.registry = ExamplesRegistry(self.src_dir)

    def _print(self, message: str, style: str = ""):
        """Print with or without rich."""
        if self.console and HAS_RICH:
            self.console.print(message, style=style)
        else:
            print(message)

    def _ensure_playwright(self, auto_install: bool = True) -> bool:
        """Ensure Playwright is installed and browsers available."""
        try:
            from nlp2cmd.utils.playwright_installer import ensure_playwright_installed
            return ensure_playwright_installed(console=self.console, auto_install=auto_install)
        except Exception as e:
            self._print(f"⚠ Playwright check failed: {e}", "yellow")
            return False

    def _ensure_env(self, scenario: ExampleScenario):
        """Setup environment for scenario."""
        # Set environment variables
        for key, value in scenario.env_setup.items():
            os.environ[key] = value

        # Ensure output dirs exist
        script_dir = scenario.script_path.parent
        (script_dir / "logs").mkdir(exist_ok=True)
        (script_dir / "screenshots").mkdir(exist_ok=True)

    def list_scenarios(self, category: Optional[str] = None):
        """Display list of scenarios."""
        scenarios = self.registry.list(category)

        if not scenarios:
            self._print("No examples found.", "red")
            return

        if HAS_RICH and self.console:
            table = Table(title="NLP2CMD Examples")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Category", style="blue")
            table.add_column("Description", style="white")
            table.add_column("Requirements", style="yellow")

            for s in scenarios:
                reqs = []
                if s.needs_playwright:
                    reqs.append("Playwright")
                if s.needs_llm:
                    reqs.append("LLM")

                table.add_row(
                    s.id,
                    s.name,
                    s.category,
                    s.description,
                    ", ".join(reqs) if reqs else "None",
                )

            self.console.print(table)
        else:
            print("\nNLP2CMD Examples:")
            print("-" * 80)
            for s in scenarios:
                reqs = []
                if s.needs_playwright:
                    reqs.append("Playwright")
                if s.needs_llm:
                    reqs.append("LLM")
                print(f"  {s.id:20} {s.name:20} [{s.category}] {s.description}")
                if reqs:
                    print(f"                       Requires: {', '.join(reqs)}")
            print("-" * 80)
            print(f"\nRun: nlp2cmd examples run <id>")

    def run_scenario(
        self,
        scenario_id: str,
        args: Optional[list[str]] = None,
        headless: bool = False,  # Default: visible (not headless)
        verbose: bool = False,
        auto_install: bool = True,
    ) -> bool:
        """Run a specific scenario with evolutionary autonomous recovery."""
        scenario = self.registry.get(scenario_id)
        if not scenario:
            self._print(f"Unknown example: {scenario_id}", "red")
            self._print("Run 'nlp2cmd examples list' to see available examples.")
            return False

        # Check if script exists
        if not scenario.script_path.exists():
            self._print(f"Script not found: {scenario.script_path}", "red")
            return False

        self._print(f"🎨 Running: {scenario.name}", "bold cyan")
        self._print(f"   {scenario.description}")
        self._print("")
        
        # Use evolutionary orchestrator if available
        if HAS_EVOLUTIONARY:
            self._print("🧬 Using Evolutionary Autonomous Orchestrator...", "dim")
            autonomous_runner = AutonomousExampleRunner(self.console)
            
            # Prepare env setup
            env_setup = scenario.env_setup.copy()
            
            # Add common env vars
            env_setup.setdefault("PYTHONPATH", str(self.src_dir))
            
            # Build args list
            final_args = []
            if not args and scenario.args_template:
                final_args = scenario.args_template.copy()
            elif args:
                final_args = list(args)
            
            # Add flags
            if headless:
                final_args.append("--headless")
            if verbose:
                final_args.append("-v")
            
            # Run with evolutionary recovery (NEVER GIVE UP)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            success, metrics = loop.run_until_complete(
                autonomous_runner.run_example(
                    scenario_id,
                    scenario.script_path,
                    final_args,
                    env_setup,
                )
            )
            
            # Print learning report
            if verbose:
                report = autonomous_runner.get_learning_report()
                self._print(f"\n📊 Learning Report:", "blue")
                for key, value in report.items():
                    self._print(f"   {key}: {value}", "dim")
            
            return success
        else:
            # Fallback to simple execution
            return self._run_simple(scenario, args, headless, verbose, auto_install)

    def _run_simple(
        self,
        scenario: ExampleScenario,
        args: Optional[list[str]] = None,
        headless: bool = False,
        verbose: bool = False,
        auto_install: bool = True,
    ) -> bool:
        """Simple execution fallback without evolutionary recovery."""
        # Pre-flight checks
        if scenario.needs_playwright:
            self._print("📦 Checking Playwright...")
            if not self._ensure_playwright(auto_install=auto_install):
                self._print("   ⚠ Playwright not available. Install with: python -m playwright install chromium")
                if not auto_install:
                    return False

        # Setup environment
        self._ensure_env(scenario)

        # Build command
        cmd = [sys.executable, str(scenario.script_path)]

        # Add default args if no custom args
        if not args and scenario.args_template:
            cmd.extend(scenario.args_template)
        elif args:
            cmd.extend(args)

        # Add common flags
        if headless:
            cmd.append("--headless")
        if verbose:
            cmd.append("-v")

        if verbose:
            self._print(f"   Command: {' '.join(cmd)}", "dim")
            self._print("")

        # Run the script
        import subprocess
        try:
            result = subprocess.run(cmd, cwd=str(scenario.script_path.parent))
            return result.returncode == 0
        except Exception as e:
            self._print(f"✗ Error running example: {e}", "red")
            return False

    def run_quick_draw(
        self,
        description: str,
        target: str = "jspaint",
        headless: bool = False,
        verbose: bool = False,
    ) -> bool:
        """Quick draw command using 03_adaptive example."""
        scenario = self.registry.get("03_adaptive")
        if not scenario:
            self._print("Adaptive drawing example not found", "red")
            return False

        args = ["--query", description, "--target", target]
        return self.run_scenario(
            "03_adaptive",
            args=args,
            headless=headless,
            verbose=verbose,
        )

    def run_autonomous(
        self,
        description: str,
        headless: bool = False,
        verbose: bool = False,
    ) -> bool:
        """Run autonomous pipeline."""
        scenario = self.registry.get("05_autonomous")
        if not scenario:
            self._print("Autonomous example not found", "red")
            return False

        # Run with description as positional arg
        return self.run_scenario(
            "05_autonomous",
            args=[description],
            headless=headless,
            verbose=verbose,
        )


# Click CLI integration
try:
    import click

    @click.group(name="examples")
    @click.pass_context
    def examples_group(ctx):
        """Run preconfigured example scenarios."""
        ctx.ensure_object(dict)
        ctx.obj["runner"] = ExamplesRunner()

    @examples_group.command(name="list")
    @click.option("--category", help="Filter by category (drawing, validation)")
    @click.pass_context
    def cmd_list(ctx, category: Optional[str]):
        """List all available examples."""
        runner: ExamplesRunner = ctx.obj["runner"]
        runner.list_scenarios(category)

    @examples_group.command(name="run", context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
    @click.argument("example_id")
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    @click.option("--headless", is_flag=True, help="Run browser in headless mode")
    @click.option("-v", "--verbose", is_flag=True, help="Verbose output")
    @click.option("--no-auto-install", is_flag=True, help="Skip auto-install of dependencies")
    @click.pass_context
    def cmd_run(ctx, example_id: str, args: tuple, headless: bool, verbose: bool, no_auto_install: bool):
        """Run a specific example by ID."""
        runner: ExamplesRunner = ctx.obj["runner"]
        success = runner.run_scenario(
            example_id,
            args=list(args) if args else None,
            headless=headless,
            verbose=verbose,
            auto_install=not no_auto_install,
        )
        ctx.exit(0 if success else 1)

    @examples_group.command(name="draw", context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
    @click.argument("description")
    @click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
    @click.option("--target", default="jspaint", help="Target drawing site (jspaint, excalidraw, kleki)")
    @click.option("--headless", is_flag=True, help="Run browser in headless mode")
    @click.option("-v", "--verbose", is_flag=True, help="Verbose output")
    @click.pass_context
    def cmd_draw(ctx, description: str, target: str, headless: bool, verbose: bool, extra_args: tuple):
        """Quick draw command: nlp2cmd examples draw 'red star'."""
        runner: ExamplesRunner = ctx.obj["runner"]
        # Build args: description first, then any extra args passed through
        args = [description] + list(extra_args)
        success = runner.run_scenario(
            "03_adaptive",
            args=args,
            headless=headless,
            verbose=verbose,
        )
        ctx.exit(0 if success else 1)

    @examples_group.command(name="autonomous", context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
    @click.argument("description")
    @click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
    @click.option("--headless", is_flag=True, help="Run browser in headless mode")
    @click.option("-v", "--verbose", is_flag=True, help="Verbose output")
    @click.pass_context
    def cmd_autonomous(ctx, description: str, headless: bool, verbose: bool, extra_args: tuple):
        """Run autonomous drawing pipeline."""
        runner: ExamplesRunner = ctx.obj["runner"]
        # Pass description and any extra args through
        args = [description] + list(extra_args)
        success = runner.run_scenario(
            "05_autonomous",
            args=args,
            headless=headless,
            verbose=verbose,
        )
        ctx.exit(0 if success else 1)

    @examples_group.command(name="search")
    @click.argument("query")
    @click.option("--max-results", type=int, default=5, help="Max results to show")
    @click.option("--source", default="auto", help="Search source: duckduckgo, searxng, auto")
    @click.pass_context
    def cmd_search(ctx, query: str, max_results: int, source: str):
        """Quick open source search: nlp2cmd examples search 'Python tutorial'."""
        import asyncio
        from nlp2cmd.skills.search import SearchSkill
        
        async def do_search():
            async with SearchSkill() as skill:
                results = await skill.search(query, max_results=max_results, source=source if source != "auto" else None)
                
                if not results:
                    print("No results found.")
                    return
                
                print(f"\n🔍 Results for: {query}\n")
                for i, r in enumerate(results, 1):
                    icon = {"duckduckgo": "🦆", "searxng": "🔍", "brave": "🦁"}.get(r.source, "📄")
                    print(f"{icon} {i}. {r.title}")
                    print(f"   {r.url}")
                    if r.snippet:
                        print(f"   {r.snippet[:120]}...")
                    print()
        
        asyncio.run(do_search())
        ctx.exit(0)

    @examples_group.command(name="metrics")
    @click.pass_context
    def cmd_metrics(ctx):
        """Show evolutionary learning metrics and statistics."""
        try:
            from nlp2cmd.evolutionary_orchestrator import EvolutionaryRecoveryEngine
            console = Console() if HAS_RICH else None
            engine = EvolutionaryRecoveryEngine(console)
            
            print("\n📊 Evolutionary Learning Metrics\n")
            print("=" * 50)
            
            # Show knowledge base summary
            kb = engine.knowledge_base
            patterns = kb.get("error_patterns", {})
            insights = kb.get("llm_insights", [])
            
            print(f"Error patterns learned: {len(patterns)}")
            print(f"LLM insights recorded: {len(insights)}")
            print(f"Database version: {kb.get('version', 1)}")
            print(f"Database location: {engine.learning_db_path}")
            print()
            
            # Show success rates
            if patterns:
                print("Strategy Success Rates:")
                for error_type, strategies in patterns.items():
                    print(f"\n  {error_type}:")
                    for strategy, stats in strategies.items():
                        attempts = stats.get("attempts", 0)
                        successes = stats.get("successes", 0)
                        rate = (successes / attempts * 100) if attempts > 0 else 0
                        print(f"    {strategy}: {rate:.0f}% ({successes}/{attempts})")
            
            print("=" * 50)
            print("\n💡 Tip: Metrics improve automatically with each execution")
            print("   The system learns which strategies work best for different errors.\n")
            
        except ImportError:
            print("Evolutionary orchestrator not available.")
            ctx.exit(1)

    @examples_group.command(name="learn")
    @click.option("--reset", is_flag=True, help="Reset learning database")
    @click.pass_context
    def cmd_learn(ctx, reset: bool):
        """Manage evolutionary learning database."""
        db_path = Path.home() / ".nlp2cmd" / "evolutionary_learning.json"
        
        if reset:
            if db_path.exists():
                db_path.unlink()
                print("✓ Learning database reset")
            else:
                print("No learning database to reset")
        else:
            if db_path.exists():
                print(f"Learning database: {db_path}")
                data = json.loads(db_path.read_text())
                print(f"Size: {db_path.stat().st_size} bytes")
                print(f"Patterns: {len(data.get('error_patterns', {}))}")
            else:
                print("No learning database yet - will be created on first run")

    @examples_group.command(name="doctor")
    @click.option("--fix", is_flag=True, help="Auto-fix issues")
    @click.pass_context
    def cmd_examples_doctor(ctx, fix: bool):
        """Diagnose examples environment and dependencies."""
        console = Console() if HAS_RICH else None
        runner = ExamplesRunner(console)
        
        print("\n🔍 Examples Environment Doctor\n")
        print("=" * 50)
        
        # Check evolutionary orchestrator
        print("✓ Evolutionary Orchestrator: " + ("Available" if HAS_EVOLUTIONARY else "Not Available"))
        
        # Check Playwright
        print("Checking Playwright...")
        has_pw = runner._ensure_playwright(auto_install=False)
        print("  " + ("✓ Playwright ready" if has_pw else "✗ Playwright not installed"))
        
        # Check scenarios
        print(f"\nRegistered examples: {len(runner.registry.scenarios)}")
        for sid, scenario in runner.registry.scenarios.items():
            exists = "✓" if scenario.script_path.exists() else "✗"
            print(f"  {exists} {sid}: {scenario.name}")
        
        # Check learning DB
        db_path = Path.home() / ".nlp2cmd" / "evolutionary_learning.json"
        print(f"\nLearning database: {db_path}")
        print("  " + ("✓ Exists" if db_path.exists() else "○ Will be created on first run"))
        
        print("=" * 50)
        print()

except ImportError:
    # Click not available - define stubs
    def examples_group(*args, **kwargs):
        pass

    def cmd_list(*args, **kwargs):
        pass

    def cmd_run(*args, **kwargs):
        pass

    def cmd_draw(*args, **kwargs):
        pass

    def cmd_autonomous(*args, **kwargs):
        pass

    def cmd_metrics(*args, **kwargs):
        pass

    def cmd_learn(*args, **kwargs):
        pass

    def cmd_examples_doctor(*args, **kwargs):
        pass
