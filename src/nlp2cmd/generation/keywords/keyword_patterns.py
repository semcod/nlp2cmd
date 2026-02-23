"""
Keyword patterns for intent detection.

This module contains pattern definitions and loading functionality
for the keyword-based intent detection system.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

import nlp2cmd.generation.keywords as _keywords_pkg
from nlp2cmd.utils.data_files import find_data_files as _find_data_files_default

logger = logging.getLogger(__name__)


def _find_data_files(**kwargs):
    """Indirection so tests can monkeypatch nlp2cmd.generation.keywords.find_data_files."""
    fn = getattr(_keywords_pkg, 'find_data_files', _find_data_files_default)
    return fn(**kwargs)


def _normalize_polish_text(text: str) -> str:
    """Normalize Polish text for pattern matching."""
    # Basic normalization - can be extended
    return text.lower().strip()


def _dedupe_case_insensitive(items: List[str]) -> List[str]:
    """Deduplicate items case-insensitively while preserving order."""
    seen = set()
    out = []
    for item in items:
        lowered = item.lower()
        if lowered not in seen:
            seen.add(lowered)
            out.append(item)
    return out


class KeywordPatterns:
    """Manages keyword patterns for intent detection."""
    
    def __init__(self, custom_patterns_file: Optional[str] = None):
        """
        Initialize keyword patterns.
        
        Args:
            custom_patterns_file: Path to custom patterns JSON file
        """
        self.patterns: Dict[str, Dict[str, List[str]]] = {}
        self.domain_boosters: Dict[str, List[str]] = {}
        self.priority_intents: Dict[str, List[str]] = {}
        self.fast_path_browser_keywords: List[str] = []
        self.fast_path_search_keywords: List[str] = []
        self.fast_path_common_images: set[str] = set()
        
        self._load_patterns_from_json(custom_patterns_file)
        self._load_detector_config_from_json()

        strict = os.environ.get("NLP2CMD_STRICT_CONFIG", "").strip().lower() in {"1", "true", "yes"}
        if strict and not self.patterns:
            raise FileNotFoundError(
                "NLP2CMD_STRICT_CONFIG is set but no patterns data files were found. "
                "Set NLP2CMD_PATTERNS_FILE or ensure data/patterns.json is accessible."
            )
    
    def _load_patterns_from_json(self, custom_patterns_file: Optional[str] = None) -> None:
        """Load patterns from external JSON file."""
        base: Dict[str, Dict[str, List[str]]] = {}
        
        # Search for patterns files
        pattern_files = []
        if custom_patterns_file:
            pattern_files.append(Path(custom_patterns_file))
        
        # Add default search paths
        for p in _find_data_files(
            explicit_path=os.environ.get("NLP2CMD_PATTERNS_FILE"),
            default_filename="patterns.json",
        ):
            pattern_files.append(p)
        
        # Load patterns from files
        for pattern_file in pattern_files:
            try:
                with open(pattern_file, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
                
                if not isinstance(payload, dict):
                    continue
                
                # Expected format: {"sql": {"intent": ["keywords"]}, "shell": {...}, ...}
                for domain, intents in payload.items():
                    if domain == "$schema" or not isinstance(intents, dict):
                        continue
                    
                    bucket = base.setdefault(domain, {})
                    if not isinstance(bucket, dict):
                        continue
                    
                    for intent, keywords in intents.items():
                        if not isinstance(intent, str) or not intent.strip() or not isinstance(keywords, list):
                            continue
                        
                        i = intent.strip()
                        clean = [_normalize_polish_text(kw.strip()) for kw in keywords if isinstance(kw, str) and kw.strip()]
                        if not clean:
                            continue
                        
                        prev = bucket.get(i)
                        prev_list = prev if isinstance(prev, list) else []
                        bucket[i] = _dedupe_case_insensitive([*clean, *prev_list])
                
                logger.debug(f"Loaded patterns from {pattern_file}")
                
            except Exception as e:
                logger.warning(f"Failed to load patterns from {pattern_file}: {e}")
                continue
        
        self.patterns = base
    
    def _load_detector_config_from_json(self) -> None:
        """Load detector configuration from JSON files."""
        for p in _find_data_files(
            explicit_path=os.environ.get("NLP2CMD_DETECTOR_CONFIG_FILE"),
            default_filename="detector_config.json",
        ):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
                
                if not isinstance(payload, dict):
                    continue
                
                # Load domain boosters
                boosters = payload.get("domain_boosters")
                if isinstance(boosters, dict):
                    for domain, keywords in boosters.items():
                        if isinstance(domain, str) and isinstance(keywords, list):
                            clean = [_normalize_polish_text(kw.strip()) for kw in keywords if isinstance(kw, str) and kw.strip()]
                            if clean:
                                self.domain_boosters[domain] = clean
                
                # Load priority intents
                priority = payload.get("priority_intents")
                if isinstance(priority, dict):
                    for domain, intents in priority.items():
                        if isinstance(domain, str) and isinstance(intents, list):
                            clean = [_normalize_polish_text(intent.strip()) for intent in intents if isinstance(intent, str) and intent.strip()]
                            if clean:
                                self.priority_intents[domain] = clean
                
                # Load fast path configurations
                fast_path = payload.get("fast_path")
                if isinstance(fast_path, dict):
                    # Browser keywords
                    b = fast_path.get("browser_keywords")
                    if isinstance(b, list):
                        clean = [_normalize_polish_text(kw.strip()) for kw in b if isinstance(kw, str) and kw.strip()]
                        self.fast_path_browser_keywords = _dedupe_case_insensitive(clean)
                    
                    # Search keywords  
                    s = fast_path.get("search_keywords")
                    if isinstance(s, list):
                        clean = [_normalize_polish_text(kw.strip()) for kw in s if isinstance(kw, str) and kw.strip()]
                        self.fast_path_search_keywords = _dedupe_case_insensitive(clean)
                    
                    # Common images
                    imgs = fast_path.get("common_images")
                    if isinstance(imgs, list):
                        for x in imgs:
                            if isinstance(x, str) and x.strip():
                                self.fast_path_common_images.add(x.strip().lower())
                
                logger.debug(f"Loaded detector config from {p}")
                
            except Exception as e:
                logger.warning(f"Failed to load detector config from {p}: {e}")
                continue
    
    def get_domain_patterns(self, domain: str) -> Dict[str, List[str]]:
        """Get all patterns for a domain."""
        return self.patterns.get(domain, {})
    
    def get_intent_patterns(self, domain: str, intent: str) -> List[str]:
        """Get patterns for a specific domain/intent combination."""
        return self.patterns.get(domain, {}).get(intent, [])
    
    def has_domain(self, domain: str) -> bool:
        """Check if patterns exist for a domain."""
        return domain in self.patterns
    
    def has_intent(self, domain: str, intent: str) -> bool:
        """Check if patterns exist for a domain/intent combination."""
        return intent in self.patterns.get(domain, {})
    
    def list_domains(self) -> List[str]:
        """List all available domains."""
        return list(self.patterns.keys())
    
    def list_intents(self, domain: str) -> List[str]:
        """List all available intents for a domain."""
        return list(self.patterns.get(domain, {}).keys())
    
    def add_pattern(self, domain: str, intent: str, keywords: List[str]) -> None:
        """Add patterns for a domain/intent combination."""
        if domain not in self.patterns:
            self.patterns[domain] = {}
        
        clean = [_normalize_polish_text(kw.strip()) for kw in keywords if isinstance(kw, str) and kw.strip()]
        if clean:
            existing = self.patterns[domain].get(intent, [])
            self.patterns[domain][intent] = _dedupe_case_insensitive([*clean, *existing])
    
    def get_domain_boosters(self, domain: str) -> List[str]:
        """Get booster keywords for a domain."""
        return self.domain_boosters.get(domain, [])
    
    def get_priority_intents(self, domain: str) -> List[str]:
        """Get priority intents for a domain."""
        return self.priority_intents.get(domain, [])
