"""Button extractor for visible clickable elements."""

from __future__ import annotations
from typing import Any
import logging

log = logging.getLogger("nlp2cmd.page_schema.button")


class ButtonExtractor:
    """Extract visible clickable elements (buttons, role=button, etc.)."""
    
    MAX_BUTTONS = 30
    
    def extract(self, page: Any) -> list[dict[str, str]]:
        """Extract buttons from the page."""
        buttons: list[dict[str, str]] = []
        
        try:
            btn_locators = page.locator(
                "button:visible, a[role='button']:visible, "
                "[role='button']:visible"
            )
            
            count = btn_locators.count()
            for i in range(min(count, self.MAX_BUTTONS)):
                try:
                    el = btn_locators.nth(i)
                    button_data = self._extract_button_data(el)
                    if button_data:
                        buttons.append(button_data)
                except Exception:
                    continue
                    
        except Exception as e:
            log.debug("Button extraction error: %s", e)
        
        return buttons
    
    def _extract_button_data(self, el: Any) -> dict[str, str] | None:
        """Extract data from a single button element."""
        text = (el.text_content() or "").strip()[:80]
        if not text or len(text) < 2:
            return None
        
        # Build a unique selector
        test_id = el.get_attribute("data-testid") or ""
        aria = el.get_attribute("aria-label") or ""
        
        if test_id:
            sel = f"[data-testid='{test_id}']"
        elif aria:
            sel = f"[aria-label='{aria}']"
        else:
            sel = f"text='{text}'"
        
        try:
            tag = el.evaluate("el => el.tagName.toLowerCase()")
        except Exception:
            tag = "button"
        
        return {
            "text": text,
            "selector": sel,
            "tag": tag,
        }
