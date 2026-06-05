# SpiralGenerator - extracted from shapes.py
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
