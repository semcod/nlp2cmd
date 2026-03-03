"""
LLM integration package for NLP2CMD.

Provides OpenRouter API client with vision support for:
- CAPTCHA solving
- Screenshot analysis
- Complex command planning
- API key OCR extraction
- Output validation (LLMValidator, local Ollama)
- Command repair (LLMRepair, OpenRouter cloud)
"""

from nlp2cmd.llm.openrouter import OpenRouterClient
from nlp2cmd.llm.vision import VisionAnalyzer
from nlp2cmd.llm.validator import LLMValidator, ValidationVerdict
from nlp2cmd.llm.repair import LLMRepair, RepairResult
from nlp2cmd.llm.router import LLMRouter, RouterResponse, get_router, reset_router, classify_task
from nlp2cmd.llm.adaptive_learner import AdaptiveLearner, classify_error, ErrorPattern

__all__ = [
    "OpenRouterClient",
    "VisionAnalyzer",
    "LLMValidator",
    "ValidationVerdict",
    "LLMRepair",
    "RepairResult",
    "LLMRouter",
    "RouterResponse",
    "get_router",
    "reset_router",
    "classify_task",
    "AdaptiveLearner",
    "classify_error",
    "ErrorPattern",
]
