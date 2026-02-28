"""Core data structures for code2flow."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from enum import Enum


class NodeType(Enum):
    """Types of flow nodes."""
    FUNCTION = "FUNC"
    CALL = "CALL"
    CONDITIONAL = "IF"
    LOOP_FOR = "FOR"
    LOOP_WHILE = "WHILE"
    ASSIGNMENT = "ASSIGN"
    RETURN = "RETURN"
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    CLASS = "CLASS"
    TRY = "TRY"
    EXCEPT = "EXCEPT"


@dataclass
class FlowNode:
    """Represents a node in the control flow graph."""
    id: int
    type: str
    label: str
    function: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    conditions: List[str] = field(default_factory=list)
    data_flow: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert node to dictionary."""
        return {
            'id': self.id,
            'type': self.type,
            'label': self.label,
            'function': self.function,
            'file': self.file,
            'line': self.line,
            'column': self.column,
            'conditions': self.conditions,
            'data_flow': self.data_flow,
            'metadata': self.metadata
        }


@dataclass 
class FlowEdge:
    """Represents an edge in the flow graph."""
    source: int
    target: int
    edge_type: str = "control"  # control, data, call
    condition: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert edge to dictionary."""
        return {
            'source': self.source,
            'target': self.target,
            'type': self.edge_type,
            'condition': self.condition,
            'metadata': self.metadata
        }


@dataclass
class DataFlow:
    """Represents data flow information."""
    variable: str
    defined_at: Optional[int] = None
    used_at: List[int] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict:
        """Convert data flow to dictionary."""
        return {
            'variable': self.variable,
            'defined_at': self.defined_at,
            'used_at': self.used_at,
            'dependencies': list(self.dependencies)
        }


@dataclass
class FunctionInfo:
    """Information about a function."""
    name: str
    qualified_name: str
    file: str
    line_start: int
    line_end: int
    args: List[str] = field(default_factory=list)
    returns: Optional[str] = None
    calls: Set[str] = field(default_factory=set)
    called_by: Set[str] = field(default_factory=set)
    complexity: int = 1  # Cyclomatic complexity
    
    def to_dict(self) -> Dict:
        """Convert function info to dictionary."""
        return {
            'name': self.name,
            'qualified_name': self.qualified_name,
            'file': self.file,
            'line_start': self.line_start,
            'line_end': self.line_end,
            'args': self.args,
            'returns': self.returns,
            'calls': list(self.calls),
            'called_by': list(self.called_by),
            'complexity': self.complexity
        }


@dataclass
class AnalysisResult:
    """Complete analysis result."""
    nodes: Dict[int, FlowNode] = field(default_factory=dict)
    cfg_edges: List[FlowEdge] = field(default_factory=list)
    dfg_edges: List[FlowEdge] = field(default_factory=list)
    call_edges: List[FlowEdge] = field(default_factory=list)
    functions: Dict[str, FunctionInfo] = field(default_factory=dict)
    data_flows: Dict[str, DataFlow] = field(default_factory=dict)
    imports: Dict[str, str] = field(default_factory=dict)
    classes: Dict[str, Dict] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary."""
        return {
            'nodes': {k: v.to_dict() for k, v in self.nodes.items()},
            'cfg_edges': [e.to_dict() for e in self.cfg_edges],
            'dfg_edges': [e.to_dict() for e in self.dfg_edges],
            'call_edges': [e.to_dict() for e in self.call_edges],
            'functions': {k: v.to_dict() for k, v in self.functions.items()},
            'data_flows': {k: v.to_dict() for k, v in self.data_flows.items()},
            'imports': self.imports,
            'classes': self.classes
        }
