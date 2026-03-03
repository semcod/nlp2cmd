#!/usr/bin/env python3
"""Generate chunked analysis for nlp2cmd project."""

import sys
sys.path.insert(0, '/home/tom/github/wronai/code2llm')

from pathlib import Path
from code2llm.core.large_repo import HierarchicalRepoSplitter, get_analysis_plan
from code2llm.core.analyzer import ProjectAnalyzer
from code2llm.core.config import Config
from code2llm.cli_exports import _export_simple_formats, _export_evolution, _export_code2logic

project_path = Path('/home/tom/github/wronai/nlp2cmd')
output_dir = Path('/home/tom/github/wronai/nlp2cmd/project')
output_dir.mkdir(parents=True, exist_ok=True)

# Get analysis plan
splitter = HierarchicalRepoSplitter(size_limit_kb=256)
plan = splitter.get_analysis_plan(project_path)

print(f"Analysis plan: {len(plan)} chunks")
for sp in plan:
    print(f"  - {sp.name}: {sp.file_count} files (~{sp.estimated_size_kb}KB)")

# Analyze each subproject
for i, subproject in enumerate(plan, 1):
    sp_output_dir = output_dir / subproject.name.replace('.', '_')
    sp_output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n[{i}/{len(plan)}] Analyzing: {subproject.name}")
    
    config = Config(
        mode='static',
        max_depth_enumeration=3,
        detect_state_machines=True,
        detect_recursion=True,
        output_dir=str(sp_output_dir),
        verbose=False
    )
    
    try:
        analyzer = ProjectAnalyzer(config)
        result = analyzer.analyze_project(str(subproject.path))
        
        # Export
        formats = ['toon', 'context']
        _export_simple_formats(type('Args', (), {'verbose': True})(), result, sp_output_dir, formats)
        _export_evolution(type('Args', (), {'verbose': True})(), result, sp_output_dir)
        
        print(f"  ✓ {subproject.name}: {len(result.functions)} functions, {len(result.classes)} classes")
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()

print(f"\n✓ Analysis complete. Output: {output_dir}")
