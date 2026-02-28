"""Data models for code2flow analysis."""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any
from pathlib import Path


@dataclass
class FlowNode:
    """Represents a node in the control flow graph."""
    id: str
    type: str  # FUNC, CALL, IF, FOR, WHILE, ASSIGN, RETURN, ENTRY, EXIT
    label: str
    function: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    conditions: List[str] = field(default_factory=list)
    data_flow: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self, compact: bool = True) -> dict:
        """Convert to dictionary, optionally skipping empty fields."""
        result = {
            "id": self.id,
            "type": self.type,
            "label": self.label,
        }
        if self.function:
            result["function"] = self.function
        if self.file:
            result["file"] = self.file
        if self.line is not None:
            result["line"] = self.line
        
        if not compact:
            if self.column is not None:
                result["column"] = self.column
            if self.conditions:
                result["conditions"] = self.conditions
            if self.data_flow:
                result["data_flow"] = self.data_flow
            if self.metadata:
                result["metadata"] = self.metadata
        else:
            if self.conditions:
                result["conditions"] = self.conditions
            if self.data_flow:
                result["data_flow"] = self.data_flow
        
        return result


@dataclass
class FlowEdge:
    """Represents an edge in the control flow graph."""
    source: str
    target: str
    edge_type: str = "control"  # control, data, call
    label: Optional[str] = None
    conditions: List[str] = field(default_factory=list)
    
    def to_dict(self, compact: bool = True) -> dict:
        """Convert to dictionary."""
        result = {
            "source": self.source,
            "target": self.target,
        }
        if self.edge_type != "control":
            result["type"] = self.edge_type
        if self.label:
            result["label"] = self.label
        if self.conditions and not compact:
            result["conditions"] = self.conditions
        return result


@dataclass
class FunctionInfo:
    """Information about a function/method."""
    name: str
    qualified_name: str
    file: str
    line: int
    column: int = 0
    module: str = ""
    class_name: Optional[str] = None
    is_method: bool = False
    is_private: bool = False
    is_property: bool = False
    docstring: Optional[str] = None
    args: List[str] = field(default_factory=list)
    returns: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    
    # CFG info
    cfg_entry: Optional[str] = None
    cfg_exit: Optional[str] = None
    cfg_nodes: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)
    called_by: List[str] = field(default_factory=list)
    
    def to_dict(self, compact: bool = True) -> dict:
        """Convert to dictionary."""
        result = {
            "name": self.name,
            "qualified_name": self.qualified_name,
            "file": self.file,
            "line": self.line,
        }
        if self.module:
            result["module"] = self.module
        if self.class_name:
            result["class"] = self.class_name
        if self.is_method:
            result["is_method"] = True
        
        if not compact:
            if self.column:
                result["column"] = self.column
            if self.is_private:
                result["is_private"] = True
            if self.is_property:
                result["is_property"] = True
            if self.docstring:
                result["docstring"] = self.docstring
            if self.args:
                result["args"] = self.args
            if self.returns:
                result["returns"] = self.returns
            if self.decorators:
                result["decorators"] = self.decorators
        
        if self.cfg_entry:
            result["cfg_entry"] = self.cfg_entry
        if self.calls:
            # Remove duplicates while preserving order
            unique_calls = list(dict.fromkeys(self.calls))
            result["calls"] = unique_calls
        if self.called_by:
            # Remove duplicates while preserving order
            unique_called_by = list(dict.fromkeys(self.called_by))
            result["called_by"] = unique_called_by
        
        return result


@dataclass
class ClassInfo:
    """Information about a class."""
    name: str
    qualified_name: str
    file: str
    line: int
    module: str = ""
    bases: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    is_state_machine: bool = False
    
    def to_dict(self, compact: bool = True) -> dict:
        """Convert to dictionary."""
        result = {
            "name": self.name,
            "qualified_name": self.qualified_name,
            "file": self.file,
            "line": self.line,
        }
        if self.module:
            result["module"] = self.module
        if self.bases:
            result["bases"] = self.bases
        if self.methods:
            result["methods"] = self.methods
        if self.is_state_machine:
            result["is_state_machine"] = True
        if not compact and self.docstring:
            result["docstring"] = self.docstring
        return result


@dataclass
class ModuleInfo:
    """Information about a module/package."""
    name: str
    file: str
    is_package: bool = False
    imports: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    
    def to_dict(self, compact: bool = True) -> dict:
        """Convert to dictionary."""
        result = {
            "name": self.name,
            "file": self.file,
        }
        if self.is_package:
            result["is_package"] = True
        if self.functions:
            result["functions"] = self.functions
        if self.classes:
            result["classes"] = self.classes
        if not compact and self.imports:
            result["imports"] = self.imports
        return result


@dataclass
class Pattern:
    """Detected behavioral pattern."""
    name: str
    type: str  # recursion, state_machine, factory, singleton, strategy, loop
    confidence: float  # 0.0 to 1.0
    functions: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    exit_points: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self, compact: bool = True) -> dict:
        """Convert to dictionary."""
        result = {
            "name": self.name,
            "type": self.type,
            "confidence": round(self.confidence, 2),
        }
        if self.functions:
            result["functions"] = self.functions
        if self.entry_points:
            result["entry_points"] = self.entry_points
        if self.exit_points:
            result["exit_points"] = self.exit_points
        if not compact and self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class AnalysisResult:
    """Complete analysis result for a project."""
    project_path: str
    analysis_mode: str
    stats: Dict[str, int] = field(default_factory=dict)
    
    # Graph data
    nodes: Dict[str, FlowNode] = field(default_factory=dict)
    edges: List[FlowEdge] = field(default_factory=list)
    
    # Code structure
    modules: Dict[str, ModuleInfo] = field(default_factory=dict)
    classes: Dict[str, ClassInfo] = field(default_factory=dict)
    functions: Dict[str, FunctionInfo] = field(default_factory=dict)
    
    # Analysis results
    patterns: List[Pattern] = field(default_factory=list)
    call_graph: Dict[str, List[str]] = field(default_factory=dict)
    entry_points: List[str] = field(default_factory=list)
    
    def to_dict(self, compact: bool = True) -> dict:
        """Convert entire result to dictionary."""
        return {
            "project_path": self.project_path,
            "analysis_mode": self.analysis_mode,
            "stats": self.stats,
            "nodes": {k: v.to_dict(compact) for k, v in self.nodes.items()} if self.nodes else {},
            "edges": [e.to_dict(compact) for e in self.edges] if self.edges else [],
            "modules": {k: v.to_dict(compact) for k, v in self.modules.items()} if self.modules else {},
            "classes": {k: v.to_dict(compact) for k, v in self.classes.items()} if self.classes else {},
            "functions": {k: v.to_dict(compact) for k, v in self.functions.items()} if self.functions else {},
            "patterns": [p.to_dict(compact) for p in self.patterns] if self.patterns else [],
            "call_graph": self.call_graph,
            "entry_points": self.entry_points,
        }
    
    def get_function_count(self) -> int:
        """Get total function count."""
        return len(self.functions)
    
    def get_class_count(self) -> int:
        """Get total class count."""
        return len(self.classes)
    
    def get_node_count(self) -> int:
        """Get total CFG node count."""
        return len(self.nodes)
    
    def get_edge_count(self) -> int:
        """Get total edge count."""
        return len(self.edges)
