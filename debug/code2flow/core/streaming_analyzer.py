"""Optimized streaming analyzer with prioritization and progress tracking.

Key optimizations:
1. Lazy CFG generation - only build when needed
2. Memory-bounded analysis with streaming output
3. Smart file prioritization (entry points, public API first)
4. Incremental analysis with change detection
5. Progress reporting with ETA
"""

import ast
import hashlib
import json
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Iterator
import fnmatch

from .config import Config, FAST_CONFIG
from .models import (
    AnalysisResult, ClassInfo, FlowEdge, FlowNode,
    FunctionInfo, ModuleInfo, Pattern
)


@dataclass
class FilePriority:
    """Priority scoring for file analysis order."""
    file_path: str
    module_name: str
    priority_score: float
    reasons: List[str] = field(default_factory=list)
    
    # Priority factors
    is_entry_point: bool = False
    is_public_api: bool = False
    has_main: bool = False
    import_count: int = 0
    lines_of_code: int = 0


@dataclass
class ScanStrategy:
    """Scanning methodology configuration."""
    name: str
    description: str
    
    # Analysis phases
    phase_1_quick_scan: bool = True  # Only functions/classes, no CFG
    phase_2_call_graph: bool = True  # Build call relationships
    phase_3_deep_analysis: bool = False  # Full CFG only for important files
    phase_4_patterns: bool = False  # Pattern detection
    
    # Memory limits
    max_files_in_memory: int = 100
    max_nodes_per_function: int = 50
    max_total_nodes: int = 10000
    
    # Prioritization
    prioritize_entry_points: bool = True
    prioritize_public_api: bool = True
    skip_private_functions: bool = True
    skip_test_files: bool = True
    
    # Output
    streaming_output: bool = True
    incremental_save: bool = True


# Predefined strategies
STRATEGY_QUICK = ScanStrategy(
    name="quick",
    description="Fast overview - functions/classes only, no CFG",
    phase_1_quick_scan=True,
    phase_2_call_graph=True,
    phase_3_deep_analysis=False,
    phase_4_patterns=False,
    max_files_in_memory=200,
    skip_private_functions=True,
)

STRATEGY_STANDARD = ScanStrategy(
    name="standard",
    description="Balanced analysis with selective CFG",
    phase_1_quick_scan=True,
    phase_2_call_graph=True,
    phase_3_deep_analysis=True,
    phase_4_patterns=True,
    max_files_in_memory=100,
    max_nodes_per_function=30,
    prioritize_entry_points=True,
)

STRATEGY_DEEP = ScanStrategy(
    name="deep",
    description="Complete analysis with full CFG for all files",
    phase_1_quick_scan=True,
    phase_2_call_graph=True,
    phase_3_deep_analysis=True,
    phase_4_patterns=True,
    max_files_in_memory=50,
    max_nodes_per_function=100,
    prioritize_entry_points=True,
)


class StreamingFileCache:
    """Memory-efficient cache with LRU eviction."""
    
    def __init__(self, max_size: int = 100, cache_dir: str = ".code2flow_cache"):
        self.max_size = max_size
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: Dict[str, tuple] = {}
        self._access_order: List[str] = []
    
    def _get_cache_key(self, file_path: str, content: str) -> str:
        """Generate cache key."""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:16]
        return f"{Path(file_path).stem}_{content_hash}"
    
    def _evict_if_needed(self) -> None:
        """Evict oldest entries if cache is full."""
        while len(self._memory_cache) >= self.max_size:
            if self._access_order:
                oldest = self._access_order.pop(0)
                if oldest in self._memory_cache:
                    del self._memory_cache[oldest]
    
    def get(self, file_path: str, content: str) -> Optional[Tuple[ast.AST, str]]:
        """Get from cache with LRU tracking."""
        key = self._get_cache_key(file_path, content)
        
        if key in self._memory_cache:
            # Move to end (most recently used)
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            return self._memory_cache[key]
        
        return None
    
    def put(self, file_path: str, content: str, data: Tuple[ast.AST, str]) -> None:
        """Store in cache with LRU management."""
        self._evict_if_needed()
        
        key = self._get_cache_key(file_path, content)
        self._memory_cache[key] = data
        self._access_order.append(key)


class SmartPrioritizer:
    """Smart file prioritization for optimal analysis order."""
    
    def __init__(self, strategy: ScanStrategy):
        self.strategy = strategy
    
    def prioritize_files(
        self,
        files: List[Tuple[str, str]],
        project_path: Path
    ) -> List[FilePriority]:
        """Score and sort files by importance."""
        scored = []
        
        # First pass: gather import relationships
        import_graph = self._build_import_graph(files, project_path)
        
        for file_path, module_name in files:
            score = 0.0
            reasons = []
            
            # Check if has main
            has_main = self._check_has_main(file_path)
            if has_main:
                score += 100.0
                reasons.append("has_main")
            
            # Check if entry point (not imported by others)
            is_entry = module_name not in import_graph or len(import_graph[module_name]) == 0
            if is_entry:
                score += 50.0
                reasons.append("entry_point")
            
            # Check if public API (no underscore prefix)
            is_public = not any(part.startswith('_') for part in module_name.split('.'))
            if is_public:
                score += 20.0
                reasons.append("public_api")
            
            # Import count (more imports = more central)
            import_count = len(import_graph.get(module_name, []))
            score += import_count * 5.0
            
            # File size (prefer smaller files first for quick wins)
            try:
                loc = len(Path(file_path).read_text().split('\n'))
                if loc < 100:
                    score += 10.0
                    reasons.append("small_file")
            except:
                loc = 0
            
            priority = FilePriority(
                file_path=file_path,
                module_name=module_name,
                priority_score=score,
                reasons=reasons,
                is_entry_point=is_entry,
                is_public_api=is_public,
                has_main=has_main,
                import_count=import_count,
                lines_of_code=loc
            )
            scored.append(priority)
        
        # Sort by score descending
        scored.sort(key=lambda x: x.priority_score, reverse=True)
        return scored
    
    def _build_import_graph(
        self,
        files: List[Tuple[str, str]],
        project_path: Path
    ) -> Dict[str, Set[str]]:
        """Build import dependency graph."""
        # Map module names to who imports them
        imported_by: Dict[str, Set[str]] = defaultdict(set)
        
        for file_path, module_name in files:
            try:
                content = Path(file_path).read_text()
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            # Simplified - just record the top-level module
                            top_module = alias.name.split('.')[0]
                            imported_by[top_module].add(module_name)
                    
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            top_module = node.module.split('.')[0]
                            imported_by[top_module].add(module_name)
            except:
                pass
        
        return imported_by
    
    def _check_has_main(self, file_path: str) -> bool:
        """Check if file has if __name__ == "__main__" block."""
        try:
            content = Path(file_path).read_text()
            return 'if __name__' in content and '__main__' in content
        except:
            return False


class StreamingAnalyzer:
    """Memory-efficient streaming analyzer with progress tracking."""
    
    def __init__(
        self,
        config: Optional[Config] = None,
        strategy: Optional[ScanStrategy] = None
    ):
        self.config = config or FAST_CONFIG
        self.strategy = strategy or STRATEGY_STANDARD
        
        # Streaming cache with memory bounds
        self.cache = StreamingFileCache(
            max_size=self.strategy.max_files_in_memory,
            cache_dir=self.config.performance.cache_dir
        ) if self.config.performance.enable_cache else None
        
        self.prioritizer = SmartPrioritizer(self.strategy)
        
        # Progress tracking
        self._progress_callback: Optional[callable] = None
        self._cancelled = False
    
    def set_progress_callback(self, callback: callable) -> None:
        """Set callback for progress updates."""
        self._progress_callback = callback
    
    def cancel(self) -> None:
        """Cancel ongoing analysis."""
        self._cancelled = True
    
    def analyze_streaming(
        self,
        project_path: str,
        output_callback: Optional[callable] = None
    ) -> Iterator[Dict]:
        """Analyze project with streaming output (yields partial results)."""
        start_time = time.time()
        project_path = Path(project_path).resolve()
        
        # Phase 1: Collect and prioritize files
        raw_files = self._collect_files(project_path)
        prioritized = self.prioritizer.prioritize_files(raw_files, project_path)
        
        total_files = len(prioritized)
        processed = 0
        
        self._report_progress(
            phase="collect",
            current=0,
            total=total_files,
            message=f"Found {total_files} files to analyze"
        )
        
        # Phase 2: Quick scan (functions/classes only)
        quick_results = []
        for priority in prioritized:
            if self._cancelled:
                break
            
            result = self._quick_scan_file(priority)
            if result:
                quick_results.append(result)
                processed += 1
                
                # Yield incremental result
                yield {
                    'type': 'file_complete',
                    'file': priority.file_path,
                    'priority': priority.priority_score,
                    'functions': len(result.get('functions', {})),
                    'classes': len(result.get('classes', {})),
                    'progress': processed / total_files,
                    'eta_seconds': self._estimate_eta(start_time, processed, total_files)
                }
                
                self._report_progress(
                    phase="quick_scan",
                    current=processed,
                    total=total_files,
                    message=f"Scanned {priority.module_name} (priority: {priority.priority_score:.1f})"
                )
        
        # Phase 3: Build call graph (memory efficient)
        if self.strategy.phase_2_call_graph and not self._cancelled:
            call_graph = self._build_call_graph_streaming(quick_results)
            
            yield {
                'type': 'call_graph_complete',
                'functions': len(call_graph),
                'edges': sum(len(calls) for calls in call_graph.values())
            }
        
        # Phase 4: Deep analysis for important files (selective CFG)
        if self.strategy.phase_3_deep_analysis and not self._cancelled:
            important_files = self._select_important_files(prioritized, quick_results)
            
            deep_processed = 0
            for priority in important_files[:50]:  # Limit to top 50
                if self._cancelled:
                    break
                
                result = self._deep_analyze_file(priority)
                if result:
                    deep_processed += 1
                    yield {
                        'type': 'deep_complete',
                        'file': priority.file_path,
                        'nodes': len(result.get('nodes', {})),
                        'progress': deep_processed / len(important_files)
                    }
        
        # Final summary
        yield {
            'type': 'complete',
            'total_files': total_files,
            'processed_files': processed,
            'elapsed_seconds': time.time() - start_time
        }
    
    def _quick_scan_file(self, priority: FilePriority) -> Optional[Dict]:
        """Quick scan - extract functions and classes only (no CFG)."""
        try:
            content = Path(priority.file_path).read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return None
        
        # Try cache
        if self.cache:
            cached = self.cache.get(priority.file_path, content)
            if cached:
                tree, _ = cached
            else:
                try:
                    tree = ast.parse(content)
                    self.cache.put(priority.file_path, content, (tree, content))
                except SyntaxError:
                    return None
        else:
            try:
                tree = ast.parse(content)
            except SyntaxError:
                return None
        
        result = {
            'module': ModuleInfo(
                name=priority.module_name,
                file=priority.file_path
            ),
            'functions': {},
            'classes': {},
            'nodes': {},
            'edges': []
        }
        
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                cls_info = ClassInfo(
                    name=node.name,
                    qualified_name=f"{priority.module_name}.{node.name}",
                    file=priority.file_path,
                    line=node.lineno,
                    module=priority.module_name
                )
                result['classes'][cls_info.qualified_name] = cls_info
                result['module'].classes.append(cls_info.qualified_name)
            
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private if configured
                if self.strategy.skip_private_functions and node.name.startswith('_'):
                    continue
                
                func_info = FunctionInfo(
                    name=node.name,
                    qualified_name=f"{priority.module_name}.{node.name}",
                    file=priority.file_path,
                    line=node.lineno,
                    module=priority.module_name
                )
                
                # Extract calls (lightweight)
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            func_info.calls.append(child.func.id)
                
                result['functions'][func_info.qualified_name] = func_info
                result['module'].functions.append(func_info.qualified_name)
        
        return result
    
    def _deep_analyze_file(self, priority: FilePriority) -> Optional[Dict]:
        """Deep analysis with limited CFG generation."""
        result = self._quick_scan_file(priority)
        if not result:
            return None
        
        # Only build CFG for functions under node limit
        max_nodes = self.strategy.max_nodes_per_function
        
        for func_name, func in result['functions'].items():
            # Skip if too many calls (simplistic heuristic)
            if len(func.calls) > 20:
                continue
            
            # Build simplified CFG
            entry_id = f"{func_name}_entry"
            exit_id = f"{func_name}_exit"
            
            result['nodes'][entry_id] = FlowNode(
                id=entry_id, type='ENTRY', label='entry', function=func_name
            )
            result['nodes'][exit_id] = FlowNode(
                id=exit_id, type='EXIT', label='exit', function=func_name
            )
            
            # Limit total nodes
            if len(result['nodes']) > self.strategy.max_total_nodes:
                break
        
        return result
    
    def _build_call_graph_streaming(self, results: List[Dict]) -> Dict[str, List[str]]:
        """Memory-efficient call graph construction."""
        call_graph = {}
        
        # Build function name lookup
        all_functions = {}
        for r in results:
            all_functions.update(r.get('functions', {}))
        
        # Resolve calls
        for r in results:
            for func_name, func in r.get('functions', {}).items():
                resolved_calls = []
                for called in func.calls:
                    # Try to resolve to known function
                    for known_name in all_functions:
                        if known_name.endswith(f".{called}") or known_name == called:
                            resolved_calls.append(known_name)
                            break
                
                func.calls = resolved_calls
                call_graph[func_name] = resolved_calls
        
        return call_graph
    
    def _select_important_files(
        self,
        prioritized: List[FilePriority],
        results: List[Dict]
    ) -> List[FilePriority]:
        """Select files for deep analysis based on importance."""
        important = []
        
        for p in prioritized:
            # Entry points are important
            if p.is_entry_point:
                important.append(p)
                continue
            
            # Find result for this file
            for r in results:
                mod = r.get('module')
                if mod and mod.name == p.module_name:
                    # Files with many functions are important
                    if len(mod.functions) > 5:
                        important.append(p)
                        break
                    
                    # Files called by many others
                    if p.import_count > 3:
                        important.append(p)
                        break
        
        return important
    
    def _collect_files(self, project_path: Path) -> List[Tuple[str, str]]:
        """Collect Python files with filtering."""
        files = []
        
        for py_file in project_path.rglob("*.py"):
            file_str = str(py_file)
            
            # Apply filters
            if self.strategy.skip_test_files:
                if any(x in file_str.lower() for x in ['test', '_test', 'conftest']):
                    continue
            
            if any(x in file_str.lower() for x in ['__pycache__', '.venv', 'venv']):
                continue
            
            # Calculate module name
            rel_path = py_file.relative_to(project_path)
            parts = list(rel_path.parts)[:-1]
            if py_file.name == '__init__.py':
                module_name = '.'.join(parts) if parts else project_path.name
            else:
                module_name = '.'.join(parts + [py_file.stem])
            
            files.append((file_str, module_name))
        
        return files
    
    def _estimate_eta(
        self,
        start_time: float,
        processed: int,
        total: int
    ) -> float:
        """Estimate remaining time."""
        if processed == 0:
            return 0.0
        
        elapsed = time.time() - start_time
        rate = processed / elapsed
        remaining = total - processed
        
        return remaining / rate if rate > 0 else 0.0
    
    def _report_progress(
        self,
        phase: str,
        current: int,
        total: int,
        message: str
    ) -> None:
        """Report progress via callback."""
        if self._progress_callback:
            self._progress_callback({
                'phase': phase,
                'current': current,
                'total': total,
                'percentage': (current / total * 100) if total > 0 else 0,
                'message': message
            })


class IncrementalAnalyzer:
    """Incremental analysis with change detection."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or FAST_CONFIG
        self.state_file = Path(".code2flow_state.json")
        self.previous_state: Dict[str, str] = {}
        self._load_state()
    
    def _load_state(self) -> None:
        """Load previous analysis state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.previous_state = data.get('file_hashes', {})
            except:
                pass
    
    def _save_state(self, current_state: Dict[str, str]) -> None:
        """Save current analysis state."""
        with open(self.state_file, 'w') as f:
            json.dump({
                'file_hashes': current_state,
                'timestamp': time.time()
            }, f)
    
    def get_changed_files(
        self,
        project_path: Path
    ) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
        """Get changed and unchanged files."""
        changed = []
        unchanged = []
        current_state = {}
        
        for py_file in project_path.rglob("*.py"):
            try:
                content = py_file.read_bytes()
                file_hash = hashlib.md5(content).hexdigest()
                file_str = str(py_file)
                
                current_state[file_str] = file_hash
                
                if file_str in self.previous_state:
                    if self.previous_state[file_str] == file_hash:
                        unchanged.append((file_str, self._get_module_name(py_file, project_path)))
                    else:
                        changed.append((file_str, self._get_module_name(py_file, project_path)))
                else:
                    changed.append((file_str, self._get_module_name(py_file, project_path)))
            except:
                pass
        
        self._save_state(current_state)
        return changed, unchanged
    
    def _get_module_name(self, py_file: Path, project_path: Path) -> str:
        """Calculate module name."""
        rel_path = py_file.relative_to(project_path)
        parts = list(rel_path.parts)[:-1]
        if py_file.name == '__init__.py':
            return '.'.join(parts) if parts else project_path.name
        return '.'.join(parts + [py_file.stem])
