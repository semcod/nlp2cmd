#!/usr/bin/env python3
"""
Demo script showcasing the enhanced dynamic NLP2CMD implementation.

This script demonstrates:
- Dynamic schema extraction from multiple sources
- Shell-gpt integration for intelligent command generation
- Enhanced NLP processing without hardcoded keywords
"""

import sys
import json
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from nlp2cmd.pipeline_runner import PipelineRunner, ShellExecutionPolicy
from nlp2cmd.enhanced import EnhancedNLP2CMD
from app2schema import extract_appspec_to_file


def main():
    """Run the enhanced NLP2CMD demo."""
    print("🚀 Enhanced NLP2CMD Demo")
    print("=" * 50)

    tmp_dir = Path(tempfile.mkdtemp(prefix="nlp2cmd_demo_"))
    appspec_path = tmp_dir / "appspec.json"

    print("\n🧩 Step 1: app2schema → generate schemas")
    print("-" * 40)

    # Generate AppSpec actions for system commands (static via help output)
    extract_appspec_to_file("git", appspec_path, source_type="shell", merge=True)
    extract_appspec_to_file("df", appspec_path, source_type="shell", merge=True)
    extract_appspec_to_file("du", appspec_path, source_type="shell", merge=True)

    # Generate a simple web schema from static HTML (no Playwright required)
    html = """
    <html>
      <body>
        <button id=\"login-button\">Login</button>
        <input id=\"username\" placeholder=\"Username\" />
        <input id=\"password\" placeholder=\"Password\" type=\"password\" />
      </body>
    </html>
    """.strip()

    html_path = tmp_dir / "page.html"
    html_path.write_text(html, encoding="utf-8")
    extract_appspec_to_file(str(html_path), appspec_path, source_type="web", merge=True)

    print(f"✅ Wrote appspec: {appspec_path}")

    print("\n🧠 Step 2: NLP2CMD → load AppSpec")
    print("-" * 40)

    nlp2cmd = EnhancedNLP2CMD(appspec_path=str(appspec_path))
    print(f"✅ Loaded {len(nlp2cmd.get_available_commands())} actions")

    # Demo queries
    demo_queries = [
        "show git status",
        "show disk usage",
        "check disk usage for current directory",
        "click login",
        "type \"admin\" into username",
    ]

    print("\n🔍 Processing Natural Language Queries:")
    print("-" * 40)

    execute_shell = "--execute-shell" in sys.argv
    execute_web = "--execute-web" in sys.argv

    runner = PipelineRunner(
        shell_policy=ShellExecutionPolicy(
            allowlist={"git", "df", "du"},
        ),
        headless=True,
    )

    for i, query in enumerate(demo_queries, 1):
        print(f"\n{i}. Query: \"{query}\"")

        try:
            ir = nlp2cmd.transform_ir(query)
            print(f"   🎯 Action: {ir.action_id}")
            print(f"   ⚡ DSL: {ir.dsl}")
            print(f"   💡 Explanation: {ir.explanation}")

            dry_run = True
            if ir.dsl_kind == "shell" and execute_shell:
                dry_run = False
            if ir.dsl_kind == "dom" and execute_web:
                dry_run = False

            if not dry_run:
                result = runner.run(ir, dry_run=False, confirm=True)
                if result.success:
                    print(f"   ✅ Executed ({result.kind}) in {result.duration_ms:.1f}ms")
                    if result.data:
                        stdout = result.data.get("stdout")
                        if isinstance(stdout, str) and stdout.strip():
                            print(stdout.strip())
                else:
                    print(f"   ❌ Execution failed ({result.kind}): {result.error}")

        except Exception as e:
            print(f"   ⚠️  Error: {e}")

    print("\n📤 AppSpec: ")
    print(str(appspec_path))

    print("\n🎉 Demo completed!")
    print("\nKey improvements:")
    print("• ✅ app2schema generates validated schema exports (static + web)")
    print("• ✅ NLP2CMD can import schema exports instead of hardcoded keywords")
    print("• ✅ Supports system commands (git/df/du) and GUI actions (web DOM → DQL)")
    print("• ✅ Hybrid NLP backends still supported")


if __name__ == "__main__":
    main()
