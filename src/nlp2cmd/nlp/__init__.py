"""NLP modules for nlp2cmd — language-aware normalization, detection, and processing."""

from __future__ import annotations

from nlp2cmd.nlp.config import (
    IntentConfig,
    IntentRegistry,
    ServiceConfig,
    ServiceRegistry,
    get_intent_registry,
    get_service_registry,
)
from nlp2cmd.nlp.normalizer import NormalizedQuery, QueryNormalizer
from nlp2cmd.nlp.intent_matcher import IntentMatcher, IntentDef, IntentMatch
from nlp2cmd.nlp.entity_resolver import EntityResolver, AppInfo

__all__ = [
    "NormalizedQuery",
    "QueryNormalizer",
    "ServiceConfig",
    "ServiceRegistry",
    "IntentConfig",
    "IntentRegistry",
    "get_service_registry",
    "get_intent_registry",
    # Phase R1 — YAML-driven multilingual NLP
    "IntentMatcher",
    "IntentDef",
    "IntentMatch",
    "EntityResolver",
    "AppInfo",
]
