"""
CAPTCHA solving via LLM vision for NLP2CMD.

Supports:
- Image CAPTCHA (text/number recognition via LLM OCR)
- reCAPTCHA v2 (checkbox + image tile selection)
- hCaptcha (image tile selection)
- Slider CAPTCHA (puzzle piece alignment)

Uses OpenRouter → Gemini 2.5 Pro Preview for vision tasks.
"""

from __future__ import annotations

import base64
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Optional

_DEBUG = os.environ.get("NLP2CMD_DEBUG", "").lower() in ("1", "true", "yes")


def _debug(msg: str) -> None:
    if _DEBUG:
        print(f"DEBUG [CaptchaSolver] {msg}", file=sys.stderr, flush=True)


@dataclass
class CaptchaInfo:
    """Detected CAPTCHA information."""
    captcha_type: str  # "image_captcha", "recaptcha_v2", "hcaptcha", "slider"
    element: Any  # Playwright element handle
    frame: Any = None  # iframe content frame, if applicable
    confidence: float = 0.0


class CaptchaSolver:
    """
    CAPTCHA detection and solving via LLM vision (OpenRouter → Gemini 2.5 Pro).

    Pipeline:
    1. detect_captcha(page) — scans page for known CAPTCHA types
    2. solve(page, captcha_info) — dispatches to type-specific solver
    3. Each solver: screenshot → LLM vision → interact with page

    Environment:
        OPENROUTER_API_KEY — required for LLM vision API calls
    """

    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
    DEFAULT_MODEL = "google/gemini-2.5-pro-preview"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Args:
            api_key: OpenRouter API key. Falls back to OPENROUTER_API_KEY env var.
            model: LLM model to use. Defaults to Gemini 2.5 Pro Preview.
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or self.DEFAULT_MODEL

    # ── Detection ────────────────────────────────────────────────────

    async def detect_captcha(self, page: Any) -> Optional[CaptchaInfo]:
        """
        Detect CAPTCHA on the current page.

        Checks for (in order):
        1. reCAPTCHA v2 iframe
        2. hCaptcha iframe
        3. Custom image CAPTCHA
        4. Slider CAPTCHA

        Returns:
            CaptchaInfo if found, None otherwise
        """
        # reCAPTCHA v2
        try:
            recaptcha = await page.query_selector('iframe[src*="recaptcha"]')
            if recaptcha:
                _debug("Detected reCAPTCHA v2")
                return CaptchaInfo(
                    captcha_type="recaptcha_v2",
                    element=recaptcha,
                    confidence=0.95,
                )
        except Exception as e:
            _debug(f"reCAPTCHA detection error: {e}")

        # hCaptcha
        try:
            hcaptcha = await page.query_selector('iframe[src*="hcaptcha"]')
            if hcaptcha:
                _debug("Detected hCaptcha")
                return CaptchaInfo(
                    captcha_type="hcaptcha",
                    element=hcaptcha,
                    confidence=0.95,
                )
        except Exception as e:
            _debug(f"hCaptcha detection error: {e}")

        # Image CAPTCHA (custom)
        try:
            selectors = [
                'img[src*="captcha"]',
                'img[alt*="captcha"]',
                '.captcha-image',
                '#captcha-image',
                'img[class*="captcha"]',
                'img[id*="captcha"]',
            ]
            for selector in selectors:
                captcha_img = await page.query_selector(selector)
                if captcha_img:
                    _debug(f"Detected image CAPTCHA via {selector}")
                    return CaptchaInfo(
                        captcha_type="image_captcha",
                        element=captcha_img,
                        confidence=0.85,
                    )
        except Exception as e:
            _debug(f"Image CAPTCHA detection error: {e}")

        # Slider CAPTCHA
        try:
            slider_selectors = [
                '.slider-captcha',
                '[class*="slide-verify"]',
                '[class*="slider-verify"]',
                '.geetest_slider',
                '.nc_wrapper',
            ]
            for selector in slider_selectors:
                slider = await page.query_selector(selector)
                if slider:
                    _debug(f"Detected slider CAPTCHA via {selector}")
                    return CaptchaInfo(
                        captcha_type="slider",
                        element=slider,
                        confidence=0.80,
                    )
        except Exception as e:
            _debug(f"Slider CAPTCHA detection error: {e}")

        return None

    # ── Solving dispatch ─────────────────────────────────────────────

    async def solve(self, page: Any, captcha_info: CaptchaInfo) -> dict[str, Any]:
        """
        Solve detected CAPTCHA.

        Args:
            page: Playwright page
            captcha_info: Detected CAPTCHA info

        Returns:
            Dict with 'success', 'type', 'attempts', 'error'
        """
        if not self.api_key:
            return {
                "success": False,
                "type": captcha_info.captcha_type,
                "error": "OPENROUTER_API_KEY not set — required for CAPTCHA solving",
            }

        _debug(f"Solving {captcha_info.captcha_type} CAPTCHA")

        handlers = {
            "image_captcha": self._solve_image_captcha,
            "recaptcha_v2": self._solve_recaptcha_v2,
            "hcaptcha": self._solve_hcaptcha,
            "slider": self._solve_slider_captcha,
        }

        handler = handlers.get(captcha_info.captcha_type)
        if not handler:
            return {
                "success": False,
                "type": captcha_info.captcha_type,
                "error": f"Unsupported CAPTCHA type: {captcha_info.captcha_type}",
            }

        try:
            success = await handler(page, captcha_info)
            return {
                "success": success,
                "type": captcha_info.captcha_type,
            }
        except Exception as e:
            return {
                "success": False,
                "type": captcha_info.captcha_type,
                "error": str(e),
            }

    # ── Image CAPTCHA ────────────────────────────────────────────────

    async def _solve_image_captcha(self, page: Any, info: CaptchaInfo) -> bool:
        """
        Solve text/number image CAPTCHA.

        1. Screenshot the CAPTCHA image
        2. Send to LLM for OCR
        3. Type the answer into the input field
        """
        element = info.element
        screenshot = await element.screenshot()
        b64 = base64.b64encode(screenshot).decode()

        answer = await self._ask_llm_vision(
            image_b64=b64,
            prompt=(
                "This is a CAPTCHA image. What text or numbers do you see? "
                "Reply with ONLY the characters you see, no explanation, no quotes. "
                "If it's distorted text, do your best to read it accurately."
            ),
        )

        if not answer:
            _debug("LLM returned no answer for image CAPTCHA")
            return False

        answer = answer.strip().strip("'\"")
        _debug(f"Image CAPTCHA answer: {answer}")

        # Find input field near the captcha
        input_selectors = [
            'input[name*="captcha"]',
            'input[id*="captcha"]',
            'input[placeholder*="captcha" i]',
            'input[placeholder*="code" i]',
            'input[placeholder*="kod" i]',
            'input[aria-label*="captcha" i]',
        ]
        for selector in input_selectors:
            input_field = await page.query_selector(selector)
            if input_field:
                await input_field.fill(answer)
                _debug(f"Filled CAPTCHA answer via {selector}")
                return True

        # Fallback: find nearest text input
        input_field = await page.query_selector(
            'input[type="text"]:near(img[src*="captcha"])'
        )
        if input_field:
            await input_field.fill(answer)
            return True

        _debug("Could not find CAPTCHA input field")
        return False

    # ── reCAPTCHA v2 ─────────────────────────────────────────────────

    async def _solve_recaptcha_v2(self, page: Any, info: CaptchaInfo) -> bool:
        """
        Solve reCAPTCHA v2.

        Step 1: Click "I'm not a robot" checkbox
        Step 2: If image challenge appears, screenshot → LLM → click tiles
        Step 3: Submit
        """
        frame_element = info.element
        try:
            content_frame = await frame_element.content_frame()
        except Exception:
            _debug("Could not access reCAPTCHA frame")
            return False

        # Step 1: Click checkbox
        checkbox = await content_frame.query_selector('.recaptcha-checkbox-border')
        if checkbox:
            await checkbox.click()
            await page.wait_for_timeout(2000)
        else:
            _debug("Could not find reCAPTCHA checkbox")
            return False

        # Step 2: Check if challenge appeared
        challenge_frame = await page.query_selector('iframe[title*="challenge"]')
        if not challenge_frame:
            _debug("No challenge appeared — checkbox click was sufficient")
            return True  # Checkbox alone was enough

        try:
            challenge_content = await challenge_frame.content_frame()
        except Exception:
            _debug("Could not access challenge frame")
            return False

        # Step 3: Screenshot challenge → LLM
        return await self._solve_tile_challenge(page, challenge_content)

    async def _solve_tile_challenge(
        self, page: Any, challenge_frame: Any, max_attempts: int = 3
    ) -> bool:
        """Solve image tile selection challenge (reCAPTCHA / hCaptcha)."""
        for attempt in range(max_attempts):
            _debug(f"Tile challenge attempt {attempt + 1}/{max_attempts}")

            challenge_area = await challenge_frame.query_selector(
                '.rc-imageselect, .challenge-container, .task-image'
            )
            if not challenge_area:
                _debug("Could not find challenge area")
                return False

            screenshot = await challenge_area.screenshot()
            b64 = base64.b64encode(screenshot).decode()

            tiles_answer = await self._ask_llm_vision(
                image_b64=b64,
                prompt=(
                    "This is a reCAPTCHA/hCaptcha image selection challenge. "
                    "Look at the instruction at the top and the grid of images below. "
                    "Which tiles (numbered 1-9 or 1-16, left-to-right, top-to-bottom) "
                    "contain the requested object? "
                    "Reply with ONLY comma-separated numbers, e.g.: 1,3,7 "
                    "If no tiles match, reply: NONE"
                ),
            )

            if not tiles_answer or tiles_answer.strip() == "NONE":
                _debug("LLM could not identify tiles")
                return False

            # Parse tile numbers
            try:
                tile_indices = [
                    int(t.strip()) - 1
                    for t in tiles_answer.split(",")
                    if t.strip().isdigit()
                ]
            except ValueError:
                _debug(f"Could not parse tile answer: {tiles_answer}")
                return False

            # Click tiles
            tiles = await challenge_frame.query_selector_all(
                '.rc-imageselect-tile, .task-image .image'
            )
            for idx in tile_indices:
                if 0 <= idx < len(tiles):
                    await tiles[idx].click()
                    await page.wait_for_timeout(400)

            # Submit
            verify_btn = await challenge_frame.query_selector(
                '#recaptcha-verify-button, .verify-button, button[type="submit"]'
            )
            if verify_btn:
                await verify_btn.click()
                await page.wait_for_timeout(2000)

            # Check if solved (challenge frame disappears)
            remaining = await page.query_selector('iframe[title*="challenge"]')
            if not remaining:
                _debug("Challenge solved!")
                return True

        return False

    # ── hCaptcha ─────────────────────────────────────────────────────

    async def _solve_hcaptcha(self, page: Any, info: CaptchaInfo) -> bool:
        """Solve hCaptcha — similar to reCAPTCHA v2 with tile selection."""
        frame_element = info.element
        try:
            content_frame = await frame_element.content_frame()
        except Exception:
            _debug("Could not access hCaptcha frame")
            return False

        # Click checkbox
        checkbox = await content_frame.query_selector('#checkbox')
        if checkbox:
            await checkbox.click()
            await page.wait_for_timeout(2000)

        # Check for challenge
        challenge_frame = await page.query_selector(
            'iframe[src*="hcaptcha"][title*="challenge"]'
        )
        if not challenge_frame:
            return True  # No challenge needed

        try:
            challenge_content = await challenge_frame.content_frame()
            return await self._solve_tile_challenge(page, challenge_content)
        except Exception as e:
            _debug(f"hCaptcha challenge error: {e}")
            return False

    # ── Slider CAPTCHA ───────────────────────────────────────────────

    async def _solve_slider_captcha(self, page: Any, info: CaptchaInfo) -> bool:
        """
        Solve slider/puzzle CAPTCHA.

        1. Screenshot the puzzle area
        2. LLM determines horizontal offset
        3. Drag slider to that position with human-like movement
        """
        element = info.element
        screenshot = await element.screenshot()
        b64 = base64.b64encode(screenshot).decode()

        offset_str = await self._ask_llm_vision(
            image_b64=b64,
            prompt=(
                "This is a slider CAPTCHA puzzle. A puzzle piece needs to be dragged "
                "horizontally to fit into a gap in the image. "
                "What horizontal pixel offset (0-300) should the slider be moved to "
                "align the piece with the gap? "
                "Reply with a single number only."
            ),
        )

        if not offset_str:
            return False

        try:
            offset = int(re.search(r"\d+", offset_str).group(0))
        except (ValueError, AttributeError):
            _debug(f"Could not parse slider offset: {offset_str}")
            return False

        _debug(f"Slider offset: {offset}px")

        # Find slider handle
        handle_selectors = [
            '.slider-handle',
            '[class*="slide-btn"]',
            '.drag-btn',
            '.geetest_slider_button',
            '.nc_iconfont',
        ]
        slider_handle = None
        for selector in handle_selectors:
            slider_handle = await page.query_selector(selector)
            if slider_handle:
                break

        if not slider_handle:
            _debug("Could not find slider handle")
            return False

        box = await slider_handle.bounding_box()
        if not box:
            return False

        # Human-like drag with slight vertical variance
        from nlp2cmd.automation.mouse_controller import MouseController, Point

        mouse = MouseController(page, human_like=True)
        start = Point(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        end = Point(start.x + offset, start.y)
        await mouse.drag(start, end, steps=30)

        await page.wait_for_timeout(1000)
        return True

    # ── LLM Vision API ───────────────────────────────────────────────

    async def _ask_llm_vision(self, image_b64: str, prompt: str) -> Optional[str]:
        """
        Send screenshot to LLM vision API and get response.

        Args:
            image_b64: Base64-encoded PNG screenshot
            prompt: Instruction prompt for the LLM

        Returns:
            LLM response text or None
        """
        if not self.api_key:
            _debug("No API key for LLM vision")
            return None

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.OPENROUTER_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/wronai/nlp2cmd",
                        "X-Title": "NLP2CMD CAPTCHA Solver",
                    },
                    json={
                        "model": self.model,
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {
                                    "url": f"data:image/png;base64,{image_b64}"
                                }},
                                {"type": "text", "text": prompt},
                            ],
                        }],
                        "max_tokens": 100,
                        "temperature": 0.1,
                    },
                    timeout=30,
                )

                if resp.status_code != 200:
                    _debug(f"LLM API error: {resp.status_code} {resp.text[:200]}")
                    return None

                data = resp.json()
                answer = data["choices"][0]["message"]["content"].strip()
                _debug(f"LLM response: {answer[:100]}")
                return answer

        except Exception as e:
            _debug(f"LLM vision API error: {e}")
            return None
