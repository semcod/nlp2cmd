"""Radio button extractor for radio button groups."""

from __future__ import annotations
from typing import Any
import logging

log = logging.getLogger("nlp2cmd.page_schema.radio")


class RadioExtractor:
    """Extract radio button groups (for token type selection, etc.)."""
    
    MAX_RADIOS = 10
    
    def extract(self, page: Any) -> list[dict[str, str]]:
        """Extract radio buttons from the page."""
        radios: list[dict[str, str]] = []
        
        try:
            radio_locators = page.locator("input[type='radio']:visible")
            
            count = radio_locators.count()
            for i in range(min(count, self.MAX_RADIOS)):
                try:
                    el = radio_locators.nth(i)
                    radio_data = self._extract_radio_data(el, page, i)
                    if radio_data:
                        radios.append(radio_data)
                except Exception:
                    continue
                    
        except Exception as e:
            log.debug("Radio extraction error: %s", e)
        
        return radios
    
    def _extract_radio_data(self, el: Any, page: Any, index: int) -> dict[str, str] | None:
        """Extract data from a single radio button element."""
        value = el.get_attribute("value") or ""
        name = el.get_attribute("name") or ""
        test_id = el.get_attribute("data-testid") or ""
        el_id = el.get_attribute("id") or ""
        
        # Find associated label text
        label_text = ""
        if el_id:
            try:
                label_sel = f"label[for='{el_id}']"
                label_el = page.query_selector(label_sel)
                if label_el:
                    label_text = (label_el.text_content() or "").strip()[:30]
            except Exception:
                pass
        
        # Build selector
        if test_id:
            sel = f"[data-testid='{test_id}']"
        elif name and value:
            sel = f"input[name='{name}'][value='{value}']"
        elif value:
            sel = f"input[type='radio'][value='{value}']"
        else:
            sel = f"input[type='radio']:visible >> nth={index}"
        
        return {
            "value": value,
            "name": name,
            "label": label_text,
            "selector": sel,
        }
