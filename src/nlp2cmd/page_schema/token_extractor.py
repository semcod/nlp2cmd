"""Token extractor for API keys and secret values."""

from __future__ import annotations
from typing import Any
import logging

log = logging.getLogger("nlp2cmd.page_schema.token")


class TokenExtractor:
    """Extract elements that look like API tokens/keys."""
    
    MAX_TOKENS_PER_SELECTOR = 5
    
    TOKEN_SELECTORS = [
        "input[readonly]",
        "input[type='text'][readonly]",
        "code",
        "pre",
        ".token-value",
        "[data-testid*='token']",
        ".api-key",
        "[class*='secret']",
        "[class*='token']",
    ]
    
    MIN_TOKEN_LENGTH = 10
    
    def extract(self, page: Any) -> list[dict[str, str]]:
        """Extract token-like elements from the page."""
        tokens: list[dict[str, str]] = []
        
        for selector in self.TOKEN_SELECTORS:
            try:
                els = page.query_selector_all(selector)
                for el in els[:self.MAX_TOKENS_PER_SELECTOR]:
                    try:
                        token_data = self._extract_token_data(el, selector)
                        if token_data:
                            tokens.append(token_data)
                    except Exception:
                        continue
            except Exception:
                continue
        
        return tokens
    
    def _extract_token_data(self, el: Any, selector: str) -> dict[str, str] | None:
        """Extract token data from an element."""
        text = (el.text_content() or el.get_attribute("value") or "").strip()
        
        if not text or len(text) < self.MIN_TOKEN_LENGTH:
            return None
        
        return {
            "selector": selector,
            "text_preview": text[:20] + "...",
            "length": str(len(text)),
        }
