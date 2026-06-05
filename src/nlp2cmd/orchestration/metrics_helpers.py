"""Shared helpers for orchestration metrics (avoids circular imports)."""

from __future__ import annotations

import hashlib


def _hash_goal(goal: str) -> str:
    """Normalize and hash a goal string for path lookup."""
    normalized = goal.lower().strip()
    for w in ("a ", "an ", "the ", "please ", "napisz ", "stwórz ", "zrób "):
        normalized = normalized.replace(w, "")
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def _func_id(code: str, language: str) -> str:
    """Generate a stable ID for a code function."""
    return hashlib.sha256(f"{language}:{code}".encode()).hexdigest()[:16]
