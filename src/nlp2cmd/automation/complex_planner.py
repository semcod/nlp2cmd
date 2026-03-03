"""
Complex command planner for NLP2CMD.

Decomposes complex natural language commands into sequences of executable
action steps. Uses LLM (OpenRouter) for planning complex multi-step tasks,
with template-based fallback for common patterns.

Example:
    "wejdź na jspaint.app i narysuj okrąg z czerwonym tłem jak biedronka"
    → [navigate, wait_canvas, select_ellipse, set_color_red, draw_circle,
       fill_red, set_color_black, draw_dots, screenshot]
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Optional

_DEBUG = os.environ.get("NLP2CMD_DEBUG", "").lower() in ("1", "true", "yes")


def _debug(msg: str) -> None:
    if _DEBUG:
        print(f"DEBUG [ComplexPlanner] {msg}", file=sys.stderr, flush=True)


@dataclass
class ActionStep:
    """Single step in a complex command execution plan."""
    action: str  # e.g. "navigate", "select_tool", "draw_circle", "screenshot"
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    wait_after_ms: int = 0
    requires: list[str] = field(default_factory=list)  # dependency on prior step results

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"action": self.action}
        if self.params:
            d["params"] = self.params
        if self.description:
            d["description"] = self.description
        if self.wait_after_ms:
            d["wait_after_ms"] = self.wait_after_ms
        return d


@dataclass
class ExecutionPlan:
    """Complete execution plan for a complex command."""
    query: str
    steps: list[ActionStep] = field(default_factory=list)
    source: str = "template"  # "template" or "llm"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "steps": [s.to_dict() for s in self.steps],
            "source": self.source,
            "metadata": self.metadata,
        }


# ── Template-based plans for common complex commands ─────────────────

DRAWING_PATTERNS: list[dict[str, Any]] = [
    {
        "pattern": r"(?:narysuj|draw)\s+(?:biedronk[eęa]|ladybug)",
        "description": "Draw a ladybug (red body, black dots, head, antennae)",
        "steps": [
            ActionStep("navigate", {"url": "https://jspaint.app"}, "Open JSPaint", 3000),
            ActionStep("wait_for_canvas", {}, "Wait for canvas to load", 1000),
            ActionStep("get_canvas_center", {}, "Get canvas dimensions"),
            # Body — red filled ellipse
            ActionStep("set_color", {"color": "#FF0000"}, "Set color to red"),
            ActionStep("draw_filled_ellipse", {"rx": 120, "ry": 120, "relative_to": "center"},
                       "Draw red circle body"),
            # Center dividing line
            ActionStep("set_color", {"color": "#000000"}, "Set color to black"),
            ActionStep("draw_line", {"from_offset": (0, -120), "to_offset": (0, 120)},
                       "Draw center line"),
            # Head — black filled circle at top
            ActionStep("draw_filled_circle", {"radius": 30, "offset": (0, -135)},
                       "Draw ladybug head"),
            # Antennae
            ActionStep("draw_line", {"from_offset": (-10, -160), "to_offset": (-30, -190)},
                       "Draw left antenna"),
            ActionStep("draw_line", {"from_offset": (10, -160), "to_offset": (30, -190)},
                       "Draw right antenna"),
            # Dots — black filled circles
            ActionStep("draw_filled_circle", {"radius": 14, "offset": (-40, -35)},
                       "Draw dot 1 (left-top)"),
            ActionStep("draw_filled_circle", {"radius": 14, "offset": (40, -35)},
                       "Draw dot 2 (right-top)"),
            ActionStep("draw_filled_circle", {"radius": 14, "offset": (-50, 20)},
                       "Draw dot 3 (left-mid)"),
            ActionStep("draw_filled_circle", {"radius": 14, "offset": (50, 20)},
                       "Draw dot 4 (right-mid)"),
            ActionStep("draw_filled_circle", {"radius": 12, "offset": (-30, 65)},
                       "Draw dot 5 (left-bottom)"),
            ActionStep("draw_filled_circle", {"radius": 12, "offset": (30, 65)},
                       "Draw dot 6 (right-bottom)"),
            ActionStep("screenshot", {"suffix": "ladybug"}, "Take screenshot", 500),
        ],
    },
    {
        "pattern": r"(?:narysuj|draw)\s+(?:okr[aąę]g|circle|ko[lł]o)",
        "description": "Draw a circle",
        "steps": [
            ActionStep("navigate", {"url": "https://jspaint.app"}, "Open JSPaint", 3000),
            ActionStep("wait_for_canvas", {}, "Wait for canvas", 1000),
            ActionStep("get_canvas_center", {}, "Get canvas dimensions"),
            ActionStep("select_tool", {"tool": "ellipse"}, "Select ellipse tool"),
            ActionStep("set_color", {"color": "#000000"}, "Set color to black"),
            ActionStep("draw_circle", {"radius": 100, "relative_to": "center"},
                       "Draw circle"),
            ActionStep("screenshot", {"suffix": "circle"}, "Take screenshot", 500),
        ],
    },
    {
        "pattern": r"(?:narysuj|draw)\s+(?:prostok[aą]t|rectangle|kwadrat|square)",
        "description": "Draw a rectangle",
        "steps": [
            ActionStep("navigate", {"url": "https://jspaint.app"}, "Open JSPaint", 3000),
            ActionStep("wait_for_canvas", {}, "Wait for canvas", 1000),
            ActionStep("get_canvas_center", {}, "Get canvas dimensions"),
            ActionStep("select_tool", {"tool": "rectangle"}, "Select rectangle tool"),
            ActionStep("set_color", {"color": "#000000"}, "Set color to black"),
            ActionStep("draw_rectangle", {"width": 200, "height": 150, "relative_to": "center"},
                       "Draw rectangle"),
            ActionStep("screenshot", {"suffix": "rectangle"}, "Take screenshot", 500),
        ],
    },
    {
        "pattern": r"(?:napisz|write|type)\s+(?:tekst|text)\s+['\"]?(.+?)['\"]?\s+(?:na|on)",
        "description": "Write text on canvas",
        "steps": [
            ActionStep("navigate", {"url": "https://jspaint.app"}, "Open JSPaint", 3000),
            ActionStep("wait_for_canvas", {}, "Wait for canvas", 1000),
            ActionStep("get_canvas_center", {}, "Get canvas dimensions"),
            ActionStep("select_tool", {"tool": "text"}, "Select text tool"),
            ActionStep("click_canvas", {"offset": (0, 0)}, "Click canvas center"),
            ActionStep("type_text", {"text": "{captured_text}"}, "Type text"),
            ActionStep("screenshot", {"suffix": "text"}, "Take screenshot", 500),
        ],
    },
]

BROWSER_PATTERNS: list[dict[str, Any]] = [
    {
        "pattern": r"(?:otw[oó]rz|open)\s+(\d+)\s+(?:tab[oóy]w|tabs?|kart)",
        "description": "Open multiple tabs",
        "steps": [
            ActionStep("open_tabs", {"count": "{captured_count}"}, "Open multiple browser tabs"),
        ],
    },
    {
        "pattern": r"(?:wyci[aą]gnij|extract|skopiuj|copy)\s+(?:klucz|key)\s+(?:API|api).*?(?:z|from)\s+(\w+)",
        "description": "Extract API key from service",
        "steps": [
            ActionStep("extract_api_key", {"service": "{captured_service}"},
                       "Extract API key from browser"),
            ActionStep("save_to_env", {"service": "{captured_service}"},
                       "Save to .env file"),
        ],
    },
]

DESKTOP_PATTERNS: list[dict[str, Any]] = [
    {
        "pattern": r"(?:otw[oó]rz|open)\s+(?:przegl[aą]dark[eę]|browser|chrome|firefox)",
        "description": "Open browser",
        "steps": [
            ActionStep("launch_app", {"app": "browser"}, "Launch browser"),
            ActionStep("wait", {"ms": 2000}, "Wait for browser to start"),
        ],
    },
    {
        "pattern": r"(?:otw[oó]rz|open)\s+(?:thunderbird|mail|poczt[eę])",
        "description": "Open email client",
        "steps": [
            ActionStep("launch_app", {"app": "thunderbird"}, "Launch email client"),
            ActionStep("wait", {"ms": 3000}, "Wait for Thunderbird to start"),
        ],
    },
    {
        "pattern": r"(?:sprawdz|check)\s+(?:poczt[eę]|mail|email)",
        "description": "Check email",
        "steps": [
            ActionStep("launch_app", {"app": "thunderbird"}, "Launch/focus Thunderbird"),
            ActionStep("wait", {"ms": 2000}, "Wait for app"),
            ActionStep("keyboard_shortcut", {"keys": "ctrl+shift+t"},
                       "Get new messages"),
        ],
    },
    {
        "pattern": r"(?:zr[oó]b|take)\s+(?:screenshot|zrzut)",
        "description": "Take screenshot",
        "steps": [
            ActionStep("screenshot_desktop", {"path": "auto"}, "Take desktop screenshot"),
        ],
    },
    {
        "pattern": r"(?:zminimalizuj|minimize)\s+(?:wszystko|all)",
        "description": "Minimize all windows",
        "steps": [
            ActionStep("shell_command", {"command": "wmctrl -k on"}, "Show desktop"),
        ],
    },
]

CAPTCHA_PATTERNS: list[dict[str, Any]] = [
    {
        "pattern": r"(?:rozwiąż|solve|rozwiaz)\s+(?:captcha|CAPTCHA)",
        "description": "Solve CAPTCHA on page",
        "steps": [
            ActionStep("detect_captcha", {}, "Detect CAPTCHA type"),
            ActionStep("solve_captcha", {}, "Solve CAPTCHA via LLM vision"),
        ],
    },
]

ALL_PATTERNS = DRAWING_PATTERNS + BROWSER_PATTERNS + DESKTOP_PATTERNS + CAPTCHA_PATTERNS


class ComplexCommandPlanner:
    """
    Decomposes complex NL commands into executable action plans.

    Two modes:
    1. Template matching — fast, deterministic, for known patterns
    2. LLM planning — flexible, for novel complex commands

    Template matching is tried first. If no template matches,
    the query is sent to OpenRouter LLM for decomposition.
    """

    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
    DEFAULT_MODEL = "google/gemini-2.5-pro-preview"

    SYSTEM_PROMPT = """\
You are an action planner for NLP2CMD desktop automation.
Given a natural language command, decompose it into a JSON array of action steps.

Available actions:
- navigate: {url} — open a URL in browser
- wait: {ms} — wait milliseconds
- wait_for_canvas: {} — wait for canvas element
- get_canvas_center: {} — get canvas dimensions
- select_tool: {tool} — select drawing tool (pencil, brush, fill, ellipse, rectangle, line, text, eraser, select)
- set_color: {color} — set foreground color (#RRGGBB)
- set_line_width: {width} — set stroke width
- draw_circle: {radius, offset?} — draw circle outline
- draw_ellipse: {rx, ry, offset?} — draw ellipse outline
- draw_rectangle: {width, height, offset?} — draw rectangle outline
- draw_line: {from_offset, to_offset} — draw line relative to center
- draw_filled_ellipse: {rx, ry, offset?, rotation?} — draw and fill ellipse
- draw_filled_circle: {radius, offset?} — draw and fill circle
- draw_filled_rectangle: {width, height, offset?} — draw and fill rectangle
- draw_arc: {radius, start_angle, end_angle, offset?, fill?} — draw arc
- draw_polygon: {points, offset?, fill?} — draw polygon from point list
- draw_bezier: {curves, offset?, fill?, close?} — draw bezier curve
- draw_svg_path: {d, offset?, fill?, scale?} — draw SVG path data
- fill_at: {offset} — click with fill bucket tool
- click_canvas: {offset} — click on canvas
- type_text: {text} — type text
- screenshot: {suffix?} — take screenshot
- launch_app: {app} — launch desktop app
- keyboard_shortcut: {keys} — press keyboard shortcut
- shell_command: {command} — run shell command
- extract_api_key: {service} — extract API key from browser
- save_to_env: {service, path?} — save to .env
- detect_captcha: {} — detect CAPTCHA
- solve_captcha: {} — solve CAPTCHA
- open_tabs: {urls: [...]} — open multiple tabs

Reply with ONLY a JSON array of objects: [{"action": "...", "params": {...}, "description": "..."}]
No explanations, no markdown, just JSON.
"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or self.DEFAULT_MODEL

    async def plan(self, query: str) -> ExecutionPlan:
        """
        Create an execution plan for a complex command.

        Routing priority:
        1. Dynamic Orchestrator (LLM-driven, if available)
        2. Template matching (hardcoded, deprecated — kept as fallback)
        3. Direct LLM planning via OpenRouter
        4. URL extraction fallback

        Args:
            query: Natural language command

        Returns:
            ExecutionPlan with ordered ActionSteps
        """
        _debug(f"Planning: {query[:100]}")

        # [NEW] Try dynamic orchestrator first (LLM-driven planning with reflection)
        plan = await self._orchestrator_plan(query)
        if plan:
            _debug(f"Orchestrator plan: {len(plan.steps)} steps")
            return plan

        # [DEPRECATED] Template matching — kept as fallback only
        plan = self._match_template(query)
        if plan:
            _debug(f"Template match (deprecated fallback): {plan.metadata.get('pattern_desc', '?')}")
            return plan

        # Fall back to LLM planning
        if self.api_key:
            plan = await self._llm_plan(query)
            if plan:
                _debug(f"LLM plan: {len(plan.steps)} steps")
                return plan

        # Last resort: simple navigation if URL detected
        url = self._extract_url(query)
        if url:
            return ExecutionPlan(
                query=query,
                steps=[ActionStep("navigate", {"url": url}, f"Open {url}", 2000)],
                source="fallback",
            )

        return ExecutionPlan(
            query=query,
            steps=[ActionStep("echo", {"message": f"Could not plan: {query}"}, "No plan")],
            source="none",
        )

    async def _orchestrator_plan(self, query: str) -> Optional[ExecutionPlan]:
        """Try to plan via the dynamic orchestration engine (LLM-driven)."""
        try:
            from nlp2cmd.orchestration import Orchestrator
            orch = Orchestrator()
            schema = await orch.plan(query)
            if schema and schema.steps:
                steps = [
                    ActionStep(
                        action=s.action,
                        params=s.params,
                        description=s.description,
                    )
                    for s in schema.steps
                ]
                return ExecutionPlan(
                    query=query,
                    steps=steps,
                    source="orchestrator",
                    metadata={"domain": schema.domain, "goal": schema.goal},
                )
        except Exception as exc:
            _debug(f"Orchestrator planning unavailable: {exc}")
        return None

    def _match_template(self, query: str) -> Optional[ExecutionPlan]:
        """Match query against known template patterns."""
        query_lower = query.lower()

        for pattern_config in ALL_PATTERNS:
            m = re.search(pattern_config["pattern"], query_lower)
            if m:
                steps = []
                for step_template in pattern_config["steps"]:
                    # Clone and resolve captured groups
                    params = dict(step_template.params)
                    for key, value in params.items():
                        if isinstance(value, str) and "{captured_" in value:
                            # Replace with captured group
                            try:
                                group_name = value.replace("{captured_", "").replace("}", "")
                                if group_name == "text" and m.lastindex and m.lastindex >= 1:
                                    params[key] = m.group(1)
                                elif group_name == "count" and m.lastindex and m.lastindex >= 1:
                                    params[key] = int(m.group(1))
                                elif group_name == "service" and m.lastindex and m.lastindex >= 1:
                                    params[key] = m.group(1)
                            except (IndexError, ValueError):
                                pass

                    # Check for URL in query and inject into navigate steps
                    if step_template.action == "navigate" and "url" not in params:
                        url = self._extract_url(query)
                        if url:
                            params["url"] = url

                    steps.append(ActionStep(
                        action=step_template.action,
                        params=params,
                        description=step_template.description,
                        wait_after_ms=step_template.wait_after_ms,
                    ))

                # Extract color from query and inject into relevant steps
                color = self._extract_color(query)
                if color:
                    for step in steps:
                        if step.action == "set_color" and step.params.get("color") == "#000000":
                            # Only override default black, not intentional colors
                            pass

                return ExecutionPlan(
                    query=query,
                    steps=steps,
                    source="template",
                    metadata={"pattern_desc": pattern_config["description"]},
                )

        return None

    async def _llm_plan(self, query: str) -> Optional[ExecutionPlan]:
        """Use LLM to decompose a complex command into steps."""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.OPENROUTER_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/wronai/nlp2cmd",
                        "X-Title": "NLP2CMD Complex Planner",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": self.SYSTEM_PROMPT},
                            {"role": "user", "content": query},
                        ],
                        "max_tokens": 2000,
                        "temperature": 0.1,
                    },
                    timeout=30,
                )

                if resp.status_code != 200:
                    _debug(f"LLM API error: {resp.status_code}")
                    return None

                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()

                # Parse JSON from response (handle markdown code blocks)
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)

                steps_data = json.loads(content)
                if not isinstance(steps_data, list):
                    return None

                steps = []
                for sd in steps_data:
                    steps.append(ActionStep(
                        action=sd.get("action", "unknown"),
                        params=sd.get("params", {}),
                        description=sd.get("description", ""),
                        wait_after_ms=sd.get("wait_after_ms", 0),
                    ))

                return ExecutionPlan(
                    query=query,
                    steps=steps,
                    source="llm",
                    metadata={"model": self.model},
                )

        except Exception as e:
            _debug(f"LLM planning error: {e}")
            return None

    @staticmethod
    def _extract_url(text: str) -> Optional[str]:
        """Extract URL from text."""
        m = re.search(r"(https?://\S+)", text)
        if m:
            return m.group(1).rstrip(".,)")
        m = re.search(
            r"\b([a-z0-9][a-z0-9-]*(?:\.[a-z0-9][a-z0-9-]*)+)(/\S*)?\b",
            text, re.IGNORECASE,
        )
        if m:
            return f"https://{m.group(1)}{m.group(2) or ''}"
        return None

    @staticmethod
    def _extract_color(text: str) -> Optional[str]:
        """Extract color from Polish/English text."""
        color_map = {
            "czerwon": "#FF0000", "red": "#FF0000",
            "czarn": "#000000", "black": "#000000",
            "biał": "#FFFFFF", "white": "#FFFFFF",
            "żółt": "#FFFF00", "yellow": "#FFFF00",
            "niebiesk": "#0000FF", "blue": "#0000FF",
            "zielon": "#00FF00", "green": "#00FF00",
            "pomarańcz": "#FFA500", "orange": "#FFA500",
            "fiolet": "#800080", "purple": "#800080",
            "różow": "#FFC0CB", "pink": "#FFC0CB",
            "szar": "#808080", "gray": "#808080", "grey": "#808080",
            "brązow": "#8B4513", "brown": "#8B4513",
        }
        text_lower = text.lower()
        for keyword, hex_color in color_map.items():
            if keyword in text_lower:
                return hex_color
        # Also match hex codes
        m = re.search(r"#[0-9a-fA-F]{6}", text)
        if m:
            return m.group(0)
        return None
