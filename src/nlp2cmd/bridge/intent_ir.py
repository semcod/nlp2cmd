"""Convert nlp2cmd detection results to pact-ir IntentIR."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nlp2cmd.generation.keywords import DetectionResult


def has_integration_packages() -> bool:
    try:
        import pact_ir  # noqa: F401
        import nlp2cmd_intent  # noqa: F401

        return True
    except ImportError:
        return False


def detection_to_intent_ir(result: DetectionResult | Any, *, query: str = "") -> Any:
    """Map DetectionResult → IntentIR via nlp2cmd-intent."""
    from nlp2cmd_intent import detection_to_intent_ir as _convert

    return _convert(result, query=query)
