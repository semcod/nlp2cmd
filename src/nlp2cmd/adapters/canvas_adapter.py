# CanvasAdapter - extracted from canvas.py
"""
Canvas drawing adapter for NLP2CMD.

Enables drawing on web-based canvas applications (jspaint.app, Excalidraw, etc.)
via Playwright mouse control. Supports tool selection, color picking, and
geometric shape drawing through natural language commands.

Supported apps:
- jspaint.app — MS Paint clone with full tool palette
- Excalidraw — diagram/whiteboard tool
- Generic canvas — fallback for any <canvas> element

Usage:
    adapter = CanvasAdapter()
    plan = adapter.generate({"text": "narysuj czerwone koło na jspaint.app"})
"""
from __future__ import annotations
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Optional
from nlp2cmd.adapters.base import AdapterConfig, BaseDSLAdapter, SafetyPolicy
from nlp2cmd.ir import ActionIR
_DEBUG = os.environ.get("NLP2CMD_DEBUG", "").lower() in ("1", "true", "yes")


def _debug(msg: str) -> None:
    if _DEBUG:
        print(f"DEBUG [CanvasAdapter] {msg}", file=sys.stderr, flush=True)


from nlp2cmd.adapters.canvas_constants import TOOLS_JSPAINT
from nlp2cmd.adapters.canvas_execution import execute_drawing_plan as _execute_drawing_plan
from nlp2cmd.adapters.canvas_safety_policy import CanvasSafetyPolicy
from nlp2cmd.adapters.drawing_plan import DrawingPlan
from nlp2cmd.adapters.drawing_step import DrawingStep

class CanvasAdapter(BaseDSLAdapter):
    """
    Adapter for canvas-based drawing via Playwright mouse control.

    Converts NL drawing commands to structured drawing plans that can be
    executed by the MouseController + Playwright.
    """

    DSL_NAME = "canvas"
    DSL_VERSION = "1.0"

    INTENTS = {
        "draw": {
            "patterns": [
                "narysuj", "rysuj", "draw", "sketch",
                "namaluj", "maluj", "paint",
            ],
            "required_entities": [],
            "optional_entities": ["shape", "color", "size"],
        },
        "fill": {
            "patterns": [
                "wypełnij", "wypelnij", "fill", "pomaluj", "zamaluj",
                "koloruj", "color",
            ],
            "required_entities": ["color"],
            "optional_entities": [],
        },
        "write_text": {
            "patterns": [
                "napisz", "wpisz", "write", "type", "tekst", "text",
            ],
            "required_entities": ["text"],
            "optional_entities": ["color", "position"],
        },
    }

    TOOLS_JSPAINT = TOOLS_JSPAINT

    # Color name → hex mapping (Polish + English)
    COLORS = {
        "czerwony": "#FF0000", "czerwone": "#FF0000", "czerwona": "#FF0000",
        "red": "#FF0000",
        "czarny": "#000000", "czarne": "#000000", "czarna": "#000000",
        "black": "#000000",
        "biały": "#FFFFFF", "białe": "#FFFFFF", "biała": "#FFFFFF",
        "white": "#FFFFFF",
        "żółty": "#FFFF00", "żółte": "#FFFF00", "żółta": "#FFFF00",
        "yellow": "#FFFF00",
        "niebieski": "#0000FF", "niebieskie": "#0000FF", "niebieska": "#0000FF",
        "blue": "#0000FF",
        "zielony": "#00FF00", "zielone": "#00FF00", "zielona": "#00FF00",
        "green": "#00FF00",
        "pomarańczowy": "#FFA500", "orange": "#FFA500",
        "fioletowy": "#800080", "purple": "#800080",
        "różowy": "#FFC0CB", "pink": "#FFC0CB",
        "szary": "#808080", "gray": "#808080", "grey": "#808080",
        "brązowy": "#8B4513", "brown": "#8B4513",
    }

    # Shape name patterns (Polish + English)
    SHAPES = {
        "circle": r"(?:okr[aąę]g|ko[lł][oa]|circle)",
        "ellipse": r"(?:elips[aeę]|ellipse|owal|oval)",
        "rectangle": r"(?:prostok[aą]t|rectangle|rect)",
        "square": r"(?:kwadrat|square)",
        "line": r"(?:lini[aeę]|kres[kę]|line)",
        "triangle": r"(?:tr[oó]jk[aą]t|triangle)",
        "star": r"(?:gwiazd[aęk]|star)",
        "dot": r"(?:kropk[aęi]|punkt|dot|point)",
    }

    # Known canvas apps
    CANVAS_APPS = {
        "jspaint": {
            "url": "https://jspaint.app",
            "canvas_selector": "canvas",
            "wait_selector": ".canvas-area",
        },
        "excalidraw": {
            "url": "https://excalidraw.com",
            "canvas_selector": "canvas",
            "wait_selector": ".excalidraw",
        },
    }

    def __init__(
        self,
        config: Optional[AdapterConfig] = None,
        safety_policy: Optional[SafetyPolicy] = None,
    ):
        super().__init__(config, safety_policy or CanvasSafetyPolicy())
        self.last_action_ir: Optional[ActionIR] = None

    def generate(self, plan: dict[str, Any]) -> str:
        """
        Generate a canvas drawing DSL command from NL plan.

        Args:
            plan: Dict with 'text', 'intent', 'entities', 'confidence'

        Returns:
            JSON string with canvas_dql.v1 drawing instructions
        """
        text = str(plan.get("text") or plan.get("query") or "")
        _debug(f"generate(): text='{text[:100]}'")

        drawing_plan = self._create_drawing_plan(text)

        payload = {
            "dsl": "canvas_dql.v1",
            "app": drawing_plan.app,
            "url": drawing_plan.url,
            "steps": [
                {"action": s.action, **s.params}
                for s in drawing_plan.steps
            ],
        }

        action_id = f"canvas.draw_{drawing_plan.app}"
        explanation = f"canvas adapter: draw on {drawing_plan.app}"

        self.last_action_ir = ActionIR(
            action_id=action_id,
            dsl=json.dumps(payload, ensure_ascii=False),
            dsl_kind="dom",
            params={"url": drawing_plan.url, "app": drawing_plan.app},
            output_format="raw",
            confidence=float(plan.get("confidence") or 0.7),
            explanation=explanation,
        )

        return self.last_action_ir.dsl

    def _create_drawing_plan(self, text: str) -> DrawingPlan:
        """Create a drawing plan from natural language text."""
        text_lower = text.lower()

        # Detect app
        app = "jspaint"
        url = "https://jspaint.app"
        for app_name, app_config in self.CANVAS_APPS.items():
            if app_name in text_lower or app_config["url"].split("//")[1] in text_lower:
                app = app_name
                url = app_config["url"]
                break

        # Also detect URL in text
        url_match = re.search(r"(https?://\S+)", text)
        if url_match:
            url = url_match.group(1).rstrip(".,)")

        plan = DrawingPlan(url=url, app=app)

        # Step 1: Navigate
        plan.steps.append(DrawingStep("navigate", {"url": url}, f"Open {app}"))
        plan.steps.append(DrawingStep("wait", {"ms": 3000}, "Wait for app to load"))
        plan.steps.append(DrawingStep("wait_for_canvas", {}, "Wait for canvas element"))
        plan.steps.append(DrawingStep("get_canvas_info", {}, "Get canvas dimensions"))

        # Detect what to draw
        is_ladybug = bool(re.search(r"biedronk[aęi]|ladybug", text_lower))
        colors = self._extract_colors(text)
        shapes = self._extract_shapes(text)
        draw_text = self._extract_draw_text(text)

        if is_ladybug:
            self._plan_ladybug(plan, colors)
        elif shapes:
            for shape in shapes:
                self._plan_shape(plan, shape, colors)
        elif draw_text:
            self._plan_text(plan, draw_text, colors)
        else:
            # Default: draw with brush in detected color
            color = colors[0] if colors else "#000000"
            plan.steps.append(DrawingStep("select_tool", {"tool": "brush"}, "Select brush"))
            plan.steps.append(DrawingStep("set_color", {"color": color}, f"Set color {color}"))

        # Final screenshot
        plan.steps.append(DrawingStep("screenshot", {"suffix": app}, "Take screenshot"))

        return plan

    def _plan_ladybug(self, plan: DrawingPlan, colors: list[str]) -> None:
        """Add ladybug drawing steps to plan."""
        body_color = "#FF0000"
        dot_color = "#000000"

        # Use custom colors if specified
        if len(colors) >= 2:
            body_color = colors[0]
            dot_color = colors[1]
        elif len(colors) == 1:
            body_color = colors[0]

        # Draw body (red filled ellipse)
        plan.steps.append(DrawingStep("select_tool", {"tool": "ellipse"}, "Select ellipse tool"))
        plan.steps.append(DrawingStep("set_color", {"color": body_color}, f"Set body color"))
        plan.steps.append(DrawingStep(
            "draw_filled_ellipse",
            {"rx": 120, "ry": 120, "relative_to": "center"},
            "Draw ladybug body",
        ))

        # Fill body
        plan.steps.append(DrawingStep("select_tool", {"tool": "fill"}, "Select fill tool"))
        plan.steps.append(DrawingStep("set_color", {"color": body_color}, f"Set fill color"))
        plan.steps.append(DrawingStep(
            "fill_at", {"offset": [0, 0]}, "Fill body with color",
        ))

        # Draw center line
        plan.steps.append(DrawingStep("select_tool", {"tool": "line"}, "Select line tool"))
        plan.steps.append(DrawingStep("set_color", {"color": dot_color}, "Set line color"))
        plan.steps.append(DrawingStep(
            "draw_line",
            {"from_offset": [0, -120], "to_offset": [0, 120]},
            "Draw center dividing line",
        ))

        # Draw dots
        plan.steps.append(DrawingStep("select_tool", {"tool": "brush"}, "Select brush"))
        plan.steps.append(DrawingStep("set_color", {"color": dot_color}, "Set dot color"))
        dot_positions = [
            (-40, -35), (40, -35),   # top row
            (-50, 15), (50, 15),     # middle row
            (-30, 60), (30, 60),     # bottom row
            (0, -70),                # head spot
        ]
        for i, (dx, dy) in enumerate(dot_positions, 1):
            plan.steps.append(DrawingStep(
                "draw_filled_circle",
                {"radius": 12, "offset": [dx, dy]},
                f"Draw dot {i}",
            ))

        # Draw head (small black semicircle at top)
        plan.steps.append(DrawingStep(
            "draw_filled_circle",
            {"radius": 30, "offset": [0, -130]},
            "Draw ladybug head",
        ))

        # Draw antennae
        plan.steps.append(DrawingStep("select_tool", {"tool": "line"}, "Select line tool"))
        plan.steps.append(DrawingStep(
            "draw_line",
            {"from_offset": [-10, -150], "to_offset": [-30, -180]},
            "Draw left antenna",
        ))
        plan.steps.append(DrawingStep(
            "draw_line",
            {"from_offset": [10, -150], "to_offset": [30, -180]},
            "Draw right antenna",
        ))

    def _plan_shape(self, plan: DrawingPlan, shape: str, colors: list[str]) -> None:
        """Add shape drawing steps to plan."""
        color = colors[0] if colors else "#000000"

        if shape == "circle":
            plan.steps.append(DrawingStep("select_tool", {"tool": "ellipse"}, "Select ellipse"))
            plan.steps.append(DrawingStep("set_color", {"color": color}, f"Set color"))
            plan.steps.append(DrawingStep(
                "draw_circle", {"radius": 100, "relative_to": "center"}, "Draw circle",
            ))
        elif shape == "ellipse":
            plan.steps.append(DrawingStep("select_tool", {"tool": "ellipse"}, "Select ellipse"))
            plan.steps.append(DrawingStep("set_color", {"color": color}, f"Set color"))
            plan.steps.append(DrawingStep(
                "draw_ellipse", {"rx": 150, "ry": 80, "relative_to": "center"}, "Draw ellipse",
            ))
        elif shape in ("rectangle", "square"):
            w = 100 if shape == "square" else 200
            h = 100 if shape == "square" else 150
            plan.steps.append(DrawingStep("select_tool", {"tool": "rectangle"}, "Select rectangle"))
            plan.steps.append(DrawingStep("set_color", {"color": color}, f"Set color"))
            plan.steps.append(DrawingStep(
                "draw_rectangle", {"width": w, "height": h, "relative_to": "center"},
                f"Draw {shape}",
            ))
        elif shape == "line":
            plan.steps.append(DrawingStep("select_tool", {"tool": "line"}, "Select line"))
            plan.steps.append(DrawingStep("set_color", {"color": color}, f"Set color"))
            plan.steps.append(DrawingStep(
                "draw_line", {"from_offset": [-100, 0], "to_offset": [100, 0]}, "Draw line",
            ))
        elif shape == "dot":
            plan.steps.append(DrawingStep("select_tool", {"tool": "brush"}, "Select brush"))
            plan.steps.append(DrawingStep("set_color", {"color": color}, f"Set color"))
            plan.steps.append(DrawingStep(
                "draw_filled_circle", {"radius": 5, "offset": [0, 0]}, "Draw dot",
            ))

    def _plan_text(self, plan: DrawingPlan, text: str, colors: list[str]) -> None:
        """Add text writing steps to plan."""
        color = colors[0] if colors else "#000000"
        plan.steps.append(DrawingStep("select_tool", {"tool": "text"}, "Select text tool"))
        plan.steps.append(DrawingStep("set_color", {"color": color}, f"Set text color"))
        plan.steps.append(DrawingStep(
            "click_canvas", {"offset": [0, 0]}, "Click on canvas center",
        ))
        plan.steps.append(DrawingStep("type_text", {"text": text}, f"Type: {text[:50]}"))

    def _extract_colors(self, text: str) -> list[str]:
        """Extract color names from text, return as hex codes."""
        text_lower = text.lower()
        found: list[str] = []
        seen: set[str] = set()

        for name, hex_code in self.COLORS.items():
            if name in text_lower and hex_code not in seen:
                found.append(hex_code)
                seen.add(hex_code)

        # Also match hex codes in text
        for m in re.finditer(r"#[0-9a-fA-F]{6}", text):
            code = m.group(0).upper()
            if code not in seen:
                found.append(code)
                seen.add(code)

        return found

    def _extract_shapes(self, text: str) -> list[str]:
        """Extract shape names from text."""
        text_lower = text.lower()
        found: list[str] = []

        for shape_name, pattern in self.SHAPES.items():
            if re.search(pattern, text_lower):
                found.append(shape_name)

        return found

    @staticmethod
    def _extract_draw_text(text: str) -> Optional[str]:
        """Extract text to draw on canvas."""
        patterns = [
            r"(?:napisz|wpisz|write|type)\s+['\"](.+?)['\"]",
            r"(?:tekst|text)\s+['\"](.+?)['\"]",
            r"(?:napisz|wpisz|write|type)\s+(.+?)(?:\s+na\s+|\s+on\s+|$)",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    def validate_syntax(self, command: str) -> dict[str, Any]:
        """Validate canvas_dql.v1 JSON command."""
        try:
            payload = json.loads(command)
        except Exception as e:
            return {"valid": False, "errors": [f"Invalid JSON: {e}"]}

        if not isinstance(payload, dict) or payload.get("dsl") != "canvas_dql.v1":
            return {"valid": False, "errors": ["Not canvas_dql.v1"]}

        if not isinstance(payload.get("steps"), list):
            return {"valid": False, "errors": ["Missing steps array"]}

        return {"valid": True, "errors": []}

    @staticmethod
    async def execute_drawing_plan(page: Any, plan_json: str) -> dict[str, Any]:
        """Execute a canvas drawing plan on a Playwright page."""
        return await _execute_drawing_plan(page, plan_json)
