"""
DSL Adapters for NLP2CMD.

This module contains adapters for transforming execution plans
into domain-specific language commands.
"""

from nlp2cmd.adapters.base import (
    AdapterConfig,
    BaseDSLAdapter,
    SafetyPolicy,
)
from nlp2cmd.adapters.sql import (
    SchemaContext,
    SQLAdapter,
    SQLSafetyPolicy,
)
from nlp2cmd.adapters.shell import (
    EnvironmentContext,
    ShellAdapter,
    ShellSafetyPolicy,
)
from nlp2cmd.adapters.docker import (
    ComposeContext,
    DockerAdapter,
    DockerSafetyPolicy,
)
from nlp2cmd.adapters.kubernetes import (
    ClusterContext,
    KubernetesAdapter,
    KubernetesSafetyPolicy,
)
from nlp2cmd.adapters.dql import (
    DQLAdapter,
    DQLSafetyPolicy,
    EntityContext,
)
from nlp2cmd.adapters.appspec import AppSpecAdapter
from nlp2cmd.adapters.browser import BrowserAdapter
from nlp2cmd.adapters.canvas import CanvasAdapter
from nlp2cmd.adapters.desktop import DesktopAdapter, DesktopAction

__all__ = [
    # Base
    "BaseDSLAdapter",
    "AdapterConfig",
    "SafetyPolicy",
    # SQL
    "SQLAdapter",
    "SQLSafetyPolicy",
    "SchemaContext",
    # Shell
    "ShellAdapter",
    "ShellSafetyPolicy",
    "EnvironmentContext",
    # Docker
    "DockerAdapter",
    "DockerSafetyPolicy",
    "ComposeContext",
    # Kubernetes
    "KubernetesAdapter",
    "KubernetesSafetyPolicy",
    "ClusterContext",
    # DQL
    "DQLAdapter",
    "DQLSafetyPolicy",
    "EntityContext",
    # AppSpec
    "AppSpecAdapter",
    # Browser
    "BrowserAdapter",
    # Canvas
    "CanvasAdapter",
    # Desktop
    "DesktopAdapter",
    "DesktopAction",
]
