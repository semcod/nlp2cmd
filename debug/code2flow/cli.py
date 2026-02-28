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
  code2flow llm-flow  # Generate LLM flow summary
        '''
    )
    
    # Add backward compatibility source argument first
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
        '--strategy',
        choices=['quick', 'standard', 'deep'],
        default='standard',
        help='Analysis strategy: quick (fast overview), standard (balanced), deep (complete)'
    )
    
    parser.add_argument(
        '--streaming',
        action='store_true',
        help='Use streaming analysis with progress reporting'
    )
    
    parser.add_argument(
        '--incremental',
        action='store_true',
        help='Only analyze changed files (requires previous run)'
    )
    
    parser.add_argument(
        '--max-memory',
        type=int,
        default=1000,
        help='Max memory in MB (default: 1000)'
    )
    
    parser.add_argument(
        '--split-output',
        action='store_true',
        help='Split YAML output into multiple files (summary, functions, classes, modules, entry_points)'
    )
    
    parser.add_argument(
        '--separate-orphans',
        action='store_true',
        help='Separate consolidated project from orphaned/isolated functions into different folders'
    )
    
    parser.add_argument(
        '--data-flow',
        action='store_true',
        help='Export data flow analysis (pipelines, state patterns, dependencies, events)'
    )
    
    parser.add_argument(
        '--data-structures',
        action='store_true',
        help='Export data structure analysis (types, flows, optimization opportunities)'
    )
    
    return parser


def main():
    """Main CLI entry point."""
    # Handle special cases first
    if len(sys.argv) > 1 and sys.argv[1] == 'llm-flow':
        from .llm_flow_generator import main as llm_flow_main
        return llm_flow_main(sys.argv[2:])
    
    if len(sys.argv) > 1 and sys.argv[1] == 'llm-context':
        # Quick LLM context generation
        return generate_llm_context(sys.argv[2:])
    
    # For all other cases, use the regular parser
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle analysis (default behavior)
    if not args.source:
        print("Error: missing required argument: source", file=sys.stderr)
        print("Usage: code2flow <source> [options]", file=sys.stderr)
        print("   or: code2flow llm-flow [options]", file=sys.stderr)
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
        if args.streaming or args.strategy in ['quick', 'deep']:
            # Use optimized streaming analyzer
            from .core.streaming_analyzer import (
                StreamingAnalyzer, STRATEGY_QUICK, 
                STRATEGY_STANDARD, STRATEGY_DEEP
            )
            
            strategy_map = {
                'quick': STRATEGY_QUICK,
                'standard': STRATEGY_STANDARD,
                'deep': STRATEGY_DEEP
            }
            strategy = strategy_map.get(args.strategy, STRATEGY_STANDARD)
            
            # Adjust strategy for memory limit
            strategy.max_files_in_memory = min(
                strategy.max_files_in_memory,
                args.max_memory // 10  # Rough heuristic
            )
            
            analyzer = StreamingAnalyzer(config, strategy)
            
            if args.verbose:
                def on_progress(update):
                    pct = update.get('percentage', 0)
                    print(f"\r[{pct:.0f}%] {update.get('message', '')}", end='', flush=True)
                analyzer.set_progress_callback(on_progress)
            
            # Collect results
            functions = {}
            classes = {}
            nodes = {}
            edges = []
            
            print(f"Analyzing with {args.strategy} strategy...")
            for update in analyzer.analyze_streaming(str(source_path)):
                if update['type'] == 'file_complete':
                    # Result is yielded but we need to re-analyze for full data
                    pass
                elif update['type'] == 'complete':
                    if args.verbose:
                        print()  # New line after progress
                    print(f"Completed in {update.get('elapsed_seconds', 0):.1f}s")
            
            # For streaming, we need to run again to get actual results
            # TODO: Modify streaming to accumulate results properly
            analyzer = ProjectAnalyzer(config)
            result = analyzer.analyze_project(str(source_path))
            
        else:
            # Use standard analyzer
            analyzer = ProjectAnalyzer(config)
            result = analyzer.analyze_project(str(source_path))
        
        if args.verbose:
            print(f"\nAnalysis complete:")
            print(f"  - Functions: {len(result.functions)}")
            print(f"  - Classes: {len(result.classes)}")
            print(f"  - CFG nodes: {len(result.nodes)}")
            print(f"  - CFG edges: {len(result.edges)}")
            
    except Exception as e:
        print(f"Error during analysis: {e}", file=sys.stderr)
        sys.exit(1)
        
    # Export results
    formats = [f.strip() for f in args.format.split(',')]
    
    try:
        if 'yaml' in formats:
            exporter = YAMLExporter()
            if args.separate_orphans:
                # Create separated output (consolidated vs orphans)
                sep_dir = output_dir / 'separated'
                exporter.export_separated(result, str(sep_dir), compact=True)
                if args.verbose:
                    print(f"  - YAML (separated): {sep_dir}/")
            elif args.split_output:
                # Create split output for large projects
                split_dir = output_dir / 'split'
                exporter.export_split(result, str(split_dir), include_defaults=args.full)
                if args.verbose:
                    print(f"  - YAML (split): {split_dir}/")
            else:
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
                
        if args.data_structures:
            exporter = YAMLExporter()
            struct_path = output_dir / 'data_structures.yaml'
            exporter.export_data_structures(result, str(struct_path), compact=True)
            if args.verbose:
                print(f"  - Data structures: {struct_path}")
                
        # Always generate LLM prompt
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


def generate_llm_context(args_list):
    """Quick command to generate LLM context only."""
    import argparse
    
    parser = argparse.ArgumentParser(
        prog='code2flow llm-context',
        description='Generate LLM-friendly context for a project'
    )
    parser.add_argument('source', help='Path to Python project')
    parser.add_argument('-o', '--output', default='./llm_context.md', help='Output file path')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args(args_list)
    
    from pathlib import Path
    from . import ProjectAnalyzer, FAST_CONFIG
    from .exporters.base import LLMPromptExporter
    
    source_path = Path(args.source)
    if not source_path.exists():
        print(f"Error: Source path not found: {source_path}", file=sys.stderr)
        return 1
    
    if args.verbose:
        print(f"Generating LLM context for: {source_path}")
    
    # Use fast config with parallel disabled for stability
    FAST_CONFIG.performance.parallel_enabled = False
    
    analyzer = ProjectAnalyzer(FAST_CONFIG)
    result = analyzer.analyze_project(str(source_path))
    
    exporter = LLMPromptExporter()
    exporter.export(result, args.output)
    
    # Print summary
    print(f"\n✓ LLM context generated: {args.output}")
    print(f"  Functions: {len(result.functions)}")
    print(f"  Classes: {len(result.classes)}")
    print(f"  Modules: {len(result.modules)}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
