# FishGenerator - extracted from shapes.py
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

class FishGenerator(ShapeGenerator):
    name = "fish"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = size * 0.8
        # Body (ellipse)
        body: PointGroup = []
        for i in range(25):
            a = 2 * math.pi * i / 24
            body.append((cx + s * 0.6 * math.cos(a), cy + s * 0.3 * math.sin(a)))
        # Tail
        tail: PointGroup = [
            (cx - s * 0.55, cy), (cx - s * 0.9, cy - s * 0.35),
            (cx - s * 0.7, cy), (cx - s * 0.9, cy + s * 0.35),
            (cx - s * 0.55, cy),
        ]
        # Eye
        eye: PointGroup = []
        for i in range(13):
            a = 2 * math.pi * i / 12
            eye.append((cx + s * 0.3 + s * 0.05 * math.cos(a),
                        cy - s * 0.05 + s * 0.05 * math.sin(a)))
        # Fin
        fin: PointGroup = [
            (cx, cy - s * 0.3), (cx - s * 0.1, cy - s * 0.6),
            (cx + s * 0.15, cy - s * 0.3),
        ]
        return [body, tail, eye, fin]
