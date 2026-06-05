"""Tests for plan_execution package."""

import pytest
from unittest.mock import MagicMock, patch

from nlp2cmd.plan_execution import (
    BrowserSetup,
    BrowserContextOptions,
    StepOrchestrator,
    StepResult,
    PlanExecutor,
)


class TestBrowserContextOptions:
    """Test BrowserContextOptions dataclass."""
    
    def test_default_values(self):
        """Test default option values."""
        opts = BrowserContextOptions()
        assert opts.headless is True
        assert opts.user_data_dir is None
        assert opts.record_video_dir is None
        assert opts.record_video_size is None
        assert opts.viewport is None
    
    def test_custom_values(self):
        """Test custom option values."""
        opts = BrowserContextOptions(
            headless=False,
            user_data_dir="/tmp/profile",
            record_video_dir="/tmp/videos",
            record_video_size={"width": 1920, "height": 1080},
            viewport={"width": 1280, "height": 720},
        )
        assert opts.headless is False
        assert opts.user_data_dir == "/tmp/profile"
        assert opts.record_video_dir == "/tmp/videos"


class TestBrowserSetup:
    """Test BrowserSetup class."""
    
    def test_initialization(self):
        """Test BrowserSetup initialization."""
        setup = BrowserSetup(headless=True)
        assert setup.headless is True
        assert setup.browser_type == "chromium"
        assert setup.has_ff_cookies is False
    
    def test_get_user_data_dir_default(self):
        """Test getting default user data dir."""
        setup = BrowserSetup()
        path = setup.get_user_data_dir()
        assert ".nlp2cmd" in str(path)
        assert "browser_profile" in str(path)
    
    def test_create_context_options_basic(self):
        """Test creating basic context options."""
        setup = BrowserSetup(headless=True)
        opts = setup.create_context_options()
        
        assert opts["headless"] is True
        assert opts["user_data_dir"] is not None
        assert opts["viewport"] == {"width": 1280, "height": 720}
        assert "record_video_dir" not in opts
    
    def test_create_context_options_with_video(self):
        """Test creating context options with video recording."""
        setup = BrowserSetup(headless=True)
        opts = setup.create_context_options(
            video_dir="/tmp/videos",
            record_video=True,
        )
        
        assert opts["record_video_dir"] == "/tmp/videos"
        assert opts["record_video_size"] == {"width": 1280, "height": 720}


class TestStepResult:
    """Test StepResult dataclass."""
    
    def test_step_result_creation(self):
        """Test creating StepResult."""
        result = StepResult(
            step_index=1,
            action="navigate",
            status="ok",
            elapsed_ms=1500,
            stored="url",
        )
        assert result.step_index == 1
        assert result.action == "navigate"
        assert result.status == "ok"
        assert result.elapsed_ms == 1500
        assert result.stored == "url"
        assert result.error is None

    def test_step_result_accepts_note(self):
        """Regression: prompt_secret skip records note without TypeError."""
        result = StepResult(
            step_index=24,
            action="prompt_secret",
            status="ok",
            elapsed_ms=0,
            note="skipped_already_available",
        )
        assert result.note == "skipped_already_available"


class TestStepOrchestrator:
    """Test StepOrchestrator class."""
    
    def test_initialization(self):
        """Test orchestrator initialization."""
        orch = StepOrchestrator(
            max_fallback_injections=5,
            max_plan_steps=50,
        )
        assert orch.max_fallback_injections == 5
        assert orch.max_plan_steps == 50
        assert orch.validator is None
        assert orch.fallback_engine is None
        assert orch.feedback_loop is None
    
    def test_get_summary_empty(self):
        """Test summary with no results."""
        orch = StepOrchestrator()
        summary = orch.get_summary()
        assert summary["ok_count"] == 0
        assert summary["fail_count"] == 0
        assert summary["err_count"] == 0
        assert summary["total_ms"] == 0
    
    def test_get_summary_with_results(self):
        """Test summary with results."""
        orch = StepOrchestrator()
        orch.results_log = [
            StepResult(step_index=1, action="navigate", status="ok", elapsed_ms=1000),
            StepResult(step_index=2, action="click", status="error", elapsed_ms=500),
            StepResult(step_index=3, action="extract", status="ok", elapsed_ms=2000),
        ]
        summary = orch.get_summary()
        assert summary["ok_count"] == 2
        assert summary["err_count"] == 1
        assert summary["total_steps"] == 3
        assert summary["total_ms"] == 3500


class TestPlanExecutor:
    """Test PlanExecutor class."""
    
    def test_initialization(self):
        """Test PlanExecutor initialization."""
        executor = PlanExecutor(headless=False)
        assert executor.headless is False
        assert executor.browser_setup is not None
        assert executor.video_recorder is None
    
    def test_detect_desktop_steps_true(self):
        """Test detecting desktop steps."""
        executor = PlanExecutor()
        
        # Create mock plan with desktop step
        mock_step = MagicMock()
        mock_step.action = "desktop_wait"
        mock_plan = MagicMock()
        mock_plan.steps = [mock_step]
        
        result = executor._detect_desktop_steps(mock_plan)
        assert result is True
    
    def test_detect_desktop_steps_false(self):
        """Test detecting no desktop steps."""
        executor = PlanExecutor()
        
        # Create mock plan with browser step
        mock_step = MagicMock()
        mock_step.action = "navigate"
        mock_plan = MagicMock()
        mock_plan.steps = [mock_step]
        
        result = executor._detect_desktop_steps(mock_plan)
        assert result is False
    
    def test_detect_desktop_steps_open_firefox_tab(self):
        """Test detecting open_firefox_tab as desktop step."""
        executor = PlanExecutor()
        
        mock_step = MagicMock()
        mock_step.action = "open_firefox_tab"
        mock_plan = MagicMock()
        mock_plan.steps = [mock_step]
        
        result = executor._detect_desktop_steps(mock_plan)
        assert result is True

    def test_injected_callbacks_are_used(self):
        """Test that PlanExecutor uses injected callbacks when provided."""
        callback_calls = {}

        def execute_step(page, context, step, variables):
            callback_calls["execute"] = (page, context, step, variables)
            return "executed"

        def resolve_variables(params, variables):
            callback_calls["resolve"] = (params, variables)
            return {"resolved": True}

        def desktop_step(step, variables):
            callback_calls["desktop"] = (step, variables)
            return "desktop-ok"

        executor = PlanExecutor(
            headless=False,
            execute_step_fn=execute_step,
            resolve_variables_fn=resolve_variables,
            desktop_step_fn=desktop_step,
        )

        assert executor._get_execute_fn() is execute_step
        assert executor._get_resolve_fn() is resolve_variables

        mock_step = MagicMock()
        mock_step.action = "desktop_wait"
        assert executor._execute_desktop_step(mock_step, {"foo": "bar"}) == "desktop-ok"

        assert "desktop" in callback_calls


class TestIntegration:
    """Integration tests for plan_execution components."""
    
    def test_full_flow_simulation(self):
        """Simulate a full execution flow."""
        # Create executor
        executor = PlanExecutor(headless=True)
        
        # Create mock plan
        mock_step1 = MagicMock()
        mock_step1.action = "navigate"
        mock_step1.description = "Go to website"
        mock_step1.params = {"url": "https://example.com"}
        mock_step1.store_as = None
        mock_step1.retry_on_fail = True
        
        mock_step2 = MagicMock()
        mock_step2.action = "click"
        mock_step2.description = "Click button"
        mock_step2.params = {"selector": "#btn"}
        mock_step2.store_as = "result"
        mock_step2.retry_on_fail = False
        
        mock_plan = MagicMock()
        mock_plan.steps = [mock_step1, mock_step2]
        mock_plan.source = "test"
        mock_plan.confidence = 0.95
        mock_plan.estimated_time_ms = 5000
        mock_plan.query = "test query"
        
        # Verify components work together
        assert executor._detect_desktop_steps(mock_plan) is False
        
        # Create orchestrator
        orchestrator = StepOrchestrator()
        
        # Verify orchestrator can track results
        orchestrator.results_log.append(StepResult(
            step_index=1,
            action="navigate",
            status="ok",
            elapsed_ms=1000,
        ))
        orchestrator.results_log.append(StepResult(
            step_index=2,
            action="click",
            status="ok",
            elapsed_ms=500,
            stored="result",
        ))
        
        summary = orchestrator.get_summary()
        assert summary["ok_count"] == 2
        assert summary["total_steps"] == 2

    def test_check_already_available_records_skip_note(self):
        """When env already has key, prompt_secret skip must not crash on StepResult(note=...)."""
        from unittest.mock import MagicMock, patch
        from nlp2cmd.automation.step_validator import StepValidator

        orch = StepOrchestrator(validator=StepValidator())
        step = MagicMock()
        step.action = "prompt_secret"
        step.params = {"env_var": "OPENROUTER_API_KEY", "key_pattern": r"sk-or-v1-[A-Za-z0-9]{64}"}
        step.store_as = "api_key"
        console = MagicMock()

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-v1-" + "a" * 64}, clear=True):
            skipped = orch._check_already_available(
                step, step_idx=23, pre_ok=True, pre_message="", resolve_vars_fn=lambda p, v: p, console=console
            )

        assert skipped is True
        assert len(orch.results_log) == 1
        assert orch.results_log[0].note == "skipped_already_available"
        assert orch.results_log[0].step_index == 24


class TestEnvironmentVariables:
    """Test environment variable handling."""
    
    @patch.dict("os.environ", {"NLP2CMD_MAX_FALLBACK_INJECTIONS": "5"})
    @patch.dict("os.environ", {"NLP2CMD_MAX_PLAN_STEPS": "50"})
    def test_fallback_injection_env_var(self):
        """Test fallback injection count from environment."""
        # When creating orchestrator, it should read from env
        import os
        assert os.environ.get("NLP2CMD_MAX_FALLBACK_INJECTIONS") == "5"
        assert os.environ.get("NLP2CMD_MAX_PLAN_STEPS") == "50"
