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
        "Pakiet nlp2cmd-intent nie jest zainstalowany (wymagany od v1.1.17).\n\n"
        "Monorepo dev (zalecane):\n"
        "  cd ../nlp2dsl && ./scripts/setup-dev.sh\n\n"
        "Ręcznie:\n"
        "  cd ../nlp2dsl && ./packages/install-dev.sh\n"
        "  pip install -e ../nlp2cmd[integration]\n"
    ) from exc

__all__ = [
    "KeywordPatterns",
    "KeywordIntentDetector",
    "DetectionResult",
    "find_data_files",
]
