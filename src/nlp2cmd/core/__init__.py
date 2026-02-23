"""
Core package for NLP2CMD framework.

This package contains the core components split into modular
models, backends, and transformation logic.
"""

from .core_models import (
    TransformStatus,
    Intent,
    Entity,
    ExecutionPlan,
    TransformResult,
)
from .core_backends import (
    NLPBackend,
    SpaCyBackend,
    LLMBackend,
    RuleBasedBackend,
)
from .core_transform import NLP2CMD

__all__ = [
    # Models
    'TransformStatus',
    'Intent',
    'Entity', 
    'ExecutionPlan',
    'TransformResult',
    # Backends
    'NLPBackend',
    'SpaCyBackend',
    'LLMBackend',
    'RuleBasedBackend',
    # Main class
    'NLP2CMD',
]
