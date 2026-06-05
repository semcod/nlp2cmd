"""ActionRegistry - extracted from __init__.py."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, Generic
from nlp2cmd.registry.action_handler import ActionHandler
from nlp2cmd.registry.action_schema import ActionSchema
from nlp2cmd.registry.param_schema import ParamSchema
from nlp2cmd.registry.param_type import ParamType

class ActionRegistry:
    """
    Central registry for all system actions.
    
    Provides:
    - Action registration and lookup
    - Schema validation
    - Allowlist enforcement
    - Domain-based filtering
    """
    
    def __init__(self):
        self._actions: dict[str, ActionSchema] = {}
        self._handlers: dict[str, ActionHandler] = {}
        self._domains: dict[str, list[str]] = {}
        self._register_builtin_actions()
    
    def _register_builtin_actions(self) -> None:
        """Register built-in actions."""
        # SQL Actions
        self.register(ActionSchema(
            name="sql_select",
            description="Execute SELECT query",
            domain="sql",
            params=[
                ParamSchema(name="table", type=ParamType.SQL_IDENTIFIER, description="Table name"),
                ParamSchema(name="columns", type=ParamType.LIST, required=False, default=["*"], description="Columns to select"),
                ParamSchema(name="filters", type=ParamType.LIST, required=False, default=[], description="WHERE conditions"),
                ParamSchema(name="ordering", type=ParamType.LIST, required=False, description="ORDER BY clauses"),
                ParamSchema(name="limit", type=ParamType.INTEGER, required=False, min_value=1, description="LIMIT value"),
            ],
            returns=ParamType.LIST,
            returns_description="List of matching rows",
            tags=["read", "query"],
        ))
        
        self.register(ActionSchema(
            name="sql_insert",
            description="Execute INSERT statement",
            domain="sql",
            params=[
                ParamSchema(name="table", type=ParamType.SQL_IDENTIFIER),
                ParamSchema(name="values", type=ParamType.DICT, description="Column-value pairs"),
            ],
            returns=ParamType.INTEGER,
            returns_description="Number of inserted rows",
            is_destructive=True,
            tags=["write", "insert"],
        ))
        
        self.register(ActionSchema(
            name="sql_update",
            description="Execute UPDATE statement",
            domain="sql",
            params=[
                ParamSchema(name="table", type=ParamType.SQL_IDENTIFIER),
                ParamSchema(name="values", type=ParamType.DICT, description="Column-value pairs to update"),
                ParamSchema(name="filters", type=ParamType.LIST, description="WHERE conditions"),
            ],
            returns=ParamType.INTEGER,
            returns_description="Number of updated rows",
            requires_confirmation=True,
            is_destructive=True,
            tags=["write", "update"],
        ))
        
        self.register(ActionSchema(
            name="sql_delete",
            description="Execute DELETE statement",
            domain="sql",
            params=[
                ParamSchema(name="table", type=ParamType.SQL_IDENTIFIER),
                ParamSchema(name="filters", type=ParamType.LIST, description="WHERE conditions"),
            ],
            returns=ParamType.INTEGER,
            returns_description="Number of deleted rows",
            requires_confirmation=True,
            is_destructive=True,
            tags=["write", "delete"],
        ))
        
        self.register(ActionSchema(
            name="sql_aggregate",
            description="Execute aggregation query",
            domain="sql",
            params=[
                ParamSchema(name="table", type=ParamType.SQL_IDENTIFIER),
                ParamSchema(name="aggregations", type=ParamType.LIST, description="Aggregation functions"),
                ParamSchema(name="grouping", type=ParamType.LIST, required=False, description="GROUP BY columns"),
                ParamSchema(name="having", type=ParamType.LIST, required=False, description="HAVING conditions"),
            ],
            returns=ParamType.LIST,
            returns_description="Aggregated results",
            tags=["read", "aggregate"],
        ))
        
        # Shell Actions
        self.register(ActionSchema(
            name="shell_find",
            description="Find files matching criteria",
            domain="shell",
            params=[
                ParamSchema(name="path", type=ParamType.FILE_PATH, required=False, default="."),
                ParamSchema(name="glob", type=ParamType.GLOB_PATTERN, required=False),
                ParamSchema(name="type", type=ParamType.STRING, required=False, allowed_values=["f", "d", "l"]),
                ParamSchema(name="size", type=ParamType.STRING, required=False, description="Size filter (e.g., +100M)"),
                ParamSchema(name="mtime", type=ParamType.INTEGER, required=False, description="Modified time in days"),
            ],
            returns=ParamType.LIST,
            returns_description="List of matching file paths",
            tags=["read", "filesystem"],
        ))
        
        self.register(ActionSchema(
            name="shell_read_file",
            description="Read file contents",
            domain="shell",
            params=[
                ParamSchema(name="path", type=ParamType.FILE_PATH),
                ParamSchema(name="encoding", type=ParamType.STRING, required=False, default="utf-8"),
            ],
            returns=ParamType.STRING,
            returns_description="File contents",
            tags=["read", "filesystem"],
        ))
        
        self.register(ActionSchema(
            name="shell_count_pattern",
            description="Count pattern occurrences in file",
            domain="shell",
            params=[
                ParamSchema(name="file", type=ParamType.FILE_PATH),
                ParamSchema(name="pattern", type=ParamType.REGEX_PATTERN),
                ParamSchema(name="case_sensitive", type=ParamType.BOOLEAN, required=False, default=True),
            ],
            returns=ParamType.INTEGER,
            returns_description="Number of matches",
            tags=["read", "search"],
        ))
        
        self.register(ActionSchema(
            name="shell_process_list",
            description="List running processes",
            domain="shell",
            params=[
                ParamSchema(name="filter", type=ParamType.STRING, required=False),
                ParamSchema(name="sort_by", type=ParamType.STRING, required=False, 
                           allowed_values=["cpu", "memory", "pid", "name"]),
                ParamSchema(name="limit", type=ParamType.INTEGER, required=False, default=10),
            ],
            returns=ParamType.LIST,
            returns_description="List of process info",
            tags=["read", "system"],
        ))
        
        # Docker Actions
        self.register(ActionSchema(
            name="docker_ps",
            description="List containers",
            domain="docker",
            params=[
                ParamSchema(name="all", type=ParamType.BOOLEAN, required=False, default=False),
                ParamSchema(name="filter", type=ParamType.STRING, required=False),
            ],
            returns=ParamType.LIST,
            returns_description="List of containers",
            tags=["read", "containers"],
        ))
        
        self.register(ActionSchema(
            name="docker_run",
            description="Run a container",
            domain="docker",
            params=[
                ParamSchema(name="image", type=ParamType.STRING),
                ParamSchema(name="name", type=ParamType.STRING, required=False),
                ParamSchema(name="ports", type=ParamType.LIST, required=False),
                ParamSchema(name="volumes", type=ParamType.LIST, required=False),
                ParamSchema(name="environment", type=ParamType.DICT, required=False),
                ParamSchema(name="detach", type=ParamType.BOOLEAN, required=False, default=True),
            ],
            returns=ParamType.STRING,
            returns_description="Container ID",
            is_destructive=True,
            tags=["write", "containers"],
        ))
        
        self.register(ActionSchema(
            name="docker_stop",
            description="Stop a container",
            domain="docker",
            params=[
                ParamSchema(name="container", type=ParamType.STRING),
                ParamSchema(name="timeout", type=ParamType.INTEGER, required=False, default=10),
            ],
            returns=ParamType.BOOLEAN,
            returns_description="Success status",
            is_destructive=True,
            tags=["write", "containers"],
        ))
        
        self.register(ActionSchema(
            name="docker_logs",
            description="Get container logs",
            domain="docker",
            params=[
                ParamSchema(name="container", type=ParamType.STRING),
                ParamSchema(name="tail", type=ParamType.INTEGER, required=False, default=100),
                ParamSchema(name="follow", type=ParamType.BOOLEAN, required=False, default=False),
            ],
            returns=ParamType.STRING,
            returns_description="Container logs",
            tags=["read", "containers"],
        ))
        
        # Kubernetes Actions
        self.register(ActionSchema(
            name="k8s_get",
            description="Get Kubernetes resources",
            domain="kubernetes",
            params=[
                ParamSchema(name="resource", type=ParamType.K8S_RESOURCE),
                ParamSchema(name="name", type=ParamType.STRING, required=False),
                ParamSchema(name="namespace", type=ParamType.STRING, required=False, default="default"),
                ParamSchema(name="labels", type=ParamType.DICT, required=False),
                ParamSchema(name="output", type=ParamType.STRING, required=False, 
                           allowed_values=["wide", "yaml", "json"]),
            ],
            returns=ParamType.LIST,
            returns_description="List of resources",
            tags=["read", "k8s"],
        ))
        
        self.register(ActionSchema(
            name="k8s_scale",
            description="Scale a deployment",
            domain="kubernetes",
            params=[
                ParamSchema(name="deployment", type=ParamType.STRING),
                ParamSchema(name="replicas", type=ParamType.INTEGER, min_value=0, max_value=100),
                ParamSchema(name="namespace", type=ParamType.STRING, required=False, default="default"),
            ],
            returns=ParamType.BOOLEAN,
            returns_description="Success status",
            is_destructive=True,
            tags=["write", "k8s", "scaling"],
        ))
        
        self.register(ActionSchema(
            name="k8s_logs",
            description="Get pod logs",
            domain="kubernetes",
            params=[
                ParamSchema(name="pod", type=ParamType.STRING),
                ParamSchema(name="container", type=ParamType.STRING, required=False),
                ParamSchema(name="namespace", type=ParamType.STRING, required=False, default="default"),
                ParamSchema(name="tail", type=ParamType.INTEGER, required=False, default=100),
                ParamSchema(name="follow", type=ParamType.BOOLEAN, required=False, default=False),
            ],
            returns=ParamType.STRING,
            returns_description="Pod logs",
            tags=["read", "k8s"],
        ))
        
        # Utility Actions
        self.register(ActionSchema(
            name="summarize_results",
            description="Summarize results from previous steps",
            domain="utility",
            params=[
                ParamSchema(name="data", type=ParamType.ANY, description="Data to summarize"),
                ParamSchema(name="format", type=ParamType.STRING, required=False, 
                           allowed_values=["text", "table", "json"], default="text"),
            ],
            returns=ParamType.STRING,
            returns_description="Formatted summary",
            tags=["utility", "formatting"],
        ))
        
        self.register(ActionSchema(
            name="filter_results",
            description="Filter results based on criteria",
            domain="utility",
            params=[
                ParamSchema(name="data", type=ParamType.LIST),
                ParamSchema(name="condition", type=ParamType.STRING, description="Filter expression"),
            ],
            returns=ParamType.LIST,
            returns_description="Filtered results",
            tags=["utility", "filtering"],
        ))
        
        self.register(ActionSchema(
            name="sort_results",
            description="Sort results",
            domain="utility",
            params=[
                ParamSchema(name="data", type=ParamType.LIST),
                ParamSchema(name="key", type=ParamType.STRING),
                ParamSchema(name="reverse", type=ParamType.BOOLEAN, required=False, default=False),
            ],
            returns=ParamType.LIST,
            returns_description="Sorted results",
            tags=["utility", "sorting"],
        ))
    
    def register(
        self,
        schema: ActionSchema,
        handler: Optional[ActionHandler] = None,
    ) -> None:
        """
        Register an action schema.
        
        Args:
            schema: Action schema definition
            handler: Optional handler for execution
        """
        self._actions[schema.name] = schema
        
        if handler:
            self._handlers[schema.name] = handler
        
        # Update domain index
        if schema.domain not in self._domains:
            self._domains[schema.domain] = []
        if schema.name not in self._domains[schema.domain]:
            self._domains[schema.domain].append(schema.name)
        
        logger.debug(f"Registered action: {schema.name} (domain: {schema.domain})")
    
    def get(self, name: str) -> Optional[ActionSchema]:
        """Get action schema by name."""
        return self._actions.get(name)
    
    def get_handler(self, name: str) -> Optional[ActionHandler]:
        """Get action handler by name."""
        return self._handlers.get(name)
    
    def has(self, name: str) -> bool:
        """Check if action exists."""
        return name in self._actions
    
    def list_actions(self, domain: Optional[str] = None) -> list[str]:
        """List all registered action names."""
        if domain:
            return self._domains.get(domain, [])
        return list(self._actions.keys())
    
    def list_domains(self) -> list[str]:
        """List all domains."""
        return list(self._domains.keys())
    
    def get_by_tag(self, tag: str) -> list[ActionSchema]:
        """Get all actions with a specific tag."""
        return [a for a in self._actions.values() if tag in a.tags]
    
    def get_destructive_actions(self) -> list[str]:
        """Get all destructive action names."""
        return [name for name, schema in self._actions.items() if schema.is_destructive]
    
    def validate_action(
        self,
        name: str,
        params: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """
        Validate an action call.
        
        Args:
            name: Action name
            params: Action parameters
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        if not self.has(name):
            return False, [f"Unknown action: {name}"]
        
        schema = self._actions[name]
        
        # Create temporary handler for validation
        handler = ActionHandler(schema)
        return handler.validate_params(params)
    
    def to_llm_prompt(self, domain: Optional[str] = None) -> str:
        """
        Generate action catalog for LLM prompt.
        
        Args:
            domain: Optional domain filter
            
        Returns:
            Formatted action catalog string
        """
        lines = ["Available actions:"]
        
        actions = self.list_actions(domain)
        
        for name in sorted(actions):
            schema = self._actions[name]
            
            # Action signature
            required = schema.get_required_params()
            optional = schema.get_optional_params()
            
            params_str = ", ".join(required)
            if optional:
                params_str += f" [, {', '.join(optional)}]"
            
            lines.append(f"\n- {name}({params_str})")
            lines.append(f"  Description: {schema.description}")
            lines.append(f"  Returns: {schema.returns.value} - {schema.returns_description}")
            
            if schema.requires_confirmation:
                lines.append("  ⚠️ Requires confirmation")
            
            if schema.is_destructive:
                lines.append("  🔴 Destructive action")
        
        return "\n".join(lines)

