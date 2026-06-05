"""Tests for canvas_planner package."""

import pytest
from unittest.mock import MagicMock, patch

from nlp2cmd.canvas_planner import (
    CanvasPlannerBase,
    CanvasPlanResult,
    RuleBasedCanvasPlanner,
    LLMCanvasPlanner,
    VectorDBPlanner,
    BlueprintPlanner,
    CanvasPlanningOrchestrator,
)
from nlp2cmd.canvas_planner.json_parse import parse_canvas_steps_json
from nlp2cmd.canvas_planner.config import resolve_canvas_model, CanvasLLMConfig


class TestCanvasLLMConfig:
    def test_resolve_canvas_model_prefers_llm_model(self, monkeypatch):
        monkeypatch.setenv("LLM_MODEL", "openrouter/test-model")
        monkeypatch.setenv("NLP2CMD_PLANNER_MODEL", "qwen2.5:3b")
        assert resolve_canvas_model() == "openrouter/test-model"

    def test_blueprints_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("CANVAS_USE_BLUEPRINTS", raising=False)
        cfg = CanvasLLMConfig.from_env()
        assert cfg.use_blueprints is False
        assert cfg.use_rule_fallback is True


class TestCanvasPlanResult:
    """Test CanvasPlanResult dataclass."""
    
    def test_creation(self):
        """Test creating CanvasPlanResult."""
        result = CanvasPlanResult(
            steps=[{"action": "navigate", "params": {}, "description": "Go"}],
            confidence=0.85,
            source="test",
            estimated_time_ms=1000,
        )
        assert result.confidence == 0.85
        assert result.source == "test"
        assert len(result.steps) == 1
        assert result.success is True
    
    def test_to_action_steps(self):
        """Test conversion to ActionStep objects."""
        result = CanvasPlanResult(
            steps=[
                {"action": "navigate", "params": {"url": "test"}, "description": "Go", "store_as": "url"},
            ],
            confidence=0.85,
            source="test",
            estimated_time_ms=1000,
        )
        # Without action_planner import, returns empty list
        steps = result.to_action_steps()
        # Should handle gracefully even without ActionStep
        assert isinstance(steps, list)


class TestCanvasPlannerBase:
    """Test CanvasPlannerBase class."""
    
    def test_initialization(self):
        """Test base initialization."""
        base = CanvasPlannerBase(ollama_url="http://test:11434", model="test-model")
        assert base.ollama_url == "http://test:11434"
        assert base.model == "test-model"
    
    def test_is_available(self):
        """Test is_available defaults to True."""
        base = CanvasPlannerBase()
        assert base.is_available() is True
    
    def test_extract_object_name_polish(self):
        """Test extracting object name from Polish query."""
        base = CanvasPlannerBase()
        result = base._extract_object_name("narysuj czerwoną gwiazdę")
        assert result == "czerwoną gwiazdę"
    
    def test_extract_object_name_english(self):
        """Test extracting object name from English query."""
        base = CanvasPlannerBase()
        result = base._extract_object_name("draw a red star")
        assert result == "a red star"
    
    def test_extract_object_name_no_match(self):
        """Test extracting object name when no match."""
        base = CanvasPlannerBase()
        result = base._extract_object_name("random text without any sketching verbs")
        assert result == "obiekt"
    
    def test_extract_canvas_url(self):
        """Test extracting canvas URL."""
        base = CanvasPlannerBase()
        result = base._extract_canvas_url("draw on jspaint.app")
        assert result == "https://jspaint.app"
    
    def test_extract_canvas_url_default(self):
        """Test default canvas URL."""
        base = CanvasPlannerBase()
        result = base._extract_canvas_url("draw something")
        assert result == "https://jspaint.app"


class TestRuleBasedCanvasPlanner:
    """Test RuleBasedCanvasPlanner."""
    
    def test_initialization(self):
        """Test planner initialization."""
        planner = RuleBasedCanvasPlanner()
        assert planner.is_available() is True
    
    def test_plan_rabbit(self):
        """Test generating plan for rabbit."""
        planner = RuleBasedCanvasPlanner()
        result = planner.plan("query", "narysuj zająca", "https://jspaint.app")
        
        assert result is not None
        assert result.confidence == 0.75
        assert result.source == "canvas_rule_based"
        assert len(result.steps) > 0
        
        # Check for rabbit-specific steps
        actions = [s["action"] for s in result.steps]
        assert "navigate" in actions
        assert "draw_filled_ellipse" in actions
        assert "screenshot" in actions
    
    def test_plan_car(self):
        """Test generating plan for car."""
        planner = RuleBasedCanvasPlanner()
        result = planner.plan("query", "narysuj samochód", "https://jspaint.app")
        
        assert result is not None
        assert result.source == "canvas_rule_based"
    
    def test_plan_house(self):
        """Test generating plan for house."""
        planner = RuleBasedCanvasPlanner()
        result = planner.plan("query", "narysuj dom", "https://jspaint.app")
        
        assert result is not None
        assert result.source == "canvas_rule_based"
    
    def test_plan_sun(self):
        """Test generating plan for sun."""
        planner = RuleBasedCanvasPlanner()
        result = planner.plan("query", "narysuj słońce", "https://jspaint.app")
        
        assert result is not None
        actions = [s["action"] for s in result.steps]
        assert "draw_line" in actions  # Sun has rays (lines)
    
    def test_plan_tree(self):
        """Test generating plan for tree."""
        planner = RuleBasedCanvasPlanner()
        result = planner.plan("query", "narysuj drzewo", "https://jspaint.app")
        
        assert result is not None
        actions = [s["action"] for s in result.steps]
        assert "draw_filled_ellipse" in actions
    
    def test_plan_generic(self):
        """Test generating plan for unknown object."""
        planner = RuleBasedCanvasPlanner()
        result = planner.plan("query", "narysuj xyz123", "https://jspaint.app")
        
        assert result is not None
        assert result.source == "canvas_rule_based"


class TestLLMCanvasPlanner:
    """Test LLMCanvasPlanner."""
    
    def test_initialization(self):
        """Test planner initialization."""
        planner = LLMCanvasPlanner(ollama_url="http://test:11434", model="test-model")
        assert planner.ollama_url == "http://test:11434"
        assert planner.model == "test-model"
    
    def test_parse_response_valid(self):
        """Test parsing valid JSON response."""
        planner = LLMCanvasPlanner()
        raw = '[{"action": "set_color", "params": {"color": "#FF0000"}}, {"action": "draw_circle", "params": {}}]'
        result = planner._parse_response(raw)
        
        assert result is not None
        assert len(result) == 2
        assert result[0]["action"] == "set_color"
    
    def test_parse_response_with_markdown(self):
        """Test parsing JSON with markdown fences."""
        planner = LLMCanvasPlanner()
        raw = '```json\n[{"action": "set_color", "params": {}}, {"action": "draw", "params": {}}]\n```'
        result = planner._parse_response(raw)
        
        assert result is not None
        assert len(result) == 2
    
    def test_parse_response_with_trailing_comma(self):
        """Test parsing JSON with trailing commas."""
        planner = LLMCanvasPlanner()
        raw = '[{"action": "set_color", "params": {"color": "#FF0000"},}, {"action": "draw", "params": {},}]'
        result = planner._parse_response(raw)
        
        assert result is not None
        assert len(result) == 2
    
    def test_parse_response_invalid(self):
        """Test parsing invalid JSON."""
        planner = LLMCanvasPlanner()
        raw = "not valid json"
        result = planner._parse_response(raw)
        
        assert result is None

    def test_parse_response_salvages_truncated_array(self):
        """Truncated LLM output should still yield complete leading steps."""
        raw = (
            '[{"action":"set_color","params":{"color":"#FF0000"}},'
            '{"action":"draw_filled_circle","params":{"radius":10,"offset":[0,0]}},'
            '{"action":"set_color","params":{"color":"#00'
        )
        result = parse_canvas_steps_json(raw)
        assert result is not None
        assert len(result) == 2
        assert result[0]["action"] == "set_color"
        assert result[1]["action"] == "draw_filled_circle"
    
    def test_build_full_plan(self):
        """Test building full plan from LLM steps."""
        planner = LLMCanvasPlanner()
        steps_data = [{"action": "set_color", "params": {"color": "#FF0000"}}]
        result = planner._build_full_plan("draw cat", steps_data, "cat")
        
        assert len(result) >= 4  # navigate, wait, center, step, screenshot
        actions = [s["action"] for s in result]
        assert "navigate" in actions
        assert "wait_for_canvas" in actions
        assert "set_color" in actions
        assert "screenshot" in actions
    
    def test_build_full_plan_with_existing_screenshot(self):
        """Test that existing screenshot is not duplicated."""
        planner = LLMCanvasPlanner()
        steps_data = [{"action": "screenshot", "params": {"suffix": "test"}}]
        result = planner._build_full_plan("draw", steps_data, "test")
        
        screenshots = [s for s in result if s["action"] == "screenshot"]
        assert len(screenshots) == 1  # Only one screenshot


class TestVectorDBPlanner:
    """Test VectorDBPlanner."""
    
    def test_initialization(self):
        """Test planner initialization."""
        planner = VectorDBPlanner()
        # Availability depends on import
        assert isinstance(planner.is_available(), bool)
    
    def test_extract_search_query(self):
        """Test extracting search query."""
        planner = VectorDBPlanner()
        result = planner._extract_search_query("narysuj lisa na jspaint.app")
        assert "lisa" in result
    
    def test_plan_not_available(self):
        """Test plan returns None when vector store unavailable."""
        planner = VectorDBPlanner()
        if not planner.is_available():
            result = planner.plan("query", "narysuj test", "https://jspaint.app")
            assert result is None


class TestBlueprintPlanner:
    """Test BlueprintPlanner."""
    
    def test_initialization(self):
        """Test planner initialization."""
        planner = BlueprintPlanner()
        assert planner.is_available() is True
    
    def test_plan_import_error(self):
        """Test plan handles import error gracefully."""
        planner = BlueprintPlanner()
        # Should return None when drawing_blueprints not available
        with patch.dict("sys.modules", {"nlp2cmd.automation.drawing_blueprints": None}):
            result = planner.plan("query", "narysuj test", "https://jspaint.app")
            assert result is None


class TestCanvasPlanningOrchestrator:
    """Test CanvasPlanningOrchestrator."""
    
    def test_initialization(self):
        """Test orchestrator initialization."""
        orch = CanvasPlanningOrchestrator(ollama_url="http://test", model="test-model")
        assert orch.ollama_url == "http://test"
        assert orch.model == "test-model"
        assert orch.blueprint is not None
        assert orch.rule is not None
    
    def test_plan_uses_llm_first(self):
        """Test that plan prefers LLM before fallbacks."""
        orch = CanvasPlanningOrchestrator()

        expected_result = CanvasPlanResult(
            steps=[{"action": "test", "params": {}, "description": "Test"}],
            confidence=0.8,
            source="canvas_llm",
            estimated_time_ms=1000,
        )
        orch.llm.plan = MagicMock(return_value=expected_result)
        orch.rule.plan = MagicMock(return_value=None)
        orch.blueprint.plan = MagicMock(return_value=None)
        orch.vector.plan = MagicMock(return_value=None)

        result = orch.plan("narysuj test", "narysuj test")

        assert result is not None
        assert result.source == "canvas_llm"
        orch.rule.plan.assert_not_called()

    def test_plan_falls_back_to_rule_when_llm_fails(self):
        """Test rule fallback when LLM and vector DB fail."""
        orch = CanvasPlanningOrchestrator()

        expected_result = CanvasPlanResult(
            steps=[{"action": "test", "params": {}, "description": "Test"}],
            confidence=0.75,
            source="canvas_rule_based",
            estimated_time_ms=1000,
        )
        orch.llm.plan = MagicMock(return_value=None)
        orch.vector.plan = MagicMock(return_value=None)
        orch.rule.plan = MagicMock(return_value=expected_result)

        result = orch.plan("narysuj test", "narysuj test")

        assert result is not None
        assert result.source == "canvas_rule_based"
    
    def test_plan_all_fail(self):
        """Test that plan returns None when all planners fail."""
        orch = CanvasPlanningOrchestrator()
        
        orch.blueprint.plan = MagicMock(return_value=None)
        orch.vector.plan = MagicMock(return_value=None)
        orch.llm.plan = MagicMock(return_value=None)
        orch.rule.plan = MagicMock(return_value=None)
        
        with patch.object(orch, '_try_template', return_value=None):
            result = orch.plan("narysuj test", "narysuj test")
        
        assert result is None
    
    def test_try_vector_db_quality_check(self):
        """Test vector DB quality check (minimum 8 drawing steps)."""
        orch = CanvasPlanningOrchestrator()
        
        # Mock vector planner with insufficient steps
        low_quality_result = CanvasPlanResult(
            steps=[
                {"action": "navigate", "params": {}, "description": "Go"},
                {"action": "draw_filled_circle", "params": {}, "description": "Circle"},
            ],
            confidence=0.9,
            source="vector_db",
            estimated_time_ms=1000,
        )
        orch.vector.plan = MagicMock(return_value=low_quality_result)
        orch.vector.is_available = MagicMock(return_value=True)
        
        # Should skip low-quality plan and return None (other planners mocked to fail)
        orch.blueprint.plan = MagicMock(return_value=None)
        orch.llm.plan = MagicMock(return_value=None)
        orch.rule.plan = MagicMock(return_value=None)
        
        with patch.object(orch, '_try_template', return_value=None):
            result = orch._try_vector_db("query", "text", "url")
        
        # Low quality plan should be rejected
        assert result is None
    
    def test_try_vector_db_high_quality(self):
        """Test vector DB accepts high-quality plan."""
        orch = CanvasPlanningOrchestrator()
        
        # Mock vector planner with sufficient steps
        high_quality_steps = [{"action": f"draw_step_{i}", "params": {}, "description": f"Step {i}"} 
                              for i in range(10)]
        high_quality_result = CanvasPlanResult(
            steps=high_quality_steps,
            confidence=0.9,
            source="vector_db",
            estimated_time_ms=1000,
        )
        orch.vector.plan = MagicMock(return_value=high_quality_result)
        orch.vector.is_available = MagicMock(return_value=True)
        
        result = orch._try_vector_db("query", "text", "url")
        
        # High quality plan should be accepted
        assert result is not None
        assert result.source == "vector_db"


class TestIntegration:
    """Integration tests."""
    
    def test_rule_based_full_flow(self):
        """Test complete flow for rule-based planning."""
        orchestrator = CanvasPlanningOrchestrator()
        
        # Use rule-based for a known shape
        result = orchestrator.rule.plan("query", "narysuj zająca", "https://jspaint.app")
        
        assert result is not None
        assert result.success is True
        assert len(result.steps) > 0
        
        # Verify step structure
        for step in result.steps:
            assert "action" in step
            assert "params" in step
            assert "description" in step
    
    def test_object_name_extraction_variations(self):
        """Test various object name extraction patterns."""
        base = CanvasPlannerBase()
        
        test_cases = [
            ("narysuj kota", "kota"),
            ("rysuj psa na jspaint", "psa"),
            ("draw a house", "a house"),
            ("paint something nice", "something nice"),
        ]
        
        for query, expected in test_cases:
            result = base._extract_object_name(query)
            assert expected in result or result == expected
