"""Main project analyzer combining all analysis techniques."""

import ast
import os
from pathlib import Path
from typing import List, Optional

from ..core.config import Config
from ..core.models import AnalysisResult
from ..extractors.cfg_extractor import CFGExtractor
from ..extractors.dfg_extractor import DFGExtractor
from ..extractors.call_graph import CallGraphExtractor
from ..patterns.detector import PatternDetector


class ProjectAnalyzer:
    """Main project flow analyzer."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.result = AnalysisResult()
        self.extractors = []
        self._init_extractors()
        
    def _init_extractors(self):
        """Initialize analysis extractors."""
        self.cfg_extractor = CFGExtractor(self.config)
        self.dfg_extractor = DFGExtractor(self.config)
        self.call_extractor = CallGraphExtractor(self.config)
        self.pattern_detector = PatternDetector(self.config)
        
    def analyze_project(self, src_path: str) -> AnalysisResult:
        """Analyze entire project at given path."""
        src_path = Path(src_path)
        
        if not src_path.exists():
            raise FileNotFoundError(f"Source path not found: {src_path}")
            
        # Find all Python files
        python_files = self._find_python_files(src_path)
        
        # Analyze each file
        for file_path in python_files:
            self._analyze_file(file_path)
            
        # Build cross-file call graph
        self._resolve_cross_file_calls()
        
        # Detect patterns
        self.pattern_detector.detect_patterns(self.result)
        
        return self.result
        
    def _find_python_files(self, root: Path) -> List[Path]:
        """Find all Python files in directory."""
        python_files = []
        
        if root.is_file() and root.suffix == '.py':
            return [root]
            
        for path in root.rglob('*.py'):
            # Skip excluded directories
            if any(skip in str(path) for skip in self.config.skip_packages):
                continue
            python_files.append(path)
            
        return sorted(python_files)
        
    def _analyze_file(self, file_path: Path):
        """Analyze single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
                
            tree = ast.parse(source)
            module_name = self._get_module_name(file_path)
            
            # Extract CFG
            cfg_result = self.cfg_extractor.extract(tree, module_name, str(file_path))
            self._merge_result(cfg_result)
            
            # Extract DFG
            dfg_result = self.dfg_extractor.extract(tree, module_name, str(file_path))
            self._merge_result(dfg_result)
            
            # Extract call graph
            call_result = self.call_extractor.extract(tree, module_name, str(file_path))
            self._merge_result(call_result)
            
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            
    def _merge_result(self, partial_result: AnalysisResult):
        """Merge partial result into main result."""
        # Merge nodes (avoiding ID conflicts)
        node_id_offset = len(self.result.nodes)
        for node_id, node in partial_result.nodes.items():
            new_id = node_id + node_id_offset
            node.id = new_id
            self.result.nodes[new_id] = node
            
        # Adjust and merge edges
        for edge in partial_result.cfg_edges:
            edge.source += node_id_offset
            edge.target += node_id_offset
            self.result.cfg_edges.append(edge)
            
        for edge in partial_result.dfg_edges:
            edge.source += node_id_offset
            edge.target += node_id_offset
            self.result.dfg_edges.append(edge)
            
        for edge in partial_result.call_edges:
            edge.source += node_id_offset
            edge.target += node_id_offset
            self.result.call_edges.append(edge)
            
        # Merge other data
        self.result.functions.update(partial_result.functions)
        self.result.data_flows.update(partial_result.data_flows)
        self.result.imports.update(partial_result.imports)
        self.result.classes.update(partial_result.classes)
        
    def _resolve_cross_file_calls(self):
        """Resolve function calls across files."""
        # Build qualified name to function info mapping
        qualified_map = {}
        for func_name, func_info in self.result.functions.items():
            qualified_map[func_info.qualified_name] = func_info
            
        # Resolve calls
        for func_name, func_info in self.result.functions.items():
            resolved_calls = set()
            for call in func_info.calls:
                # Try to resolve call to qualified name
                if call in qualified_map:
                    resolved_calls.add(call)
                    qualified_map[call].called_by.add(func_name)
                else:
                    # Try with module prefixes
                    for qualified_name in qualified_map:
                        if qualified_name.endswith(f".{call}") or qualified_name == call:
                            resolved_calls.add(qualified_name)
                            qualified_map[qualified_name].called_by.add(func_name)
                            break
                    else:
                        resolved_calls.add(call)  # Keep unresolved
                        
            func_info.calls = resolved_calls
            
    def _get_module_name(self, file_path: Path) -> str:
        """Get module name from file path."""
        # Find the package root
        parts = []
        current = file_path.parent
        
        # Look for __init__.py to find package boundary
        while current.parent != current:
            if (current / '__init__.py').exists():
                parts.insert(0, current.name)
                current = current.parent
            else:
                break
                
        parts.append(file_path.stem)
        return '.'.join(parts) if parts else file_path.stem
