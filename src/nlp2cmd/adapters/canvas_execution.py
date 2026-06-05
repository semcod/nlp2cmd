"""Canvas drawing plan execution on Playwright pages."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from nlp2cmd.adapters.canvas_constants import TOOLS_JSPAINT
from nlp2cmd.automation.mouse_controller import MouseController, Point

StepHandler = Callable[["PlanContext", dict, int, int, str], Awaitable[None]]


def _log_step(step_num: int, total: int, action: str, status: str, details: str = "") -> None:
    prefix = f"[Canvas {step_num}/{total}]"
    if status == "OK":
        print(f"{prefix} ✓ {action}: {details}", file=sys.stderr)
    elif status == "ERROR":
        print(f"{prefix} ✗ {action} FAILED: {details}", file=sys.stderr)
    else:
        print(f"{prefix} → {action}: {details}", file=sys.stderr)


async def _check_canvas_has_drawing(page: Any) -> dict:
    try:
        return await page.evaluate("""
            () => {
                const canvas = document.querySelector('canvas');
                if (!canvas) return {error: 'No canvas found'};
                const ctx = canvas.getContext('2d');
                const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                const data = imageData.data;
                let nonWhitePixels = 0;
                const totalPixels = data.length / 4;
                for (let i = 0; i < data.length; i += 400) {
                    const r = data[i];
                    const g = data[i + 1];
                    const b = data[i + 2];
                    const a = data[i + 3];
                    if (!(r === 255 && g === 255 && b === 255) && a > 0) {
                        nonWhitePixels++;
                    }
                }
                return {
                    totalPixels: totalPixels,
                    nonWhitePixels: nonWhitePixels,
                    hasDrawing: nonWhitePixels > 10,
                    isBlank: nonWhitePixels <= 10
                };
            }
        """)
    except Exception as e:
        return {"error": str(e), "hasDrawing": False}


@dataclass
class PlanContext:
    page: Any
    mouse: MouseController
    canvas_center: Optional[Point] = None
    canvas_box: Optional[dict] = None
    executed: int = 0
    errors: list[str] = field(default_factory=list)

    def mark_ok(self) -> None:
        self.executed += 1

    def add_error(self, step_i: int, message: str) -> None:
        self.errors.append(f"Step {step_i}: {message}")


async def _step_navigate(ctx: PlanContext, step: dict, i: int, total: int, action: str) -> None:
    url = step.get("url", "")
    _log_step(i, total, action, "START", f"Navigating to {url}")
    await ctx.page.goto(url, wait_until="networkidle", timeout=15000)
    current_url = ctx.page.url
    if url in current_url or "jspaint" in current_url:
        _log_step(i, total, action, "OK", f"Loaded: {current_url[:50]}")
        ctx.mark_ok()
    else:
        _log_step(i, total, action, "ERROR", f"Wrong URL: {current_url}")
        ctx.add_error(i, f"Navigation failed - got {current_url}")


async def _step_wait(ctx: PlanContext, step: dict, i: int, total: int, action: str) -> None:
    ms = step.get("ms", 1000)
    _log_step(i, total, action, "START", f"Waiting {ms}ms")
    await ctx.page.wait_for_timeout(ms)
    _log_step(i, total, action, "OK", f"Waited {ms}ms")
    ctx.mark_ok()


async def _step_wait_for_canvas(ctx: PlanContext, step: dict, i: int, total: int, action: str) -> None:
    _log_step(i, total, action, "START", "Looking for canvas element")
    try:
        await ctx.page.wait_for_selector("canvas", timeout=10000)
        canvas_info = await ctx.page.evaluate("""
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
        if canvas_info.get("visible"):
            _log_step(i, total, action, "OK", f"Canvas ready: {canvas_info}")
            ctx.mark_ok()
        else:
            _log_step(i, total, action, "ERROR", f"Canvas not visible: {canvas_info}")
            ctx.add_error(i, "Canvas not visible")
    except Exception as e:
        _log_step(i, total, action, "ERROR", f"Canvas not found: {e}")
        ctx.add_error(i, f"Canvas wait failed - {e}")


async def _step_get_canvas_info(ctx: PlanContext, step: dict, i: int, total: int, action: str) -> None:
    _log_step(i, total, action, "START", "Getting canvas dimensions")
    canvas_el = await ctx.page.query_selector("canvas")
    if not canvas_el:
        _log_step(i, total, action, "ERROR", "Canvas element not found")
        ctx.add_error(i, "Canvas element is None")
        return
    ctx.canvas_box = await canvas_el.bounding_box()
    if not ctx.canvas_box:
        _log_step(i, total, action, "ERROR", "Canvas has no bounding box")
        ctx.add_error(i, "Canvas bounding box is None")
        return
    ctx.canvas_center = Point(
        ctx.canvas_box["x"] + ctx.canvas_box["width"] / 2,
        ctx.canvas_box["y"] + ctx.canvas_box["height"] / 2,
    )
    _log_step(
        i, total, action, "OK",
        f"Center: ({ctx.canvas_center.x:.0f}, {ctx.canvas_center.y:.0f}), "
        f"Size: {ctx.canvas_box['width']:.0f}x{ctx.canvas_box['height']:.0f}",
    )
    ctx.mark_ok()


async def _step_select_tool(ctx: PlanContext, step: dict, i: int, total: int, action: str) -> None:
    tool_name = step.get("tool", "brush")
    _log_step(i, total, action, "START", f"Selecting tool: {tool_name}")
    tool_info = TOOLS_JSPAINT.get(tool_name)
    if not tool_info:
        _log_step(i, total, action, "ERROR", f"Unknown tool: {tool_name}")
        ctx.add_error(i, f"Unknown tool {tool_name}")
        return

    el = await ctx.page.query_selector(tool_info["selector"])
    if el:
        await el.click()
        await ctx.page.wait_for_timeout(300)
        is_active = await ctx.page.evaluate(f"""
            () => {{
                const tool = document.querySelector('{tool_info["selector"]}');
                return tool && (tool.classList.contains('selected') || tool.getAttribute('aria-pressed') === 'true');
            }}
        """)
        status = "OK" if is_active else "WARN"
        detail = f"Tool {tool_name} selected via selector" if is_active else f"Tool {tool_name} clicked but may not be active"
        _log_step(i, total, action, status, detail)
        ctx.mark_ok()
        return

    tools = await ctx.page.query_selector_all(".tool")
    idx = tool_info.get("fallback_idx", 0)
    if 0 <= idx < len(tools):
        await tools[idx].click()
        await ctx.page.wait_for_timeout(300)
        _log_step(i, total, action, "OK", f"Tool {tool_name} selected via index {idx}")
        ctx.mark_ok()
    else:
        _log_step(i, total, action, "ERROR", f"Tool index {idx} out of range ({len(tools)} tools)")
        ctx.add_error(i, "Tool selection failed")


async def _step_set_color(ctx: PlanContext, step: dict, i: int, total: int, action: str) -> None:
    color = step.get("color", "#000000")
    _log_step(i, total, action, "START", f"Setting color: {color}")
    color_set = False

    try:
        color_result = await ctx.page.evaluate(f"""
            () => {{
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
        if color_result.get("method") == "click":
            color_set = True
            _log_step(i, total, action, "OK", f"Color set via palette click: {color_result}")
    except Exception as e:
        _log_step(i, total, action, "WARN", f"Palette click failed: {e}")

    if not color_set:
        try:
            await ctx.page.evaluate(f"""
                (() => {{
                    if (typeof window.set_foreground_color === 'function') {{
                        window.set_foreground_color('{color}');
                        return {{method: 'jspaint_api'}};
                    }}
                    const canvas = document.querySelector('canvas');
                    if (canvas) {{
                        const ctx2d = canvas.getContext('2d');
                        if (ctx2d) {{
                            ctx2d.strokeStyle = '{color}';
                            ctx2d.fillStyle = '{color}';
                            return {{method: 'canvas_context'}};
                        }}
                    }}
                    return {{method: 'none'}};
                }})()
            """)
            color_set = True
            _log_step(i, total, action, "OK", f"Color set via JS: {color}")
        except Exception as e:
            _log_step(i, total, action, "WARN", f"JS color set failed: {e}")

    if not color_set:
        _log_step(i, total, action, "ERROR", f"Could not set color {color}")
        ctx.add_error(i, "Color setting failed")
    else:
        await ctx.page.wait_for_timeout(100)
        ctx.mark_ok()


async def _require_canvas_center(ctx: PlanContext, i: int, total: int, action: str) -> bool:
    if ctx.canvas_center:
        return True
    _log_step(i, total, action, "ERROR", "No canvas center")
    ctx.add_error(i, "No canvas center")
    return False


async def _step_draw_circle(ctx: PlanContext, step: dict, i: int, total: int, action: str) -> None:
    if not await _require_canvas_center(ctx, i, total, action):
        return
    offset = step.get("offset", [0, 0])
    center = Point(ctx.canvas_center.x + offset[0], ctx.canvas_center.y + offset[1])
    radius = step.get("radius", 50)
    _log_step(i, total, action, "START", f"Drawing circle at ({center.x:.0f}, {center.y:.0f}) r={radius}")
    before_check = await _check_canvas_has_drawing(ctx.page)
    try:
        await ctx.mouse.draw_circle(center, radius)
        await ctx.page.wait_for_timeout(100)
        after_check = await _check_canvas_has_drawing(ctx.page)
        if after_check.get("hasDrawing"):
            _log_step(i, total, action, "OK", f"Circle drawn - canvas has {after_check.get('nonWhitePixels', 0)} non-white pixels")
            ctx.mark_ok()
        else:
            _log_step(i, total, action, "ERROR", f"Circle NOT visible - Before: {before_check}, After: {after_check}")
            ctx.add_error(i, "Draw circle produced no visible output")
    except Exception as e:
        _log_step(i, total, action, "ERROR", f"Draw failed: {e}")
        ctx.add_error(i, f"Draw circle failed - {e}")


async def _step_draw_ellipse(ctx: PlanContext, step: dict, i: int, total: int, action: str) -> None:
    if not await _require_canvas_center(ctx, i, total, action):
        return
    offset = step.get("offset", [0, 0])
    center = Point(ctx.canvas_center.x + offset[0], ctx.canvas_center.y + offset[1])
    rx = step.get("rx", 100)
    ry = step.get("ry", 80)
    _log_step(i, total, action, "START", f"Drawing ellipse at ({center.x:.0f}, {center.y:.0f}) rx={rx} ry={ry}")
    before_check = await _check_canvas_has_drawing(ctx.page)
    try:
        await ctx.mouse.draw_ellipse(center, rx, ry)
        await ctx.page.wait_for_timeout(100)
        after_check = await _check_canvas_has_drawing(ctx.page)
        if after_check.get("hasDrawing"):
            _log_step(i, total, action, "OK", f"Ellipse drawn - canvas has {after_check.get('nonWhitePixels', 0)} non-white pixels")
            ctx.mark_ok()
        else:
            _log_step(i, total, action, "ERROR", "Ellipse NOT visible - canvas still blank!")
            ctx.add_error(i, "Draw ellipse produced no visible output")
    except Exception as e:
        _log_step(i, total, action, "ERROR", f"Draw failed: {e}")
        ctx.add_error(i, f"Draw ellipse failed - {e}")


async def _step_draw_rectangle(ctx: PlanContext, step: dict, i: int, total: int, action: str) -> None:
    if not await _require_canvas_center(ctx, i, total, action):
        return
    w = step.get("width", 200)
    h = step.get("height", 150)
    top_left = Point(ctx.canvas_center.x - w / 2, ctx.canvas_center.y - h / 2)
    _log_step(i, total, action, "START", f"Drawing rectangle {w}x{h} at ({top_left.x:.0f}, {top_left.y:.0f})")
    try:
        await ctx.mouse.draw_rectangle(top_left, w, h)
        _log_step(i, total, action, "OK", "Rectangle drawn")
        ctx.mark_ok()
    except Exception as e:
        _log_step(i, total, action, "ERROR", f"Draw failed: {e}")
        ctx.add_error(i, f"Draw rect failed - {e}")


async def _step_draw_line(ctx: PlanContext, step: dict, i: int, total: int, action: str) -> None:
    if not await _require_canvas_center(ctx, i, total, action):
        return
    from_off = step.get("from_offset", [-100, 0])
    to_off = step.get("to_offset", [100, 0])
    start = Point(ctx.canvas_center.x + from_off[0], ctx.canvas_center.y + from_off[1])
    end = Point(ctx.canvas_center.x + to_off[0], ctx.canvas_center.y + to_off[1])
    _log_step(i, total, action, "START", f"Drawing line from ({start.x:.0f}, {start.y:.0f}) to ({end.x:.0f}, {end.y:.0f})")
    before_check = await _check_canvas_has_drawing(ctx.page)
    try:
        await ctx.mouse.draw_line(start, end)
        await ctx.page.wait_for_timeout(100)
        after_check = await _check_canvas_has_drawing(ctx.page)
        if after_check.get("hasDrawing"):
            _log_step(i, total, action, "OK", f"Line drawn - canvas has {after_check.get('nonWhitePixels', 0)} non-white pixels")
            ctx.mark_ok()
        else:
            _log_step(i, total, action, "ERROR", "Line NOT visible - canvas still blank!")
            ctx.add_error(i, "Draw line produced no visible output")
    except Exception as e:
        _log_step(i, total, action, "ERROR", f"Draw failed: {e}")
        ctx.add_error(i, f"Draw line failed - {e}")


async def _step_fill_at(ctx: PlanContext, step: dict, i: int, total: int, action: str) -> None:
    if not await _require_canvas_center(ctx, i, total, action):
        return
    offset = step.get("offset", [0, 0])
    x = ctx.canvas_center.x + offset[0]
    y = ctx.canvas_center.y + offset[1]
    _log_step(i, total, action, "START", f"Fill at ({x:.0f}, {y:.0f})")
    before_check = await _check_canvas_has_drawing(ctx.page)
    try:
        await ctx.mouse.fill_at(x, y)
        await ctx.page.wait_for_timeout(100)
        after_check = await _check_canvas_has_drawing(ctx.page)
        if after_check.get("nonWhitePixels", 0) > before_check.get("nonWhitePixels", 0):
            _log_step(i, total, action, "OK", f"Fill applied - pixels: {before_check.get('nonWhitePixels', 0)} → {after_check.get('nonWhitePixels', 0)}")
        else:
            _log_step(i, total, action, "WARN", "Fill may not have worked - pixel count unchanged")
        ctx.mark_ok()
    except Exception as e:
        _log_step(i, total, action, "ERROR", f"Fill failed: {e}")
        ctx.add_error(i, f"Fill failed - {e}")


async def _step_click_canvas(ctx: PlanContext, step: dict, i: int, total: int, action: str) -> None:
    if not await _require_canvas_center(ctx, i, total, action):
        return
    offset = step.get("offset", [0, 0])
    x = int(ctx.canvas_center.x + offset[0])
    y = int(ctx.canvas_center.y + offset[1])
    _log_step(i, total, action, "START", f"Click at ({x}, {y})")
    try:
        await ctx.mouse.click(x, y)
        _log_step(i, total, action, "OK", "Clicked")
        ctx.mark_ok()
    except Exception as e:
        _log_step(i, total, action, "ERROR", f"Click failed: {e}")
        ctx.add_error(i, f"Click failed - {e}")


async def _step_type_text(ctx: PlanContext, step: dict, i: int, total: int, action: str) -> None:
    text = step.get("text", "")
    _log_step(i, total, action, "START", f"Typing: {text[:30]}")
    try:
        await ctx.page.keyboard.type(text, delay=30)
        _log_step(i, total, action, "OK", f"Typed {len(text)} chars")
        ctx.mark_ok()
    except Exception as e:
        _log_step(i, total, action, "ERROR", f"Type failed: {e}")
        ctx.add_error(i, f"Type failed - {e}")


async def _step_screenshot(ctx: PlanContext, step: dict, i: int, total: int, action: str) -> None:
    suffix = step.get("suffix", "canvas")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path.home() / ".nlp2cmd" / "screenshots" / f"{suffix}_{ts}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    _log_step(i, total, action, "START", f"Saving to {path}")
    try:
        await ctx.page.screenshot(path=str(path))
        _log_step(i, total, action, "OK", f"Screenshot saved: {path}")
        ctx.mark_ok()
    except Exception as e:
        _log_step(i, total, action, "ERROR", f"Screenshot failed: {e}")
        ctx.add_error(i, f"Screenshot failed - {e}")


STEP_HANDLERS: dict[str, StepHandler] = {
    "navigate": _step_navigate,
    "wait": _step_wait,
    "wait_for_canvas": _step_wait_for_canvas,
    "get_canvas_info": _step_get_canvas_info,
    "select_tool": _step_select_tool,
    "set_color": _step_set_color,
    "draw_circle": _step_draw_circle,
    "draw_filled_circle": _step_draw_circle,
    "draw_ellipse": _step_draw_ellipse,
    "draw_filled_ellipse": _step_draw_ellipse,
    "draw_rectangle": _step_draw_rectangle,
    "draw_line": _step_draw_line,
    "fill_at": _step_fill_at,
    "click_canvas": _step_click_canvas,
    "type_text": _step_type_text,
    "screenshot": _step_screenshot,
}


async def execute_drawing_plan(page: Any, plan_json: str) -> dict[str, Any]:
    """Execute a canvas drawing plan on a Playwright page."""
    try:
        plan = json.loads(plan_json)
    except Exception as e:
        return {"success": False, "error": f"Invalid plan JSON: {e}"}

    steps = plan.get("steps", [])
    ctx = PlanContext(page=page, mouse=MouseController(page, human_like=True))
    total_steps = len(steps)

    for i, step in enumerate(steps, 1):
        action = step.get("action", "")
        handler = STEP_HANDLERS.get(action)
        try:
            if handler is None:
                _log_step(i, total_steps, action, "WARN", f"Unknown action: {action}")
                ctx.add_error(i, f"Unknown action {action}")
                continue
            await handler(ctx, step, i, total_steps, action)
        except Exception as e:
            _log_step(i, total_steps, action, "ERROR", f"Exception: {e}")
            ctx.add_error(i, f"Exception - {e}")

    success = ctx.executed > 0 and len(ctx.errors) == 0
    if ctx.errors:
        print(f"\n[Canvas] Completed with {len(ctx.errors)} errors:", file=sys.stderr)
        for err in ctx.errors[:5]:
            print(f"  - {err}", file=sys.stderr)
    else:
        print(f"\n[Canvas] All {ctx.executed} steps completed successfully", file=sys.stderr)

    return {
        "success": success,
        "steps_executed": ctx.executed,
        "total_steps": len(steps),
        "errors": ctx.errors,
    }
