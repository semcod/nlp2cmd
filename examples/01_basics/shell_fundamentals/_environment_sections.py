"""Section printers for environment_analysis demo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nlp2cmd.environment import EnvironmentAnalyzer

from _example_helpers import print_rule


def format_size(gb: float) -> str:
    if gb >= 1000:
        return f"{gb/1000:.1f} TB"
    return f"{gb:.1f} GB"


def _progress_bar(percent: float, width: int = 30) -> str:
    filled = int(percent / 100 * width)
    return "█" * filled + "░" * (width - filled)


def print_section_header(title: str) -> None:
    print_rule(width=70, char="─", leading_newline=True)
    print(title)
    print_rule(width=70, char="─")


def print_system_info(env: dict[str, Any]) -> None:
    print_section_header("1. SYSTEM INFORMATION")
    print(f"\n🖥️  Operating System:")
    print(f"   System:  {env['os']['system']}")
    print(f"   Release: {env['os']['release']}")
    print(f"   Machine: {env['os']['machine']}")
    print(f"   Python:  {env['os']['python_version']}")
    print(f"\n🐚 Shell:\n   Name: {env['shell']['name']}\n   Path: {env['shell']['path']}")
    print(f"\n👤 User:\n   Name: {env['user']['name']}\n   Home: {env['user']['home']}")
    print(f"   Root: {'Yes' if env['user']['is_root'] else 'No'}")
    print(f"\n📂 Working Directory:\n   {env['cwd']}")


def print_tool_detection(analyzer: EnvironmentAnalyzer) -> dict[str, Any]:
    print_section_header("2. TOOL DETECTION")
    tools_to_check = [
        "docker", "docker-compose", "kubectl", "git", "python", "node",
        "psql", "mysql", "redis-cli", "terraform", "aws", "gcloud", "helm", "ansible",
    ]
    print("\n🔧 Checking available tools...")
    tools = analyzer.detect_tools(tools_to_check)
    available = [info for info in tools.values() if info.available]
    unavailable = [info for info in tools.values() if not info.available]

    print("\n✅ Available tools:")
    for tool in available:
        version_str = f"v{tool.version}" if tool.version else "unknown version"
        config_str = f" (config: {len(tool.config_files)} files)" if tool.config_files else ""
        print(f"   • {tool.name}: {version_str}{config_str}")
        for config_file in tool.config_files:
            print(f"     └─ {config_file}")

    if unavailable:
        print("\n❌ Unavailable tools:")
        for tool in unavailable:
            print(f"   • {tool.name}")
    return tools


def print_service_status(analyzer: EnvironmentAnalyzer) -> dict[str, Any]:
    print_section_header("3. SERVICE STATUS")
    print("\n🔌 Checking services...")
    services = analyzer.check_services()
    for name, info in services.items():
        status_icon = "🟢" if info.running else "🔴"
        port_str = f":{info.port}" if info.port else ""
        reachable_str = " (reachable)" if info.reachable else " (not reachable)" if info.port else ""
        print(f"   {status_icon} {name}{port_str}{reachable_str}")
    return services


def print_config_files(analyzer: EnvironmentAnalyzer) -> list[dict[str, Any]]:
    print_section_header("4. CONFIGURATION FILES")
    print(f"\n📁 Scanning current directory: {Path.cwd()}")
    configs = analyzer.find_config_files(Path.cwd())
    if not configs:
        print("\n   No configuration files found in current directory")
        return configs

    print("\n📄 Found configuration files:")
    for config in configs:
        size = config.get("size", 0)
        size_str = f"{size} bytes" if size < 1024 else f"{size/1024:.1f} KB"
        name = config.get("name", "unknown")
        fmt = config.get("format") or (Path(name).suffix.lstrip(".") or "unknown")
        print(f"   • {name}\n     Format: {fmt}\n     Size: {size_str}\n     Path: {config.get('path', '')}")
    return configs


def print_resources(analyzer: EnvironmentAnalyzer) -> tuple[dict[str, Any], dict[str, Any] | None]:
    print_section_header("5. SYSTEM RESOURCES")
    resources = analyzer._get_resources()
    disk = resources.get("disk", {})
    memory = resources.get("memory")

    print(f"\n💾 Disk Usage:")
    print(f"   Total:  {format_size(disk.get('total_gb', 0.0))}")
    print(f"   Used:   {format_size(disk.get('used_gb', 0.0))} ({disk.get('percent_used', 0.0):.1f}%)")
    print(f"   Free:   {format_size(disk.get('free_gb', 0.0))}")
    print(f"   [{_progress_bar(disk.get('percent_used', 0.0))}]")

    if memory and memory.get("total_gb"):
        print(f"\n🧠 Memory:")
        print(f"   Total:     {format_size(memory.get('total_gb', 0.0))}")
        print(f"   Available: {format_size(memory.get('available_gb', 0.0))}")
        print(f"   Used:      {memory.get('percent_used', 0.0):.1f}%")
        print(f"   [{_progress_bar(memory.get('percent_used', 0.0))}]")
    return disk, memory


def print_command_validation(analyzer: EnvironmentAnalyzer, services: dict[str, Any]) -> None:
    print_section_header("6. COMMAND VALIDATION")
    commands = ["docker ps", "kubectl get pods", "nonexistent-command --arg", "git status", "cd /tmp"]
    print("\n🔍 Validating commands against environment:")
    for cmd in commands:
        result = analyzer.validate_command(cmd, {"services": services})
        icon = "✅" if result["valid"] else "⚠️ "
        print(f"   {icon} {cmd}")
        for warning in result.get("warnings", []):
            print(f"      └─ {warning}")


def print_full_report(analyzer: EnvironmentAnalyzer) -> Any:
    print_section_header("7. FULL ENVIRONMENT REPORT")
    report = analyzer.full_report()
    print("\n📊 Generating recommendations...")
    if report.recommendations:
        print("\n💡 Recommendations:")
        for rec in report.recommendations:
            print(f"   • {rec}")
    else:
        print("\n   ✅ No recommendations - environment looks good!")
    return report


def print_export_preview(report: Any) -> dict[str, Any]:
    print_section_header("8. EXPORT REPORT")
    report_data = {
        "os": report.os_info,
        "tools": {
            name: {
                "available": info.available,
                "version": info.version,
                "path": info.path,
                "config_files": info.config_files,
            }
            for name, info in report.tools.items()
        },
        "services": {
            name: {"running": info.running, "port": info.port, "reachable": info.reachable}
            for name, info in report.services.items()
        },
        "resources": report.resources,
        "config_files": [
            {
                "name": cf.get("name", "unknown"),
                "format": cf.get("format") or (Path(cf.get("name", "")).suffix.lstrip(".") or "unknown"),
                "path": cf.get("path", ""),
                "size": cf.get("size", 0),
            }
            for cf in report.config_files
        ],
        "recommendations": report.recommendations,
    }
    print("\n📝 Report JSON preview:")
    print_rule(width=40)
    print(json.dumps(report_data, indent=2)[:500] + "...")
    print("\n💾 To save full report:\n   nlp2cmd --analyze-env --output env-report.json")
    return report_data
