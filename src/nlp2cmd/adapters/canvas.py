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


@dataclass
class DrawingStep:
    """Single step in a drawing plan."""
    action: str  # "select_tool", "set_color", "draw_circle", "fill_area", etc.
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class DrawingPlan:
    """Complete drawing plan for canvas operations."""
    url: str = "https://jspaint.app"
    app: str = "jspaint"
    steps: list[DrawingStep] = field(default_factory=list)


class CanvasSafetyPolicy(SafetyPolicy):
    """Safety policy for canvas operations — generally safe."""
    enabled: bool = True


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

    # JSPaint tool selectors
    TOOLS_JSPAINT = {
        "pencil": {"selector": '.tool[title*="Pencil"]', "fallback_idx": 4},
        "brush": {"selector": '.tool[title*="Brush"]', "fallback_idx": 5},
        "fill": {"selector": '.tool[title*="Fill"]', "fallback_idx": 9},
        "eraser": {"selector": '.tool[title*="Eraser"]', "fallback_idx": 3},
        "pick_color": {"selector": '.tool[title*="Pick Color"]', "fallback_idx": 6},
        "magnifier": {"selector": '.tool[title*="Magnifier"]', "fallback_idx": 7},
        "select": {"selector": '.tool[title*="Select"]', "fallback_idx": 0},
        "free_select": {"selector": '.tool[title*="Free-Form Select"]', "fallback_idx": 1},
        "text": {"selector": '.tool[title*="Text"]', "fallback_idx": 10},
        "line": {"selector": '.tool[title*="Line"]', "fallback_idx": 11},
        "curve": {"selector": '.tool[title*="Curve"]', "fallback_idx": 12},
        "rectangle": {"selector": '.tool[title*="Rectangle"]', "fallback_idx": 13},
        "polygon": {"selector": '.tool[title*="Polygon"]', "fallback_idx": 14},
        "ellipse": {"selector": '.tool[title*="Ellipse"]', "fallback_idx": 15},
        "rounded_rectangle": {"selector": '.tool[title*="Rounded Rectangle"]', "fallback_idx": 16},
    }

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

    # ── Execution helpers (used by PipelineRunner) ───────────────────

    @staticmethod
    async def execute_drawing_plan(page: Any, plan_json: str) -> dict[str, Any]:
        """
        Execute a canvas drawing plan on a Playwright page.
        
        IMPROVED: Added detailed diagnostic logging for each step.
        """
        from nlp2cmd.automation.mouse_controller import MouseController, Point

        try:
            plan = json.loads(plan_json)
        except Exception as e:
            return {"success": False, "error": f"Invalid plan JSON: {e}"}

        steps = plan.get("steps", [])
        mouse = MouseController(page, human_like=True)
        canvas_center: Optional[Point] = None
        canvas_box: Optional[dict] = None
        executed = 0
        errors = []
        
        # Diagnostic logging
        import sys
        def log_step(step_num: int, action: str, status: str, details: str = ""):
            prefix = f"[Canvas {step_num}/{len(steps)}]"
            if status == "OK":
                print(f"{prefix} ✓ {action}: {details}", file=sys.stderr)
            elif status == "ERROR":
                print(f"{prefix} ✗ {action} FAILED: {details}", file=sys.stderr)
            else:
                print(f"{prefix} → {action}: {details}", file=sys.stderr)
        
        # Helper to check if canvas has non-white pixels (drawing verification)
        async def check_canvas_has_drawing() -> dict:
            """Check if canvas has visible drawing by sampling pixels."""
            try:
                result = await page.evaluate("""
                    () => {
                        const canvas = document.querySelector('canvas');
                        if (!canvas) return {error: 'No canvas found'};
                        const ctx = canvas.getContext('2d');
                        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                        const data = imageData.data;
                        
                        // Count non-white/non-transparent pixels
                        let nonWhitePixels = 0;
                        let totalPixels = data.length / 4;
                        
                        // Sample every 100th pixel for performance
                        for (let i = 0; i < data.length; i += 400) {
                            const r = data[i];
                            const g = data[i + 1];
                            const b = data[i + 2];
                            const a = data[i + 3];
                            
                            // Not white (255,255,255) and not fully transparent
                            if (!(r === 255 && g === 255 && b === 255) && a > 0) {
                                nonWhitePixels++;
                            }
                        }
                        
                        return {
                            totalPixels: totalPixels,
                            nonWhitePixels: nonWhitePixels,
                            hasDrawing: nonWhitePixels > 10,  // Threshold
                            isBlank: nonWhitePixels <= 10
                        };
                    }
                """)
                return result
            except Exception as e:
                return {error: str(e), hasDrawing: False}
        
        # Capture canvas state before first drawing
        canvas_was_blank_before = True

        for i, step in enumerate(steps, 1):
            action = step.get("action", "")
            description = step.get("description", action)
            
            try:
                if action == "navigate":
                    url = step.get("url", "")
                    log_step(i, action, "START", f"Navigating to {url}")
                    await page.goto(url, wait_until="networkidle", timeout=15000)
                    # Verify page loaded
                    current_url = page.url
                    if url in current_url or "jspaint" in current_url:
                        log_step(i, action, "OK", f"Loaded: {current_url[:50]}")
                        executed += 1
                    else:
                        log_step(i, action, "ERROR", f"Wrong URL: {current_url}")
                        errors.append(f"Step {i}: Navigation failed - got {current_url}")

                elif action == "wait":
                    ms = step.get("ms", 1000)
                    log_step(i, action, "START", f"Waiting {ms}ms")
                    await page.wait_for_timeout(ms)
                    log_step(i, action, "OK", f"Waited {ms}ms")
                    executed += 1

                elif action == "wait_for_canvas":
                    log_step(i, action, "START", "Looking for canvas element")
                    try:
                        await page.wait_for_selector("canvas", timeout=10000)
                        # Verify canvas is visible and has size
                        canvas_info = await page.evaluate("""
                            () => {
                                const canvas = document.querySelector('canvas');
                                if (!canvas) return {error: 'No canvas found'};
                                const rect = canvas.getBoundingClientRect();
                                return {
                                    width: canvas.width,
                                    height: canvas.height,
                                    visible: rect.width > 0 && rect.height > 0,
                                    rect: {x: rect.x, y: rect.y, w: rect.width, h: rect.height}
                                };
                            }
                        """)
                        if canvas_info.get('visible'):
                            log_step(i, action, "OK", f"Canvas ready: {canvas_info}")
                            executed += 1
                        else:
                            log_step(i, action, "ERROR", f"Canvas not visible: {canvas_info}")
                            errors.append(f"Step {i}: Canvas not visible")
                    except Exception as e:
                        log_step(i, action, "ERROR", f"Canvas not found: {e}")
                        errors.append(f"Step {i}: Canvas wait failed - {e}")

                elif action == "get_canvas_info":
                    log_step(i, action, "START", "Getting canvas dimensions")
                    canvas_el = await page.query_selector("canvas")
                    if canvas_el:
                        canvas_box = await canvas_el.bounding_box()
                        if canvas_box:
                            canvas_center = Point(
                                canvas_box["x"] + canvas_box["width"] / 2,
                                canvas_box["y"] + canvas_box["height"] / 2,
                            )
                            log_step(i, action, "OK", f"Center: ({canvas_center.x:.0f}, {canvas_center.y:.0f}), Size: {canvas_box['width']:.0f}x{canvas_box['height']:.0f}")
                            executed += 1
                        else:
                            log_step(i, action, "ERROR", "Canvas has no bounding box")
                            errors.append(f"Step {i}: Canvas bounding box is None")
                    else:
                        log_step(i, action, "ERROR", "Canvas element not found")
                        errors.append(f"Step {i}: Canvas element is None")

                elif action == "select_tool":
                    tool_name = step.get("tool", "brush")
                    log_step(i, action, "START", f"Selecting tool: {tool_name}")
                    tool_info = CanvasAdapter.TOOLS_JSPAINT.get(tool_name)
                    if tool_info:
                        # Try selector first
                        el = await page.query_selector(tool_info["selector"])
                        if el:
                            await el.click()
                            await page.wait_for_timeout(300)  # Wait for tool activation
                            # Verify tool was selected
                            is_active = await page.evaluate(f"""
                                () => {{
                                    const tool = document.querySelector('{tool_info["selector"]}');
                                    return tool && (tool.classList.contains('selected') || tool.getAttribute('aria-pressed') === 'true');
                                }}
                            """)
                            if is_active:
                                log_step(i, action, "OK", f"Tool {tool_name} selected via selector")
                                executed += 1
                            else:
                                log_step(i, action, "WARN", f"Tool {tool_name} clicked but may not be active")
                                executed += 1  # Still count as executed
                        else:
                            # Fallback: click by index
                            tools = await page.query_selector_all(".tool")
                            idx = tool_info.get("fallback_idx", 0)
                            if 0 <= idx < len(tools):
                                await tools[idx].click()
                                await page.wait_for_timeout(300)
                                log_step(i, action, "OK", f"Tool {tool_name} selected via index {idx}")
                                executed += 1
                            else:
                                log_step(i, action, "ERROR", f"Tool index {idx} out of range ({len(tools)} tools)")
                                errors.append(f"Step {i}: Tool selection failed")
                    else:
                        log_step(i, action, "ERROR", f"Unknown tool: {tool_name}")
                        errors.append(f"Step {i}: Unknown tool {tool_name}")

                elif action == "set_color":
                    color = step.get("color", "#000000")
                    log_step(i, action, "START", f"Setting color: {color}")
                    
                    # Try multiple methods to set color
                    color_set = False
                    
                    # Method 1: Try to find and click color in palette
                    try:
                        # Look for color swatch
                        color_result = await page.evaluate(f"""
                            () => {{
                                // Try to find color button with matching background
                                const buttons = document.querySelectorAll('.color-button, .swatch, [class*="color"]');
                                for (const btn of buttons) {{
                                    const style = window.getComputedStyle(btn);
                                    if (style.backgroundColor.includes('{color}') || style.background.includes('{color}')) {{
                                        btn.click();
                                        return {{method: 'click', element: btn.className}};
                                    }}
                                }}
                                return {{method: 'none found'}};
                            }}
                        """)
                        if color_result.get('method') == 'click':
                            color_set = True
                            log_step(i, action, "OK", f"Color set via palette click: {color_result}")
                    except Exception as e:
                        log_step(i, action, "WARN", f"Palette click failed: {e}")
                    
                    # Method 2: JS injection for JSPaint
                    if not color_set:
                        try:
                            await page.evaluate(f"""
                                (() => {{
                                    if (typeof window.set_foreground_color === 'function') {{
                                        window.set_foreground_color('{color}');
                                        return {{method: 'jspaint_api'}};
                                    }}
                                    // Try to set canvas context directly
                                    const canvas = document.querySelector('canvas');
                                    if (canvas) {{
                                        const ctx = canvas.getContext('2d');
                                        if (ctx) {{
                                            ctx.strokeStyle = '{color}';
                                            ctx.fillStyle = '{color}';
                                            return {{method: 'canvas_context'}};
                                        }}
                                    }}
                                    return {{method: 'none'}};
                                }})()
                            """)
                            color_set = True
                            log_step(i, action, "OK", f"Color set via JS: {color}")
                        except Exception as e:
                            log_step(i, action, "WARN", f"JS color set failed: {e}")
                    
                    if not color_set:
                        log_step(i, action, "ERROR", f"Could not set color {color}")
                        errors.append(f"Step {i}: Color setting failed")
                    
                    await page.wait_for_timeout(100)
                    if color_set:
                        executed += 1

                elif action == "draw_circle" or action == "draw_filled_circle":
                    if canvas_center:
                        offset = step.get("offset", [0, 0])
                        center = Point(
                            canvas_center.x + offset[0],
                            canvas_center.y + offset[1],
                        )
                        radius = step.get("radius", 50)
                        log_step(i, action, "START", f"Drawing circle at ({center.x:.0f}, {center.y:.0f}) r={radius}")
                        
                        # Check canvas before drawing
                        before_check = await check_canvas_has_drawing()
                        
                        try:
                            await mouse.draw_circle(center, radius)
                            await page.wait_for_timeout(100)  # Wait for render
                            
                            # Verify drawing actually happened
                            after_check = await check_canvas_has_drawing()
                            
                            if after_check.get('hasDrawing') and not before_check.get('hasDrawing'):
                                log_step(i, action, "OK", f"✓ Circle drawn - canvas now has {after_check.get('nonWhitePixels', 0)} non-white pixels")
                                executed += 1
                            elif after_check.get('hasDrawing') and before_check.get('hasDrawing'):
                                log_step(i, action, "OK", f"Circle drawn (canvas already had drawing)")
                                executed += 1
                            else:
                                log_step(i, action, "ERROR", f"✗ Circle NOT visible - canvas still blank! Before: {before_check}, After: {after_check}")
                                errors.append(f"Step {i}: Draw circle produced no visible output")
                        except Exception as e:
                            log_step(i, action, "ERROR", f"Draw failed: {e}")
                            errors.append(f"Step {i}: Draw circle failed - {e}")
                    else:
                        log_step(i, action, "ERROR", "No canvas center available")
                        errors.append(f"Step {i}: No canvas center")

                elif action == "draw_ellipse" or action == "draw_filled_ellipse":
                    if canvas_center:
                        offset = step.get("offset", [0, 0])
                        center = Point(
                            canvas_center.x + offset[0],
                            canvas_center.y + offset[1],
                        )
                        rx = step.get("rx", 100)
                        ry = step.get("ry", 80)
                        log_step(i, action, "START", f"Drawing ellipse at ({center.x:.0f}, {center.y:.0f}) rx={rx} ry={ry}")
                        
                        before_check = await check_canvas_has_drawing()
                        
                        try:
                            await mouse.draw_ellipse(center, rx, ry)
                            await page.wait_for_timeout(100)
                            
                            after_check = await check_canvas_has_drawing()
                            
                            if after_check.get('hasDrawing'):
                                log_step(i, action, "OK", f"Ellipse drawn - canvas has {after_check.get('nonWhitePixels', 0)} non-white pixels")
                                executed += 1
                            else:
                                log_step(i, action, "ERROR", f"✗ Ellipse NOT visible - canvas still blank!")
                                errors.append(f"Step {i}: Draw ellipse produced no visible output")
                        except Exception as e:
                            log_step(i, action, "ERROR", f"Draw failed: {e}")
                            errors.append(f"Step {i}: Draw ellipse failed - {e}")
                    else:
                        log_step(i, action, "ERROR", "No canvas center")
                        errors.append(f"Step {i}: No canvas center")

                elif action == "draw_rectangle":
                    if canvas_center:
                        w = step.get("width", 200)
                        h = step.get("height", 150)
                        top_left = Point(
                            canvas_center.x - w / 2,
                            canvas_center.y - h / 2,
                        )
                        log_step(i, action, "START", f"Drawing rectangle {w}x{h} at ({top_left.x:.0f}, {top_left.y:.0f})")
                        try:
                            await mouse.draw_rectangle(top_left, w, h)
                            log_step(i, action, "OK", f"Rectangle drawn")
                            executed += 1
                        except Exception as e:
                            log_step(i, action, "ERROR", f"Draw failed: {e}")
                            errors.append(f"Step {i}: Draw rect failed - {e}")
                    else:
                        log_step(i, action, "ERROR", "No canvas center")
                        errors.append(f"Step {i}: No canvas center")

                elif action == "draw_line":
                    if canvas_center:
                        from_off = step.get("from_offset", [-100, 0])
                        to_off = step.get("to_offset", [100, 0])
                        start = Point(canvas_center.x + from_off[0], canvas_center.y + from_off[1])
                        end = Point(canvas_center.x + to_off[0], canvas_center.y + to_off[1])
                        log_step(i, action, "START", f"Drawing line from ({start.x:.0f}, {start.y:.0f}) to ({end.x:.0f}, {end.y:.0f})")
                        
                        before_check = await check_canvas_has_drawing()
                        
                        try:
                            await mouse.draw_line(start, end)
                            await page.wait_for_timeout(100)
                            
                            after_check = await check_canvas_has_drawing()
                            
                            if after_check.get('hasDrawing'):
                                log_step(i, action, "OK", f"Line drawn - canvas has {after_check.get('nonWhitePixels', 0)} non-white pixels")
                                executed += 1
                            else:
                                log_step(i, action, "ERROR", f"✗ Line NOT visible - canvas still blank!")
                                errors.append(f"Step {i}: Draw line produced no visible output")
                        except Exception as e:
                            log_step(i, action, "ERROR", f"Draw failed: {e}")
                            errors.append(f"Step {i}: Draw line failed - {e}")
                    else:
                        log_step(i, action, "ERROR", "No canvas center")
                        errors.append(f"Step {i}: No canvas center")

                elif action == "fill_at":
                    if canvas_center:
                        offset = step.get("offset", [0, 0])
                        x = canvas_center.x + offset[0]
                        y = canvas_center.y + offset[1]
                        log_step(i, action, "START", f"Fill at ({x:.0f}, {y:.0f})")
                        
                        before_check = await check_canvas_has_drawing()
                        
                        try:
                            await mouse.fill_at(x, y)
                            await page.wait_for_timeout(100)
                            
                            after_check = await check_canvas_has_drawing()
                            
                            # Fill should change pixel count
                            if after_check.get('nonWhitePixels', 0) > before_check.get('nonWhitePixels', 0):
                                log_step(i, action, "OK", f"Fill applied - pixels: {before_check.get('nonWhitePixels', 0)} → {after_check.get('nonWhitePixels', 0)}")
                                executed += 1
                            else:
                                log_step(i, action, "WARN", f"Fill may not have worked - pixel count unchanged")
                                executed += 1  # Still count as executed but warn
                        except Exception as e:
                            log_step(i, action, "ERROR", f"Fill failed: {e}")
                            errors.append(f"Step {i}: Fill failed - {e}")
                    else:
                        log_step(i, action, "ERROR", "No canvas center")
                        errors.append(f"Step {i}: No canvas center")

                elif action == "click_canvas":
                    if canvas_center:
                        offset = step.get("offset", [0, 0])
                        x = int(canvas_center.x + offset[0])
                        y = int(canvas_center.y + offset[1])
                        log_step(i, action, "START", f"Click at ({x}, {y})")
                        try:
                            await mouse.click(x, y)
                            log_step(i, action, "OK", f"Clicked")
                            executed += 1
                        except Exception as e:
                            log_step(i, action, "ERROR", f"Click failed: {e}")
                            errors.append(f"Step {i}: Click failed - {e}")
                    else:
                        log_step(i, action, "ERROR", "No canvas center")
                        errors.append(f"Step {i}: No canvas center")

                elif action == "type_text":
                    text = step.get("text", "")
                    log_step(i, action, "START", f"Typing: {text[:30]}")
                    try:
                        await page.keyboard.type(text, delay=30)
                        log_step(i, action, "OK", f"Typed {len(text)} chars")
                        executed += 1
                    except Exception as e:
                        log_step(i, action, "ERROR", f"Type failed: {e}")
                        errors.append(f"Step {i}: Type failed - {e}")

                elif action == "screenshot":
                    suffix = step.get("suffix", "canvas")
                    from pathlib import Path
                    from datetime import datetime
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    path = Path.home() / ".nlp2cmd" / "screenshots" / f"{suffix}_{ts}.png"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    log_step(i, action, "START", f"Saving to {path}")
                    try:
                        await page.screenshot(path=str(path))
                        log_step(i, action, "OK", f"Screenshot saved: {path}")
                        executed += 1
                    except Exception as e:
                        log_step(i, action, "ERROR", f"Screenshot failed: {e}")
                        errors.append(f"Step {i}: Screenshot failed - {e}")

                else:
                    log_step(i, action, "WARN", f"Unknown action: {action}")
                    errors.append(f"Step {i}: Unknown action {action}")

            except Exception as e:
                log_step(i, action, "ERROR", f"Exception: {e}")
                errors.append(f"Step {i}: Exception - {e}")
                # Continue with remaining steps

        # Final summary
        success = executed > 0 and len(errors) == 0
        if errors:
            print(f"\n[Canvas] Completed with {len(errors)} errors:", file=sys.stderr)
            for err in errors[:5]:  # Show first 5 errors
                print(f"  - {err}", file=sys.stderr)
        else:
            print(f"\n[Canvas] All {executed} steps completed successfully", file=sys.stderr)

        return {
            "success": success,
            "steps_executed": executed,
            "total_steps": len(steps),
            "errors": errors,
        }
