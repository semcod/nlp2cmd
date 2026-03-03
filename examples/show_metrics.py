#!/usr/bin/env python3
"""
Show orchestration metrics and workspace status.

Displays:
- Task execution history (recent tasks, success rate, avg duration)
- Learned decision paths (cached for reuse)
- Generated function cache (JS/Python functions)
- Per-domain statistics

Usage:
    python3 show_metrics.py
    python3 show_metrics.py --recent 10
    python3 show_metrics.py --functions
    python3 show_metrics.py --paths
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nlp2cmd.orchestration.metrics import (
    MetricsCollector,
    PathOptimizer,
    FunctionCache,
    get_workspace,
)


def main():
    parser = argparse.ArgumentParser(description="NLP2CMD metrics dashboard")
    parser.add_argument("--recent", type=int, default=5,
                        help="Show N recent tasks (default: 5)")
    parser.add_argument("--functions", action="store_true",
                        help="Show cached generated functions")
    parser.add_argument("--paths", action="store_true",
                        help="Show learned decision paths")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    args = parser.parse_args()

    ws = get_workspace()
    mc = MetricsCollector(workspace=ws)
    po = PathOptimizer(workspace=ws)
    fc = FunctionCache(workspace=ws)

    summary = mc.get_summary()
    path_stats = po.get_stats()
    func_stats = fc.get_stats()

    if args.json:
        print(json.dumps({
            "workspace": str(ws),
            "summary": summary,
            "paths": path_stats,
            "functions": func_stats,
        }, indent=2))
        return

    print(f"{'═' * 60}")
    print(f"  NLP2CMD Orchestration Metrics")
    print(f"  Workspace: {ws}")
    print(f"{'═' * 60}")

    print(f"\n📊 Summary:")
    print(f"  Tasks:          {summary.get('total_tasks', 0)}")
    print(f"  Success rate:   {summary.get('success_rate', 0):.0%}")
    print(f"  Avg duration:   {summary.get('avg_duration_ms', 0):.0f}ms")
    print(f"  Total LLM calls: {summary.get('total_llm_calls', 0)}")
    print(f"  Total tokens:   {summary.get('total_tokens_in', 0) + summary.get('total_tokens_out', 0)}")
    print(f"  Total repairs:  {summary.get('total_repairs', 0)}")

    domains = summary.get("domains", {})
    if domains:
        print(f"\n📁 Per-domain:")
        for domain, ds in sorted(domains.items()):
            rate = ds.get("success", 0) / max(ds.get("tasks", 1), 1)
            print(f"  {domain:20s} {ds['tasks']:3d} tasks, {rate:.0%} success, {ds['avg_ms']:.0f}ms avg")

    print(f"\n🔗 Learned paths: {path_stats.get('total_paths', 0)}")
    print(f"  Total reuses:   {path_stats.get('total_successes', 0)}")

    print(f"\n📦 Cached functions: {func_stats.get('total_functions', 0)}")
    print(f"  Python: {func_stats.get('py_functions', 0)}")
    print(f"  JS:     {func_stats.get('js_functions', 0)}")
    print(f"  Usage:  {func_stats.get('total_usage', 0)}")

    # Recent tasks
    recent = mc.get_recent_tasks(args.recent)
    if recent:
        print(f"\n📋 Recent tasks ({len(recent)}):")
        for t in recent:
            status = "✓" if t.get("success") else "✗"
            dur = t.get("total_duration_ms", 0)
            steps = t.get("steps_total", 0)
            print(f"  {status} {t.get('goal', '?')[:50]:50s} {dur:>6.0f}ms {steps}steps")

    # Functions detail
    if args.functions:
        funcs = fc.lookup()
        if funcs:
            print(f"\n📦 Generated functions:")
            for f in funcs:
                print(f"  [{f.get('language', '?')}] {f.get('name', '?'):30s} "
                      f"used:{f.get('usage_count', 0)}x "
                      f"tags:{','.join(f.get('tags', []))}")

    # Paths detail
    if args.paths:
        po_data = po._load()
        if po_data:
            print(f"\n🔗 Learned paths:")
            for gh, p in po_data.items():
                actions = [s.get("action", "?") for s in (p.steps if hasattr(p, 'steps') else [])]
                print(f"  [{p.domain}] {p.goal_example[:40]:40s} "
                      f"used:{p.success_count}x "
                      f"steps:{' → '.join(actions[:5])}")


if __name__ == "__main__":
    main()
