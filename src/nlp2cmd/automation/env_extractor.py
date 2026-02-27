"""
API key extraction from browser sessions for NLP2CMD.

Extracts API keys from authenticated browser sessions (OpenRouter, Anthropic,
OpenAI, etc.) and saves them to .env files. Uses persistent browser contexts
to preserve login sessions.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


_DEBUG = os.environ.get("NLP2CMD_DEBUG", "").lower() in ("1", "true", "yes")


def _debug(msg: str) -> None:
    if _DEBUG:
        print(f"DEBUG [EnvExtractor] {msg}", file=sys.stderr, flush=True)


@dataclass
class ServiceConfig:
    """Configuration for a known API service."""
    name: str
    url: str
    login_url: str = ""
    key_selectors: list[str] = field(default_factory=list)
    key_pattern: str = ""
    env_var: str = ""
    instructions: str = ""


# Known API services and their key page configurations
KNOWN_SERVICES: dict[str, ServiceConfig] = {
    "openrouter": ServiceConfig(
        name="OpenRouter",
        url="https://openrouter.ai/settings/keys",
        login_url="https://openrouter.ai/auth/login",
        key_selectors=["[data-testid='api-key']", ".api-key-value", "code", "pre"],
        key_pattern=r"sk-or-v1-[a-f0-9]{64}",
        env_var="OPENROUTER_API_KEY",
        instructions="Navigate to OpenRouter Settings → Keys to find your API key.",
    ),
    "anthropic": ServiceConfig(
        name="Anthropic",
        url="https://console.anthropic.com/settings/keys",
        login_url="https://console.anthropic.com/login",
        key_selectors=["[data-testid='api-key']", ".key-value", "code"],
        key_pattern=r"sk-ant-[a-zA-Z0-9-]{40,}",
        env_var="ANTHROPIC_API_KEY",
        instructions="Navigate to Anthropic Console → Settings → API Keys.",
    ),
    "openai": ServiceConfig(
        name="OpenAI",
        url="https://platform.openai.com/api-keys",
        login_url="https://platform.openai.com/login",
        key_selectors=["[data-testid='api-key']", ".key-value", "code", "input[type='text']"],
        key_pattern=r"sk-[a-zA-Z0-9]{48,}",
        env_var="OPENAI_API_KEY",
        instructions="Navigate to OpenAI Platform → API Keys.",
    ),
    "github": ServiceConfig(
        name="GitHub",
        url="https://github.com/settings/tokens",
        login_url="https://github.com/login",
        key_selectors=["#new-oauth-token", ".token", "code", "input[type='text']"],
        key_pattern=r"gh[ps]_[A-Za-z0-9_]{36,}",
        env_var="GITHUB_TOKEN",
        instructions="Navigate to GitHub → Settings → Developer settings → Personal access tokens.",
    ),
    "huggingface": ServiceConfig(
        name="Hugging Face",
        url="https://huggingface.co/settings/tokens",
        login_url="https://huggingface.co/login",
        key_selectors=[".token-value", "code", "input[type='text']"],
        key_pattern=r"hf_[A-Za-z0-9]{34,}",
        env_var="HF_TOKEN",
        instructions="Navigate to Hugging Face → Settings → Access Tokens.",
    ),
    "replicate": ServiceConfig(
        name="Replicate",
        url="https://replicate.com/account/api-tokens",
        login_url="https://replicate.com/signin",
        key_selectors=[".token", "code", "input[type='text']"],
        key_pattern=r"r8_[A-Za-z0-9]{37,}",
        env_var="REPLICATE_API_TOKEN",
        instructions="Navigate to Replicate → Account → API Tokens.",
    ),
}

# NL aliases for service detection (Polish + English)
SERVICE_ALIASES: dict[str, str] = {
    "openrouter": "openrouter",
    "open router": "openrouter",
    "anthropic": "anthropic",
    "claude": "anthropic",
    "openai": "openai",
    "gpt": "openai",
    "chatgpt": "openai",
    "github": "github",
    "huggingface": "huggingface",
    "hugging face": "huggingface",
    "hf": "huggingface",
    "replicate": "replicate",
}


class EnvExtractor:
    """
    Extracts API keys from browser sessions and saves to .env files.

    Uses Playwright persistent browser context to preserve login sessions.
    Supports multiple extraction strategies:
    1. DOM selectors — fast, direct CSS queries
    2. Regex on page text — fallback for dynamically rendered keys
    3. Screenshot + LLM OCR — last resort via OpenRouter/Gemini vision
    """

    BROWSER_PROFILE_DIR = Path.home() / ".nlp2cmd" / "browser_profile"

    def __init__(self, llm_api_key: Optional[str] = None):
        """
        Args:
            llm_api_key: OpenRouter API key for LLM-based OCR fallback.
                        Falls back to OPENROUTER_API_KEY env var.
        """
        self.llm_api_key = llm_api_key or os.getenv("OPENROUTER_API_KEY")

    @staticmethod
    def detect_service(text: str) -> Optional[str]:
        """
        Detect which API service the user is referring to from NL text.

        Args:
            text: Natural language query (e.g. "wyciągnij klucz z OpenRouter")

        Returns:
            Service key (e.g. "openrouter") or None
        """
        text_lower = text.lower()
        for alias, service_key in SERVICE_ALIASES.items():
            if alias in text_lower:
                return service_key
        return None

    @staticmethod
    def detect_env_path(text: str, default: str = ".env") -> str:
        """
        Extract target .env file path from NL text.

        Args:
            text: Natural language query
            default: Default path if not found

        Returns:
            Path string for the .env file
        """
        # Look for explicit path patterns
        patterns = [
            r"(?:do|to|w|into)\s+(?:pliku\s+)?([~./][\w./_-]+\.env\b[\w.]*)",
            r"(?:save|zapisz|save to)\s+([~./][\w./_-]+\.env\b[\w.]*)",
            r"(\.env(?:\.\w+)?)\b",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                path = m.group(1).strip()
                if path.startswith("~"):
                    path = str(Path(path).expanduser())
                return path
        return default

    def get_service_config(self, service: str) -> Optional[ServiceConfig]:
        """Get configuration for a known service."""
        return KNOWN_SERVICES.get(service)

    def list_services(self) -> list[str]:
        """List all supported service names."""
        return list(KNOWN_SERVICES.keys())

    async def extract_and_save(
        self,
        service: str,
        env_path: str = ".env",
        headless: bool = False,
        timeout_ms: int = 30000,
    ) -> dict[str, Any]:
        """
        Extract API key from browser and save to .env file.

        Pipeline:
        1. Open persistent browser (preserves login cookies)
        2. Navigate to service's key page
        3. Try DOM selectors → regex → LLM OCR
        4. Save to .env (append, don't overwrite existing)

        Args:
            service: Service name (e.g. "openrouter")
            env_path: Path to .env file
            headless: Run browser in headless mode (False recommended for first login)
            timeout_ms: Page load timeout

        Returns:
            Dict with 'success', 'key' (masked), 'env_var', 'env_path', 'error'
        """
        config = KNOWN_SERVICES.get(service)
        if not config:
            return {
                "success": False,
                "error": f"Unknown service: {service}. Supported: {', '.join(KNOWN_SERVICES)}",
            }

        _debug(f"Extracting {config.name} API key from {config.url}")

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return {
                "success": False,
                "error": "Playwright is required. Install: pip install playwright && playwright install",
            }

        result: dict[str, Any] = {"success": False, "service": service}

        async with async_playwright() as pw:
            # Persistent context preserves login sessions
            self.BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=str(self.BROWSER_PROFILE_DIR),
                headless=headless,
                viewport={"width": 1280, "height": 720},
            )

            try:
                page = context.pages[0] if context.pages else await context.new_page()

                # Navigate to keys page
                _debug(f"Navigating to {config.url}")
                await page.goto(config.url, wait_until="networkidle", timeout=timeout_ms)
                await page.wait_for_timeout(2000)

                # Check if redirected to login
                if config.login_url and config.login_url in page.url:
                    _debug("Redirected to login page — waiting for user to log in")
                    result["needs_login"] = True
                    result["login_url"] = config.login_url
                    result["instructions"] = (
                        f"Please log in to {config.name} in the browser window. "
                        f"The key will be extracted automatically after login."
                    )
                    # Wait for user to log in (up to 2 minutes)
                    try:
                        await page.wait_for_url(
                            f"**{config.url.split('//')[1].split('/')[0]}/**",
                            timeout=120000,
                        )
                        await page.goto(config.url, wait_until="networkidle", timeout=timeout_ms)
                        await page.wait_for_timeout(2000)
                    except Exception:
                        result["error"] = "Login timeout — please log in and try again"
                        return result

                # Try extraction strategies
                key = await self._extract_key_from_page(page, config)

                if key:
                    masked = self._mask_key(key)
                    _debug(f"Found key: {masked}")
                    self._save_to_env(key, config.env_var, env_path)
                    result.update({
                        "success": True,
                        "key_masked": masked,
                        "env_var": config.env_var,
                        "env_path": env_path,
                    })
                else:
                    # Screenshot for debugging
                    screenshot_path = Path.home() / ".nlp2cmd" / f"debug_{service}.png"
                    await page.screenshot(path=str(screenshot_path))
                    result["error"] = (
                        f"Could not find API key on {config.url}. "
                        f"Debug screenshot saved to {screenshot_path}. "
                        f"{config.instructions}"
                    )

            finally:
                await context.close()

        return result

    async def _extract_key_from_page(
        self, page: Any, config: ServiceConfig
    ) -> Optional[str]:
        """
        Multi-tier key extraction.

        Tier 1: CSS selectors
        Tier 2: Regex on full page text
        Tier 3: Screenshot + LLM OCR (if API key available)
        """
        # Tier 1: DOM selectors
        for selector in config.key_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for el in elements:
                    text = await el.text_content()
                    if text and re.search(config.key_pattern, text.strip()):
                        _debug(f"Tier 1 match via selector '{selector}'")
                        m = re.search(config.key_pattern, text.strip())
                        if m:
                            return m.group(0)
            except Exception as e:
                _debug(f"Selector '{selector}' failed: {e}")

        # Tier 2: Regex on full page text
        try:
            body_text = await page.text_content("body")
            if body_text:
                match = re.search(config.key_pattern, body_text)
                if match:
                    _debug("Tier 2 match via body text regex")
                    return match.group(0)
        except Exception as e:
            _debug(f"Body text extraction failed: {e}")

        # Tier 3: Screenshot + LLM OCR
        if self.llm_api_key:
            try:
                screenshot_bytes = await page.screenshot()
                key = await self._llm_ocr_extract(screenshot_bytes, config)
                if key:
                    _debug("Tier 3 match via LLM OCR")
                    return key
            except Exception as e:
                _debug(f"LLM OCR failed: {e}")

        return None

    async def _llm_ocr_extract(
        self, screenshot: bytes, config: ServiceConfig
    ) -> Optional[str]:
        """Use LLM vision (OpenRouter → Gemini) to extract key from screenshot."""
        if not self.llm_api_key:
            return None

        try:
            import base64
            import httpx

            b64 = base64.b64encode(screenshot).decode()

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.llm_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "google/gemini-2.5-pro-preview",
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {
                                    "url": f"data:image/png;base64,{b64}"
                                }},
                                {"type": "text", "text": (
                                    f"Look at this screenshot of {config.name} API keys page. "
                                    f"Find any API key matching the pattern: {config.key_pattern}. "
                                    f"Reply with ONLY the key, no explanation. "
                                    f"If no key found, reply: NONE"
                                )},
                            ],
                        }],
                        "max_tokens": 150,
                    },
                    timeout=30,
                )
                data = resp.json()
                answer = data["choices"][0]["message"]["content"].strip()
                if answer and answer != "NONE" and re.search(config.key_pattern, answer):
                    m = re.search(config.key_pattern, answer)
                    return m.group(0) if m else None
        except Exception as e:
            _debug(f"LLM OCR error: {e}")

        return None

    @staticmethod
    def _mask_key(key: str) -> str:
        """Mask API key for safe display (show first 8 and last 4 chars)."""
        if len(key) <= 16:
            return key[:4] + "…" + key[-4:]
        return key[:8] + "…" + key[-4:]

    @staticmethod
    def _save_to_env(key: str, var_name: str, env_path: str) -> None:
        """
        Append or update API key in .env file.

        - Creates file if it doesn't exist
        - Updates existing var if present
        - Appends new var if not present
        - Sets file permissions to 600 (owner read/write only)
        """
        path = Path(env_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = []
        found = False

        if path.exists():
            lines = path.read_text().splitlines()
            for i, line in enumerate(lines):
                if line.strip().startswith(f"{var_name}="):
                    lines[i] = f"{var_name}={key}"
                    found = True
                    break

        if not found:
            if lines and lines[-1].strip():
                lines.append("")  # blank line separator
            lines.append(f"{var_name}={key}")

        path.write_text("\n".join(lines) + "\n")

        # Secure permissions (owner-only)
        try:
            os.chmod(str(path), 0o600)
        except OSError:
            pass  # Windows doesn't support chmod the same way

        _debug(f"Saved {var_name} to {path} (permissions: 600)")
