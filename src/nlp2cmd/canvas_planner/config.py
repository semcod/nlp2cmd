"""Shared LLM configuration for canvas planning."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, "1" if default else "0").strip().lower() in {
        "1", "true", "yes", "on",
    }


def resolve_canvas_model(explicit: str | None = None) -> str:
    """Resolve canvas planner model from env (LLM_MODEL takes precedence)."""
    if explicit:
        return explicit
    return (
        os.getenv("LLM_MODEL")
        or os.getenv("LITELLM_MODEL")
        or os.getenv("NLP2CMD_PLANNER_MODEL")
        or os.getenv("NLP2CMD_LLM_MODEL")
        or "qwen2.5:3b"
    )


def resolve_ollama_url(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


@dataclass(frozen=True)
class CanvasLLMConfig:
    ollama_url: str
    model: str
    timeout: float
    max_retries: int
    use_blueprints: bool
    use_templates: bool
    use_rule_fallback: bool

    @classmethod
    def from_env(
        cls,
        *,
        ollama_url: str | None = None,
        model: str | None = None,
    ) -> CanvasLLMConfig:
        return cls(
            ollama_url=resolve_ollama_url(ollama_url),
            model=resolve_canvas_model(model),
            timeout=float(os.getenv("CANVAS_LLM_TIMEOUT", "60")),
            max_retries=int(os.getenv("CANVAS_LLM_RETRIES", "2")),
            use_blueprints=_env_flag("CANVAS_USE_BLUEPRINTS", default=False),
            use_templates=_env_flag("CANVAS_USE_TEMPLATES", default=False),
            use_rule_fallback=_env_flag("CANVAS_USE_RULE_FALLBACK", default=True),
        )
