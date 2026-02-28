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
        for ep_name, _, ep_func in important_entries[:10]:
            flow = self._trace_flow(ep_name, ep_func, result, depth=3)
            if flow:
                lines.append(f"### Flow {flow_id}: {ep_name.split('.')[-1]}")
                lines.append(f"```")
                lines.append(flow)
                lines.append(f"```")
                lines.append("")
                flow_id += 1
        
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
    
    def _trace_flow(self, func_name: str, func, result: AnalysisResult, depth: int) -> str:
        """Trace execution flow from a function."""
        if depth <= 0 or not func.calls:
            return func_name.split('.')[-1]
        
        lines = [func_name.split('.')[-1]]
        for called in func.calls[:3]:
            called_func = result.functions.get(called)
            if called_func:
                sub_flow = self._trace_flow(called, called_func, result, depth - 1)
                for line in sub_flow.split('\n'):
                    lines.append("  → " + line)
        
        return '\n'.join(lines)
