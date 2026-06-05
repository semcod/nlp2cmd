# CrescentGenerator - extracted from shapes.py
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

class CrescentGenerator(ShapeGenerator):
    name = "crescent"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        steps = 36
        # Outer circle
        pts: PointGroup = []
        for i in range(steps + 1):
            a = 2 * math.pi * i / steps
            pts.append((cx + size * math.cos(a), cy + size * math.sin(a)))
        # Inner circle (offset to create crescent)
        inner: PointGroup = []
        offset = size * 0.4
        for i in range(steps + 1):
            a = 2 * math.pi * i / steps
            inner.append((cx + offset + size * 0.8 * math.cos(a),
                          cy + size * 0.8 * math.sin(a)))
        return [pts, inner]
