"""Control Flow Graph (CFG) extractor using AST."""

import ast
from collections import defaultdict
from typing import Optional

from ..core.config import Config
from ..core.models import AnalysisResult, FlowNode, FlowEdge, FunctionInfo


class CFGExtractor(ast.NodeVisitor):
    """Extract Control Flow Graph from AST."""
    
    def __init__(self, config: Config):
        self.config = config
        self.result = AnalysisResult()
        self.module_name = ""
        self.file_path = ""
        self.node_counter = 0
        
        # Context tracking
        self.function_stack = []
        self.class_stack = []
        self.current_node = None
        self.entry_nodes = {}  # Function -> entry node ID
        
    def extract(self, tree: ast.AST, module_name: str, file_path: str) -> AnalysisResult:
        """Extract CFG from AST."""
        self.result = AnalysisResult()
        self.module_name = module_name
        self.file_path = file_path
        self.node_counter = 0
        
        self.visit(tree)
        return self.result
        
    def new_node(self, node_type: str, label: str, **kwargs) -> int:
        """Create new flow node."""
        node_id = self.node_counter
        self.node_counter += 1
        
        node = FlowNode(
            id=node_id,
            type=node_type,
            label=label,
            function=self.function_stack[-1] if self.function_stack else None,
            file=self.file_path,
            line=kwargs.get('line'),
            column=kwargs.get('column'),
            conditions=kwargs.get('conditions', []),
            data_flow=kwargs.get('data_flow', [])
        )
        
        self.result.nodes[node_id] = node
        return node_id
        
    def connect(self, source: Optional[int], target: Optional[int], 
                edge_type: str = "control", condition: Optional[str] = None):
        """Create edge between nodes."""
        if source is not None and target is not None:
            edge = FlowEdge(
                source=source,
                target=target,
                edge_type=edge_type,
                condition=condition
            )
            self.result.cfg_edges.append(edge)
            
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition."""
        func_name = self._qualified_name(node.name)
        self.function_stack.append(func_name)
        
        # Create entry node
        entry = self.new_node("FUNC", f"FUNC:{func_name}", line=node.lineno)
        self.entry_nodes[func_name] = entry
        
        # Track previous node
        prev_node = self.current_node
        self.current_node = entry
        
        # Store function info
        func_info = FunctionInfo(
            name=node.name,
            qualified_name=func_name,
            file=self.file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            args=[arg.arg for arg in node.args.args]
        )
        self.result.functions[func_name] = func_info
        
        # Visit body
        for stmt in node.body:
            self.visit(stmt)
            
        # Create exit node
        exit_node = self.new_node("RETURN", f"RETURN:{func_name}", 
                                  line=node.end_lineno or node.lineno)
        self.connect(self.current_node, exit_node)
        
        # Restore context
        self.function_stack.pop()
        self.current_node = prev_node
        
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function definition."""
        self.visit_FunctionDef(node)  # Treat same as sync for CFG
        
    def visit_If(self, node: ast.If):
        """Visit if statement."""
        # Create condition node
        condition = self._extract_condition(node.test)
        cond_node = self.new_node("IF", condition, line=node.lineno)
        self.connect(self.current_node, cond_node, condition=condition)
        
        # Save current for branches
        branch_entry = cond_node
        
        # Visit then branch
        then_last = []
        for stmt in node.body:
            prev = self.current_node
            self.current_node = branch_entry
            self.visit(stmt)
            then_last.append(self.current_node)
            branch_entry = self.current_node
            
        # Visit else branch
        else_last = []
        if node.orelse:
            branch_entry = cond_node
            for stmt in node.orelse:
                prev = self.current_node
                self.current_node = branch_entry
                self.visit(stmt)
                else_last.append(self.current_node)
                branch_entry = self.current_node
                
        # Merge point
        merge_node = self.new_node("MERGE", "merge", line=node.end_lineno)
        for last in then_last + else_last:
            self.connect(last, merge_node)
            
        self.current_node = merge_node
        
    def visit_For(self, node: ast.For):
        """Visit for loop."""
        # Create loop header
        iter_str = self._expr_to_str(node.iter)
        target_str = self._expr_to_str(node.target)
        loop_header = self.new_node("FOR", f"for {target_str} in {iter_str}", 
                                    line=node.lineno)
        self.connect(self.current_node, loop_header)
        
        # Loop body
        body_entry = loop_header
        body_last = []
        for stmt in node.body:
            self.current_node = body_entry
            self.visit(stmt)
            body_last.append(self.current_node)
            body_entry = self.current_node
            
        # Back edge to header
        for last in body_last:
            self.connect(last, loop_header, edge_type="loop")
            
        # Exit (after loop)
        exit_node = self.new_node("EXIT_LOOP", "exit_loop", line=node.end_lineno)
        self.connect(loop_header, exit_node)  # False branch
        self.current_node = exit_node
        
    def visit_While(self, node: ast.While):
        """Visit while loop."""
        # Loop header with condition
        condition = self._extract_condition(node.test)
        loop_header = self.new_node("WHILE", f"while {condition}", line=node.lineno)
        self.connect(self.current_node, loop_header)
        
        # Loop body
        body_entry = loop_header
        body_last = []
        for stmt in node.body:
            self.current_node = body_entry
            self.visit(stmt)
            body_last.append(self.current_node)
            body_entry = self.current_node
            
        # Back edge
        for last in body_last:
            self.connect(last, loop_header, edge_type="loop")
            
        # Exit
        exit_node = self.new_node("EXIT_LOOP", "exit_loop", line=node.end_lineno)
        self.connect(loop_header, exit_node, condition="False")
        self.current_node = exit_node
        
    def visit_Try(self, node: ast.Try):
        """Visit try statement."""
        try_entry = self.new_node("TRY", "try", line=node.lineno)
        self.connect(self.current_node, try_entry)
        
        # Try body
        self.current_node = try_entry
        for stmt in node.body:
            self.visit(stmt)
        try_last = self.current_node
        
        # Except handlers
        for handler in node.handlers:
            handler_node = self.new_node("EXCEPT", self._format_except(handler), 
                                         line=handler.lineno)
            self.connect(try_entry, handler_node, edge_type="exception")
            
            self.current_node = handler_node
            for stmt in handler.body:
                self.visit(stmt)
                
        # Merge
        merge = self.new_node("MERGE", "merge", line=node.end_lineno)
        self.connect(try_last, merge)
        self.current_node = merge
        
    def visit_Assign(self, node: ast.Assign):
        """Visit assignment."""
        targets = [self._expr_to_str(t) for t in node.targets]
        value = self._expr_to_str(node.value)
        label = f"{' = '.join(targets)} = {value[:50]}"
        
        assign_node = self.new_node("ASSIGN", label, line=node.lineno)
        self.connect(self.current_node, assign_node)
        self.current_node = assign_node
        
    def visit_Return(self, node: ast.Return):
        """Visit return statement."""
        value = self._expr_to_str(node.value) if node.value else "None"
        return_node = self.new_node("RETURN", f"return {value[:50]}", line=node.lineno)
        self.connect(self.current_node, return_node)
        self.current_node = return_node
        
    def visit_Expr(self, node: ast.Expr):
        """Visit expression statement."""
        if isinstance(node.value, ast.Call):
            # Function call
            call_name = self._expr_to_str(node.value.func)
            args = [self._expr_to_str(a) for a in node.value.args]
            label = f"CALL {call_name}({', '.join(args)})"[:80]
            
            call_node = self.new_node("CALL", label, line=node.lineno)
            self.connect(self.current_node, call_node)
            self.current_node = call_node
            
            # Track call in function info
            if self.function_stack:
                func_name = self.function_stack[-1]
                if func_name in self.result.functions:
                    self.result.functions[func_name].calls.add(call_name)
        else:
            self.generic_visit(node)
            
    def _qualified_name(self, name: str) -> str:
        """Get fully qualified name."""
        parts = [self.module_name]
        if self.class_stack:
            parts.append(self.class_stack[-1])
        parts.append(name)
        return '.'.join(parts)
        
    def _extract_condition(self, node: ast.AST) -> str:
        """Extract condition as string."""
        try:
            return ast.unparse(node) if hasattr(ast, 'unparse') else str(node)[:50]
        except:
            return str(node)[:50]
            
    def _expr_to_str(self, node: ast.AST) -> str:
        """Convert AST expression to string."""
        if node is None:
            return "None"
        try:
            return ast.unparse(node) if hasattr(ast, 'unparse') else str(node)
        except:
            return str(node)
            
    def _format_except(self, handler: ast.ExceptHandler) -> str:
        """Format except handler."""
        if handler.type:
            type_str = self._expr_to_str(handler.type)
            if handler.name:
                return f"except {type_str} as {handler.name}"
            return f"except {type_str}"
        return "except"
