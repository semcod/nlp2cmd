# SunGenerator - extracted from shapes.py
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
from nlp2cmd.skills.drawing.shape_generator import ShapeGenerator

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
