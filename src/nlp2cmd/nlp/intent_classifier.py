"""Intent classification helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from nlp2cmd.generation.keywords.keyword_detector import KeywordIntentDetector


@dataclass
class IntentResult:
    """Classification result for intent detection."""

    domain: str
    intent: str
    confidence: float
    matched_keyword: Optional[str] = None


class IntentClassifier:
    """Lightweight intent classifier wrapper."""

    def __init__(self, detector: Optional[KeywordIntentDetector] = None) -> None:
        self.detector = detector or KeywordIntentDetector()

    def classify(self, text: str) -> IntentResult:
        """Classify intent from text."""
        detection = self.detector.detect(text)
        return IntentResult(
            domain=detection.domain,
            intent=detection.intent,
            confidence=detection.confidence,
            matched_keyword=detection.matched_keyword,
        )
