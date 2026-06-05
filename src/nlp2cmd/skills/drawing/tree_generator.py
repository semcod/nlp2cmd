# TreeGenerator - extracted from shapes.py
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
