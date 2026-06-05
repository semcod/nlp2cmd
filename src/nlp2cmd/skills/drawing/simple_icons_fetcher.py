# SimpleIconsFetcher - extracted from object_fetcher.py
"""
Object Fetcher — autonomous shape data retrieval from online databases.

Fetches SVG paths, icon definitions, and geometric data from real online
sources. Converts SVG path data to vertex lists usable by ShapeRegistry.

Supported databases:
- Simple Icons (simpleicons.org) — 3000+ brand/tech SVGs
- SVG Repo — millions of free SVG icons
- Iconify API — unified icon API (Material, FontAwesome, etc.)
- Local cache with TTL for offline operation

Single Responsibility: fetch external shape data → convert to PointGroup format.
"""

from __future__ import annotations

import json
import math
import re
import ssl
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PointGroup = list[tuple[float, float]]


# ── SVG Path Parser ──────────────────────────────────────────────────────

def parse_svg_path(d: str, scale: float = 1.0, center: bool = True) -> list[PointGroup]:
    """
    Parse SVG path 'd' attribute into point groups.

    Supports: M, L, H, V, C, Q, Z (absolute) and m, l, h, v, c, q, z (relative).
    Arcs (A/a) are approximated with line segments.

    Args:
        d: SVG path data string
        scale: Scale factor to normalize coordinates
        center: If True, center the shape around (0, 0)

    Returns:
        List of point groups
    """
    if not d or not d.strip():
        return []

    groups: list[PointGroup] = []
    current: PointGroup = []
    cx, cy = 0.0, 0.0  # current point
    sx, sy = 0.0, 0.0  # start of subpath

    # Tokenize: split into commands + numbers
    tokens = re.findall(r'[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', d)

    i = 0
    cmd = 'M'

    def next_num() -> float:
        nonlocal i
        while i < len(tokens) and tokens[i] in 'MmLlHhVvCcSsQqTtAaZz':
            i += 1
        if i < len(tokens):
            val = float(tokens[i])
            i += 1
            return val
        return 0.0

    while i < len(tokens):
        t = tokens[i]
        if t in 'MmLlHhVvCcSsQqTtAaZz':
            cmd = t
            i += 1
        # else: implicit repeat of previous command

        if cmd == 'M':
            if current:
                groups.append(current)
                current = []
            cx, cy = next_num(), next_num()
            sx, sy = cx, cy
            current.append((cx, cy))
            cmd = 'L'  # subsequent coords are lineto

        elif cmd == 'm':
            if current:
                groups.append(current)
                current = []
            cx += next_num()
            cy += next_num()
            sx, sy = cx, cy
            current.append((cx, cy))
            cmd = 'l'

        elif cmd == 'L':
            cx, cy = next_num(), next_num()
            current.append((cx, cy))

        elif cmd == 'l':
            cx += next_num()
            cy += next_num()
            current.append((cx, cy))

        elif cmd == 'H':
            cx = next_num()
            current.append((cx, cy))

        elif cmd == 'h':
            cx += next_num()
            current.append((cx, cy))

        elif cmd == 'V':
            cy = next_num()
            current.append((cx, cy))

        elif cmd == 'v':
            cy += next_num()
            current.append((cx, cy))

        elif cmd == 'C':
            # Cubic bezier: approximate with line segments
            x1, y1 = next_num(), next_num()
            x2, y2 = next_num(), next_num()
            x3, y3 = next_num(), next_num()
            for t in [0.25, 0.5, 0.75, 1.0]:
                bx = (1-t)**3*cx + 3*(1-t)**2*t*x1 + 3*(1-t)*t**2*x2 + t**3*x3
                by = (1-t)**3*cy + 3*(1-t)**2*t*y1 + 3*(1-t)*t**2*y2 + t**3*y3
                current.append((bx, by))
            cx, cy = x3, y3

        elif cmd == 'c':
            x1, y1 = cx + next_num(), cy + next_num()
            x2, y2 = cx + next_num(), cy + next_num()
            dx, dy = next_num(), next_num()
            x3, y3 = cx + dx, cy + dy
            for t in [0.25, 0.5, 0.75, 1.0]:
                bx = (1-t)**3*cx + 3*(1-t)**2*t*x1 + 3*(1-t)*t**2*x2 + t**3*x3
                by = (1-t)**3*cy + 3*(1-t)**2*t*y1 + 3*(1-t)*t**2*y2 + t**3*y3
                current.append((bx, by))
            cx, cy = x3, y3

        elif cmd == 'Q':
            x1, y1 = next_num(), next_num()
            x2, y2 = next_num(), next_num()
            for t in [0.33, 0.66, 1.0]:
                bx = (1-t)**2*cx + 2*(1-t)*t*x1 + t**2*x2
                by = (1-t)**2*cy + 2*(1-t)*t*y1 + t**2*y2
                current.append((bx, by))
            cx, cy = x2, y2

        elif cmd == 'q':
            x1, y1 = cx + next_num(), cy + next_num()
            dx, dy = next_num(), next_num()
            x2, y2 = cx + dx, cy + dy
            for t in [0.33, 0.66, 1.0]:
                bx = (1-t)**2*cx + 2*(1-t)*t*x1 + t**2*x2
                by = (1-t)**2*cy + 2*(1-t)*t*y1 + t**2*y2
                current.append((bx, by))
            cx, cy = x2, y2

        elif cmd in ('Z', 'z'):
            if current:
                current.append((sx, sy))
                groups.append(current)
                current = []
            cx, cy = sx, sy

        elif cmd in ('S', 's', 'T', 't', 'A', 'a'):
            # Skip unsupported commands, consume their parameters
            param_counts = {'S': 4, 's': 4, 'T': 2, 't': 2, 'A': 7, 'a': 7}
            for _ in range(param_counts.get(cmd, 0)):
                next_num()

        else:
            i += 1  # skip unknown

    if current:
        groups.append(current)

    if not groups:
        return []

    # Apply scale and centering
    all_pts = [p for g in groups for p in g]
    if not all_pts:
        return groups

    if center:
        min_x = min(p[0] for p in all_pts)
        max_x = max(p[0] for p in all_pts)
        min_y = min(p[1] for p in all_pts)
        max_y = max(p[1] for p in all_pts)
        off_x = (min_x + max_x) / 2
        off_y = (min_y + max_y) / 2
        w = max_x - min_x or 1
        h = max_y - min_y or 1
        norm = max(w, h) / 2
    else:
        off_x, off_y, norm = 0, 0, 1

    result: list[PointGroup] = []
    for g in groups:
        scaled = [((x - off_x) / norm * scale * 100,
                   (y - off_y) / norm * scale * 100) for x, y in g]
        result.append(scaled)

    return result


# ── Data Classes ─────────────────────────────────────────────────────────
from nlp2cmd.skills.drawing.__base_fetcher import _BaseFetcher
from nlp2cmd.skills.drawing.fetched_shape import FetchedShape

class SimpleIconsFetcher(_BaseFetcher):
    """
    Fetch SVG icons from Simple Icons (simpleicons.org).

    3000+ brand/tech icons with clean SVG paths.
    API: https://cdn.simpleicons.org/{slug}
    """

    BASE = "https://cdn.simpleicons.org"

    async def fetch(self, name: str) -> Optional[FetchedShape]:
        slug = name.lower().replace(" ", "").replace("-", "")
        try:
            svg = self._get(f"{self.BASE}/{slug}", accept="image/svg+xml").decode()
            paths = re.findall(r'd="([^"]+)"', svg)
            if paths:
                points = parse_svg_path(paths[0])
                if points:
                    return FetchedShape(
                        name=name, points=points, source="simpleicons",
                        svg_path=paths[0],
                        metadata={"slug": slug, "url": f"{self.BASE}/{slug}"},
                    )
        except Exception:
            pass
        return None
