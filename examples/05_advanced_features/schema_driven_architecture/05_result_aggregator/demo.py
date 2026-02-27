#!/usr/bin/env python3
"""
Demo 05: Result Aggregator
Demonstracja Result Aggregator - formatowanie i agregacja wyników.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Any
from enum import Enum

sys.path.append(str(Path(__file__).resolve().parents[2]))


class OutputFormat(Enum):
    """Format wyjściowy."""
    JSON = "json"
    YAML = "yaml"
    TABLE = "table"
    MARKDOWN = "markdown"


@dataclass
class ExecutionResult:
    """Wynik wykonania."""
    step_number: int
    success: bool
    action: str
    result: Any


class ResultAggregator:
    """Agregator wyników."""
    
    def aggregate(self, results: List[ExecutionResult], format: OutputFormat = OutputFormat.TABLE) -> str:
        """Agreguje wyniki w wybrany format."""
        
        if format == OutputFormat.JSON:
            return self._to_json(results)
        elif format == OutputFormat.YAML:
            return self._to_yaml(results)
        elif format == OutputFormat.TABLE:
            return self._to_table(results)
        elif format == OutputFormat.MARKDOWN:
            return self._to_markdown(results)
        
        return str(results)
    
    def _to_json(self, results: List[ExecutionResult]) -> str:
        import json
        data = [
            {
                "step": r.step_number,
                "action": r.action,
                "success": r.success,
                "result": r.result
            }
            for r in results
        ]
        return json.dumps(data, indent=2, default=str)
    
    def _to_yaml(self, results: List[ExecutionResult]) -> str:
        lines = ["results:"]
        for r in results:
            lines.append(f"  - step: {r.step_number}")
            lines.append(f"    action: {r.action}")
            lines.append(f"    success: {r.success}")
            lines.append(f"    result: {r.result}")
        return "\n".join(lines)
    
    def _to_table(self, results: List[ExecutionResult]) -> str:
        lines = ["| Step | Action | Success | Result |"]
        lines.append("|------|--------|---------|--------|")
        for r in results:
            success_icon = "✅" if r.success else "❌"
            result_str = str(r.result)[:30] if r.result else "N/A"
            lines.append(f"| {r.step_number} | {r.action} | {success_icon} | {result_str} |")
        return "\n".join(lines)
    
    def _to_markdown(self, results: List[ExecutionResult]) -> str:
        lines = ["# Execution Results\n"]
        for r in results:
            icon = "✅" if r.success else "❌"
            lines.append(f"## Step {r.step_number}: {r.action} {icon}")
            lines.append(f"```json")
            lines.append(f"{r.result}")
            lines.append(f"```\n")
        return "\n".join(lines)


def main():
    print("=" * 60)
    print("Demo 05: Result Aggregator")
    print("=" * 60)
    print()
    
    aggregator = ResultAggregator()
    
    # Mock results
    mock_results = [
        ExecutionResult(1, True, "check_disk_space", {"free_gb": 150.5}),
        ExecutionResult(2, True, "create_backup", {"backup_id": "backup_001"}),
        ExecutionResult(3, True, "run_tests", {"passed": 45, "failed": 0}),
    ]
    
    print("📊 Agregacja wyników:\n")
    
    for fmt in OutputFormat:
        print(f"📝 Format: {fmt.value.upper()}")
        output = aggregator.aggregate(mock_results, fmt)
        print(output)
        print()
    
    print("💡 Zastosowania Result Aggregator:")
    print("   • Formatowanie dla różnych interfejsów (CLI, web, API)")
    print("   • Logowanie i raportowanie")
    print("   • Integracja z monitoringiem")
    print("   • Generowanie powiadomień")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 05")
    print("=" * 60)


if __name__ == "__main__":
    main()
