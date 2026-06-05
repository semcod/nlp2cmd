"""
DrawObjectSkill — Shape resolution and rendering with vision feedback.

Handles the full lifecycle of drawing a single object:
1. Resolve shape (registry → online database → LLM generation)
2. Render on canvas via PlaywrightRenderer
3. Quick vision check that something was actually drawn

Pipeline:
    resolve_shape → set_color → render → vision_verify_drawn

Single Responsibility: Turn a shape name/description into pixels on canvas.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class DrawStatus(Enum):
    """Status of a single object draw operation."""
    PENDING = "pending"
    RESOLVING = "resolving"
    DRAWING = "drawing"
    DRAWN = "drawn"
    VERIFIED = "verified"
    FAILED = "failed"


@dataclass
class ObjectDrawResult:
    """Result of drawing a single object."""
    shape_name: str
    status: DrawStatus = DrawStatus.PENDING
    color: str = ""
    center_x: float = 0
    center_y: float = 0
    size: float = 100
    source: str = ""           # "registry", "database", "llm", "fallback"
    draw_time_ms: float = 0
    vision_check: str = ""     # Brief vision description of what was drawn
    vision_confirmed: bool = False
    error: str = ""


@dataclass
class SceneDrawResult:
    """Result of drawing multiple objects (a scene)."""
    objects: list[ObjectDrawResult] = field(default_factory=list)
    total_time_ms: float = 0
    objects_drawn: int = 0
    objects_verified: int = 0
    objects_failed: int = 0

    @property
    def success(self) -> bool:
        return self.objects_drawn > 0 and self.objects_failed == 0

    @property
    def partial(self) -> bool:
        return self.objects_drawn > 0 and self.objects_failed > 0

    def summary(self) -> str:
        parts = []
        for obj in self.objects:
            icon = {"verified": "✅", "drawn": "✓", "failed": "✗"}.get(
                obj.status.value, "?"
            )
            parts.append(f"{icon} {obj.shape_name} ({obj.source})")
        return ", ".join(parts)


QUICK_VERIFY_PROMPT = """Look at this screenshot of a drawing canvas.

I just drew a {shape_name} in {color} at approximately the center area.
Can you see it? Answer briefly in JSON:
{{
  "drawn": true,
  "what_i_see": "a red star shape in the center of the canvas",
  "confidence": 0.9
}}"""


class DrawObjectSkill:
    """
    Resolve and draw shapes with vision verification.

    Composes:
    - ShapeRegistry (built-in shapes)
    - ObjectFetcher (online databases: Iconify, SimpleIcons, SVGRepo)
    - TextToShapeEngine (LLM-generated vertices)
    - PlaywrightRenderer (browser drawing)
    - Vision LLM (quick draw verification)

    Usage:
        drawer = DrawObjectSkill(renderer, skill)
        result = await drawer.draw("car", color="#FF0000", cx=400, cy=300)

        # Draw multiple objects as a scene
        scene = await drawer.draw_scene(
            [("star", "#FFD700"), ("house", "#8B4513"), ("tree", "#228B22")],
            canvas_width=1024, canvas_height=768,
        )
    """

    def __init__(self, renderer=None, skill=None, use_vision: bool = True):
        """
        Args:
            renderer: PlaywrightRenderer instance (for browser drawing)
            skill: DrawingSkill instance (for shape generation)
            use_vision: Whether to use vision model for draw verification
        """
        self._renderer = renderer
        self._skill = skill
        self._use_vision = use_vision
        self._router = None
        self._page = None

    def set_renderer(self, renderer, page=None):
        """Set or update the renderer (and optionally the page for vision)."""
        self._renderer = renderer
        if page is not None:
            self._page = page

    def set_skill(self, skill):
        """Set or update the DrawingSkill."""
        self._skill = skill

    def _get_router(self):
        if self._router is None:
            from nlp2cmd.skills.drawing.llm_helpers import get_drawing_router
            self._router = get_drawing_router()
        return self._router

    def _ensure_skill(self):
        if self._skill is None:
            from nlp2cmd.skills.drawing.skill import DrawingSkill
            self._skill = DrawingSkill()
        return self._skill

    # ── Main draw entry point ─────────────────────────────────────────

    async def draw(
        self,
        shape_name: str,
        color: str = "#000000",
        cx: float = 0,
        cy: float = 0,
        size: float = 100,
        verify: bool = True,
        verbose: bool = False,
    ) -> ObjectDrawResult:
        """
        Resolve shape, draw it on canvas, optionally verify with vision.

        Args:
            shape_name: Shape name (e.g. "car", "star", "butterfly")
            color: Hex color code
            cx: Center X coordinate
            cy: Center Y coordinate
            size: Shape size
            verify: Whether to vision-verify after drawing
            verbose: Print progress

        Returns:
            ObjectDrawResult with status and details
        """
        result = ObjectDrawResult(
            shape_name=shape_name, color=color,
            center_x=cx, center_y=cy, size=size,
        )
        t0 = time.time()

        # Step 1: Resolve shape
        result.status = DrawStatus.RESOLVING
        source = await self._resolve_shape(shape_name, verbose)
        result.source = source

        if source == "not_found":
            result.status = DrawStatus.FAILED
            result.error = f"Shape '{shape_name}' not found in any source"
            result.draw_time_ms = (time.time() - t0) * 1000
            return result

        if verbose:
            print(f"  📦 {shape_name}: resolved from {source}")

        # Step 2: Draw
        result.status = DrawStatus.DRAWING
        try:
            skill = self._ensure_skill()
            event = skill.draw(shape_name, color=color,
                               center_x=cx, center_y=cy, size=size)

            if self._renderer:
                await self._renderer.set_color(color)
                await self._renderer.draw_shape(event)

            result.status = DrawStatus.DRAWN
            if verbose:
                print(f"  ✏️  {shape_name}: drawn at ({cx:.0f}, {cy:.0f})")

        except Exception as e:
            result.status = DrawStatus.FAILED
            result.error = str(e)
            result.draw_time_ms = (time.time() - t0) * 1000
            if verbose:
                print(f"  ⚠ {shape_name}: draw failed — {e}")
            return result

        # Step 3: Vision verify
        if verify and self._use_vision and self._page:
            vision_result = await self._quick_verify(shape_name, color, verbose)
            if vision_result:
                result.vision_check = vision_result.get("what_i_see", "")
                result.vision_confirmed = vision_result.get("drawn", False)
                if result.vision_confirmed:
                    result.status = DrawStatus.VERIFIED

        result.draw_time_ms = (time.time() - t0) * 1000
        return result

    # ── Scene drawing ─────────────────────────────────────────────────

    async def draw_scene(
        self,
        objects: list[tuple[str, str]],
        canvas_width: float = 1024,
        canvas_height: float = 768,
        verify_each: bool = False,
        verify_final: bool = True,
        verbose: bool = False,
    ) -> SceneDrawResult:
        """
        Draw multiple objects in an auto-layout grid.

        Args:
            objects: List of (shape_name, color) tuples
            canvas_width: Canvas width for layout
            canvas_height: Canvas height for layout
            verify_each: Vision-verify each individual shape
            verify_final: Vision-verify the final scene
            verbose: Print progress

        Returns:
            SceneDrawResult with per-object results
        """
        import math
        t0 = time.time()
        scene = SceneDrawResult()

        n = len(objects)
        cols = min(n, max(1, int(math.ceil(math.sqrt(n)))))
        rows = max(1, math.ceil(n / cols))
        cell_w = canvas_width / (cols + 1)
        cell_h = canvas_height / (rows + 1)
        shape_size = min(cell_w, cell_h) * 0.35

        for i, (shape_name, color) in enumerate(objects):
            row = i // cols
            col = i % cols
            cx = (col + 1) * cell_w
            cy = (row + 1) * cell_h

            obj_result = await self.draw(
                shape_name, color=color,
                cx=cx, cy=cy, size=shape_size,
                verify=verify_each, verbose=verbose,
            )
            scene.objects.append(obj_result)

            if obj_result.status in (DrawStatus.DRAWN, DrawStatus.VERIFIED):
                scene.objects_drawn += 1
                if obj_result.status == DrawStatus.VERIFIED:
                    scene.objects_verified += 1
            else:
                scene.objects_failed += 1

        scene.total_time_ms = (time.time() - t0) * 1000
        return scene

    # ── Shape resolution ──────────────────────────────────────────────

    async def _resolve_shape(self, shape_name: str, verbose: bool) -> str:
        """
        Resolve shape from multiple sources.
        Returns source name or "not_found".
        """
        from nlp2cmd.skills.drawing.shapes import ShapeRegistry

        # Source 1: Built-in registry
        if shape_name in ShapeRegistry.available():
            return "registry"

        # Source 2: Online databases (Iconify, SimpleIcons, SVGRepo)
        try:
            from nlp2cmd.skills.drawing.object_fetcher import ObjectFetcher
            from nlp2cmd.skills.drawing.text_to_shape import DynamicShapeGenerator

            fetcher = ObjectFetcher()
            fetched = await fetcher.fetch(shape_name, verbose=verbose)
            if fetched and fetched.points:
                gen = DynamicShapeGenerator(shape_name, fetched.points)
                ShapeRegistry.register(gen)
                return f"database:{fetched.source}"
        except Exception:
            pass

        # Source 3: LLM generation
        try:
            from nlp2cmd.skills.drawing.text_to_shape import TextToShapeEngine

            engine = TextToShapeEngine(auto_register=True)
            generated = await engine.generate(shape_name, complex_mode=True,
                                              verbose=verbose)
            if generated and generated.points:
                return f"llm:{generated.model_used}"
        except Exception:
            pass

        # Source 4: Fallback — use circle
        if verbose:
            print(f"  ⚠ '{shape_name}' not found, using circle fallback")

        return "not_found"

    # ── Vision verification ───────────────────────────────────────────

    async def _quick_verify(self, shape_name: str, color: str,
                            verbose: bool) -> dict | None:
        """Quick vision check that something was drawn."""
        router = self._get_router()
        if router is None or self._page is None:
            return None

        try:
            screenshot_bytes = await self._page.screenshot()
            b64 = base64.b64encode(screenshot_bytes).decode()

            prompt = QUICK_VERIFY_PROMPT.format(
                shape_name=shape_name, color=color,
            )

            resp = await router.route_call(
                prompt=prompt,
                task_category="vision",
                images=[b64],
                timeout=15,
            )

            if resp and resp.text:
                data = self._parse_json(resp.text)
                if data and verbose:
                    drawn = data.get("drawn", False)
                    desc = data.get("what_i_see", "")[:60]
                    icon = "✅" if drawn else "❌"
                    print(f"  {icon} Vision: {desc}")
                return data
        except Exception:
            pass
        return None

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        from nlp2cmd.skills.drawing.llm_helpers import parse_llm_json_object
        return parse_llm_json_object(text)
