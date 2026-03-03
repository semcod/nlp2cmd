"""
Open Source Search Engine for nlp2cmd.

Provides internet search capabilities using open source and privacy-friendly
search engines: DuckDuckGo (primary), SearXNG (self-hosted fallback), and
Brave Search (optional with API key).

Usage:
    from nlp2cmd.skills.search import SearchSkill, SearchResult
    
    skill = SearchSkill()
    results = await skill.search("Python Playwright tutorial")
    
    for r in results:
        print(f"{r.title}: {r.url}")
        print(f"  {r.snippet}")
"""

from nlp2cmd.skills.search.engine import SearchEngine, SearchResult, SearchConfig
from nlp2cmd.skills.search.skill import SearchSkill

__all__ = [
    "SearchEngine",
    "SearchResult", 
    "SearchConfig",
    "SearchSkill",
]
