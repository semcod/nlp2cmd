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

@dataclass
class StepMetric:
    """Metrics for a single orchestration step."""
    action: str
    status: str  # "success", "failed", "skipped", "repaired"
    duration_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    llm_model: str = ""
    error: Optional[str] = None


@dataclass
class TaskMetric:
    """Metrics for a complete orchestrated task."""
    task_id: str
    goal: str
    goal_hash: str  # for path lookup
    domain: str = "general"
    success: bool = False
    total_duration_ms: float = 0.0
    steps_total: int = 0
    steps_succeeded: int = 0
    steps_failed: int = 0
    steps_repaired: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    llm_calls: int = 0
    plan_source: str = ""  # "llm", "heuristic", "cached_path"
    reflection_verdict: str = ""
    step_metrics: list[dict] = field(default_factory=list)
    generated_functions: list[str] = field(default_factory=list)
    timestamp: str = ""
    decision_path: list[str] = field(default_factory=list)  # action sequence

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.goal_hash:
            self.goal_hash = _hash_goal(self.goal)


@dataclass
class LearnedPath:
    """A successful decision path that can be reused for similar goals."""
    goal_hash: str
    goal_example: str
    domain: str
    steps: list[dict]  # [{action, params_template, description}]
    success_count: int = 0
    avg_duration_ms: float = 0.0
    avg_tokens: int = 0
    last_used: str = ""
    generated_functions: list[str] = field(default_factory=list)


@dataclass
class GeneratedFunction:
    """A generated JS or Python function cached for reuse."""
    func_id: str
    language: str  # "js" or "py"
    name: str
    code: str
    description: str = ""
    goal_hash: str = ""
    usage_count: int = 0
    last_used: str = ""
    created: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.created:
            self.created = datetime.now(timezone.utc).isoformat()


# =====================================================================
# MetricsCollector
# =====================================================================

class MetricsCollector:
    """Collects and persists orchestration metrics.

    Usage:
        mc = MetricsCollector()
        mc.start_task("fibonacci in python", domain="code_editor")
        mc.record_step("generate_code", "success", duration_ms=1200, tokens_out=500)
        mc.record_step("inject_code", "success", duration_ms=50)
        mc.finish_task(success=True, reflection_verdict="valid")
        summary = mc.get_summary()
    """

    def __init__(self, workspace: Optional[Path] = None):
        self._ws = workspace or get_workspace()
        self._metrics_dir = self._ws / "metrics"
        self._metrics_dir.mkdir(parents=True, exist_ok=True)
        self._tasks_file = self._metrics_dir / "tasks.jsonl"
        self._summary_file = self._metrics_dir / "summary.json"

        # Current task being tracked
        self._current: Optional[TaskMetric] = None
        self._task_start: float = 0.0
        self._step_start: float = 0.0

    def start_task(self, goal: str, domain: str = "general",
                   task_id: Optional[str] = None) -> str:
        """Begin tracking a new task."""
        tid = task_id or f"task_{int(time.time() * 1000)}"
        self._current = TaskMetric(
            task_id=tid,
            goal=goal,
            goal_hash=_hash_goal(goal),
            domain=domain,
        )
        self._task_start = time.time()
        return tid

    def record_step(
        self,
        action: str,
        status: str,
        duration_ms: float = 0.0,
        tokens_in: int = 0,
        tokens_out: int = 0,
        llm_model: str = "",
        error: Optional[str] = None,
    ) -> None:
        """Record metrics for one step."""
        if not self._current:
            return

        sm = StepMetric(
            action=action,
            status=status,
            duration_ms=duration_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            llm_model=llm_model,
            error=error,
        )
        self._current.step_metrics.append(asdict(sm))
        self._current.decision_path.append(action)
        self._current.llm_calls += (1 if tokens_out > 0 else 0)
        self._current.total_tokens_in += tokens_in
        self._current.total_tokens_out += tokens_out

        if status == "success":
            self._current.steps_succeeded += 1
        elif status == "failed":
            self._current.steps_failed += 1
        elif status == "repaired":
            self._current.steps_repaired += 1
        self._current.steps_total += 1

    def record_generated_function(self, func_id: str) -> None:
        """Record that a function was generated during this task."""
        if self._current:
            self._current.generated_functions.append(func_id)

    def finish_task(
        self,
        success: bool,
        reflection_verdict: str = "",
        plan_source: str = "",
    ) -> TaskMetric:
        """Finish tracking and persist the task metrics."""
        if not self._current:
            raise RuntimeError("No task in progress")

        self._current.success = success
        self._current.total_duration_ms = (time.time() - self._task_start) * 1000
        self._current.reflection_verdict = reflection_verdict
        self._current.plan_source = plan_source

        # Append to JSONL log
        try:
            with open(self._tasks_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(self._current), ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.debug("Failed to write task metric: %s", exc)

        # Update summary
        self._update_summary(self._current)

        result = self._current
        self._current = None
        return result

    def get_summary(self) -> dict:
        """Load aggregated summary statistics."""
        if self._summary_file.exists():
            try:
                return json.loads(self._summary_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return self._empty_summary()

    def get_recent_tasks(self, n: int = 20) -> list[dict]:
        """Load last N task metrics from the JSONL log."""
        if not self._tasks_file.exists():
            return []
        tasks = []
        try:
            for line in self._tasks_file.read_text(encoding="utf-8").strip().split("\n"):
                if line.strip():
                    tasks.append(json.loads(line))
        except Exception:
            pass
        return tasks[-n:]

    # ── Private ──────────────────────────────────────────────────────

    def _update_summary(self, task: TaskMetric) -> None:
        summary = self.get_summary()
        summary["total_tasks"] += 1
        if task.success:
            summary["successful_tasks"] += 1
        else:
            summary["failed_tasks"] += 1
        summary["total_tokens_in"] += task.total_tokens_in
        summary["total_tokens_out"] += task.total_tokens_out
        summary["total_llm_calls"] += task.llm_calls
        summary["total_duration_ms"] += task.total_duration_ms
        summary["total_steps"] += task.steps_total
        summary["total_repairs"] += task.steps_repaired

        # Running averages
        n = summary["total_tasks"]
        summary["avg_duration_ms"] = summary["total_duration_ms"] / n
        summary["avg_tokens_per_task"] = (
            (summary["total_tokens_in"] + summary["total_tokens_out"]) / n
        )
        summary["success_rate"] = summary["successful_tasks"] / n

        # Per-domain stats
        domain = task.domain
        ds = summary.setdefault("domains", {}).setdefault(domain, {
            "tasks": 0, "success": 0, "avg_ms": 0.0, "total_ms": 0.0,
        })
        ds["tasks"] += 1
        if task.success:
            ds["success"] += 1
        ds["total_ms"] += task.total_duration_ms
        ds["avg_ms"] = ds["total_ms"] / ds["tasks"]

        summary["last_updated"] = datetime.now(timezone.utc).isoformat()

        try:
            self._summary_file.write_text(
                json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8",
            )
        except Exception as exc:
            logger.debug("Failed to write summary: %s", exc)

    @staticmethod
    def _empty_summary() -> dict:
        return {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_llm_calls": 0,
            "total_duration_ms": 0.0,
            "total_steps": 0,
            "total_repairs": 0,
            "avg_duration_ms": 0.0,
            "avg_tokens_per_task": 0.0,
            "success_rate": 0.0,
            "domains": {},
            "last_updated": "",
        }


# =====================================================================
# PathOptimizer — learn and reuse successful decision paths
# =====================================================================

class PathOptimizer:
    """Stores successful decision paths for reuse on similar goals.

    When a task succeeds, its step sequence (decision path) is stored
    indexed by goal_hash. Next time a similar goal is requested, the
    cached path can be used instead of LLM planning — saving tokens and latency.
    """

    def __init__(self, workspace: Optional[Path] = None):
        self._ws = workspace or get_workspace()
        self._paths_dir = self._ws / "paths"
        self._paths_dir.mkdir(parents=True, exist_ok=True)
        self._paths_file = self._paths_dir / "learned_paths.json"
        self._cache: Optional[dict[str, LearnedPath]] = None

    def _load(self) -> dict[str, LearnedPath]:
        if self._cache is not None:
            return self._cache
        self._cache = {}
        if self._paths_file.exists():
            try:
                data = json.loads(self._paths_file.read_text(encoding="utf-8"))
                for k, v in data.items():
                    self._cache[k] = LearnedPath(**v)
            except Exception as exc:
                logger.debug("Failed to load learned paths: %s", exc)
        return self._cache

    def _save(self) -> None:
        if self._cache is None:
            return
        try:
            data = {k: asdict(v) for k, v in self._cache.items()}
            self._paths_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8",
            )
        except Exception as exc:
            logger.debug("Failed to save learned paths: %s", exc)

    def lookup(self, goal: str) -> Optional[LearnedPath]:
        """Find a cached path for a similar goal."""
        paths = self._load()
        gh = _hash_goal(goal)
        return paths.get(gh)

    def record_success(self, task: TaskMetric) -> None:
        """Store a successful task's decision path for future reuse."""
        if not task.success or not task.decision_path:
            return

        paths = self._load()
        gh = task.goal_hash

        if gh in paths:
            p = paths[gh]
            p.success_count += 1
            n = p.success_count
            p.avg_duration_ms = (p.avg_duration_ms * (n - 1) + task.total_duration_ms) / n
            p.avg_tokens = int((p.avg_tokens * (n - 1) + task.total_tokens_in + task.total_tokens_out) / n)
            p.last_used = datetime.now(timezone.utc).isoformat()
            if task.generated_functions:
                for fn in task.generated_functions:
                    if fn not in p.generated_functions:
                        p.generated_functions.append(fn)
        else:
            paths[gh] = LearnedPath(
                goal_hash=gh,
                goal_example=task.goal[:200],
                domain=task.domain,
                steps=[sm for sm in task.step_metrics if sm.get("status") == "success"],
                success_count=1,
                avg_duration_ms=task.total_duration_ms,
                avg_tokens=task.total_tokens_in + task.total_tokens_out,
                last_used=datetime.now(timezone.utc).isoformat(),
                generated_functions=list(task.generated_functions),
            )

        self._save()

    def get_stats(self) -> dict:
        """Return statistics about learned paths."""
        paths = self._load()
        return {
            "total_paths": len(paths),
            "total_successes": sum(p.success_count for p in paths.values()),
            "domains": list({p.domain for p in paths.values()}),
        }


# =====================================================================
# FunctionCache — store generated JS/Python functions for reuse
# =====================================================================

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


# =====================================================================
# Helpers
# =====================================================================

def _hash_goal(goal: str) -> str:
    """Normalize and hash a goal string for path lookup."""
    normalized = goal.lower().strip()
    # Remove articles, prepositions, etc. for fuzzy matching
    for w in ("a ", "an ", "the ", "please ", "napisz ", "stwórz ", "zrób "):
        normalized = normalized.replace(w, "")
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def _func_id(code: str, language: str) -> str:
    """Generate a stable ID for a code function."""
    return hashlib.sha256(f"{language}:{code}".encode()).hexdigest()[:16]
