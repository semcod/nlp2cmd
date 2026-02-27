#!/usr/bin/env python3
"""
Demo 04: Plan Executor
Demonstracja Plan Executor - wykonanie typowanych akcji.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Any

sys.path.append(str(Path(__file__).resolve().parents[2]))


@dataclass
class ExecutionResult:
    """Wynik wykonania kroku."""
    step_number: int
    success: bool
    action: str
    result: Any
    error: str = None


class PlanExecutor:
    """Wykonawca planu."""
    
    def __init__(self):
        self.action_handlers = {
            "execute_command": self._mock_execute,
            "check_disk_space": self._mock_check_disk,
            "create_backup": self._mock_backup,
            "run_tests": self._mock_tests,
            "build_image": self._mock_build,
        }
    
    def _mock_execute(self, params: dict) -> dict:
        return {"status": "success", "output": f"Executed: {params.get('cmd', 'N/A')}"}
    
    def _mock_check_disk(self, params: dict) -> dict:
        return {"status": "success", "free_gb": 150.5, "total_gb": 500.0}
    
    def _mock_backup(self, params: dict) -> dict:
        return {"status": "success", "backup_id": "backup_001", "size_mb": 1024}
    
    def _mock_tests(self, params: dict) -> dict:
        return {"status": "success", "passed": 45, "failed": 0}
    
    def _mock_build(self, params: dict) -> dict:
        return {"status": "success", "image_id": "app:latest", "build_time": 45}
    
    def execute_step(self, step_number: int, action: str, params: dict) -> ExecutionResult:
        """Wykonuje pojedynczy krok planu."""
        handler = self.action_handlers.get(action, self._mock_execute)
        
        try:
            result = handler(params)
            success = result.get("status") == "success"
            return ExecutionResult(
                step_number=step_number,
                success=success,
                action=action,
                result=result
            )
        except Exception as e:
            return ExecutionResult(
                step_number=step_number,
                success=False,
                action=action,
                result=None,
                error=str(e)
            )
    
    def execute_plan(self, plan: List[Any]) -> List[ExecutionResult]:
        """Wykonuje cały plan."""
        results = []
        for step in plan:
            result = self.execute_step(
                step.step_number,
                step.action,
                step.params
            )
            results.append(result)
            
            # Stop on failure
            if not result.success:
                break
        
        return results


def main():
    print("=" * 60)
    print("Demo 04: Plan Executor")
    print("=" * 60)
    print()
    
    executor = PlanExecutor()
    
    # Mock plan
    mock_plan = [
        type('Step', (), {'step_number': 1, 'action': 'check_disk_space', 'params': {}})(),
        type('Step', (), {'step_number': 2, 'action': 'create_backup', 'params': {'type': 'full'}})(),
        type('Step', (), {'step_number': 3, 'action': 'run_tests', 'params': {}})(),
    ]
    
    print("⚙️  Wykonywanie planu:\n")
    
    results = executor.execute_plan(mock_plan)
    
    for result in results:
        icon = "✅" if result.success else "❌"
        print(f"{icon} Krok {result.step_number}: {result.action}")
        print(f"   Wynik: {result.result}")
        if result.error:
            print(f"   Błąd: {result.error}")
        print()
    
    print("💡 Charakterystyka Plan Executor:")
    print("   • Typowane akcje (type-safe)")
    print("   • Obsługa błędów i rollback")
    print("   • Równoległe wykonywanie niezależnych kroków")
    print("   • Śledzenie postępu i logowanie")
    
    print()
    print("=" * 60)
    print("✅ Koniec demo 04")
    print("=" * 60)


if __name__ == "__main__":
    main()
