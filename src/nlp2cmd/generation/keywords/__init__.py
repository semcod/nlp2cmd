"""
Keywords package for NLP2CMD intent detection.

Re-exports canonical implementation from nlp2cmd-intent.
"""

try:
    from nlp2cmd_intent.keywords import (
        DetectionResult,
        KeywordIntentDetector,
        KeywordPatterns,
        find_data_files,
    )
except ImportError as exc:  # pragma: no cover - install hint
    raise ImportError(
        "Pakiet nlp2cmd-intent nie jest zainstalowany lub jest za stary (wymagany >=0.1.1 od nlp2cmd v1.1.17).\n\n"
        "PyPI:\n"
        "  pip install -U 'nlp2cmd-intent>=0.1.1'\n\n"
        "Monorepo dev (zalecane):\n"
        "  cd ../nlp2cmd && make update\n"
        "  # lub: cd ../nlp2dsl && ./scripts/setup-dev.sh\n"
    ) from exc

__all__ = [
    "KeywordPatterns",
    "KeywordIntentDetector",
    "DetectionResult",
    "find_data_files",
]
