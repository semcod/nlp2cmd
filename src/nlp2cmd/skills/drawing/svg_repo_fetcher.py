# SVGRepoFetcher - extracted from object_fetcher.py
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

class SVGRepoFetcher(_BaseFetcher):
    """
    Search and fetch from SVG Repo (svgrepo.com).

    1M+ free SVG vectors. Uses their search API.
    """

    SEARCH_URL = "https://www.svgrepo.com/vectors"

    async def fetch(self, name: str) -> Optional[FetchedShape]:
        # SVG Repo doesn't have a clean JSON API, so we try direct URL patterns
        slug = name.lower().replace(" ", "-")
        try:
            svg = self._get(
                f"https://www.svgrepo.com/download/{slug}.svg",
                accept="image/svg+xml"
            ).decode()
            paths = re.findall(r'd="([^"]+)"', svg)
            all_points: list[PointGroup] = []
            for p in paths[:3]:  # Limit to first 3 paths
                parsed = parse_svg_path(p)
                all_points.extend(parsed)
            if all_points:
                return FetchedShape(
                    name=name, points=all_points, source="svgrepo",
                    svg_path=paths[0] if paths else "",
                )
        except Exception:
            pass
        return None
