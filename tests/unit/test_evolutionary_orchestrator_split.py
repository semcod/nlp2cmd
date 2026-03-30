from __future__ import annotations

from pathlib import Path


def test_legacy_and_new_exports_match() -> None:
    from nlp2cmd.evolutionary import (
        AutonomousExampleRunner,
        ExecutionMetrics,
        EvolutionaryRecoveryEngine,
        RecoveryAttempt,
        RecoveryStrategy,
    )
    import nlp2cmd.evolutionary_orchestrator as legacy

    assert legacy.EvolutionaryRecoveryEngine is EvolutionaryRecoveryEngine
    assert legacy.AutonomousExampleRunner is AutonomousExampleRunner
    assert legacy.RecoveryStrategy is RecoveryStrategy
    assert legacy.ExecutionMetrics is ExecutionMetrics
    assert legacy.RecoveryAttempt is RecoveryAttempt


def test_knowledge_store_roundtrip(tmp_path: Path) -> None:
    from nlp2cmd.evolutionary import ExecutionMetrics, RecoveryStrategy
    from nlp2cmd.evolutionary.store import EvolutionaryKnowledgeStore

    store = EvolutionaryKnowledgeStore(tmp_path / "learning.json")
    store.record_recovery("ModuleNotFoundError", RecoveryStrategy.INSTALL_DEPENDENCY, True)
    store.record_execution(
        ExecutionMetrics(start_time=0.0, end_time=1.0, attempts=1, success=True)
    )

    report = store.get_learning_report()
    assert report["total_executions"] == 1
    assert report["successful"] == 1
    assert report["patterns_learned"] == 1
    assert store.knowledge_base["error_patterns"]["ModuleNotFoundError"]["install_dependency"]["successes"] == 1
