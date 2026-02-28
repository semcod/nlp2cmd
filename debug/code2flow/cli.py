#!/usr/bin/env python3
"""
code2flow - CLI for Python code flow analysis

Analyze control flow, data flow, and call graphs of Python codebases.
"""

import argparse
import sys
from pathlib import Path

from .core.config import Config, ANALYSIS_MODES
from .core.analyzer import ProjectAnalyzer
from .exporters.base import YAMLExporter, JSONExporter, MermaidExporter, LLMPromptExporter
from .visualizers.graph import GraphVisualizer


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog='code2flow',
        description='Analyze Python code control flow, data flow, and call graphs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  code2flow /path/to/project
  code2flow /path/to/project -m static -o ./analysis
  code2flow /path/to/project --format yaml,json,mermaid
        '''
    )
    
    parser.add_argument(
        'source',
        nargs='?',
        help='Path to Python source file or directory'
    )
    
    parser.add_argument(
        '-m', '--mode',
        choices=list(ANALYSIS_MODES.keys()),
        default='hybrid',
        help=f'Analysis mode (default: hybrid)'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='./code2flow_output',
        help='Output directory (default: ./code2flow_output)'
    )
    
    parser.add_argument(
        '-f', '--format',
        default='yaml,mermaid,png',
        help='Output formats: yaml,json,mermaid,png (comma-separated)'
    )
    
    parser.add_argument(
        '--full',
        action='store_true',
        help='Include all fields in output (including empty/null values)'
    )
    
    parser.add_argument(
        '--no-patterns',
        action='store_true',
        help='Disable pattern detection'
    )
    
    parser.add_argument(
        '--max-depth',
        type=int,
        default=10,
        help='Maximum analysis depth (default: 10)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--no-png',
        action='store_true',
        help='Skip automatic PNG generation from Mermaid files'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.1.0'
    )

    subparsers = parser.add_subparsers(dest='command')

    llm_flow = subparsers.add_parser(
        'llm-flow',
        help='Generate compact LLM-friendly flow summary from analysis.yaml'
    )
    llm_flow.add_argument(
        '-i', '--input',
        default='./output/analysis.yaml',
        help='Path to analysis.yaml (default: ./output/analysis.yaml)'
    )
    llm_flow.add_argument(
        '-o', '--output',
        default='./output/llm_flow.yaml',
        help='Output llm_flow.yaml path (default: ./output/llm_flow.yaml)'
    )
    llm_flow.add_argument(
        '--md',
        default=None,
        help='Optional output Markdown summary path (e.g. ./output/llm_flow.md)'
    )
    llm_flow.add_argument('--max-functions', type=int, default=40)
    llm_flow.add_argument('--limit-decisions', type=int, default=8)
    llm_flow.add_argument('--limit-calls', type=int, default=12)
    
    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command == 'llm-flow':
        from .llm_flow_generator import main as llm_flow_main

        argv = [
            '--input', args.input,
            '--output', args.output,
            '--max-functions', str(args.max_functions),
            '--limit-decisions', str(args.limit_decisions),
            '--limit-calls', str(args.limit_calls),
        ]
        if args.md:
            argv += ['--md', args.md]
        return llm_flow_main(argv)
    
    if not args.source:
        print("Error: missing required argument: source", file=sys.stderr)
        sys.exit(2)

    # Validate source path
    source_path = Path(args.source)
    if not source_path.exists():
        print(f"Error: Source path not found: {source_path}", file=sys.stderr)
        sys.exit(1)
        
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure analysis
    config = Config(
        mode=args.mode,
        max_depth_enumeration=args.max_depth,
        detect_state_machines=not args.no_patterns,
        detect_recursion=not args.no_patterns,
        output_dir=str(output_dir)
    )
    
    if args.verbose:
        print(f"Analyzing: {source_path}")
        print(f"Mode: {args.mode}")
        print(f"Output: {output_dir}")
        
    # Run analysis
    try:
        analyzer = ProjectAnalyzer(config)
        result = analyzer.analyze_project(str(source_path))
        
        if args.verbose:
            print(f"\nAnalysis complete:")
            print(f"  - Functions: {len(result.functions)}")
            print(f"  - Classes: {len(result.classes)}")
            print(f"  - CFG nodes: {len(result.nodes)}")
            print(f"  - CFG edges: {len(result.cfg_edges)}")
            
    except Exception as e:
        print(f"Error during analysis: {e}", file=sys.stderr)
        sys.exit(1)
        
    # Export results
    formats = [f.strip() for f in args.format.split(',')]
    
    try:
        if 'yaml' in formats:
            exporter = YAMLExporter()
            filepath = output_dir / 'analysis.yaml'
            exporter.export(result, str(filepath), include_defaults=args.full)
            if args.verbose:
                print(f"  - YAML: {filepath}")
                
        if 'json' in formats:
            exporter = JSONExporter()
            filepath = output_dir / 'analysis.json'
            exporter.export(result, str(filepath), include_defaults=args.full)
            if args.verbose:
                print(f"  - JSON: {filepath}")
                
        if 'mermaid' in formats:
            exporter = MermaidExporter()
            filepath = output_dir / 'flow.mmd'
            exporter.export(result, str(filepath))
            filepath = output_dir / 'calls.mmd'
            exporter.export_call_graph(result, str(filepath))
            filepath = output_dir / 'compact_flow.mmd'
            exporter.export_compact(result, str(filepath))
            if args.verbose:
                print(f"  - Mermaid: {output_dir / '*.mmd'}")
                
            # Auto-generate PNG from Mermaid files (unless disabled)
            if not args.no_png:
                try:
                    from .mermaid_generator import generate_pngs
                    png_count = generate_pngs(output_dir, output_dir)
                    if args.verbose and png_count > 0:
                        print(f"  - PNG: {png_count} files generated")
                except ImportError:
                    # Fallback to external script
                    try:
                        import subprocess
                        script_path = Path(__file__).parent.parent / 'mermaid_to_png.py'
                        if script_path.exists():
                            result = subprocess.run([
                                'python', str(script_path), 
                                '--batch', str(output_dir), str(output_dir)
                            ], capture_output=True, text=True, timeout=60)
                            if result.returncode == 0 and args.verbose:
                                print(f"  - PNG: {output_dir / '*.png'}")
                    except Exception as png_error:
                        if args.verbose:
                            print(f"  - PNG: Skipped (install with: make install-mermaid)")
            elif args.verbose:
                print(f"  - PNG: Skipped (--no-png)")
                
        if 'png' in formats:
            visualizer = GraphVisualizer(result)
            filepath = output_dir / 'cfg.png'
            visualizer.visualize_cfg(str(filepath))
            filepath = output_dir / 'call_graph.png'
            visualizer.visualize_call_graph(str(filepath))
            if args.verbose:
                print(f"  - PNG: {output_dir / '*.png'}")
                
        # Always generate LLM prompt
        exporter = LLMPromptExporter()
        filepath = output_dir / 'llm_prompt.md'
        exporter.export(result, str(filepath))
        if args.verbose:
            print(f"  - LLM prompt: {filepath}")
            
    except Exception as e:
        print(f"Error during export: {e}", file=sys.stderr)
        sys.exit(1)
        
    if args.verbose:
        print(f"\nAll outputs saved to: {output_dir}")
        
    return 0


if __name__ == '__main__':
    sys.exit(main())
