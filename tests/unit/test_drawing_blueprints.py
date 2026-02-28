"""Tests for drawing blueprints and canvas decomposition improvements."""

from __future__ import annotations

import re

import pytest


class TestDrawingBlueprints:
    """Test the drawing_blueprints module."""

    def test_import(self):
        from nlp2cmd.automation.drawing_blueprints import (
            lookup_blueprint,
            get_blueprint_steps,
            list_available_blueprints,
            OBJECT_BLUEPRINTS,
        )
        assert len(OBJECT_BLUEPRINTS) >= 14

    def test_list_available(self):
        from nlp2cmd.automation.drawing_blueprints import list_available_blueprints
        names = list_available_blueprints()
        assert "rabbit" in names
        assert "car" in names
        assert "ladybug" in names
        assert "cat" in names
        assert "house" in names
        assert "heart" in names
        assert "snowman" in names

    @pytest.mark.parametrize("query,expected_name", [
        ("narysuj zajaca", "rabbit"),
        ("narysuj królika", "rabbit"),
        ("draw a rabbit", "rabbit"),
        ("narysuj kota", "cat"),
        ("draw cat", "cat"),
        ("narysuj psa", "dog"),
        ("narysuj samochód", "car"),
        ("draw a car", "car"),
        ("narysuj dom", "house"),
        ("narysuj domek", "house"),
        ("narysuj drzewo", "tree"),
        ("narysuj słońce", "sun"),
        ("narysuj kwiat", "flower"),
        ("narysuj gwiazdę", "star"),
        ("narysuj serce", "heart"),
        ("draw heart", "heart"),
        ("narysuj rybę", "fish"),
        ("narysuj motyla", "butterfly"),
        ("narysuj bałwana", "snowman"),
        ("draw snowman", "snowman"),
        ("narysuj biedronkę", "ladybug"),
        ("draw ladybug", "ladybug"),
    ])
    def test_lookup_blueprint_polish_and_english(self, query, expected_name):
        from nlp2cmd.automation.drawing_blueprints import lookup_blueprint
        bp = lookup_blueprint(query)
        assert bp is not None, f"No blueprint for: {query}"
        assert bp["name"] == expected_name

    def test_lookup_returns_none_for_unknown(self):
        from nlp2cmd.automation.drawing_blueprints import lookup_blueprint
        assert lookup_blueprint("narysuj dinozaura") is None
        assert lookup_blueprint("otwórz przeglądarkę") is None

    @pytest.mark.parametrize("name", [
        "rabbit", "cat", "dog", "car", "house", "tree",
        "sun", "flower", "star", "heart", "fish", "butterfly",
        "snowman", "ladybug",
    ])
    def test_blueprint_steps_valid(self, name):
        """Each blueprint should produce valid steps with screenshot at end."""
        from nlp2cmd.automation.drawing_blueprints import OBJECT_BLUEPRINTS
        bp = next(b for b in OBJECT_BLUEPRINTS if b["name"] == name)
        steps = bp["steps_fn"]()
        assert len(steps) >= 5, f"{name} has too few steps: {len(steps)}"

        # Last step should be screenshot
        assert steps[-1].action == "screenshot", f"{name} missing screenshot"
        assert steps[-1].params.get("suffix") == name

        # All steps should have valid action names
        valid_actions = {
            "set_color", "set_line_width",
            "draw_filled_ellipse", "draw_filled_circle", "draw_filled_rectangle",
            "draw_circle", "draw_ellipse", "draw_rectangle",
            "draw_line", "draw_arc", "draw_polygon", "draw_bezier",
            "draw_svg_path", "screenshot",
        }
        for step in steps:
            assert step.action in valid_actions, (
                f"{name}: unknown action '{step.action}'"
            )

    def test_rabbit_has_body_parts(self):
        from nlp2cmd.automation.drawing_blueprints import get_blueprint_steps
        steps = get_blueprint_steps("narysuj królika")
        assert steps is not None
        descs = " ".join(s.description for s in steps)
        assert "Body" in descs
        assert "Head" in descs
        assert "ear" in descs.lower()

    def test_car_has_wheels(self):
        from nlp2cmd.automation.drawing_blueprints import get_blueprint_steps
        steps = get_blueprint_steps("narysuj samochód")
        assert steps is not None
        descs = " ".join(s.description for s in steps)
        assert "wheel" in descs.lower()

    def test_heart_uses_svg_path(self):
        from nlp2cmd.automation.drawing_blueprints import get_blueprint_steps
        steps = get_blueprint_steps("narysuj serce")
        assert steps is not None
        has_svg = any(s.action == "draw_svg_path" for s in steps)
        assert has_svg, "Heart should use draw_svg_path"

    def test_star_uses_polygon(self):
        from nlp2cmd.automation.drawing_blueprints import get_blueprint_steps
        steps = get_blueprint_steps("narysuj gwiazdę")
        assert steps is not None
        has_polygon = any(s.action == "draw_polygon" for s in steps)
        assert has_polygon, "Star should use draw_polygon"

    def test_cat_uses_bezier_for_tail(self):
        from nlp2cmd.automation.drawing_blueprints import get_blueprint_steps
        steps = get_blueprint_steps("narysuj kota")
        assert steps is not None
        has_bezier = any(s.action == "draw_bezier" for s in steps)
        assert has_bezier, "Cat should use draw_bezier for tail"

    def test_sun_uses_arc_for_smile(self):
        from nlp2cmd.automation.drawing_blueprints import get_blueprint_steps
        steps = get_blueprint_steps("narysuj słońce")
        assert steps is not None
        has_arc = any(s.action == "draw_arc" for s in steps)
        assert has_arc, "Sun should use draw_arc for smile"

    def test_colors_are_valid_hex(self):
        """All color params should be valid hex codes."""
        from nlp2cmd.automation.drawing_blueprints import OBJECT_BLUEPRINTS
        hex_re = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for bp in OBJECT_BLUEPRINTS:
            steps = bp["steps_fn"]()
            for step in steps:
                if step.action == "set_color":
                    color = step.params.get("color", "")
                    assert hex_re.match(color), (
                        f"{bp['name']}: invalid color '{color}'"
                    )


class TestCanvasDecompositionIntegration:
    """Test that ActionPlanner routes to blueprints via decompose_sync."""

    def test_blueprint_takes_priority(self):
        """Blueprint match should produce canvas_blueprint source."""
        from nlp2cmd.automation.action_planner import ActionPlanner
        planner = ActionPlanner()
        plan = planner.decompose_sync("narysuj kota na jspaint.app")
        assert plan is not None
        assert plan.source == "canvas_blueprint"
        assert plan.confidence >= 0.95
        actions = [s.action for s in plan.steps]
        assert "navigate" in actions
        assert "wait_for_canvas" in actions
        assert "draw_filled_ellipse" in actions or "draw_filled_circle" in actions

    def test_blueprint_extracts_url(self):
        """URL from query should be used for navigation."""
        from nlp2cmd.automation.action_planner import ActionPlanner
        planner = ActionPlanner()
        plan = planner.decompose_sync("narysuj psa na jspaint.app")
        assert plan is not None
        nav = next(s for s in plan.steps if s.action == "navigate")
        assert "jspaint.app" in nav.params["url"]

    def test_blueprint_default_url(self):
        """Default to jspaint.app when no URL specified."""
        from nlp2cmd.automation.action_planner import ActionPlanner
        planner = ActionPlanner()
        plan = planner.decompose_sync("narysuj dom")
        assert plan is not None
        nav = next(s for s in plan.steps if s.action == "navigate")
        assert nav.params["url"] == "https://jspaint.app"

    @pytest.mark.parametrize("query,blueprint_name", [
        ("narysuj biedronkę", "ladybug"),
        ("narysuj królika", "rabbit"),
        ("narysuj auto", "car"),
        ("draw a flower", "flower"),
        ("narysuj bałwana", "snowman"),
    ])
    def test_various_objects_route_to_blueprint(self, query, blueprint_name):
        from nlp2cmd.automation.action_planner import ActionPlanner
        planner = ActionPlanner()
        plan = planner.decompose_sync(query)
        assert plan is not None
        assert plan.source == "canvas_blueprint"
        screenshots = [s for s in plan.steps if s.action == "screenshot"]
        assert len(screenshots) >= 1
        assert screenshots[0].params.get("suffix") == blueprint_name

    def test_non_drawing_query_returns_none_from_canvas(self):
        """Non-drawing queries should not match canvas decomposition."""
        from nlp2cmd.automation.action_planner import ActionPlanner
        planner = ActionPlanner()
        plan = planner.decompose_sync("otwórz przeglądarkę")
        if plan:
            assert plan.source != "canvas_blueprint"
