"""Form input extractor for text inputs and textareas."""

from __future__ import annotations
from typing import Any
import logging

log = logging.getLogger("nlp2cmd.page_schema.form")


class FormExtractor:
    """Extract visible text input fields and textareas."""
    
    MAX_INPUTS = 15
    
    def extract(self, page: Any) -> list[dict[str, str]]:
        """Extract form inputs from the page."""
        forms: list[dict[str, str]] = []
        
        try:
            input_locators = page.locator(
                "input[type='text']:visible, input:not([type]):visible, "
                "textarea:visible"
            )
            
            count = input_locators.count()
            for i in range(min(count, self.MAX_INPUTS)):
                try:
                    el = input_locators.nth(i)
                    input_data = self._extract_input_data(el, i)
                    if input_data:
                        forms.append(input_data)
                except Exception:
                    continue
                    
        except Exception as e:
            log.debug("Form extraction error: %s", e)
        
        return forms
    
    def _extract_input_data(self, el: Any, index: int) -> dict[str, str] | None:
        """Extract data from a single input element."""
        name = el.get_attribute("name") or ""
        placeholder = el.get_attribute("placeholder") or ""
        inp_type = el.get_attribute("type") or "text"
        test_id = el.get_attribute("data-testid") or ""
        
        # Build selector
        if test_id:
            sel = f"[data-testid='{test_id}']"
        elif name:
            sel = f"input[name='{name}']"
        elif placeholder:
            sel = f"input[placeholder='{placeholder}']"
        else:
            sel = f"input[type='{inp_type}']:visible >> nth={index}"
        
        return {
            "name": name,
            "placeholder": placeholder,
            "selector": sel,
            "type": inp_type,
        }
