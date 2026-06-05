"""Unified sync LLM client for canvas step generation."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .config import CanvasLLMConfig

log = logging.getLogger("nlp2cmd.canvas_planner.llm_client")


def _normalize_ollama_model(model: str) -> str:
    if model.startswith("ollama/"):
        return model.split("/", 1)[1]
    if "/" in model and not model.startswith("openrouter/"):
        return model.split("/", 1)[-1]
    return model


def _call_via_router(prompt: str, config: CanvasLLMConfig) -> str | None:
    try:
        from nlp2cmd.llm.router import get_router
    except ImportError:
        return None

    router = get_router()
    if not router.is_ready:
        return None

    async def _run() -> str | None:
        response = await router.completion(
            prompt,
            task="planning",
            max_tokens=3000,
            temperature=0.3,
        )
        if response.success and response.content:
            return response.content.strip()
        if response.error:
            log.warning("Canvas router LLM failed: %s", response.error)
        return None

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()
    except Exception as exc:
        log.warning("Canvas router LLM error: %s", exc)
        return None


def _call_via_ollama(prompt: str, config: CanvasLLMConfig) -> str | None:
    try:
        import requests
    except ImportError:
        log.debug("requests not available for canvas LLM")
        return None

    model = _normalize_ollama_model(config.model)
    if model.startswith("openrouter/"):
        return None

    resp = None
    for attempt in range(config.max_retries + 1):
        try:
            resp = requests.post(
                f"{config.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 3000},
                },
                timeout=config.timeout,
            )
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
            if attempt < config.max_retries:
                log.warning("Canvas Ollama returned %d, retrying...", resp.status_code)
        except Exception as exc:
            if attempt < config.max_retries:
                log.warning(
                    "Canvas Ollama error (attempt %d/%d): %s",
                    attempt + 1,
                    config.max_retries + 1,
                    exc,
                )
            else:
                raise
    return None


def call_canvas_llm(prompt: str, config: CanvasLLMConfig) -> str | None:
    """Call configured LLM for canvas planning (router first, Ollama fallback)."""
    raw = _call_via_router(prompt, config)
    if raw:
        log.info("[CanvasLLM] plan via router (%s)", config.model)
        return raw

    raw = _call_via_ollama(prompt, config)
    if raw:
        log.info("[CanvasLLM] plan via Ollama (%s)", _normalize_ollama_model(config.model))
    return raw
