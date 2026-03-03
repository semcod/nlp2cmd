# Skills package for nlp2cmd

# Lazy imports to avoid hard dependency on aiohttp for non-search use cases
def __getattr__(name):
    if name in ("SearchSkill", "SearchEngine", "SearchResult", "SearchConfig"):
        from nlp2cmd.skills.search import SearchSkill, SearchEngine, SearchResult, SearchConfig
        _exports = {
            "SearchSkill": SearchSkill,
            "SearchEngine": SearchEngine,
            "SearchResult": SearchResult,
            "SearchConfig": SearchConfig,
        }
        return _exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "SearchSkill",
    "SearchEngine",
    "SearchResult",
    "SearchConfig",
]
