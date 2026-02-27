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

__all__ = [
    "NormalizedQuery",
    "QueryNormalizer",
    "ServiceConfig",
    "ServiceRegistry",
    "IntentConfig",
    "IntentRegistry",
    "get_service_registry",
    "get_intent_registry",
]
