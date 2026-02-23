"""
CLI commands for NLP2CMD.

Provides various command implementations for repair, validation, and analysis.
"""

from __future__ import annotations

import json
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

    class Panel:  # type: ignore
        def __init__(self, renderable, *args, **kwargs):
            self.renderable = renderable

    class Table:  # type: ignore
        def __init__(self, *args, **kwargs):
            return


def repair_command(ctx, file: str, backup: bool):
    """Repair a configuration file."""
    console = Console()
    file_path = Path(file)
    
    try:
        from nlp2cmd.schemas import SchemaRegistry
        registry = SchemaRegistry()
    except Exception:
        console.print("[red]Schema registry not available[/red]")
        return

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


def validate_command(ctx, file: str):
    """Validate a configuration file."""
    console = Console()
    file_path = Path(file)
    
    try:
        from nlp2cmd.schemas import SchemaRegistry
        registry = SchemaRegistry()
    except Exception:
        console.print("[red]Schema registry not available[/red]")
        return

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


def analyze_env_command(ctx, output: Optional[str]):
    """Analyze system environment."""
    console = Console()
    
    try:
        from nlp2cmd.environment import EnvironmentAnalyzer
        analyzer = EnvironmentAnalyzer()
    except Exception:
        console.print("[red]Environment analyzer not available[/red]")
        return
        
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


# Stub commands for when click is not available
def repair_stub(*args, **kwargs):
    pass

def validate_stub(*args, **kwargs):
    pass

def analyze_env_stub(*args, **kwargs):
    pass

def version_stub(*args, **kwargs):
    pass
