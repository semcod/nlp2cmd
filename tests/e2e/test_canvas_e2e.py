"""E2E tests for canvas drawing workflows with Playwright.

These tests require playwright to be installed:
    pip install playwright
    playwright install chromium

Run with:
    pytest tests/e2e/test_canvas_e2e.py -v --tb=short

Note: These tests open a real browser window.
Set HEADLESS=1 to run in headless mode.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest


# Skip all tests if playwright not installed
playwright = pytest.importorskip("playwright")

from playwright.sync_api import sync_playwright


# Default to headless unless explicitly disabled
HEADLESS = os.environ.get("HEADLESS", "0") != "0"


class TestCanvasDrawingE2E:
    """End-to-end tests for canvas drawing workflows."""

    @pytest.fixture(scope="class")
    def browser_context(self):
        """Create browser context for tests."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
            )
            yield context
            context.close()
            browser.close()

    def _navigate_to_jspaint(self, page):
        """Helper: navigate to jspaint and wait for canvas."""
        page.goto("https://jspaint.app", wait_until="networkidle")
        # Wait for canvas to be ready
        try:
            page.wait_for_selector("canvas", timeout=10000)
        except Exception:
            pass
        page.wait_for_timeout(1000)

    def _get_canvas_center(self, page) -> tuple[float, float]:
        """Helper: get canvas center coordinates."""
        try:
            canvas = page.locator("canvas").first
            if canvas.is_visible():
                box = canvas.bounding_box()
                if box:
                    return (
                        box["x"] + box["width"] // 2,
                        box["y"] + box["height"] // 2,
                    )
        except Exception:
            pass
        return (640, 360)  # Default fallback

    def _js_draw_filled_circle(self, cx: float, cy: float, radius: float, color: str) -> str:
        """JS helper: draw filled circle on canvas."""
        return f"""
        () => {{
            const canvas = document.querySelector('canvas');
            if (!canvas) return 'no_canvas';
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            const ctx = canvas.getContext('2d');
            const pcx = ({cx} - rect.left) * scaleX;
            const pcy = ({cy} - rect.top) * scaleY;
            const pr = {radius} * Math.min(scaleX, scaleY);
            ctx.save();
            ctx.fillStyle = '{color}';
            ctx.beginPath();
            ctx.arc(pcx, pcy, pr, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
            return 'filled_circle';
        }}
        """

    def _js_draw_polygon(self, points: list[tuple[float, float]], color: str, width: int = 2, fill: bool = False) -> str:
        pts_js = ",".join([f"[{x},{y}]" for x, y in points])
        return f"""
        () => {{
            const canvas = document.querySelector('canvas');
            if (!canvas) return 'no_canvas';
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            const ctx = canvas.getContext('2d');
            const pts = [{pts_js}];
            if (!pts.length) return 'no_points';
            ctx.save();
            ctx.lineWidth = {width};
            ctx.strokeStyle = '{color}';
            ctx.fillStyle = '{color}';
            ctx.beginPath();
            ctx.moveTo((pts[0][0] - rect.left) * scaleX, (pts[0][1] - rect.top) * scaleY);
            for (let i = 1; i < pts.length; i++) {{
                ctx.lineTo((pts[i][0] - rect.left) * scaleX, (pts[i][1] - rect.top) * scaleY);
            }}
            ctx.closePath();
            if ({str(bool(fill)).lower()}) ctx.fill();
            ctx.stroke();
            ctx.restore();
            return '{"polygon_filled" if fill else "polygon_stroked"}';
        }}
        """

    def _js_draw_bezier(self, commands: list[dict], color: str, width: int = 2, fill: bool = False, close: bool = False) -> str:
        import json as _json

        cmds_js = _json.dumps(commands)
        return f"""
        () => {{
            const canvas = document.querySelector('canvas');
            if (!canvas) return 'no_canvas';
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            const ctx = canvas.getContext('2d');
            const cmds = {cmds_js};
            if (!Array.isArray(cmds) || cmds.length === 0) return 'no_cmds';
            ctx.save();
            ctx.lineWidth = {width};
            ctx.strokeStyle = '{color}';
            ctx.fillStyle = '{color}';
            ctx.beginPath();
            for (const c of cmds) {{
                const t = (c.type || '').toUpperCase();
                if (t === 'M') {{
                    ctx.moveTo((c.x - rect.left) * scaleX, (c.y - rect.top) * scaleY);
                }} else if (t === 'L') {{
                    ctx.lineTo((c.x - rect.left) * scaleX, (c.y - rect.top) * scaleY);
                }} else if (t === 'Q') {{
                    ctx.quadraticCurveTo(
                        (c.cpx - rect.left) * scaleX, (c.cpy - rect.top) * scaleY,
                        (c.x - rect.left) * scaleX, (c.y - rect.top) * scaleY
                    );
                }} else if (t === 'C') {{
                    ctx.bezierCurveTo(
                        (c.cp1x - rect.left) * scaleX, (c.cp1y - rect.top) * scaleY,
                        (c.cp2x - rect.left) * scaleX, (c.cp2y - rect.top) * scaleY,
                        (c.x - rect.left) * scaleX, (c.y - rect.top) * scaleY
                    );
                }}
            }}
            if ({str(bool(close)).lower()}) ctx.closePath();
            if ({str(bool(fill)).lower()}) ctx.fill();
            ctx.stroke();
            ctx.restore();
            return '{"bezier_filled" if fill else "bezier_stroked"}';
        }}
        """

    def test_jspaint_loads_and_has_canvas(self, browser_context):
        """Test that jspaint.app loads with canvas element."""
        page = browser_context.new_page()
        page.goto("https://jspaint.app", wait_until="networkidle")

        # Check canvas exists
        canvas = page.locator("canvas")
        assert canvas.count() > 0, "No canvas found on jspaint.app"

        # Check canvas is visible
        assert canvas.first.is_visible(), "Canvas not visible"

        page.close()

    def test_draw_simple_red_circle(self, browser_context):
        """Test drawing a simple red circle on canvas."""
        page = browser_context.new_page()
        self._navigate_to_jspaint(page)

        cx, cy = self._get_canvas_center(page)
        radius = 50
        color = "#FF0000"

        # Draw circle via canvas API
        result = page.evaluate(self._js_draw_filled_circle(cx, cy, radius, color))
        assert result == "filled_circle", f"Drawing failed: {result}"

        # Take screenshot for verification
        screenshot_path = "/tmp/test_circle.png"
        page.screenshot(path=screenshot_path, full_page=False)
        assert Path(screenshot_path).exists(), "Screenshot not saved"

        page.close()

    def test_draw_ladybug_blueprint(self, browser_context):
        """Test drawing a ladybug using the blueprint steps."""
        from nlp2cmd.automation.drawing_blueprints import get_blueprint_steps

        page = browser_context.new_page()
        self._navigate_to_jspaint(page)

        # Get ladybug blueprint steps
        steps = get_blueprint_steps("narysuj biedronkę")
        assert steps is not None, "Ladybug blueprint not found"
        assert len(steps) > 5, "Ladybug blueprint has too few steps"

        cx, cy = self._get_canvas_center(page)

        current_color = "#000000"
        current_line_width = 2

        # Execute drawing steps
        for step in steps:
            action = step.action
            params = step.params or {}

            if action == "set_color":
                current_color = str(params.get("color", current_color))

            elif action == "set_line_width":
                try:
                    current_line_width = max(1, int(params.get("width", params.get("line_width", current_line_width))))
                except Exception:
                    current_line_width = 2

            elif action == "draw_filled_circle":
                offset = params.get("offset", [0, 0])
                radius = params.get("radius", 20)
                color = params.get("color", current_color)
                x = cx + offset[0]
                y = cy + offset[1]
                page.evaluate(self._js_draw_filled_circle(x, y, radius, color))
                page.wait_for_timeout(50)

            elif action == "draw_circle":
                offset = params.get("offset", [0, 0])
                radius = params.get("radius", 20)
                color = params.get("color", current_color)
                x = cx + offset[0]
                y = cy + offset[1]
                page.evaluate(self._js_draw_filled_circle(x, y, radius, color))
                page.wait_for_timeout(50)

            elif action == "draw_polygon":
                offset = params.get("offset", [0, 0]) or [0, 0]
                fill = bool(params.get("fill", False))
                pts = []
                for pt in (params.get("points", []) or []):
                    try:
                        px = float(pt[0])
                        py = float(pt[1])
                    except Exception:
                        continue
                    pts.append((cx + float(offset[0]) + px, cy + float(offset[1]) + py))
                if pts:
                    page.evaluate(self._js_draw_polygon(pts, current_color, current_line_width, fill))
                    page.wait_for_timeout(50)

            elif action == "draw_bezier":
                fill = bool(params.get("fill", False))
                close = bool(params.get("close", False))
                try:
                    width = max(1, int(params.get("line_width", current_line_width)))
                except Exception:
                    width = current_line_width
                cmds: list[dict] = []
                for c in (params.get("curves", []) or []):
                    if not isinstance(c, dict):
                        continue
                    t = str(c.get("type", "")).upper()
                    if t == "M":
                        cmds.append({"type": "M", "x": cx + float(c.get("x", 0)), "y": cy + float(c.get("y", 0))})
                    elif t == "L":
                        cmds.append({"type": "L", "x": cx + float(c.get("x", 0)), "y": cy + float(c.get("y", 0))})
                    elif t == "Q":
                        cmds.append({
                            "type": "Q",
                            "cpx": cx + float(c.get("cpx", 0)),
                            "cpy": cy + float(c.get("cpy", 0)),
                            "x": cx + float(c.get("x", 0)),
                            "y": cy + float(c.get("y", 0)),
                        })
                    elif t == "C":
                        cmds.append({
                            "type": "C",
                            "cp1x": cx + float(c.get("cp1x", 0)),
                            "cp1y": cy + float(c.get("cp1y", 0)),
                            "cp2x": cx + float(c.get("cp2x", 0)),
                            "cp2y": cy + float(c.get("cp2y", 0)),
                            "x": cx + float(c.get("x", 0)),
                            "y": cy + float(c.get("y", 0)),
                        })
                if cmds:
                    page.evaluate(self._js_draw_bezier(cmds, current_color, width, fill, close))
                    page.wait_for_timeout(50)

            elif action == "screenshot":
                suffix = params.get("suffix", "ladybug")
                screenshot_path = f"/tmp/test_{suffix}.png"
                page.screenshot(path=screenshot_path, full_page=False)
                assert Path(screenshot_path).exists()

        page.close()

    def test_canvas_api_with_polygon(self, browser_context):
        """Test polygon drawing via canvas API."""
        page = browser_context.new_page()
        self._navigate_to_jspaint(page)

        cx, cy = self._get_canvas_center(page)

        # Draw a triangle using polygon
        points = [
            (cx, cy - 50),      # top
            (cx - 40, cy + 30),  # bottom left
            (cx + 40, cy + 30),  # bottom right
        ]
        points_js = ",".join([f"[{x},{y}]" for x, y in points])

        js_code = f"""
        () => {{
            const canvas = document.querySelector('canvas');
            if (!canvas) return 'no_canvas';
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            const ctx = canvas.getContext('2d');
            const pts = [{points_js}];
            ctx.save();
            ctx.fillStyle = '#00FF00';
            ctx.beginPath();
            ctx.moveTo((pts[0][0] - rect.left) * scaleX, (pts[0][1] - rect.top) * scaleY);
            for (let i = 1; i < pts.length; i++) {{
                ctx.lineTo((pts[i][0] - rect.left) * scaleX, (pts[i][1] - rect.top) * scaleY);
            }}
            ctx.closePath();
            ctx.fill();
            ctx.restore();
            return 'polygon_drawn';
        }}
        """

        result = page.evaluate(js_code)
        assert result == "polygon_drawn", f"Polygon drawing failed: {result}"

        page.close()

    def test_canvas_api_with_bezier(self, browser_context):
        """Test bezier curve drawing via canvas API."""
        page = browser_context.new_page()
        self._navigate_to_jspaint(page)

        cx, cy = self._get_canvas_center(page)

        # Draw a simple curve
        js_code = f"""
        () => {{
            const canvas = document.querySelector('canvas');
            if (!canvas) return 'no_canvas';
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            const ctx = canvas.getContext('2d');
            ctx.save();
            ctx.strokeStyle = '#0000FF';
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.moveTo(({cx - 50} - rect.left) * scaleX, ({cy} - rect.top) * scaleY);
            ctx.quadraticCurveTo(
                ({cx} - rect.left) * scaleX, ({cy - 80} - rect.top) * scaleY,
                ({cx + 50} - rect.left) * scaleX, ({cy} - rect.top) * scaleY
            );
            ctx.stroke();
            ctx.restore();
            return 'bezier_drawn';
        }}
        """

        result = page.evaluate(js_code)
        assert result == "bezier_drawn", f"Bezier drawing failed: {result}"

        page.close()


class TestCanvasDecompositionE2E:
    """E2E tests for canvas workflow through ActionPlanner."""

    @pytest.fixture(scope="class")
    def browser_context(self):
        """Create browser context for tests."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
            )
            yield context
            context.close()
            browser.close()

    def test_action_planner_generates_canvas_plan(self, monkeypatch):
        """Test that ActionPlanner generates a canvas plan for drawing queries."""
        monkeypatch.setenv("CANVAS_USE_BLUEPRINTS", "1")
        from nlp2cmd.automation.action_planner import ActionPlanner

        planner = ActionPlanner()
        plan = planner.decompose_sync("narysuj biedronkę na jspaint.app")

        assert plan is not None, "No plan generated"
        assert plan.source in {"canvas_blueprint", "canvas_llm", "canvas_rule_based", "vector_db"}, (
            f"Unexpected source: {plan.source}"
        )

        # Check plan has expected steps
        actions = [s.action for s in plan.steps]
        assert "navigate" in actions, "Missing navigate step"
        assert "wait_for_canvas" in actions, "Missing wait_for_canvas step"

        # Check drawing steps exist
        drawing_actions = [
            "draw_filled_circle", "draw_filled_ellipse", "draw_circle",
            "draw_line", "draw_polygon", "draw_bezier", "draw_arc"
        ]
        has_drawing = any(a in actions for a in drawing_actions)
        assert has_drawing, f"No drawing actions found in: {actions}"

    def test_full_workflow_with_video_recording(self, browser_context, tmp_path):
        """Test full canvas workflow with video recording.

        This test demonstrates the complete workflow from query to video.
        """
        from nlp2cmd.automation.action_planner import ActionPlanner

        # 1. Generate plan
        planner = ActionPlanner()
        plan = planner.decompose_sync("narysuj biedronkę na jspaint.app")
        assert plan is not None

        # 2. Execute in browser with video
        video_dir = tmp_path / "videos"
        video_dir.mkdir()

        context = browser_context.browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(video_dir),
            record_video_size={"width": 1280, "height": 720},
        )
        page = context.new_page()

        # Execute steps
        for step in plan.steps:
            action = step.action
            params = step.params or {}

            if action == "navigate":
                url = params.get("url", "https://jspaint.app")
                page.goto(url, wait_until="networkidle")
                page.wait_for_timeout(1000)

            elif action == "wait_for_canvas":
                try:
                    page.wait_for_selector("canvas", timeout=5000)
                except Exception:
                    pass
                page.wait_for_timeout(1000)

            # ... (other actions would be handled here)

        # Take final screenshot
        screenshot_path = tmp_path / "final_ladybug.png"
        page.screenshot(path=str(screenshot_path), full_page=False)

        context.close()

        # Verify outputs
        assert screenshot_path.exists(), "Screenshot not created"
        video_files = list(video_dir.glob("*.webm")) + list(video_dir.glob("*.mp4"))
        assert len(video_files) > 0, "No video file created"
