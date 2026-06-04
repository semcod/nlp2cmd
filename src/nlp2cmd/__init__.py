"""
NLP2CMD - Natural Language to Domain-Specific Commands

A framework for transforming natural language into DSL commands
with support for SQL, Shell, Docker, Kubernetes, and more.

Architecture (LLM as Planner + Typed Actions):
- NLP Layer: Intent classification + entity extraction
- Decision Router: Routes to direct execution or LLM planner
- LLM Planner: Generates multi-step execution plans
- Plan Validator: Validates plans against action registry
- Action Engine: Executes typed actions (no eval/shell)
- Result Aggregator: Formats and summarizes results

Key principle: LLM plans. Code executes. System controls.
"""

__version__ = "1.1.13"
__author__ = "NLP2CMD Team"

# Import core classes with fallback
try:
    from nlp2cmd.core.core_transform import NLP2CMD
    from nlp2cmd.core.core_models import TransformResult
except ImportError:
    # Fallback if TOON integration causes import issues
    NLP2CMD = None
    TransformResult = None
from nlp2cmd.adapters import (
    BaseDSLAdapter,
    AppSpecAdapter,
    SQLAdapter,
    ShellAdapter,
    DockerAdapter,
    DQLAdapter,
    KubernetesAdapter,
    BrowserAdapter,
    SQLSafetyPolicy,
    ShellSafetyPolicy,
    DockerSafetyPolicy,
    KubernetesSafetyPolicy,
)
from nlp2cmd.schemas import SchemaRegistry, FileFormatSchema
from nlp2cmd.feedback import FeedbackAnalyzer, FeedbackResult, FeedbackType
from nlp2cmd.environment import EnvironmentAnalyzer
from nlp2cmd.validators import BaseValidator
from nlp2cmd.evolutionary import (
    EvolutionaryRecoveryEngine,
    AutonomousExampleRunner,
    RecoveryStrategy,
    ExecutionMetrics,
    RecoveryAttempt,
)

# New components (LLM as Planner architecture)
from nlp2cmd.router import (
    DecisionRouter,
    RoutingDecision,
    RoutingResult,
    RouterConfig,
)

from nlp2cmd.registry import (
    ActionRegistry,
    ActionSchema,
    ActionResult,
    ActionHandler,
    ParamSchema,
    ParamType,
    get_registry,
)

from nlp2cmd.executor import (
    PlanExecutor,
    PlanValidator,
    ExecutionPlan,
    ExecutionContext,
    ExecutionResult,
    PlanStep,
    StepResult,
    StepStatus,
)

from nlp2cmd.planner import (
    LLMPlanner,
    PlannerConfig,
    PlanningResult,
)

from nlp2cmd.aggregator import (
    ResultAggregator,
    AggregatedResult,
    OutputFormat,
)

__all__ = [
    # Core
    "NLP2CMD",
    "TransformResult",
    # Adapters
    "BaseDSLAdapter",
    "SQLAdapter",
    "ShellAdapter",
    "DockerAdapter",
    "DQLAdapter",
    "KubernetesAdapter",
    "BrowserAdapter",
    # Safety Policies
    "SQLSafetyPolicy",
    "ShellSafetyPolicy",
    "DockerSafetyPolicy",
    "KubernetesSafetyPolicy",
    # Schemas
    "SchemaRegistry",
    "FileFormatSchema",
    # Feedback
    "FeedbackAnalyzer",
    "FeedbackResult",
    "FeedbackType",
    # Environment
    "EnvironmentAnalyzer",
    # Validators
    "BaseValidator",
    # Router (new)
    "DecisionRouter",
    "RoutingDecision",
    "RoutingResult",
    "RouterConfig",
    # Registry (new)
    "ActionRegistry",
    "ActionSchema",
    "ActionResult",
    "ActionHandler",
    "ParamSchema",
    "ParamType",
    "get_registry",
    # Executor (new)
    "PlanExecutor",
    "PlanValidator",
    "ExecutionPlan",
    "ExecutionContext",
    "ExecutionResult",
    "PlanStep",
    "StepResult",
    "StepStatus",
    # Planner (new)
    "LLMPlanner",
    "PlannerConfig",
    "PlanningResult",
    # Aggregator (new)
    "ResultAggregator",
    "AggregatedResult",
    "OutputFormat",
    # Evolutionary Orchestrator (new)
    "EvolutionaryRecoveryEngine",
    "AutonomousExampleRunner",
    "RecoveryStrategy",
    "ExecutionMetrics",
    "RecoveryAttempt",
]
