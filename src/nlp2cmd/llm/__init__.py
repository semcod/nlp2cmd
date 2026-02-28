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

__all__ = [
    "OpenRouterClient",
    "VisionAnalyzer",
    "LLMValidator",
    "ValidationVerdict",
    "LLMRepair",
    "RepairResult",
]
