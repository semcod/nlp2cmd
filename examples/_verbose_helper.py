"""
Shared verbose/debug helper for NLP2CMD examples.

When --verbose is passed, enables:
  1. NLP2CMD_DEBUG=1 — turns on internal module debug logs (router, adapters, etc.)
  2. Page schema inspection — dumps DOM structure, interactive elements, canvases
  3. Decision logging — shows selector matching, color picker detection, tool selection

Usage in example scripts:
    from _verbose_helper import init_verbose, vlog, dump_page_schema, dump_selectors

    args = parser.parse_args()
    init_verbose(args.verbose)
    ...
    await dump_page_schema(page)
    await dump_selectors(page, {"canvas": "canvas", "run": "#run-btn"})
"""

from __future__ import annotations

import os
import sys
from typing import Any
from urllib.parse import urlparse

from _verbose_schema import PAGE_SCHEMA_EVAL_JS, log_schema_summary

_VERBOSE = False


def init_verbose(enabled: bool) -> None:
    """Initialize verbose mode. Call early, before importing nlp2cmd modules."""
    global _VERBOSE
    _VERBOSE = enabled
    if enabled:
        os.environ["NLP2CMD_DEBUG"] = "1"
        os.environ["NLP2CMD_ROUTER_VERBOSE"] = "1"
        vlog("Verbose mode ON — NLP2CMD_DEBUG=1, NLP2CMD_ROUTER_VERBOSE=1")


def vlog(msg: str, indent: int = 0) -> None:
    """Print a verbose log message (only when --verbose is active)."""
    if not _VERBOSE:
        return
    prefix = "  " * indent
    print(f"[VERBOSE] {prefix}{msg}", flush=True)


async def dump_page_schema(page, max_depth: int = 3) -> dict[str, Any]:
    """
    Inspect the page DOM and print a schema summary.
    Returns a dict with page structure info.
    """
    if not _VERBOSE:
        return {}

    vlog("─── Page Schema Inspection ───")

    info: dict[str, Any] = {}

    # Basic page info
    title = await page.title()
    url = page.url
    vlog(f"URL:   {url}")
    vlog(f"Title: {title}")
    info["url"] = url
    info["title"] = title

    # Viewport
    vp = page.viewport_size
    if vp:
        vlog(f"Viewport: {vp['width']}×{vp['height']}")
        info["viewport"] = vp

    schema = await page.evaluate(PAGE_SCHEMA_EVAL_JS)
    info["schema"] = schema
    log_schema_summary(schema, vlog)

    vlog("─── End Schema ───")
    return info


async def dump_selectors(page, selectors: dict[str, str]) -> dict[str, int]:
    """
    Try each selector and report which ones matched elements.
    Returns {name: count} for found elements.
    """
    if not _VERBOSE:
        return {}

    vlog("─── Selector Matching ───")
    results = {}
    for name, selector in selectors.items():
        try:
            count = await page.locator(selector).count()
            status = f"✓ {count} match(es)" if count > 0 else "✗ no match"
            vlog(f"  {name:20s} → {selector:50s} {status}")
            results[name] = count
        except Exception as e:
            vlog(f"  {name:20s} → {selector:50s} ERROR: {e}")
            results[name] = 0
    vlog("─── End Selectors ───")
    return results


def vlog_decision(action: str, reason: str, alternatives: list[str] | None = None) -> None:
    """Log a decision made during automation."""
    if not _VERBOSE:
        return
    vlog(f"DECISION: {action}")
    vlog(f"  reason: {reason}", indent=1)
    if alternatives:
        vlog(f"  alternatives considered: {alternatives}", indent=1)


def ensure_playwright_browsers(auto_install: bool = True, browser_type: str = "chromium") -> bool:
    """
    Check if Playwright browsers are installed, and auto-install if missing.
    SYNC version - for use in non-async contexts.

    Args:
        auto_install: If True, automatically installs browsers without prompting.
        browser_type: The browser type to install (default: chromium).

    Returns:
        True if browsers are available (or were successfully installed),
        False if installation failed or was declined.
    """
    try:
        from playwright.sync_api import sync_playwright

        # Check if browser exists by trying to launch it
        with sync_playwright() as pw:
            try:
                browser = getattr(pw, browser_type).launch()
                browser.close()
                vlog(f"Playwright {browser_type} browser found")
                return True
            except Exception as e:
                vlog(f"Browser launch check failed: {e}")
                pass  # Browser not installed
    except ImportError:
        print("ERROR: Playwright Python package not installed.")
        print("       Run: pip install playwright")
        return False

    # Browser not found, try to install
    print(f"Playwright {browser_type} browser not found.")

    if not auto_install:
        response = input("Would you like to install it now? [Y/n]: ").strip().lower()
        if response not in ("", "y", "yes"):
            print(f"Please install manually: playwright install {browser_type}")
            return False

    print(f"Installing Playwright {browser_type} browser...")
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", browser_type],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"✓ Playwright {browser_type} installed successfully")
        return True
    else:
        print(f"✗ Installation failed:")
        print(result.stderr)
        print(f"\nPlease install manually: playwright install {browser_type}")
        return False


async def ensure_playwright_browsers_async(auto_install: bool = True, browser_type: str = "chromium") -> bool:
    """
    Check if Playwright browsers are installed, and auto-install if missing.
    ASYNC version - for use inside async functions.

    Args:
        auto_install: If True, automatically installs browsers without prompting.
        browser_type: The browser type to install (default: chromium).

    Returns:
        True if browsers are available (or were successfully installed),
        False if installation failed or was declined.
    """
    try:
        from playwright.async_api import async_playwright

        # Check if browser exists by trying to launch it
        async with async_playwright() as pw:
            try:
                browser = await getattr(pw, browser_type).launch()
                await browser.close()
                vlog(f"Playwright {browser_type} browser found")
                return True
            except Exception as e:
                vlog(f"Browser launch check failed: {e}")
                pass  # Browser not installed
    except ImportError:
        print("ERROR: Playwright Python package not installed.")
        print("       Run: pip install playwright")
        return False

    # Browser not found, try to install
    print(f"Playwright {browser_type} browser not found.")

    if not auto_install:
        response = input("Would you like to install it now? [Y/n]: ").strip().lower()
        if response not in ("", "y", "yes"):
            print(f"Please install manually: playwright install {browser_type}")
            return False

    print(f"Installing Playwright {browser_type} browser...")
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", browser_type],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"✓ Playwright {browser_type} installed successfully")
        return True
    else:
        print(f"✗ Installation failed:")
        print(result.stderr)
        print(f"\nPlease install manually: playwright install {browser_type}")
        return False


def _build_url_candidates(initial_url: str, fallback_urls: list[str] | None = None) -> list[str]:
    urls_to_try = [initial_url]
    if fallback_urls:
        urls_to_try.extend(fallback_urls)

    parsed = urlparse(initial_url)
    base_domain = f"{parsed.scheme}://{parsed.netloc}"
    for url in (
        base_domain,
        f"{base_domain}/",
        f"{base_domain}/pl",
        f"{base_domain}/pl/",
        f"{base_domain}/en",
        f"{base_domain}/en/",
        f"{base_domain}/draw",
        f"{base_domain}/draw.html",
        f"{base_domain}/canvas",
        f"{base_domain}/whiteboard",
        f"{base_domain}/board",
    ):
        if url not in urls_to_try:
            urls_to_try.append(url)
    return urls_to_try


async def _try_url_for_selector(page, url: str, required_selector: str, timeout: int) -> str | None:
    response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    await page.wait_for_timeout(1000)

    status = response.status if response else 0
    title = await page.title()
    if status == 404 or "404" in title or "Not Found" in title:
        vlog("  → 404 or not found page", indent=2)
        return None

    element_count = await page.locator(required_selector).count()
    if element_count > 0:
        vlog(f"  → SUCCESS: Found {element_count} '{required_selector}' elements", indent=2)
        print(f"   ✓ Auto-discovered working URL: {page.url}")
        return page.url

    vlog(f"  → No '{required_selector}' found, trying next", indent=2)
    return None


async def discover_working_url(page, initial_url: str, fallback_urls: list[str] | None = None, 
                                required_selector: str = "canvas", timeout: int = 10000) -> str | None:
    """
    Auto-discover working URL when initial URL fails (404 or missing required elements).
    
    Strategy:
    1. Check if initial URL loads and has required element
    2. If not, try fallback URLs in order
    3. If none work, try base domain auto-discovery
    
    Args:
        page: Playwright page object
        initial_url: The URL to try first
        fallback_urls: List of alternative URLs to try
        required_selector: CSS selector that must exist on the page (default: canvas)
        timeout: Timeout in ms for each attempt
        
    Returns:
        Working URL string, or None if no URL works
    """
    urls_to_try = _build_url_candidates(initial_url, fallback_urls)
    vlog(f"URL discovery: will try {len(urls_to_try)} URLs looking for '{required_selector}'")

    for i, url in enumerate(urls_to_try, 1):
        try:
            vlog(f"Trying URL {i}/{len(urls_to_try)}: {url}", indent=1)
            working = await _try_url_for_selector(page, url, required_selector, timeout)
            if working:
                return working
        except Exception as e:
            vlog(f"  → Failed: {str(e)[:60]}", indent=2)
    
    vlog(f"No working URL found after {len(urls_to_try)} attempts", indent=1)
    return None


async def auto_navigate_with_fallback(page, target_urls: dict[str, str], 
                                       target_name: str, **discovery_kwargs) -> str | None:
    """
    Navigate to target URL with automatic fallback discovery.
    
    Args:
        page: Playwright page object
        target_urls: Dict mapping target names to URLs
        target_name: Key in target_urls to navigate to
        **discovery_kwargs: Passed to discover_working_url()
        
    Returns:
        The actual URL that worked, or None if all failed
    """
    initial_url = target_urls.get(target_name)
    if not initial_url:
        print(f"ERROR: Unknown target '{target_name}'")
        return None
    
    print(f"3. Opening {target_name}...")
    
    # Try initial URL first
    working_url = await discover_working_url(page, initial_url, **discovery_kwargs)
    
    if working_url:
        return working_url
    
    # If that failed, try other targets as fallbacks
    print(f"   Initial URL failed, trying alternative paths...")
    
    for other_name, other_url in target_urls.items():
        if other_name != target_name:
            vlog(f"Trying alternative target: {other_name}")
            working_url = await discover_working_url(page, other_url, **discovery_kwargs)
            if working_url:
                print(f"   ✓ Switched to alternative: {other_name} ({working_url})")
                return working_url
    
    print(f"   ✗ Could not find working URL for {target_name}")
    return None
