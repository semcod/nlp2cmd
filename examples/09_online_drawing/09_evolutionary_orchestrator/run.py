#!/usr/bin/env python3
"""
09_evolutionary_orchestrator - Demonstracja "Never Give Up" Engine

Ten przykład pokazuje jak EvolutionaryOrchestrator automatycznie:
- Naprawia błędy podczas wykonania
- Konsultuje się z LLM przy problemach
- Uczy się najlepszych strategii naprawy
- Nigdy nie poddaje się bez próby recovery

Użycie:
    python3 run.py --scenario dependency_error    # Symuluje brak zależności
    python3 run.py --scenario timeout            # Symuluje timeout
    python3 run.py --scenario success            # Normalne wykonanie
    python3 run.py --list                        # Lista scenariuszy
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from nlp2cmd import (
    EvolutionaryRecoveryEngine,
    AutonomousExampleRunner,
    RecoveryStrategy,
    ExecutionMetrics,
)


console = Console()


# Predefined scenarios for demonstration
SCENARIOS = {
    "success": {
        "description": "Normalne wykonanie bez błędów",
        "will_fail": False,
        "fail_after": 0,
    },
    "dependency_error": {
        "description": "Symuluje brak zależności (ModuleNotFoundError)",
        "will_fail": True,
        "fail_type": "DEPENDENCY_ERROR",
        "fail_message": "ModuleNotFoundError: No module named 'playwright'",
        "recoverable": True,
    },
    "timeout": {
        "description": "Symuluje timeout podczas wykonania",
        "will_fail": True,
        "fail_type": "TIMEOUT_ERROR",
        "fail_message": "TIMEOUT_ERROR: Script execution exceeded 120s",
        "recoverable": True,
    },
    "hf_token_error": {
        "description": "Symuluje brak HF_TOKEN",
        "will_fail": True,
        "fail_type": "HF_TOKEN_ERROR",
        "fail_message": "HF_TOKEN_ERROR: HuggingFace token not found",
        "recoverable": True,
    },
    "unrecoverable": {
        "description": "Symuluje nieodwracalny błąd",
        "will_fail": True,
        "fail_type": "EXECUTION_ERROR",
        "fail_message": "EXECUTION_ERROR: Critical system failure",
        "recoverable": False,
    },
}


async def mock_example_execution(context: dict) -> dict:
    """
    Symuluje wykonanie przykładu z możliwością błędu.
    W prawdziwym użyciu byłoby to uruchomienie np. 03_adaptive/run.py
    """
    scenario = context.get("scenario", "success")
    config = SCENARIOS.get(scenario, SCENARIOS["success"])
    
    console.print(f"[dim]  → Wykonuję scenariusz: {scenario}[/dim]")
    
    if config.get("will_fail"):
        fail_type = config.get("fail_type", "EXECUTION_ERROR")
        fail_msg = config.get("fail_message", "Unknown error")
        
        console.print(f"[red]  → Symulowany błąd: {fail_type}[/red]")
        
        # Raise appropriate exception
        if "DEPENDENCY" in fail_type:
            raise RuntimeError(fail_msg)
        elif "TIMEOUT" in fail_type:
            raise RuntimeError(fail_msg)
        elif "HF_TOKEN" in fail_type:
            raise RuntimeError(fail_msg)
        else:
            raise RuntimeError(fail_msg)
    
    # Success case
    await asyncio.sleep(0.5)  # Simulate work
    console.print("[green]  → Wykonanie zakończone sukcesem[/green]")
    
    return {
        "result": "success",
        "scenario": scenario,
        "output": "Mock execution completed successfully",
    }


async def run_scenario(scenario_name: str, use_orchestrator: bool = True) -> dict:
    """Uruchamia scenariusz z lub bez orchestratora."""
    
    config = SCENARIOS.get(scenario_name, SCENARIOS["success"])
    
    console.print(f"\n[bold cyan]Scenariusz: {scenario_name}[/bold cyan]")
    console.print(f"[dim]{config['description']}[/dim]")
    
    if use_orchestrator:
        console.print("\n[yellow]Używam EvolutionaryOrchestrator...[/yellow]")
        
        engine = EvolutionaryRecoveryEngine(console=console)
        
        context = {
            "scenario": scenario_name,
            "description": config["description"],
        }
        
        success, result, metrics = await engine.execute_with_evolutionary_recovery(
            mock_example_execution,
            context,
            max_attempts=3,
        )
        
        return {
            "success": success,
            "metrics": metrics,
            "result": result,
        }
    else:
        console.print("\n[yellow]Wykonanie bez orchestratora (bezpośrednie)...[/yellow]")
        
        try:
            context = {"scenario": scenario_name}
            result = await mock_example_execution(context)
            return {
                "success": True,
                "metrics": None,
                "result": result,
            }
        except Exception as e:
            console.print(f"[red]Błąd (bez recovery): {e}[/red]")
            return {
                "success": False,
                "metrics": None,
                "result": None,
            }


def print_metrics_report(metrics: ExecutionMetrics, title: str = "Execution Report"):
    """Drukuje raport metryk."""
    
    table = Table(title=title, show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Success", "✅ Yes" if metrics.success else "❌ No")
    table.add_row("Attempts", str(metrics.attempts))
    table.add_row("Recovery Count", str(metrics.recovery_count))
    table.add_row("Duration", f"{metrics.duration_ms:.0f} ms")
    
    if metrics.error_type:
        table.add_row("Error Type", metrics.error_type)
    
    if metrics.recovery_attempts:
        table.add_row("", "")
        table.add_row("[bold]Recovery Attempts[/bold]", "")
        for i, attempt in enumerate(metrics.recovery_attempts, 1):
            status = "✅" if attempt.success else "❌"
            table.add_row(
                f"  Attempt {i}",
                f"{status} {attempt.strategy.value}"
            )
    
    console.print(table)


def print_learning_report():
    """Drukuje raport uczenia się."""
    
    engine = EvolutionaryRecoveryEngine(console=console)
    report = engine.get_learning_report()
    
    if "message" in report:
        console.print(f"\n[dim]{report['message']}[/dim]")
        return
    
    table = Table(title="Evolutionary Learning Report", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Executions", str(report.get("total_executions", 0)))
    table.add_row("Successful", str(report.get("successful", 0)))
    table.add_row("Success Rate", f"{report.get('success_rate', 0):.1%}")
    table.add_row("Recent Success Rate", f"{report.get('recent_success_rate', 0):.1%}")
    table.add_row("Avg Duration", f"{report.get('avg_duration_ms', 0):.0f} ms")
    table.add_row("Avg Recoveries", f"{report.get('avg_recoveries', 0):.1f}")
    table.add_row("Patterns Learned", str(report.get("patterns_learned", 0)))
    table.add_row("LLM Insights", str(report.get("llm_insights", 0)))
    
    console.print(table)


async def main():
    parser = argparse.ArgumentParser(
        description="Evolutionary Orchestrator Demo - 'Never Give Up' Engine"
    )
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()),
        default="success",
        help="Scenariusz do wykonania",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Lista dostępnych scenariuszy",
    )
    parser.add_argument(
        "--no-orchestrator",
        action="store_true",
        help="Wyłącz orchestrator (bez recovery)",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Porównaj: z i bez orchestratora",
    )
    
    args = parser.parse_args()
    
    if args.list:
        console.print("\n[bold]Dostępne scenariusze:[/bold]\n")
        for name, config in SCENARIOS.items():
            console.print(f"  [cyan]{name:20}[/cyan] - {config['description']}")
        console.print()
        return
    
    # Header
    console.print(Panel.fit(
        "[bold]Evolutionary Orchestrator Demo[/bold]\n"
        "'Never Give Up' Engine - Autonomiczny system naprawy",
        title="NLP2CMD",
        border_style="blue",
    ))
    
    if args.compare:
        # Run both versions for comparison
        console.print("\n[bold red]=== BEZ ORCHESTRATORA ===[/bold red]")
        result_without = await run_scenario(args.scenario, use_orchestrator=False)
        
        console.print("\n[bold green]=== Z ORCHESTRATOREM ===[/bold green]")
        result_with = await run_scenario(args.scenario, use_orchestrator=True)
        
        # Comparison table
        console.print("\n[bold]Porównanie:[/bold]")
        table = Table(show_header=True)
        table.add_column("Aspekt", style="cyan")
        table.add_column("Bez Orchestratora", style="red")
        table.add_column("Z Orchestratorem", style="green")
        
        table.add_row(
            "Sukces",
            "✅ Tak" if result_without["success"] else "❌ Nie",
            "✅ Tak" if result_with["success"] else "❌ Nie",
        )
        table.add_row(
            "Recovery Attempts",
            "0",
            str(result_with["metrics"].recovery_count) if result_with["metrics"] else "N/A",
        )
        
        console.print(table)
    else:
        # Single run
        result = await run_scenario(
            args.scenario,
            use_orchestrator=not args.no_orchestrator
        )
        
        if result["metrics"]:
            print_metrics_report(result["metrics"])
    
    # Show learning report
    console.print("\n[bold]Baza wiedzy evolutionary:[/bold]")
    print_learning_report()
    
    console.print("\n[dim]EvolutionaryOrchestrator zapisuje wiedzę do: ~/.nlp2cmd/evolutionary_learning.json[/dim]\n")


if __name__ == "__main__":
    asyncio.run(main())
