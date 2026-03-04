"""Copy button extractor for copy-to-clipboard buttons."""

from __future__ import annotations
from typing import Any
import logging

log = logging.getLogger("nlp2cmd.page_schema.copy_button")


class CopyButtonExtractor:
    """Extract buttons likely used to copy tokens to clipboard."""
    
    MAX_COPY_BUTTONS = 5
    
    def extract(self, page: Any) -> list[dict[str, str]]:
        """Extract copy buttons from the page."""
        copy_buttons: list[dict[str, str]] = []
        
        try:
            copy_locators = page.locator(
                "button:has-text('Copy'):visible, "
                "button:has-text('Kopiuj'):visible, "
                "button[aria-label*='copy' i]:visible, "
                "button[aria-label*='clipboard' i]:visible, "
                "[data-testid*='copy']:visible"
            )
            
            count = copy_locators.count()
            for i in range(min(count, self.MAX_COPY_BUTTONS)):
                try:
                    el = copy_locators.nth(i)
                    button_data = self._extract_copy_button_data(el)
                    if button_data:
                        copy_buttons.append(button_data)
                except Exception:
                    continue
                    
        except Exception as e:
            log.debug("Copy button extraction error: %s", e)
        
        return copy_buttons
    
    def _extract_copy_button_data(self, el: Any) -> dict[str, str] | None:
        """Extract data from a single copy button element."""
        text = (el.text_content() or "").strip()[:40]
        test_id = el.get_attribute("data-testid") or ""
        aria = el.get_attribute("aria-label") or ""
        
        # Build selector
        if test_id:
            sel = f"[data-testid='{test_id}']"
        elif aria:
            sel = f"button[aria-label='{aria}']"
        elif text:
            sel = f"text='{text}'"
        else:
            sel = "button >> nth=0"
        
        return {
            "text": text,
            "selector": sel,
        }
