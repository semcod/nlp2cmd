# CastleGenerator - extracted from shapes.py
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

class CastleGenerator(ShapeGenerator):
    name = "castle"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = size * 0.8
        # Main wall
        wall: PointGroup = [
            (cx - s * 0.6, cy + s * 0.5), (cx - s * 0.6, cy - s * 0.2),
            (cx + s * 0.6, cy - s * 0.2), (cx + s * 0.6, cy + s * 0.5),
        ]
        # Battlements
        bm: PointGroup = []
        for i in range(7):
            x = cx - s * 0.6 + i * s * 0.2
            bm.append((x, cy - s * 0.2))
            bm.append((x, cy - s * 0.35))
            bm.append((x + s * 0.1, cy - s * 0.35))
            bm.append((x + s * 0.1, cy - s * 0.2))
        # Left tower
        lt: PointGroup = [
            (cx - s * 0.7, cy + s * 0.5), (cx - s * 0.7, cy - s * 0.5),
            (cx - s * 0.5, cy - s * 0.5), (cx - s * 0.5, cy + s * 0.5),
        ]
        # Right tower
        rt: PointGroup = [
            (cx + s * 0.5, cy + s * 0.5), (cx + s * 0.5, cy - s * 0.5),
            (cx + s * 0.7, cy - s * 0.5), (cx + s * 0.7, cy + s * 0.5),
        ]
        # Left tower roof
        lr: PointGroup = [
            (cx - s * 0.75, cy - s * 0.5), (cx - s * 0.6, cy - s * 0.8),
            (cx - s * 0.45, cy - s * 0.5),
        ]
        # Right tower roof
        rr: PointGroup = [
            (cx + s * 0.45, cy - s * 0.5), (cx + s * 0.6, cy - s * 0.8),
            (cx + s * 0.75, cy - s * 0.5),
        ]
        # Gate
        gate: PointGroup = []
        for i in range(13):
            a = math.pi * i / 12
            gate.append((cx + s * 0.15 * math.cos(a), cy + s * 0.5 - s * 0.25 * math.sin(a)))
        gate.extend([(cx + s * 0.15, cy + s * 0.5), (cx - s * 0.15, cy + s * 0.5)])
        return [wall, bm, lt, rt, lr, rr, gate]
