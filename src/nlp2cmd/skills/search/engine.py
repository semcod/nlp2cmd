"""
Open Source Search Engine implementation.

Supports:
- DuckDuckGo (HTML scraping, no API key needed)
- SearXNG (self-hosted or public instances, no API key)
- Brave Search (requires API key, optional)
"""

from __future__ import annotations

import asyncio
import json
import random
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote, urljoin, urlparse

import aiohttp

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    BeautifulSoup = None


@dataclass
class SearchResult:
    """Single search result."""
    title: str
    url: str
    snippet: str
    source: str = "unknown"  # duckduckgo, searxng, brave
    rank: int = 0
    timestamp: Optional[str] = None
    
    def __str__(self) -> str:
        return f"[{self.source}] {self.title} ({self.rank})"


@dataclass 
class SearchConfig:
    """Configuration for search engine."""
    # DuckDuckGo settings
    ddg_max_results: int = 10
    ddg_timeout: int = 15
    ddg_safe_search: str = "moderate"  # on, moderate, off
    
    # SearXNG settings
    searxng_instances: list[str] = field(default_factory=lambda: [
        "https://search.sapti.org",
        "https://search.leptons.xyz",
        "https://search.jabux.org",
    ])
    searxng_timeout: int = 20
    
    # Brave Search settings (optional, requires API key)
    brave_api_key: Optional[str] = None
    brave_timeout: int = 10
    
    # General settings
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".nlp2cmd" / "search_cache")
    cache_ttl: int = 3600  # seconds
    user_agent: str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    def __post_init__(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)


class SearchEngine:
    """
    Open source search engine aggregator.
    
    Primary: DuckDuckGo (HTML scraping, no API key)
    Fallback: SearXNG (public instances)
    Optional: Brave Search (if API key provided)
    """
    
    def __init__(self, config: Optional[SearchConfig] = None):
        self.config = config or SearchConfig()
        self._cache: dict[str, tuple[list[SearchResult], float]] = {}
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            headers = {
                "User-Agent": self.config.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session
    
    def _cache_key(self, query: str, source: str) -> str:
        """Generate cache key for query."""
        return f"{source}:{query.lower().strip()}"
    
    def _check_cache(self, key: str) -> Optional[list[SearchResult]]:
        """Check if results are in cache and not expired."""
        if key in self._cache:
            results, timestamp = self._cache[key]
            if time.time() - timestamp < self.config.cache_ttl:
                return results
            del self._cache[key]
        return None
    
    def _save_cache(self, key: str, results: list[SearchResult]):
        """Save results to cache."""
        self._cache[key] = (results, time.time())
        # Also save to disk cache
        cache_file = self.config.cache_dir / f"{hash(key)}.json"
        try:
            data = [
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                    "source": r.source,
                    "rank": r.rank,
                    "timestamp": r.timestamp,
                }
                for r in results
            ]
            cache_file.write_text(json.dumps(data, indent=2))
        except Exception:
            pass
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
        source: Optional[str] = None,
    ) -> list[SearchResult]:
        """
        Search using available engines.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            source: Force specific source ('duckduckgo', 'searxng', 'brave', 'auto')
        
        Returns:
            List of SearchResult objects
        """
        if not query or not query.strip():
            return []
        
        query = query.strip()
        
        # Check memory cache
        cache_key = self._cache_key(query, source or "auto")
        cached = self._check_cache(cache_key)
        if cached:
            return cached[:max_results]
        
        results: list[SearchResult] = []
        
        # Try specific source or auto-fallback
        if source == "duckduckgo" or source is None:
            results = await self._search_duckduckgo(query, max_results)
        
        if not results and (source == "searxng" or source is None):
            results = await self._search_searxng(query, max_results)
        
        if not results and (source == "brave" or source is None):
            results = await self._search_brave(query, max_results)
        
        # Save to cache
        if results:
            self._save_cache(cache_key, results)
        
        return results[:max_results]
    
    async def _search_duckduckgo(self, query: str, max_results: int) -> list[SearchResult]:
        """Search using DuckDuckGo HTML scraping."""
        try:
            session = await self._get_session()
            
            # DuckDuckGo HTML interface
            encoded_query = quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=self.config.ddg_timeout),
                allow_redirects=True,
            ) as response:
                if response.status != 200:
                    return []
                
                html = await response.text()
                return self._parse_duckduckgo_html(html, max_results)
                
        except Exception as e:
            print(f"   ⚠ DuckDuckGo search failed: {e}")
            return []
    
    def _parse_duckduckgo_html(self, html: str, max_results: int) -> list[SearchResult]:
        """Parse DuckDuckGo HTML results."""
        if HAS_BS4:
            return self._parse_duckduckgo_bs4(html, max_results)
        else:
            return self._parse_duckduckgo_regex(html, max_results)
    
    def _parse_duckduckgo_bs4(self, html: str, max_results: int) -> list[SearchResult]:
        """Parse DuckDuckGo HTML using BeautifulSoup."""
        results = []
        soup = BeautifulSoup(html, "html.parser")
        
        # DuckDuckGo uses .result class for search results
        result_divs = soup.find_all("div", class_="result")
        
        for idx, div in enumerate(result_divs[:max_results], 1):
            try:
                # Title and link
                title_link = div.find("a", class_="result__a")
                if not title_link:
                    continue
                
                title = title_link.get_text(strip=True)
                url = title_link.get("href", "")
                
                # Snippet
                snippet_div = div.find("a", class_="result__snippet")
                snippet = snippet_div.get_text(strip=True) if snippet_div else ""
                
                # Clean URL (DuckDuckGo uses redirects)
                if url.startswith("/l/?"):
                    # Extract actual URL from redirect
                    match = re.search(r'uddg=([^&]+)', url)
                    if match:
                        from urllib.parse import unquote
                        url = unquote(match.group(1))
                
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source="duckduckgo",
                    rank=idx,
                    timestamp=None,
                ))
                
            except Exception:
                continue
        
        return results
    
    def _parse_duckduckgo_regex(self, html: str, max_results: int) -> list[SearchResult]:
        """Parse DuckDuckGo HTML using regex fallback (no bs4 required)."""
        results = []
        
        # Find result blocks
        # DuckDuckGo HTML structure: <div class="result">...</div>
        result_blocks = re.findall(
            r'<div class="result[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>',
            html,
            re.DOTALL | re.IGNORECASE
        )
        
        if not result_blocks:
            # Try alternative pattern
            result_blocks = re.findall(
                r'<div class="web-result[^"]*"[^>]*>(.*?)</div>\s*</div>',
                html,
                re.DOTALL | re.IGNORECASE
            )
        
        for idx, block in enumerate(result_blocks[:max_results], 1):
            try:
                # Extract title and URL
                title_match = re.search(
                    r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
                    block,
                    re.DOTALL | re.IGNORECASE
                )
                if not title_match:
                    continue
                
                url = title_match.group(1)
                title = re.sub(r'<[^>]+>', '', title_match.group(2)).strip()
                
                # Extract snippet
                snippet_match = re.search(
                    r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
                    block,
                    re.DOTALL | re.IGNORECASE
                )
                snippet = ""
                if snippet_match:
                    snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()
                
                # Clean URL (DuckDuckGo uses redirects)
                if url.startswith("/l/?"):
                    match = re.search(r'uddg=([^&]+)', url)
                    if match:
                        from urllib.parse import unquote
                        url = unquote(match.group(1))
                
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source="duckduckgo",
                    rank=idx,
                    timestamp=None,
                ))
                
            except Exception:
                continue
        
        return results
    
    async def _search_searxng(self, query: str, max_results: int) -> list[SearchResult]:
        """Search using SearXNG public instances."""
        # Try multiple instances in random order
        instances = self.config.searxng_instances.copy()
        random.shuffle(instances)
        
        for instance in instances:
            try:
                results = await self._search_single_searxng(instance, query, max_results)
                if results:
                    return results
            except Exception:
                continue
        
        return []
    
    async def _search_single_searxng(
        self,
        instance: str,
        query: str,
        max_results: int,
    ) -> list[SearchResult]:
        """Search using a single SearXNG instance."""
        try:
            session = await self._get_session()
            
            # SearXNG API endpoint
            encoded_query = quote(query)
            url = f"{instance.rstrip('/')}/search?q={encoded_query}&format=json&categories=general"
            
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=self.config.searxng_timeout),
            ) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                return self._parse_searxng_json(data, max_results, instance)
                
        except Exception:
            return []
    
    def _parse_searxng_json(
        self,
        data: dict,
        max_results: int,
        instance: str,
    ) -> list[SearchResult]:
        """Parse SearXNG JSON results."""
        results = []
        
        for idx, item in enumerate(data.get("results", [])[:max_results], 1):
            try:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    source=f"searxng",
                    rank=idx,
                    timestamp=item.get("publishedDate"),
                ))
            except Exception:
                continue
        
        return results
    
    async def _search_brave(self, query: str, max_results: int) -> list[SearchResult]:
        """Search using Brave Search API (requires API key)."""
        if not self.config.brave_api_key:
            return []
        
        try:
            session = await self._get_session()
            
            url = "https://api.search.brave.com/api/web/search"
            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": self.config.brave_api_key,
            }
            params = {
                "q": query,
                "count": min(max_results, 20),
            }
            
            async with session.get(
                url,
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.config.brave_timeout),
            ) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                return self._parse_brave_json(data, max_results)
                
        except Exception:
            return []
    
    def _parse_brave_json(self, data: dict, max_results: int) -> list[SearchResult]:
        """Parse Brave Search API JSON results."""
        results = []
        
        web_results = data.get("web", {}).get("results", [])
        
        for idx, item in enumerate(web_results[:max_results], 1):
            try:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    source="brave",
                    rank=idx,
                    timestamp=None,
                ))
            except Exception:
                continue
        
        return results
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False
