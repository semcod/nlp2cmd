"""
Browser automation configuration loader — single source of truth.

Replaces hardcoded selectors, paths, and patterns scattered across:
- form_data_loader.py (dismiss_selectors, type_selectors)
- site_explorer.py (dismiss_selectors, CONTACT_KEYWORDS, contact paths)
- pipeline_runner_utils.py (junk field patterns, contact field tokens)

All config is loaded from data/browser_config/*.yaml with per-domain overrides.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from nlp2cmd.utils.yaml_compat import yaml
from nlp2cmd.utils.data_files import find_data_file


_BROWSER_CONFIG_DIR = "browser_config"

# Module-level cache to avoid reloading on every call
_cache: dict[str, Any] = {}


def _find_config_dir() -> Optional[Path]:
    """Find the browser_config/ directory inside data/."""
    # Try to find a known file inside browser_config/ to locate the directory
    p = find_data_file(explicit_path=None, default_filename=f"{_BROWSER_CONFIG_DIR}/selectors.yaml")
    if p and p.exists():
        return p.parent
    # Fallback: look relative to this file's package
    here = Path(__file__).resolve().parent.parent / "data" / _BROWSER_CONFIG_DIR
    if here.is_dir():
        return here
    return None


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file, return empty dict on failure."""
    try:
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


class BrowserConfigLoader:
    """Single source of truth for browser automation config.

    Loads from ``data/browser_config/*.yaml`` with optional per-domain
    overrides from ``data/browser_config/domains/<domain>.yaml``.
    """

    def __init__(self, *, domain: Optional[str] = None):
        self.domain = domain
        self._selectors: dict[str, Any] = {}
        self._contact_paths: dict[str, Any] = {}
        self._junk_patterns: dict[str, Any] = {}
        self._domain_overrides: dict[str, Any] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True

        cfg_dir = _find_config_dir()
        if not cfg_dir:
            return

        self._selectors = _load_yaml(cfg_dir / "selectors.yaml")
        self._contact_paths = _load_yaml(cfg_dir / "contact_paths.yaml")
        self._junk_patterns = _load_yaml(cfg_dir / "junk_field_patterns.yaml")

        if self.domain:
            domain_file = cfg_dir / "domains" / f"{self.domain}.yaml"
            if domain_file.exists():
                self._domain_overrides = _load_yaml(domain_file)

    # ------------------------------------------------------------------
    # Selectors
    # ------------------------------------------------------------------

    def get_dismiss_selectors(self) -> list[str]:
        """Get popup/cookie dismiss selectors (domain override → global)."""
        self._ensure_loaded()
        override = self._domain_overrides.get("dismiss_popups")
        base = self._selectors.get("dismiss_popups", [])
        if isinstance(override, list) and override:
            return _dedupe([*override, *base])
        return list(base) if isinstance(base, list) else []

    def get_submit_selectors(self) -> list[str]:
        self._ensure_loaded()
        override = self._domain_overrides.get("submit_form")
        base = self._selectors.get("submit_form", [])
        if isinstance(override, list) and override:
            return _dedupe([*override, *base])
        return list(base) if isinstance(base, list) else []

    def get_type_selectors(self, selector_type: str = "search") -> list[str]:
        self._ensure_loaded()
        ts = self._selectors.get("type_selectors", {})
        if isinstance(ts, dict):
            result = ts.get(selector_type, ts.get("generic", []))
            return list(result) if isinstance(result, list) else []
        return []

    def get_contact_page_link_selectors(self) -> list[str]:
        self._ensure_loaded()
        return list(self._selectors.get("contact_page_links", []))

    # ------------------------------------------------------------------
    # Contact paths
    # ------------------------------------------------------------------

    def get_common_contact_paths(self) -> list[str]:
        self._ensure_loaded()
        return list(self._contact_paths.get("common_paths", []))

    def get_contact_url_keywords(self) -> list[str]:
        self._ensure_loaded()
        return list(self._contact_paths.get("url_keywords", []))

    def get_contact_page_keywords(self) -> list[str]:
        self._ensure_loaded()
        return list(self._contact_paths.get("page_keywords", []))

    # ------------------------------------------------------------------
    # Junk field patterns
    # ------------------------------------------------------------------

    def get_junk_field_types(self) -> list[str]:
        self._ensure_loaded()
        ji = self._junk_patterns.get("junk_indicators", {})
        return list(ji.get("field_types", []))

    def get_junk_exact_names(self) -> list[str]:
        self._ensure_loaded()
        ji = self._junk_patterns.get("junk_indicators", {})
        return list(ji.get("exact_names", []))

    def get_junk_substring_matches(self) -> list[str]:
        self._ensure_loaded()
        ji = self._junk_patterns.get("junk_indicators", {})
        return list(ji.get("substring_matches", []))

    def get_junk_prefix_matches(self) -> list[str]:
        self._ensure_loaded()
        ji = self._junk_patterns.get("junk_indicators", {})
        return list(ji.get("prefix_matches", []))

    def get_contact_field_types(self) -> list[str]:
        self._ensure_loaded()
        ci = self._junk_patterns.get("contact_indicators", {})
        return list(ci.get("field_types", []))

    def get_contact_allowed_field_types(self) -> list[str]:
        self._ensure_loaded()
        ci = self._junk_patterns.get("contact_indicators", {})
        return list(ci.get("allowed_field_types", []))

    def get_contact_tokens(self) -> list[str]:
        self._ensure_loaded()
        ci = self._junk_patterns.get("contact_indicators", {})
        return list(ci.get("tokens", []))

    # ------------------------------------------------------------------
    # Domain overrides
    # ------------------------------------------------------------------

    def get_domain_config(self, key: str, default: Any = None) -> Any:
        """Get arbitrary domain-specific config value."""
        self._ensure_loaded()
        return self._domain_overrides.get(key, default)

    # ------------------------------------------------------------------
    # Learning / mutation (Phase 4 hook)
    # ------------------------------------------------------------------

    def save_learned_selector(
        self,
        category: str,
        selector: str,
        *,
        domain: Optional[str] = None,
    ) -> bool:
        """Save a newly discovered selector to domain config (Phase 4 hook).

        Returns True if saved successfully.
        """
        cfg_dir = _find_config_dir()
        if not cfg_dir:
            return False

        target_domain = domain or self.domain or "_learned"
        domain_dir = cfg_dir / "domains"
        domain_dir.mkdir(parents=True, exist_ok=True)
        domain_file = domain_dir / f"{target_domain}.yaml"

        existing = _load_yaml(domain_file) if domain_file.exists() else {}
        current = existing.get(category, [])
        if not isinstance(current, list):
            current = []

        sel = selector.strip()
        if sel in current:
            return False

        current.insert(0, sel)
        existing[category] = current[:50]  # Cap at 50

        try:
            domain_file.write_text(
                yaml.safe_dump(existing, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            return True
        except Exception:
            return False


class DynamicSelectorGenerator:
    """Generate selectors dynamically using LLM when static ones fail.

    Usage:
        gen = DynamicSelectorGenerator(config_loader=loader)
        selectors = gen.suggest_selectors(page_html, "cookie_consent_dismiss")
        # Returns list of CSS selectors; saves successful ones to config.
    """

    def __init__(
        self,
        *,
        config_loader: Optional[BrowserConfigLoader] = None,
        llm_config: Optional[dict] = None,
    ):
        self.config_loader = config_loader or BrowserConfigLoader()
        self.llm_config = llm_config

    def suggest_selectors(
        self,
        page_html: str,
        intent: str,
        *,
        domain_hint: Optional[str] = None,
        max_selectors: int = 5,
    ) -> list[str]:
        """Ask LLM to suggest CSS selectors for the given intent.

        Args:
            page_html: Raw HTML of the page (truncated to ~8K chars)
            intent: What we're looking for (e.g. "cookie_consent_dismiss",
                    "contact_form_fields", "submit_button")
            domain_hint: Optional domain for caching learned selectors
            max_selectors: Maximum number of selectors to return

        Returns:
            List of suggested CSS selectors (may be empty on LLM failure)
        """
        import json as _json

        html_snippet = page_html[:8000] if len(page_html) > 8000 else page_html

        prompt = (
            f"Given this HTML page snippet, suggest {max_selectors} CSS selectors "
            f"for: {intent}\n\n"
            f"HTML:\n{html_snippet}\n\n"
            f'Return ONLY valid JSON: {{"selectors": ["sel1", "sel2", ...]}}'
        )

        try:
            from nlp2cmd.generation.llm_simple import LiteLLMClient

            llm = LiteLLMClient(config=self.llm_config)
            import asyncio

            response = asyncio.run(llm.generate(prompt))
            if not response:
                return []

            # Parse JSON from response
            raw = response.strip()
            # Try to extract JSON from markdown code blocks
            import re

            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.DOTALL)
            if m:
                raw = m.group(1)
            else:
                m2 = re.search(r"(\{.*\})", raw, flags=re.DOTALL)
                if m2:
                    raw = m2.group(1)

            data = _json.loads(raw)
            selectors = data.get("selectors", [])
            if not isinstance(selectors, list):
                return []

            result = [s.strip() for s in selectors if isinstance(s, str) and s.strip()]

            # Save successful selectors for future use
            if result and self.config_loader and domain_hint:
                for sel in result[:3]:
                    self.config_loader.save_learned_selector(
                        intent, sel, domain=domain_hint
                    )

            return result[:max_selectors]

        except Exception:
            return []


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _dedupe(items: list[str]) -> list[str]:
    """Deduplicate while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if isinstance(item, str) and item.strip() and item not in seen:
            seen.add(item)
            result.append(item)
    return result
