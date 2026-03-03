"""
Dynamic Orchestration Engine for NLP2CMD.

Provides LLM-driven task planning, execution, reflection, and repair —
replacing hardcoded template/pattern matching with dynamic reasoning.

Architecture:
    User prompt → DecisionRouter
                    ↓ (DYNAMIC_ORCHESTRATOR)
                  Planner (LLM) → TaskSchema
                    ↓
                  StepExecutor (with retry)
                    ↓ on failure → Repairer (LLM)
                  ResultAnalyzer / Reflector (LLM)
                    ↓ invalid → re-plan / re-generate
                  Final output

Usage:
    from nlp2cmd.orchestration import Orchestrator, TaskResult

    orch = Orchestrator()
    result = await orch.run("napisz program sortujący w Pythonie", context={})
"""

from nlp2cmd.orchestration.engine import (
    Orchestrator,
    TaskResult,
    StepResult,
    TaskSchema,
    StepDef,
)
from nlp2cmd.orchestration.reflection import (
    ResultAnalyzer,
    ReflectionVerdict,
)
from nlp2cmd.orchestration.handlers import register_default_handlers
from nlp2cmd.orchestration.metrics import (
    MetricsCollector,
    PathOptimizer,
    FunctionCache,
    get_workspace,
)

__all__ = [
    "Orchestrator",
    "TaskResult",
    "StepResult",
    "TaskSchema",
    "StepDef",
    "ResultAnalyzer",
    "ReflectionVerdict",
    "register_default_handlers",
    "MetricsCollector",
    "PathOptimizer",
    "FunctionCache",
    "get_workspace",
]
