"""
Plan Executor for NLP2CMD.

Executes multi-step execution plans with support for:
- Sequential step execution
- Foreach loops over results
- Variable references between steps
- Conditional execution
- Error handling and rollback
"""

from nlp2cmd.executor.execution_context import ExecutionContext
from nlp2cmd.executor.execution_plan import ExecutionPlan
from nlp2cmd.executor.execution_result import ExecutionResult
from nlp2cmd.executor.plan_executor import PlanExecutor
from nlp2cmd.executor.plan_step import PlanStep
from nlp2cmd.executor.plan_validator import PlanValidator
from nlp2cmd.executor.step_result import StepResult
from nlp2cmd.executor.step_status import StepStatus

__all__ = [
    "StepStatus",
    "PlanStep",
    "StepResult",
    "ExecutionPlan",
    "ExecutionContext",
    "ExecutionResult",
    "PlanValidator",
    "PlanExecutor",
]
