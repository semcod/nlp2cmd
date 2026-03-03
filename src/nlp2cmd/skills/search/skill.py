"""
SearchSkill - High-level interface for search operations.

Integrates SearchEngine with nlp2cmd's skill system for:
- Natural language query understanding
- Context-aware search
- Result summarization via LLM
- Integration with drawing/examples
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from nlp2cmd.skills.search.engine import SearchEngine, SearchResult, SearchConfig


@dataclass
class SearchContext:
    """Context for search operations."""
    query: str
    intent: str = "general"  # general, image, code, news
    language: str = "en"
    max_results: int = 10


class SearchSkill:
    """
    High-level search skill for nlp2cmd.
    
    Wraps SearchEngine with additional capabilities:
    - Query preprocessing
    - Result filtering
    - LLM-powered summarization
    """
    
    def __init__(self, config: Optional[SearchConfig] = None):
        self.config = config or SearchConfig()
        self.engine = SearchEngine(self.config)
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
        source: Optional[str] = None,
    ) -> list[SearchResult]:
        """
        Perform search with preprocessing.
        
        Args:
            query: Search query (natural language)
            max_results: Max results to return
            source: Force specific engine
        
        Returns:
            List of search results
        """
        # Preprocess query
        clean_query = self._preprocess_query(query)
        
        # Perform search
        results = await self.engine.search(
            query=clean_query,
            max_results=max_results,
            source=source,
        )
        
        return results
    
    def _preprocess_query(self, query: str) -> str:
        """Clean and optimize query for search."""
        # Remove common prefixes
        prefixes = [
            "search for", "find", "look up", "wyszukaj", "znajdź",
            "szukaj", "poszukaj", "wyszukaj w internecie",
        ]
        
        query_lower = query.lower().strip()
        for prefix in prefixes:
            if query_lower.startswith(prefix.lower()):
                query = query[len(prefix):].strip()
                break
        
        # Remove punctuation at end
        query = query.rstrip(".!?")
        
        return query
    
    async def search_and_summarize(
        self,
        query: str,
        max_results: int = 5,
    ) -> dict:
        """
        Search and summarize results using LLM.
        
        Returns:
            Dict with 'results', 'summary', and 'sources'
        """
        results = await self.search(query, max_results=max_results)
        
        if not results:
            return {
                "results": [],
                "summary": "No results found.",
                "sources": [],
            }
        
        # Try to summarize with LLM if available
        summary = await self._summarize_results(query, results)
        
        return {
            "results": [
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                    "source": r.source,
                }
                for r in results
            ],
            "summary": summary,
            "sources": list(set(r.source for r in results)),
        }
    
    async def _summarize_results(
        self,
        query: str,
        results: list[SearchResult],
    ) -> str:
        """Summarize search results using LLM."""
        try:
            from nlp2cmd.llm.router import get_router
            
            router = get_router()
            
            # Build context from results
            context = "\n\n".join([
                f"{i+1}. {r.title}\n   {r.snippet}"
                for i, r in enumerate(results[:3])
            ])
            
            prompt = f"""Based on the following search results for "{query}", 
provide a brief 2-3 sentence summary of the key information found:

{context}

Summary:"""
            
            response = await router.route_call(
                prompt=prompt,
                task_category="text",
                timeout=15,
            )
            
            if response and response.text:
                return response.text.strip()
                
        except Exception:
            pass
        
        # Fallback: return simple concatenation
        return " | ".join([r.snippet for r in results[:3] if r.snippet])
    
    async def search_for_drawing_reference(
        self,
        shape_name: str,
    ) -> Optional[SearchResult]:
        """
        Search for drawing reference images/info for a shape.
        
        Useful for finding visual references before drawing.
        """
        query = f"{shape_name} simple drawing diagram outline"
        
        results = await self.search(query, max_results=3)
        
        # Filter for likely good reference sources
        good_sources = ["wikipedia", "wikimedia", "svg", "icon", "clipart"]
        
        for result in results:
            url_lower = result.url.lower()
            if any(s in url_lower for s in good_sources):
                return result
        
        # Return first result if no good match
        return results[0] if results else None
    
    async def close(self):
        """Clean up resources."""
        await self.engine.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False
