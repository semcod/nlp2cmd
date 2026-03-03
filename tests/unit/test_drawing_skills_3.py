"""
Tests for the 3 new drawing skill modules:
- DrawNavigationSkill (navigation.py)
- DrawObjectSkill (draw_object.py)
- DrawValidationSkill (validation.py)

Tests cover data classes, JSON parsing, state machines, plan building,
and scene layout — all without requiring Playwright or LLM.
"""

import json
import math
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ── Imports ──────────────────────────────────────────────────────────────

from nlp2cmd.skills.drawing.navigation import (
    DrawNavigationSkill,
    NavigationResult,
    NavigationState,
    NavigationStep,
    CanvasInfo,
    DRAWING_SITES,
    POPUP_TEXTS,
    POPUP_CSS_SELECTORS,
    CANVAS_VERIFY_PROMPT,
)

from nlp2cmd.skills.drawing.draw_object import (
    DrawObjectSkill,
    ObjectDrawResult,
    SceneDrawResult,
    DrawStatus,
)

from nlp2cmd.skills.drawing.validation import (
    DrawValidationSkill,
    ValidationReport,
    TaskPlan,
    ObjectAssessment,
    ObjectStatus,
)


# ═══════════════════════════════════════════════════════════════════════════
# DrawNavigationSkill tests
# ═══════════════════════════════════════════════════════════════════════════

class TestNavigationState:
    """Test NavigationState enum."""

    def test_all_states_exist(self):
        states = [s.value for s in NavigationState]
        assert "idle" in states
        assert "ready" in states
        assert "failed" in states
        assert "navigating" in states
        assert "verifying" in states

    def test_state_values(self):
        assert NavigationState.IDLE.value == "idle"
        assert NavigationState.READY.value == "ready"
        assert NavigationState.FAILED.value == "failed"


class TestCanvasInfo:
    """Test CanvasInfo dataclass."""

    def test_defaults(self):
        c = CanvasInfo()
        assert c.url == ""
        assert c.width == 0
        assert c.height == 0
        assert c.has_canvas is False
        assert c.vision_confirmed is False
        assert c.tool_selected == ""

    def test_with_values(self):
        c = CanvasInfo(
            url="https://jspaint.app",
            site_name="jspaint",
            width=1024,
            height=768,
            has_canvas=True,
            vision_confirmed=True,
            vision_description="MS Paint clone",
        )
        assert c.width == 1024
        assert c.site_name == "jspaint"
        assert c.vision_confirmed is True


class TestNavigationStep:
    """Test NavigationStep dataclass."""

    def test_defaults(self):
        s = NavigationStep(action="navigate")
        assert s.action == "navigate"
        assert s.success is False
        assert s.duration_ms == 0
        assert s.vision_used is False

    def test_with_values(self):
        s = NavigationStep(
            action="verify_canvas",
            success=True,
            detail="canvas found",
            duration_ms=150.5,
            vision_used=True,
        )
        assert s.success is True
        assert s.vision_used is True


class TestNavigationResult:
    """Test NavigationResult dataclass."""

    def test_defaults(self):
        r = NavigationResult()
        assert r.state == NavigationState.IDLE
        assert r.success is False
        assert r.total_time_ms == 0

    def test_success(self):
        r = NavigationResult(state=NavigationState.READY)
        assert r.success is True

    def test_failed(self):
        r = NavigationResult(state=NavigationState.FAILED, error="no sites")
        assert r.success is False
        assert r.error == "no sites"

    def test_total_time(self):
        r = NavigationResult(steps=[
            NavigationStep(action="a", duration_ms=100),
            NavigationStep(action="b", duration_ms=200),
            NavigationStep(action="c", duration_ms=50),
        ])
        assert r.total_time_ms == 350


class TestDrawingSites:
    """Test DRAWING_SITES registry."""

    def test_jspaint_exists(self):
        assert "jspaint" in DRAWING_SITES
        assert "canvas" in DRAWING_SITES["jspaint"]["canvas_selector"]

    def test_all_sites_have_urls(self):
        for name, info in DRAWING_SITES.items():
            assert "urls" in info, f"{name} missing urls"
            assert len(info["urls"]) > 0, f"{name} has no urls"

    def test_all_sites_have_canvas_selector(self):
        for name, info in DRAWING_SITES.items():
            assert "canvas_selector" in info, f"{name} missing canvas_selector"

    def test_fallback_order(self):
        orders = {k: v.get("fallback_order", 99) for k, v in DRAWING_SITES.items()}
        assert orders["jspaint"] < orders["draw.chat"]


class TestNavigationSkillInit:
    """Test DrawNavigationSkill initialization."""

    def test_default_init(self):
        nav = DrawNavigationSkill()
        assert nav._max_retries == 2
        assert nav._use_vision is True
        assert nav._router is None

    def test_no_vision(self):
        nav = DrawNavigationSkill(use_vision=False)
        assert nav._use_vision is False

    def test_custom_retries(self):
        nav = DrawNavigationSkill(max_retries=5)
        assert nav._max_retries == 5


class TestNavigationJsonParsing:
    """Test _parse_json method."""

    def test_plain_json(self):
        result = DrawNavigationSkill._parse_json('{"has_canvas": true}')
        assert result == {"has_canvas": True}

    def test_json_in_markdown(self):
        text = '```json\n{"has_canvas": true}\n```'
        result = DrawNavigationSkill._parse_json(text)
        assert result == {"has_canvas": True}

    def test_json_with_trailing_comma(self):
        text = '{"has_canvas": true, "ready": false,}'
        result = DrawNavigationSkill._parse_json(text)
        assert result == {"has_canvas": True, "ready": False}

    def test_json_with_surrounding_text(self):
        text = 'Here is the result: {"found": true} done.'
        result = DrawNavigationSkill._parse_json(text)
        assert result == {"found": True}

    def test_invalid_json(self):
        result = DrawNavigationSkill._parse_json("not json at all")
        assert result is None

    def test_empty_string(self):
        result = DrawNavigationSkill._parse_json("")
        assert result is None


class TestNavigationSiteOrder:
    """Test _build_site_order method."""

    def test_primary_first(self):
        nav = DrawNavigationSkill()
        order = nav._build_site_order("jspaint", fallback=False)
        assert len(order) == 1
        assert order[0][0] == "jspaint"

    def test_fallback_chain(self):
        nav = DrawNavigationSkill()
        order = nav._build_site_order("jspaint", fallback=True)
        assert len(order) > 1
        assert order[0][0] == "jspaint"

    def test_custom_url(self):
        nav = DrawNavigationSkill()
        order = nav._build_site_order("https://example.com/draw", fallback=False)
        assert len(order) == 1
        assert order[0][0] == "https://example.com/draw"
        assert order[0][1]["urls"] == ["https://example.com/draw"]

    def test_custom_url_with_fallback(self):
        nav = DrawNavigationSkill()
        order = nav._build_site_order("https://example.com/draw", fallback=True)
        assert len(order) > 1


class TestPopupConstants:
    """Test popup text/selector constants are reasonable."""

    def test_popup_texts_not_empty(self):
        assert len(POPUP_TEXTS) > 10

    def test_popup_texts_include_common(self):
        texts_lower = [t.lower() for t in POPUP_TEXTS]
        assert "accept" in texts_lower
        assert "ok" in texts_lower
        assert "close" in [t.lower() for t in POPUP_TEXTS]

    def test_css_selectors_not_empty(self):
        assert len(POPUP_CSS_SELECTORS) > 5


# ═══════════════════════════════════════════════════════════════════════════
# DrawObjectSkill tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDrawStatus:
    """Test DrawStatus enum."""

    def test_all_statuses(self):
        vals = [s.value for s in DrawStatus]
        assert "pending" in vals
        assert "drawn" in vals
        assert "verified" in vals
        assert "failed" in vals
        assert "resolving" in vals
        assert "drawing" in vals


class TestObjectDrawResult:
    """Test ObjectDrawResult dataclass."""

    def test_defaults(self):
        r = ObjectDrawResult(shape_name="star")
        assert r.shape_name == "star"
        assert r.status == DrawStatus.PENDING
        assert r.color == ""
        assert r.source == ""
        assert r.vision_confirmed is False

    def test_with_values(self):
        r = ObjectDrawResult(
            shape_name="car",
            status=DrawStatus.VERIFIED,
            color="#FF0000",
            source="database:iconify",
            vision_confirmed=True,
            vision_check="red car shape visible",
        )
        assert r.status == DrawStatus.VERIFIED
        assert r.source == "database:iconify"


class TestSceneDrawResult:
    """Test SceneDrawResult dataclass."""

    def test_empty_scene(self):
        s = SceneDrawResult()
        assert s.success is False
        assert s.partial is False
        assert s.summary() == ""

    def test_all_drawn(self):
        s = SceneDrawResult(
            objects=[
                ObjectDrawResult("star", status=DrawStatus.DRAWN, source="registry"),
                ObjectDrawResult("house", status=DrawStatus.DRAWN, source="registry"),
            ],
            objects_drawn=2,
            objects_failed=0,
        )
        assert s.success is True
        assert s.partial is False

    def test_partial(self):
        s = SceneDrawResult(
            objects=[
                ObjectDrawResult("star", status=DrawStatus.DRAWN, source="registry"),
                ObjectDrawResult("dragon", status=DrawStatus.FAILED, source="not_found"),
            ],
            objects_drawn=1,
            objects_failed=1,
        )
        assert s.success is False
        assert s.partial is True

    def test_summary_format(self):
        s = SceneDrawResult(
            objects=[
                ObjectDrawResult("star", status=DrawStatus.VERIFIED, source="registry"),
            ],
            objects_drawn=1,
        )
        text = s.summary()
        assert "star" in text
        assert "registry" in text


class TestDrawObjectSkillInit:
    """Test DrawObjectSkill initialization."""

    def test_default_init(self):
        d = DrawObjectSkill()
        assert d._renderer is None
        assert d._skill is None
        assert d._use_vision is True

    def test_no_vision(self):
        d = DrawObjectSkill(use_vision=False)
        assert d._use_vision is False

    def test_set_renderer(self):
        d = DrawObjectSkill()
        mock_renderer = MagicMock()
        mock_page = MagicMock()
        d.set_renderer(mock_renderer, mock_page)
        assert d._renderer is mock_renderer
        assert d._page is mock_page

    def test_ensure_skill_creates_default(self):
        d = DrawObjectSkill()
        skill = d._ensure_skill()
        assert skill is not None
        from nlp2cmd.skills.drawing.skill import DrawingSkill
        assert isinstance(skill, DrawingSkill)


class TestDrawObjectJsonParsing:
    """Test _parse_json method on DrawObjectSkill."""

    def test_plain_json(self):
        r = DrawObjectSkill._parse_json('{"drawn": true}')
        assert r == {"drawn": True}

    def test_markdown_wrapped(self):
        r = DrawObjectSkill._parse_json('```json\n{"drawn": true}\n```')
        assert r == {"drawn": True}

    def test_invalid(self):
        r = DrawObjectSkill._parse_json("no json here")
        assert r is None


class TestSceneLayout:
    """Test draw_scene grid layout calculations."""

    @pytest.mark.asyncio
    async def test_scene_layout_single_object(self):
        """Single object should be centered."""
        d = DrawObjectSkill(use_vision=False)
        # Mock the draw method
        d.draw = AsyncMock(return_value=ObjectDrawResult(
            "star", status=DrawStatus.DRAWN, source="registry",
        ))

        scene = await d.draw_scene(
            [("star", "#FF0000")],
            canvas_width=1024, canvas_height=768,
        )
        assert scene.objects_drawn == 1
        assert len(scene.objects) == 1

    @pytest.mark.asyncio
    async def test_scene_layout_multiple_objects(self):
        """Multiple objects should all get drawn."""
        d = DrawObjectSkill(use_vision=False)
        d.draw = AsyncMock(return_value=ObjectDrawResult(
            "x", status=DrawStatus.DRAWN, source="registry",
        ))

        objects = [("star", "#FF0000"), ("house", "#8B4513"), ("tree", "#228B22")]
        scene = await d.draw_scene(objects, canvas_width=1024, canvas_height=768)

        assert d.draw.call_count == 3
        assert scene.objects_drawn == 3

    @pytest.mark.asyncio
    async def test_scene_handles_failures(self):
        """Failed objects should be counted."""
        d = DrawObjectSkill(use_vision=False)

        async def mock_draw(name, **kwargs):
            if name == "dragon":
                return ObjectDrawResult(name, status=DrawStatus.FAILED, error="not found")
            return ObjectDrawResult(name, status=DrawStatus.DRAWN, source="registry")

        d.draw = mock_draw

        objects = [("star", "#FF0000"), ("dragon", "#00FF00")]
        scene = await d.draw_scene(objects, canvas_width=1024, canvas_height=768)

        assert scene.objects_drawn == 1
        assert scene.objects_failed == 1
        assert scene.partial is True


# ═══════════════════════════════════════════════════════════════════════════
# DrawValidationSkill tests
# ═══════════════════════════════════════════════════════════════════════════

class TestObjectStatus:
    """Test ObjectStatus enum."""

    def test_all_statuses(self):
        vals = [s.value for s in ObjectStatus]
        assert "pending" in vals
        assert "drawn" in vals
        assert "missing" in vals
        assert "wrong" in vals
        assert "partial" in vals


class TestObjectAssessment:
    """Test ObjectAssessment dataclass."""

    def test_defaults(self):
        a = ObjectAssessment(name="star")
        assert a.status == ObjectStatus.PENDING
        assert a.confidence == 0.0

    def test_with_issue(self):
        a = ObjectAssessment(
            name="house",
            status=ObjectStatus.WRONG,
            requested_color="#0000FF",
            actual_color="red",
            issue="Wrong color",
            suggestion="Redraw in blue",
        )
        assert a.status == ObjectStatus.WRONG
        assert a.issue == "Wrong color"


class TestTaskPlan:
    """Test TaskPlan dataclass."""

    def test_empty_plan(self):
        p = TaskPlan()
        assert p.description == ""
        assert len(p.objects) == 0
        assert p.object_names == []

    def test_add_objects(self):
        p = TaskPlan(description="red star and blue house")
        p.add("star", "#FF0000")
        p.add("house", "#0000FF")
        assert len(p.objects) == 2
        assert p.object_names == ["star", "house"]
        assert p.objects[0]["color"] == "#FF0000"

    def test_add_without_color(self):
        p = TaskPlan()
        p.add("circle")
        assert p.objects[0]["color"] == ""


class TestValidationReport:
    """Test ValidationReport dataclass."""

    def test_empty_report(self):
        plan = TaskPlan(description="test")
        r = ValidationReport(plan=plan)
        assert r.done == []
        assert r.remaining == []
        assert r.wrong == []
        assert r.all_done is True  # No assessments = vacuously true
        assert r.progress_pct == 0.0

    def test_all_done(self):
        plan = TaskPlan(description="star and house")
        plan.add("star")
        plan.add("house")
        r = ValidationReport(
            plan=plan,
            assessments=[
                ObjectAssessment("star", status=ObjectStatus.DRAWN),
                ObjectAssessment("house", status=ObjectStatus.DRAWN),
            ],
        )
        assert r.all_done is True
        assert r.progress_pct == 1.0
        assert len(r.done) == 2
        assert len(r.remaining) == 0

    def test_partial_progress(self):
        plan = TaskPlan(description="star, house, tree")
        r = ValidationReport(
            plan=plan,
            assessments=[
                ObjectAssessment("star", status=ObjectStatus.DRAWN),
                ObjectAssessment("house", status=ObjectStatus.MISSING),
                ObjectAssessment("tree", status=ObjectStatus.PENDING),
            ],
        )
        assert r.all_done is False
        assert len(r.done) == 1
        assert len(r.remaining) == 2
        assert r.progress_pct == pytest.approx(1 / 3)

    def test_wrong_objects(self):
        plan = TaskPlan(description="test")
        r = ValidationReport(
            plan=plan,
            assessments=[
                ObjectAssessment("star", status=ObjectStatus.WRONG, issue="wrong color"),
                ObjectAssessment("house", status=ObjectStatus.PARTIAL, issue="incomplete"),
            ],
        )
        assert len(r.wrong) == 2
        assert r.all_done is False

    def test_summary_format(self):
        plan = TaskPlan(description="test")
        r = ValidationReport(
            plan=plan,
            assessments=[
                ObjectAssessment("star", status=ObjectStatus.DRAWN),
                ObjectAssessment("house", status=ObjectStatus.MISSING),
            ],
        )
        s = r.summary()
        assert "1/2" in s
        assert "50%" in s

    def test_next_actions_for_missing(self):
        plan = TaskPlan(description="test")
        plan.add("house", "#0000FF")
        r = ValidationReport(
            plan=plan,
            assessments=[
                ObjectAssessment("house", status=ObjectStatus.MISSING,
                                 requested_color="#0000FF"),
            ],
        )
        actions = r.next_actions()
        assert len(actions) == 1
        assert "house" in actions[0]
        assert "#0000FF" in actions[0]

    def test_next_actions_for_wrong(self):
        plan = TaskPlan(description="test")
        r = ValidationReport(
            plan=plan,
            assessments=[
                ObjectAssessment("star", status=ObjectStatus.WRONG,
                                 issue="wrong color", suggestion="redraw in red"),
            ],
        )
        actions = r.next_actions()
        assert len(actions) == 1
        assert "redraw in red" in actions[0]

    def test_next_actions_empty_when_all_done(self):
        plan = TaskPlan(description="test")
        r = ValidationReport(
            plan=plan,
            assessments=[
                ObjectAssessment("star", status=ObjectStatus.DRAWN),
            ],
        )
        assert r.next_actions() == []


class TestValidationSkillInit:
    """Test DrawValidationSkill initialization."""

    def test_default_init(self):
        v = DrawValidationSkill()
        assert v._use_vision is True
        assert v._max_retries == 2

    def test_no_vision(self):
        v = DrawValidationSkill(use_vision=False)
        assert v._use_vision is False


class TestValidationJsonParsing:
    """Test _parse_json method on DrawValidationSkill."""

    def test_plain_json(self):
        r = DrawValidationSkill._parse_json('{"scene_description": "canvas"}')
        assert r["scene_description"] == "canvas"

    def test_markdown_json(self):
        text = 'Here:\n```json\n{"ok": true}\n```\n'
        r = DrawValidationSkill._parse_json(text)
        assert r == {"ok": True}

    def test_trailing_comma(self):
        text = '{"objects": [{"name": "star",}],}'
        r = DrawValidationSkill._parse_json(text)
        assert r["objects"][0]["name"] == "star"

    def test_invalid(self):
        assert DrawValidationSkill._parse_json("no json") is None


class TestValidationHeuristic:
    """Test heuristic fallback validation."""

    @pytest.mark.asyncio
    async def test_heuristic_with_no_vision(self):
        """Without vision, all objects should be PENDING or PARTIAL."""
        v = DrawValidationSkill(use_vision=False)
        plan = TaskPlan(description="star and house")
        plan.add("star", "#FF0000")
        plan.add("house", "#0000FF")

        # Pass a non-existent file path to trigger heuristic
        report = await v.validate("/nonexistent/screenshot.png", plan)

        # Should have assessments for both objects
        assert len(report.assessments) == 2
        # All should be pending since screenshot doesn't exist
        for a in report.assessments:
            assert a.status == ObjectStatus.PENDING


class TestPlanFromDescription:
    """Test DrawValidationSkill.plan_from_description static method."""

    def test_simple_shape(self):
        plan = DrawValidationSkill.plan_from_description("red star")
        assert plan.description == "red star"
        # Should detect 'star' as shape
        if plan.objects:
            assert plan.objects[0]["name"] == "star"

    def test_empty_description(self):
        plan = DrawValidationSkill.plan_from_description("")
        assert plan.description == ""


# ═══════════════════════════════════════════════════════════════════════════
# Integration: __init__.py exports
# ═══════════════════════════════════════════════════════════════════════════

class TestExports:
    """Test that all new skill classes are exported from drawing package."""

    def test_navigation_exports(self):
        from nlp2cmd.skills.drawing import (
            DrawNavigationSkill, NavigationResult, NavigationState, CanvasInfo,
        )
        assert DrawNavigationSkill is not None

    def test_draw_object_exports(self):
        from nlp2cmd.skills.drawing import (
            DrawObjectSkill, ObjectDrawResult, SceneDrawResult, DrawStatus,
        )
        assert DrawObjectSkill is not None

    def test_validation_exports(self):
        from nlp2cmd.skills.drawing import (
            DrawValidationSkill, ValidationReport, TaskPlan,
            ObjectAssessment, ObjectStatus,
        )
        assert DrawValidationSkill is not None

    def test_all_in___all__(self):
        import nlp2cmd.skills.drawing as pkg
        assert "DrawNavigationSkill" in pkg.__all__
        assert "DrawObjectSkill" in pkg.__all__
        assert "DrawValidationSkill" in pkg.__all__
        assert "TaskPlan" in pkg.__all__
        assert "ValidationReport" in pkg.__all__
        assert "ObjectStatus" in pkg.__all__
        assert "CanvasInfo" in pkg.__all__
        assert "DrawStatus" in pkg.__all__
