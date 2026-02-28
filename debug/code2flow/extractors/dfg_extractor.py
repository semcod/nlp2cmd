"""Data Flow Graph (DFG) extractor using AST."""

import ast
from collections import defaultdict
from typing import Set, Dict, List

from ..core.config import Config
from ..core.models import AnalysisResult, FlowEdge, DataFlow


class DFGExtractor(ast.NodeVisitor):
    """Extract Data Flow Graph from AST."""
    
    def __init__(self, config: Config):
        self.config = config
        self.result = AnalysisResult()
        self.module_name = ""
        self.file_path = ""
        
        # Data flow tracking
        self.variable_defs: Dict[str, int] = {}  # variable -> node_id where defined
        self.variable_uses: Dict[str, List[int]] = defaultdict(list)  # variable -> nodes where used
        self.current_scope = ""
        self.scope_stack = []
        
    def extract(self, tree: ast.AST, module_name: str, file_path: str) -> AnalysisResult:
        """Extract DFG from AST."""
        self.result = AnalysisResult()
        self.module_name = module_name
        self.file_path = file_path
        self.variable_defs = {}
        self.variable_uses = defaultdict(list)
        self.current_scope = module_name
        self.scope_stack = [module_name]
        
        self.visit(tree)
        self._build_data_flow_edges()
        
        return self.result
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition."""
        func_name = f"{self.module_name}.{node.name}"
        self.scope_stack.append(func_name)
        self.current_scope = func_name
        
        # Visit body
        for stmt in node.body:
            self.visit(stmt)
            
        self.scope_stack.pop()
        self.current_scope = self.scope_stack[-1] if self.scope_stack else self.module_name
        
    def visit_Assign(self, node: ast.Assign):
        """Track variable assignments."""
        # Get variables being assigned
        targets = self._extract_targets(node.targets)
        
        # Get dependencies from value
        dependencies = self._extract_names(node.value)
        
        for target in targets:
            scoped_name = f"{self.current_scope}.{target}"
            
            # Create data flow record
            if scoped_name not in self.result.data_flows:
                self.result.data_flows[scoped_name] = DataFlow(
                    variable=target,
                    dependencies=set()
                )
                
            self.result.data_flows[scoped_name].dependencies.update(dependencies)
            
            # Track this as a definition
            self.variable_defs[scoped_name] = node.lineno
            
        # Also record uses in the value
        for dep in dependencies:
            scoped_dep = f"{self.current_scope}.{dep}" if dep not in self.variable_defs else dep
            if dep not in self.variable_uses:
                self.variable_uses[scoped_dep] = []
            self.variable_uses[scoped_dep].append(node.lineno)
            
        self.generic_visit(node)
        
    def visit_AugAssign(self, node: ast.AugAssign):
        """Track augmented assignments (+=, *=, etc.)."""
        target = self._expr_to_str(node.target)
        dependencies = self._extract_names(node.value)
        
        scoped_name = f"{self.current_scope}.{target}"
        
        if scoped_name not in self.result.data_flows:
            self.result.data_flows[scoped_name] = DataFlow(
                variable=target,
                dependencies=set()
            )
            
        # Augmented assignment both uses and defines
        self.result.data_flows[scoped_name].dependencies.add(target)
        self.result.data_flows[scoped_name].dependencies.update(dependencies)
        
        self.generic_visit(node)
        
    def visit_For(self, node: ast.For):
        """Track loop variable."""
        if isinstance(node.target, ast.Name):
            loop_var = node.target.id
            scoped_name = f"{self.current_scope}.{loop_var}"
            
            # Loop variable depends on iterator
            iter_deps = self._extract_names(node.iter)
            
            if scoped_name not in self.result.data_flows:
                self.result.data_flows[scoped_name] = DataFlow(
                    variable=loop_var,
                    dependencies=set(iter_deps)
                )
            else:
                self.result.data_flows[scoped_name].dependencies.update(iter_deps)
                
        self.generic_visit(node)
        
    def visit_Call(self, node: ast.Call):
        """Track data flow through function calls."""
        # Track arguments as data flow to the call
        for i, arg in enumerate(node.args):
            deps = self._extract_names(arg)
            if deps:
                # Create implicit data flow for this argument
                call_str = self._expr_to_str(node.func)
                flow_key = f"{call_str}.arg{i}"
                
                if flow_key not in self.result.data_flows:
                    self.result.data_flows[flow_key] = DataFlow(
                        variable=flow_key,
                        dependencies=deps
                    )
                else:
                    self.result.data_flows[flow_key].dependencies.update(deps)
                    
        self.generic_visit(node)
        
    def _extract_targets(self, targets: List[ast.AST]) -> List[str]:
        """Extract variable names from assignment targets."""
        names = []
        for target in targets:
            names.extend(self._get_names(target))
        return names
        
    def _get_names(self, node: ast.AST) -> List[str]:
        """Get all variable names from an AST node."""
        names = []
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                names.append(child.id)
            elif isinstance(child, ast.Tuple) or isinstance(child, ast.List):
                for elt in child.elts:
                    names.extend(self._get_names(elt))
        return names
        
    def _extract_names(self, node: ast.AST) -> Set[str]:
        """Extract all variable names used in expression."""
        names = set()
        if node is None:
            return names
            
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                names.add(child.id)
                
        return names
        
    def _expr_to_str(self, node: ast.AST) -> str:
        """Convert AST expression to string."""
        if node is None:
            return "None"
        try:
            return ast.unparse(node) if hasattr(ast, 'unparse') else str(node)
        except:
            return str(node)
            
    def _build_data_flow_edges(self):
        """Build DFG edges from data flow records."""
        # For each variable, create edges from its dependencies
        for var_name, data_flow in self.result.data_flows.items():
            # This is a simplified representation
            # In a full implementation, we'd map to actual node IDs
            pass  # Edges built during CFG extraction
