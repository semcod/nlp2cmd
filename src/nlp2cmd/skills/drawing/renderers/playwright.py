"""
Playwright Renderer — draws on browser canvas via mouse movements.

Uses the existing MouseController for human-like mouse interactions.
Works with any web-based canvas application (jspaint, draw.chat, Excalidraw, etc.).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nlp2cmd.skills.drawing.events import ShapeDrawn
from nlp2cmd.skills.drawing.renderers.base import PointGroup, Renderer


class PlaywrightRenderer(Renderer):
    """
    Render drawings on a browser canvas via Playwright mouse control.

    Usage:
        renderer = PlaywrightRenderer(page)
        await renderer.init_canvas(1024, 768, url="https://jspaint.app")
        await renderer.set_color("#ff0000")
        await renderer.draw_path([(100, 100), (200, 200), (100, 200), (100, 100)])
    """

    def __init__(self, page: Any, human_like: bool = True) -> None:
        self._page = page
        self._human_like = human_like
        self._canvas_box: dict[str, float] | None = None
        self._current_color = "#000000"

    async def init_canvas(self, width: float, height: float, url: str = "", app: str = "generic") -> dict[str, Any]:
        """Navigate to URL and discover the canvas element."""
        if url:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._page.wait_for_timeout(2000)

        # Dismiss common popups
        for text in ["Accept", "Akceptuję", "OK", "Got it", "Close", "×", "Zrozumiałem"]:
            try:
                btn = self._page.get_by_text(text, exact=False).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    await self._page.wait_for_timeout(300)
            except Exception:
                continue

        # Find canvas
        canvas = self._page.locator("canvas").first
        try:
            await canvas.wait_for(state="visible", timeout=10000)
        except Exception:
            await self._page.wait_for_timeout(5000)

        box = await canvas.bounding_box()
        if box:
            self._canvas_box = box
        else:
            self._canvas_box = {"x": 0, "y": 0, "width": width, "height": height}

        return {
            "width": self._canvas_box["width"],
            "height": self._canvas_box["height"],
            "center_x": self._canvas_box["x"] + self._canvas_box["width"] / 2,
            "center_y": self._canvas_box["y"] + self._canvas_box["height"] / 2,
            "offset_x": self._canvas_box["x"],
            "offset_y": self._canvas_box["y"],
        }

    async def set_color(self, color: str) -> None:
        """Set the drawing color via multiple strategies (platform-independent)."""
        self._current_color = color

        # Method 1: JSPaint internal color API
        # jspaint stores foreground color in a global array and uses jQuery events
        try:
            result = await self._page.evaluate(f"""
                (() => {{
                    // jspaint: set_foreground_color or internal colors array
                    if (typeof window.set_foreground_color === 'function') {{
                        window.set_foreground_color('{color}');
                        return 'jspaint_api';
                    }}
                    // jspaint alternative: colors array + trigger
                    if (window.colors && Array.isArray(window.colors)) {{
                        window.colors[0] = '{color}';
                        if (window.$colorbox) {{
                            window.$colorbox.trigger('color-changed');
                        }}
                        return 'jspaint_colors';
                    }}
                    // jspaint: try selecting foreground color via palette click simulation
                    if (window.$) {{
                        const $swatch = window.$('.color-button').first();
                        if ($swatch.length) {{
                            // Store color for when jspaint reads it
                            window.$swatch_fg_color = '{color}';
                        }}
                    }}
                    return null;
                }})()
            """)
            if result:
                return
        except Exception:
            pass

        # Method 2: Click matching color in palette (jspaint bottom color bar)
        try:
            # jspaint palette: colored divs at bottom of screen
            palette_selectors = [
                f'.color-button[style*="{color}"]',
                f'[data-color="{color}"]',
            ]
            for sel in palette_selectors:
                el = self._page.locator(sel).first
                if await el.count() > 0:
                    await el.click()
                    await self._page.wait_for_timeout(100)
                    return
        except Exception:
            pass

        # Method 3: HTML5 color input element
        try:
            ci = self._page.locator('input[type="color"]').first
            if await ci.count() > 0:
                await ci.evaluate(
                    f'el => {{ el.value = "{color}"; '
                    f'el.dispatchEvent(new Event("input", {{bubbles: true}})); '
                    f'el.dispatchEvent(new Event("change", {{bubbles: true}})); }}'
                )
                return
        except Exception:
            pass

        # Method 4: Direct canvas context (fallback, may be overridden by app)
        try:
            await self._page.evaluate(f"""
                (() => {{
                    const canvas = document.querySelector('canvas');
                    if (canvas) {{
                        const ctx = canvas.getContext('2d');
                        if (ctx) {{
                            ctx.strokeStyle = '{color}';
                            ctx.fillStyle = '{color}';
                        }}
                    }}
                }})()
            """)
        except Exception:
            pass

    async def draw_path(self, points: PointGroup, color: str = "", fill: bool = False) -> None:
        """Draw a continuous path on the canvas via mouse movements."""
        if not points or len(points) < 2:
            return

        if color and color != self._current_color:
            await self.set_color(color)

        ox = self._canvas_box["x"] if self._canvas_box else 0
        oy = self._canvas_box["y"] if self._canvas_box else 0

        x0, y0 = points[0]
        await self._page.mouse.move(ox + x0, oy + y0)
        await self._page.mouse.down()

        for x, y in points[1:]:
            await self._page.mouse.move(ox + x, oy + y)
            await self._page.wait_for_timeout(10 if self._human_like else 2)

        await self._page.mouse.up()
        await self._page.wait_for_timeout(50)

    async def draw_shape(self, event: ShapeDrawn) -> None:
        """Render a ShapeDrawn event by drawing all its point groups."""
        if event.color:
            await self.set_color(event.color)

        for group in event.points:
            await self.draw_path(group, color=event.color, fill=event.fill)

    async def clear(self) -> None:
        """Clear the canvas via Ctrl+A, Delete or JS."""
        try:
            await self._page.keyboard.press("Control+a")
            await self._page.keyboard.press("Delete")
        except Exception:
            try:
                await self._page.evaluate("""
                    () => {
                        const canvas = document.querySelector('canvas');
                        if (canvas) {
                            const ctx = canvas.getContext('2d');
                            ctx.clearRect(0, 0, canvas.width, canvas.height);
                            ctx.fillStyle = '#ffffff';
                            ctx.fillRect(0, 0, canvas.width, canvas.height);
                        }
                    }
                """)
            except Exception:
                pass

    async def screenshot(self, path: str) -> str | None:
        """Take a screenshot of the page."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            await self._page.screenshot(path=str(p))
            return str(p)
        except Exception:
            return None

    async def dispose(self) -> None:
        """No-op — page lifecycle is managed externally."""
        pass
