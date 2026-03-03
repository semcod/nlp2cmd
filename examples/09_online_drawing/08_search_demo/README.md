# 08 — Search Demo: Open Source Search Engine

Internet search using privacy-friendly open source search engines — no API keys needed!

## How It Works

**SearchEngine** aggregates multiple open source search providers:

1. **DuckDuckGo** (primary) — HTML scraping, no API key, privacy-focused
2. **SearXNG** (fallback) — Self-hostable metasearch, no API key  
3. **Brave Search** (optional) — Requires API key, but fast

All searches are cached locally for 1 hour to avoid rate limits.

## Usage

```bash
# Basic search
python3 run.py "Python best practices"

# More results
python3 run.py "machine learning tutorial" --max-results 10

# Summarize with LLM
python3 run.py --summarize "climate change solutions"

# Using run.sh
./run.sh 08_search_demo "Python Playwright"
./run.sh 08_search_demo "API documentation" --summarize
```

## Output Example

```
🔍 Open Source Search
   Query: Python Playwright tutorial

⏳ Searching...

✅ Found 5 results:

🦆 1. Playwright Python Tutorial | Microsoft
   URL: https://playwright.dev/python/docs/intro
   Playwright is a framework for Web Testing and Automation...

🦆 2. Getting started with Playwright for Python
   URL: https://github.com/microsoft/playwright-python
   Python version of the Playwright testing library...

🔍 3. Playwright Tutorial: A Complete Guide
   URL: https://www.browserstack.com/guide/playwright-python-tutorial
   Learn how to use Playwright for Python...
```

## Architecture

```
SearchSkill
├── SearchEngine
│   ├── DuckDuckGo (HTML scraping)
│   ├── SearXNG (API)
│   └── Brave (optional API)
├── Query preprocessing
├── Result caching (memory + disk)
└── LLM summarization (optional)
```

## Privacy & Open Source

| Feature | Status |
|---------|--------|
| No tracking | ✅ |
| No API key required | ✅ (DuckDuckGo/SearXNG) |
| Open source | ✅ |
| Local caching | ✅ |
| LLM-independent | ✅ (summarization optional) |

## Requirements

```bash
pip install aiohttp beautifulsoup4
```

## Comparison with Commercial Search

| Provider | API Key | Rate Limit | Privacy |
|----------|---------|------------|---------|
| DuckDuckGo | No | ~100/day | ✅ High |
| SearXNG | No | Varies | ✅ High |
| Brave | Yes | 2000/month | ✅ High |
| Google | Yes | Paid | ❌ Low |
| Bing | Yes | Paid | ❌ Low |
