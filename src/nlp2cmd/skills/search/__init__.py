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

# Lazy imports — aiohttp and bs4 are optional dependencies.
# Eagerly importing engine.py would cause ModuleNotFoundError
# for every nlp2cmd import if aiohttp/bs4 aren't installed.

_EXPORTS = {
    "SearchEngine": "nlp2cmd.skills.search.engine",
    "SearchResult": "nlp2cmd.skills.search.engine",
    "SearchConfig": "nlp2cmd.skills.search.engine",
    "SearchSkill": "nlp2cmd.skills.search.skill",
}


def __getattr__(name: str):
    if name in _EXPORTS:
        import importlib
        module = importlib.import_module(_EXPORTS[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "SearchEngine",
    "SearchResult", 
    "SearchConfig",
    "SearchSkill",
]
