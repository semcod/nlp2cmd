"""
Site Explorer - Automatic discovery of forms and pages on websites.

Algorytm eksploracji strony www:
1. Odwiedź stronę główną i zbierz linki z menu/nawigacji
2. Przeszukaj podstrony (max 2-3 poziomy) pod kątem formularzy
3. Zwróć URL strony zawierającej formularz
4. Cache'uj wyniki w site profile
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen, Request
from urllib.error import URLError
import xml.etree.ElementTree as ET

# Import modular page analysis
try:
    from nlp2cmd.page_analysis import PageAnalyzer, PageAnalysisResult
    _PAGE_ANALYSIS_AVAILABLE = True
except ImportError:
    _PAGE_ANALYSIS_AVAILABLE = False

_DEBUG = os.environ.get("NLP2CMD_DEBUG", "").lower() in ("1", "true", "yes")


def _debug(msg: str) -> None:
    """Print debug message to stderr when NLP2CMD_DEBUG=1."""
    if _DEBUG:
        print(f"DEBUG [SiteExplorer] {msg}", file=sys.stderr, flush=True)


# ── Module-level helpers for platform URL resolution ──────────────────
def _github_readme_url(url: str) -> str:
    """Convert github.com/owner/repo to raw README URL."""
    parsed = urlparse(url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) >= 2:
        return f"https://github.com/{parts[0]}/{parts[1]}"
    return url


def _github_docs_url(url: str) -> str:
    """Try to resolve GitHub repo docs (wiki, /docs, or README)."""
    parsed = urlparse(url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) >= 2:
        return f"https://github.com/{parts[0]}/{parts[1]}/tree/main/docs"
    return url


def _pypi_to_docs_url(url: str) -> Optional[str]:
    """Convert pypi.org/project/X to readthedocs or homepage."""
    parsed = urlparse(url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) >= 2 and parts[0] == "project":
        pkg = parts[1].lower().replace("-", "").replace("_", "")
        return f"https://{pkg}.readthedocs.io/en/latest/"
    return None


@dataclass
class PageInfo:
    """Information about a discovered page."""
    url: str
    title: str = ""
    links: list[str] = field(default_factory=list)
    has_form: bool = False
    form_count: int = 0
    contact_field_count: int = 0
    junk_field_count: int = 0
    score: float = 0.0  # Relevance score for form/contact pages
    load_time_ms: float = 0.0  # Page load + analysis time


@dataclass
class ExplorationResult:
    """Result of site exploration."""
    success: bool
    form_url: Optional[str] = None
    form_page: Optional[PageInfo] = None
    explored_pages: list[PageInfo] = field(default_factory=list)
    error: Optional[str] = None


class SiteExplorer:
    """
    Explores website to find forms, contact pages, and other content.
    
    Usage:
        explorer = SiteExplorer()
        result = explorer.find_form(url="https://example.com", intent="contact")
        if result.success:
            print(f"Found form at: {result.form_url}")
    """
    
    # Keywords that suggest a page might contain a contact form
    CONTACT_KEYWORDS = [
        "kontakt", "contact", "napisz do nas", "write to us",
        "formularz", "form", "wiadomość", "message",
        "pomoc", "help", "support", "serwis",
        "zapytaj", "ask", "biuro", "office", "dane", "info",
        "obsługa", "obsuga", "klienta", "customer",
    ]
    
    # Keywords that suggest articles/content
    ARTICLE_KEYWORDS = [
        "artykuł", "article", "blog", "news", "wiadomości", "aktualności",
        "publikacja", "publication", "post", "wpis", "treść", "content",
        "poradnik", "guide", "tutorial", "instrukcja", "manual",
    ]
    
    # Keywords that suggest products/services
    PRODUCT_KEYWORDS = [
        "produkt", "product", "usługa", "service", "oferta", "offer",
        "sklep", "shop", "store", "cennik", "price", "cena", "buy",
        "katalog", "catalog", "portfolio", "galeria", "gallery",
    ]
    
    # Keywords that suggest documentation/help
    DOCS_KEYWORDS = [
        "dokumentacja", "documentation", "docs", "pomoc", "help",
        "faq", "pytania", "questions", "support", "wsparcie",
        "manual", "instrukcja", "guide", "tutorial", "readme",
        "wiki", "api", "reference", "examples", "przykłady",
        "github", "gitlab", "bitbucket", "repository", "repo"
    ]
    
    # Keywords that suggest form fields
    FORM_FIELD_KEYWORDS = [
        "email", "e-mail", "telefon", "phone", "imię", "name",
        "nazwisko", "surname", "wiadomość", "message", "temat", "subject",
    ]

    # Resource types to block for faster loading
    BLOCKED_RESOURCE_PATTERNS = (
        "**/*.png", "**/*.jpg", "**/*.jpeg", "**/*.gif", "**/*.svg",
        "**/*.webp", "**/*.ico", "**/*.bmp", "**/*.tiff",
        "**/*.woff", "**/*.woff2", "**/*.ttf", "**/*.eot",
        "**/*.mp4", "**/*.webm", "**/*.ogg", "**/*.mp3",
    )

    # Smart URL shortcuts for known platforms (Strategy 3)
    PLATFORM_DOCS_URLS: dict[str, Any] = {
        "github.com": {
            "readme": lambda url: _github_readme_url(url),
            "docs": lambda url: _github_docs_url(url),
        },
        "readthedocs.io": {
            "docs": lambda url: url if "/en/" in url else url.rstrip("/") + "/en/latest/",
        },
        "docs.python.org": {
            "docs": lambda _url: "https://docs.python.org/3/",
        },
        "pypi.org": {
            "docs": lambda url: _pypi_to_docs_url(url),
        },
    }

    # Known documentation frameworks with predictable URL structures (Strategy 8)
    DOCS_FRAMEWORKS: dict[str, list[str]] = {
        "readthedocs": ["/en/latest/", "/en/stable/", "readthedocs.io"],
        "mkdocs": ["/mkdocs.yml", "mkdocs-material", "/site/"],
        "gitbook": ["gitbook.io", ".gitbook.io"],
        "sphinx": ["/_static/sphinx", "searchindex.js", "genindex.html"],
        "docusaurus": ["/docs/", "/blog/", "docusaurus"],
    }

    def __init__(
        self,
        max_depth: int = 2,
        max_pages: int = 10,
        headless: bool = True,
        timeout_ms: int = 15000,
        dynamic_wait_ms: int = 500,
        block_resources: bool = True,
        max_retries: int = 3,
    ):
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.dynamic_wait_ms = dynamic_wait_ms
        self.block_resources = block_resources
        self.max_retries = max_retries
        self._explored_urls: set[str] = set()
        self._max_sitemap_urls: int = 50
        self._timing_stats: list[dict[str, Any]] = []

    # ── Strategy 2: Resource Blocking ──────────────────────────────────
    @staticmethod
    def _setup_resource_blocking(context: Any) -> None:
        """Block images, fonts, video, CSS to speed up page loads (~70% faster)."""
        def _abort_heavy(route: Any) -> None:
            try:
                route.abort()
            except Exception:
                pass

        for pattern in SiteExplorer.BLOCKED_RESOURCE_PATTERNS:
            try:
                context.route(pattern, _abort_heavy)
            except Exception:
                pass
        _debug("Resource blocking enabled")

    # ── Strategy 3: Smart URL Patterns ─────────────────────────────────
    def _resolve_platform_url(self, url: str, content_type: str) -> Optional[str]:
        """Try to resolve a direct URL for known platforms (GitHub, RTD, PyPI)."""
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()

        for platform, handlers in self.PLATFORM_DOCS_URLS.items():
            if platform in netloc:
                handler = handlers.get(content_type) or handlers.get("docs")
                if handler:
                    try:
                        resolved = handler(url)
                        if resolved:
                            _debug(f"Platform shortcut: {platform} -> {resolved}")
                            return resolved
                    except Exception:
                        pass
        return None

    # ── Strategy 4: EPIPE Retry with Backoff ───────────────────────────
    def _goto_with_retry(self, page: Any, url: str) -> None:
        """Navigate to URL with exponential backoff on EPIPE / timeout errors."""
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                page.wait_for_timeout(self.dynamic_wait_ms)
                return
            except Exception as e:
                last_exc = e
                err_str = str(e).lower()
                is_retriable = any(kw in err_str for kw in [
                    "epipe", "broken pipe", "timeout", "net::err_",
                    "connection reset", "connection refused",
                ])
                if not is_retriable:
                    raise
                wait_ms = min(1000 * (2 ** attempt), 8000)
                _debug(f"Retry {attempt + 1}/{self.max_retries} for {url} after {wait_ms}ms: {e}")
                page.wait_for_timeout(wait_ms)
        if last_exc:
            raise last_exc

    # ── Strategy 7: GitHub API Integration ─────────────────────────────
    @staticmethod
    def _try_github_api(url: str) -> Optional[str]:
        """Try to fetch README via GitHub API (no browser needed)."""
        parsed = urlparse(url)
        if "github.com" not in parsed.netloc:
            return None
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(parts) < 2:
            return None
        owner, repo = parts[0], parts[1]
        api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        try:
            req = Request(api_url, headers={
                "Accept": "application/vnd.github.v3.raw",
                "User-Agent": "nlp2cmd/1.0",
            })
            with urlopen(req, timeout=5) as resp:
                content = resp.read().decode("utf-8", errors="replace")
                if len(content) > 50:
                    _debug(f"GitHub API: fetched README ({len(content)} chars) for {owner}/{repo}")
                    return content
        except Exception as e:
            _debug(f"GitHub API failed for {owner}/{repo}: {e}")
        return None

    # ── Strategy 8: Documentation Framework Detection ──────────────────
    def _detect_docs_framework(self, url: str, page_html: str = "") -> Optional[str]:
        """Detect documentation framework from URL or page HTML."""
        url_lower = url.lower()
        html_lower = page_html.lower() if page_html else ""
        combined = url_lower + " " + html_lower

        for framework, indicators in self.DOCS_FRAMEWORKS.items():
            if any(ind in combined for ind in indicators):
                _debug(f"Detected docs framework: {framework} at {url}")
                return framework
        return None

    # ── Strategy 9: Timing Metrics ─────────────────────────────────────
    def _record_timing(self, url: str, phase: str, duration_ms: float) -> None:
        """Record timing metric for a phase."""
        entry = {"url": url, "phase": phase, "duration_ms": round(duration_ms, 1)}
        self._timing_stats.append(entry)
        if duration_ms > 5000:
            _debug(f"⚠ SLOW {phase}: {url} took {duration_ms:.0f}ms")
        elif _DEBUG:
            _debug(f"Timing {phase}: {url} = {duration_ms:.0f}ms")

    def get_timing_stats(self) -> list[dict[str, Any]]:
        """Return collected timing stats."""
        return list(self._timing_stats)

    # ── Strategy 10: Graceful Degradation ──────────────────────────────
    @staticmethod
    def _fallback_static_scrape(url: str, timeout: int = 5) -> Optional[PageInfo]:
        """Fallback: fetch page with urllib (no JS) when Playwright fails."""
        try:
            req = Request(url, headers={"User-Agent": "nlp2cmd/1.0 (static fallback)"})
            with urlopen(req, timeout=timeout) as resp:
                html = resp.read().decode("utf-8", errors="replace")

            info = PageInfo(url=url)

            # Extract title
            m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            if m:
                info.title = m.group(1).strip()

            # Count form fields
            inputs = len(re.findall(r'<input\b', html, re.IGNORECASE))
            textareas = len(re.findall(r'<textarea\b', html, re.IGNORECASE))
            info.form_count = inputs + textareas
            info.has_form = info.form_count > 0

            # Extract links
            for m in re.finditer(r'href=["\']([^"\']+)["\']', html):
                href = m.group(1)
                if href.startswith(("http://", "https://")):
                    info.links.append(href)
                elif href.startswith("/"):
                    info.links.append(urljoin(url, href))
            info.links = info.links[:20]

            _debug(f"Static fallback OK: {url} title='{info.title[:40]}' forms={info.form_count} links={len(info.links)}")
            return info
        except Exception as e:
            _debug(f"Static fallback failed for {url}: {e}")
            return None

    def find_content(
        self,
        url: str,
        content_type: str = "article",
        search_term: Optional[str] = None,
        page: Optional[Any] = None,
        context: Optional[Any] = None,
        close_browser: bool = True,
    ) -> ExplorationResult:
        """
        Find content on the website (articles, products, docs, etc.).
        
        Args:
            url: Starting URL (homepage)
            content_type: Type of content to find (article, product, docs, etc.)
            search_term: Optional term to search for in content
            page: Optional existing Playwright page
            context: Optional existing Playwright context
            close_browser: Whether to close browser after exploration
        
        Returns:
            ExplorationResult with content URL or error
        """
        from playwright.sync_api import sync_playwright

        t0 = time.perf_counter()

        # Strategy 3: Try platform-specific URL shortcuts first
        platform_url = self._resolve_platform_url(url, content_type)
        if platform_url and platform_url != url:
            url = platform_url

        # Strategy 7: For GitHub docs, try API first (no browser needed)
        if content_type == "docs" and "github.com" in urlparse(url).netloc:
            readme_content = self._try_github_api(url)
            if readme_content:
                info = PageInfo(url=url, title=f"README ({urlparse(url).path})", score=10.0,
                                load_time_ms=(time.perf_counter() - t0) * 1000)
                self._record_timing(url, "github_api", info.load_time_ms)
                return ExplorationResult(
                    success=True, form_url=url, form_page=info, explored_pages=[info],
                )

        should_close_browser = False
        should_close_context = False
        
        try:
            if page is None:
                p = sync_playwright().start()
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context()
                # Strategy 2: Block heavy resources
                if self.block_resources:
                    self._setup_resource_blocking(context)
                page = context.new_page()
                should_close_browser = True
                should_close_context = close_browser
            
            # Reset state
            self._explored_urls = set()
            self._timing_stats = []
            explored_pages: list[PageInfo] = []

            # Fast-path: try common contact URLs first (cheap and often works even
            # when menu extraction fails or homepage blocks link discovery).
            if intent == "contact":
                try:
                    parsed_base = urlparse(url)
                    base = f"{parsed_base.scheme}://{parsed_base.netloc}" if parsed_base.scheme and parsed_base.netloc else url
                    common_paths = [
                        "/kontakt",
                        "/kontakt/",
                        "/contact",
                        "/contact/",
                        "/kontakt-2",
                        "/kontakt-3",
                    ]
                    for pth in common_paths:
                        if len(self._explored_urls) >= self.max_pages:
                            break
                        cand = self._normalize_url(urljoin(base, pth))
                        result = self._explore_recursive(
                            page=page,
                            url=cand,
                            depth=0,
                            intent=intent,
                            explored_pages=explored_pages,
                            base_domain=urlparse(url).netloc,
                        )
                        if result and result.contact_field_count > 0:
                            return ExplorationResult(
                                success=True,
                                form_url=result.url,
                                form_page=result,
                                explored_pages=explored_pages,
                            )
                except Exception:
                    pass
            
            # Start exploration - first analyze the main page for links
            main_page_result = self._explore_recursive(
                page=page,
                url=url,
                depth=0,
                intent=content_type,
                explored_pages=explored_pages,
                base_domain=urlparse(url).netloc,
                search_term=search_term,
            )
            
            _debug(f"Main page result: {main_page_result is not None}")
            if main_page_result:
                _debug(f"Main page URL: {main_page_result.url}")
                _debug(f"Main page has form: {main_page_result.has_form}, contact_fields: {main_page_result.contact_field_count}")
                _debug(f"Main page links: {len(main_page_result.links)}")
            
            # If main page has the target content AND it's not contact intent, return it
            if main_page_result and self._has_content_type(main_page_result, content_type) and content_type != "contact":
                return ExplorationResult(
                    success=True,
                    form_url=main_page_result.url,  # Reuse field for content URL
                    form_page=main_page_result,
                    explored_pages=explored_pages,
                )
            
            # For contact intent, always explore contact links first even if main page has form
            if main_page_result and main_page_result.links and len(explored_pages) < self.max_pages:
                _debug("Exploring links from main page")
                # Sort links by contact relevance
                contact_links = []
                other_links = []
                
                for link in main_page_result.links[:12]:  # Check more links from main page
                    if len(self._explored_urls) >= self.max_pages:
                        break
                    
                    link_lower = link.lower()
                    if self._is_contact_url(link_lower):
                        contact_links.append(link)
                    else:
                        other_links.append(link)
                
                _debug(f"Found {len(contact_links)} contact links: {contact_links}")
                
                # Explore contact links first
                for link in contact_links[:5]:  # Check up to 5 contact links
                    if len(self._explored_urls) >= self.max_pages:
                        break
                    _debug(f"Exploring contact link: {link}")
                    result = self._explore_recursive(
                        page=page,
                        url=link,
                        depth=1,
                        intent=content_type,
                        explored_pages=explored_pages,
                        base_domain=urlparse(url).netloc,
                        search_term=search_term,
                    )
                    if result and self._has_content_type(result, content_type):
                        _debug(f"Found contact form at: {link}")
                        return ExplorationResult(
                            success=True,
                            form_url=result.url,
                            form_page=result,
                            explored_pages=explored_pages,
                        )
                
                # Then explore other links if no contact form found
                for link in other_links[:3]:  # Check up to 3 other links
                    if len(self._explored_urls) >= self.max_pages:
                        break
                    result = self._explore_recursive(
                        page=page,
                        url=link,
                        depth=1,
                        intent=content_type,
                        explored_pages=explored_pages,
                        base_domain=urlparse(url).netloc,
                        search_term=search_term,
                    )
                    if result and self._has_content_type(result, content_type):
                        return ExplorationResult(
                            success=True,
                            form_url=result.url,
                            form_page=result,
                            explored_pages=explored_pages,
                        )
            
            # No content found - return best candidate
            best_page = self._find_best_content_candidate(explored_pages, content_type, search_term)
            if best_page and self._has_content_type(best_page, content_type):
                return ExplorationResult(
                    success=True,
                    form_url=best_page.url,
                    form_page=best_page,
                    explored_pages=explored_pages,
                )
            
            return ExplorationResult(
                success=False,
                explored_pages=explored_pages,
                error=f"No {content_type} found after exploring {len(explored_pages)} pages",
            )
            
        finally:
            if should_close_context and context:
                context.close()
            if should_close_browser and page:
                try:
                    page.context.browser.close()
                except Exception:
                    pass

    def find_form(
        self,
        url: str,
        intent: str = "contact",
        page: Optional[Any] = None,  # Playwright page object
        context: Optional[Any] = None,  # Playwright context
        close_browser: bool = True,
    ) -> ExplorationResult:
        """
        Find a form on the website matching the intent.
        
        Args:
            url: Starting URL (homepage)
            intent: Type of form to find (contact, search, newsletter, etc.)
            page: Optional existing Playwright page (if None, creates new browser)
            context: Optional existing Playwright context
            close_browser: Whether to close browser after exploration
        
        Returns:
            ExplorationResult with form URL or error
        """
        from playwright.sync_api import sync_playwright

        t0 = time.perf_counter()

        should_close_browser = False
        should_close_context = False
        
        try:
            if page is None:
                p = sync_playwright().start()
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context()
                # Strategy 2: Block heavy resources
                if self.block_resources:
                    self._setup_resource_blocking(context)
                page = context.new_page()
                should_close_browser = True
                should_close_context = close_browser
            
            # Reset state
            self._explored_urls = set()
            self._timing_stats = []
            explored_pages: list[PageInfo] = []

            # Fast-path: try common contact URLs first (cheap and often works even
            # when menu extraction fails or homepage blocks link discovery).
            if intent == "contact":
                try:
                    parsed_base = urlparse(url)
                    base = (
                        f"{parsed_base.scheme}://{parsed_base.netloc}"
                        if parsed_base.scheme and parsed_base.netloc
                        else url
                    )
                    common_paths = [
                        "/kontakt",
                        "/kontakt/",
                        "/contact",
                        "/contact/",
                        "/kontakt-2",
                        "/kontakt-3",
                    ]
                    for pth in common_paths:
                        if len(self._explored_urls) >= self.max_pages:
                            break
                        cand = self._normalize_url(urljoin(base, pth))
                        result = self._explore_recursive(
                            page=page,
                            url=cand,
                            depth=0,
                            intent=intent,
                            explored_pages=explored_pages,
                            base_domain=urlparse(url).netloc,
                        )
                        if result and result.contact_field_count > 0:
                            return ExplorationResult(
                                success=True,
                                form_url=result.url,
                                form_page=result,
                                explored_pages=explored_pages,
                            )
                except Exception:
                    pass

            try:
                sitemap_urls = self._get_sitemap_urls(url)
            except Exception:
                sitemap_urls = []

            if sitemap_urls:
                if intent == "contact":
                    _debug(f"Found {len(sitemap_urls)} sitemap URLs, prioritizing contact links")
                    # For contact intent, prioritize contact URLs from sitemap
                    contact_sitemap_urls = []
                    other_sitemap_urls = []
                    
                    for u in sitemap_urls:
                        u_lower = u.lower()
                        # More strict contact detection - exclude article-like URLs
                        # Look for exact contact-related words, not partial matches
                        is_contact = any(
                            kw in u_lower.split('-') or kw in u_lower.split('/') 
                            for kw in ["kontakt", "contact", "formularz"]
                        )
                        # Only look for standalone "form" word, not part of other words
                        has_form_word = (
                            " form" in u_lower or u_lower.endswith("form") or 
                            u_lower.startswith("form") or " form/" in u_lower
                        ) and not any(word in u_lower for word in ["informacje", "platform", "transform"])
                        
                        is_contact = is_contact or has_form_word
                        is_article = any(kw in u_lower for kw in ["artykul", "article", "informacje", "news", "blog"])
                        
                        if is_contact and not is_article:
                            contact_sitemap_urls.append(u)
                        else:
                            other_sitemap_urls.append(u)
                    
                    _debug(f"Contact sitemap URLs: {contact_sitemap_urls[:3]}")
                    
                    # Explore contact URLs first
                    for u in contact_sitemap_urls[:5]:
                        if len(self._explored_urls) >= self.max_pages:
                            break
                        result = self._explore_recursive(
                            page=page,
                            url=u,
                            depth=0,
                            intent=intent,
                            explored_pages=explored_pages,
                            base_domain=urlparse(url).netloc,
                        )
                        if result and ((intent != "contact" and result.has_form) or (intent == "contact" and result.contact_field_count > 0)):
                            return ExplorationResult(
                                success=True,
                                form_url=result.url,
                                form_page=result,
                                explored_pages=explored_pages,
                            )
                    
                    # Then explore a few other URLs
                    for u in other_sitemap_urls[:3]:
                        if len(self._explored_urls) >= self.max_pages:
                            break
                        result = self._explore_recursive(
                            page=page,
                            url=u,
                            depth=0,
                            intent=intent,
                            explored_pages=explored_pages,
                            base_domain=urlparse(url).netloc,
                        )
                        if result and ((intent != "contact" and result.has_form) or (intent == "contact" and result.contact_field_count > 0)):
                            return ExplorationResult(
                                success=True,
                                form_url=result.url,
                                form_page=result,
                                explored_pages=explored_pages,
                            )
                else:
                    # Original logic for non-contact intents
                    for u in sitemap_urls:
                        if len(self._explored_urls) >= self.max_pages:
                            break
                        result = self._explore_recursive(
                            page=page,
                            url=u,
                            depth=0,
                            intent=intent,
                            explored_pages=explored_pages,
                            base_domain=urlparse(url).netloc,
                        )
                        if result and result.has_form:
                            return ExplorationResult(
                                success=True,
                                form_url=result.url,
                                form_page=result,
                                explored_pages=explored_pages,
                            )
            
            # Start exploration - use the same logic as find_content for contact intent
            if intent == "contact":
                _debug(f"Using contact-aware exploration for {url}")
                # Use the same logic as find_content for contact
                main_page_result = self._explore_recursive(
                    page=page,
                    url=url,
                    depth=0,
                    intent=intent,
                    explored_pages=explored_pages,
                    base_domain=urlparse(url).netloc,
                )
                
                _debug(f"Main page result: {main_page_result is not None}")
                if main_page_result:
                    _debug(f"Main page URL: {main_page_result.url}")
                    _debug(f"Main page has form: {main_page_result.has_form}, contact_fields: {main_page_result.contact_field_count}")
                    _debug(f"Main page links: {len(main_page_result.links)}")
                
                # For contact intent, always explore contact links first even if main page has form
                if main_page_result and main_page_result.links and len(explored_pages) < self.max_pages:
                    _debug("Exploring links from main page")
                    # Sort links by contact relevance
                    contact_links = []
                    other_links = []
                    
                    for link in main_page_result.links[:12]:  # Check more links from main page
                        if len(self._explored_urls) >= self.max_pages:
                            break
                        
                        link_lower = link.lower()
                        if self._is_contact_url(link_lower):
                            contact_links.append(link)
                        else:
                            other_links.append(link)
                    
                    _debug(f"Found {len(contact_links)} contact links: {contact_links}")
                    
                    # Explore contact links first
                    for link in contact_links[:5]:  # Check up to 5 contact links
                        if len(self._explored_urls) >= self.max_pages:
                            break
                        _debug(f"Exploring contact link: {link}")
                        result = self._explore_recursive(
                            page=page,
                            url=link,
                            depth=1,
                            intent=intent,
                            explored_pages=explored_pages,
                            base_domain=urlparse(url).netloc,
                        )
                        if result and result.contact_field_count > 0:
                            _debug(f"Found contact form at: {link}")
                            return ExplorationResult(
                                success=True,
                                form_url=result.url,
                                form_page=result,
                                explored_pages=explored_pages,
                            )
                    
                    # Then explore other links if no contact form found
                    for link in other_links[:3]:  # Check up to 3 other links
                        if len(self._explored_urls) >= self.max_pages:
                            break
                        result = self._explore_recursive(
                            page=page,
                            url=link,
                            depth=1,
                            intent=intent,
                            explored_pages=explored_pages,
                            base_domain=urlparse(url).netloc,
                        )
                        if result and result.contact_field_count > 0:
                            return ExplorationResult(
                                success=True,
                                form_url=result.url,
                                form_page=result,
                                explored_pages=explored_pages,
                            )
            else:
                # Original logic for non-contact intents
                result = self._explore_recursive(
                    page=page,
                    url=url,
                    depth=0,
                    intent=intent,
                    explored_pages=explored_pages,
                    base_domain=urlparse(url).netloc,
                )
                
                if result and result.has_form:
                    return ExplorationResult(
                        success=True,
                        form_url=result.url,
                        form_page=result,
                        explored_pages=explored_pages,
                    )
            
            # No form found - return best candidate or failure
            best_page = self._find_best_form_candidate(explored_pages, intent)
            if best_page and ((intent != "contact" and best_page.has_form) or (intent == "contact" and best_page.contact_field_count > 0)):
                return ExplorationResult(
                    success=True,
                    form_url=best_page.url,
                    form_page=best_page,
                    explored_pages=explored_pages,
                )
            
            return ExplorationResult(
                success=False,
                explored_pages=explored_pages,
                error=f"No form found after exploring {len(explored_pages)} pages",
            )
            
        finally:
            if should_close_context and context:
                context.close()
            if should_close_browser and page:
                try:
                    page.context.browser.close()
                except Exception:
                    pass
    
    def _explore_recursive(
        self,
        page: Any,
        url: str,
        depth: int,
        intent: str,
        explored_pages: list[PageInfo],
        base_domain: str,
        search_term: Optional[str] = None,
    ) -> Optional[PageInfo]:
        """Recursively explore pages to find forms or content."""
        
        # Normalize URL
        url = self._normalize_url(url)
        
        # Skip if already explored or max limits reached
        if url in self._explored_urls:
            return None
        if len(self._explored_urls) >= self.max_pages:
            return None
        if depth > self.max_depth:
            return None
        
        # Check domain - stay on same domain
        parsed = urlparse(url)
        if parsed.netloc != base_domain:
            return None
        
        self._explored_urls.add(url)
        
        try:
            t_start = time.perf_counter()

            # Strategy 4: Navigate with EPIPE retry + exponential backoff
            self._goto_with_retry(page, url)
            
            # Try to dismiss popups first
            self._dismiss_popups(page)
            
            page_info = self._analyze_page(page, url)

            # Strategy 9: Record timing
            elapsed_ms = (time.perf_counter() - t_start) * 1000
            page_info.load_time_ms = elapsed_ms
            self._record_timing(url, "explore", elapsed_ms)

            explored_pages.append(page_info)
            
            # If target content found, return immediately (except for contact - we want to check contact links first)
            if self._has_content_type(page_info, intent) and intent != "contact":
                return page_info
            
            # For contact intent, always explore contact links first even if main page has form
            if intent == "contact":
                # Check if this page has contact-related URL - if yes, return it
                if self._is_contact_url(url.lower()) and page_info.contact_field_count > 0:
                    return page_info  # This is likely a contact page
                # Otherwise, continue exploring to find contact page even if current page has form
            elif page_info.has_form:
                return page_info  # For non-contact intents, return immediately
            
            # Otherwise explore linked pages
            if depth < self.max_depth:
                for link in page_info.links[:5]:  # Limit links per page
                    result = self._explore_recursive(
                        page=page,
                        url=link,
                        depth=depth + 1,
                        intent=intent,
                        explored_pages=explored_pages,
                        base_domain=base_domain,
                        search_term=search_term,
                    )
                    if not result:
                        continue

                    if intent == "contact":
                        if result.contact_field_count > 0:
                            return result
                    else:
                        if result.has_form or self._has_content_type(result, intent):
                            return result
            
            return None
            
        except Exception as e:
            _debug(f"Playwright failed for {url}: {e}")
            # Strategy 10: Graceful degradation — try static scrape
            fallback = self._fallback_static_scrape(url)
            if fallback:
                explored_pages.append(fallback)
                return fallback
            return None
    
    def _analyze_page(self, page: Any, url: str, console: Optional[Any] = None) -> PageInfo:
        """Analyze a page for forms, iframes, and links."""
        info = PageInfo(url=url)

        try:
            info.title = page.title() or ""
        except Exception:
            pass

        # Look for forms/fields
        try:
            inputs = page.query_selector_all('input:not([type="hidden"])')
            textareas = page.query_selector_all('textarea')
            selects = page.query_selector_all('select')

            info.form_count = len(inputs) + len(textareas) + len(selects)
            info.has_form = info.form_count > 0
        except Exception:
            inputs = []
            textareas = []
            selects = []
            info.form_count = 0
            info.has_form = False

        # Compute contact-like vs junk fields for contact intent.
        # This helps avoid false positives (search boxes, cookie consent toggles,
        # comment forms, captcha-only pages).
        try:
            field_nodes = []
            try:
                field_nodes.extend(inputs[:30])
            except Exception:
                field_nodes.extend(inputs)
            try:
                field_nodes.extend(textareas[:15])
            except Exception:
                field_nodes.extend(textareas)

            def _is_junk_desc(field_type: str, name: str, fid: str, placeholder: str, aria: str) -> bool:
                ft = (field_type or "").strip().lower()
                n = (name or "").strip().lower()
                i = (fid or "").strip().lower()
                p = (placeholder or "").strip().lower()
                a = (aria or "").strip().lower()
                hay = " ".join([n, i, p, a])

                if ft == "search" or n in {"s", "q", "search", "query"}:
                    return True
                if "search" in hay or "szukaj" in hay or "wyszuki" in hay:
                    return True

                if "cookie" in hay or "consent" in hay:
                    return True
                if i.startswith("cky") or "cky" in hay:
                    return True
                if i.startswith("cmplz") or "cmplz" in hay:
                    return True

                if "captcha" in hay or "recaptcha" in hay or "g-recaptcha" in hay or "hcaptcha" in hay:
                    return True

                if n.startswith("apbct__") or "cleantalk" in hay:
                    return True

                if "comment" in hay or n in {"author", "email", "url"}:
                    return True

                return False

            def _is_contact_desc(field_type: str, name: str, fid: str, placeholder: str, aria: str) -> bool:
                ft = (field_type or "").strip().lower()
                n = (name or "").strip().lower()
                i = (fid or "").strip().lower()
                p = (placeholder or "").strip().lower()
                a = (aria or "").strip().lower()
                hay = " ".join([n, i, p, a])

                if _is_junk_desc(field_type, name, fid, placeholder, aria):
                    return False

                if ft in {"email", "tel"}:
                    return True
                if ft == "textarea":
                    return True

                tokens = [
                    "email",
                    "e-mail",
                    "mail",
                    "telefon",
                    "phone",
                    "wiadomo",
                    "message",
                    "temat",
                    "subject",
                    "imi",
                    "name",
                ]
                return any(t in hay for t in tokens)

            for node in field_nodes:
                try:
                    tag = (node.evaluate('el => el.tagName.toLowerCase()') or "").strip().lower()
                except Exception:
                    tag = ""
                try:
                    ftype = (node.get_attribute('type') or ("textarea" if tag == "textarea" else "text"))
                except Exception:
                    ftype = "text"
                try:
                    name = node.get_attribute('name') or ""
                except Exception:
                    name = ""
                try:
                    fid = node.get_attribute('id') or ""
                except Exception:
                    fid = ""
                try:
                    placeholder = node.get_attribute('placeholder') or ""
                except Exception:
                    placeholder = ""
                try:
                    aria = node.get_attribute('aria-label') or ""
                except Exception:
                    aria = ""

                if _is_junk_desc(str(ftype), name, fid, placeholder, aria):
                    info.junk_field_count += 1
                if _is_contact_desc(str(ftype), name, fid, placeholder, aria):
                    info.contact_field_count += 1
        except Exception:
            pass
        
        # Check for forms inside iframes (common for contact widgets)
        if not info.has_form:
            try:
                iframes = page.query_selector_all('iframe')
                for i, iframe in enumerate(iframes[:3]):  # Check first 3 iframes
                    try:
                        frame = iframe.content_frame()
                        if frame:
                            # Count inputs in iframe
                            iframe_inputs = frame.query_selector_all('input:not([type="hidden"])')
                            iframe_textareas = frame.query_selector_all('textarea')
                            if len(iframe_inputs) > 0 or len(iframe_textareas) > 0:
                                info.has_form = True
                                info.form_count += len(iframe_inputs) + len(iframe_textareas)
                                break
                    except Exception:
                        continue
            except Exception:
                pass
        
        # Score page based on content
        info.score = self._score_page(page, url, info)
        
        # Extract links for further exploration
        try:
            selector_groups = [
                'nav a[href], header a[href], [role="navigation"] a[href]',
                'footer a[href]',
                'a[href]',
            ]
            for sel in selector_groups:
                links = page.query_selector_all(sel)
                for link in links:
                    try:
                        href = link.get_attribute('href')
                        if href:
                            absolute_url = urljoin(url, href)
                            parsed = urlparse(absolute_url)
                            if parsed.netloc == urlparse(url).netloc:
                                if not any(absolute_url.endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.mp4']):
                                    info.links.append(absolute_url)
                    except Exception:
                        continue
        except Exception:
            pass
        
        # Remove duplicates but preserve order
        seen = set()
        unique_links = []
        for link in info.links:
            normalized = self._normalize_url(link)
            if normalized not in seen:
                seen.add(normalized)
                unique_links.append(normalized)
        info.links = unique_links[:10]  # Limit links
        
        return info
    
    def _analyze_page_dispatch(self, page: Any, url: str, console: Optional[Any] = None) -> PageInfo:
        """New page analysis using modular PageAnalyzer.
        
        This is the refactored version that uses the page_analysis package.
        Falls back to legacy _analyze_page if modular version unavailable.
        """
        if not _PAGE_ANALYSIS_AVAILABLE:
            return self._analyze_page(page, url, console)
        
        try:
            from nlp2cmd.page_analysis import PageAnalyzer
            
            analyzer = PageAnalyzer(max_links=10)
            result = analyzer.analyze(page, url)
            
            # Convert PageAnalysisResult to PageInfo
            info = PageInfo(url=url)
            info.title = result.title
            info.has_form = result.has_form
            info.form_count = result.form_count
            info.links = result.links
            info.score = result.score
            
            # Copy field classification counts
            info.contact_field_count = result.contact_field_count
            info.junk_field_count = result.junk_field_count
            
            return info
            
        except Exception as e:
            _debug(f"PageAnalyzer failed: {e}, falling back to legacy")
            return self._analyze_page(page, url, console)
    
    def _dismiss_popups(self, page: Any) -> None:
        """Try to dismiss common popups and cookie consents."""
        dismiss_selectors = [
            'button:has-text("Accept all")',
            'button:has-text("Akceptuj wszystko")',
            'button:has-text("Zaakceptuj")',
            'button:has-text("Accept")',
            'button:has-text("Zgadzam się")',
            'button:has-text("Zgadzam sie")',
            'button:has-text("I agree")',
            'button:has-text("OK")',
            'button[aria-label*="Accept"]',
            'button[aria-label*="Akceptuj"]',
            '[data-testid="cookie-accept"]',
            '.cookie-accept',
            '#onetrust-accept-btn-handler',
        ]
        
        for selector in dismiss_selectors:
            try:
                page.wait_for_selector(selector, state="visible", timeout=1500)
                page.click(selector, timeout=1500)
                page.wait_for_timeout(500)
                break
            except Exception:
                continue
    
    def _score_page(self, page: Any, url: str, info: PageInfo, intent: str = "contact") -> float:
        """Score page relevance for finding content."""
        score = 0.0
        url_lower = url.lower()
        title_lower = info.title.lower()
        
        # Choose keyword set based on intent
        if intent == "contact":
            keywords = self.CONTACT_KEYWORDS
        elif intent == "article":
            keywords = self.ARTICLE_KEYWORDS
        elif intent == "product":
            keywords = self.PRODUCT_KEYWORDS
        elif intent == "docs":
            keywords = self.DOCS_KEYWORDS
        else:
            keywords = self.CONTACT_KEYWORDS  # Default
        
        # URL contains intent keywords
        for kw in keywords:
            if kw in url_lower:
                score += 2.0
        
        # Title contains intent keywords
        for kw in keywords:
            if kw in title_lower:
                score += 1.5
        
        # Special scoring for different content types
        if intent == "contact" and info.has_form:
            score += 4.0  # Increased boost for forms
            # Check for email/phone fields (strong indicator of contact form)
            try:
                page_html = page.content().lower()
                indicators = self.FORM_FIELD_KEYWORDS + ["required", "wyslij", "wyślij", "submit"]
                for kw in indicators:
                    if kw in page_html:
                        score += 0.5
            except Exception:
                pass
        elif intent == "article":
            # Check for article-like content
            try:
                page_html = page.content().lower()
                article_indicators = ["<article", "<h1", "<h2", "blog", "news", "post"]
                for indicator in article_indicators:
                    if indicator in page_html:
                        score += 0.3
            except Exception:
                pass
        elif intent == "product":
            # Check for product indicators
            try:
                page_html = page.content().lower()
                product_indicators = ["price", "cena", "buy", "kup", "cart", "koszyk", "shop"]
                for indicator in product_indicators:
                    if indicator in page_html:
                        score += 0.3
            except Exception:
                pass
        elif intent == "docs":
            # Check for documentation indicators
            try:
                page_html = page.content().lower()
                docs_indicators = ["documentation", "docs", "manual", "guide", "tutorial", "faq"]
                for indicator in docs_indicators:
                    if indicator in page_html:
                        score += 0.3
            except Exception:
                pass
        
        return score
    
    @staticmethod
    def _is_contact_url(url_lower: str) -> bool:
        """Check if a lowered URL looks like a contact/form page.

        Avoids false positives from words like 'informacje', 'platform', 'transform'.
        """
        # Direct keyword hits
        if any(kw in url_lower for kw in ["kontakt", "contact", "formularz"]):
            return True
        # Standalone "form" (not inside other words)
        has_form_word = (
            "/form" in url_lower or url_lower.endswith("/form")
            or "-form" in url_lower or "form-" in url_lower
        ) and not any(w in url_lower for w in ["informacje", "platform", "transform", "perform", "reform"])
        return has_form_word

    def _find_best_form_candidate(
        self,
        pages: list[PageInfo],
        intent: str,
    ) -> Optional[PageInfo]:
        """Find the best page with form based on scores."""
        # Filter pages with forms
        form_pages = [p for p in pages if p.has_form]
        if not form_pages:
            return None
        
        # Prioritize pages with contact-related URLs for contact intent
        if intent == "contact":
            contact_urls = [p for p in form_pages if self._is_contact_url(p.url.lower())]
            if contact_urls:
                form_pages = contact_urls
        
        # Sort by score descending
        form_pages.sort(key=lambda p: p.score, reverse=True)
        return form_pages[0]
    
    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize URL for comparison."""
        # Remove fragment
        url = url.split('#')[0]
        # Remove trailing slash
        url = url.rstrip('/')
        return url

    def _get_sitemap_urls(self, base_url: str) -> list[str]:
        parsed = urlparse(base_url)
        if not parsed.scheme or not parsed.netloc:
            return []

        sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"

        try:
            with urlopen(sitemap_url, timeout=max(1, int(self.timeout_ms / 1000))) as resp:
                raw = resp.read()
        except Exception:
            return []

        try:
            root = ET.fromstring(raw)
        except Exception:
            return []

        ns = ""
        if root.tag.startswith("{") and "}" in root.tag:
            ns = root.tag.split("}", 1)[0] + "}"

        urls: list[str] = []

        if root.tag.endswith("sitemapindex"):
            for sm in root.findall(f"{ns}sitemap"):
                loc = sm.find(f"{ns}loc")
                if loc is None or not (loc.text or "").strip():
                    continue
                sm_url = (loc.text or "").strip()
                try:
                    with urlopen(sm_url, timeout=max(1, int(self.timeout_ms / 1000))) as resp:
                        sm_raw = resp.read()
                    sm_root = ET.fromstring(sm_raw)
                except Exception:
                    continue

                sm_ns = ""
                if sm_root.tag.startswith("{") and "}" in sm_root.tag:
                    sm_ns = sm_root.tag.split("}", 1)[0] + "}"

                for u in sm_root.findall(f"{sm_ns}url"):
                    loc2 = u.find(f"{sm_ns}loc")
                    if loc2 is None:
                        continue
                    txt = (loc2.text or "").strip()
                    if not txt:
                        continue
                    if urlparse(txt).netloc != parsed.netloc:
                        continue
                    urls.append(txt)
                    if len(urls) >= self._max_sitemap_urls:
                        break
                if len(urls) >= self._max_sitemap_urls:
                    break
        else:
            for u in root.findall(f"{ns}url"):
                loc = u.find(f"{ns}loc")
                if loc is None:
                    continue
                txt = (loc.text or "").strip()
                if not txt:
                    continue
                if urlparse(txt).netloc != parsed.netloc:
                    continue
                urls.append(txt)
                if len(urls) >= self._max_sitemap_urls:
                    break

        if not urls:
            return []

        def _score_url(u: str) -> float:
            ul = u.lower()
            s = 0.0
            for kw in self.CONTACT_KEYWORDS:
                if kw in ul:
                    s += 2.0
            if any(x in ul for x in ["kontakt", "contact", "formularz", "form", "wiadomosc", "wiadomość"]):
                s += 2.0
            if any(x in ul for x in ["tel", "email", "mail"]):
                s += 1.0
            return s

        urls = sorted(urls, key=_score_url, reverse=True)
        return urls[: self._max_sitemap_urls]

    def _has_content_type(self, page_info: PageInfo, content_type: str) -> bool:
        """Check if page has specific content type."""
        if content_type in ["contact", "form"]:
            return page_info.has_form
        
        intent_keywords = {
            "article": self.ARTICLE_KEYWORDS,
            "product": self.PRODUCT_KEYWORDS,
            "docs": self.DOCS_KEYWORDS,
        }
        keywords = intent_keywords.get(content_type, [])
        url_lower = page_info.url.lower()
        title_lower = page_info.title.lower()
        
        for kw in keywords:
            if kw in url_lower or kw in title_lower:
                return True
        return False
    
    def _find_best_content_candidate(
        self,
        pages: list[PageInfo],
        content_type: str,
        search_term: Optional[str] = None,
    ) -> Optional[PageInfo]:
        """Find best page for content type."""
        intent_keywords = {
            "article": self.ARTICLE_KEYWORDS,
            "product": self.PRODUCT_KEYWORDS,
            "docs": self.DOCS_KEYWORDS,
        }
        keywords = intent_keywords.get(content_type, [])
        
        best_page = None
        best_score = -1.0
        
        for p in pages:
            score = 0.0
            url_lower = p.url.lower()
            title_lower = p.title.lower()
            
            for kw in keywords:
                if kw in url_lower:
                    score += 2.0
                if kw in title_lower:
                    score += 1.5
            
            if search_term:
                st_lower = search_term.lower()
                if st_lower in url_lower:
                    score += 3.0
                if st_lower in title_lower:
                    score += 2.0
            
            if score > best_score:
                best_score = score
                best_page = p
        
        return best_page

    # ── Strategy 5: Two-Phase Exploration ─────────────────────────────
    def find_content_twophase(
        self,
        url: str,
        content_type: str = "article",
        search_term: Optional[str] = None,
        quick_timeout_ms: int = 5000,
        quick_max_pages: int = 5,
    ) -> ExplorationResult:
        """Phase 1: quick scan with short timeouts. Phase 2: deep dive on best candidates."""
        from playwright.sync_api import sync_playwright

        t0 = time.perf_counter()
        _debug(f"Two-phase exploration: phase 1 (quick scan) for {url}")

        # Phase 1: Quick scan — short timeouts, few pages
        quick_explorer = SiteExplorer(
            max_depth=1,
            max_pages=quick_max_pages,
            headless=self.headless,
            timeout_ms=quick_timeout_ms,
            dynamic_wait_ms=200,
            block_resources=True,
            max_retries=1,
        )
        quick_result = quick_explorer.find_content(
            url=url, content_type=content_type, search_term=search_term,
        )

        phase1_ms = (time.perf_counter() - t0) * 1000
        self._record_timing(url, "twophase_quick", phase1_ms)

        if quick_result.success:
            _debug(f"Two-phase: found in phase 1 ({phase1_ms:.0f}ms)")
            return quick_result

        # Phase 2: Deep dive on discovered links
        _debug(f"Two-phase: phase 2 (deep dive) on {len(quick_result.explored_pages)} candidates")
        candidate_urls = []
        for pg in quick_result.explored_pages:
            candidate_urls.extend(pg.links[:3])

        if not candidate_urls:
            return quick_result

        # Deduplicate
        seen = set()
        unique_candidates = []
        for c in candidate_urls:
            norm = self._normalize_url(c)
            if norm not in seen:
                seen.add(norm)
                unique_candidates.append(norm)

        deep_explorer = SiteExplorer(
            max_depth=self.max_depth,
            max_pages=self.max_pages,
            headless=self.headless,
            timeout_ms=self.timeout_ms,
            dynamic_wait_ms=self.dynamic_wait_ms,
            block_resources=self.block_resources,
            max_retries=self.max_retries,
        )

        for cand_url in unique_candidates[:8]:
            deep_result = deep_explorer.find_content(
                url=cand_url, content_type=content_type, search_term=search_term,
            )
            if deep_result.success:
                total_ms = (time.perf_counter() - t0) * 1000
                self._record_timing(url, "twophase_deep", total_ms)
                _debug(f"Two-phase: found in phase 2 ({total_ms:.0f}ms)")
                return deep_result

        total_ms = (time.perf_counter() - t0) * 1000
        self._record_timing(url, "twophase_fail", total_ms)
        return ExplorationResult(
            success=False,
            explored_pages=quick_result.explored_pages,
            error=f"Two-phase: no {content_type} found after {total_ms:.0f}ms",
        )

    # ── Strategy 6: Parallel Link Exploration ──────────────────────────
    def _explore_links_parallel(
        self,
        urls: list[str],
        content_type: str,
        max_workers: int = 3,
    ) -> list[PageInfo]:
        """Explore multiple URLs in parallel using static fallback (no browser)."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results: list[PageInfo] = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(self._fallback_static_scrape, u): u for u in urls[:max_workers * 3]}
            for future in as_completed(futures, timeout=10):
                try:
                    info = future.result()
                    if info:
                        results.append(info)
                except Exception:
                    pass
        _debug(f"Parallel scan: {len(results)}/{len(urls)} pages fetched")
        return results

    def explore(
        self,
        url: str,
        query: str,
        page: Optional[Any] = None,
        context: Optional[Any] = None,
        close_browser: bool = True,
    ) -> ExplorationResult:
        """Universal exploration - auto-detects intent from query."""
        intent = self._detect_intent_from_query(query)
        
        if intent == "contact":
            return self.find_form(url, intent="contact", page=page, context=context, close_browser=close_browser)
        elif intent in ["article", "product", "docs"]:
            return self.find_content(url, content_type=intent, page=page, context=context, close_browser=close_browser)
        else:
            return self._explore_generic(url, intent, query, page, context, close_browser)
    
    def _detect_intent_from_query(self, query: str) -> str:
        """Detect intent type from natural language query."""
        query_lower = query.lower()
        
        intent_keywords = {
            "contact": self.CONTACT_KEYWORDS,
            "article": self.ARTICLE_KEYWORDS,
            "product": self.PRODUCT_KEYWORDS,
            "docs": self.DOCS_KEYWORDS,
        }
        
        scores = {intent: sum(1 for kw in keywords if kw in query_lower) 
                  for intent, keywords in intent_keywords.items()}
        
        if scores:
            best = max(scores, key=scores.get)
            if scores[best] > 0:
                return best
        return "contact"
    
    def _explore_generic(self, url, intent, query, page, context, close_browser):
        """Generic exploration for any intent type."""
        from playwright.sync_api import sync_playwright
        
        should_close = False
        try:
            if page is None:
                p = sync_playwright().start()
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context()
                if self.block_resources:
                    self._setup_resource_blocking(context)
                page = context.new_page()
                should_close = True
            
            self._explored_urls = set()
            explored_pages = []
            
            result = self._explore_recursive(
                page=page, url=url, depth=0, intent=intent,
                explored_pages=explored_pages,
                base_domain=urlparse(url).netloc,
                search_term=query,
            )
            
            intent_keywords = {
                "contact": self.CONTACT_KEYWORDS,
                "article": self.ARTICLE_KEYWORDS,
                "product": self.PRODUCT_KEYWORDS,
                "docs": self.DOCS_KEYWORDS,
            }
            keywords = intent_keywords.get(intent, [])
            
            best_page = max(
                explored_pages,
                key=lambda p: self._score_for_intent(p, intent, keywords, query),
                default=None
            )
            
            if best_page:
                return ExplorationResult(
                    success=True, form_url=best_page.url,
                    form_page=best_page, explored_pages=explored_pages
                )
            return ExplorationResult(
                success=False, explored_pages=explored_pages,
                error=f"No content found for '{intent}'"
            )
        finally:
            if should_close and context:
                context.close()
    
    def _score_for_intent(self, page_info, intent, keywords, query):
        """Score page for intent."""
        score = 0.0
        url_lower = page_info.url.lower()
        title_lower = page_info.title.lower()
        for kw in keywords:
            if kw in url_lower:
                score += 2.0
            if kw in title_lower:
                score += 1.5
        if intent == "contact" and page_info.has_form:
            score += 3.0
        return score


def quick_find_content(
    url: str,
    content_type: str = "article",
    search_term: Optional[str] = None,
    headless: bool = True,
) -> Optional[str]:
    """
    Quick helper to find content URL without managing browser.
    
    Returns:
        URL of page with content, or None if not found
    """
    explorer = SiteExplorer(headless=headless)
    result = explorer.find_content(url=url, content_type=content_type, search_term=search_term)
    return result.form_url if result.success else None


def quick_find_form(
    url: str,
    intent: str = "contact",
    headless: bool = True,
) -> Optional[str]:
    """
    Quick helper to find form URL without managing browser.
    
    Returns:
        URL of page with form, or None if not found
    """
    explorer = SiteExplorer(headless=headless)
    result = explorer.find_form(url=url, intent=intent)
    return result.form_url if result.success else None
