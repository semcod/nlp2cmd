"""Field classifier for determining if fields are contact-like or junk."""

from __future__ import annotations
from typing import Optional
import logging

from .base import FieldInfo

log = logging.getLogger("nlp2cmd.page_analysis.classifier")


class FieldClassifier:
    """Classify form fields as contact-like or junk (search, cookie, etc.)."""
    
    # Junk field patterns
    JUNK_KEYWORDS = [
        "search", "szukaj", "wyszuki",
        "cookie", "consent",
        "captcha", "recaptcha", "g-recaptcha", "hcaptcha",
        "comment",
    ]
    
    JUNK_IDS = ["cky", "cmplz", "apbct__"]
    JUNK_NAMES = {"s", "q", "search", "query"}  # Removed email - it's a contact field
    
    # Contact field patterns
    CONTACT_TYPES = {"email", "tel", "textarea"}
    CONTACT_KEYWORDS = [
        "email", "e-mail", "mail",
        "telefon", "phone",
        "wiadomo", "message",
        "temat", "subject",
        "imi", "name",
    ]
    
    def classify(self, field_info: FieldInfo) -> tuple[bool, bool]:
        """Classify a field as (is_junk, is_contact).
        
        Returns:
            Tuple of (is_junk, is_contact) booleans
        """
        field_type = field_info.field_type.lower()
        name = field_info.name.lower()
        field_id = field_info.field_id.lower()
        placeholder = field_info.placeholder.lower()
        aria = field_info.aria_label.lower()
        
        haystack = " ".join([name, field_id, placeholder, aria])
        
        is_junk = self._is_junk(field_type, name, field_id, placeholder, aria, haystack)
        
        if is_junk:
            return True, False
        
        is_contact = self._is_contact(field_type, haystack)
        
        return is_junk, is_contact
    
    def _is_junk(
        self,
        field_type: str,
        name: str,
        field_id: str,
        placeholder: str,
        aria: str,
        haystack: str,
    ) -> bool:
        """Check if field is junk (search, cookie, captcha, etc.)."""
        # Search fields
        if field_type == "search" or name in self.JUNK_NAMES:
            return True
        
        for kw in self.JUNK_KEYWORDS[:3]:  # search keywords
            if kw in haystack:
                return True
        
        # Cookie/consent fields
        for kw in self.JUNK_KEYWORDS[3:5]:  # cookie keywords
            if kw in haystack:
                return True
        
        for junk_id in self.JUNK_IDS[:2]:  # cky, cmplz
            if field_id.startswith(junk_id) or junk_id in haystack:
                return True
        
        # Captcha fields
        for kw in self.JUNK_KEYWORDS[5:9]:  # captcha keywords
            if kw in haystack:
                return True
        
        # Comment fields - only if it looks like a comment form
        if "comment" in haystack and name in {"author", "url"}:
            return True
        
        return False
    
    def _is_contact(self, field_type: str, haystack: str) -> bool:
        """Check if field is contact-like."""
        # Direct type match
        if field_type in self.CONTACT_TYPES:
            return True
        
        # Keyword match
        for kw in self.CONTACT_KEYWORDS:
            if kw in haystack:
                return True
        
        return False
    
    def classify_batch(self, fields: list[FieldInfo]) -> tuple[int, int]:
        """Classify multiple fields and return counts.
        
        Returns:
            Tuple of (contact_count, junk_count)
        """
        contact_count = 0
        junk_count = 0
        
        for field in fields:
            is_junk, is_contact = self.classify(field)
            field.is_junk = is_junk
            field.is_contact = is_contact
            
            if is_junk:
                junk_count += 1
            if is_contact:
                contact_count += 1
        
        return contact_count, junk_count
