# ButterflyGenerator - extracted from shapes.py
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

class ButterflyGenerator(ShapeGenerator):
    name = "butterfly"

    def generate(self, cx: float, cy: float, size: float, **params: Any) -> list[PointGroup]:
        s = size * 0.8
        # Upper left wing
        ulw: PointGroup = []
        for i in range(25):
            t = i / 24
            a = math.pi / 2 + t * math.pi
            r = s * (0.5 + 0.3 * math.sin(t * math.pi))
            ulw.append((cx + r * math.cos(a) * 0.8, cy + r * math.sin(a) - s * 0.2))
        # Upper right wing (mirror)
        urw: PointGroup = [(cx - (x - cx), y) for x, y in ulw]
        # Lower left wing
        llw: PointGroup = []
        for i in range(20):
            t = i / 19
            a = -math.pi / 2 - t * math.pi * 0.7
            r = s * (0.3 + 0.2 * math.sin(t * math.pi))
            llw.append((cx + r * math.cos(a) * 0.8, cy + r * math.sin(a) + s * 0.1))
        # Lower right wing (mirror)
        lrw: PointGroup = [(cx - (x - cx), y) for x, y in llw]
        # Body
        body: PointGroup = [
            (cx, cy - s * 0.5), (cx - s * 0.03, cy), (cx, cy + s * 0.4),
            (cx + s * 0.03, cy), (cx, cy - s * 0.5),
        ]
        # Antennae
        ant1: PointGroup = [(cx, cy - s * 0.5), (cx - s * 0.15, cy - s * 0.8)]
        ant2: PointGroup = [(cx, cy - s * 0.5), (cx + s * 0.15, cy - s * 0.8)]
        return [ulw, urw, llw, lrw, body, ant1, ant2]
