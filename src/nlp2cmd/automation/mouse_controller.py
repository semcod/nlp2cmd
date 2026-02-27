"""
Advanced mouse controller for NLP2CMD.

Provides human-like mouse movements, Bézier curves, drag & drop,
and geometric shape drawing via Playwright.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Point:
    """2D point for mouse operations."""
    x: float
    y: float

    def __add__(self, other: Point) -> Point:
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Point) -> Point:
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Point:
        return Point(self.x * scalar, self.y * scalar)

    def distance_to(self, other: Point) -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


class MouseController:
    """
    Advanced mouse control via Playwright with human-like movements.

    Supports:
    - Click, double-click, right-click with human-like delays
    - Smooth drag & drop with interpolation
    - Bézier curve movements for natural-looking paths
    - Geometric shape drawing (circle, rectangle, ellipse, line)
    - Dot/spot drawing for patterns (e.g. ladybug spots)
    - Human-like jitter and timing randomization
    """

    def __init__(self, page: Any, human_like: bool = True):
        """
        Initialize mouse controller.

        Args:
            page: Playwright page object
            human_like: Add small random delays and jitter for natural movement
        """
        self.page = page
        self.human_like = human_like

    # ── Helpers ──────────────────────────────────────────────────────

    def _jitter(self, value: float, amount: float = 1.5) -> float:
        """Add small random jitter to a coordinate."""
        if self.human_like:
            return value + random.uniform(-amount, amount)
        return value

    async def _human_delay(self, base_ms: int = 10, variance_ms: int = 5) -> None:
        """Wait with human-like random variance."""
        if self.human_like:
            delay = base_ms + random.randint(-variance_ms, variance_ms)
            await self.page.wait_for_timeout(max(1, delay))
        else:
            await self.page.wait_for_timeout(base_ms)

    # ── Basic operations ─────────────────────────────────────────────

    async def click(self, x: int, y: int, button: str = "left") -> None:
        """Click with human-like delay."""
        await self.page.mouse.click(x, y, button=button, delay=50)

    async def double_click(self, x: int, y: int) -> None:
        """Double-click at coordinates."""
        await self.page.mouse.dblclick(x, y)

    async def right_click(self, x: int, y: int) -> None:
        """Right-click at coordinates."""
        await self.page.mouse.click(x, y, button="right")

    async def move_to(self, x: float, y: float) -> None:
        """Move mouse to coordinates."""
        await self.page.mouse.move(x, y)

    # ── Drag & Drop ──────────────────────────────────────────────────

    async def drag(
        self,
        from_pt: Point,
        to_pt: Point,
        steps: int = 20,
        button: str = "left",
    ) -> None:
        """
        Smooth drag from one point to another with linear interpolation.

        Args:
            from_pt: Starting point
            to_pt: Ending point
            steps: Number of intermediate points (more = smoother)
            button: Mouse button to hold
        """
        await self.page.mouse.move(from_pt.x, from_pt.y)
        await self._human_delay(30)
        await self.page.mouse.down(button=button)

        for i in range(1, steps + 1):
            t = i / steps
            x = self._jitter(from_pt.x + (to_pt.x - from_pt.x) * t)
            y = self._jitter(from_pt.y + (to_pt.y - from_pt.y) * t)
            await self.page.mouse.move(x, y)
            await self._human_delay(8, 3)

        await self.page.mouse.up(button=button)

    # ── Bézier Curves ────────────────────────────────────────────────

    def _compute_bezier(self, control_points: list[Point], steps: int) -> list[Point]:
        """
        De Casteljau algorithm for arbitrary-order Bézier curves.

        Args:
            control_points: Control points defining the curve
            steps: Number of output points

        Returns:
            List of points along the Bézier curve
        """
        result: list[Point] = []
        n = len(control_points) - 1
        for step in range(steps + 1):
            t = step / steps
            pts = [Point(p.x, p.y) for p in control_points]
            for r in range(1, n + 1):
                for i in range(n - r + 1):
                    pts[i] = Point(
                        (1 - t) * pts[i].x + t * pts[i + 1].x,
                        (1 - t) * pts[i].y + t * pts[i + 1].y,
                    )
            result.append(pts[0])
        return result

    async def bezier_move(self, points: list[Point], steps: int = 50) -> None:
        """
        Move mouse along a Bézier curve (no drawing, just movement).

        Args:
            points: Control points for the Bézier curve
            steps: Number of interpolation steps
        """
        curve_points = self._compute_bezier(points, steps)
        for pt in curve_points:
            await self.page.mouse.move(self._jitter(pt.x), self._jitter(pt.y))
            await self._human_delay(5, 2)

    async def bezier_draw(self, points: list[Point], steps: int = 50) -> None:
        """
        Draw (mouse down) along a Bézier curve.

        Args:
            points: Control points for the Bézier curve
            steps: Number of interpolation steps
        """
        curve_points = self._compute_bezier(points, steps)
        await self.page.mouse.move(curve_points[0].x, curve_points[0].y)
        await self.page.mouse.down()

        for pt in curve_points[1:]:
            await self.page.mouse.move(self._jitter(pt.x), self._jitter(pt.y))
            await self._human_delay(5, 2)

        await self.page.mouse.up()

    # ── Geometric Shapes ─────────────────────────────────────────────

    async def draw_circle(
        self,
        center: Point,
        radius: float,
        steps: int = 72,
    ) -> None:
        """
        Draw a circle by tracing points along its circumference.

        Args:
            center: Center point of the circle
            radius: Radius in pixels
            steps: Number of points (more = smoother circle)
        """
        points: list[Point] = []
        for i in range(steps + 1):
            angle = 2 * math.pi * i / steps
            x = center.x + radius * math.cos(angle)
            y = center.y + radius * math.sin(angle)
            points.append(Point(x, y))

        await self.page.mouse.move(points[0].x, points[0].y)
        await self.page.mouse.down()

        for pt in points[1:]:
            await self.page.mouse.move(self._jitter(pt.x, 0.5), self._jitter(pt.y, 0.5))
            await self._human_delay(8, 2)

        await self.page.mouse.up()

    async def draw_ellipse(
        self,
        center: Point,
        rx: float,
        ry: float,
        steps: int = 72,
    ) -> None:
        """
        Draw an ellipse.

        Args:
            center: Center point
            rx: Horizontal radius
            ry: Vertical radius
            steps: Number of points
        """
        points: list[Point] = []
        for i in range(steps + 1):
            angle = 2 * math.pi * i / steps
            x = center.x + rx * math.cos(angle)
            y = center.y + ry * math.sin(angle)
            points.append(Point(x, y))

        await self.page.mouse.move(points[0].x, points[0].y)
        await self.page.mouse.down()

        for pt in points[1:]:
            await self.page.mouse.move(self._jitter(pt.x, 0.5), self._jitter(pt.y, 0.5))
            await self._human_delay(8, 2)

        await self.page.mouse.up()

    async def draw_rectangle(
        self,
        top_left: Point,
        width: float,
        height: float,
    ) -> None:
        """
        Draw a rectangle by tracing its 4 corners.

        Args:
            top_left: Top-left corner
            width: Width in pixels
            height: Height in pixels
        """
        corners = [
            top_left,
            Point(top_left.x + width, top_left.y),
            Point(top_left.x + width, top_left.y + height),
            Point(top_left.x, top_left.y + height),
            top_left,  # close the rectangle
        ]
        await self.page.mouse.move(corners[0].x, corners[0].y)
        await self.page.mouse.down()

        for pt in corners[1:]:
            await self.page.mouse.move(pt.x, pt.y)
            await self._human_delay(20, 5)

        await self.page.mouse.up()

    async def draw_line(self, start: Point, end: Point, steps: int = 10) -> None:
        """
        Draw a straight line.

        Args:
            start: Starting point
            end: Ending point
            steps: Interpolation steps
        """
        await self.page.mouse.move(start.x, start.y)
        await self.page.mouse.down()

        for i in range(1, steps + 1):
            t = i / steps
            x = start.x + (end.x - start.x) * t
            y = start.y + (end.y - start.y) * t
            await self.page.mouse.move(x, y)
            await self._human_delay(10, 3)

        await self.page.mouse.up()

    async def draw_dots(
        self,
        points: list[Point],
        radius: float = 3,
        steps_per_dot: int = 24,
    ) -> None:
        """
        Draw filled dots (small circles) at given positions.
        Useful for patterns like ladybug spots.

        Args:
            points: Center points for each dot
            radius: Radius of each dot
            steps_per_dot: Smoothness of each dot
        """
        for pt in points:
            await self.draw_circle(pt, radius, steps=steps_per_dot)
            await self._human_delay(50, 20)

    async def fill_at(self, x: float, y: float) -> None:
        """
        Single click intended for fill-bucket tool usage.

        Args:
            x: X coordinate to click
            y: Y coordinate to click
        """
        await self.page.mouse.click(int(x), int(y))

    # ── Scroll ───────────────────────────────────────────────────────

    async def scroll(self, x: int, y: int, delta_x: int = 0, delta_y: int = -120) -> None:
        """
        Scroll at a given position.

        Args:
            x: X position
            y: Y position
            delta_x: Horizontal scroll amount
            delta_y: Vertical scroll amount (negative = scroll down)
        """
        await self.page.mouse.move(x, y)
        await self.page.mouse.wheel(delta_x, delta_y)

    # ── Human-like movement ──────────────────────────────────────────

    async def human_move(self, from_pt: Point, to_pt: Point, duration_ms: int = 300) -> None:
        """
        Move mouse with a natural-looking Bézier arc (not a straight line).

        Args:
            from_pt: Starting position
            to_pt: Target position
            duration_ms: Approximate movement duration
        """
        # Create a random control point offset for the arc
        mid = Point(
            (from_pt.x + to_pt.x) / 2 + random.uniform(-50, 50),
            (from_pt.y + to_pt.y) / 2 + random.uniform(-50, 50),
        )
        steps = max(10, duration_ms // 10)
        await self.bezier_move([from_pt, mid, to_pt], steps=steps)
