"""Call graph extractor using AST."""

import ast
from typing import Optional, Set

from ..core.config import Config
from ..core.models import AnalysisResult, FlowEdge


class CallGraphExtractor(ast.NodeVisitor):
    """Extract call graph from AST."""
    
    def __init__(self, config: Config):
        self.config = config
        self.result = AnalysisResult()
        self.module_name = ""
        self.file_path = ""
        
        # Context
        self.function_stack = []
        self.class_stack = []
        self.imports = {}
        
    def extract(self, tree: ast.AST, module_name: str, file_path: str) -> AnalysisResult:
        """Extract call graph from AST."""
        self.result = AnalysisResult()
        self.module_name = module_name
        self.file_path = file_path
        self.function_stack = []
        self.class_stack = []
        self.imports = {}
        
        self.visit(tree)
        return self.result
        
    def visit_Import(self, node: ast.Import):
        """Track imports."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = alias.name
            self.result.imports[name] = alias.name
            
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Track from imports."""
        module = node.module or ""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            full_name = f"{module}.{alias.name}" if module else alias.name
            self.imports[name] = full_name
            self.result.imports[name] = full_name
            
    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition."""
        self.class_stack.append(node.name)
        
        # Store class info
        self.result.classes[node.name] = {
            'file': self.file_path,
            'line': node.lineno,
            'methods': [m.name for m in node.body if isinstance(m, ast.FunctionDef)],
            'bases': [self._expr_to_str(b) for b in node.bases]
        }
        
        for stmt in node.body:
            self.visit(stmt)
            
        self.class_stack.pop()
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition and track calls within it."""
        func_name = self._qualified_name(node.name)
        self.function_stack.append(func_name)
        
        # Visit body to find calls
        for stmt in node.body:
            self.visit(stmt)
            
        self.function_stack.pop()
        
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function."""
        self.visit_FunctionDef(node)
        
    def visit_Call(self, node: ast.Call):
        """Track function calls."""
        if not self.function_stack:
            self.generic_visit(node)
            return
            
        caller = self.function_stack[-1]
        callee = self._resolve_call(node.func)
        
        if callee and caller in self.result.functions:
            self.result.functions[caller].calls.add(callee)
            
            # Create call edge
            edge = FlowEdge(
                source=-1,  # Will be resolved
                target=-1,
                edge_type="call",
                metadata={'caller': caller, 'callee': callee}
            )
            self.result.call_edges.append(edge)
            
        self.generic_visit(node)
        
    def _qualified_name(self, name: str) -> str:
        """Get fully qualified name."""
        parts = [self.module_name]
        if self.class_stack:
            parts.append(self.class_stack[-1])
        parts.append(name)
        return '.'.join(parts)
        
    def _resolve_call(self, node: ast.AST) -> Optional[str]:
        """Resolve a call to its full name."""
        if isinstance(node, ast.Name):
            # Simple function call
            if node.id in self.imports:
                return self.imports[node.id]
            return f"{self.module_name}.{node.id}"
            
        elif isinstance(node, ast.Attribute):
            # Method or module.function call
            parts = []
            current = node
            
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
                
            if isinstance(current, ast.Name):
                parts.append(current.id)
                parts.reverse()
                
                # Check if root is an import
                root = parts[0]
                if root in self.imports:
                    return f"{self.imports[root]}.{'.'.join(parts[1:])}"
                    
                # Check for self/cls
                if root in ('self', 'cls') and self.class_stack:
                    return f"{self.module_name}.{self.class_stack[-1]}.{'.'.join(parts[1:])}"
                    
                return f"{self.module_name}.{'.'.join(parts)}"
                
        return None
        
    def _expr_to_str(self, node: ast.AST) -> str:
        """Convert AST expression to string."""
        if node is None:
            return ""
        try:
            return ast.unparse(node) if hasattr(ast, 'unparse') else str(node)
        except:
            return str(node)
