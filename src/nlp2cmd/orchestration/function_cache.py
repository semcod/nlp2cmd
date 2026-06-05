# FunctionCache - extracted from metrics.py
"""
Metrics collection and decision-path optimization for the Orchestration Engine.

Tracks per-task and per-step execution costs to enable:
1. Cost analysis (LLM tokens, latency, step count, success rate)
2. Decision path learning (store successful paths for reuse)
3. Generated function caching (JS/Python functions for browser/devops automation)

Persistent storage: ~/.nlp2cmd/ (or $NLP2CMD_CACHE_DIR)

Directory layout:
    ~/.nlp2cmd/
    ├── metrics/
    │   ├── tasks.jsonl           # append-only task execution log
    │   └── summary.json          # aggregated statistics
    ├── paths/
    │   └── learned_paths.json    # successful decision paths indexed by goal hash
    ├── generated/
    │   ├── js/                   # cached JS functions (browser automation)
    │   ├── py/                   # cached Python functions (devops/local)
    │   └── index.json            # function index with metadata
    └── config.json               # workspace configuration
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_WORKSPACE_ENV = "NLP2CMD_CACHE_DIR"
_DEFAULT_WORKSPACE = Path.home() / ".nlp2cmd"


def get_workspace() -> Path:
    """Return the .nlp2cmd workspace directory, creating it if needed."""
    ws = Path(os.environ.get(_WORKSPACE_ENV, str(_DEFAULT_WORKSPACE))).expanduser()
    ws.mkdir(parents=True, exist_ok=True)
    return ws


# =====================================================================
# Data classes
# =====================================================================
from nlp2cmd.orchestration.generated_function import GeneratedFunction
from nlp2cmd.orchestration.metrics_helpers import _func_id

class FunctionCache:
    """Caches auto-generated JS and Python functions in .nlp2cmd/generated/.

    When the orchestrator generates code (JS for browser automation, Python
    for devops), successful functions are saved for reuse. This avoids
    re-generating the same function via LLM on subsequent runs.
    """

    def __init__(self, workspace: Optional[Path] = None):
        self._ws = workspace or get_workspace()
        self._gen_dir = self._ws / "generated"
        self._js_dir = self._gen_dir / "js"
        self._py_dir = self._gen_dir / "py"
        self._index_file = self._gen_dir / "index.json"

        for d in (self._gen_dir, self._js_dir, self._py_dir):
            d.mkdir(parents=True, exist_ok=True)

        self._index: Optional[dict[str, dict]] = None

    def _load_index(self) -> dict[str, dict]:
        if self._index is not None:
            return self._index
        self._index = {}
        if self._index_file.exists():
            try:
                self._index = json.loads(self._index_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return self._index

    def _save_index(self) -> None:
        if self._index is None:
            return
        try:
            self._index_file.write_text(
                json.dumps(self._index, indent=2, ensure_ascii=False), encoding="utf-8",
            )
        except Exception as exc:
            logger.debug("Failed to save function index: %s", exc)

    def store(
        self,
        code: str,
        language: str,
        name: str = "",
        description: str = "",
        goal_hash: str = "",
        tags: Optional[list[str]] = None,
    ) -> str:
        """Store a generated function. Returns the func_id."""
        func_id = _func_id(code, language)
        idx = self._load_index()

        # Already cached?
        if func_id in idx:
            idx[func_id]["usage_count"] = idx[func_id].get("usage_count", 0) + 1
            idx[func_id]["last_used"] = datetime.now(timezone.utc).isoformat()
            self._save_index()
            return func_id

        # Determine filename
        ext = "js" if language == "js" else "py"
        safe_name = name or func_id[:16]
        safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in safe_name)
        filename = f"{safe_name}.{ext}"
        target_dir = self._js_dir if language == "js" else self._py_dir
        filepath = target_dir / filename

        # Write code file
        try:
            filepath.write_text(code, encoding="utf-8")
        except Exception as exc:
            logger.debug("Failed to write generated function: %s", exc)
            return func_id

        # Update index
        gf = GeneratedFunction(
            func_id=func_id,
            language=language,
            name=name or safe_name,
            code="",  # not stored in index — read from file
            description=description,
            goal_hash=goal_hash,
            usage_count=1,
            last_used=datetime.now(timezone.utc).isoformat(),
            tags=tags or [],
        )
        idx[func_id] = asdict(gf)
        idx[func_id]["filepath"] = str(filepath.relative_to(self._ws))
        self._save_index()
        return func_id

    def lookup(self, goal_hash: str = "", language: str = "",
               tags: Optional[list[str]] = None) -> list[dict]:
        """Find cached functions matching criteria."""
        idx = self._load_index()
        results = []
        for fid, meta in idx.items():
            if goal_hash and meta.get("goal_hash") != goal_hash:
                continue
            if language and meta.get("language") != language:
                continue
            if tags and not set(tags).issubset(set(meta.get("tags", []))):
                continue
            results.append({**meta, "func_id": fid})
        return results

    def get_code(self, func_id: str) -> Optional[str]:
        """Read the actual code of a cached function."""
        idx = self._load_index()
        meta = idx.get(func_id)
        if not meta:
            return None
        rel_path = meta.get("filepath", "")
        if not rel_path:
            return None
        full_path = self._ws / rel_path
        if full_path.exists():
            return full_path.read_text(encoding="utf-8")
        return None

    def get_stats(self) -> dict:
        idx = self._load_index()
        js_count = sum(1 for m in idx.values() if m.get("language") == "js")
        py_count = sum(1 for m in idx.values() if m.get("language") == "py")
        total_uses = sum(m.get("usage_count", 0) for m in idx.values())
        return {
            "total_functions": len(idx),
            "js_functions": js_count,
            "py_functions": py_count,
            "total_usage": total_uses,
        }
