"""Export analysis results to various formats."""

import json
import yaml
from pathlib import Path
from typing import Any, Dict

from ..core.models import AnalysisResult


class JSONExporter:
    """Export to JSON format."""
    
    def export(self, result: AnalysisResult, output_path: str, compact: bool = True, include_defaults: bool = False) -> None:
        """Export to JSON file."""
        data = result.to_dict(compact=compact and not include_defaults)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2 if not compact else None, ensure_ascii=False)


class YAMLExporter:
    """Export to YAML format."""
    
    def export(self, result: AnalysisResult, output_path: str, compact: bool = True, include_defaults: bool = False) -> None:
        """Export to YAML file."""
        data = result.to_dict(compact=compact and not include_defaults)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    def export_grouped(self, result: AnalysisResult, output_path: str) -> None:
        """Export with grouped CFG flows by function - more readable format."""
        # Group CFG nodes by function
        from collections import defaultdict
        
        func_flows = defaultdict(list)
        
        # Group nodes by their function
        for node_id, node in result.nodes.items():
            if hasattr(node, 'function') and node.function:
                func_flows[node.function].append({
                    'id': node_id,
                    'type': getattr(node, 'type', 'unknown'),
                    'label': getattr(node, 'label', ''),
                    'line': getattr(node, 'line', None),
                })
        
        # Build flow sequences
        grouped_data = {
            'project': result.project_path,
            'analysis_mode': result.analysis_mode,
            'summary': {
                'functions': len(result.functions),
                'classes': len(result.classes),
                'modules': len(result.modules),
            },
            'control_flows': {}
        }
        
        for func_name, nodes in sorted(func_flows.items()):
            if len(nodes) < 2:
                continue
                
            # Sort nodes to create logical flow
            sorted_nodes = sorted(nodes, key=lambda n: (n['line'] or 0, n['id']))
            
            # Create flow sequence
            flow_sequence = []
            for i, node in enumerate(sorted_nodes):
                flow_sequence.append({
                    'step': i + 1,
                    'node_type': node['type'],
                    'label': node['label'][:50] if node['label'] else node['type'],
                    'line': node['line'],
                })
            
            grouped_data['control_flows'][func_name] = {
                'node_count': len(nodes),
                'flow_sequence': flow_sequence,
                'entry_point': sorted_nodes[0]['id'] if sorted_nodes else None,
                'exit_point': sorted_nodes[-1]['id'] if sorted_nodes else None,
            }
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(grouped_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    def export_split(self, result: AnalysisResult, output_dir: str, compact: bool = True, include_defaults: bool = False) -> None:
        """Export analysis split into multiple files for large repositories.
        
        Creates:
        - summary.yaml - project overview and stats
        - functions.yaml - all functions with their calls
        - classes.yaml - all classes with methods
        - modules.yaml - all modules
        - cfg_nodes.yaml - control flow graph nodes (optional, can be large)
        - entry_points.yaml - main entry points
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        compact_mode = compact and not include_defaults
        
        # 1. Summary file
        summary = {
            'project': result.project_path,
            'analysis_mode': result.analysis_mode,
            'stats': result.stats,
            'overview': {
                'total_functions': len(result.functions),
                'total_classes': len(result.classes),
                'total_modules': len(result.modules),
                'total_nodes': len(result.nodes),
                'total_edges': len(result.edges),
                'entry_points_count': len(result.entry_points),
            }
        }
        with open(output_path / 'summary.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(summary, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        # 2. Functions file
        functions_data = {
            'count': len(result.functions),
            'functions': {k: v.to_dict(compact_mode) for k, v in result.functions.items()}
        }
        with open(output_path / 'functions.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(functions_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        # 3. Classes file
        classes_data = {
            'count': len(result.classes),
            'classes': {k: v.to_dict(compact_mode) for k, v in result.classes.items()}
        }
        with open(output_path / 'classes.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(classes_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        # 4. Modules file
        modules_data = {
            'count': len(result.modules),
            'modules': {k: v.to_dict(compact_mode) for k, v in result.modules.items()}
        }
        with open(output_path / 'modules.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(modules_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        # 5. Entry points file
        entry_data = {
            'count': len(result.entry_points),
            'entry_points': result.entry_points,
            'important_entries': []
        }
        # Add detailed info for top entry points
        for ep in result.entry_points[:50]:
            func = result.functions.get(ep)
            if func:
                entry_data['important_entries'].append({
                    'name': ep,
                    'calls_count': len(func.calls),
                    'called_by_count': len(func.called_by),
                    'file': func.file,
                    'line': func.line,
                })
        with open(output_path / 'entry_points.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(entry_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        # 6. CFG nodes (only if not compact mode, can be very large)
        if not compact_mode:
            nodes_data = {
                'count': len(result.nodes),
                'nodes': {k: v.to_dict(compact_mode) for k, v in result.nodes.items()}
            }
            with open(output_path / 'cfg_nodes.yaml', 'w', encoding='utf-8') as f:
                yaml.dump(nodes_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        # Print summary with file sizes
        summary_size = (output_path / 'summary.yaml').stat().st_size // 1024
        functions_size = (output_path / 'functions.yaml').stat().st_size // 1024
        classes_size = (output_path / 'classes.yaml').stat().st_size // 1024
        modules_size = (output_path / 'modules.yaml').stat().st_size // 1024
        entry_size = (output_path / 'entry_points.yaml').stat().st_size // 1024
        
        print(f"✓ Split export created in {output_dir}:")
        print(f"  - summary.yaml ({summary_size}KB)")
        print(f"  - functions.yaml ({functions_size}KB)")
        print(f"  - classes.yaml ({classes_size}KB)")
        print(f"  - modules.yaml ({modules_size}KB)")
        print(f"  - entry_points.yaml ({entry_size}KB)")
        if not compact_mode:
            print(f"  - cfg_nodes.yaml")
    
    def export_separated(self, result: AnalysisResult, output_dir: str, compact: bool = True) -> dict:
        """Export analysis separating consolidated project from orphaned functions.
        
        Creates two folders:
        - consolidated/ - functions connected to the main project structure
        - orphans/ - isolated functions not connected to main flows
        
        Returns statistics about the separation.
        """
        from collections import defaultdict
        
        output_path = Path(output_dir)
        consolidated_dir = output_path / 'consolidated'
        orphans_dir = output_path / 'orphans'
        consolidated_dir.mkdir(parents=True, exist_ok=True)
        orphans_dir.mkdir(parents=True, exist_ok=True)
        
        # Identify orphan functions
        # Orphans = no calls AND not called by anyone (isolated)
        # Or = called but caller is also orphan (dead code chain)
        
        consolidated_funcs = {}
        orphan_funcs = {}
        
        # First pass: identify clearly connected functions
        for func_name, func in result.functions.items():
            has_calls = len(func.calls) > 0
            is_called = len(func.called_by) > 0
            is_entry = func_name in result.entry_points
            
            if is_entry:
                # Entry points are always consolidated
                consolidated_funcs[func_name] = func
            elif has_calls and is_called:
                # Functions that both call and are called = consolidated
                consolidated_funcs[func_name] = func
            elif is_called and not has_calls:
                # Leaf functions (called but don't call) = consolidated
                consolidated_funcs[func_name] = func
            elif has_calls and not is_called:
                # Functions that call but aren't called = check if they call consolidated
                calls_consolidated = any(c in consolidated_funcs for c in func.calls)
                if calls_consolidated:
                    consolidated_funcs[func_name] = func
                else:
                    orphan_funcs[func_name] = func
            else:
                # No calls, not called = orphan
                orphan_funcs[func_name] = func
        
        # Second pass: resolve chains (functions called by orphans are also orphans)
        changed = True
        iterations = 0
        while changed and iterations < 10:
            changed = False
            iterations += 1
            for func_name, func in list(consolidated_funcs.items()):
                # If all callers are orphans, this becomes orphan
                if func.called_by and all(c in orphan_funcs for c in func.called_by):
                    orphan_funcs[func_name] = func
                    del consolidated_funcs[func_name]
                    changed = True
        
        # Group nodes by function for each category
        def get_nodes_for_funcs(funcs):
            nodes = {}
            for node_id, node in result.nodes.items():
                if hasattr(node, 'function') and node.function in funcs:
                    nodes[node_id] = node
            return nodes
        
        consolidated_nodes = get_nodes_for_funcs(consolidated_funcs)
        orphan_nodes = get_nodes_for_funcs(orphan_funcs)
        
        # Export consolidated project
        consolidated_data = {
            'summary': {
                'total_functions': len(consolidated_funcs),
                'total_nodes': len(consolidated_nodes),
                'percentage_of_project': f"{len(consolidated_funcs) / len(result.functions) * 100:.1f}%",
                'description': 'Functions connected to main project flows - REFACTOR THESE',
            },
            'functions': {k: v.to_dict(compact) for k, v in consolidated_funcs.items()},
            'nodes': {k: v.to_dict(compact) for k, v in consolidated_nodes.items()},
        }
        
        with open(consolidated_dir / 'project.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(consolidated_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        # Export orphans
        orphan_data = {
            'summary': {
                'total_functions': len(orphan_funcs),
                'total_nodes': len(orphan_nodes),
                'percentage_of_project': f"{len(orphan_funcs) / len(result.functions) * 100:.1f}%",
                'description': 'Isolated functions NOT connected to main flows - LEAVE AS IS',
            },
            'functions': {k: v.to_dict(compact) for k, v in orphan_funcs.items()},
            'nodes': {k: v.to_dict(compact) for k, v in orphan_nodes.items()},
        }
        
        with open(orphans_dir / 'isolated.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(orphan_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        # Create index file
        index = {
            'project_path': result.project_path,
            'separation_strategy': 'connectivity-based',
            'consolidated': {
                'function_count': len(consolidated_funcs),
                'percentage': f"{len(consolidated_funcs) / len(result.functions) * 100:.1f}%",
                'location': 'consolidated/',
                'files': ['consolidated/project.yaml'],
            },
            'orphans': {
                'function_count': len(orphan_funcs),
                'percentage': f"{len(orphan_funcs) / len(result.functions) * 100:.1f}%",
                'location': 'orphans/',
                'files': ['orphans/isolated.yaml'],
            },
            'orphan_function_list': sorted(orphan_funcs.keys())[:100],  # First 100 for reference
        }
        
        with open(output_path / 'index.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(index, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        # Print summary
        print(f"✓ Separated export created in {output_dir}:")
        print(f"  📦 consolidated/project.yaml - {len(consolidated_funcs)} functions ({len(consolidated_funcs) / len(result.functions) * 100:.1f}%)")
        print(f"     → Functions connected to main project flows")
        print(f"     → REFACTOR THESE")
        print(f"  🗑️  orphans/isolated.yaml - {len(orphan_funcs)} functions ({len(orphan_funcs) / len(result.functions) * 100:.1f}%)")
        print(f"     → Isolated functions not connected to main flows")
        print(f"     → LEAVE AS IS (do not refactor)")
        
        return {
            'consolidated_count': len(consolidated_funcs),
            'orphan_count': len(orphan_funcs),
            'total': len(result.functions),
        }
    
    def export_data_flow(self, result: AnalysisResult, output_path: str, compact: bool = True) -> None:
        """Export detailed data flow analysis showing what happens in the project.
        
        Analyzes:
        - Data pipelines (input → transform → output)
        - State transitions and lifecycles
        - Cross-component data dependencies
        - Event/callback flows
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 1. Identify data transformation chains
        data_pipelines = self._find_data_pipelines(result)
        
        # 2. Identify state management patterns
        state_patterns = self._find_state_patterns(result)
        
        # 3. Identify data dependencies between modules
        data_deps = self._find_data_dependencies(result)
        
        # 4. Identify event/callback flows
        event_flows = self._find_event_flows(result)
        
        # Build data flow report
        flow_data = {
            'project_path': result.project_path,
            'analysis_type': 'data_flow',
            'summary': {
                'data_pipelines_count': len(data_pipelines),
                'state_managers_count': len(state_patterns),
                'cross_module_data_deps': len(data_deps),
                'event_flows_count': len(event_flows),
            },
            'data_pipelines': data_pipelines,
            'state_patterns': state_patterns,
            'data_dependencies': data_deps,
            'event_flows': event_flows,
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(flow_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        print(f"✓ Data flow exported: {output_path}")
        print(f"  - Data pipelines: {len(data_pipelines)}")
        print(f"  - State patterns: {len(state_patterns)}")
        print(f"  - Data dependencies: {len(data_deps)}")
        print(f"  - Event flows: {len(event_flows)}")
    
    def _find_data_pipelines(self, result: AnalysisResult) -> list:
        """Find data transformation pipelines in the codebase."""
        pipelines = []
        
        # Data processing indicators by stage
        input_indicators = ['parse', 'load', 'read', 'fetch', 'get', 'input', 'receive', 'extract']
        transform_indicators = ['transform', 'convert', 'process', 'validate', 'filter', 'map', 'reduce', 'compute']
        output_indicators = ['serialize', 'format', 'write', 'save', 'send', 'output', 'render', 'encode']
        
        # Group functions by their data role
        input_funcs = []
        transform_funcs = []
        output_funcs = []
        
        for func_name, func in result.functions.items():
            name_lower = func.name.lower()
            
            if any(ind in name_lower for ind in input_indicators):
                input_funcs.append((func_name, func))
            elif any(ind in name_lower for ind in transform_indicators):
                transform_funcs.append((func_name, func))
            elif any(ind in name_lower for ind in output_indicators):
                output_funcs.append((func_name, func))
        
        # Find chains: input → transform → output
        for in_name, in_func in input_funcs[:20]:
            for t_name, t_func in transform_funcs[:30]:
                # Check if input calls transform
                if t_name in in_func.calls:
                    for out_name, out_func in output_funcs[:20]:
                        # Check if transform calls output
                        if out_name in t_func.calls:
                            pipelines.append({
                                'pipeline_id': f"pipeline_{len(pipelines)+1}",
                                'stages': [
                                    {'stage': 'input', 'function': in_name, 'description': in_func.docstring[:100] if in_func.docstring else 'N/A'},
                                    {'stage': 'transform', 'function': t_name, 'description': t_func.docstring[:100] if t_func.docstring else 'N/A'},
                                    {'stage': 'output', 'function': out_name, 'description': out_func.docstring[:100] if out_func.docstring else 'N/A'},
                                ],
                                'data_flow': f"{in_name} → {t_name} → {out_name}",
                            })
                            if len(pipelines) >= 15:
                                return pipelines
        
        return pipelines
    
    def _find_state_patterns(self, result: AnalysisResult) -> list:
        """Find state management patterns and lifecycles."""
        patterns = []
        
        # State-related keywords
        state_indicators = ['state', 'status', 'mode', 'phase', 'lifecycle', 'session', 'context']
        transition_indicators = ['transition', 'change', 'update', 'set_state', 'switch']
        
        for func_name, func in result.functions.items():
            name_lower = func.name.lower()
            
            # Check for state management functions
            is_state_related = any(ind in name_lower for ind in state_indicators + transition_indicators)
            
            if is_state_related:
                # Find what states this function affects
                affected_states = []
                for call in func.calls[:10]:
                    call_func = result.functions.get(call)
                    if call_func:
                        call_lower = call_func.name.lower()
                        if any(ind in call_lower for ind in state_indicators):
                            affected_states.append(call)
                
                patterns.append({
                    'function': func_name,
                    'type': 'state_manager' if 'set' in name_lower or 'update' in name_lower else 'state_reader',
                    'affects_states': affected_states[:5],
                    'description': func.docstring[:150] if func.docstring else 'N/A',
                })
                
                if len(patterns) >= 20:
                    break
        
        return patterns
    
    def _find_data_dependencies(self, result: AnalysisResult) -> list:
        """Find cross-module data dependencies."""
        deps = []
        
        # Track which modules share data
        module_data_flow = {}
        
        for func_name, func in result.functions.items():
            func_module = func_name.rsplit('.', 1)[0] if '.' in func_name else 'root'
            
            for called in func.calls[:15]:
                called_module = called.rsplit('.', 1)[0] if '.' in called else 'root'
                
                if func_module != called_module and called in result.functions:
                    key = (func_module, called_module)
                    if key not in module_data_flow:
                        module_data_flow[key] = {
                            'from_module': func_module,
                            'to_module': called_module,
                            'data_functions': [],
                            'call_count': 0,
                        }
                    
                    module_data_flow[key]['data_functions'].append({
                        'caller': func_name,
                        'callee': called,
                    })
                    module_data_flow[key]['call_count'] += 1
        
        # Convert to list and sort by call count
        deps = sorted(module_data_flow.values(), key=lambda x: x['call_count'], reverse=True)
        
        # Limit data functions per dependency
        for dep in deps:
            dep['data_functions'] = dep['data_functions'][:10]
        
        return deps[:15]
    
    def _find_event_flows(self, result: AnalysisResult) -> list:
        """Find event-driven patterns and callback flows."""
        flows = []
        
        # Event/callback indicators
        event_indicators = ['event', 'emit', 'trigger', 'notify', 'callback', 'handler', 'listen', 'subscribe']
        hook_indicators = ['hook', 'on_', 'before_', 'after_', 'pre_', 'post_']
        
        for func_name, func in result.functions.items():
            name_lower = func.name.lower()
            
            is_event_related = (
                any(ind in name_lower for ind in event_indicators) or
                any(name_lower.startswith(ind) for ind in hook_indicators)
            )
            
            if is_event_related:
                # Find event handlers (functions called by this that might be callbacks)
                handlers = []
                for called in func.calls[:10]:
                    called_func = result.functions.get(called)
                    if called_func:
                        called_lower = called_func.name.lower()
                        if any(ind in called_lower for ind in event_indicators + ['handle', 'process']):
                            handlers.append(called)
                
                flows.append({
                    'event_source': func_name,
                    'type': 'emitter' if 'emit' in name_lower or 'trigger' in name_lower else 'handler',
                    'handlers': handlers[:5],
                    'description': func.docstring[:150] if func.docstring else 'N/A',
                })
                
                if len(flows) >= 20:
                    break
        
        return flows
    
    def export_data_structures(self, result: AnalysisResult, output_path: str, compact: bool = True) -> None:
        """Export data structure analysis focusing on data types, flows, and optimization opportunities.
        
        Analyzes:
        - Data types and their usage patterns
        - Data flow graphs (DFG) between functions
        - Process dependencies and data transformations
        - Optimization opportunities (type reduction, process consolidation)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 1. Analyze data types and structures
        data_types = self._analyze_data_types(result)
        
        # 2. Build data flow graph
        data_flow_graph = self._build_data_flow_graph(result)
        
        # 3. Identify process patterns
        process_patterns = self._identify_process_patterns(result)
        
        # 4. Calculate optimization opportunities
        optimization_analysis = self._analyze_optimization_opportunities(result, data_types, data_flow_graph)
        
        # Build comprehensive data structure report
        structure_data = {
            'project_path': result.project_path,
            'analysis_type': 'data_structures',
            'summary': {
                'unique_data_types': len(data_types),
                'data_flow_nodes': len(data_flow_graph.get('nodes', [])),
                'process_patterns': len(process_patterns),
                'optimization_potential': optimization_analysis.get('potential_score', 0),
            },
            'data_types': data_types,
            'data_flow_graph': data_flow_graph,
            'process_patterns': process_patterns,
            'optimization_analysis': optimization_analysis,
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(structure_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        print(f"✓ Data structures exported: {output_path}")
        print(f"  - Data types: {len(data_types)}")
        print(f"  - Flow nodes: {len(data_flow_graph.get('nodes', []))}")
        print(f"  - Process patterns: {len(process_patterns)}")
        print(f"  - Optimization score: {optimization_analysis.get('potential_score', 0):.1f}")
    
    def _analyze_data_types(self, result: AnalysisResult) -> list:
        """Analyze data types and their usage patterns."""
        data_types = {}
        
        # Common data type indicators in function names and docstrings
        type_indicators = {
            'list': ['list', 'array', 'items', 'elements', 'collection', 'sequence'],
            'dict': ['dict', 'map', 'mapping', 'key_value', 'record', 'object'],
            'str': ['string', 'text', 'content', 'message', 'input_text'],
            'int': ['int', 'integer', 'count', 'index', 'number', 'id'],
            'float': ['float', 'decimal', 'score', 'probability', 'rate'],
            'bool': ['bool', 'boolean', 'flag', 'is_', 'has_', 'can_'],
            'tuple': ['tuple', 'pair', 'coordinate', 'point'],
            'set': ['set', 'unique', 'collection_unique'],
        }
        
        for func_name, func in result.functions.items():
            # Analyze function name for type hints
            func_name_lower = func.name.lower()
            docstring = func.docstring.lower() if func.docstring else ''
            
            detected_types = []
            for type_name, indicators in type_indicators.items():
                if any(ind in func_name_lower or ind in docstring for ind in indicators):
                    detected_types.append(type_name)
            
            # Analyze parameter patterns (simplified)
            param_types = self._infer_parameter_types(func)
            
            # Analyze return patterns
            return_types = self._infer_return_types(func)
            
            if detected_types or param_types or return_types:
                type_key = f"{','.join(sorted(set(detected_types + param_types + return_types)))}"
                
                if type_key not in data_types:
                    data_types[type_key] = {
                        'type_name': type_key,
                        'detected_types': list(set(detected_types)),
                        'parameter_types': list(set(param_types)),
                        'return_types': list(set(return_types)),
                        'functions': [],
                        'usage_count': 0,
                        'cross_module_usage': 0,
                    }
                
                data_types[type_key]['functions'].append(func_name)
                data_types[type_key]['usage_count'] += 1
                
                # Check cross-module usage
                func_module = func_name.rsplit('.', 1)[0] if '.' in func_name else 'root'
                for called in func.calls[:10]:
                    called_module = called.rsplit('.', 1)[0] if '.' in called else 'root'
                    if func_module != called_module:
                        data_types[type_key]['cross_module_usage'] += 1
                        break
        
        return sorted(data_types.values(), key=lambda x: x['usage_count'], reverse=True)
    
    def _infer_parameter_types(self, func) -> list:
        """Infer parameter types from function name patterns."""
        param_types = []
        
        # Common parameter patterns
        if 'list' in func.name.lower() or 'items' in func.name.lower():
            param_types.append('list')
        if 'dict' in func.name.lower() or 'map' in func.name.lower():
            param_types.append('dict')
        if 'text' in func.name.lower() or 'string' in func.name.lower():
            param_types.append('str')
        if 'count' in func.name.lower() or 'index' in func.name.lower():
            param_types.append('int')
        
        return param_types
    
    def _infer_return_types(self, func) -> list:
        """Infer return types from function name patterns."""
        return_types = []
        
        # Common return patterns
        if func.name.startswith('get_') or func.name.startswith('find_'):
            return_types.append('dict')  # Usually returns records
        if func.name.startswith('is_') or func.name.startswith('has_'):
            return_types.append('bool')
        if func.name.startswith('count_') or func.name.startswith('len_'):
            return_types.append('int')
        if func.name.startswith('list_') or func.name.startswith('get_all_'):
            return_types.append('list')
        
        return return_types
    
    def _build_data_flow_graph(self, result: AnalysisResult) -> dict:
        """Build data flow graph showing how data moves between functions."""
        nodes = {}
        edges = []
        
        # Create nodes for functions
        for func_name, func in result.functions.items():
            # Determine data type for this function
            data_types = self._get_function_data_types(func)
            
            nodes[func_name] = {
                'id': func_name,
                'name': func.name.split('.')[-1],
                'module': func_name.rsplit('.', 1)[0] if '.' in func_name else 'root',
                'data_types': data_types,
                'in_degree': len(func.called_by),
                'out_degree': len(func.calls),
                'is_hub': len(func.calls) > 5 or len(func.called_by) > 5,
            }
        
        # Create edges for data flow
        for func_name, func in result.functions.items():
            for called in func.calls[:15]:  # Limit for performance
                if called in result.functions:
                    edges.append({
                        'from': func_name,
                        'to': called,
                        'data_flow': True,
                        'weight': 1,
                    })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'stats': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'hub_nodes': sum(1 for n in nodes.values() if n['is_hub']),
            }
        }
    
    def _get_function_data_types(self, func) -> list:
        """Get data types associated with a function."""
        types = []
        
        # Check function name
        name_lower = func.name.lower()
        if 'list' in name_lower or 'items' in name_lower:
            types.append('list')
        if 'dict' in name_lower or 'map' in name_lower:
            types.append('dict')
        if 'text' in name_lower or 'string' in name_lower:
            types.append('str')
        if 'count' in name_lower or 'index' in name_lower:
            types.append('int')
        
        # Check docstring
        if func.docstring:
            docstring_lower = func.docstring.lower()
            if 'list' in docstring_lower:
                types.append('list')
            if 'dict' in docstring_lower:
                types.append('dict')
            if 'string' in docstring_lower or 'text' in docstring_lower:
                types.append('str')
        
        return list(set(types))
    
    def _identify_process_patterns(self, result: AnalysisResult) -> list:
        """Identify common data processing patterns."""
        patterns = {
            'filter': [],
            'map': [],
            'reduce': [],
            'aggregate': [],
            'transform': [],
            'validate': [],
        }
        
        process_indicators = {
            'filter': ['filter', 'select', 'where', 'find', 'search'],
            'map': ['map', 'transform', 'convert', 'apply', 'process'],
            'reduce': ['reduce', 'sum', 'count', 'aggregate', 'fold'],
            'aggregate': ['group', 'bucket', 'cluster', 'partition'],
            'transform': ['transform', 'convert', 'normalize', 'standardize'],
            'validate': ['validate', 'check', 'verify', 'ensure', 'assert'],
        }
        
        for func_name, func in result.functions.items():
            name_lower = func.name.lower()
            docstring = func.docstring.lower() if func.docstring else ''
            
            for pattern_type, indicators in process_indicators.items():
                if any(ind in name_lower or ind in docstring for ind in indicators):
                    patterns[pattern_type].append({
                        'function': func_name,
                        'description': func.docstring[:100] if func.docstring else 'N/A',
                        'data_flow': f"{len(func.called_by)} → {func_name} → {len(func.calls)}",
                    })
                    break
        
        # Convert to list and sort by usage
        process_patterns = []
        for pattern_type, funcs in patterns.items():
            process_patterns.append({
                'pattern_type': pattern_type,
                'functions': funcs[:10],  # Limit per pattern
                'count': len(funcs),
            })
        
        return sorted(process_patterns, key=lambda x: x['count'], reverse=True)
    
    def _analyze_optimization_opportunities(self, result: AnalysisResult, data_types: list, data_flow_graph: dict) -> dict:
        """Analyze optimization opportunities for data types and processes."""
        optimization = {
            'potential_score': 0.0,
            'type_consolidation': [],
            'process_consolidation': [],
            'hub_optimization': [],
            'recommendations': [],
        }
        
        # 1. Type consolidation opportunities
        similar_types = {}
        for dt in data_types:
            type_signature = ','.join(sorted(dt['detected_types']))
            if type_signature not in similar_types:
                similar_types[type_signature] = []
            similar_types[type_signature].append(dt)
        
        for type_sig, similar in similar_types.items():
            if len(similar) > 1:
                total_usage = sum(s['usage_count'] for s in similar)
                if total_usage > 10:  # Significant usage
                    optimization['type_consolidation'].append({
                        'type_signature': type_sig,
                        'similar_types': [s['type_name'] for s in similar],
                        'total_usage': total_usage,
                        'potential_reduction': len(similar) - 1,
                    })
        
        # 2. Process consolidation
        process_patterns = self._identify_process_patterns(result)
        for pattern in process_patterns:
            if pattern['count'] > 5:  # Many similar processes
                optimization['process_consolidation'].append({
                    'pattern_type': pattern['pattern_type'],
                    'function_count': pattern['count'],
                    'potential_reduction': pattern['count'] // 3,  # Consolidate 1/3
                })
        
        # 3. Hub optimization (functions with many connections)
        hub_nodes = [n for n in data_flow_graph['nodes'].values() if n['is_hub']]
        for hub in hub_nodes[:10]:  # Top 10 hubs
            optimization['hub_optimization'].append({
                'function': hub['id'],
                'connections': hub['in_degree'] + hub['out_degree'],
                'optimization_type': 'split' if hub['out_degree'] > 10 else 'cache',
            })
        
        # 4. Calculate overall potential score
        type_score = len(optimization['type_consolidation']) * 10
        process_score = len(optimization['process_consolidation']) * 15
        hub_score = len(optimization['hub_optimization']) * 5
        optimization['potential_score'] = (type_score + process_score + hub_score) / 100.0
        
        # 5. Generate recommendations
        if optimization['type_consolidation']:
            optimization['recommendations'].append(
                f"Consolidate {len(optimization['type_consolidation'])} similar data types to reduce complexity"
            )
        if optimization['process_consolidation']:
            optimization['recommendations'].append(
                f"Merge {len(optimization['process_consolidation'])} process patterns to eliminate redundancy"
            )
        if optimization['hub_optimization']:
            optimization['recommendations'].append(
                f"Optimize {len(optimization['hub_optimization'])} hub functions for better performance"
            )
        
        return optimization


class MermaidExporter:
    """Export call graph to Mermaid format."""
    
    def export(self, result: AnalysisResult, output_path: str) -> None:
        """Export call graph as Mermaid flowchart."""
        self.export_call_graph(result, output_path)
    
    def export_call_graph(self, result: AnalysisResult, output_path: str) -> None:
        """Export simplified call graph."""
        lines = ["flowchart TD"]
        
        # Add nodes grouped by module
        modules: Dict[str, list] = {}
        for func_name in result.functions:
            parts = func_name.split('.')
            module = parts[0] if parts else 'unknown'
            if module not in modules:
                modules[module] = []
            modules[module].append(func_name)
        
        # Create subgraphs
        for module, funcs in sorted(modules.items()):
            safe_module = module.replace('-', '_').replace('.', '_')
            lines.append(f"    subgraph {safe_module}")
            for func_name in funcs[:50]:
                safe_id = self._safe_id(func_name)
                short_name = func_name.split('.')[-1][:30]
                lines.append(f'        {safe_id}["{short_name}"]')
            lines.append("    end")
        
        # Add edges
        edge_count = 0
        max_edges = 500
        for func_name, func in result.functions.items():
            source_id = self._safe_id(func_name)
            for called in func.calls[:10]:
                if called in result.functions:
                    target_id = self._safe_id(called)
                    lines.append(f"    {source_id} --> {target_id}")
                    edge_count += 1
                    if edge_count >= max_edges:
                        break
            if edge_count >= max_edges:
                break
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def export_compact(self, result: AnalysisResult, output_path: str) -> None:
        """Export compact flowchart - same as call graph for now."""
        self.export_call_graph(result, output_path)
    
    def _safe_id(self, name: str) -> str:
        """Create Mermaid-safe node ID."""
        safe = name.replace('.', '_').replace('-', '_').replace(':', '_')
        if len(safe) > 40:
            safe = safe[:20] + '_' + str(hash(name) % 10000)
        return safe


class LLMPromptExporter:
    """Export LLM-ready analysis summary with architecture and flows."""
    
    def export(self, result: AnalysisResult, output_path: str) -> None:
        """Generate comprehensive LLM prompt with architecture description."""
        lines = [
            "# System Architecture Analysis",
            "",
            f"## Overview",
            f"",
            f"- **Project**: {result.project_path}",
            f"- **Analysis Mode**: {result.analysis_mode}",
            f"- **Total Functions**: {len(result.functions)}",
            f"- **Total Classes**: {len(result.classes)}",
            f"- **Modules**: {len(result.modules)}",
            f"- **Entry Points**: {len(result.entry_points)}",
            f"",
        ]
        
        # Architecture - Group by module
        lines.extend([
            "## Architecture by Module",
            "",
        ])
        
        # Get top modules by function count
        module_stats = []
        for mod_name, mod in result.modules.items():
            func_count = len(mod.functions)
            class_count = len(mod.classes)
            if func_count > 0 or class_count > 0:
                module_stats.append((mod_name, func_count, class_count, mod.file))
        
        module_stats.sort(key=lambda x: x[1], reverse=True)
        
        for mod_name, func_count, class_count, file_path in module_stats[:20]:
            lines.append(f"### {mod_name}")
            lines.append(f"- **Functions**: {func_count}")
            if class_count > 0:
                lines.append(f"- **Classes**: {class_count}")
            if file_path:
                lines.append(f"- **File**: `{file_path.split('/')[-1]}`")
            lines.append("")
        
        # Key Entry Points - limit to most important
        lines.extend([
            "## Key Entry Points",
            "",
            "Main execution flows into the system:",
            "",
        ])
        
        # Filter and prioritize entry points
        important_entries = []
        for ep in result.entry_points:
            func = result.functions.get(ep)
            if func:
                # Score by number of calls (more calls = more important)
                score = len(func.calls) + len(func.called_by)
                important_entries.append((ep, score, func))
        
        important_entries.sort(key=lambda x: x[1], reverse=True)
        
        for ep, score, func in important_entries[:30]:
            lines.append(f"### {ep}")
            if func.docstring:
                lines.append(f"> {func.docstring[:150]}")
            if func.calls:
                lines.append(f"- **Calls**: {', '.join(func.calls[:8])}")
            lines.append("")
        
        # Process Flows - identify call chains
        lines.extend([
            "## Process Flows",
            "",
            "Key execution flows identified:",
            "",
        ])
        
        # Find call chains from entry points
        flow_id = 1
        seen_flows = set()  # Deduplicate flows
        seen_base_names = set()  # Track base function names
        
        for ep_name, _, ep_func in important_entries[:20]:  # More entries to find unique ones
            # Skip if we've seen this base name (handles class methods vs module functions)
            base_name = ep_name.split('.')[-1]
            module_name = ep_name.rsplit('.', 1)[0] if '.' in ep_name else ''
            
            # Prefer class methods over module functions (more specific)
            is_class_method = '.' in module_name and not module_name.endswith('__init__')
            
            if base_name in seen_base_names:
                # Already seen - skip unless this is a class method and we haven't recorded it
                continue
            
            seen_base_names.add(base_name)
            
            flow = self._trace_flow(ep_name, ep_func, result, depth=3)
            if flow and flow not in seen_flows:
                seen_flows.add(flow)
                lines.append(f"### Flow {flow_id}: {base_name}")
                lines.append(f"```")
                lines.append(flow)
                lines.append(f"```")
                lines.append("")
                flow_id += 1
                if flow_id > 10:  # Limit to 10 unique flows
                    break
        
        # Key Classes and Their Responsibilities
        if result.classes:
            lines.extend([
                "## Key Classes",
                "",
            ])
            
            # Sort classes by method count
            class_list = [(name, cls) for name, cls in result.classes.items()]
            class_list.sort(key=lambda x: len(x[1].methods), reverse=True)
            
            for cls_name, cls in class_list[:20]:
                lines.append(f"### {cls_name}")
                if cls.docstring:
                    lines.append(f"> {cls.docstring[:100]}")
                lines.append(f"- **Methods**: {len(cls.methods)}")
                if cls.methods:
                    method_list = ', '.join(cls.methods[:10])
                    lines.append(f"- **Key Methods**: {method_list}")
                if cls.bases:
                    lines.append(f"- **Inherits**: {', '.join(cls.bases)}")
                lines.append("")
        
        # Data Flow - functions that transform data
        lines.extend([
            "## Data Transformation Functions",
            "",
            "Key functions that process and transform data:",
            "",
        ])
        
        data_funcs = []
        for func_name, func in result.functions.items():
            # Look for data processing indicators
            data_indicators = ['parse', 'transform', 'convert', 'process', 'validate', 
                             'serialize', 'deserialize', 'encode', 'decode', 'format']
            if any(ind in func.name.lower() for ind in data_indicators):
                data_funcs.append((func_name, func))
        
        for func_name, func in data_funcs[:25]:
            lines.append(f"### {func_name}")
            if func.docstring:
                lines.append(f"> {func.docstring[:100]}")
            if func.calls:
                lines.append(f"- **Output to**: {', '.join(func.calls[:5])}")
            lines.append("")
        
        # Detected Patterns
        if result.patterns:
            lines.extend([
                "## Behavioral Patterns",
                "",
            ])
            
            for pattern in result.patterns[:15]:
                lines.append(f"### {pattern.name}")
                lines.append(f"- **Type**: {pattern.type}")
                lines.append(f"- **Confidence**: {pattern.confidence:.2f}")
                if pattern.functions:
                    lines.append(f"- **Functions**: {', '.join(pattern.functions[:5])}")
                lines.append("")
        
        # API Surface - public functions
        lines.extend([
            "## Public API Surface",
            "",
            "Functions exposed as public API (no underscore prefix):",
            "",
        ])
        
        public_funcs = [(name, f) for name, f in result.functions.items() 
                       if not f.name.startswith('_') and '.' in name]
        public_funcs.sort(key=lambda x: len(x[1].calls), reverse=True)
        
        for func_name, func in public_funcs[:40]:
            short_name = func_name.split('.')[-1]
            lines.append(f"- `{func_name}` - {len(func.calls)} calls")
        
        lines.append("")
        
        # System Interactions
        lines.extend([
            "## System Interactions",
            "",
            "How components interact:",
            "",
            "```mermaid",
            "graph TD",
        ])
        
        # Add key interactions to mermaid diagram
        added_edges = set()
        for ep_name, _, ep_func in important_entries[:15]:
            for called in ep_func.calls[:5]:
                edge = (ep_name.split('.')[-1][:20], called.split('.')[-1][:20])
                if edge not in added_edges and len(added_edges) < 30:
                    added_edges.add(edge)
                    lines.append(f"    {edge[0]} --> {edge[1]}")
        
        lines.extend([
            "```",
            "",
            "## Reverse Engineering Guidelines",
            "",
            "When working with this codebase:",
            "",
            "1. **Entry Points**: Start analysis from the entry points listed above",
            "2. **Core Logic**: Focus on classes with many methods (top of 'Key Classes' section)",
            "3. **Data Flow**: Follow data transformation functions for understanding data pipeline",
            "4. **Process Flows**: Use the flow diagrams to understand execution paths",
            "5. **API Surface**: Public API functions show intended external interface",
            "6. **Patterns**: Behavioral patterns indicate reusable design approaches",
            "",
            "## Context for LLM",
            "",
            "You are analyzing a Python codebase with the above architecture.",
            "- Respond with code changes that preserve existing call graph structure",
            "- Maintain the architectural patterns identified",
            "- Respect the public API surface",
            "- Consider the process flows when suggesting modifications",
        ])
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def _trace_flow(self, func_name: str, func, result: AnalysisResult, depth: int, visited: set = None) -> str:
        """Trace execution flow from a function with cycle detection."""
        if visited is None:
            visited = set()
        
        # Prevent cycles
        if func_name in visited or depth <= 0:
            return func_name.split('.')[-1]
        
        visited.add(func_name)
        
        short_name = func_name.split('.')[-1]
        module = func_name.rsplit('.', 1)[0] if '.' in func_name else 'root'
        
        lines = [f"{short_name} [{module}]"]
        
        # Group calls by module to show cross-module flows
        calls_by_module = {}
        for called in func.calls[:5]:  # Top 5 calls
            called_module = called.rsplit('.', 1)[0] if '.' in called else 'root'
            if called_module not in calls_by_module:
                calls_by_module[called_module] = []
            calls_by_module[called_module].append(called)
        
        # Show calls, prioritizing cross-module flows
        shown = 0
        for called_module, calls in sorted(calls_by_module.items(), 
                                           key=lambda x: x[0] != module):  # Cross-module first
            for called in calls[:2]:  # Max 2 per module
                if shown >= 3:
                    break
                    
                called_func = result.functions.get(called)
                if called_func and called not in visited:
                    sub_flow = self._trace_flow(called, called_func, result, depth - 1, visited.copy())
                    called_short = called.split('.')[-1]
                    cross_indicator = " →" if called_module != module else ""
                    lines.append(f"  └─{cross_indicator}> {called_short}")
                    
                    # Add indented sub-flow
                    sub_lines = sub_flow.split('\n')[1:]  # Skip first line (already shown)
                    for sub_line in sub_lines[:3]:  # Limit depth display
                        lines.append("    " + sub_line)
                    shown += 1
        
        return '\n'.join(lines)
    
    def _analyze_call_patterns(self, result: AnalysisResult) -> dict:
        """Analyze common call patterns in the codebase."""
        patterns = {
            'entry_to_api': [],
            'api_to_internal': [],
            'cross_module': [],
        }
        
        # Find entry points that call public API
        seen_functions = set()  # Deduplicate
        for ep_name in result.entry_points[:30]:
            # Skip duplicates (class methods vs module functions)
            base_name = ep_name.split('.')[-1]
            if base_name in seen_functions:
                continue
            seen_functions.add(base_name)
            ep_func = result.functions.get(ep_name)
            if not ep_func:
                continue
                
            for called in ep_func.calls:
                called_func = result.functions.get(called)
                if called_func:
                    # Check if called function is public API
                    if not called_func.name.startswith('_'):
                        patterns['entry_to_api'].append((ep_name, called))
                    # Check if cross-module
                    ep_module = ep_name.rsplit('.', 1)[0] if '.' in ep_name else ''
                    called_module = called.rsplit('.', 1)[0] if '.' in called else ''
                    if ep_module != called_module:
                        patterns['cross_module'].append((ep_name, called))
        
        return patterns
