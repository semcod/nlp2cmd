"""Query Normalization - Steps 1a-1e.

1a. Lowercase conversion
1b. Punctuation removal
1c. Whitespace normalization
1d. Unicode normalization (NFKC)
1e. Stopword removal (optional)
"""

import re
import unicodedata
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from .config import NormalizationConfig


@dataclass
class NormalizationResult:
    """Result of query normalization."""
    original: str
    normalized: str
    tokens: List[str] = field(default_factory=list)
    language: str = "en"
    steps_applied: List[str] = field(default_factory=list)


class QueryNormalizer:
    """Normalize queries for consistent processing."""
    
    def __init__(self, config: Optional[NormalizationConfig] = None):
        self.config = config or NormalizationConfig()
    
    def normalize(self, query: str, language: str = "en") -> NormalizationResult:
        """Apply full normalization pipeline (1a-1e)."""
        result = NormalizationResult(
            original=query,
            normalized=query,
            language=language,
        )
        
        # 1d. Unicode normalization (NFKC) - do first
        if self.config.unicode_normalize:
            result.normalized = self._unicode_normalize(result.normalized)
            result.steps_applied.append("unicode_nfkc")
        
        # 1a. Lowercase conversion
        if self.config.lowercase:
            result.normalized = self._lowercase(result.normalized)
            result.steps_applied.append("lowercase")
        
        # 1b. Punctuation removal
        if self.config.remove_punctuation:
            result.normalized = self._remove_punctuation(result.normalized)
            result.steps_applied.append("remove_punctuation")
        
        # 1c. Whitespace normalization
        if self.config.normalize_whitespace:
            result.normalized = self._normalize_whitespace(result.normalized)
            result.steps_applied.append("normalize_whitespace")
        
        # 1e. Stopword removal
        if self.config.remove_stopwords:
            result.normalized = self._remove_stopwords(result.normalized, language)
            result.steps_applied.append("remove_stopwords")
        
        # Tokenize
        result.tokens = self._tokenize(result.normalized)
        
        return result
    
    def _unicode_normalize(self, text: str) -> str:
        """1d. Normalize Unicode to NFKC form."""
        return unicodedata.normalize('NFKC', text)
    
    def _lowercase(self, text: str) -> str:
        """1a. Convert to lowercase."""
        return text.lower()
    
    def _remove_punctuation(self, text: str) -> str:
        """1b. Remove punctuation marks."""
        # Keep alphanumeric, whitespace, and dots (for qualified names)
        return re.sub(r'[^\w\s\.]', ' ', text)
    
    def _normalize_whitespace(self, text: str) -> str:
        """1c. Normalize whitespace (multiple spaces -> single)."""
        return ' '.join(text.split())
    
    def _remove_stopwords(self, text: str, language: str) -> str:
        """1e. Remove stopwords."""
        stopwords = self.config.stopwords.get(language, [])
        words = text.split()
        filtered = [w for w in words if w not in stopwords]
        return ' '.join(filtered)
    
    def _tokenize(self, text: str) -> List[str]:
        """Split text into tokens."""
        return text.split()
    
    # Individual step methods for granular control
    def step_1a_lowercase(self, text: str) -> str:
        """Step 1a: Convert to lowercase."""
        return text.lower()
    
    def step_1b_remove_punctuation(self, text: str) -> str:
        """Step 1b: Remove punctuation."""
        return re.sub(r'[^\w\s\.]', ' ', text)
    
    def step_1c_normalize_whitespace(self, text: str) -> str:
        """Step 1c: Normalize whitespace."""
        return ' '.join(text.split())
    
    def step_1d_unicode_normalize(self, text: str) -> str:
        """Step 1d: Unicode NFKC normalization."""
        return unicodedata.normalize('NFKC', text)
    
    def step_1e_remove_stopwords(self, text: str, language: str = "en") -> str:
        """Step 1e: Remove stopwords."""
        stopwords = self.config.stopwords.get(language, [])
        words = text.split()
        filtered = [w for w in words if w not in stopwords]
        return ' '.join(filtered)
