# RocketGenerator - extracted from shapes.py
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

class RocketGenerator(ShapeGenerator):
    name = "rocket"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = size * 0.8
        # Body
        body: PointGroup = [
            (cx - s * 0.15, cy + s * 0.5), (cx - s * 0.15, cy - s * 0.3),
            (cx, cy - s * 0.8), (cx + s * 0.15, cy - s * 0.3),
            (cx + s * 0.15, cy + s * 0.5), (cx - s * 0.15, cy + s * 0.5),
        ]
        # Left fin
        lf: PointGroup = [
            (cx - s * 0.15, cy + s * 0.3), (cx - s * 0.4, cy + s * 0.6),
            (cx - s * 0.15, cy + s * 0.5),
        ]
        # Right fin
        rf: PointGroup = [
            (cx + s * 0.15, cy + s * 0.3), (cx + s * 0.4, cy + s * 0.6),
            (cx + s * 0.15, cy + s * 0.5),
        ]
        # Window
        window: PointGroup = []
        for i in range(13):
            a = 2 * math.pi * i / 12
            window.append((cx + s * 0.08 * math.cos(a),
                           cy - s * 0.15 + s * 0.08 * math.sin(a)))
        # Flame
        flame: PointGroup = [
            (cx - s * 0.1, cy + s * 0.5), (cx - s * 0.05, cy + s * 0.7),
            (cx, cy + s * 0.6), (cx + s * 0.05, cy + s * 0.75),
            (cx + s * 0.1, cy + s * 0.5),
        ]
        return [body, lf, rf, window, flame]
