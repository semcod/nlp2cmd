# FetchedShape - extracted from object_fetcher.py
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
@dataclass
class FetchedShape:
    """Shape data retrieved from an external database."""
    name: str
    points: list[PointGroup]
    source: str  # "simpleicons", "iconify", "svgrepo", "cache"
    svg_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    fetch_time_ms: float = 0.0
