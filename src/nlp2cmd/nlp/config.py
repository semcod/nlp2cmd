"""
Configuration loader — Etap 2 of the NLP refactoring plan.

Loads services and intents from YAML files instead of hardcoded dicts.
Provides a single ``ServiceRegistry`` and ``IntentRegistry`` that other
modules can query, eliminating duplicated KNOWN_SERVICES definitions.

Design goals:
  • Single source of truth for service configs and intent examples
  • Hot-reloadable (call ``load()`` again to pick up file changes)
  • Backward compatible — returns the same data shapes that existing
    code expects (dict-of-dicts for services, nested dict for intents)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

log = logging.getLogger(__name__)

# Default config directory (inside the package's data/ folder)
_DEFAULT_CONFIG_DIR = Path(__file__).resolve().parent.parent / "data" / "config"


# ---------------------------------------------------------------------------
# Service registry
# ---------------------------------------------------------------------------

@dataclass
class ServiceConfig:
    """Configuration for a known API service (mirrors env_extractor.ServiceConfig)."""

    name: str
    display_name: str = ""
    base_url: str = ""
    keys_url: str = ""
    login_url: str = ""
    key_pattern: str = ""
    env_var: str = ""
    key_selectors: list[str] = field(default_factory=list)
    instructions: str = ""

    def to_planner_dict(self) -> dict[str, Any]:
        """Return dict compatible with action_planner.KNOWN_SERVICES values."""
        return {
            "base_url": self.base_url,
            "keys_url": self.keys_url,
            "key_pattern": self.key_pattern,
            "env_var": self.env_var,
            "key_selectors": list(self.key_selectors),
        }


class ServiceRegistry:
    """Loads and serves service configurations from ``services.yaml``."""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self._config_dir = config_dir or _DEFAULT_CONFIG_DIR
        self._services: dict[str, ServiceConfig] = {}
        self.load()

    def load(self) -> None:
        """(Re-)load services from YAML."""
        path = self._config_dir / "services.yaml"
        if not path.exists():
            log.warning("services.yaml not found at %s", path)
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            log.error("Failed to load services.yaml: %s", e)
            return

        services_data = data.get("services", {})
        self._services = {}
        for name, cfg in services_data.items():
            self._services[name] = ServiceConfig(
                name=name,
                display_name=cfg.get("display_name", name),
                base_url=cfg.get("base_url", ""),
                keys_url=cfg.get("keys_url", ""),
                login_url=cfg.get("login_url", ""),
                key_pattern=cfg.get("key_pattern", ""),
                env_var=cfg.get("env_var", ""),
                key_selectors=cfg.get("key_selectors", []),
                instructions=cfg.get("instructions", ""),
            )
        log.debug("Loaded %d services from %s", len(self._services), path)

    def get(self, name: str) -> Optional[ServiceConfig]:
        """Get service config by name (case-insensitive)."""
        return self._services.get(name.lower())

    def list_names(self) -> list[str]:
        """Return sorted list of known service names."""
        return sorted(self._services.keys())

    def as_planner_dict(self) -> dict[str, dict[str, Any]]:
        """Return dict compatible with action_planner.KNOWN_SERVICES."""
        return {name: svc.to_planner_dict() for name, svc in self._services.items()}

    def __contains__(self, name: str) -> bool:
        return name.lower() in self._services

    def __len__(self) -> int:
        return len(self._services)

    def items(self) -> list[tuple[str, ServiceConfig]]:
        return list(self._services.items())


# ---------------------------------------------------------------------------
# Intent registry
# ---------------------------------------------------------------------------

@dataclass
class IntentConfig:
    """Configuration for a single intent under a domain."""

    domain: str
    intent: str
    confidence_base: float = 0.85
    examples: dict[str, list[str]] = field(default_factory=dict)

    def get_examples(self, lang: str = "pl") -> list[str]:
        """Return examples for the given language, falling back to English."""
        return self.examples.get(lang, self.examples.get("en", []))

    def all_examples(self) -> list[str]:
        """Return all examples across all languages (for training data export)."""
        result = []
        for examples in self.examples.values():
            result.extend(examples)
        return result


class IntentRegistry:
    """Loads and serves intent configurations from ``intents.yaml``."""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self._config_dir = config_dir or _DEFAULT_CONFIG_DIR
        self._intents: dict[str, dict[str, IntentConfig]] = {}
        self.load()

    def load(self) -> None:
        """(Re-)load intents from YAML."""
        path = self._config_dir / "intents.yaml"
        if not path.exists():
            log.warning("intents.yaml not found at %s", path)
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            log.error("Failed to load intents.yaml: %s", e)
            return

        self._intents = {}
        for domain, intents in data.items():
            if not isinstance(intents, dict):
                continue
            self._intents[domain] = {}
            for intent_name, cfg in intents.items():
                if not isinstance(cfg, dict):
                    continue
                self._intents[domain][intent_name] = IntentConfig(
                    domain=domain,
                    intent=intent_name,
                    confidence_base=cfg.get("confidence_base", 0.85),
                    examples=cfg.get("examples", {}),
                )
        total = sum(len(v) for v in self._intents.values())
        log.debug("Loaded %d intents across %d domains from %s",
                  total, len(self._intents), path)

    def get(self, domain: str, intent: str) -> Optional[IntentConfig]:
        """Get a specific intent config."""
        return self._intents.get(domain, {}).get(intent)

    def get_domain(self, domain: str) -> dict[str, IntentConfig]:
        """Get all intents for a domain."""
        return dict(self._intents.get(domain, {}))

    def list_domains(self) -> list[str]:
        """Return list of known domains."""
        return sorted(self._intents.keys())

    def all_examples_for_training(self) -> list[dict[str, str]]:
        """Export all examples as training data: [{text, label}, ...]."""
        result = []
        for domain, intents in self._intents.items():
            for intent_name, cfg in intents.items():
                label = f"{domain}/{intent_name}"
                for example in cfg.all_examples():
                    result.append({"text": example, "label": label})
        return result


# ---------------------------------------------------------------------------
# Singleton accessors (lazy-loaded)
# ---------------------------------------------------------------------------

_service_registry: Optional[ServiceRegistry] = None
_intent_registry: Optional[IntentRegistry] = None


def get_service_registry(config_dir: Optional[Path] = None) -> ServiceRegistry:
    """Return the global ServiceRegistry singleton (lazy-loaded)."""
    global _service_registry
    if _service_registry is None:
        _service_registry = ServiceRegistry(config_dir)
    return _service_registry


def get_intent_registry(config_dir: Optional[Path] = None) -> IntentRegistry:
    """Return the global IntentRegistry singleton (lazy-loaded)."""
    global _intent_registry
    if _intent_registry is None:
        _intent_registry = IntentRegistry(config_dir)
    return _intent_registry
