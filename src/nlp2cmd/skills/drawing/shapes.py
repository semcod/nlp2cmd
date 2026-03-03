"""
Shape generators — geometry for all supported shapes.

Each shape is a registered ShapeGenerator that produces point groups.
New shapes can be added via ShapeRegistry.register() (Open/Closed Principle).
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any


PointGroup = list[tuple[float, float]]


class ShapeGenerator(ABC):
    """Abstract shape generator — one responsibility: produce point groups."""

    name: str = ""

    @abstractmethod
    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        """
        Generate point groups for this shape.

        Args:
            cx: Center X coordinate
            cy: Center Y coordinate
            size: Base size (radius, half-width, etc.)
            **params: Shape-specific parameters

        Returns:
            List of point groups. Each group is a list of (x, y) tuples
            representing a continuous stroke.
        """
        ...


# ── Concrete Shape Generators ────────────────────────────────────────────

class CircleGenerator(ShapeGenerator):
    name = "circle"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        steps = params.get("steps", 36)
        radius = params.get("radius", size)
        pts: PointGroup = []
        for i in range(steps + 1):
            angle = 2 * math.pi * i / steps
            pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
        return [pts]


class EllipseGenerator(ShapeGenerator):
    name = "ellipse"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        steps = params.get("steps", 36)
        rx = params.get("rx", size)
        ry = params.get("ry", size * 0.6)
        pts: PointGroup = []
        for i in range(steps + 1):
            angle = 2 * math.pi * i / steps
            pts.append((cx + rx * math.cos(angle), cy + ry * math.sin(angle)))
        return [pts]


class RectangleGenerator(ShapeGenerator):
    name = "rectangle"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        w = params.get("width", size * 2)
        h = params.get("height", size * 1.4)
        x0, y0 = cx - w / 2, cy - h / 2
        return [[(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h), (x0, y0)]]


class SquareGenerator(ShapeGenerator):
    name = "square"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = params.get("side", size * 2)
        x0, y0 = cx - s / 2, cy - s / 2
        return [[(x0, y0), (x0 + s, y0), (x0 + s, y0 + s), (x0, y0 + s), (x0, y0)]]


class TriangleGenerator(ShapeGenerator):
    name = "triangle"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        return [[(cx, cy - size),
                 (cx - size * 0.87, cy + size * 0.5),
                 (cx + size * 0.87, cy + size * 0.5),
                 (cx, cy - size)]]


class StarGenerator(ShapeGenerator):
    name = "star"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        points_count = params.get("points_count", 5)
        inner_ratio = params.get("inner_ratio", 0.4)
        pts: PointGroup = []
        for i in range(points_count):
            angle = -math.pi / 2 + 2 * math.pi * i / points_count
            pts.append((cx + size * math.cos(angle), cy + size * math.sin(angle)))
            angle2 = angle + math.pi / points_count
            pts.append((cx + size * inner_ratio * math.cos(angle2),
                        cy + size * inner_ratio * math.sin(angle2)))
        pts.append(pts[0])
        return [pts]


class HeartGenerator(ShapeGenerator):
    name = "heart"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        steps = params.get("steps", 60)
        pts: PointGroup = []
        for i in range(steps + 1):
            t = 2 * math.pi * i / steps
            x = 16 * math.sin(t) ** 3
            y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
            pts.append((cx + x * size / 16, cy + y * size / 16))
        return [pts]


class SpiralGenerator(ShapeGenerator):
    name = "spiral"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        turns = params.get("turns", 3)
        points_per_turn = params.get("points_per_turn", 30)
        total = turns * points_per_turn
        pts: PointGroup = []
        for i in range(total):
            t = i / total
            r = size * t
            angle = t * turns * 2 * math.pi
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        return [pts]


class HouseGenerator(ShapeGenerator):
    name = "house"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        body = [(cx - size, cy), (cx + size, cy),
                (cx + size, cy + size * 1.2),
                (cx - size, cy + size * 1.2), (cx - size, cy)]
        roof = [(cx - size * 1.1, cy), (cx, cy - size * 0.8), (cx + size * 1.1, cy)]
        door = [(cx - size * 0.2, cy + size * 0.5), (cx + size * 0.2, cy + size * 0.5),
                (cx + size * 0.2, cy + size * 1.2), (cx - size * 0.2, cy + size * 1.2),
                (cx - size * 0.2, cy + size * 0.5)]
        return [body, roof, door]


class FlowerGenerator(ShapeGenerator):
    name = "flower"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        petals = params.get("petals", 6)
        points_per_petal = params.get("points_per_petal", 20)
        groups: list[PointGroup] = []
        for p in range(petals):
            petal: PointGroup = []
            base_angle = 2 * math.pi * p / petals
            for i in range(points_per_petal):
                t = i / (points_per_petal - 1)
                angle = base_angle + (t - 0.5) * (2 * math.pi / petals)
                r = size * math.sin(t * math.pi)
                petal.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
            groups.append(petal)
        return groups


class SunGenerator(ShapeGenerator):
    name = "sun"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        rays = params.get("rays", 8)
        circle: PointGroup = []
        for i in range(36 + 1):
            angle = 2 * math.pi * i / 36
            circle.append((cx + size * 0.5 * math.cos(angle), cy + size * 0.5 * math.sin(angle)))
        groups: list[PointGroup] = [circle]
        for i in range(rays):
            angle = 2 * math.pi * i / rays
            ray: PointGroup = [
                (cx + size * 0.55 * math.cos(angle), cy + size * 0.55 * math.sin(angle)),
                (cx + size * math.cos(angle), cy + size * math.sin(angle)),
            ]
            groups.append(ray)
        return groups


class TreeGenerator(ShapeGenerator):
    name = "tree"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        trunk: PointGroup = [
            (cx - size * 0.1, cy), (cx + size * 0.1, cy),
            (cx + size * 0.1, cy + size), (cx - size * 0.1, cy + size),
            (cx - size * 0.1, cy),
        ]
        crown: PointGroup = []
        for i in range(36 + 1):
            angle = 2 * math.pi * i / 36
            crown.append((cx + size * 0.7 * math.cos(angle),
                          cy - size * 0.5 + size * 0.7 * math.sin(angle)))
        return [trunk, crown]


class LineGenerator(ShapeGenerator):
    name = "line"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        dx = params.get("dx", size)
        dy = params.get("dy", 0)
        return [[(cx - dx, cy - dy), (cx + dx, cy + dy)]]


class DotGenerator(ShapeGenerator):
    name = "dot"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        radius = params.get("radius", 5)
        steps = 12
        pts: PointGroup = []
        for i in range(steps + 1):
            angle = 2 * math.pi * i / steps
            pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
        return [pts]


class GridGenerator(ShapeGenerator):
    name = "grid"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        cols = params.get("cols", 5)
        rows = params.get("rows", 5)
        x0, y0 = cx - size, cy - size
        x1, y1 = cx + size, cy + size
        dx = (x1 - x0) / cols
        dy = (y1 - y0) / rows
        groups: list[PointGroup] = []
        for c in range(cols + 1):
            x = x0 + c * dx
            groups.append([(x, y0), (x, y1)])
        for r in range(rows + 1):
            y = y0 + r * dy
            groups.append([(x0, y), (x1, y)])
        return groups


class WaveGenerator(ShapeGenerator):
    name = "wave"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        waves = params.get("waves", 3)
        amplitude = params.get("amplitude", size * 0.3)
        points = params.get("points", 60)
        width = size * 2
        x0 = cx - width / 2
        pts: PointGroup = []
        for i in range(points):
            t = i / (points - 1)
            x = x0 + t * width
            y = cy + amplitude * math.sin(t * waves * 2 * math.pi)
            pts.append((x, y))
        return [pts]


# ── Shape Registry (OCP) ─────────────────────────────────────────────────

class ShapeRegistry:
    """
    Registry of all available shape generators.

    New shapes can be added at runtime via register().
    This follows the Open/Closed Principle — the registry is open for
    extension but closed for modification.
    """

    _generators: dict[str, ShapeGenerator] = {}

    @classmethod
    def register(cls, generator: ShapeGenerator) -> None:
        """Register a shape generator."""
        cls._generators[generator.name] = generator

    @classmethod
    def get(cls, name: str) -> ShapeGenerator:
        """Get a shape generator by name. Falls back to circle."""
        if not cls._generators:
            cls._init_defaults()
        gen = cls._generators.get(name)
        if gen is None:
            gen = cls._generators.get("circle", CircleGenerator())
        return gen

    @classmethod
    def available(cls) -> list[str]:
        """List all registered shape names."""
        if not cls._generators:
            cls._init_defaults()
        return sorted(cls._generators.keys())

    @classmethod
    def _init_defaults(cls) -> None:
        """Register all built-in shape generators."""
        for gen_class in [
            CircleGenerator, EllipseGenerator, RectangleGenerator, SquareGenerator,
            TriangleGenerator, StarGenerator, HeartGenerator, SpiralGenerator,
            HouseGenerator, FlowerGenerator, SunGenerator, TreeGenerator,
            LineGenerator, DotGenerator, GridGenerator, WaveGenerator,
        ]:
            cls.register(gen_class())
