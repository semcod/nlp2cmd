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


from nlp2cmd.skills.drawing.svg_path_parser import PointGroup, parse_svg_path


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
