"""
Vision analysis module for NLP2CMD.

Provides high-level screenshot analysis for:
- UI element detection
- CAPTCHA image interpretation
- Canvas/drawing verification
- API key OCR from screenshots

Built on top of OpenRouterClient.
"""

from __future__ import annotations

import base64
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

_DEBUG = os.environ.get("NLP2CMD_DEBUG", "").lower() in ("1", "true", "yes")


def _debug(msg: str) -> None:
    if _DEBUG:
        print(f"DEBUG [Vision] {msg}", file=sys.stderr, flush=True)


@dataclass
class VisionResult:
    """Result of a vision analysis."""
    success: bool = True
    answer: str = ""
    structured: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    model: str = ""
    tokens_used: int = 0


class VisionAnalyzer:
    """
    High-level vision analysis using LLM.

    Wraps OpenRouterClient with task-specific prompts for common
    automation scenarios.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Args:
            api_key: OpenRouter API key
            model: Vision model to use
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or "google/gemini-2.5-pro-preview"

    async def _get_client(self):
        from nlp2cmd.llm.openrouter import OpenRouterClient
        return OpenRouterClient(api_key=self.api_key, default_model=self.model)

    @staticmethod
    def _encode_image(image: bytes | str | Path) -> str:
        """Convert image to base64 string."""
        if isinstance(image, str):
            image = Path(image)
        if isinstance(image, Path):
            image = image.read_bytes()
        return base64.b64encode(image).decode()

    async def describe_screenshot(
        self,
        image: bytes | str | Path,
        context: str = "",
    ) -> VisionResult:
        """
        Describe what's visible in a screenshot.

        Args:
            image: Screenshot bytes, file path, or Path object
            context: Optional context about what we're looking at

        Returns:
            VisionResult with description
        """
        b64 = self._encode_image(image)
        client = await self._get_client()

        prompt = "Describe what you see in this screenshot. Be concise and factual."
        if context:
            prompt = f"Context: {context}\n{prompt}"

        resp = await client.vision(b64, prompt, max_tokens=500)
        return VisionResult(
            success=resp.success,
            answer=resp.content,
            error=resp.error,
            model=resp.model,
            tokens_used=resp.tokens_used,
        )

    async def find_ui_element(
        self,
        image: bytes | str | Path,
        element_description: str,
    ) -> VisionResult:
        """
        Find a UI element in a screenshot and return its approximate position.

        Args:
            image: Screenshot
            element_description: What to find (e.g. "the submit button")

        Returns:
            VisionResult with position data in structured field
        """
        b64 = self._encode_image(image)
        client = await self._get_client()

        prompt = (
            f"Find the UI element: '{element_description}' in this screenshot. "
            f"Reply with JSON: {{\"found\": true/false, \"x\": pixel_x, \"y\": pixel_y, "
            f"\"width\": approx_width, \"height\": approx_height, \"label\": \"text on element\"}}. "
            f"Coordinates should be approximate center of the element. "
            f"Reply with ONLY JSON, no explanation."
        )

        resp = await client.vision(b64, prompt, max_tokens=200, temperature=0.1)

        result = VisionResult(
            success=resp.success,
            answer=resp.content,
            error=resp.error,
            model=resp.model,
            tokens_used=resp.tokens_used,
        )

        # Parse structured response
        if resp.success and resp.content:
            try:
                import json
                import re
                content = re.sub(r"^```(?:json)?\s*", "", resp.content)
                content = re.sub(r"\s*```$", "", content)
                result.structured = json.loads(content)
            except Exception:
                _debug(f"Could not parse UI element response: {resp.content[:100]}")

        return result

    async def read_text_from_image(
        self,
        image: bytes | str | Path,
        region_hint: str = "",
    ) -> VisionResult:
        """
        OCR — extract text from an image/screenshot.

        Args:
            image: Screenshot
            region_hint: Optional hint about which region to focus on

        Returns:
            VisionResult with extracted text
        """
        b64 = self._encode_image(image)
        client = await self._get_client()

        prompt = "Read ALL text visible in this image. Reply with the text only, preserving layout."
        if region_hint:
            prompt = f"Focus on: {region_hint}. {prompt}"

        resp = await client.vision(b64, prompt, max_tokens=1000)
        return VisionResult(
            success=resp.success,
            answer=resp.content,
            error=resp.error,
            model=resp.model,
            tokens_used=resp.tokens_used,
        )

    async def verify_drawing(
        self,
        image: bytes | str | Path,
        expected_description: str,
    ) -> VisionResult:
        """
        Verify that a drawing matches the expected description.

        Args:
            image: Screenshot of the drawing
            expected_description: What should be drawn (e.g. "red circle with black dots")

        Returns:
            VisionResult with verification result
        """
        b64 = self._encode_image(image)
        client = await self._get_client()

        prompt = (
            f"I asked for: '{expected_description}'. "
            f"Does this drawing match? Reply with JSON: "
            f"{{\"matches\": true/false, \"score\": 0-100, \"description\": \"what you see\", "
            f"\"issues\": [\"list of differences\"]}}. "
            f"Reply with ONLY JSON."
        )

        resp = await client.vision(b64, prompt, max_tokens=300, temperature=0.1)

        result = VisionResult(
            success=resp.success,
            answer=resp.content,
            error=resp.error,
            model=resp.model,
            tokens_used=resp.tokens_used,
        )

        if resp.success and resp.content:
            try:
                import json
                import re
                content = re.sub(r"^```(?:json)?\s*", "", resp.content)
                content = re.sub(r"\s*```$", "", content)
                result.structured = json.loads(content)
            except Exception:
                _debug(f"Could not parse verification response: {resp.content[:100]}")

        return result

    async def analyze_captcha(
        self,
        image: bytes | str | Path,
        captcha_type: str = "unknown",
    ) -> VisionResult:
        """
        Analyze a CAPTCHA image.

        Args:
            image: CAPTCHA screenshot
            captcha_type: Hint about CAPTCHA type

        Returns:
            VisionResult with CAPTCHA solution
        """
        b64 = self._encode_image(image)
        client = await self._get_client()

        if captcha_type == "image_captcha":
            prompt = (
                "This is a CAPTCHA image with distorted text/numbers. "
                "What characters do you see? Reply with ONLY the characters, nothing else."
            )
        elif captcha_type == "slider":
            prompt = (
                "This is a slider CAPTCHA puzzle. The puzzle piece needs to fit into a gap. "
                "What horizontal pixel offset (0-300) should the slider move? "
                "Reply with a single number only."
            )
        elif captcha_type in ("recaptcha_v2", "hcaptcha"):
            prompt = (
                "This is an image tile selection CAPTCHA. "
                "Read the instruction at the top. Which tiles (numbered 1-9 or 1-16, "
                "left-to-right, top-to-bottom) contain the requested object? "
                "Reply with comma-separated numbers only, e.g.: 1,3,7"
            )
        else:
            prompt = (
                "This appears to be a CAPTCHA. Describe what type it is and provide "
                "the solution. If text/numbers: reply with the text. "
                "If tile selection: reply with tile numbers. "
                "If slider: reply with pixel offset."
            )

        resp = await client.vision(b64, prompt, max_tokens=100, temperature=0.1)
        return VisionResult(
            success=resp.success,
            answer=resp.content,
            error=resp.error,
            model=resp.model,
            tokens_used=resp.tokens_used,
        )
