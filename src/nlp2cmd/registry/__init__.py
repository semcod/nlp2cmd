"""
Action Registry for NLP2CMD.

Central registry of all allowed actions with their schemas,
validators, and execution handlers.
"""

from nlp2cmd.registry.action_handler import ActionHandler
from nlp2cmd.registry.action_registry import ActionRegistry
from nlp2cmd.registry.action_result import ActionResult
from nlp2cmd.registry.action_schema import ActionSchema
from nlp2cmd.registry.get_registry import get_registry
from nlp2cmd.registry.param_schema import ParamSchema
from nlp2cmd.registry.param_type import ParamType

__all__ = [
    "ParamType",
    "ParamSchema",
    "ActionSchema",
    "ActionResult",
    "ActionHandler",
    "ActionRegistry",
    "get_registry",
]
