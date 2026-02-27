"""
Base Explorer - Abstract base class for all exploration types.

Provides common interface for exploring:
- Websites (WebExplorer)
- File systems (DiskExplorer)
- Services/APIs (ServiceExplorer)
- Data structures (DataTreeExplorer)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, Optional, TypeVar


T = TypeVar('T')


@dataclass
class ExplorationResult(Generic[T]):
    """Result of exploration in any space."""
    success: bool
    target: Optional[T] = None
    path: list[str] = field(default_factory=list)  # Path to target
    candidates: list[T] = field(default_factory=list)  # All found candidates
    metadata: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class ExplorationContext:
    """Context for exploration - what we're looking for."""
    intent: str  # e.g., "contact", "product", "file", "endpoint"
    search_term: Optional[str] = None
    filters: dict[str, Any] = field(default_factory=dict)
    max_depth: int = 3
    max_results: int = 10


class BaseExplorer(ABC):
    """
    Abstract base class for all explorers.
    
    Implementations must provide:
    - explore(root, context) -> ExplorationResult
    - supports(space_type) -> bool
    """
    
    def __init__(
        self,
        max_depth: int = 3,
        max_results: int = 10,
        timeout_seconds: float = 30.0,
    ):
        self.max_depth = max_depth
        self.max_results = max_results
        self.timeout_seconds = timeout_seconds
        self._visited: set[str] = set()
    
    @abstractmethod
    def explore(
        self,
        root: Any,
        context: ExplorationContext,
    ) -> ExplorationResult:
        """
        Explore from root to find targets matching context.
        
        Args:
            root: Starting point (URL, path, service URL, data root)
            context: What to look for
            
        Returns:
            ExplorationResult with findings
        """
        pass
    
    @abstractmethod
    def supports(self, space_type: str) -> bool:
        """Check if this explorer supports given space type."""
        pass
    
    def _should_stop(self, current_depth: int, found_count: int) -> bool:
        """Check if exploration should stop."""
        if current_depth >= self.max_depth:
            return True
        if found_count >= self.max_results:
            return True
        return False
    
    def _score_relevance(self, item: Any, context: ExplorationContext) -> float:
        """
        Score how relevant an item is to the search context.
        Override in subclasses for domain-specific scoring.
        """
        score = 0.0
        
        # Basic keyword matching
        if context.search_term:
            search_lower = context.search_term.lower()
            item_str = str(item).lower()
            
            if search_lower in item_str:
                score += 1.0
            
            # Partial word matches
            search_words = search_lower.split()
            for word in search_words:
                if len(word) > 2 and word in item_str:
                    score += 0.3
        
        # Intent-specific scoring
        intent_keywords = self._get_intent_keywords(context.intent)
        item_str = str(item).lower()
        for kw in intent_keywords:
            if kw in item_str:
                score += 0.5
        
        return score
    
    def _get_intent_keywords(self, intent: str) -> list[str]:
        """Get keywords associated with an intent."""
        keywords = {
            "contact": ["contact", "kontakt", "form", "formularz", "email"],
            "product": ["product", "produkt", "price", "cena", "buy", "shop"],
            "article": ["article", "artykul", "blog", "news", "post"],
            "docs": ["docs", "documentation", "api", "manual", "guide"],
            "file": ["file", "document", "pdf", "doc", "config"],
            "endpoint": ["api", "endpoint", "service", "rest", "graphql"],
            "data": ["data", "table", "record", "field", "schema"],
        }
        return keywords.get(intent, [])
    
    def reset(self) -> None:
        """Reset exploration state."""
        self._visited = set()


class ExplorerRegistry:
    """Registry of available explorers."""
    
    _explorers: dict[str, BaseExplorer] = {}
    
    @classmethod
    def register(cls, space_type: str, explorer: BaseExplorer) -> None:
        """Register an explorer for a space type."""
        cls._explorers[space_type] = explorer
    
    @classmethod
    def get(cls, space_type: str) -> Optional[BaseExplorer]:
        """Get explorer for space type."""
        return cls._explorers.get(space_type)
    
    @classmethod
    def list_supported(cls) -> list[str]:
        """List all supported space types."""
        return list(cls._explorers.keys())
    
    @classmethod
    def auto_detect(cls, root: Any) -> Optional[str]:
        """Auto-detect space type from root."""
        root_str = str(root)
        
        # URL -> web
        if root_str.startswith(("http://", "https://")):
            return "web"
        
        # Path -> disk
        if root_str.startswith(("/", ".", "~", "C:", "D:")):
            return "disk"
        
        # API endpoint -> service
        if any(x in root_str for x in ["/api/", "/v1/", "/graphql"]):
            return "service"
        
        # Dictionary/list -> data
        if isinstance(root, (dict, list)):
            return "data"
        
        return None


def explore(
    root: Any,
    intent: str,
    search_term: Optional[str] = None,
    space_type: Optional[str] = None,
    **kwargs,
) -> ExplorationResult:
    """
    Universal exploration function.
    
    Usage:
        # Explore website for contact form
        result = explore("https://example.com", "contact")
        
        # Explore disk for config files
        result = explore("/etc", "file", search_term="config")
        
        # Explore API
        result = explore("https://api.example.com", "endpoint")
    """
    # Auto-detect space type if not provided
    if space_type is None:
        space_type = ExplorerRegistry.auto_detect(root)
    
    if space_type is None:
        return ExplorationResult(
            success=False,
            error=f"Could not auto-detect space type for: {root}",
        )
    
    # Get appropriate explorer
    explorer = ExplorerRegistry.get(space_type)
    if explorer is None:
        return ExplorationResult(
            success=False,
            error=f"No explorer registered for space type: {space_type}",
        )
    
    # Create context and explore
    context = ExplorationContext(
        intent=intent,
        search_term=search_term,
        **kwargs,
    )
    
    return explorer.explore(root, context)
