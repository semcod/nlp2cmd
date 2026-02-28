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
    """Export LLM-ready analysis summary."""
    
    def export(self, result: AnalysisResult, output_path: str) -> None:
        """Generate LLM prompt with analysis summary."""
        lines = [
            "# System Behavioral Analysis",
            "",
            f"## Overview",
            f"",
            f"- **Project**: {result.project_path}",
            f"- **Analysis Mode**: {result.analysis_mode}",
            f"- **Functions**: {len(result.functions)}",
            f"- **Classes**: {len(result.classes)}",
            f"- **Patterns**: {len(result.patterns)}",
            "",
            "## Entry Points",
            "",
        ]
        
        for ep in result.entry_points[:20]:
            lines.append(f"- `{ep}`")
        
        if len(result.entry_points) > 20:
            lines.append(f"- ... and {len(result.entry_points) - 20} more")
        
        lines.extend([
            "",
            "## Detected Patterns",
            "",
        ])
        
        for pattern in result.patterns[:10]:
            lines.append(f"### {pattern.name}")
            lines.append(f"- **Type**: {pattern.type}")
            lines.append(f"- **Confidence**: {pattern.confidence:.2f}")
            if pattern.functions:
                lines.append(f"- **Functions**: {', '.join(pattern.functions[:5])}")
            lines.append("")
        
        lines.extend([
            "## Key Functions",
            "",
        ])
        
        for func_name in list(result.functions.keys())[:20]:
            func = result.functions[func_name]
            lines.append(f"### {func_name}")
            if func.docstring:
                lines.append(f"> {func.docstring[:100]}")
            if func.calls:
                lines.append(f"- Calls: {', '.join(func.calls[:5])}")
            lines.append("")
        
        lines.extend([
            "## Reverse Engineering Guidelines",
            "",
            "1. Preserve call graph structure",
            "2. Maintain identified behavioral patterns",
            "3. Keep data flow dependencies",
            "4. Preserve state machine transitions",
            "5. Maintain control flow logic",
        ])
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
