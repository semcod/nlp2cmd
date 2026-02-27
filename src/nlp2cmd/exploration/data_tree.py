"""
Data Tree Explorer - Data structure navigation.

Explore nested data structures: JSON, XML, database records, config trees.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional, Union

from nlp2cmd.exploration.base import BaseExplorer, ExplorationContext, ExplorationResult


@dataclass
class DataNode:
    """A node in a data tree."""
    path: str  # JSONPath-like path, e.g., "users[0].name"
    key: str
    value: Any
    type: str  # "dict", "list", "str", "int", "float", "bool", "null"
    parent: Optional["DataNode"] = None
    children: list["DataNode"] = field(default_factory=list)
    depth: int = 0


@dataclass
class DataMatch:
    """A match in data exploration."""
    node: DataNode
    score: float
    match_type: str  # "key", "value", "path", "type"


class DataTreeExplorer(BaseExplorer):
    """Explorer for nested data structures (JSON, dicts, etc.)."""
    
    def __init__(
        self,
        max_depth: int = 10,
        max_results: int = 20,
        include_values_in_search: bool = True,
    ):
        super().__init__(max_depth, max_results)
        self.include_values = include_values_in_search
    
    def supports(self, space_type: str) -> bool:
        return space_type in ("data", "json", "tree", "structure", "dict")
    
    def explore(
        self,
        root: Any,
        context: ExplorationContext,
    ) -> ExplorationResult[DataNode]:
        """Explore data structure starting from root."""
        if not isinstance(root, (dict, list)):
            # Try to parse if string
            if isinstance(root, str):
                try:
                    root = json.loads(root)
                except json.JSONDecodeError:
                    return ExplorationResult(
                        success=False,
                        error=f"Cannot parse as JSON: {root[:100]}",
                    )
            else:
                return ExplorationResult(
                    success=False,
                    error=f"Root must be dict or list, got {type(root).__name__}",
                )
        
        matches: list[DataMatch] = []
        self._visited = set()
        
        # Walk the tree
        for node in self._walk(root, path="", parent=None, depth=0):
            match = self._match_node(node, context)
            if match:
                matches.append(match)
        
        if not matches:
            return ExplorationResult(
                success=False,
                error=f"No matches for '{context.search_term}' in data",
                candidates=[],
            )
        
        # Sort by score
        matches.sort(key=lambda m: m.score, reverse=True)
        
        best = matches[0].node if matches else None
        
        return ExplorationResult(
            success=True,
            target=best,
            path=[best.path] if best else [],
            candidates=[m.node for m in matches],
            metadata={
                "search_term": context.search_term,
                "intent": context.intent,
                "total_matches": len(matches),
                "root_type": type(root).__name__,
            },
        )
    
    def _walk(
        self,
        data: Any,
        path: str,
        parent: Optional[DataNode],
        depth: int,
    ) -> Iterator[DataNode]:
        """Walk data tree yielding nodes."""
        if self._should_stop(depth, len(self._visited)):
            return
        
        # Mark visited to prevent cycles in circular references
        node_id = f"{path}:{id(data)}"
        if node_id in self._visited:
            return
        self._visited.add(node_id)
        
        # Determine type
        node_type = self._get_type(data)
        
        # Create node
        if parent is None:
            key = "<root>"
        elif path and "." in path:
            key = path.split(".")[-1].replace("[", "").replace("]", "")
        else:
            key = path
        
        node = DataNode(
            path=path or "<root>",
            key=key,
            value=data,
            type=node_type,
            parent=parent,
            depth=depth,
        )
        
        yield node
        
        # Recurse into children
        if isinstance(data, dict):
            for k, v in data.items():
                child_path = f"{path}.{k}" if path else k
                for child in self._walk(v, child_path, node, depth + 1):
                    node.children.append(child)
                    yield child
                    
        elif isinstance(data, list):
            for i, v in enumerate(data):
                child_path = f"{path}[{i}]" if path else f"[{i}]"
                for child in self._walk(v, child_path, node, depth + 1):
                    node.children.append(child)
                    yield child
    
    def _get_type(self, value: Any) -> str:
        """Get type name for value."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "bool"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            return "str"
        elif isinstance(value, dict):
            return "dict"
        elif isinstance(value, list):
            return "list"
        else:
            return type(value).__name__
    
    def _match_node(self, node: DataNode, context: ExplorationContext) -> Optional[DataMatch]:
        """Check if node matches search context."""
        search_term = context.search_term
        if not search_term:
            # Without search term, match based on intent
            return self._match_by_intent(node, context)
        
        search_lower = search_term.lower()
        score = 0.0
        match_types: list[str] = []
        
        # Match in key
        if search_lower in node.key.lower():
            score += 2.0
            match_types.append("key")
        
        # Match in path
        if search_lower in node.path.lower():
            score += 1.0
            match_types.append("path")
        
        # Match in value (for scalars)
        if self.include_values and node.type in ("str", "int", "float", "bool"):
            value_str = str(node.value).lower()
            if search_lower in value_str:
                score += 1.5
                match_types.append("value")
        
        # Type-based matching
        if context.intent == "number" and node.type in ("int", "float"):
            score += 0.5
        elif context.intent == "text" and node.type == "str":
            score += 0.5
        elif context.intent == "list" and node.type == "list":
            score += 0.5
        elif context.intent == "object" and node.type == "dict":
            score += 0.5
        
        if score > 0:
            return DataMatch(
                node=node,
                score=score,
                match_type=",".join(match_types),
            )
        
        return None
    
    def _match_by_intent(self, node: DataNode, context: ExplorationContext) -> Optional[DataMatch]:
        """Match based on intent when no search term provided."""
        intent = context.intent
        score = 0.0
        
        # Score based on intent
        if intent == "config":
            # Look for config-like keys
            config_keys = ["config", "settings", "options", "params", "env"]
            for ck in config_keys:
                if ck in node.key.lower():
                    score += 2.0
                    break
        
        elif intent == "data":
            # Look for data containers
            if node.type == "dict" and len(node.children) > 0:
                score += 0.5
            if node.type == "list" and len(node.children) > 0:
                score += 0.5
        
        elif intent == "identifier":
            # Look for ID-like keys
            id_patterns = ["id", "uuid", "key", "name", "code", "slug"]
            for pattern in id_patterns:
                if pattern in node.key.lower():
                    score += 1.0
                    break
        
        if score > 0:
            return DataMatch(
                node=node,
                score=score,
                match_type="intent",
            )
        
        return None
    
    def get_value(self, root: Any, path: str) -> Optional[Any]:
        """Get value at specific path."""
        try:
            current = root
            parts = self._parse_path(path)
            
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                elif isinstance(current, list):
                    try:
                        idx = int(part)
                        current = current[idx]
                    except (ValueError, IndexError):
                        return None
                else:
                    return None
                
                if current is None:
                    return None
            
            return current
        except Exception:
            return None
    
    def _parse_path(self, path: str) -> list[str]:
        """Parse path like 'users[0].name' into parts."""
        parts: list[str] = []
        current = ""
        in_bracket = False
        
        for char in path:
            if char == "[":
                if current:
                    parts.append(current)
                    current = ""
                in_bracket = True
            elif char == "]":
                if current:
                    parts.append(current)
                    current = ""
                in_bracket = False
            elif char == "." and not in_bracket:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += char
        
        if current:
            parts.append(current)
        
        return parts
    
    def find_all_by_key(
        self,
        root: Any,
        key: str,
        value: Optional[Any] = None,
    ) -> list[DataNode]:
        """Find all nodes with matching key (and optionally value)."""
        matches: list[DataNode] = []
        
        for node in self._walk(root, "", None, 0):
            if node.key == key:
                if value is None or node.value == value:
                    matches.append(node)
        
        return matches
    
    def to_jsonpath(self, node: DataNode) -> str:
        """Convert node path to JSONPath format."""
        # Convert dot notation to JSONPath
        parts = self._parse_path(node.path)
        jsonpath = "$." + ".".join(parts[1:]) if len(parts) > 1 else "$"
        return jsonpath


def quick_find_in_data(
    data: Union[dict, list, str],
    search_term: str,
    max_depth: int = 5,
) -> Optional[str]:
    """Quick helper to find path in data."""
    explorer = DataTreeExplorer(max_depth=max_depth)
    context = ExplorationContext(
        intent="data",
        search_term=search_term,
    )
    result = explorer.explore(data, context)
    return result.target.path if result.target else None
