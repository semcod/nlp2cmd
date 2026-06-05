# IconifyFetcher - extracted from object_fetcher.py
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

class IconifyFetcher(_BaseFetcher):
    """
    Fetch icons from Iconify API (api.iconify.design).

    Unified API for 200,000+ icons from 150+ icon sets:
    Material Design, FontAwesome, Tabler, Lucide, etc.

    API: https://api.iconify.design/{prefix}/{name}.svg
    Search: https://api.iconify.design/search?query={query}
    """

    BASE = "https://api.iconify.design"

    # Priority icon sets for shape-like icons
    ICON_SETS = [
        "mdi",           # Material Design Icons (7000+)
        "ph",            # Phosphor Icons
        "lucide",        # Lucide Icons
        "tabler",        # Tabler Icons
        "fa-solid",      # FontAwesome Solid
        "game-icons",    # Game Icons (4000+ RPG/game shapes)
        "noto",          # Noto Emoji (colored)
        "twemoji",       # Twitter Emoji
        "emojione",      # EmojiOne
        "fluent-emoji-flat",  # Fluent Emoji
    ]

    # Shape name → icon name mappings for common objects
    SHAPE_MAP: dict[str, list[str]] = {
        "car": ["mdi:car", "fa-solid:car", "game-icons:race-car"],
        "tree": ["mdi:tree", "game-icons:pine-tree", "mdi:pine-tree"],
        "house": ["mdi:home", "fa-solid:house", "game-icons:house"],
        "bird": ["mdi:bird", "game-icons:bird-twitter", "game-icons:eagle-head"],
        "cat": ["mdi:cat", "game-icons:sitting-cat", "game-icons:cat"],
        "dog": ["mdi:dog", "game-icons:sitting-dog"],
        "fish": ["mdi:fish", "game-icons:fish"],
        "boat": ["mdi:sail-boat", "game-icons:sail-boat", "fa-solid:ship"],
        "airplane": ["mdi:airplane", "fa-solid:plane", "game-icons:commercial-airplane"],
        "mountain": ["mdi:mountain", "game-icons:mountain-peak"],
        "cloud": ["mdi:cloud", "fa-solid:cloud"],
        "sun": ["mdi:weather-sunny", "fa-solid:sun"],
        "moon": ["mdi:weather-night", "game-icons:moon"],
        "star": ["mdi:star", "fa-solid:star"],
        "heart": ["mdi:heart", "fa-solid:heart"],
        "flower": ["mdi:flower", "game-icons:flower-pot"],
        "butterfly": ["game-icons:butterfly", "mdi:butterfly"],
        "robot": ["mdi:robot", "game-icons:robot-golem"],
        "rocket": ["mdi:rocket", "game-icons:rocket"],
        "bicycle": ["mdi:bicycle", "fa-solid:bicycle"],
        "guitar": ["mdi:guitar-acoustic", "game-icons:guitar"],
        "piano": ["mdi:piano", "game-icons:piano-keys"],
        "castle": ["game-icons:castle", "mdi:castle"],
        "dragon": ["game-icons:dragon-head", "game-icons:dragon"],
        "sword": ["game-icons:sword", "game-icons:crossed-swords"],
        "shield": ["game-icons:shield", "mdi:shield"],
        "crown": ["game-icons:crown", "mdi:crown"],
        "skull": ["game-icons:skull", "mdi:skull"],
        "anchor": ["mdi:anchor", "game-icons:anchor"],
        "lightning": ["mdi:lightning-bolt", "game-icons:lightning"],
        "diamond": ["mdi:diamond", "game-icons:cut-diamond"],
        "mushroom": ["game-icons:mushroom", "game-icons:spotted-mushroom"],
        "apple": ["mdi:apple", "game-icons:apple"],
        "key": ["mdi:key", "game-icons:key"],
        "book": ["mdi:book", "game-icons:book-cover"],
        "camera": ["mdi:camera", "fa-solid:camera"],
        "clock": ["mdi:clock", "fa-solid:clock"],
        "globe": ["mdi:earth", "fa-solid:globe"],
        "flag": ["mdi:flag", "game-icons:flag"],
        "trophy": ["mdi:trophy", "game-icons:trophy"],
        "pizza": ["mdi:pizza", "game-icons:pizza-slice"],
        "coffee": ["mdi:coffee", "fa-solid:mug-hot"],
        "helmet": ["game-icons:viking-helmet", "game-icons:space-helmet"],
        "paw": ["mdi:paw", "game-icons:paw-print"],
    }

    async def fetch(self, name: str) -> Optional[FetchedShape]:
        name_lower = name.lower().strip()

        # Try direct shape map first
        candidates = self.SHAPE_MAP.get(name_lower, [])

        # If not in map, search the API
        if not candidates:
            candidates = await self._search(name_lower)

        for icon_id in candidates:
            shape = await self._fetch_icon(icon_id, name)
            if shape:
                return shape

        return None

    async def _search(self, query: str) -> list[str]:
        """Search Iconify for matching icons."""
        try:
            data = json.loads(
                self._get(f"{self.BASE}/search?query={query}&limit=5")
            )
            icons = data.get("icons", [])
            return icons[:5]
        except Exception:
            return []

    async def _fetch_icon(self, icon_id: str, display_name: str) -> Optional[FetchedShape]:
        """Fetch a specific icon by its Iconify ID (e.g., 'mdi:car')."""
        if ":" not in icon_id:
            return None
        prefix, icon_name = icon_id.split(":", 1)
        try:
            svg = self._get(
                f"{self.BASE}/{prefix}/{icon_name}.svg",
                accept="image/svg+xml"
            ).decode()
            paths = re.findall(r'd="([^"]+)"', svg)
            all_points: list[PointGroup] = []
            for p in paths:
                parsed = parse_svg_path(p)
                all_points.extend(parsed)
            if all_points:
                return FetchedShape(
                    name=display_name, points=all_points, source="iconify",
                    svg_path=paths[0] if paths else "",
                    metadata={"icon_id": icon_id, "prefix": prefix, "icon_name": icon_name},
                )
        except Exception:
            pass
        return None
