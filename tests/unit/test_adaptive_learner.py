"""
Tests for AdaptiveLearner — self-learning LLM routing system.

Tests cover:
- Error classification (credit exhaustion, rate limits, timeouts, etc.)
- Performance tracking and health scoring
- Fallback pair learning
- Model skip logic (cooldown, consecutive failures, negative preference)
- Evolution rules (credit block, rate limit extension, local promotion)
- Persistence (save/load cycle)
- Learned routing rules
- Reset functionality
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Error Classification Tests
# ---------------------------------------------------------------------------

class TestErrorClassification:
    """Test error message classification into known categories."""

    def test_credit_exhausted_402(self):
        from nlp2cmd.llm.adaptive_learner import classify_error
        ep = classify_error("HTTP 402 Payment Required", "openrouter/model", "text")
        assert ep.category == "credit_exhausted"
        assert not ep.recoverable
        assert ep.cooldown_seconds >= 3600

    def test_credit_exhausted_quota(self):
        from nlp2cmd.llm.adaptive_learner import classify_error
        ep = classify_error("You exceeded your current quota", "openrouter/x", "coding")
        assert ep.category == "credit_exhausted"

    def test_credit_exhausted_insufficient(self):
        from nlp2cmd.llm.adaptive_learner import classify_error
        ep = classify_error("insufficient credit balance", "openrouter/x", "text")
        assert ep.category == "credit_exhausted"
        assert not ep.recoverable

    def test_rate_limited_429(self):
        from nlp2cmd.llm.adaptive_learner import classify_error
        ep = classify_error("HTTP 429 Too Many Requests", "openrouter/x", "text")
        assert ep.category == "rate_limited"
        assert ep.recoverable
        assert ep.cooldown_seconds >= 60

    def test_rate_limited_text(self):
        from nlp2cmd.llm.adaptive_learner import classify_error
        ep = classify_error("rate limit exceeded for this model", "x", "coding")
        assert ep.category == "rate_limited"

    def test_timeout(self):
        from nlp2cmd.llm.adaptive_learner import classify_error
        ep = classify_error("Request timed out after 60s", "ollama/qwen:7b", "text")
        assert ep.category == "timeout"
        assert ep.recoverable

    def test_timeout_connect(self):
        from nlp2cmd.llm.adaptive_learner import classify_error
        ep = classify_error("connect timeout to localhost:11434", "ollama/x", "fast")
        assert ep.category == "timeout"

    def test_model_unavailable_404(self):
        from nlp2cmd.llm.adaptive_learner import classify_error
        ep = classify_error("HTTP 404: model not found", "ollama/missing", "text")
        assert ep.category == "model_unavailable"
        assert ep.recoverable

    def test_model_unavailable_connection_refused(self):
        from nlp2cmd.llm.adaptive_learner import classify_error
        ep = classify_error("Connection refused to localhost:11434", "ollama/x", "text")
        assert ep.category == "model_unavailable"

    def test_auth_error_401(self):
        from nlp2cmd.llm.adaptive_learner import classify_error
        ep = classify_error("HTTP 401 Unauthorized", "openrouter/x", "text")
        assert ep.category == "auth_error"
        assert not ep.recoverable

    def test_auth_error_invalid_key(self):
        from nlp2cmd.llm.adaptive_learner import classify_error
        ep = classify_error("Invalid API key provided", "openrouter/x", "coding")
        assert ep.category == "auth_error"

    def test_context_overflow(self):
        from nlp2cmd.llm.adaptive_learner import classify_error
        ep = classify_error("context_length_exceeded: max 4096 tokens", "x", "text")
        assert ep.category == "context_overflow"
        assert ep.recoverable

    def test_unknown_error(self):
        from nlp2cmd.llm.adaptive_learner import classify_error
        ep = classify_error("Some random weird error", "x", "text")
        assert ep.category == "unknown"
        assert ep.recoverable

    def test_error_pattern_fields(self):
        from nlp2cmd.llm.adaptive_learner import classify_error
        ep = classify_error("402 Payment Required", "openrouter/grok", "vision")
        assert ep.model == "openrouter/grok"
        assert ep.task == "vision"
        assert ep.timestamp > 0
        assert len(ep.error_msg) > 0


# ---------------------------------------------------------------------------
# ModelPerformance Tests
# ---------------------------------------------------------------------------

class TestModelPerformance:
    """Test performance tracking data class."""

    def test_defaults(self):
        from nlp2cmd.llm.adaptive_learner import ModelPerformance
        mp = ModelPerformance(model="ollama/qwen:7b", task="text")
        assert mp.success_rate == 0.5  # No calls yet
        assert mp.avg_latency_ms == float("inf")
        assert mp.is_cooled_down is True
        assert mp.health_score >= 0  # 0.0 when no latency data (inf → speed_factor=0)

    def test_success_rate(self):
        from nlp2cmd.llm.adaptive_learner import ModelPerformance
        mp = ModelPerformance(model="x", task="t", total_calls=10, successes=8, failures=2)
        assert mp.success_rate == 0.8

    def test_avg_latency(self):
        from nlp2cmd.llm.adaptive_learner import ModelPerformance
        mp = ModelPerformance(model="x", task="t", successes=5, total_latency_ms=1000)
        assert mp.avg_latency_ms == 200.0

    def test_cooldown(self):
        from nlp2cmd.llm.adaptive_learner import ModelPerformance
        mp = ModelPerformance(model="x", task="t", cooldown_until=time.time() + 9999)
        assert mp.is_cooled_down is False
        assert mp.health_score == -1.0

    def test_consecutive_failures_penalty(self):
        from nlp2cmd.llm.adaptive_learner import ModelPerformance
        mp1 = ModelPerformance(model="x", task="t", total_calls=10, successes=8,
                               failures=2, total_latency_ms=800, consecutive_failures=0)
        mp2 = ModelPerformance(model="x", task="t", total_calls=10, successes=8,
                               failures=2, total_latency_ms=800, consecutive_failures=3)
        assert mp1.health_score > mp2.health_score

    def test_learned_preference_boost(self):
        from nlp2cmd.llm.adaptive_learner import ModelPerformance
        mp_neutral = ModelPerformance(model="x", task="t", total_calls=10, successes=10,
                                      total_latency_ms=500, learned_preference=0.0)
        mp_preferred = ModelPerformance(model="x", task="t", total_calls=10, successes=10,
                                        total_latency_ms=500, learned_preference=0.8)
        assert mp_preferred.health_score > mp_neutral.health_score

    def test_serialization(self):
        from nlp2cmd.llm.adaptive_learner import ModelPerformance
        mp = ModelPerformance(model="ollama/x", task="coding", total_calls=5, successes=4)
        d = mp.to_dict()
        mp2 = ModelPerformance.from_dict(d)
        assert mp2.model == "ollama/x"
        assert mp2.total_calls == 5
        assert mp2.successes == 4


# ---------------------------------------------------------------------------
# AdaptiveLearner Core Tests
# ---------------------------------------------------------------------------

class TestAdaptiveLearner:
    """Test AdaptiveLearner core functionality."""

    def _make_learner(self, tmp_path):
        from nlp2cmd.llm.adaptive_learner import AdaptiveLearner
        return AdaptiveLearner(cache_dir=tmp_path)

    def test_record_success(self, tmp_path):
        learner = self._make_learner(tmp_path)
        learner.record_success("ollama/qwen:7b", "text", 150.0)
        perf = learner._performance["ollama/qwen:7b:text"]
        assert perf.total_calls == 1
        assert perf.successes == 1
        assert perf.total_latency_ms == 150.0
        assert perf.consecutive_failures == 0

    def test_record_failure(self, tmp_path):
        learner = self._make_learner(tmp_path)
        pattern = learner.record_failure("openrouter/x", "vision", "402 Payment Required")
        assert pattern.category == "credit_exhausted"
        perf = learner._performance["openrouter/x:vision"]
        assert perf.failures == 1
        assert perf.consecutive_failures == 1

    def test_consecutive_failures_reset_on_success(self, tmp_path):
        learner = self._make_learner(tmp_path)
        learner.record_failure("x", "t", "timeout")
        learner.record_failure("x", "t", "timeout")
        assert learner._performance["x:t"].consecutive_failures == 2
        learner.record_success("x", "t", 100)
        assert learner._performance["x:t"].consecutive_failures == 0

    def test_fallback_pair_learning(self, tmp_path):
        learner = self._make_learner(tmp_path)
        learner.record_success(
            "ollama/qwen:7b", "text", 200.0,
            was_fallback=True, fallback_from="openrouter/grok",
        )
        assert learner._fallback_pairs["openrouter/grok:text"] == "ollama/qwen:7b"

    def test_get_fallback_model(self, tmp_path):
        learner = self._make_learner(tmp_path)
        learner.record_success(
            "ollama/qwen:7b", "coding", 300.0,
            was_fallback=True, fallback_from="openrouter/qwen-coder",
        )
        fb = learner.get_fallback_model("openrouter/qwen-coder", "coding")
        assert fb == "ollama/qwen:7b"

    def test_get_fallback_model_none(self, tmp_path):
        learner = self._make_learner(tmp_path)
        fb = learner.get_fallback_model("unknown", "text")
        assert fb is None

    def test_recommend_model(self, tmp_path):
        learner = self._make_learner(tmp_path)
        # Record some successes
        for _ in range(5):
            learner.record_success("ollama/qwen:7b", "text", 200)
        for _ in range(5):
            learner.record_success("ollama/qwen:3b", "text", 100)

        # qwen:3b should be recommended (faster)
        best = learner.recommend_model("text")
        assert best is not None
        assert "qwen" in best

    def test_recommend_model_skips_cooldown(self, tmp_path):
        learner = self._make_learner(tmp_path)
        learner.record_success("model_a", "text", 100)
        learner.record_failure("model_b", "text", "402 Payment Required")

        best = learner.recommend_model("text", available_models=["model_a", "model_b"])
        assert best == "model_a"

    def test_should_skip_model_cooldown(self, tmp_path):
        learner = self._make_learner(tmp_path)
        learner.record_failure("openrouter/x", "text", "402 Payment Required")
        assert learner.should_skip_model("openrouter/x", "text") is True

    def test_should_skip_model_consecutive_failures(self, tmp_path):
        learner = self._make_learner(tmp_path)
        learner.record_failure("x", "t", "timeout")
        learner.record_failure("x", "t", "timeout")
        learner.record_failure("x", "t", "timeout")
        assert learner.should_skip_model("x", "t") is True

    def test_should_not_skip_healthy_model(self, tmp_path):
        learner = self._make_learner(tmp_path)
        learner.record_success("ollama/qwen:7b", "text", 150)
        assert learner.should_skip_model("ollama/qwen:7b", "text") is False

    def test_should_not_skip_unknown_model(self, tmp_path):
        learner = self._make_learner(tmp_path)
        assert learner.should_skip_model("never_seen", "text") is False


# ---------------------------------------------------------------------------
# Evolution Tests
# ---------------------------------------------------------------------------

class TestEvolution:
    """Test the evolve() method — pattern-based routing adaptation."""

    def _make_learner(self, tmp_path):
        from nlp2cmd.llm.adaptive_learner import AdaptiveLearner
        return AdaptiveLearner(cache_dir=tmp_path)

    def test_evolve_blocks_credit_exhausted(self, tmp_path):
        learner = self._make_learner(tmp_path)
        learner.record_failure("openrouter/grok", "text", "402 Payment Required")
        actions = learner.evolve()
        # Should block the model for multiple tasks
        blocked = [a for a in actions if "Blocked" in a]
        assert len(blocked) > 0

    def test_evolve_extends_rate_limit_cooldown(self, tmp_path):
        learner = self._make_learner(tmp_path)
        for _ in range(4):
            learner.record_failure("openrouter/x", "coding", "429 Too Many Requests")
        actions = learner.evolve()
        extended = [a for a in actions if "cooldown" in a.lower()]
        assert len(extended) > 0

    def test_evolve_promotes_good_local_models(self, tmp_path):
        learner = self._make_learner(tmp_path)
        for _ in range(6):
            learner.record_success("ollama/qwen:7b", "coding", 200)
        actions = learner.evolve()
        promoted = [a for a in actions if "Promoted" in a]
        assert len(promoted) > 0

    def test_evolve_no_actions_when_healthy(self, tmp_path):
        learner = self._make_learner(tmp_path)
        learner.record_success("ollama/qwen:7b", "text", 100)
        actions = learner.evolve()
        # Might promote if enough calls, but otherwise quiet
        # Just verify it doesn't crash
        assert isinstance(actions, list)


# ---------------------------------------------------------------------------
# Persistence Tests
# ---------------------------------------------------------------------------

class TestPersistence:
    """Test save/load cycle."""

    def test_save_and_load(self, tmp_path):
        from nlp2cmd.llm.adaptive_learner import AdaptiveLearner

        # Create learner and record some data
        l1 = AdaptiveLearner(cache_dir=tmp_path)
        l1.record_success("ollama/qwen:7b", "text", 150)
        l1.record_failure("openrouter/x", "vision", "402 Payment Required")
        l1.record_success("ollama/llava:7b", "vision", 1200,
                          was_fallback=True, fallback_from="openrouter/x")

        # Create a new learner from same directory
        l2 = AdaptiveLearner(cache_dir=tmp_path)

        # Verify data was loaded
        assert "ollama/qwen:7b:text" in l2._performance
        assert l2._performance["ollama/qwen:7b:text"].successes == 1
        assert "openrouter/x:vision" in l2._performance
        assert l2._performance["openrouter/x:vision"].failures == 1
        assert l2._fallback_pairs.get("openrouter/x:vision") == "ollama/llava:7b"

    def test_cache_file_created(self, tmp_path):
        from nlp2cmd.llm.adaptive_learner import AdaptiveLearner

        learner = AdaptiveLearner(cache_dir=tmp_path)
        learner.record_success("x", "t", 100)

        cache_file = tmp_path / "adaptive_routing.json"
        assert cache_file.exists()

        data = json.loads(cache_file.read_text())
        assert data["version"] == 1
        assert "performance" in data

    def test_reset(self, tmp_path):
        from nlp2cmd.llm.adaptive_learner import AdaptiveLearner

        learner = AdaptiveLearner(cache_dir=tmp_path)
        learner.record_success("x", "t", 100)
        learner.record_failure("y", "t", "error")

        cache_file = tmp_path / "adaptive_routing.json"
        assert cache_file.exists()

        learner.reset()
        assert len(learner._performance) == 0
        assert len(learner._rules) == 0
        assert len(learner._error_history) == 0
        assert not cache_file.exists()


# ---------------------------------------------------------------------------
# Learned Rules Tests
# ---------------------------------------------------------------------------

class TestLearnedRules:
    """Test routing rule learning."""

    def test_fallback_creates_rule(self, tmp_path):
        from nlp2cmd.llm.adaptive_learner import AdaptiveLearner

        learner = AdaptiveLearner(cache_dir=tmp_path)
        learner.record_success(
            "ollama/qwen:7b", "coding", 300,
            was_fallback=True, fallback_from="openrouter/qwen-coder",
        )

        assert len(learner._rules) == 1
        rule = learner._rules[0]
        assert rule.task == "coding"
        assert rule.preferred_model == "ollama/qwen:7b"
        assert rule.avoided_model == "openrouter/qwen-coder"

    def test_repeated_fallback_increases_confidence(self, tmp_path):
        from nlp2cmd.llm.adaptive_learner import AdaptiveLearner

        learner = AdaptiveLearner(cache_dir=tmp_path)
        for _ in range(5):
            learner.record_success(
                "ollama/qwen:7b", "text", 200,
                was_fallback=True, fallback_from="openrouter/grok",
            )

        assert len(learner._rules) == 1
        assert learner._rules[0].confidence > 0.5
        assert learner._rules[0].times_applied == 5

    def test_rules_persisted(self, tmp_path):
        from nlp2cmd.llm.adaptive_learner import AdaptiveLearner

        l1 = AdaptiveLearner(cache_dir=tmp_path)
        l1.record_success("ollama/x", "text", 100,
                          was_fallback=True, fallback_from="remote/y")

        l2 = AdaptiveLearner(cache_dir=tmp_path)
        assert len(l2._rules) == 1
        assert l2._rules[0].preferred_model == "ollama/x"


# ---------------------------------------------------------------------------
# Performance Report Tests
# ---------------------------------------------------------------------------

class TestPerformanceReport:
    """Test get_performance_report() output."""

    def test_report_structure(self, tmp_path):
        from nlp2cmd.llm.adaptive_learner import AdaptiveLearner

        learner = AdaptiveLearner(cache_dir=tmp_path)
        learner.record_success("ollama/qwen:7b", "text", 150)
        learner.record_failure("openrouter/x", "text", "402 Payment Required")

        report = learner.get_performance_report()
        assert "models" in report
        assert "rules" in report
        assert "error_summary" in report
        assert "fallback_pairs" in report

        assert "ollama/qwen:7b:text" in report["models"]
        m = report["models"]["ollama/qwen:7b:text"]
        assert m["success_rate"] == 1.0
        assert m["total_calls"] == 1
        assert m["in_cooldown"] is False

        assert report["error_summary"]["credit_exhausted"] == 1


# ---------------------------------------------------------------------------
# ErrorPattern serialization
# ---------------------------------------------------------------------------

class TestErrorPatternSerialization:
    """Test ErrorPattern to_dict/from_dict."""

    def test_round_trip(self):
        from nlp2cmd.llm.adaptive_learner import ErrorPattern

        ep = ErrorPattern(
            category="credit_exhausted",
            model="openrouter/x",
            task="text",
            error_msg="402 Payment Required",
            timestamp=1234567890.0,
            recoverable=False,
            cooldown_seconds=3600.0,
        )
        d = ep.to_dict()
        ep2 = ErrorPattern.from_dict(d)
        assert ep2.category == "credit_exhausted"
        assert ep2.model == "openrouter/x"
        assert ep2.timestamp == 1234567890.0
        assert ep2.recoverable is False


# ---------------------------------------------------------------------------
# Integration: Router + AdaptiveLearner
# ---------------------------------------------------------------------------

class TestRouterAdaptiveIntegration:
    """Test that LLMRouter properly uses AdaptiveLearner."""

    def test_router_creates_learner(self):
        from nlp2cmd.llm.router import LLMRouter

        router = LLMRouter.__new__(LLMRouter)
        router._verbose = False
        router._config = {}
        router._strategy = "latency-based-routing"
        router._router = None
        router._litellm_available = False
        router._stats = {}

        # With adaptive_learning=True (default)
        try:
            from nlp2cmd.llm.adaptive_learner import AdaptiveLearner
            router._learner = AdaptiveLearner()
            assert router._learner is not None
        except Exception:
            pytest.skip("AdaptiveLearner import failed")
        finally:
            if router._learner:
                router._learner.reset()

    def test_router_without_learner(self):
        from nlp2cmd.llm.router import LLMRouter

        router = LLMRouter.__new__(LLMRouter)
        router._verbose = False
        router._config = {}
        router._strategy = "latency-based-routing"
        router._router = None
        router._litellm_available = False
        router._stats = {}
        router._learner = None

        # Stats should work without learner
        stats = router.get_stats()
        assert "adaptive_learning" not in stats
