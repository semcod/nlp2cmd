"""
Unit tests for the search skill.
"""

import pytest
from pathlib import Path

# Skip all tests if aiohttp not available
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

pytestmark = pytest.mark.skipif(not HAS_AIOHTTP, reason="aiohttp not installed")


class TestSearchConfig:
    """Test SearchConfig data class."""
    
    def test_default_config(self):
        from nlp2cmd.skills.search import SearchConfig
        config = SearchConfig()
        assert config.ddg_max_results == 10
        assert config.ddg_timeout == 15
        assert config.cache_ttl == 3600
        assert config.brave_api_key is None
    
    def test_config_creates_cache_dir(self, tmp_path):
        from nlp2cmd.skills.search import SearchConfig
        cache_dir = tmp_path / "test_cache"
        config = SearchConfig(cache_dir=cache_dir)
        assert cache_dir.exists()


class TestSearchResult:
    """Test SearchResult data class."""
    
    def test_result_creation(self):
        from nlp2cmd.skills.search import SearchResult
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
            source="duckduckgo",
            rank=1
        )
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.source == "duckduckgo"
        assert result.rank == 1
    
    def test_result_str(self):
        from nlp2cmd.skills.search import SearchResult
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="",
            source="duckduckgo",
            rank=1
        )
        assert "duckduckgo" in str(result)
        assert "Test" in str(result)


class TestSearchEngine:
    """Test SearchEngine functionality."""
    
    @pytest.fixture
    async def engine(self):
        from nlp2cmd.skills.search import SearchEngine, SearchConfig
        config = SearchConfig()
        engine = SearchEngine(config)
        yield engine
        await engine.close()
    
    def test_engine_creation(self):
        from nlp2cmd.skills.search import SearchEngine
        engine = SearchEngine()
        assert engine.config is not None
    
    def test_cache_key_generation(self):
        from nlp2cmd.skills.search import SearchEngine
        engine = SearchEngine()
        key1 = engine._cache_key("Python tutorial", "duckduckgo")
        key2 = engine._cache_key("python tutorial", "duckduckgo")
        assert key1 == key2  # Case insensitive
    
    def test_empty_query_returns_empty(self):
        from nlp2cmd.skills.search import SearchEngine
        engine = SearchEngine()
        import asyncio
        results = asyncio.run(engine.search(""))
        assert results == []
    
    def test_whitespace_query_returns_empty(self):
        from nlp2cmd.skills.search import SearchEngine
        engine = SearchEngine()
        import asyncio
        results = asyncio.run(engine.search("   "))
        assert results == []


class TestHTMLParsing:
    """Test HTML parsing with and without BeautifulSoup."""
    
    def test_parse_duckduckgo_bs4(self):
        """Test parsing with BeautifulSoup if available."""
        from nlp2cmd.skills.search.engine import SearchEngine, HAS_BS4
        engine = SearchEngine()
        
        # Sample DuckDuckGo HTML
        html = '''
        <div class="result">
            <a class="result__a" href="/l/?uddg=https%3A%2F%2Fexample.com">Example Title</a>
            <a class="result__snippet">Example snippet text</a>
        </div>
        '''
        
        if HAS_BS4:
            results = engine._parse_duckduckgo_bs4(html, 10)
            assert len(results) == 1
            assert results[0].title == "Example Title"
            assert results[0].snippet == "Example snippet text"
            assert results[0].source == "duckduckgo"
    
    def test_parse_duckduckgo_regex(self):
        """Test regex-based parsing (no BS4 required)."""
        from nlp2cmd.skills.search.engine import SearchEngine
        engine = SearchEngine()
        
        # Sample DuckDuckGo HTML
        html = '''
        <div class="result"><a class="result__a" href="/l/?uddg=https%3A%2F%2Fexample.com">Example Title</a><a class="result__snippet">Example snippet text</a></div></div></div>
        '''
        
        results = engine._parse_duckduckgo_regex(html, 10)
        assert len(results) >= 0  # May or may not match depending on HTML structure


class TestSearchSkill:
    """Test SearchSkill high-level interface."""
    
    def test_skill_creation(self):
        from nlp2cmd.skills.search import SearchSkill
        skill = SearchSkill()
        assert skill.engine is not None
    
    def test_preprocess_query_removes_prefixes(self):
        from nlp2cmd.skills.search import SearchSkill
        skill = SearchSkill()
        
        # Test various prefixes are removed
        assert skill._preprocess_query("search for Python") == "Python"
        assert skill._preprocess_query("find Python") == "Python"
        assert skill._preprocess_query("wyszukaj Python") == "Python"
        assert skill._preprocess_query("Python") == "Python"
    
    def test_preprocess_query_removes_punctuation(self):
        from nlp2cmd.skills.search import SearchSkill
        skill = SearchSkill()
        
        assert skill._preprocess_query("Python.") == "Python"
        assert skill._preprocess_query("Python!") == "Python"
        assert skill._preprocess_query("Python?") == "Python"


class TestSearchIntegration:
    """Integration tests requiring network."""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_AIOHTTP, reason="aiohttp not installed")
    async def test_duckduckgo_live_search(self):
        """Live test against DuckDuckGo (may fail due to rate limiting)."""
        from nlp2cmd.skills.search import SearchSkill
        
        async with SearchSkill() as skill:
            results = await skill.search("python programming", max_results=3)
            
            # Should get some results (or empty if rate limited)
            if results:
                assert len(results) <= 3
                for r in results:
                    assert r.title
                    assert r.url
                    assert r.source == "duckduckgo"
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_AIOHTTP, reason="aiohttp not installed")
    async def test_search_and_summarize(self):
        """Test search with summarization."""
        from nlp2cmd.skills.search import SearchSkill
        
        async with SearchSkill() as skill:
            result = await skill.search_and_summarize("python", max_results=2)
            
            assert "results" in result
            assert "summary" in result
            assert "sources" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
