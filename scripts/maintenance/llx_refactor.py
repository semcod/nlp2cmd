#!/usr/bin/env python3
"""Refactor the repository using LLX model selection and Aider.

This helper is designed for the pyqual pipeline. It uses LLX's project
metrics and model routing to pick an appropriate model, then hands the
refactor prompt to Aider via LLX's MCP Aider handler.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from llx.analysis.collector import ProjectMetrics, analyze_project
from llx.config import LlxConfig
from llx.mcp.tools import _handle_aider
from llx.routing.selector import select_model

DEFAULT_MODEL = os.getenv("LLX_REFACTOR_MODEL", "ollama/qwen2.5-coder:7b")
ALLOWED_ROOTS = ("src/", "scripts/", "tools/", "tests/")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Refactor tracked Python files using LLX + Aider.",
    )
    parser.add_argument(
        "workdir",
        nargs="?",
        default=".",
        help="Repository working directory (default: current directory)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Force a specific model instead of LLX routing",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="Override the default refactor prompt",
    )
    parser.add_argument(
        "--use-docker",
        dest="use_docker",
        action="store_true",
        help="Run Aider in Docker",
    )
    parser.add_argument(
        "--no-docker",
        dest="use_docker",
        action="store_false",
        help="Force local Aider execution",
    )
    parser.set_defaults(use_docker=None)
    return parser


def git_tracked_python_files(workdir: Path) -> list[str]:
    """Return tracked Python files from the git repository.

    We intentionally keep the file list limited to tracked sources so the
    refactor pass stays focused on the actual codebase and avoids virtualenvs
    or generated artifacts.
    """
    result = subprocess.run(
        ["git", "ls-files", "--", "*.py"],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    else:
        files = []

    if not files:
        files = []
        for root_name in ALLOWED_ROOTS:
            root = workdir / root_name.rstrip("/")
            if not root.exists():
                continue
            files.extend(
                str(path.relative_to(workdir))
                for path in root.rglob("*.py")
                if path.is_file()
            )
        files.extend(
            path.name
            for path in workdir.glob("*.py")
            if path.is_file()
        )

    selected = [
        path
        for path in files
        if path.endswith(".py") and (path.startswith(ALLOWED_ROOTS) or "/" not in path)
    ]
    return sorted(dict.fromkeys(selected))


def select_llx_model(workdir: Path) -> tuple[str, ProjectMetrics | None, str]:
    """Select a model using LLX's project metrics and routing logic."""
    fallback_reason = "LLX model selection failed; using fallback Ollama model"
    try:
        metrics = analyze_project(workdir)
        config = LlxConfig.load(workdir)
        selection = select_model(metrics, config, prefer_local=True, task_hint="refactor")
        model_id = selection.model_id
        reason = selection.explain()

        # LLX's Docker Aider integration expects an Ollama-compatible model.
        if not model_id.startswith("ollama/"):
            model_id = DEFAULT_MODEL
            reason += "\n  • Docker Aider fallback: forcing local Ollama model"

        return model_id, metrics, reason
    except Exception as exc:
        return DEFAULT_MODEL, None, f"{fallback_reason}: {exc}"


def build_prompt(workdir: Path, metrics: ProjectMetrics | None, file_count: int) -> str:
    """Build a refactor prompt for Aider."""
    lines = [
        f"Refactor the tracked Python code in {workdir.resolve()}.",
        "Use LLX's project analysis and your own code understanding to make",
        "high-value, low-risk refactors that improve maintainability.",
        "",
        "Goals:",
        "- reduce cyclomatic complexity and duplicated logic",
        "- split large functions/classes into smaller helpers when needed",
        "- keep public behavior stable and avoid unnecessary API churn",
        "- preserve tests and update them only when the behavior legitimately changes",
        "- keep changes incremental and easy to review",
        "- prefer readability and locality over broad rewrites",
        "",
    ]

    if metrics is not None:
        lines.extend(
            [
                "Project metrics:",
                f"- files: {metrics.total_files}",
                f"- lines: {metrics.total_lines:,}",
                f"- functions: {metrics.total_functions}",
                f"- classes: {metrics.total_classes}",
                f"- avg CC: {metrics.avg_cc:.1f}",
                f"- max CC: {metrics.max_cc}",
                f"- critical functions: {metrics.critical_count}",
                f"- dependency cycles: {metrics.dependency_cycles}",
                f"- hotspots: {metrics.hotspot_count}",
                "",
            ]
        )

    lines.extend(
        [
            f"Context files available: {file_count}",
            "Use the existing project analysis artifacts under ./project if helpful.",
            "Focus first on high-complexity modules and their tests.",
            "Only edit files that are needed to complete the refactor cleanly.",
        ]
    )
    return "\n".join(lines)


async def run_refactor(workdir: Path, model: str | None, prompt: str | None, use_docker: bool | None) -> int:
    files = git_tracked_python_files(workdir)
    if not files:
        print(f"[llx-refactor] No tracked Python files found under {workdir}", file=sys.stderr)
        return 1

    selected_model, metrics, selection_reason = select_llx_model(workdir)
    if model:
        selected_model = model
        selection_reason = f"Forced model override: {model}"

    if use_docker is None:
        use_docker = shutil.which("aider") is None

    # Keep the prompt focused on refactoring rather than a full rewrite.
    final_prompt = prompt or build_prompt(workdir, metrics, len(files))

    print("[llx-refactor] Model selection:")
    print(selection_reason)
    print(f"[llx-refactor] Selected model: {selected_model}")
    print(f"[llx-refactor] Files passed to Aider: {len(files)}")
    print(f"[llx-refactor] Execution mode: {'docker' if use_docker else 'local'}")

    if use_docker and not selected_model.startswith("ollama/"):
        # Keep Docker execution aligned with the LLX/Aider helper's Ollama
        # integration. This preserves a deterministic local path.
        selected_model = DEFAULT_MODEL

    result = await _handle_aider(
        {
            "prompt": final_prompt,
            "path": str(workdir),
            "model": selected_model,
            "files": files,
            "use_docker": use_docker,
            "docker_args": [],
        }
    )

    command = result.get("command")
    if command:
        print(f"[llx-refactor] Command: {command}")

    if result.get("success"):
        stdout = (result.get("stdout") or "").strip()
        stderr = (result.get("stderr") or "").strip()
        if stdout:
            print(stdout)
        if stderr:
            print(stderr, file=sys.stderr)
        return 0

    error = result.get("error") or "Unknown error"
    print(f"[llx-refactor] Failed: {error}", file=sys.stderr)
    stdout = (result.get("stdout") or "").strip()
    stderr = (result.get("stderr") or "").strip()
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    return 1


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    workdir = Path(args.workdir).resolve()
    if not workdir.exists():
        print(f"[llx-refactor] Workdir does not exist: {workdir}", file=sys.stderr)
        return 1

    return asyncio.run(
        run_refactor(
            workdir=workdir,
            model=args.model,
            prompt=args.prompt,
            use_docker=args.use_docker,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
