"""
Entity resolver — YAML-driven multilingual entity extraction with fuzzy matching.

Loads entity definitions from data/entities/*.yaml and resolves entity values
from user queries using exact + fuzzy matching (rapidfuzz).

Supported entity types:
- colors: "czerwony" → "#FF0000", "red" → "#FF0000"
- shapes: "koło" → "circle", "kreis" → "circle"
- apps: "chromka" → chrome AppInfo, "przeglądarka" → firefox AppInfo

Usage:
    resolver = EntityResolver()
    color = resolver.resolve_color("narysuj czerwone koło")
    # → "#FF0000"
    app = resolver.resolve_app("odpal mi chromka")
    # → AppInfo(name="chrome", launch="google-chrome", ...)
"""

from __future__ import annotations

import logging
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from nlp2cmd.utils.yaml_compat import yaml

log = logging.getLogger(__name__)

_PKG_DIR = Path(__file__).resolve().parent.parent
_ENTITIES_DIR_CANDIDATES = [
    _PKG_DIR / "data" / "entities",
    _PKG_DIR.parent.parent / "data" / "entities",  # project root
]
_ENTITIES_DIR = next((d for d in _ENTITIES_DIR_CANDIDATES if d.is_dir()), _ENTITIES_DIR_CANDIDATES[0])


@dataclass
class AppInfo:
    """Application info loaded from apps.yaml."""
    name: str
    launch: str
    process: str = ""
    wmclass: str = ""
    aliases: dict[str, list[str]] = field(default_factory=dict)

    def all_aliases(self) -> list[str]:
        result: list[str] = []
        for lang_aliases in self.aliases.values():
            result.extend(lang_aliases)
        return result


class EntityResolver:
    """
    Multilingual entity resolver backed by YAML data files.

    Resolves colors, shapes, and app names from any supported language
    using exact match + rapidfuzz fallback.
    """

    FUZZY_THRESHOLD = 75

    def __init__(self, entities_dir: Optional[Path] = None):
        self._entities_dir = entities_dir or _ENTITIES_DIR
        self._colors: dict[str, str] = {}       # normalized_name → hex
        self._shapes: dict[str, str] = {}       # normalized_name → canonical_shape
        self._apps: dict[str, AppInfo] = {}     # canonical_name → AppInfo
        self._app_alias_index: dict[str, str] = {}  # normalized_alias → canonical_name
        self.load()

    def load(self) -> None:
        """Load all entity YAML files."""
        self._load_colors()
        self._load_shapes()
        self._load_apps()

    def _load_colors(self) -> None:
        path = self._entities_dir / "colors.yaml"
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            log.warning("Failed to load colors.yaml: %s", e)
            return

        self._colors.clear()
        for hex_code, langs in data.get("colors", {}).items():
            for lang_names in langs.values():
                for name in lang_names:
                    self._colors[self._normalize(name)] = hex_code

    def _load_shapes(self) -> None:
        path = self._entities_dir / "shapes.yaml"
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            log.warning("Failed to load shapes.yaml: %s", e)
            return

        self._shapes.clear()
        for canonical, langs in data.get("shapes", {}).items():
            for lang_names in langs.values():
                for name in lang_names:
                    self._shapes[self._normalize(name)] = canonical

    def _load_apps(self) -> None:
        path = self._entities_dir / "apps.yaml"
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            log.warning("Failed to load apps.yaml: %s", e)
            return

        self._apps.clear()
        self._app_alias_index.clear()
        for canonical, cfg in data.get("apps", {}).items():
            app = AppInfo(
                name=canonical,
                launch=cfg.get("launch", canonical),
                process=cfg.get("process", ""),
                wmclass=cfg.get("wmclass", ""),
                aliases=cfg.get("aliases", {}),
            )
            self._apps[canonical] = app
            # Index all aliases
            for lang_aliases in app.aliases.values():
                for alias in lang_aliases:
                    self._app_alias_index[self._normalize(alias)] = canonical

    # ── Color resolution ─────────────────────────────────────────

    def resolve_color(self, text: str) -> Optional[str]:
        """
        Find a color name in text and return its hex code.

        Args:
            text: User query (any language)

        Returns:
            Hex color code (e.g. "#FF0000") or None
        """
        normalized = self._normalize(text)
        # Exact match
        for color_name, hex_code in self._colors.items():
            if color_name in normalized:
                return hex_code

        # Fuzzy match
        return self._fuzzy_color(normalized)

    def resolve_all_colors(self, text: str) -> list[str]:
        """Find all color names in text, return list of hex codes."""
        normalized = self._normalize(text)
        found: list[str] = []
        seen: set[str] = set()
        for color_name, hex_code in self._colors.items():
            if color_name in normalized and hex_code not in seen:
                found.append(hex_code)
                seen.add(hex_code)
        return found

    def _fuzzy_color(self, text: str) -> Optional[str]:
        try:
            from rapidfuzz import fuzz, process
        except ImportError:
            return None

        words = text.split()
        color_names = list(self._colors.keys())
        for word in words:
            match = process.extractOne(word, color_names, scorer=fuzz.WRatio)
            if match and match[1] >= self.FUZZY_THRESHOLD:
                return self._colors[match[0]]
        return None

    # ── Shape resolution ─────────────────────────────────────────

    def resolve_shape(self, text: str) -> Optional[str]:
        """
        Find a shape name in text and return its canonical name.

        Args:
            text: User query (any language)

        Returns:
            Canonical shape name (e.g. "circle") or None
        """
        normalized = self._normalize(text)
        for shape_name, canonical in self._shapes.items():
            if shape_name in normalized:
                return canonical
        return self._fuzzy_shape(normalized)

    def resolve_all_shapes(self, text: str) -> list[str]:
        """Find all shape names in text."""
        normalized = self._normalize(text)
        found: list[str] = []
        seen: set[str] = set()
        for shape_name, canonical in self._shapes.items():
            if shape_name in normalized and canonical not in seen:
                found.append(canonical)
                seen.add(canonical)
        return found

    def _fuzzy_shape(self, text: str) -> Optional[str]:
        try:
            from rapidfuzz import fuzz, process
        except ImportError:
            return None

        words = text.split()
        shape_names = list(self._shapes.keys())
        for word in words:
            match = process.extractOne(word, shape_names, scorer=fuzz.WRatio)
            if match and match[1] >= self.FUZZY_THRESHOLD:
                return self._shapes[match[0]]
        return None

    # ── App resolution ───────────────────────────────────────────

    def resolve_app(self, text: str) -> Optional[AppInfo]:
        """
        Find an app name in text and return its AppInfo.

        Supports colloquial names, typos, and multiple languages.

        Args:
            text: User query (any language)

        Returns:
            AppInfo or None
        """
        normalized = self._normalize(text)

        # Exact alias match (longest match first to avoid false positives)
        sorted_aliases = sorted(self._app_alias_index.keys(), key=len, reverse=True)
        for alias in sorted_aliases:
            if alias in normalized:
                canonical = self._app_alias_index[alias]
                return self._apps.get(canonical)

        # Fuzzy match
        return self._fuzzy_app(normalized)

    def _fuzzy_app(self, text: str) -> Optional[AppInfo]:
        try:
            from rapidfuzz import fuzz, process
        except ImportError:
            return None

        words = text.split()
        alias_names = list(self._app_alias_index.keys())
        for word in words:
            if len(word) < 3:
                continue
            match = process.extractOne(word, alias_names, scorer=fuzz.WRatio)
            if match and match[1] >= self.FUZZY_THRESHOLD:
                canonical = self._app_alias_index[match[0]]
                return self._apps.get(canonical)
        return None

    def get_app(self, name: str) -> Optional[AppInfo]:
        """Get app info by canonical name."""
        return self._apps.get(name)

    def list_apps(self) -> list[str]:
        """Return sorted list of canonical app names."""
        return sorted(self._apps.keys())

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text: lowercase + strip diacritics."""
        text = text.lower().strip()
        nfkd = unicodedata.normalize("NFKD", text)
        return "".join(c for c in nfkd if not unicodedata.combining(c))
