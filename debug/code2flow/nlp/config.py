"""NLP Configuration - YAML-driven settings for NLP pipeline."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path
import yaml


@dataclass
class NormalizationConfig:
    """Configuration for query normalization."""
    # 1a: Lowercase conversion
    lowercase: bool = True
    # 1b: Punctuation removal  
    remove_punctuation: bool = True
    # 1c: Whitespace normalization
    normalize_whitespace: bool = True
    # 1d: Unicode normalization (NFKC)
    unicode_normalize: bool = True
    # 1e: Stopword removal
    remove_stopwords: bool = False
    # Language-specific stopwords
    stopwords: Dict[str, List[str]] = field(default_factory=lambda: {
        "en": ["the", "a", "an", "is", "are", "was", "were"],
        "pl": ["w", "z", "do", "na", "jest", "są"],
    })


@dataclass
class IntentMatchingConfig:
    """Configuration for intent matching."""
    # 2a: Fuzzy matching threshold (0.0-1.0)
    fuzzy_threshold: float = 0.8
    # 2b: Semantic similarity threshold
    semantic_threshold: float = 0.85
    # 2c: Keyword matching weight
    keyword_weight: float = 0.6
    # 2d: Context window size
    context_window: int = 3
    # 2e: Multi-intent resolution strategy
    multi_intent_strategy: str = "best_match"  # best_match, combine, sequential
    # Fuzzy matching algorithm
    fuzzy_algorithm: str = "token_sort_ratio"  # ratio, partial_ratio, token_sort_ratio


@dataclass
class EntityResolutionConfig:
    """Configuration for entity resolution."""
    # 3a: Entity types to extract
    entity_types: List[str] = field(default_factory=lambda: [
        "function", "class", "module", "variable", "file"
    ])
    # 3b: Name matching threshold
    name_match_threshold: float = 0.9
    # 3c: Context-aware disambiguation
    context_disambiguation: bool = True
    # 3d: Hierarchical resolution (class.method -> method)
    hierarchical_resolution: bool = True
    # 3e: Alias resolution (short names -> qualified names)
    alias_resolution: bool = True


@dataclass
class MultilingualConfig:
    """Configuration for multilingual processing."""
    # Supported languages
    languages: List[str] = field(default_factory=lambda: ["en", "pl"])
    # Default language
    default_language: str = "en"
    # Language detection confidence threshold
    lang_detect_threshold: float = 0.7
    # Cross-language matching
    cross_language_matching: bool = True


@dataclass
class NLPConfig:
    """Main NLP pipeline configuration."""
    # Sub-configurations
    normalization: NormalizationConfig = field(default_factory=NormalizationConfig)
    intent_matching: IntentMatchingConfig = field(default_factory=IntentMatchingConfig)
    entity_resolution: EntityResolutionConfig = field(default_factory=EntityResolutionConfig)
    multilingual: MultilingualConfig = field(default_factory=MultilingualConfig)
    
    # Pipeline stages
    enable_normalization: bool = True
    enable_intent_matching: bool = True
    enable_entity_resolution: bool = True
    
    # Logging
    verbose: bool = False
    
    @classmethod
    def from_yaml(cls, path: str) -> "NLPConfig":
        """Load configuration from YAML file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return cls(
            normalization=NormalizationConfig(**data.get('normalization', {})),
            intent_matching=IntentMatchingConfig(**data.get('intent_matching', {})),
            entity_resolution=EntityResolutionConfig(**data.get('entity_resolution', {})),
            multilingual=MultilingualConfig(**data.get('multilingual', {})),
            enable_normalization=data.get('enable_normalization', True),
            enable_intent_matching=data.get('enable_intent_matching', True),
            enable_entity_resolution=data.get('enable_entity_resolution', True),
            verbose=data.get('verbose', False),
        )
    
    def to_yaml(self, path: str) -> None:
        """Save configuration to YAML file."""
        data = {
            'normalization': self.normalization.__dict__,
            'intent_matching': self.intent_matching.__dict__,
            'entity_resolution': self.entity_resolution.__dict__,
            'multilingual': self.multilingual.__dict__,
            'enable_normalization': self.enable_normalization,
            'enable_intent_matching': self.enable_intent_matching,
            'enable_entity_resolution': self.enable_entity_resolution,
            'verbose': self.verbose,
        }
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


# Predefined configurations
FAST_NLP_CONFIG = NLPConfig(
    normalization=NormalizationConfig(
        lowercase=True,
        remove_punctuation=True,
        normalize_whitespace=True,
        unicode_normalize=True,
        remove_stopwords=False,
    ),
    intent_matching=IntentMatchingConfig(
        fuzzy_threshold=0.7,  # Lower threshold for speed
        semantic_threshold=0.8,
        keyword_weight=0.8,  # Higher weight on keywords
        fuzzy_algorithm="ratio",  # Faster algorithm
    ),
    entity_resolution=EntityResolutionConfig(
        entity_types=["function", "class"],
        name_match_threshold=0.85,
        context_disambiguation=False,  # Skip for speed
    ),
    verbose=False,
)

PRECISE_NLP_CONFIG = NLPConfig(
    normalization=NormalizationConfig(
        lowercase=True,
        remove_punctuation=True,
        normalize_whitespace=True,
        unicode_normalize=True,
        remove_stopwords=True,
    ),
    intent_matching=IntentMatchingConfig(
        fuzzy_threshold=0.9,
        semantic_threshold=0.95,
        keyword_weight=0.4,
        context_window=5,
        fuzzy_algorithm="token_sort_ratio",
    ),
    entity_resolution=EntityResolutionConfig(
        entity_types=["function", "class", "module", "variable", "file"],
        name_match_threshold=0.95,
        context_disambiguation=True,
        hierarchical_resolution=True,
        alias_resolution=True,
    ),
    verbose=True,
)
