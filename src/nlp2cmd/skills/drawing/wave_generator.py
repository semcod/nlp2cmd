# WaveGenerator - extracted from shapes.py
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
