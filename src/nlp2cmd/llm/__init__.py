"""
LLM integration package for NLP2CMD.

Provides OpenRouter API client with vision support for:
- CAPTCHA solving
- Screenshot analysis
- Complex command planning
- API key OCR extraction
"""

from nlp2cmd.llm.openrouter import OpenRouterClient
from nlp2cmd.llm.vision import VisionAnalyzer

__all__ = [
    "OpenRouterClient",
    "VisionAnalyzer",
]
