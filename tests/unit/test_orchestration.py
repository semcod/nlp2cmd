"""Tests for nlp2cmd.orchestration — dynamic orchestration engine + reflection."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nlp2cmd.orchestration.engine import (
    Orchestrator,
    TaskResult,
    TaskSchema,
    StepDef,
    StepResult,
    StepStatus,
    _parse_json,
)
from nlp2cmd.orchestration.reflection import (
    ResultAnalyzer,
    ReflectionResult,
    ReflectionVerdict,
    has_error_signals,
    classify_error,
    _parse_json_safe,
)


# =====================================================================
# Reflection module tests
# =====================================================================

class TestHasErrorSignals:
    def test_empty_string(self):
        assert has_error_signals("") is False

    def test_clean_output(self):
        assert has_error_signals("Hello World\nDone!") is False

    def test_traceback(self):
        assert has_error_signals("Traceback (most recent call last):\n  File...") is True

    def test_syntax_error(self):
        assert has_error_signals("SyntaxError: invalid syntax") is True

    def test_exit_code_1(self):
        assert has_error_signals("[Execution complete with exit code 1]") is True

    def test_segfault(self):
        assert has_error_signals("Segmentation fault (core dumped)") is True

    def test_case_insensitive(self):
        assert has_error_signals("TYPEERROR: cannot add int and str") is True

    def test_compilation_error(self):
        assert has_error_signals("Compilation error on line 5") is True


class TestClassifyError:
    def test_none_for_empty(self):
        assert classify_error("") is None

    def test_syntax_error(self):
        assert classify_error("SyntaxError: unexpected EOF") == "syntax_error"

    def test_indentation_error(self):
        assert classify_error("IndentationError: unexpected indent") == "syntax_error"

    def test_name_error(self):
        assert classify_error("NameError: name 'x' is not defined") == "reference_error"

    def test_type_error(self):
        assert classify_error("TypeError: unsupported operand") == "type_error"

    def test_import_error(self):
        assert classify_error("ImportError: No module named 'foo'") == "import_error"

    def test_runtime_error(self):
        assert classify_error("Traceback (most recent call last):\n  File...") == "runtime_error"

    def test_compilation_error(self):
        assert classify_error("Compilation error in main.c") == "compilation_error"

    def test_crash(self):
        assert classify_error("Segmentation fault (core dumped)") == "crash"

    def test_nonzero_exit(self):
        assert classify_error("[exit code 1]") == "nonzero_exit"

    def test_clean_output(self):
        assert classify_error("Hello World\n42") is None


class TestResultAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return ResultAnalyzer(router=None)

    @pytest.mark.asyncio
    async def test_error_signals_fast_path(self, analyzer):
        result = await analyzer.analyze(
            goal="compute fibonacci",
            output="Traceback (most recent call last):\n  SyntaxError: invalid",
        )
        assert result.verdict == ReflectionVerdict.ERROR
        assert result.should_retry is True
        assert result.error_type == "syntax_error"

    @pytest.mark.asyncio
    async def test_empty_output(self, analyzer):
        result = await analyzer.analyze(
            goal="print hello",
            output="",
        )
        assert result.verdict == ReflectionVerdict.INVALID
        assert result.should_retry is True

    @pytest.mark.asyncio
    async def test_clean_output_heuristic(self, analyzer):
        result = await analyzer.analyze(
            goal="print numbers",
            output="1 2 3 4 5",
        )
        assert result.verdict == ReflectionVerdict.VALID
        assert result.confidence > 0.0

    @pytest.mark.asyncio
    async def test_suggest_repair_without_router(self, analyzer):
        """Without a router, suggest_repair should return None."""
        analyzer_no_router = ResultAnalyzer(router=None)
        analyzer_no_router._router = None
        analyzer_no_router._auto_init_router = False  # prevent lazy LLM init
        suggestion = await analyzer_no_router.suggest_repair(
            goal="test", output="error", code="print(x)",
        )
        assert suggestion is None


class TestParseJsonSafe:
    def test_direct_json(self):
        assert _parse_json_safe('{"a": 1}') == {"a": 1}

    def test_with_preamble(self):
        assert _parse_json_safe('Here is the result: {"b": 2}') == {"b": 2}

    def test_invalid(self):
        assert _parse_json_safe("not json at all") is None

    def test_empty(self):
        assert _parse_json_safe("") is None


# =====================================================================
# Engine module tests
# =====================================================================

class TestParseJson:
    def test_direct(self):
        assert _parse_json('{"x": 1}') == {"x": 1}

    def test_markdown_fenced(self):
        assert _parse_json('```json\n{"x": 2}\n```') == {"x": 2}

    def test_with_preamble(self):
        assert _parse_json('Here is the plan:\n{"goal": "test"}') == {"goal": "test"}

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _parse_json("no json here")

    def test_nested(self):
        result = _parse_json('{"steps": [{"a": 1}, {"b": 2}]}')
        assert len(result["steps"]) == 2


class TestStepDef:
    def test_to_dict(self):
        s = StepDef("navigate", "Go to URL", {"url": "https://example.com"})
        d = s.to_dict()
        assert d["action"] == "navigate"
        assert d["description"] == "Go to URL"
        assert d["url"] == "https://example.com"

    def test_minimal(self):
        s = StepDef("inspect")
        assert s.action == "inspect"
        assert s.description == ""
        assert s.params == {}


class TestTaskSchema:
    def test_basic(self):
        schema = TaskSchema(
            goal="test",
            domain="code_editor",
            steps=[StepDef("navigate"), StepDef("inspect")],
        )
        assert len(schema.steps) == 2
        assert schema.domain == "code_editor"


class TestOrchestrator:
    @pytest.fixture
    def orch(self):
        return Orchestrator(router=None, handlers={})

    def test_init(self, orch):
        assert orch._handlers == {}
        assert orch._context == {}

    def test_register_handler(self, orch):
        async def my_handler(step, ctx):
            return StepResult(StepStatus.SUCCESS, {"val": 42})

        orch.register_handler("test_action", my_handler)
        assert "test_action" in orch._handlers

    @pytest.mark.asyncio
    async def test_heuristic_plan(self, orch):
        schema = orch._heuristic_plan("write fibonacci")
        assert schema.goal == "write fibonacci"
        assert len(schema.steps) >= 1

    @pytest.mark.asyncio
    async def test_sanitize_code_editor(self, orch):
        schema = TaskSchema(
            goal="test",
            domain="code_editor",
            steps=[StepDef("generate_code"), StepDef("inject_code")],
            metadata={"language": "python"},
        )
        sanitized = orch._sanitize_schema(schema)
        actions = [s.action for s in sanitized.steps]
        # Must start with navigate + dismiss + inspect
        assert actions[0] == "navigate"
        # Must end with capture_output / screenshot
        assert "capture_output" in actions
        assert "screenshot" in actions

    @pytest.mark.asyncio
    async def test_execute_with_handler(self):
        """With router=None, heuristic plan is used (inspect + generate_code)."""
        results = []

        async def inspect_handler(step, ctx):
            results.append("inspected")
            return StepResult(StepStatus.SUCCESS, {"page": "loaded"})

        async def gen_handler(step, ctx):
            results.append("generated")
            return StepResult(StepStatus.SUCCESS, {"generated_code": "print(1)"})

        orch = Orchestrator(
            router=None,
            handlers={
                "inspect": inspect_handler,
                "generate_code": gen_handler,
            },
        )
        # Force no router so heuristic plan is used
        orch._router = None
        schema = orch._heuristic_plan("test task")
        # Manually execute the plan steps
        for step_def in schema.steps:
            handler = orch._handlers.get(step_def.action)
            if handler:
                r = await handler(step_def, orch._context)
                orch._context.update(r.data)
        assert len(results) == 2
        assert "inspected" in results
        assert "generated" in results

    @pytest.mark.asyncio
    async def test_step_failure_returns_error(self):
        async def failing_handler(step, ctx):
            return StepResult(StepStatus.FAILED, error="boom")

        orch = Orchestrator(
            router=None,
            handlers={"inspect": failing_handler, "generate_code": failing_handler},
        )
        orch._router = None  # force heuristic plan
        result = await orch.run("test task")
        assert result.success is False
        assert result.error is not None
        # Error could be "boom" or "No handler" depending on plan
        assert "boom" in result.error or "No handler" in result.error

    @pytest.mark.asyncio
    async def test_context_accumulation(self):
        """Context from step A should be visible to step B."""
        async def step_a(step, ctx):
            return StepResult(StepStatus.SUCCESS, {"key_a": "val_a"})

        async def step_b(step, ctx):
            return StepResult(StepStatus.SUCCESS, {"key_b": "val_b"})

        orch = Orchestrator(
            router=None,
            handlers={"inspect": step_a, "generate_code": step_b},
        )
        orch._router = None  # force heuristic plan
        # Execute heuristic plan directly to avoid LLM interference
        orch._context = {"goal": "test"}
        schema = orch._heuristic_plan("test")
        for step_def in schema.steps:
            handler = orch._handlers.get(step_def.action)
            if handler:
                r = await handler(step_def, orch._context)
                orch._context.update(r.data)
        assert orch._context.get("key_a") == "val_a"
        assert orch._context.get("key_b") == "val_b"


# =====================================================================
# Router integration test
# =====================================================================

class TestRouterDecisionOrchestrator:
    def test_dynamic_orchestrator_in_routing_decisions(self):
        from nlp2cmd.router import RoutingDecision
        assert hasattr(RoutingDecision, "DYNAMIC_ORCHESTRATOR")
        assert RoutingDecision.DYNAMIC_ORCHESTRATOR.value == "dynamic_orchestrator"

    def test_router_default_routes_to_orchestrator(self):
        from nlp2cmd.router import DecisionRouter
        router = DecisionRouter()
        result = router.route(
            intent="custom_complex_task",
            entities={"x": 1},
            text="do something complex with reflection",
            confidence=0.9,
        )
        # Should route to DYNAMIC_ORCHESTRATOR since orchestration module is importable
        assert result.decision.value in ("dynamic_orchestrator", "llm_planner")

    def test_simple_intent_still_direct(self):
        from nlp2cmd.router import DecisionRouter, RoutingDecision
        router = DecisionRouter()
        result = router.route(
            intent="select",
            entities={"table": "users"},
            text="show users",
            confidence=0.95,
        )
        assert result.decision == RoutingDecision.DIRECT


# =====================================================================
# Handlers module tests
# =====================================================================

class TestHandlers:
    def test_register_default_handlers(self):
        from nlp2cmd.orchestration.handlers import register_default_handlers
        orch = Orchestrator(router=None)
        orch._router = None
        register_default_handlers(orch)
        expected = {
            "shell_exec", "generate_code", "wait", "inspect",
            "navigate", "dismiss_popups", "inject_code",
            "find_and_click", "capture_output", "screenshot", "validate",
        }
        assert expected.issubset(set(orch._handlers.keys()))

    @pytest.mark.asyncio
    async def test_handle_wait(self):
        from nlp2cmd.orchestration.handlers import handle_wait
        import time
        t0 = time.time()
        result = await handle_wait(StepDef("wait", params={"seconds": 0.1}), {})
        assert result.status == StepStatus.SUCCESS
        assert time.time() - t0 >= 0.1

    @pytest.mark.asyncio
    async def test_handle_shell_exec_success(self):
        from nlp2cmd.orchestration.handlers import handle_shell_exec
        result = await handle_shell_exec(
            StepDef("shell_exec", params={"command": "echo hello"}), {},
        )
        assert result.status == StepStatus.SUCCESS
        assert "hello" in result.data.get("output", "")

    @pytest.mark.asyncio
    async def test_handle_shell_exec_failure(self):
        from nlp2cmd.orchestration.handlers import handle_shell_exec
        result = await handle_shell_exec(
            StepDef("shell_exec", params={"command": "false"}), {},
        )
        assert result.status == StepStatus.FAILED
        assert result.data.get("exit_code") != 0

    @pytest.mark.asyncio
    async def test_handle_shell_exec_no_command(self):
        from nlp2cmd.orchestration.handlers import handle_shell_exec
        result = await handle_shell_exec(
            StepDef("shell_exec", params={}), {},
        )
        assert result.status == StepStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_handle_inspect_no_page(self):
        from nlp2cmd.orchestration.handlers import handle_inspect
        result = await handle_inspect(StepDef("inspect"), {})
        assert result.status == StepStatus.SUCCESS
        assert result.data.get("page_schema") == {}

    @pytest.mark.asyncio
    async def test_handle_navigate_no_page(self):
        from nlp2cmd.orchestration.handlers import handle_navigate
        result = await handle_navigate(
            StepDef("navigate", params={"url": "https://example.com"}), {},
        )
        assert result.status == StepStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_handle_navigate_no_url(self):
        from nlp2cmd.orchestration.handlers import handle_navigate
        result = await handle_navigate(
            StepDef("navigate", params={}), {"page": "mock"},
        )
        assert result.status == StepStatus.FAILED

    @pytest.mark.asyncio
    async def test_handle_inject_code_no_page(self):
        from nlp2cmd.orchestration.handlers import handle_inject_code
        result = await handle_inject_code(
            StepDef("inject_code"), {"generated_code": "print(1)"},
        )
        assert result.status == StepStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_handle_inject_code_no_code(self):
        from nlp2cmd.orchestration.handlers import handle_inject_code
        from unittest.mock import AsyncMock, MagicMock
        mock_page = MagicMock()
        result = await handle_inject_code(StepDef("inject_code"), {"page": mock_page})
        assert result.status == StepStatus.FAILED

    @pytest.mark.asyncio
    async def test_handle_screenshot_no_page(self):
        from nlp2cmd.orchestration.handlers import handle_screenshot
        result = await handle_screenshot(StepDef("screenshot"), {})
        assert result.status == StepStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_handle_dismiss_popups_no_page(self):
        from nlp2cmd.orchestration.handlers import handle_dismiss_popups
        result = await handle_dismiss_popups(StepDef("dismiss_popups"), {})
        assert result.status == StepStatus.SUCCESS
        assert result.data.get("popups_dismissed") == []

    @pytest.mark.asyncio
    async def test_handle_capture_output_no_page(self):
        from nlp2cmd.orchestration.handlers import handle_capture_output
        result = await handle_capture_output(StepDef("capture_output"), {})
        assert result.status == StepStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_handle_find_and_click_no_page(self):
        from nlp2cmd.orchestration.handlers import handle_find_and_click
        result = await handle_find_and_click(
            StepDef("find_and_click", params={"purpose": "run"}), {},
        )
        assert result.status == StepStatus.SKIPPED

    def test_normalize_purpose(self):
        from nlp2cmd.orchestration.handlers import _normalize_purpose
        assert _normalize_purpose("run") == "run"
        assert _normalize_purpose("Run the code") == "run"
        assert _normalize_purpose("execute program") == "run"
        assert _normalize_purpose("uruchom") == "run"
        assert _normalize_purpose("submit form") == "submit"
        assert _normalize_purpose("unknown thing") == "run"  # default

    def test_strip_code_fences(self):
        from nlp2cmd.orchestration.handlers import _strip_code_fences
        assert _strip_code_fences("```python\nprint(1)\n```") == "print(1)"
        assert _strip_code_fences("print(1)") == "print(1)"
        assert _strip_code_fences("```\ncode\n```") == "code"


class TestComplexPlannerOrchestrator:
    """Test that ComplexCommandPlanner now delegates to Orchestrator."""

    @pytest.mark.asyncio
    async def test_orchestrator_plan_called(self):
        from nlp2cmd.automation.complex_planner import ComplexCommandPlanner
        planner = ComplexCommandPlanner(api_key=None)
        plan = await planner.plan("write fibonacci in python")
        # Should get a plan from orchestrator or template fallback
        assert plan is not None
        assert len(plan.steps) > 0
        assert plan.source in ("orchestrator", "template", "llm", "none")

    @pytest.mark.asyncio
    async def test_template_still_works_as_fallback(self):
        from nlp2cmd.automation.complex_planner import ComplexCommandPlanner
        planner = ComplexCommandPlanner(api_key=None)
        # "narysuj okrąg" should match DRAWING_PATTERNS template
        plan = await planner.plan("narysuj okrąg na jspaint")
        assert plan is not None
        assert len(plan.steps) > 0


# =====================================================================
# Metrics module tests
# =====================================================================

class TestMetricsCollector:
    @pytest.fixture
    def tmp_ws(self, tmp_path):
        return tmp_path / ".nlp2cmd_test"

    @pytest.fixture
    def mc(self, tmp_ws):
        from nlp2cmd.orchestration.metrics import MetricsCollector
        return MetricsCollector(workspace=tmp_ws)

    def test_start_and_finish_task(self, mc):
        tid = mc.start_task("test goal", domain="code_editor")
        assert tid.startswith("task_")
        mc.record_step("inspect", "success", duration_ms=100)
        mc.record_step("generate_code", "success", duration_ms=1500, tokens_out=500)
        mc.record_step("inject_code", "failed", error="no page")
        result = mc.finish_task(success=False, plan_source="llm")
        assert result.success is False
        assert result.steps_total == 3
        assert result.steps_succeeded == 2
        assert result.steps_failed == 1
        assert result.total_tokens_out == 500
        assert result.llm_calls == 1
        assert result.domain == "code_editor"
        assert len(result.decision_path) == 3

    def test_summary_persists(self, mc, tmp_ws):
        mc.start_task("goal 1")
        mc.record_step("inspect", "success")
        mc.finish_task(success=True)

        mc.start_task("goal 2")
        mc.record_step("generate", "failed", error="timeout")
        mc.finish_task(success=False)

        summary = mc.get_summary()
        assert summary["total_tasks"] == 2
        assert summary["successful_tasks"] == 1
        assert summary["failed_tasks"] == 1
        assert summary["success_rate"] == 0.5

    def test_jsonl_log(self, mc, tmp_ws):
        mc.start_task("task A")
        mc.finish_task(success=True)
        mc.start_task("task B")
        mc.finish_task(success=True)

        tasks = mc.get_recent_tasks()
        assert len(tasks) == 2
        assert tasks[0]["goal"] == "task A"
        assert tasks[1]["goal"] == "task B"

    def test_record_generated_function(self, mc):
        mc.start_task("gen test")
        mc.record_generated_function("func_abc123")
        result = mc.finish_task(success=True)
        assert "func_abc123" in result.generated_functions

    def test_domain_stats(self, mc):
        mc.start_task("shell task", domain="shell")
        mc.finish_task(success=True)
        mc.start_task("code task", domain="code_editor")
        mc.finish_task(success=True)
        summary = mc.get_summary()
        assert "shell" in summary["domains"]
        assert "code_editor" in summary["domains"]
        assert summary["domains"]["shell"]["tasks"] == 1


class TestPathOptimizer:
    @pytest.fixture
    def po(self, tmp_path):
        from nlp2cmd.orchestration.metrics import PathOptimizer
        return PathOptimizer(workspace=tmp_path / ".nlp2cmd_test")

    def test_lookup_empty(self, po):
        assert po.lookup("nonexistent goal") is None

    def test_record_and_lookup(self, po):
        from nlp2cmd.orchestration.metrics import TaskMetric
        task = TaskMetric(
            task_id="t1", goal="write fibonacci", goal_hash="",
            domain="code_editor", success=True,
            total_duration_ms=5000, total_tokens_in=100, total_tokens_out=500,
            decision_path=["navigate", "inspect", "generate_code", "inject_code"],
            step_metrics=[
                {"action": "navigate", "status": "success"},
                {"action": "inspect", "status": "success"},
                {"action": "generate_code", "status": "success"},
            ],
        )
        po.record_success(task)
        result = po.lookup("write fibonacci")
        assert result is not None
        assert result.success_count == 1
        assert result.domain == "code_editor"

    def test_increment_success_count(self, po):
        from nlp2cmd.orchestration.metrics import TaskMetric
        task = TaskMetric(
            task_id="t1", goal="write fibonacci", goal_hash="",
            domain="code_editor", success=True,
            total_duration_ms=5000, total_tokens_in=100, total_tokens_out=500,
            decision_path=["navigate", "generate_code"],
            step_metrics=[{"action": "navigate", "status": "success"}],
        )
        po.record_success(task)
        po.record_success(task)
        result = po.lookup("write fibonacci")
        assert result.success_count == 2

    def test_stats(self, po):
        stats = po.get_stats()
        assert stats["total_paths"] == 0

    def test_failed_task_not_recorded(self, po):
        from nlp2cmd.orchestration.metrics import TaskMetric
        task = TaskMetric(
            task_id="t1", goal="bad task", goal_hash="",
            success=False, decision_path=["inspect"],
            step_metrics=[],
        )
        po.record_success(task)
        assert po.lookup("bad task") is None


class TestFunctionCache:
    @pytest.fixture
    def fc(self, tmp_path):
        from nlp2cmd.orchestration.metrics import FunctionCache
        return FunctionCache(workspace=tmp_path / ".nlp2cmd_test")

    def test_store_and_get_code(self, fc):
        code = "def fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a+b\n    return a"
        func_id = fc.store(code, "py", name="fibonacci", description="Fibonacci function")
        assert func_id

        retrieved = fc.get_code(func_id)
        assert retrieved == code

    def test_store_js(self, fc):
        js_code = "function inject() { document.querySelector('.cm-content').click(); }"
        func_id = fc.store(js_code, "js", name="inject_cm6",
                           tags=["browser", "injection"])
        assert func_id

        results = fc.lookup(language="js")
        assert len(results) == 1
        assert results[0]["language"] == "js"

    def test_dedup_on_same_code(self, fc):
        code = "print('hello')"
        id1 = fc.store(code, "py", name="hello1")
        id2 = fc.store(code, "py", name="hello2")
        assert id1 == id2  # same code → same ID

        stats = fc.get_stats()
        assert stats["total_functions"] == 1
        assert stats["py_functions"] == 1

    def test_lookup_by_goal_hash(self, fc):
        from nlp2cmd.orchestration.metrics import _hash_goal
        gh = _hash_goal("write fibonacci")
        fc.store("def fib(): pass", "py", name="fib", goal_hash=gh)
        fc.store("console.log(1)", "js", name="log", goal_hash="other")

        results = fc.lookup(goal_hash=gh)
        assert len(results) == 1
        assert results[0]["name"] == "fib"

    def test_lookup_by_tags(self, fc):
        fc.store("def a(): pass", "py", name="a", tags=["devops", "shell"])
        fc.store("def b(): pass", "py", name="b", tags=["browser"])

        results = fc.lookup(tags=["devops"])
        assert len(results) == 1
        assert results[0]["name"] == "a"

    def test_stats(self, fc):
        fc.store("x = 1", "py", name="x")
        fc.store("var y = 2;", "js", name="y")
        stats = fc.get_stats()
        assert stats["total_functions"] == 2
        assert stats["js_functions"] == 1
        assert stats["py_functions"] == 1

    def test_get_code_nonexistent(self, fc):
        assert fc.get_code("nonexistent_id") is None


class TestHashGoal:
    def test_deterministic(self):
        from nlp2cmd.orchestration.metrics import _hash_goal
        h1 = _hash_goal("write fibonacci in python")
        h2 = _hash_goal("write fibonacci in python")
        assert h1 == h2

    def test_case_insensitive(self):
        from nlp2cmd.orchestration.metrics import _hash_goal
        h1 = _hash_goal("Write Fibonacci")
        h2 = _hash_goal("write fibonacci")
        assert h1 == h2

    def test_strips_articles(self):
        from nlp2cmd.orchestration.metrics import _hash_goal
        h1 = _hash_goal("write a fibonacci program")
        h2 = _hash_goal("write fibonacci program")
        assert h1 == h2

    def test_different_goals_different_hashes(self):
        from nlp2cmd.orchestration.metrics import _hash_goal
        h1 = _hash_goal("fibonacci")
        h2 = _hash_goal("quicksort")
        assert h1 != h2
