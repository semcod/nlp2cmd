"""Vector database planner for semantic drawing pattern search."""

from __future__ import annotations
import logging
import re
from typing import Any

from .base import CanvasPlannerBase, CanvasPlanResult

log = logging.getLogger("nlp2cmd.canvas_planner.vector")

# Import check for vector store
try:
    from nlp2cmd.automation.vector_store import get_vector_store
    _VECTOR_STORE_AVAILABLE = True
except ImportError:
    _VECTOR_STORE_AVAILABLE = False

    def get_vector_store(*a, **kw):  # type: ignore
        return None


class VectorDBPlanner(CanvasPlannerBase):
    """Searches vector database for semantically similar drawing patterns."""
    
    def is_available(self) -> bool:
        """Check if vector store is available."""
        return _VECTOR_STORE_AVAILABLE
    
    def plan(self, query: str, text: str, canvas_url: str = "https://jspaint.app") -> CanvasPlanResult | None:
        """Search vector database for drawing pattern."""
        if not _VECTOR_STORE_AVAILABLE:
            log.debug("Vector store not available, skipping semantic search")
            return None
        
        try:
            store = get_vector_store()
            if not store or not store.is_available():
                log.debug("Vector store client not initialized")
                return None
            
            # Extract object description from query
            search_query = self._extract_search_query(text)
            
            log.info("[VectorDBPlanner] Searching for: %s", search_query)
            
            best_pattern = self._find_best_pattern(store, search_query)
            
            if not best_pattern:
                log.debug("No matching patterns in vector DB")
                return None
            
            # Build plan from pattern
            steps = self._build_plan_from_pattern(best_pattern, canvas_url)
            
            # Determine confidence from search quality
            confidence = self._calculate_confidence(store, search_query, best_pattern)
            
            return CanvasPlanResult(
                steps=steps,
                confidence=confidence,
                source="vector_db",
                estimated_time_ms=len(steps) * 400,
            )
            
        except Exception as e:
            log.warning("Vector DB search failed: %s", e)
            return None
    
    def _extract_search_query(self, text: str) -> str:
        """Extract object description from query."""
        obj_match = re.search(
            r"(?:narysuj|rysuj|namaluj|maluj|naszkicuj|draw|paint|sketch)\s+(.+?)(?:\s+na\s+|\s+w\s+|\s*$)",
            text,
        )
        search_query = obj_match.group(1).strip() if obj_match else text
        search_query = re.sub(r"\s*https?://\S+", "", search_query).strip()
        return search_query
    
    def _find_best_pattern(self, store, search_query: str) -> Any | None:
        """Find best matching pattern in vector DB."""
        query_lower = search_query.lower()
        
        # Simple stemming for Polish
        if query_lower.endswith(("a", "ek", "kiem", "ka")):
            base_query = re.sub(r'(a|ek|kiem|ka)$', '', query_lower)
        else:
            base_query = query_lower
        
        # Try exact/fuzzy match on tags first
        all_patterns = store.list_patterns()
        for p_name in all_patterns:
            p = store.get_pattern(p_name)
            if p and (base_query in p.tags or query_lower in p.tags or base_query == p.name):
                log.info("[VectorDBPlanner] Exact tag match: %s", p.name)
                return p
        
        # Fallback to semantic search
        results = store.search(search_query, n_results=3, min_confidence=0.0)
        if results:
            best_pattern, confidence = results[0]
            log.info("[VectorDBPlanner] Semantic match: %s (confidence: %.2f)", 
                     best_pattern.name, confidence)
            return best_pattern
        
        return None
    
    def _calculate_confidence(self, store, search_query: str, pattern: Any) -> float:
        """Calculate confidence score for pattern match."""
        # Re-run search to get confidence
        results = store.search(search_query, n_results=1, min_confidence=0.0)
        if results:
            return results[0][1]
        return 0.80  # Default confidence for tag matches
    
    def _build_plan_from_pattern(self, pattern: Any, canvas_url: str) -> list[dict[str, Any]]:
        """Build action steps from pattern."""
        steps: list[dict[str, Any]] = [
            {"action": "navigate", "params": {"url": canvas_url}, "description": f"Open {canvas_url}"},
            {"action": "wait_for_canvas", "params": {}, "description": "Wait for canvas"},
            {"action": "get_canvas_center", "params": {}, "description": "Get canvas center"},
        ]
        
        for step_data in pattern.steps:
            action = step_data.get("action", "")
            params = step_data.get("params", {})
            desc = step_data.get("description", action)
            if action:
                steps.append({"action": action, "params": params, "description": desc})
        
        return steps
