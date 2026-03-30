"""Persistence and reporting for evolutionary learning data."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .types import ExecutionMetrics, RecoveryStrategy


class EvolutionaryKnowledgeStore:
    """Stores and persists learning data for recovery attempts."""

    def __init__(self, learning_db_path: Optional[Path] = None):
        self.learning_db_path = (
            learning_db_path
            or Path.home() / ".nlp2cmd" / "evolutionary_learning.json"
        )
        self.learning_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.knowledge_base = self._load_knowledge()

    def _default_knowledge(self) -> dict[str, Any]:
        return {
            "error_patterns": {},
            "successful_strategies": {},
            "llm_insights": [],
            "execution_history": [],
            "version": 1,
        }

    def _load_knowledge(self) -> dict[str, Any]:
        """Wczytuje bazę wiedzy o naprawach."""
        if self.learning_db_path.exists():
            try:
                data = json.loads(self.learning_db_path.read_text())
                if isinstance(data, dict):
                    default = self._default_knowledge()
                    default.update(data)
                    return default
            except Exception:
                pass
        return self._default_knowledge()

    def _save_knowledge(self) -> None:
        """Zapisuje bazę wiedzy."""
        self.learning_db_path.write_text(
            json.dumps(self.knowledge_base, indent=2, default=str)
        )

    def record_recovery(
        self,
        error_type: str,
        strategy: RecoveryStrategy,
        success: bool,
    ) -> None:
        """Updates the learned strategy statistics."""
        patterns = self.knowledge_base.setdefault("error_patterns", {})
        error_stats = patterns.setdefault(error_type, {})
        strategy_stats = error_stats.setdefault(
            strategy.value,
            {"attempts": 0, "successes": 0},
        )

        strategy_stats["attempts"] += 1
        if success:
            strategy_stats["successes"] += 1
            successful = self.knowledge_base.setdefault("successful_strategies", {})
            successful[strategy.value] = successful.get(strategy.value, 0) + 1

        self._save_knowledge()

    def record_execution(self, metrics: ExecutionMetrics) -> None:
        """Przechowuje historię wykonań."""
        history = self.knowledge_base.setdefault("execution_history", [])
        history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "success": metrics.success,
                "attempts": metrics.attempts,
                "recovery_count": metrics.recovery_count,
                "duration_ms": metrics.duration_ms,
                "error_type": metrics.error_type,
            }
        )
        self.knowledge_base["execution_history"] = history[-100:]
        self._save_knowledge()

    def get_learning_report(self) -> dict[str, Any]:
        """Generuje raport uczenia się."""
        history = self.knowledge_base.get("execution_history", [])
        if not history:
            return {"message": "No executions yet"}

        total = len(history)
        successful = sum(1 for h in history if h.get("success"))
        avg_duration = (
            sum(h.get("duration_ms", 0) for h in history) / total if total > 0 else 0
        )
        avg_recoveries = (
            sum(h.get("recovery_count", 0) for h in history) / total if total > 0 else 0
        )

        recent = history[-10:] if len(history) >= 10 else history
        recent_success_rate = (
            sum(1 for h in recent if h.get("success")) / len(recent) if recent else 0
        )

        return {
            "total_executions": total,
            "successful": successful,
            "success_rate": successful / total if total > 0 else 0,
            "recent_success_rate": recent_success_rate,
            "avg_duration_ms": avg_duration,
            "avg_recoveries": avg_recoveries,
            "patterns_learned": len(self.knowledge_base.get("error_patterns", {})),
            "llm_insights": len(self.knowledge_base.get("llm_insights", [])),
            "evolution": "System is learning and adapting",
        }
