"""
Evolutionary Autonomous Orchestrator - "Never Give Up" Engine

Backward-compatible shim — real implementation lives in nlp2cmd.evolutionary/.
"""

from nlp2cmd.evolutionary import (
    AutonomousExampleRunner,
    ExecutionMetrics,
    EvolutionaryKnowledgeStore,
    EvolutionaryRecoveryEngine,
    EvolutionaryRecoveryPlanner,
    RecoveryAttempt,
    RecoveryStrategy,
)

__all__ = [
    "AutonomousExampleRunner",
    "EvolutionaryKnowledgeStore",
    "EvolutionaryRecoveryEngine",
    "EvolutionaryRecoveryPlanner",
    "ExecutionMetrics",
    "RecoveryAttempt",
    "RecoveryStrategy",
]
