"""Export analysis results to various formats."""

import json
import yaml
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import defaultdict
from ..core.models import AnalysisResult


class YAMLExporter:
    """Export analysis to YAML format."""
    
    def export(self, result: AnalysisResult, filepath: str, include_defaults: bool = False):
        """Export result to YAML file. Skip empty values by default."""
        data = result.to_dict(include_defaults)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, indent=2, 
                     allow_unicode=True, sort_keys=False)
                     
    def export_summary(self, result: AnalysisResult, filepath: str):
        """Export human-readable summary."""
        summary = self._generate_summary(result)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(summary, f, default_flow_style=False, indent=2,
                     allow_unicode=True)
                     
    def _generate_summary(self, result: AnalysisResult) -> Dict[str, Any]:
        """Generate summary statistics."""
        return {
            'overview': {
                'total_nodes': len(result.nodes),
                'total_functions': len(result.functions),
                'total_classes': len(result.classes),
                'cfg_edges': len(result.cfg_edges),
                'dfg_edges': len(result.dfg_edges),
                'call_edges': len(result.call_edges)
            },
            'functions': {
                name: {
                    'calls': list(info.calls),
                    'called_by': list(info.called_by),
                    'complexity': info.complexity
                }
                for name, info in result.functions.items()
            },
            'data_flows': {
                name: {
                    'dependencies': list(flow.dependencies)
                }
                for name, flow in result.data_flows.items()
            }
        }


class JSONExporter:
    """Export analysis to JSON format."""
    
    def export(self, result: AnalysisResult, filepath: str, include_defaults: bool = False):
        """Export result to JSON file. Skip empty values by default."""
        data = result.to_dict(include_defaults)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


class CompactMermaidExporter:
    """Export to compact Mermaid format with deduplication and subgraphs."""
    
    def export(self, result: AnalysisResult, filepath: str):
        """Export compact CFG with function subgraphs and pattern deduplication."""
        lines = ['flowchart TD']
        lines.append('    %% Auto-generated compact flow diagram')
        lines.append('    %% Deduplicated nodes, grouped by function')
        lines.append('')
        
        # Group nodes by function
        from collections import defaultdict
        function_nodes = defaultdict(list)
        global_nodes = []
        
        for node_id, node in result.nodes.items():
            if node.function:
                function_nodes[node.function].append((node_id, node))
            else:
                global_nodes.append((node_id, node))
        
        # Track unique node patterns for deduplication
        pattern_map = {}  # (type, label_pattern) -> first_node_id
        node_aliases = {}  # node_id -> alias_id (for deduplicated nodes)
        
        # Helper to get canonical pattern key
        def get_pattern_key(node):
            # Normalize label: remove specific values, keep structure
            label = node.label
            # Replace string literals with placeholder
            import re
            label_normalized = re.sub(r"['\"][^'\"]*['\"]", '"..."', label)
            # Replace numbers with placeholder
            label_normalized = re.sub(r'\b\d+\b', 'N', label_normalized)
            return (node.type, label_normalized[:30])
        
        # Build pattern map for deduplication
        for func_name, nodes in function_nodes.items():
            for node_id, node in nodes:
                pattern_key = get_pattern_key(node)
                if pattern_key in pattern_map:
                    # Reuse existing node
                    node_aliases[node_id] = pattern_map[pattern_key]
                else:
                    pattern_map[pattern_key] = node_id
                    node_aliases[node_id] = node_id
        
        # Generate subgraphs for functions
        subgraph_count = 0
        for func_name in sorted(function_nodes.keys()):
            nodes = function_nodes[func_name]
            if not nodes:
                continue
                
            # Sanitize function name for subgraph ID
            safe_func = self._safe_id(func_name)
            short_name = func_name.split('.')[-1][:25]
            
            lines.append(f'    subgraph {safe_func}["{short_name}"]')
            subgraph_count += 1
            
            # Add unique nodes in this function
            added_patterns = set()
            for node_id, node in nodes:
                alias_id = node_aliases.get(node_id, node_id)
                if alias_id != node_id:
                    continue  # Skip - will use alias
                    
                pattern_key = get_pattern_key(node)
                if pattern_key in added_patterns:
                    continue
                added_patterns.add(pattern_key)
                
                label = self._escape_label(node.label[:35])
                node_id_str = f'N{node_id}'
                
                # Shape based on type
                if node.type == 'FUNC':
                    lines.append(f'        {node_id_str}[["{label}"]]')
                elif node.type == 'CALL':
                    lines.append(f'        {node_id_str}(["{label}"])')
                elif node.type in ['IF', 'WHILE', 'FOR']:
                    lines.append(f'        {node_id_str}{{"{label}"}}')
                elif node.type == 'RETURN':
                    lines.append(f'        {node_id_str}[/"{label}"/]')
                else:
                    lines.append(f'        {node_id_str}["{label}"]')
            
            lines.append('    end')
            lines.append('')
        
        # Add global nodes
        if global_nodes:
            lines.append('    %% Global scope')
            for node_id, node in global_nodes:
                label = self._escape_label(node.label[:35])
                lines.append(f'    N{node_id}["{label}"]')
            lines.append('')
        
        # Generate edges (using aliases for deduplication)
        lines.append('    %% Control flow edges')
        edge_count = 0
        added_edges = set()  # Deduplicate edges
        
        for edge in result.cfg_edges:
            src_alias = node_aliases.get(edge.source, edge.source)
            tgt_alias = node_aliases.get(edge.target, edge.target)
            
            edge_key = (src_alias, tgt_alias, edge.condition)
            if edge_key in added_edges:
                continue
            added_edges.add(edge_key)
            
            src = f'N{src_alias}'
            tgt = f'N{tgt_alias}'
            
            if edge.condition:
                cond = self._escape_label(edge.condition[:15])
                lines.append(f'    {src} -->|"{cond}"| {tgt}')
            else:
                lines.append(f'    {src} --> {tgt}')
            edge_count += 1
        
        lines.append('')
        
        # Add external call edges (between functions)
        if result.call_edges:
            lines.append('    %% Inter-function calls')
            for edge in result.call_edges:
                if edge.metadata.get('caller') and edge.metadata.get('callee'):
                    caller = self._safe_id(edge.metadata['caller'])
                    callee = self._safe_id(edge.metadata['callee'])
                    lines.append(f'    {caller} -.->|call| {callee}')
            lines.append('')
        
        # Styling - apply by pattern type, not individual nodes
        lines.append('    %% Styling by pattern type')
        lines.append('    classDef func fill:#4CAF50,stroke:#2E7D32,color:#fff,stroke-width:2px')
        lines.append('    classDef call fill:#2196F3,stroke:#1565C0,color:#fff')
        lines.append('    classDef decision fill:#FF9800,stroke:#E65100,stroke-width:2px')
        lines.append('    classDef loop fill:#9C27B0,stroke:#6A1B9A,color:#fff')
        lines.append('    classDef return fill:#E91E63,stroke:#AD1457,color:#fff')
        lines.append('    classDef entry fill:#00BCD4,stroke:#00838F,color:#fff')
        lines.append('')
        
        # Apply styles to unique nodes
        style_map = defaultdict(list)
        for node_id, node in result.nodes.items():
            alias_id = node_aliases.get(node_id, node_id)
            if alias_id == node_id:  # Only style unique nodes
                node_type = node.type.lower()
                if node_type in ['func', 'call', 'if', 'for', 'while', 'return', 'entry']:
                    style_map[node_type].append(f'N{node_id}')
        
        for node_type, node_list in style_map.items():
            if node_list:
                # Batch style application for compactness
                nodes_str = ','.join(node_list[:10])  # Limit per line
                lines.append(f'    class {nodes_str} {node_type}')
        
        # Add metadata comment
        lines.append('')
        lines.append(f'    %% Summary: {len(pattern_map)} unique patterns, {edge_count} edges, {subgraph_count} functions')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
            
    def _escape_label(self, label: str) -> str:
        """Escape special characters for Mermaid."""
        return label.replace('"', '&quot;').replace('[', '(').replace(']', ')').replace('{', '(').replace('}', ')').replace('(', '(').replace(')', ')')
        
    def _safe_id(self, name: str) -> str:
        """Create safe Mermaid ID from name."""
        safe = name.replace('.', '_').replace('-', '_').replace(':', '_').replace(' ', '_')
        return f'F{hash(name) % 10000}_{safe[:20]}'


class MermaidExporter:
    """Export to standard Mermaid diagram format."""
    
    def export(self, result: AnalysisResult, filepath: str):
        """Export CFG as Mermaid flowchart."""
        lines = ['graph TD']
        
        # Add nodes
        for node_id, node in result.nodes.items():
            label = self._escape_label(node.label[:40])
            lines.append(f'    N{node_id}["{label}"]')
            
        # Add edges
        for edge in result.cfg_edges:
            if edge.condition:
                lines.append(f'    N{edge.source} -->|{self._escape_label(edge.condition[:20])}| N{edge.target}')
            else:
                lines.append(f'    N{edge.source} --> N{edge.target}')
                
        # Add styling classes
        lines.append('')
        lines.append('    classDef func fill:#4CAF50,stroke:#2E7D32,color:#fff')
        lines.append('    classDef call fill:#2196F3,stroke:#1565C0,color:#fff')
        lines.append('    classDef if fill:#FF9800,stroke:#E65100')
        lines.append('    classDef loop fill:#9C27B0,stroke:#6A1B9A,color:#fff')
        lines.append('    classDef return fill:#E91E63,stroke:#AD1457,color:#fff')
        
        # Apply classes
        for node_id, node in result.nodes.items():
            node_type = node.type.lower()
            if node_type in ['func', 'call', 'if', 'for', 'while', 'return']:
                lines.append(f'    class N{node_id} {node_type}')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
            
    def export_call_graph(self, result: AnalysisResult, filepath: str):
        """Export call graph as Mermaid diagram."""
        split_enabled = os.getenv('CODE2FLOW_CALLS_SPLIT', '0').strip() not in {'0', 'false', 'False', ''}
        keep_main = os.getenv('CODE2FLOW_CALLS_KEEP_MAIN', '0').strip() not in {'0', 'false', 'False', ''}
        try:
            min_nodes = int(os.getenv('CODE2FLOW_CALLS_MIN_NODES', '20'))
        except Exception:
            min_nodes = 20
        try:
            target_parts = int(os.getenv('CODE2FLOW_CALLS_TARGET_PARTS', '0'))
        except Exception:
            target_parts = 0
        try:
            max_nodes = int(os.getenv('CODE2FLOW_CALLS_MAX_NODES', '250'))
        except Exception:
            max_nodes = 250
        try:
            max_parts = int(os.getenv('CODE2FLOW_CALLS_MAX_PARTS', '20'))
        except Exception:
            max_parts = 20
        include_singletons = os.getenv('CODE2FLOW_CALLS_INCLUDE_SINGLETONS', '0').strip() not in {'0', 'false', 'False', ''}

        if not split_enabled:
            lines = self._render_call_graph_mermaid(result, funcs=set(result.functions.keys()))
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            return

        parts = self._partition_call_graph(
            result,
            min_nodes=min_nodes,
            max_nodes=max_nodes,
            max_parts=max_parts,
            target_parts=target_parts,
            include_singletons=include_singletons,
        )

        base = Path(filepath)
        out_dir = base.parent
        stem = base.stem

        if keep_main:
            lines = self._render_call_graph_mermaid(result, funcs=set(result.functions.keys()))
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

        for idx, funcs in enumerate(parts, 1):
            part_path = out_dir / f"{stem}_part_{idx:02d}.mmd"
            lines = self._render_call_graph_mermaid(result, funcs=funcs)
            with open(part_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

    def _render_call_graph_mermaid(self, result: AnalysisResult, funcs: set) -> List[str]:
        lines = ['graph LR']

        for func_name in sorted(funcs):
            short_name = func_name.split('.')[-1][:30]
            safe_id = self._safe_id(func_name)
            lines.append(f'    {safe_id}["{short_name}"]')

        for func_name in sorted(funcs):
            func_info = result.functions.get(func_name)
            if not func_info:
                continue
            caller_id = self._safe_id(func_name)
            for callee in sorted(func_info.calls):
                if callee in funcs:
                    callee_id = self._safe_id(callee)
                    lines.append(f'    {caller_id} --> {callee_id}')

        return lines

    def _partition_call_graph(
        self,
        result: AnalysisResult,
        *,
        min_nodes: int,
        max_nodes: int,
        max_parts: int,
        target_parts: int,
        include_singletons: bool,
    ) -> List[set]:
        import networkx as nx

        funcs = set(result.functions.keys())
        g = nx.Graph()
        g.add_nodes_from(funcs)

        for caller, info in result.functions.items():
            for callee in info.calls:
                if caller in funcs and callee in funcs:
                    g.add_edge(caller, callee)

        comps = [set(c) for c in nx.connected_components(g)]
        comps.sort(key=lambda s: len(s), reverse=True)

        parts: List[set] = []

        if target_parts and target_parts > 0:
            # Heuristic: aim for N parts by sizing max_nodes accordingly.
            # Respect explicit max_parts if it's smaller.
            effective_parts = min(max_parts, target_parts)
            if effective_parts > 0:
                # Ceiling division
                derived = (len(funcs) + effective_parts - 1) // effective_parts
                # Keep it within sane bounds
                max_nodes = max(min_nodes, min(max_nodes, max(30, derived)))

        def add_part(p: set) -> None:
            if len(parts) >= max_parts:
                return
            if len(p) == 1 and not include_singletons:
                return
            parts.append(p)

        # Pack small components together so we don't end up with only a single part
        # when the graph is highly disconnected.
        packed: set = set()
        def flush_packed(force: bool = False) -> None:
            nonlocal packed
            if not packed:
                return
            if force or len(packed) >= min_nodes or include_singletons:
                add_part(set(packed))
                packed = set()

        for comp in comps:
            if len(parts) >= max_parts:
                break

            if len(comp) <= max_nodes:
                # Pack small comps into larger bins
                if len(comp) < min_nodes and not include_singletons:
                    if len(packed) + len(comp) > max_nodes:
                        flush_packed(force=True)
                    packed |= comp
                    if len(packed) >= min_nodes:
                        flush_packed(force=True)
                else:
                    flush_packed(force=True)
                    add_part(comp)
                continue

            sub = g.subgraph(comp)
            remaining = set(sub.nodes())

            while remaining and len(parts) < max_parts:
                start = next(iter(remaining))
                chunk: set = set()
                q: List[str] = [start]
                seen_local: set = set()

                while q and len(chunk) < max_nodes:
                    cur = q.pop(0)
                    if cur in seen_local:
                        continue
                    seen_local.add(cur)
                    if cur not in remaining:
                        continue
                    chunk.add(cur)
                    for nxt in sub.neighbors(cur):
                        if nxt in remaining and nxt not in seen_local and len(chunk) < max_nodes:
                            q.append(nxt)

                if len(chunk) < min_nodes and len(remaining) > min_nodes:
                    for n in list(remaining):
                        if len(chunk) >= min_nodes:
                            break
                        if n not in chunk:
                            chunk.add(n)

                remaining -= chunk
                add_part(chunk)

        flush_packed(force=False)

        return parts
            
    def export_compact(self, result: AnalysisResult, filepath: str):
        """Export using compact format with deduplication."""
        exporter = CompactMermaidExporter()
        exporter.export(result, filepath)
            
    def _escape_label(self, label: str) -> str:
        """Escape special characters for Mermaid."""
        return label.replace('"', '&quot;').replace('[', '(').replace(']', ')')
        
    def _safe_id(self, name: str) -> str:
        """Create safe Mermaid ID from name."""
        # Replace invalid characters
        safe = name.replace('.', '_').replace('-', '_').replace(':', '_')
        return f'F{hash(name) % 100000}_{safe[:30]}'


class LLMPromptExporter:
    """Export analysis as LLM-ready prompt."""
    
    def export(self, result: AnalysisResult, filepath: str):
        """Generate comprehensive LLM prompt."""
        lines = [
            "# System Analysis Report",
            "",
            "## Overview",
            f"- Total functions: {len(result.functions)}",
            f"- Total classes: {len(result.classes)}",
            f"- Total nodes in CFG: {len(result.nodes)}",
            f"- Control flow edges: {len(result.cfg_edges)}",
            f"- Data flow edges: {len(result.dfg_edges)}",
            "",
            "## Function Call Graph",
            ""
        ]
        
        # Call graph
        for func_name, func_info in result.functions.items():
            if func_info.calls:
                lines.append(f"- **{func_name}** calls: {', '.join(sorted(func_info.calls))}")
            if func_info.called_by:
                lines.append(f"  - called by: {', '.join(sorted(func_info.called_by))}")
                
        lines.extend(["", "## Data Flows", ""])
        
        # Data flows
        for var_name, data_flow in result.data_flows.items():
            if data_flow.dependencies:
                lines.append(f"- `{var_name}` depends on: {', '.join(sorted(data_flow.dependencies))}")
                
        lines.extend(["", "## Classes", ""])
        
        # Classes
        for class_name, class_info in result.classes.items():
            methods = class_info.get('methods', [])
            lines.append(f"- **{class_name}** ({len(methods)} methods)")
            if class_info.get('bases'):
                lines.append(f"  - inherits from: {', '.join(class_info['bases'])}")
                
        lines.extend(["", "## Reverse Engineering Guidelines", "", 
                     "1. Preserve the call graph structure",
                     "2. Maintain data dependencies",
                     "3. Recreate class hierarchies",
                     "4. Implement control flow patterns", ""])
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
