# CarGenerator - extracted from shapes.py
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

class CarGenerator(ShapeGenerator):
    name = "car"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = size * 0.8
        # Body
        body: PointGroup = [
            (cx - s, cy + s * 0.1), (cx - s, cy - s * 0.2),
            (cx - s * 0.6, cy - s * 0.2), (cx - s * 0.4, cy - s * 0.6),
            (cx + s * 0.4, cy - s * 0.6), (cx + s * 0.6, cy - s * 0.2),
            (cx + s, cy - s * 0.2), (cx + s, cy + s * 0.1),
        ]
        # Left wheel
        lw: PointGroup = []
        for i in range(17):
            a = 2 * math.pi * i / 16
            lw.append((cx - s * 0.55 + s * 0.18 * math.cos(a),
                       cy + s * 0.1 + s * 0.18 * math.sin(a)))
        # Right wheel
        rw: PointGroup = []
        for i in range(17):
            a = 2 * math.pi * i / 16
            rw.append((cx + s * 0.55 + s * 0.18 * math.cos(a),
                       cy + s * 0.1 + s * 0.18 * math.sin(a)))
        # Windshield
        ws: PointGroup = [
            (cx - s * 0.35, cy - s * 0.2), (cx - s * 0.15, cy - s * 0.55),
            (cx + s * 0.15, cy - s * 0.55), (cx + s * 0.35, cy - s * 0.2),
        ]
        return [body, lw, rw, ws]
