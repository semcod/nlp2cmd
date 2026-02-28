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
