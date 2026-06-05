"""Backward-compatible re-export of canonical keyword detector."""

from nlp2cmd_intent.keywords import keyword_detector as _impl

DetectionResult = _impl.DetectionResult
KeywordIntentDetector = _impl.KeywordIntentDetector
_get_fuzzy_schema_matcher = _impl._get_fuzzy_schema_matcher
_get_ml_classifier = _impl._get_ml_classifier
_get_query_normalizer = _impl._get_query_normalizer
_get_semantic_matcher = _impl._get_semantic_matcher

__all__ = ["DetectionResult", "KeywordIntentDetector"]
