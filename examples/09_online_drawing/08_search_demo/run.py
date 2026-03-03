#!/usr/bin/env python3
"""
Example: Open Source Search Engine

Demonstrates the SearchSkill for internet search without API keys.
Uses DuckDuckGo (primary) and SearXNG (fallback).

Usage:
    python3 run.py "Python best practices"
    python3 run.py "machine learning tutorial" --max-results 5
    python3 run.py --summarize "climate change solutions"
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Setup paths
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from nlp2cmd.skills.search import SearchSkill, SearchConfig


async def search_demo(query: str, max_results: int = 5, summarize: bool = False):
    """Demonstrate search functionality."""
    print(f"🔍 Open Source Search")
    print(f"   Query: {query}")
    print()
    
    config = SearchConfig(
        ddg_max_results=max_results,
        searxng_timeout=15,
    )
    
    async with SearchSkill(config) as skill:
        if summarize:
            print("⏳ Searching and summarizing...")
            result = await skill.search_and_summarize(query, max_results=max_results)
            
            print(f"\n📊 Sources: {', '.join(result['sources'])}")
            print(f"\n📝 Summary:")
            print(f"   {result['summary']}")
            
            print(f"\n📎 Top Results:")
            for i, r in enumerate(result['results'][:5], 1):
                print(f"   {i}. [{r['source']}] {r['title']}")
                print(f"      {r['url']}")
        else:
            print("⏳ Searching...")
            results = await skill.search(query, max_results=max_results)
            
            if not results:
                print("   ❌ No results found")
                return
            
            print(f"\n✅ Found {len(results)} results:")
            print()
            
            for i, r in enumerate(results, 1):
                icon = {"duckduckgo": "🦆", "searxng": "🔍", "brave": "🦁"}.get(r.source, "📄")
                print(f"{icon} {i}. {r.title}")
                print(f"   URL: {r.url}")
                print(f"   {r.snippet[:150]}{'...' if len(r.snippet) > 150 else ''}")
                print()


def main():
    parser = argparse.ArgumentParser(description="Open Source Search Engine Demo")
    parser.add_argument("query", nargs="?", default="Python programming",
                        help="Search query")
    parser.add_argument("--max-results", type=int, default=5,
                        help="Maximum results (default: 5)")
    parser.add_argument("--summarize", action="store_true",
                        help="Summarize results with LLM")
    parser.add_argument("--source", default=None,
                        help="Force source: duckduckgo, searxng, brave, auto")
    
    args = parser.parse_args()
    
    asyncio.run(search_demo(
        query=args.query,
        max_results=args.max_results,
        summarize=args.summarize,
    ))


if __name__ == "__main__":
    main()
