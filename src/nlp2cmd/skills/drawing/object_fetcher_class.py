# ObjectFetcher - extracted from object_fetcher.py
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
from nlp2cmd.skills.drawing.fetched_shape import FetchedShape
from nlp2cmd.skills.drawing.iconify_fetcher import IconifyFetcher
from nlp2cmd.skills.drawing.simple_icons_fetcher import SimpleIconsFetcher
from nlp2cmd.skills.drawing.svg_repo_fetcher import SVGRepoFetcher

class ObjectFetcher:
    """
    Autonomous shape fetcher with multi-database search and local caching.

    Fetch priority:
    1. Local cache (instant)
    2. Iconify API (200k+ icons from 150+ sets)
    3. Simple Icons (3000+ brand SVGs)
    4. SVG Repo (1M+ vectors)

    Usage:
        fetcher = ObjectFetcher()
        shape = await fetcher.fetch("car")
        if shape:
            # shape.points is list of PointGroups ready for ShapeRegistry
            print(f"Got {shape.name} from {shape.source}")
    """

    def __init__(self, cache_dir: Optional[Path] = None, cache_ttl: int = 86400):
        self._cache_dir = cache_dir or Path.home() / ".nlp2cmd" / "shape_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_ttl = cache_ttl
        self._memory: dict[str, FetchedShape] = {}
        self._fetchers = [
            IconifyFetcher(),
            SimpleIconsFetcher(),
            SVGRepoFetcher(),
        ]

    async def fetch(self, name: str, verbose: bool = False) -> Optional[FetchedShape]:
        """
        Fetch shape by name. Tries cache, then online databases.

        Args:
            name: Object/shape name (e.g., "car", "butterfly", "castle")
            verbose: Print progress messages

        Returns:
            FetchedShape or None
        """
        name_lower = name.lower().strip()
        t0 = time.time()

        # 1. Memory cache
        if name_lower in self._memory:
            shape = self._memory[name_lower]
            shape.fetch_time_ms = 0
            return shape

        # 2. Disk cache
        cached = self._load_cache(name_lower)
        if cached:
            if verbose:
                print(f"  📦 Cache hit: {name_lower}")
            self._memory[name_lower] = cached
            cached.fetch_time_ms = (time.time() - t0) * 1000
            return cached

        # 3. Online databases
        if verbose:
            print(f"  🌐 Fetching '{name_lower}' from online databases...")

        for fetcher in self._fetchers:
            try:
                shape = await fetcher.fetch(name_lower)
                if shape and shape.points:
                    shape.fetch_time_ms = (time.time() - t0) * 1000
                    if verbose:
                        n_pts = sum(len(g) for g in shape.points)
                        print(f"  ✓ Found in {shape.source} ({n_pts} vertices, {shape.fetch_time_ms:.0f}ms)")
                    self._memory[name_lower] = shape
                    self._save_cache(name_lower, shape)
                    return shape
            except Exception as e:
                if verbose:
                    print(f"  ⚠ {fetcher.__class__.__name__}: {e}")
                continue

        if verbose:
            print(f"  ✗ Not found in any database")
        return None

    def _load_cache(self, name: str) -> Optional[FetchedShape]:
        """Load from disk cache if not expired."""
        path = self._cache_dir / f"{name}.json"
        if not path.exists():
            return None
        age = time.time() - path.stat().st_mtime
        if age > self._cache_ttl:
            return None
        try:
            with open(path) as f:
                data = json.load(f)
            # Reconstruct point groups from nested lists
            points = [
                [(p[0], p[1]) for p in group]
                for group in data.get("points", [])
            ]
            return FetchedShape(
                name=data["name"],
                points=points,
                source="cache",
                svg_path=data.get("svg_path", ""),
                metadata=data.get("metadata", {}),
            )
        except Exception:
            return None

    def _save_cache(self, name: str, shape: FetchedShape) -> None:
        """Save to disk cache."""
        try:
            data = {
                "name": shape.name,
                "points": [list(g) for g in shape.points],
                "source": shape.source,
                "svg_path": shape.svg_path,
                "metadata": shape.metadata,
            }
            path = self._cache_dir / f"{name}.json"
            with open(path, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def clear_cache(self) -> int:
        """Clear all cached shapes. Returns number of files removed."""
        count = 0
        for f in self._cache_dir.glob("*.json"):
            f.unlink()
            count += 1
        self._memory.clear()
        return count

    @staticmethod
    def known_objects() -> list[str]:
        """List objects with known Iconify mappings."""
        return sorted(IconifyFetcher.SHAPE_MAP.keys())
