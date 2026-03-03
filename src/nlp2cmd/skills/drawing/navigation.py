"""
DrawNavigationSkill — Vision-guided canvas discovery and browser navigation.

Uses Qwen VL (via LLM Router vision task) to:
1. Navigate to drawing sites with intelligent fallback
2. Verify canvas is visible and ready (vision confirmation)
3. Dismiss popups using both heuristic + vision strategies
4. Select drawing tools (pencil/brush) with vision guidance

Pipeline:
    navigate → vision_verify → dismiss_popups → select_tool → ready

Single Responsibility: Get the browser to a state where drawing can begin.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class NavigationState(Enum):
    """State of the navigation process."""
    IDLE = "idle"
    NAVIGATING = "navigating"
    VERIFYING = "verifying"
    DISMISSING_POPUPS = "dismissing_popups"
    SELECTING_TOOL = "selecting_tool"
    READY = "ready"
    FAILED = "failed"


@dataclass
class CanvasInfo:
    """Information about the discovered canvas."""
    url: str = ""
    site_name: str = ""
    width: float = 0
    height: float = 0
    offset_x: float = 0
    offset_y: float = 0
    has_canvas: bool = False
    tool_selected: str = ""
    popups_dismissed: int = 0
    vision_confirmed: bool = False
    vision_description: str = ""
    navigation_time_ms: float = 0


@dataclass
class NavigationStep:
    """A single step in the navigation process."""
    action: str
    success: bool = False
    detail: str = ""
    duration_ms: float = 0
    vision_used: bool = False


@dataclass
class NavigationResult:
    """Full result of the navigation process."""
    state: NavigationState = NavigationState.IDLE
    canvas: CanvasInfo = field(default_factory=CanvasInfo)
    steps: list[NavigationStep] = field(default_factory=list)
    error: str = ""

    @property
    def success(self) -> bool:
        return self.state == NavigationState.READY

    @property
    def total_time_ms(self) -> float:
        return sum(s.duration_ms for s in self.steps)


# ── Drawing site registry ─────────────────────────────────────────────────

DRAWING_SITES = {
    "jspaint": {
        "urls": ["https://jspaint.app", "https://jspaint.app/"],
        "canvas_selector": "canvas",
        "tool_selector": ".tool[title*='Pencil'], .tool[title*='pencil']",
        "fallback_order": 1,
    },
    "excalidraw": {
        "urls": ["https://excalidraw.com/", "https://excalidraw.com"],
        "canvas_selector": "canvas",
        "tool_selector": None,
        "fallback_order": 2,
    },
    "kleki": {
        "urls": ["https://kleki.com/", "https://kleki.com"],
        "canvas_selector": "canvas",
        "tool_selector": None,
        "fallback_order": 3,
    },
    "draw.chat": {
        "urls": [
            "https://draw.chat/",
            "https://draw.chat/pl/index.html",
            "https://draw.chat/en/index.html",
        ],
        "canvas_selector": "canvas",
        "tool_selector": None,
        "fallback_order": 4,
    },
}

POPUP_TEXTS = [
    "Accept", "Accept all", "Akceptuję", "Zaakceptuj wszystko",
    "Accept cookies", "Agree", "Zgadzam się", "I understand", "Rozumiem",
    "OK", "Got it", "Close", "Zamknij", "×", "Zrozumiałem",
    "Skip", "Pomiń", "No thanks", "Not now", "Później", "Nie teraz",
    "Maybe later", "Continue", "Kontynuuj", "Dalej",
]

POPUP_CSS_SELECTORS = [
    '[class*="cookie"] button', '[class*="consent"] button',
    '[id*="cookie"] button', '[id*="consent"] button',
    '[class*="gdpr"] button', '.cc-dismiss', '.cc-allow',
    '#onetrust-accept-btn-handler',
    'button[aria-label="Close"]', 'button[aria-label="close"]',
    '[class*="modal"] button[class*="close"]',
    '[role="dialog"] button[class*="close"]',
]

CANVAS_VERIFY_PROMPT = """Analyze this screenshot of a web application.

Answer these questions in JSON format:
1. Is there a drawing canvas visible? (yes/no)
2. Is the canvas ready for drawing (no popups/modals blocking it)?
3. What drawing tool is currently selected (pencil/brush/none/unknown)?
4. Are there any popups, modals, or cookie banners visible?
5. Brief description of what you see.

Respond ONLY with JSON:
{
  "has_canvas": true,
  "canvas_ready": true,
  "current_tool": "pencil",
  "has_popups": false,
  "popup_description": "",
  "description": "MS Paint clone with white canvas and tool palette on left"
}"""

FIND_POPUP_CLOSE_PROMPT = """Look at this screenshot. There are popups or modals blocking the canvas.

Find the close/dismiss/accept button for each popup. Return the approximate pixel coordinates
of each button to click, in order of priority.

Respond ONLY with JSON:
{
  "buttons": [
    {"label": "Accept cookies", "x": 500, "y": 400, "priority": 1},
    {"label": "Close modal", "x": 800, "y": 200, "priority": 2}
  ]
}"""

FIND_TOOL_PROMPT = """Look at this screenshot of a drawing application.

I need to select the pencil/freehand drawing tool. Find the button or icon
for the pencil/pen/brush/freehand tool.

Return the approximate pixel coordinates of the tool button.

Respond ONLY with JSON:
{
  "found": true,
  "tool_name": "pencil",
  "x": 50,
  "y": 200,
  "confidence": 0.9
}"""


# ── DrawNavigationSkill ───────────────────────────────────────────────────

class DrawNavigationSkill:
    """
    Vision-guided navigation to drawing canvas.

    Uses Qwen VL to verify canvas state, find/dismiss popups,
    and select drawing tools — replacing brittle CSS selector heuristics.

    Usage:
        nav = DrawNavigationSkill()
        result = await nav.navigate(page, site="jspaint")
        if result.success:
            print(f"Canvas ready: {result.canvas.width}x{result.canvas.height}")
    """

    def __init__(self, max_retries: int = 2, use_vision: bool = True):
        self._router = None
        self._max_retries = max_retries
        self._use_vision = use_vision

    def _get_router(self):
        """Lazy-init LLM router for vision calls."""
        if self._router is None:
            try:
                from nlp2cmd.llm.router import get_router
                self._router = get_router()
            except ImportError:
                self._router = None
        return self._router

    async def _vision_call(self, page, prompt: str) -> dict | None:
        """Take screenshot and send to vision model, return parsed JSON."""
        if not self._use_vision:
            return None

        router = self._get_router()
        if router is None:
            return None

        try:
            screenshot_bytes = await page.screenshot()
            b64 = base64.b64encode(screenshot_bytes).decode()

            resp = await router.route_call(
                prompt=prompt,
                task_category="vision",
                images=[b64],
                timeout=30,
            )

            if resp and resp.text:
                return self._parse_json(resp.text)
        except Exception:
            pass
        return None

    # ── Main navigation entry point ───────────────────────────────────

    async def navigate(
        self,
        page,
        site: str = "jspaint",
        fallback: bool = True,
        verbose: bool = False,
    ) -> NavigationResult:
        """
        Navigate to a drawing site and prepare canvas for drawing.

        Args:
            page: Playwright page
            site: Site key from DRAWING_SITES or URL
            fallback: Try other sites if primary fails
            verbose: Print progress

        Returns:
            NavigationResult with canvas info and step details
        """
        result = NavigationResult(state=NavigationState.NAVIGATING)
        t0 = time.time()

        # Build ordered list of sites to try
        sites_to_try = self._build_site_order(site, fallback)

        for site_name, site_info in sites_to_try:
            if verbose:
                print(f"  🌐 Trying {site_name}...")

            step_result = await self._try_site(page, site_name, site_info, verbose)
            result.steps.extend(step_result.steps)

            if step_result.success:
                result.state = NavigationState.READY
                result.canvas = step_result.canvas
                result.canvas.navigation_time_ms = (time.time() - t0) * 1000
                return result

        result.state = NavigationState.FAILED
        result.error = "No drawing site available"
        return result

    async def _try_site(self, page, site_name: str, site_info: dict,
                        verbose: bool) -> NavigationResult:
        """Try to navigate to a single site and prepare canvas."""
        result = NavigationResult()

        # Step 1: Navigate
        nav_step = await self._navigate_to_site(page, site_name, site_info, verbose)
        result.steps.append(nav_step)
        if not nav_step.success:
            return result

        # Step 2: Dismiss popups (heuristic first)
        popup_step = await self._dismiss_popups_heuristic(page, verbose)
        result.steps.append(popup_step)

        # Step 3: Vision verification — is canvas visible and ready?
        verify_step = await self._verify_canvas_vision(page, verbose)
        result.steps.append(verify_step)

        canvas_ready = verify_step.success
        vision_data = None

        if verify_step.detail:
            vision_data = self._parse_json(verify_step.detail) if isinstance(verify_step.detail, str) else None

        # Step 4: If vision says popups still visible, try vision-guided dismiss
        if vision_data and vision_data.get("has_popups"):
            vision_popup_step = await self._dismiss_popups_vision(page, verbose)
            result.steps.append(vision_popup_step)
            # Re-verify
            verify_step2 = await self._verify_canvas_vision(page, verbose)
            result.steps.append(verify_step2)
            canvas_ready = verify_step2.success

        # Step 5: Find canvas element and get dimensions
        if canvas_ready or not self._use_vision:
            canvas_step = await self._discover_canvas(page, site_info, verbose)
            result.steps.append(canvas_step)
            if canvas_step.success:
                result.canvas = self._parse_canvas_info(
                    canvas_step.detail, site_name, page.url
                )
                result.canvas.vision_confirmed = verify_step.vision_used and verify_step.success
                if vision_data:
                    result.canvas.vision_description = vision_data.get("description", "")

                # Step 6: Select drawing tool
                tool_step = await self._select_tool(page, site_info, verbose)
                result.steps.append(tool_step)
                if tool_step.success:
                    result.canvas.tool_selected = tool_step.detail
                    result.state = NavigationState.READY
                else:
                    # Tool selection failure is non-fatal
                    result.state = NavigationState.READY

                return result

        result.state = NavigationState.FAILED
        return result

    # ── Step implementations ──────────────────────────────────────────

    async def _navigate_to_site(self, page, site_name: str, site_info: dict,
                                verbose: bool) -> NavigationStep:
        """Navigate to site URLs with fallback."""
        t0 = time.time()
        urls = site_info.get("urls", [])
        if not urls:
            urls = [site_name] if site_name.startswith("http") else []

        for url in urls:
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                status = response.status if response else 0
                if status in (404, 410, 500, 502, 503):
                    continue

                await page.wait_for_timeout(2000)

                return NavigationStep(
                    action="navigate",
                    success=True,
                    detail=page.url,
                    duration_ms=(time.time() - t0) * 1000,
                )
            except Exception:
                continue

        return NavigationStep(
            action="navigate",
            success=False,
            detail=f"All {len(urls)} URLs failed for {site_name}",
            duration_ms=(time.time() - t0) * 1000,
        )

    async def _dismiss_popups_heuristic(self, page, verbose: bool) -> NavigationStep:
        """Dismiss popups using text matching and CSS selectors."""
        t0 = time.time()
        dismissed = 0

        for text in POPUP_TEXTS:
            try:
                btn = page.get_by_text(text, exact=False).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click(timeout=2000)
                    await page.wait_for_timeout(300)
                    dismissed += 1
            except Exception:
                continue

        for sel in POPUP_CSS_SELECTORS:
            try:
                el = page.locator(sel).first
                if await el.count() > 0 and await el.is_visible():
                    await el.click(timeout=2000)
                    await page.wait_for_timeout(300)
                    dismissed += 1
            except Exception:
                continue

        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(300)
        except Exception:
            pass

        return NavigationStep(
            action="dismiss_popups_heuristic",
            success=True,
            detail=f"{dismissed} dismissed",
            duration_ms=(time.time() - t0) * 1000,
        )

    async def _verify_canvas_vision(self, page, verbose: bool) -> NavigationStep:
        """Use vision model to verify canvas is visible and ready."""
        t0 = time.time()

        data = await self._vision_call(page, CANVAS_VERIFY_PROMPT)
        if data is None:
            # No vision available — fall back to DOM check
            has_canvas = await self._check_canvas_dom(page)
            return NavigationStep(
                action="verify_canvas",
                success=has_canvas,
                detail="dom_check_only",
                duration_ms=(time.time() - t0) * 1000,
                vision_used=False,
            )

        has_canvas = data.get("has_canvas", False)
        canvas_ready = data.get("canvas_ready", False)

        if verbose:
            desc = data.get("description", "")[:80]
            print(f"  👁️ Vision: canvas={'✓' if has_canvas else '✗'}, "
                  f"ready={'✓' if canvas_ready else '✗'} — {desc}")

        import json
        return NavigationStep(
            action="verify_canvas",
            success=has_canvas and canvas_ready,
            detail=json.dumps(data),
            duration_ms=(time.time() - t0) * 1000,
            vision_used=True,
        )

    async def _dismiss_popups_vision(self, page, verbose: bool) -> NavigationStep:
        """Use vision to find and click popup close buttons."""
        t0 = time.time()
        dismissed = 0

        data = await self._vision_call(page, FIND_POPUP_CLOSE_PROMPT)
        if data and "buttons" in data:
            buttons = sorted(data["buttons"], key=lambda b: b.get("priority", 99))
            for btn_info in buttons[:5]:
                x = btn_info.get("x", 0)
                y = btn_info.get("y", 0)
                if x > 0 and y > 0:
                    try:
                        await page.mouse.click(x, y)
                        await page.wait_for_timeout(500)
                        dismissed += 1
                        if verbose:
                            print(f"  🖱️ Vision-clicked: {btn_info.get('label', '?')} at ({x},{y})")
                    except Exception:
                        continue

        return NavigationStep(
            action="dismiss_popups_vision",
            success=dismissed > 0,
            detail=f"{dismissed} vision-dismissed",
            duration_ms=(time.time() - t0) * 1000,
            vision_used=True,
        )

    async def _discover_canvas(self, page, site_info: dict,
                               verbose: bool) -> NavigationStep:
        """Find the canvas element and get its bounding box."""
        t0 = time.time()
        selector = site_info.get("canvas_selector", "canvas")

        for attempt in range(10):
            try:
                canvas = page.locator(selector).first
                if await canvas.count() > 0:
                    box = await canvas.bounding_box()
                    if box and box["width"] > 50 and box["height"] > 50:
                        import json
                        return NavigationStep(
                            action="discover_canvas",
                            success=True,
                            detail=json.dumps(box),
                            duration_ms=(time.time() - t0) * 1000,
                        )
            except Exception:
                pass
            await page.wait_for_timeout(1000)

        return NavigationStep(
            action="discover_canvas",
            success=False,
            detail="Canvas not found after polling",
            duration_ms=(time.time() - t0) * 1000,
        )

    async def _select_tool(self, page, site_info: dict,
                           verbose: bool) -> NavigationStep:
        """Select the pencil/drawing tool, first via CSS then via vision."""
        t0 = time.time()

        # Strategy 1: Known CSS selector for the site
        tool_sel = site_info.get("tool_selector")
        if tool_sel:
            try:
                tool_btn = page.locator(tool_sel).first
                if await tool_btn.count() > 0:
                    await tool_btn.click()
                    await page.wait_for_timeout(300)
                    return NavigationStep(
                        action="select_tool",
                        success=True,
                        detail="pencil (css)",
                        duration_ms=(time.time() - t0) * 1000,
                    )
            except Exception:
                pass

        # Strategy 2: Vision-guided tool selection
        data = await self._vision_call(page, FIND_TOOL_PROMPT)
        if data and data.get("found"):
            x = data.get("x", 0)
            y = data.get("y", 0)
            if x > 0 and y > 0:
                try:
                    await page.mouse.click(x, y)
                    await page.wait_for_timeout(300)
                    tool_name = data.get("tool_name", "pencil")
                    if verbose:
                        print(f"  🖌️ Vision selected: {tool_name} at ({x},{y})")
                    return NavigationStep(
                        action="select_tool",
                        success=True,
                        detail=f"{tool_name} (vision)",
                        duration_ms=(time.time() - t0) * 1000,
                        vision_used=True,
                    )
                except Exception:
                    pass

        # Strategy 3: Assume default tool is fine
        return NavigationStep(
            action="select_tool",
            success=True,
            detail="default (no explicit selection)",
            duration_ms=(time.time() - t0) * 1000,
        )

    # ── Helpers ───────────────────────────────────────────────────────

    def _build_site_order(self, primary: str, fallback: bool) -> list[tuple[str, dict]]:
        """Build ordered list of (site_name, site_info) to try."""
        result = []

        if primary in DRAWING_SITES:
            result.append((primary, DRAWING_SITES[primary]))
        elif primary.startswith("http"):
            result.append((primary, {"urls": [primary], "canvas_selector": "canvas"}))

        if fallback:
            others = sorted(
                [(k, v) for k, v in DRAWING_SITES.items() if k != primary],
                key=lambda x: x[1].get("fallback_order", 99),
            )
            result.extend(others)

        return result

    async def _check_canvas_dom(self, page) -> bool:
        """Simple DOM check for canvas presence."""
        try:
            canvas = page.locator("canvas").first
            if await canvas.count() > 0:
                box = await canvas.bounding_box()
                return box is not None and box["width"] > 50 and box["height"] > 50
        except Exception:
            pass
        return False

    def _parse_canvas_info(self, detail_json: str, site_name: str,
                           url: str) -> CanvasInfo:
        """Parse canvas bounding box JSON into CanvasInfo."""
        import json
        try:
            box = json.loads(detail_json)
            return CanvasInfo(
                url=url,
                site_name=site_name,
                width=box.get("width", 0),
                height=box.get("height", 0),
                offset_x=box.get("x", 0),
                offset_y=box.get("y", 0),
                has_canvas=True,
            )
        except Exception:
            return CanvasInfo(url=url, site_name=site_name)

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        """Robustly parse JSON from LLM output."""
        import json
        import re

        clean = text.strip()
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0]
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0]

        if not clean.startswith("{"):
            start = clean.find("{")
            end = clean.rfind("}")
            if start >= 0 and end > start:
                clean = clean[start:end + 1]

        try:
            clean = re.sub(r',\s*}', '}', clean)
            clean = re.sub(r',\s*]', ']', clean)
            return json.loads(clean)
        except json.JSONDecodeError:
            return None
