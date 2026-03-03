"""
LLM Router for NLP2CMD — multi-model routing with fallbacks and specialization.

Uses LiteLLM Router for:
- Task-based model specialization (vision, coding, text, polish, repair, etc.)
- Priority-based fallback chains (paid remote → free remote → local Ollama)
- Latency-based routing between deployments
- Automatic retry and cooldown on failures

Environment:
    OPENROUTER_API_KEY       — for remote models via OpenRouter
    OLLAMA_BASE_URL          — Ollama endpoint (default: http://localhost:11434)
    NLP2CMD_ROUTER_CONFIG    — path to litellm_config.yaml (auto-detected)
    NLP2CMD_ROUTER_STRATEGY  — routing strategy override (default: from config)
    NLP2CMD_ROUTER_VERBOSE   — enable verbose logging (default: false)

Usage:
    from nlp2cmd.llm.router import LLMRouter

    router = LLMRouter()
    # Text completion with auto-routing
    resp = await router.completion("Pokaż procesy", task="text")
    # Vision with fallback chain
    resp = await router.vision(image_b64, "What's in this image?")
    # Auto-detect task from prompt
    resp = await router.auto_completion("napisz zapytanie SQL dla użytkowników")
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

_DEBUG = os.environ.get("NLP2CMD_DEBUG", "").lower() in ("1", "true", "yes")
_VERBOSE = os.environ.get("NLP2CMD_ROUTER_VERBOSE", "").lower() in ("1", "true", "yes")


def _debug(msg: str) -> None:
    if _DEBUG or _VERBOSE:
        print(f"DEBUG [LLMRouter] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RouterResponse:
    """Unified response from LLM Router."""
    content: str = ""
    model: str = ""
    task: str = ""
    deployment_id: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    fallback_used: bool = False
    attempts: int = 1

    @property
    def tokens_used(self) -> int:
        return self.usage.get("total_tokens", 0)


@dataclass
class ModelHealth:
    """Health status of a model deployment."""
    model_name: str
    deployment_id: str
    healthy: bool
    last_error: Optional[str] = None
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    total_calls: int = 0


# ---------------------------------------------------------------------------
# Task classifier — keyword-based (fast, no embeddings needed)
# ---------------------------------------------------------------------------

_TASK_PATTERNS: dict[str, list[str]] = {
    "vision": [
        r"\bimage\b", r"\bpicture\b", r"\bscreenshot\b", r"\bphoto\b",
        r"\bcaptcha\b", r"\bocr\b", r"\bvisual\b", r"\bchart\b",
        r"\bobrazek\b", r"\bobrazk\b", r"\bzrzut\b", r"\bzdj[eę]ci\b",
        r"\bopisz.*obraz\b", r"\bco (jest|widzisz) na\b",
    ],
    "coding": [
        r"\bcode\b", r"\bsql\b", r"\bquery\b", r"\bdocker\b",
        r"\bkubectl\b", r"\bshell\b", r"\bbash\b", r"\bscript\b",
        r"\bfunction\b", r"\bclass\b", r"\bapi\b", r"\bdebug\b",
        r"\bkod\b", r"\bskrypt\b", r"\bkomend[aęy]\b", r"\bzapytani[ea]\b",
        r"\bkontener\b", r"\bpod[sy]?\b",
    ],
    "polish": [
        r"\bpo polsku\b", r"\bprzetłumacz\b", r"\bwyjaśnij\b",
        r"\bpokaż\b", r"\bznajdź\b", r"\bwyświetl\b", r"\butwórz\b",
        r"\busun\b", r"\bzmień\b", r"\bskopiuj\b", r"\bprzenieś\b",
    ],
    "planning": [
        r"\bplan\b", r"\bsteps?\b", r"\bdecompose\b", r"\bsequence\b",
        r"\bmulti.?step\b", r"\bworkflow\b",
        r"\bkrok[ió]w?\b", r"\betap\b", r"\bzaplanuj\b", r"\brozłóż\b",
    ],
    "repair": [
        r"\brepair\b", r"\bfix\b", r"\bfailed?\b", r"\berror\b",
        r"\bnapraw\b", r"\bbłąd\b", r"\bnie działa\b",
        r"\bnapraw.*komend",
    ],
}


def classify_task(prompt: str) -> str:
    """Classify prompt into task category using keyword patterns."""
    prompt_lower = prompt.lower()
    scores: dict[str, int] = {}

    for task, patterns in _TASK_PATTERNS.items():
        score = sum(1 for p in patterns if re.search(p, prompt_lower))
        if score > 0:
            scores[task] = score

    if not scores:
        return "text"

    return max(scores, key=scores.get)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def _find_config() -> Optional[Path]:
    """Find litellm_config.yaml in standard locations."""
    explicit = os.environ.get("NLP2CMD_ROUTER_CONFIG")
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p

    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent / "config" / "litellm_config.yaml",
        Path.cwd() / "config" / "litellm_config.yaml",
        Path.cwd() / "litellm_config.yaml",
        Path.home() / ".config" / "nlp2cmd" / "litellm_config.yaml",
    ]
    for c in candidates:
        if c.exists():
            _debug(f"Found config at {c}")
            return c

    _debug("No litellm_config.yaml found, using built-in defaults")
    return None


def _load_config(path: Optional[Path] = None) -> dict[str, Any]:
    """Load and parse litellm_config.yaml."""
    if path is None:
        path = _find_config()
    if path is None:
        return {}

    try:
        import yaml
        with open(path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        _debug(f"Loaded config: {len(cfg.get('model_list', []))} model deployments")
        return cfg
    except Exception as e:
        _debug(f"Failed to load config {path}: {e}")
        return {}


# ---------------------------------------------------------------------------
# Built-in fallback model definitions (used when no config file found)
# ---------------------------------------------------------------------------

def _builtin_model_list() -> list[dict[str, Any]]:
    """Minimal built-in model list for when no config.yaml is available."""
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    ollama_base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    models: list[dict[str, Any]] = []

    # Remote models (only if API key available)
    if openrouter_key:
        models.extend([
            {
                "model_name": "vision",
                "litellm_params": {
                    "model": "openrouter/google/gemini-2.5-pro-preview",
                    "api_key": openrouter_key,
                    "api_base": "https://openrouter.ai/api/v1",
                },
            },
            {
                "model_name": "vision",
                "litellm_params": {
                    "model": "openrouter/qwen/qwen-2.5-vl-7b-instruct:free",
                    "api_key": openrouter_key,
                    "api_base": "https://openrouter.ai/api/v1",
                },
            },
            {
                "model_name": "coding",
                "litellm_params": {
                    "model": "openrouter/qwen/qwen-2.5-coder-32b-instruct",
                    "api_key": openrouter_key,
                    "api_base": "https://openrouter.ai/api/v1",
                },
            },
            {
                "model_name": "text",
                "litellm_params": {
                    "model": "openrouter/x-ai/grok-code-fast-1",
                    "api_key": openrouter_key,
                    "api_base": "https://openrouter.ai/api/v1",
                },
            },
            {
                "model_name": "repair",
                "litellm_params": {
                    "model": "openrouter/qwen/qwen-2.5-coder-32b-instruct",
                    "api_key": openrouter_key,
                    "api_base": "https://openrouter.ai/api/v1",
                },
            },
        ])

    # Local Ollama models (always available as fallback)
    models.extend([
        {
            "model_name": "vision",
            "litellm_params": {
                "model": "ollama/qwen2.5vl:7b",
                "api_base": ollama_base,
            },
        },
        {
            "model_name": "vision",
            "litellm_params": {
                "model": "ollama/llava:7b",
                "api_base": ollama_base,
            },
        },
        {
            "model_name": "coding",
            "litellm_params": {
                "model": "ollama/qwen2.5-coder:7b",
                "api_base": ollama_base,
            },
        },
        {
            "model_name": "text",
            "litellm_params": {
                "model": "ollama/qwen2.5:7b",
                "api_base": ollama_base,
            },
        },
        {
            "model_name": "polish",
            "litellm_params": {
                "model": "ollama/SpeakLeash/bielik-11b-v2.3-instruct:Q8_0",
                "api_base": ollama_base,
            },
        },
        {
            "model_name": "repair",
            "litellm_params": {
                "model": "ollama/qwen2.5-coder:7b",
                "api_base": ollama_base,
            },
        },
        {
            "model_name": "validation",
            "litellm_params": {
                "model": "ollama/qwen2.5:3b",
                "api_base": ollama_base,
            },
        },
        {
            "model_name": "fast",
            "litellm_params": {
                "model": "ollama/qwen2.5:3b",
                "api_base": ollama_base,
            },
        },
        {
            "model_name": "planning",
            "litellm_params": {
                "model": "ollama/qwen2.5:7b",
                "api_base": ollama_base,
            },
        },
    ])

    return models


# ---------------------------------------------------------------------------
# Resolve os.environ/VAR_NAME references in config
# ---------------------------------------------------------------------------

def _resolve_env_refs(obj: Any) -> Any:
    """Recursively resolve 'os.environ/VAR_NAME' strings to env values."""
    if isinstance(obj, str) and obj.startswith("os.environ/"):
        var_name = obj[len("os.environ/"):]
        val = os.environ.get(var_name, "")
        if not val:
            _debug(f"Warning: env var {var_name} is empty")
        return val
    elif isinstance(obj, dict):
        return {k: _resolve_env_refs(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_env_refs(item) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# LLMRouter — main class
# ---------------------------------------------------------------------------

class LLMRouter:
    """
    Smart LLM Router with multi-model support, fallbacks, and task specialization.

    Wraps LiteLLM Router for automatic model selection based on:
    1. Task type (vision, coding, text, polish, repair, validation, fast, planning)
    2. Priority-based fallbacks (paid remote → free remote → local Ollama)
    3. Latency-based routing between deployments
    4. Automatic retry on failure with cooldown

    Works with or without LiteLLM installed — falls back to direct HTTP calls.
    """

    VALID_TASKS = ("vision", "coding", "text", "polish", "repair", "validation", "fast", "planning")
    DEFAULT_TASK = "text"

    def __init__(
        self,
        config_path: Optional[str] = None,
        strategy: Optional[str] = None,
        verbose: bool = False,
        adaptive_learning: bool = True,
    ):
        self._verbose = verbose or _VERBOSE
        self._config = _load_config(Path(config_path) if config_path else None)
        self._strategy = (
            strategy
            or os.environ.get("NLP2CMD_ROUTER_STRATEGY")
            or self._config.get("router_settings", {}).get("routing_strategy", "latency-based-routing")
        )
        self._router = None
        self._litellm_available = False
        self._stats: dict[str, dict[str, Any]] = {}
        self._learner = None
        if adaptive_learning:
            try:
                from nlp2cmd.llm.adaptive_learner import AdaptiveLearner
                self._learner = AdaptiveLearner()
                _debug("Adaptive learner initialized")
            except Exception as e:
                _debug(f"Adaptive learner init failed: {e}")
        self._init_router()

    def _init_router(self) -> None:
        """Initialize LiteLLM Router if available."""
        try:
            import litellm
            from litellm import Router

            litellm.set_verbose = self._verbose
            if not self._verbose:
                litellm.suppress_debug_info = True

            # Build model list
            if self._config.get("model_list"):
                model_list = _resolve_env_refs(self._config["model_list"])
            else:
                model_list = _builtin_model_list()

            # Filter out models with empty API keys
            valid_models = []
            for m in model_list:
                params = m.get("litellm_params", {})
                api_key = params.get("api_key", "")
                # Local models don't need API keys
                model_id = params.get("model", "")
                is_local = model_id.startswith("ollama/")
                if is_local or api_key:
                    valid_models.append(m)
                else:
                    _debug(f"Skipping {model_id} — no API key")

            if not valid_models:
                _debug("No valid models configured!")
                return

            # Router settings
            router_settings = self._config.get("router_settings", {})
            fallback_cfg = self._config.get("litellm_settings", {}).get("fallbacks", [])

            # Build fallback dict
            fallbacks: list[dict[str, list[str]]] = []
            if fallback_cfg:
                fallbacks = fallback_cfg

            self._router = Router(
                model_list=valid_models,
                routing_strategy=self._strategy,
                num_retries=router_settings.get("num_retries", 3),
                timeout=router_settings.get("timeout", 60),
                allowed_fails=router_settings.get("allowed_fails", 2),
                cooldown_time=router_settings.get("cooldown_time", 30),
                fallbacks=fallbacks,
                set_verbose=self._verbose,
                retry_after=router_settings.get("retry_after", 0),
            )

            self._litellm_available = True
            _debug(
                f"Router initialized: {len(valid_models)} deployments, "
                f"strategy={self._strategy}, fallbacks={len(fallbacks)}"
            )

        except ImportError:
            _debug("LiteLLM not installed — using direct HTTP fallback")
            self._litellm_available = False
        except Exception as e:
            _debug(f"Router init failed: {e}")
            self._litellm_available = False

    @property
    def is_ready(self) -> bool:
        """Check if router is operational."""
        return self._litellm_available and self._router is not None

    @property
    def available_tasks(self) -> list[str]:
        """List available task types based on configured models."""
        if not self._router:
            return []
        seen = set()
        for m in (self._router.model_list or []):
            name = m.get("model_name", "")
            if name:
                seen.add(name)
        return sorted(seen)

    # -------------------------------------------------------------------
    # Core completion methods
    # -------------------------------------------------------------------

    async def completion(
        self,
        prompt: str,
        *,
        task: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.3,
        json_mode: bool = False,
        **kwargs: Any,
    ) -> RouterResponse:
        """
        Text completion routed to the best model for the task.

        Args:
            prompt: User message
            task: Task type (vision, coding, text, polish, etc.)
                  Auto-detected from prompt if None.
            system: Optional system message
            max_tokens: Maximum response tokens
            temperature: Sampling temperature
            json_mode: Request JSON-formatted response
        """
        resolved_task = task or classify_task(prompt)
        if resolved_task not in self.VALID_TASKS:
            resolved_task = self.DEFAULT_TASK

        _debug(f"completion: task={resolved_task}, prompt={prompt[:80]!r}")

        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        extra: dict[str, Any] = {}
        if json_mode:
            extra["response_format"] = {"type": "json_object"}

        return await self._route_call(
            task=resolved_task,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **extra,
            **kwargs,
        )

    async def vision(
        self,
        image_b64: str,
        prompt: str,
        *,
        system: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.1,
    ) -> RouterResponse:
        """
        Vision analysis — send image + text prompt.

        Automatically routes to vision-capable models with fallback.
        """
        _debug(f"vision: prompt={prompt[:80]!r}")

        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})

        messages.append({
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{image_b64}"
                }},
                {"type": "text", "text": prompt},
            ],
        })

        return await self._route_call(
            task="vision",
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    async def auto_completion(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> RouterResponse:
        """
        Completion with automatic task classification.

        Analyzes the prompt to determine the best task/model category.
        """
        task = classify_task(prompt)
        _debug(f"auto_completion: classified as task={task}")
        return await self.completion(
            prompt, task=task, system=system,
            max_tokens=max_tokens, temperature=temperature, **kwargs,
        )

    # -------------------------------------------------------------------
    # Internal routing
    # -------------------------------------------------------------------

    async def _route_call(
        self,
        task: str,
        messages: list[dict[str, Any]],
        max_tokens: int = 1000,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> RouterResponse:
        """Route a call through LiteLLM Router or direct fallback."""
        start = time.time()

        if self._litellm_available and self._router:
            return await self._call_via_router(
                task, messages, max_tokens, temperature, start, **kwargs,
            )
        else:
            return await self._call_direct_fallback(
                task, messages, max_tokens, temperature, start, **kwargs,
            )

    async def _call_via_router(
        self,
        task: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        temperature: float,
        start: float,
        **kwargs: Any,
    ) -> RouterResponse:
        """Call via LiteLLM Router with automatic fallbacks + adaptive learning."""
        try:
            response = await self._router.acompletion(
                model=task,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )

            latency = (time.time() - start) * 1000
            content = response.choices[0].message.content or ""
            model = getattr(response, "model", "") or ""
            usage = {}
            if hasattr(response, "usage") and response.usage:
                usage = {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                    "total_tokens": getattr(response.usage, "total_tokens", 0),
                }

            self._record_stat(task, model, latency, True)
            # Adaptive learning: record success
            if self._learner:
                self._learner.record_success(model, task, latency)

            return RouterResponse(
                content=content,
                model=model,
                task=task,
                usage=usage,
                latency_ms=latency,
                success=True,
            )

        except Exception as e:
            latency = (time.time() - start) * 1000
            error_msg = str(e)
            _debug(f"Router call failed for task={task}: {error_msg[:200]}")
            self._record_stat(task, "", latency, False, error_msg)

            # Adaptive learning: record failure + try learned fallback
            if self._learner:
                pattern = self._learner.record_failure("", task, error_msg)
                self._learner.evolve()

                # Try learned fallback model via direct HTTP
                fb_model = self._learner.get_fallback_model("", task)
                if fb_model and fb_model.startswith("ollama/"):
                    _debug(f"Adaptive fallback: trying learned model {fb_model}")
                    ollama_base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
                    local_name = fb_model.replace("ollama/", "")
                    fb_result = await self._http_ollama(
                        local_name, messages, max_tokens, temperature, ollama_base,
                    )
                    if fb_result.success:
                        fb_result.task = task
                        fb_result.latency_ms = (time.time() - start) * 1000
                        fb_result.fallback_used = True
                        self._learner.record_success(
                            fb_model, task, fb_result.latency_ms,
                            was_fallback=True, fallback_from="litellm_router",
                        )
                        return fb_result

            return RouterResponse(
                task=task,
                latency_ms=latency,
                success=False,
                error=error_msg,
            )

    async def _call_direct_fallback(
        self,
        task: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        temperature: float,
        start: float,
        **kwargs: Any,
    ) -> RouterResponse:
        """
        Direct HTTP fallback when LiteLLM is not installed.
        Tries OpenRouter first, then Ollama.
        """
        openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
        ollama_base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

        # Task → model mapping for direct calls
        task_models = {
            "vision": ("google/gemini-2.5-pro-preview", "llava:7b"),
            "coding": ("qwen/qwen-2.5-coder-32b-instruct", "qwen2.5-coder:7b"),
            "text": ("x-ai/grok-code-fast-1", "qwen2.5:7b"),
            "polish": ("x-ai/grok-code-fast-1", "bielik-1.5b:latest"),
            "repair": ("qwen/qwen-2.5-coder-32b-instruct", "qwen2.5-coder:7b"),
            "validation": (None, "qwen2.5:3b"),
            "fast": (None, "qwen2.5:3b"),
            "planning": ("google/gemini-2.5-pro-preview", "qwen2.5:7b"),
        }

        remote_model, local_model = task_models.get(task, (None, "qwen2.5:7b"))

        # Adaptive learning: check if remote model should be skipped
        skip_remote = False
        if self._learner and remote_model:
            remote_id = f"openrouter/{remote_model}"
            if self._learner.should_skip_model(remote_id, task):
                _debug(f"Adaptive: skipping {remote_id} (learned to avoid)")
                skip_remote = True

        # Try OpenRouter first (if key available and model defined and not skipped)
        if openrouter_key and remote_model and not skip_remote:
            result = await self._http_openrouter(
                remote_model, messages, max_tokens, temperature, openrouter_key,
            )
            if result.success:
                result.task = task
                result.latency_ms = (time.time() - start) * 1000
                if self._learner:
                    self._learner.record_success(
                        f"openrouter/{remote_model}", task, result.latency_ms,
                    )
                return result
            _debug(f"OpenRouter failed for {remote_model}, trying Ollama...")
            # Adaptive learning: record the remote failure
            if self._learner:
                self._learner.record_failure(
                    f"openrouter/{remote_model}", task,
                    result.error or "unknown error",
                )

        # Fallback to Ollama
        result = await self._http_ollama(
            local_model, messages, max_tokens, temperature, ollama_base,
        )
        result.task = task
        result.latency_ms = (time.time() - start) * 1000
        result.fallback_used = bool(openrouter_key and remote_model and not skip_remote)

        # Adaptive learning: record Ollama success/failure
        if self._learner:
            ollama_id = f"ollama/{local_model}"
            if result.success:
                self._learner.record_success(
                    ollama_id, task, result.latency_ms,
                    was_fallback=result.fallback_used,
                    fallback_from=f"openrouter/{remote_model}" if result.fallback_used else None,
                )
                self._learner.evolve()
            else:
                self._learner.record_failure(
                    ollama_id, task, result.error or "unknown error",
                )

        return result

    async def _http_openrouter(
        self,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        temperature: float,
        api_key: str,
    ) -> RouterResponse:
        """Direct HTTP call to OpenRouter (no LiteLLM dependency)."""
        try:
            import httpx

            body = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/wronai/nlp2cmd",
                        "X-Title": "NLP2CMD",
                    },
                    json=body,
                    timeout=60,
                )

                if resp.status_code != 200:
                    return RouterResponse(
                        success=False,
                        error=f"OpenRouter HTTP {resp.status_code}: {resp.text[:200]}",
                        model=model,
                    )

                data = resp.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )

                return RouterResponse(
                    content=content,
                    model=data.get("model", model),
                    usage=data.get("usage", {}),
                    success=True,
                )

        except Exception as e:
            return RouterResponse(success=False, error=str(e), model=model)

    async def _http_ollama(
        self,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        temperature: float,
        base_url: str,
    ) -> RouterResponse:
        """Direct HTTP call to Ollama (no LiteLLM dependency)."""
        try:
            import httpx

            body = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                },
            }

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{base_url}/api/chat",
                    json=body,
                    timeout=120,
                )

                if resp.status_code != 200:
                    return RouterResponse(
                        success=False,
                        error=f"Ollama HTTP {resp.status_code}: {resp.text[:200]}",
                        model=f"ollama/{model}",
                    )

                data = resp.json()
                content = data.get("message", {}).get("content", "").strip()

                usage = {}
                if "eval_count" in data:
                    usage = {
                        "prompt_tokens": data.get("prompt_eval_count", 0),
                        "completion_tokens": data.get("eval_count", 0),
                        "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                    }

                return RouterResponse(
                    content=content,
                    model=f"ollama/{model}",
                    usage=usage,
                    success=True,
                )

        except Exception as e:
            return RouterResponse(
                success=False,
                error=str(e),
                model=f"ollama/{model}",
            )

    # -------------------------------------------------------------------
    # Stats and health
    # -------------------------------------------------------------------

    def _record_stat(
        self, task: str, model: str, latency_ms: float,
        success: bool, error: Optional[str] = None,
    ) -> None:
        """Record call statistics."""
        key = f"{task}:{model}"
        if key not in self._stats:
            self._stats[key] = {
                "total": 0, "success": 0, "fail": 0,
                "total_latency": 0.0, "last_error": None,
            }
        s = self._stats[key]
        s["total"] += 1
        s["total_latency"] += latency_ms
        if success:
            s["success"] += 1
        else:
            s["fail"] += 1
            s["last_error"] = error

    def get_health(self) -> list[ModelHealth]:
        """Get health status of all model deployments."""
        results = []
        for key, s in self._stats.items():
            task, model = key.split(":", 1)
            total = s["total"]
            results.append(ModelHealth(
                model_name=task,
                deployment_id=model,
                healthy=s["fail"] < s["total"] * 0.5,
                last_error=s["last_error"],
                avg_latency_ms=s["total_latency"] / total if total > 0 else 0,
                success_rate=s["success"] / total if total > 0 else 1.0,
                total_calls=total,
            ))
        return results

    def get_stats(self) -> dict[str, Any]:
        """Get router statistics summary."""
        stats = {
            "litellm_available": self._litellm_available,
            "strategy": self._strategy,
            "available_tasks": self.available_tasks,
            "total_calls": sum(s["total"] for s in self._stats.values()),
            "total_failures": sum(s["fail"] for s in self._stats.values()),
            "models": self._stats,
        }
        if self._learner:
            stats["adaptive_learning"] = self._learner.get_performance_report()
        return stats

    def __repr__(self) -> str:
        status = "ready" if self.is_ready else "fallback-mode"
        return f"<LLMRouter status={status} strategy={self._strategy} tasks={self.available_tasks}>"


# ---------------------------------------------------------------------------
# Module-level convenience singleton
# ---------------------------------------------------------------------------

_default_router: Optional[LLMRouter] = None


def get_router(**kwargs: Any) -> LLMRouter:
    """Get or create the default LLMRouter singleton."""
    global _default_router
    if _default_router is None:
        _default_router = LLMRouter(**kwargs)
    return _default_router


def reset_router() -> None:
    """Reset the default router (e.g., after config change)."""
    global _default_router
    _default_router = None
