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
    
    def to_dict(self, include_defaults: bool = False) -> Dict:
        """Convert node to dictionary. Skip empty values by default."""
        result = {
            'id': self.id,
            'type': self.type,
            'label': self.label,
        }
        
        # Only include non-empty values unless include_defaults=True
        if include_defaults or self.function is not None:
            result['function'] = self.function
        if include_defaults or self.file is not None:
            result['file'] = self.file
        if include_defaults or self.line is not None:
            result['line'] = self.line
        if include_defaults or self.column is not None:
            result['column'] = self.column
        if include_defaults or self.conditions:
            result['conditions'] = self.conditions
        if include_defaults or self.data_flow:
            result['data_flow'] = self.data_flow
        if include_defaults or self.metadata:
            result['metadata'] = self.metadata
            
        return result


@dataclass 
class FlowEdge:
    """Represents an edge in the flow graph."""
    source: int
    target: int
    edge_type: str = "control"  # control, data, call
    condition: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self, include_defaults: bool = False) -> Dict:
        """Convert edge to dictionary. Skip empty values by default."""
        result = {
            'source': self.source,
            'target': self.target,
        }
        
        if include_defaults or self.edge_type != "control":
            result['type'] = self.edge_type
        if include_defaults or self.condition is not None:
            result['condition'] = self.condition
        if include_defaults or self.metadata:
            result['metadata'] = self.metadata
            
        return result


@dataclass
class DataFlow:
    """Represents data flow information."""
    variable: str
    defined_at: Optional[int] = None
    used_at: List[int] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    
    def to_dict(self, include_defaults: bool = False) -> Dict:
        """Convert data flow to dictionary. Skip empty values by default."""
        result = {'variable': self.variable}
        
        if include_defaults or self.defined_at is not None:
            result['defined_at'] = self.defined_at
        if include_defaults or self.used_at:
            result['used_at'] = self.used_at
        if include_defaults or self.dependencies:
            result['dependencies'] = list(self.dependencies)
            
        return result


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
    
    def to_dict(self, include_defaults: bool = False) -> Dict:
        """Convert function info to dictionary. Skip empty values by default."""
        result = {
            'name': self.name,
            'qualified_name': self.qualified_name,
            'file': self.file,
            'line_start': self.line_start,
            'line_end': self.line_end,
        }
        
        if include_defaults or self.args:
            result['args'] = self.args
        if include_defaults or self.returns is not None:
            result['returns'] = self.returns
        if include_defaults or self.calls:
            result['calls'] = list(self.calls)
        if include_defaults or self.called_by:
            result['called_by'] = list(self.called_by)
        if include_defaults or self.complexity != 1:
            result['complexity'] = self.complexity
            
        return result


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
    
    def to_dict(self, include_defaults: bool = False) -> Dict:
        """Convert result to dictionary. Skip empty values by default."""
        result = {}
        
        if self.nodes:
            result['nodes'] = {k: v.to_dict(include_defaults) for k, v in self.nodes.items()}
        if self.cfg_edges:
            result['cfg_edges'] = [e.to_dict(include_defaults) for e in self.cfg_edges]
        if self.dfg_edges:
            result['dfg_edges'] = [e.to_dict(include_defaults) for e in self.dfg_edges]
        if self.call_edges:
            result['call_edges'] = [e.to_dict(include_defaults) for e in self.call_edges]
        if self.functions:
            result['functions'] = {k: v.to_dict(include_defaults) for k, v in self.functions.items()}
        if self.data_flows:
            result['data_flows'] = {k: v.to_dict(include_defaults) for k, v in self.data_flows.items()}
        if include_defaults or self.imports:
            result['imports'] = self.imports
        if include_defaults or self.classes:
            result['classes'] = self.classes
            
        return result
