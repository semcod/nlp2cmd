# EllipseGenerator - extracted from shapes.py
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
