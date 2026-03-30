#!/usr/bin/env python3
"""
Dynamic sources example: Shell script + Makefile.

This example demonstrates the intended flow:
1) app2schema: extract schema from local sources (.sh, Makefile)
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from app2schema import extract_appspec_to_file
from nlp2cmd.adapters import AppSpecAdapter
from nlp2cmd.core import NLP2CMD


def main() -> None:
    tmp_dir = Path(tempfile.mkdtemp(prefix="nlp2cmd_dynamic_sources_"))

    sh_path = tmp_dir / "demo.sh"
    sh_path.write_text(
        """#!/usr/bin/env bash
# Demo script
# Usage: demo.sh [--name NAME] [-v]

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)
      NAME="$2"; shift 2;;
    -v)
      VERBOSE=1; shift;;
    *)
      shift;;
  esac
done
""",
        encoding="utf-8",
    )

    mk_path = tmp_dir / "Makefile"
    mk_path.write_text(
        """# Demo Makefile
+.PHONY: test
+test:
+\techo running tests
+""",
        encoding="utf-8",
    )

    appspec_path = tmp_dir / "appspec.json"

    # app2schema: produce AppSpec (single file)
    # Note: current CLI implementation writes a single AppSpec; if you need a merged spec
    # across multiple sources, generate one spec per source and merge externally.
    extract_appspec_to_file(str(sh_path), appspec_path, source_type="shell_script")
    extract_appspec_to_file(str(mk_path), appspec_path, source_type="makefile", merge=True)

    adapter = AppSpecAdapter(appspec_path=appspec_path)
    nlp = NLP2CMD(adapter=adapter)

    print("\n=== Transform (ActionIR) ===")
    ir = nlp.transform_ir("run demo script with verbose")
    print(json.dumps(ir.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
