"""
Human-readable description of the active LLM configuration.

Used to surface, at CLI startup, *whether* an LLM is used and *which* one —
so users can see at a glance that e.g. drawing/planning is going through
OpenRouter with their configured model, or falling back to a local Ollama
model / rule-based planning.

This module is intentionally light: it only inspects environment variables and
optional imports, and never performs network calls or heavy router init.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Env vars that select the default model, in precedence order.
# Mirrors nlp2cmd.canvas_planner.config.resolve_canvas_model.
_MODEL_ENV_KEYS = (
    "LLM_MODEL",
    "LITELLM_MODEL",
    "NLP2CMD_PLANNER_MODEL",
    "NLP2CMD_LLM_MODEL",
)

_DEFAULT_LOCAL_MODEL = "qwen2.5:3b"


@dataclass(frozen=True)
class LLMInfo:
    """Snapshot of the configured LLM backend."""

    model: str
    source_env: str | None
    provider: str
    openrouter_key: bool
    ollama_url: str
    litellm_available: bool
    is_default: bool

    @property
    def available(self) -> bool:
        """Whether some LLM backend is plausibly reachable."""
        if self.provider == "OpenRouter":
            return self.openrouter_key
        # Local/LiteLLM: assume reachable (Ollama may be running locally)
        return True


def _resolve_model() -> tuple[str, str | None]:
    for key in _MODEL_ENV_KEYS:
        val = (os.getenv(key) or "").strip()
        if val:
            return val, key
    return _DEFAULT_LOCAL_MODEL, None


def _provider_for(model: str) -> str:
    if model.startswith("openrouter/"):
        return "OpenRouter"
    if model.startswith("ollama/"):
        return "Ollama (local)"
    if "/" in model:
        return "LiteLLM/OpenRouter"
    return "Ollama (local)"


def describe_active_llm() -> LLMInfo:
    """Inspect the environment and return an :class:`LLMInfo` snapshot."""
    model, source_env = _resolve_model()
    try:
        import litellm  # noqa: F401

        litellm_available = True
    except Exception:
        litellm_available = False

    return LLMInfo(
        model=model,
        source_env=source_env,
        provider=_provider_for(model),
        openrouter_key=bool(os.getenv("OPENROUTER_API_KEY")),
        ollama_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        litellm_available=litellm_available,
        is_default=source_env is None,
    )


def format_llm_banner() -> str:
    """
    Build a one-line, Rich-markup banner describing the active LLM.

    Examples:
        🤖 LLM: OpenRouter · model=openrouter/deepseek/deepseek-v4-pro · key=set · router=litellm
        🤖 LLM: Ollama (local) · model=qwen2.5:3b (default) · url=http://localhost:11434
    """
    info = describe_active_llm()
    router = "litellm" if info.litellm_available else "direct-http"
    parts = [f"[bold]🤖 LLM:[/bold] {info.provider}"]

    model_label = info.model + (" [dim](default)[/dim]" if info.is_default else "")
    parts.append(f"model={model_label}")

    if info.provider == "OpenRouter" or info.openrouter_key:
        key_state = "[green]set[/green]" if info.openrouter_key else "[red]missing[/red]"
        parts.append(f"OpenRouter key={key_state}")
    if info.provider.startswith("Ollama"):
        parts.append(f"url={info.ollama_url}")

    parts.append(f"router={router}")

    banner = "  ·  ".join(parts)

    # Warn about the common misconfiguration: OpenRouter model but no key.
    if info.provider == "OpenRouter" and not info.openrouter_key:
        banner += (
            "\n[yellow]⚠ OPENROUTER_API_KEY not set — OpenRouter calls will fail; "
            "falling back to local Ollama / rule-based planning.[/yellow]"
        )
    return banner
