"""get_registry - extracted from __init__.py."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, Generic
from nlp2cmd.registry.action_registry import ActionRegistry

_registry: ActionRegistry | None = None


def get_registry() -> ActionRegistry:
    """Get the global action registry instance."""
    global _registry
    if _registry is None:
        _registry = ActionRegistry()
    return _registry

