# ArrowGenerator - extracted from shapes.py
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

class ArrowGenerator(ShapeGenerator):
    name = "arrow"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = size
        direction = params.get("direction", "right")
        if direction == "right":
            pts: PointGroup = [
                (cx - s, cy - s * 0.15), (cx + s * 0.3, cy - s * 0.15),
                (cx + s * 0.3, cy - s * 0.4), (cx + s, cy),
                (cx + s * 0.3, cy + s * 0.4), (cx + s * 0.3, cy + s * 0.15),
                (cx - s, cy + s * 0.15), (cx - s, cy - s * 0.15),
            ]
        elif direction == "up":
            pts = [
                (cx - s * 0.15, cy + s), (cx - s * 0.15, cy - s * 0.3),
                (cx - s * 0.4, cy - s * 0.3), (cx, cy - s),
                (cx + s * 0.4, cy - s * 0.3), (cx + s * 0.15, cy - s * 0.3),
                (cx + s * 0.15, cy + s), (cx - s * 0.15, cy + s),
            ]
        else:
            pts = [
                (cx - s, cy), (cx + s, cy),
                (cx + s * 0.5, cy - s * 0.3),
                (cx + s, cy),
                (cx + s * 0.5, cy + s * 0.3),
            ]
        return [pts]
