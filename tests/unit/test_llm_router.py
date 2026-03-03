"""
Tests for LLM Router — multi-model routing with fallbacks and specialization.

Tests cover:
- Task classification (keyword-based)
- Config loading and env resolution
- Router initialization (with and without LiteLLM)
- Completion routing
- Vision routing
- Auto-classification
- Fallback behavior
- Health/stats tracking
- Singleton management
"""

from __future__ import annotations

import asyncio
import os
import json
from pathlib import Path
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Task classifier tests (no external deps needed)
# ---------------------------------------------------------------------------

class TestClassifyTask:
    """Test keyword-based task classification."""

    def test_vision_english(self):
        from nlp2cmd.llm.router import classify_task
        assert classify_task("describe this image") == "vision"
        assert classify_task("what's in the screenshot") == "vision"
        assert classify_task("analyze the chart") == "vision"
        assert classify_task("solve the captcha") == "vision"

    def test_vision_polish(self):
        from nlp2cmd.llm.router import classify_task
        assert classify_task("opisz zrzut ekranu") == "vision"
        assert classify_task("co jest na obrazku") == "vision"

    def test_coding_english(self):
        from nlp2cmd.llm.router import classify_task
        assert classify_task("write SQL query for users") == "coding"
        assert classify_task("docker run nginx") == "coding"
        assert classify_task("kubectl get pods") == "coding"
        assert classify_task("debug this script") == "coding"

    def test_coding_polish(self):
        from nlp2cmd.llm.router import classify_task
        assert classify_task("napisz kod do parsowania") == "coding"
        assert classify_task("zapytanie SQL dla zamówień") == "coding"
        assert classify_task("komenda shell") == "coding"

    def test_polish_tasks(self):
        from nlp2cmd.llm.router import classify_task
        result = classify_task("przetłumacz na polski")
        assert result == "polish"
        result = classify_task("wyjaśnij po polsku jak to działa")
        assert result == "polish"

    def test_planning_tasks(self):
        from nlp2cmd.llm.router import classify_task
        assert classify_task("plan a sequence of actions") == "planning"
        assert classify_task("decompose this into steps") == "planning"
        assert classify_task("zaplanuj kroki") == "planning"

    def test_repair_tasks(self):
        from nlp2cmd.llm.router import classify_task
        assert classify_task("fix this command") == "repair"
        assert classify_task("command failed with error") == "repair"
        assert classify_task("napraw komendę") == "repair"

    def test_general_text_fallback(self):
        from nlp2cmd.llm.router import classify_task
        assert classify_task("hello world") == "text"
        assert classify_task("what is the meaning of life") == "text"


# ---------------------------------------------------------------------------
# Config loading tests
# ---------------------------------------------------------------------------

class TestConfigLoading:
    """Test configuration loading and env resolution."""

    def test_resolve_env_refs(self):
        from nlp2cmd.llm.router import _resolve_env_refs

        with patch.dict(os.environ, {"TEST_KEY": "secret123"}):
            assert _resolve_env_refs("os.environ/TEST_KEY") == "secret123"

    def test_resolve_env_refs_missing(self):
        from nlp2cmd.llm.router import _resolve_env_refs

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NONEXISTENT_VAR", None)
            assert _resolve_env_refs("os.environ/NONEXISTENT_VAR") == ""

    def test_resolve_env_refs_nested(self):
        from nlp2cmd.llm.router import _resolve_env_refs

        with patch.dict(os.environ, {"MY_KEY": "val123"}):
            result = _resolve_env_refs({
                "api_key": "os.environ/MY_KEY",
                "model": "test-model",
                "nested": {"key": "os.environ/MY_KEY"},
            })
            assert result["api_key"] == "val123"
            assert result["model"] == "test-model"
            assert result["nested"]["key"] == "val123"

    def test_resolve_env_refs_list(self):
        from nlp2cmd.llm.router import _resolve_env_refs

        with patch.dict(os.environ, {"K": "v"}):
            result = _resolve_env_refs(["os.environ/K", "plain"])
            assert result == ["v", "plain"]

    def test_find_config_from_project(self):
        from nlp2cmd.llm.router import _find_config

        config_path = _find_config()
        # Should find config/litellm_config.yaml
        if config_path:
            assert config_path.name == "litellm_config.yaml"
            assert config_path.exists()

    def test_load_config_valid(self):
        from nlp2cmd.llm.router import _load_config

        config_path = Path(__file__).resolve().parent.parent.parent / "config" / "litellm_config.yaml"
        if config_path.exists():
            cfg = _load_config(config_path)
            assert "model_list" in cfg
            assert len(cfg["model_list"]) > 0
            # Verify task categories exist
            task_names = {m["model_name"] for m in cfg["model_list"]}
            assert "vision" in task_names
            assert "coding" in task_names
            assert "text" in task_names

    def test_load_config_missing_file(self):
        from nlp2cmd.llm.router import _load_config

        cfg = _load_config(Path("/nonexistent/config.yaml"))
        assert cfg == {}

    def test_builtin_model_list(self):
        from nlp2cmd.llm.router import _builtin_model_list

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            models = _builtin_model_list()
            assert len(models) > 0
            names = {m["model_name"] for m in models}
            assert "vision" in names
            assert "coding" in names
            assert "text" in names
            assert "validation" in names
            assert "fast" in names

    def test_builtin_model_list_no_api_key(self):
        from nlp2cmd.llm.router import _builtin_model_list

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENROUTER_API_KEY", None)
            models = _builtin_model_list()
            # Should still have local Ollama models
            assert len(models) > 0
            for m in models:
                model_id = m["litellm_params"]["model"]
                assert model_id.startswith("ollama/"), f"Without API key, all models should be local: {model_id}"


# ---------------------------------------------------------------------------
# Router data class tests
# ---------------------------------------------------------------------------

class TestRouterResponse:
    """Test RouterResponse data class."""

    def test_defaults(self):
        from nlp2cmd.llm.router import RouterResponse

        resp = RouterResponse()
        assert resp.content == ""
        assert resp.success is True
        assert resp.tokens_used == 0
        assert resp.fallback_used is False

    def test_with_usage(self):
        from nlp2cmd.llm.router import RouterResponse

        resp = RouterResponse(
            content="hello",
            model="test-model",
            usage={"total_tokens": 42, "prompt_tokens": 10, "completion_tokens": 32},
        )
        assert resp.tokens_used == 42

    def test_error_response(self):
        from nlp2cmd.llm.router import RouterResponse

        resp = RouterResponse(success=False, error="connection timeout")
        assert not resp.success
        assert resp.error == "connection timeout"


class TestModelHealth:
    """Test ModelHealth data class."""

    def test_healthy(self):
        from nlp2cmd.llm.router import ModelHealth

        h = ModelHealth(
            model_name="vision",
            deployment_id="ollama/llava:7b",
            healthy=True,
            success_rate=0.95,
            total_calls=20,
        )
        assert h.healthy
        assert h.success_rate == 0.95


# ---------------------------------------------------------------------------
# Router initialization tests
# ---------------------------------------------------------------------------

class TestRouterInit:
    """Test LLMRouter initialization."""

    def test_init_without_litellm(self):
        """Router should gracefully handle missing litellm."""
        from nlp2cmd.llm.router import LLMRouter

        with patch.dict("sys.modules", {"litellm": None}):
            # Force reimport scenario — just test that it doesn't crash
            router = LLMRouter.__new__(LLMRouter)
            router._verbose = False
            router._config = {}
            router._strategy = "latency-based-routing"
            router._router = None
            router._litellm_available = False
            router._stats = {}
            router._learner = None

            assert not router.is_ready
            assert router.available_tasks == []

    def test_valid_tasks_constant(self):
        from nlp2cmd.llm.router import LLMRouter

        assert "vision" in LLMRouter.VALID_TASKS
        assert "coding" in LLMRouter.VALID_TASKS
        assert "text" in LLMRouter.VALID_TASKS
        assert "polish" in LLMRouter.VALID_TASKS
        assert "repair" in LLMRouter.VALID_TASKS
        assert "validation" in LLMRouter.VALID_TASKS
        assert "fast" in LLMRouter.VALID_TASKS
        assert "planning" in LLMRouter.VALID_TASKS


# ---------------------------------------------------------------------------
# Singleton tests
# ---------------------------------------------------------------------------

class TestSingleton:
    """Test get_router / reset_router singleton management."""

    def test_get_router_returns_same_instance(self):
        from nlp2cmd.llm.router import get_router, reset_router

        reset_router()
        r1 = get_router()
        r2 = get_router()
        assert r1 is r2
        reset_router()

    def test_reset_router_creates_new(self):
        from nlp2cmd.llm.router import get_router, reset_router

        reset_router()
        r1 = get_router()
        reset_router()
        r2 = get_router()
        assert r1 is not r2
        reset_router()


# ---------------------------------------------------------------------------
# Stats and health tests
# ---------------------------------------------------------------------------

class TestStatsAndHealth:
    """Test statistics recording and health checks."""

    def test_record_and_get_stats(self):
        from nlp2cmd.llm.router import LLMRouter

        router = LLMRouter.__new__(LLMRouter)
        router._verbose = False
        router._config = {}
        router._strategy = "latency-based-routing"
        router._router = None
        router._litellm_available = False
        router._stats = {}
        router._learner = None

        router._record_stat("vision", "ollama/llava:7b", 150.0, True)
        router._record_stat("vision", "ollama/llava:7b", 200.0, True)
        router._record_stat("vision", "ollama/llava:7b", 0.0, False, "timeout")

        stats = router.get_stats()
        assert stats["total_calls"] == 3
        assert stats["total_failures"] == 1

    def test_get_health(self):
        from nlp2cmd.llm.router import LLMRouter

        router = LLMRouter.__new__(LLMRouter)
        router._verbose = False
        router._config = {}
        router._strategy = "latency-based-routing"
        router._router = None
        router._litellm_available = False
        router._stats = {}
        router._learner = None

        router._record_stat("coding", "ollama/qwen:7b", 100.0, True)
        router._record_stat("coding", "ollama/qwen:7b", 100.0, True)
        router._record_stat("coding", "ollama/qwen:7b", 0.0, False, "err")

        health = router.get_health()
        assert len(health) == 1
        assert health[0].model_name == "coding"
        assert health[0].healthy is True  # 1 fail out of 3 < 50%
        assert health[0].total_calls == 3
        assert health[0].last_error == "err"

    def test_unhealthy_model(self):
        from nlp2cmd.llm.router import LLMRouter

        router = LLMRouter.__new__(LLMRouter)
        router._verbose = False
        router._config = {}
        router._strategy = "latency-based-routing"
        router._router = None
        router._litellm_available = False
        router._stats = {}
        router._learner = None

        # 3 failures out of 4 calls = 75% failure rate
        router._record_stat("text", "remote/model", 0.0, False, "err1")
        router._record_stat("text", "remote/model", 0.0, False, "err2")
        router._record_stat("text", "remote/model", 0.0, False, "err3")
        router._record_stat("text", "remote/model", 100.0, True)

        health = router.get_health()
        assert len(health) == 1
        assert health[0].healthy is False


# ---------------------------------------------------------------------------
# Direct HTTP fallback tests (mocked)
# ---------------------------------------------------------------------------

class TestDirectFallback:
    """Test direct HTTP calls when LiteLLM is not available."""

    @pytest.mark.asyncio
    async def test_ollama_fallback(self):
        from nlp2cmd.llm.router import LLMRouter

        router = LLMRouter.__new__(LLMRouter)
        router._verbose = False
        router._config = {}
        router._strategy = "latency-based-routing"
        router._router = None
        router._litellm_available = False
        router._stats = {}
        router._learner = None

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "ls -la /tmp"},
            "eval_count": 10,
            "prompt_eval_count": 20,
        }

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENROUTER_API_KEY", None)
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post.return_value = mock_response
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client

                resp = await router.completion("list files", task="coding")
                assert resp.success
                assert resp.content == "ls -la /tmp"
                assert resp.task == "coding"
                assert "ollama/" in resp.model

    @pytest.mark.asyncio
    async def test_openrouter_with_fallback_to_ollama(self):
        from nlp2cmd.llm.router import LLMRouter

        router = LLMRouter.__new__(LLMRouter)
        router._verbose = False
        router._config = {}
        router._strategy = "latency-based-routing"
        router._router = None
        router._litellm_available = False
        router._stats = {}
        router._learner = None

        # First call (OpenRouter) fails, second (Ollama) succeeds
        fail_response = MagicMock()
        fail_response.status_code = 500
        fail_response.text = "Internal Server Error"

        ok_response = MagicMock()
        ok_response.status_code = 200
        ok_response.json.return_value = {
            "message": {"content": "SELECT * FROM users;"},
            "eval_count": 5,
            "prompt_eval_count": 15,
        }

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post.side_effect = [fail_response, ok_response]
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client

                resp = await router.completion("SQL query for users", task="coding")
                assert resp.success
                assert resp.fallback_used
                assert "ollama/" in resp.model

    @pytest.mark.asyncio
    async def test_auto_completion_classifies_and_routes(self):
        from nlp2cmd.llm.router import LLMRouter

        router = LLMRouter.__new__(LLMRouter)
        router._verbose = False
        router._config = {}
        router._strategy = "latency-based-routing"
        router._router = None
        router._litellm_available = False
        router._stats = {}
        router._learner = None

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "docker ps -a"},
            "eval_count": 5,
            "prompt_eval_count": 10,
        }

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENROUTER_API_KEY", None)
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post.return_value = mock_response
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client

                resp = await router.auto_completion("pokaż kontenery docker")
                assert resp.success
                # Should classify as coding (docker keyword)
                assert resp.task == "coding"


# ---------------------------------------------------------------------------
# Config validation test
# ---------------------------------------------------------------------------

class TestConfigYaml:
    """Validate the litellm_config.yaml structure."""

    def test_config_yaml_is_valid(self):
        import yaml

        config_path = Path(__file__).resolve().parent.parent.parent / "config" / "litellm_config.yaml"
        if not config_path.exists():
            pytest.skip("config/litellm_config.yaml not found")

        with open(config_path) as f:
            cfg = yaml.safe_load(f)

        assert "model_list" in cfg
        assert "router_settings" in cfg
        assert "litellm_settings" in cfg
        assert "routes" in cfg

        # Verify all required task types have at least one model
        required_tasks = {"vision", "coding", "text", "polish", "repair", "validation", "fast", "planning"}
        configured_tasks = {m["model_name"] for m in cfg["model_list"]}
        missing = required_tasks - configured_tasks
        assert not missing, f"Missing task models in config: {missing}"

        # Verify each model has litellm_params
        for m in cfg["model_list"]:
            assert "litellm_params" in m, f"Model {m.get('model_name')} missing litellm_params"
            assert "model" in m["litellm_params"], f"Model {m.get('model_name')} missing model ID"

    def test_config_has_fallbacks(self):
        import yaml

        config_path = Path(__file__).resolve().parent.parent.parent / "config" / "litellm_config.yaml"
        if not config_path.exists():
            pytest.skip("config/litellm_config.yaml not found")

        with open(config_path) as f:
            cfg = yaml.safe_load(f)

        fallbacks = cfg.get("litellm_settings", {}).get("fallbacks", [])
        assert len(fallbacks) > 0, "No fallbacks configured"

    def test_config_has_routes(self):
        import yaml

        config_path = Path(__file__).resolve().parent.parent.parent / "config" / "litellm_config.yaml"
        if not config_path.exists():
            pytest.skip("config/litellm_config.yaml not found")

        with open(config_path) as f:
            cfg = yaml.safe_load(f)

        routes = cfg.get("routes", [])
        assert len(routes) > 0, "No routes configured"
        for route in routes:
            assert "route_name" in route
            assert "utterances" in route
            assert "model" in route
            assert "threshold" in route

    def test_vision_models_include_qwen_vl(self):
        import yaml

        config_path = Path(__file__).resolve().parent.parent.parent / "config" / "litellm_config.yaml"
        if not config_path.exists():
            pytest.skip("config/litellm_config.yaml not found")

        with open(config_path) as f:
            cfg = yaml.safe_load(f)

        vision_models = [
            m["litellm_params"]["model"]
            for m in cfg["model_list"]
            if m["model_name"] == "vision"
        ]
        # Should include Qwen2.5-VL
        qwen_vl = [m for m in vision_models if "qwen" in m.lower() and "vl" in m.lower()]
        assert len(qwen_vl) > 0, f"No Qwen VL model in vision list: {vision_models}"


# ---------------------------------------------------------------------------
# Repr test
# ---------------------------------------------------------------------------

class TestRepr:
    def test_repr(self):
        from nlp2cmd.llm.router import LLMRouter

        router = LLMRouter.__new__(LLMRouter)
        router._verbose = False
        router._config = {}
        router._strategy = "latency-based-routing"
        router._router = None
        router._litellm_available = False
        router._stats = {}
        router._learner = None

        r = repr(router)
        assert "LLMRouter" in r
        assert "fallback-mode" in r
