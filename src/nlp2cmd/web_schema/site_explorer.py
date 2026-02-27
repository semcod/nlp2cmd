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
import re
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen
import xml.etree.ElementTree as ET


@dataclass
class PageInfo:
    """Information about a discovered page."""
    url: str
    title: str = ""
    links: list[str] = field(default_factory=list)
    has_form: bool = False
    form_count: int = 0
    score: float = 0.0  # Relevance score for form/contact pages


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
        "manual", "instrukcja", "guide", "tutorial",
    ]
    
    # Keywords that suggest form fields
    FORM_FIELD_KEYWORDS = [
        "email", "e-mail", "telefon", "phone", "imię", "name",
        "nazwisko", "surname", "wiadomość", "message", "temat", "subject",
    ]
    
    def __init__(
        self,
        max_depth: int = 2,
        max_pages: int = 10,
        headless: bool = True,
        timeout_ms: int = 15000,
        dynamic_wait_ms: int = 3000,
    ):
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.dynamic_wait_ms = dynamic_wait_ms
        self._explored_urls: set[str] = set()
        self._max_sitemap_urls: int = 50
    
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
        
        should_close_browser = False
        should_close_context = False
        
        try:
            if page is None:
                p = sync_playwright().start()
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context()
                page = context.new_page()
                should_close_browser = True
                should_close_context = close_browser
            
            # Reset state
            self._explored_urls = set()
            explored_pages: list[PageInfo] = []
            
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
            
            print(f"DEBUG: Main page result: {main_page_result is not None}")
            if main_page_result:
                print(f"DEBUG: Main page URL: {main_page_result.url}")
                print(f"DEBUG: Main page has form: {main_page_result.has_form}")
                print(f"DEBUG: Main page links: {len(main_page_result.links)}")
            
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
                print(f"DEBUG: Exploring links from main page")
                # Sort links by contact relevance
                contact_links = []
                other_links = []
                
                for link in main_page_result.links[:12]:  # Check more links from main page
                    if len(self._explored_urls) >= self.max_pages:
                        break
                    
                    link_lower = link.lower()
                    if any(kw in link_lower for kw in ["kontakt", "contact", "formularz", "form"]):
                        contact_links.append(link)
                    else:
                        other_links.append(link)
                
                print(f"DEBUG: Found {len(contact_links)} contact links: {contact_links}")
                
                # Explore contact links first
                for link in contact_links[:5]:  # Check up to 5 contact links
                    if len(self._explored_urls) >= self.max_pages:
                        break
                    print(f"DEBUG: Exploring contact link: {link}")
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
                        print(f"DEBUG: Found contact form at: {link}")
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
        
        should_close_browser = False
        should_close_context = False
        
        try:
            if page is None:
                p = sync_playwright().start()
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context()
                page = context.new_page()
                should_close_browser = True
                should_close_context = close_browser
            
            # Reset state
            self._explored_urls = set()
            explored_pages: list[PageInfo] = []

            try:
                sitemap_urls = self._get_sitemap_urls(url)
            except Exception:
                sitemap_urls = []

            if sitemap_urls:
                if intent == "contact":
                    print(f"DEBUG: Found {len(sitemap_urls)} sitemap URLs, prioritizing contact links")
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
                    
                    print(f"DEBUG: Contact sitemap URLs: {contact_sitemap_urls[:3]}")
                    
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
                        if result and result.has_form:
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
                        if result and result.has_form:
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
                print(f"DEBUG: Using contact-aware exploration for {url}")
                # Use the same logic as find_content for contact
                main_page_result = self._explore_recursive(
                    page=page,
                    url=url,
                    depth=0,
                    intent=intent,
                    explored_pages=explored_pages,
                    base_domain=urlparse(url).netloc,
                )
                
                print(f"DEBUG: Main page result: {main_page_result is not None}")
                if main_page_result:
                    print(f"DEBUG: Main page URL: {main_page_result.url}")
                    print(f"DEBUG: Main page has form: {main_page_result.has_form}")
                    print(f"DEBUG: Main page links: {len(main_page_result.links)}")
                
                # For contact intent, always explore contact links first even if main page has form
                if main_page_result and main_page_result.links and len(explored_pages) < self.max_pages:
                    print(f"DEBUG: Exploring links from main page")
                    # Sort links by contact relevance
                    contact_links = []
                    other_links = []
                    
                    for link in main_page_result.links[:12]:  # Check more links from main page
                        if len(self._explored_urls) >= self.max_pages:
                            break
                        
                        link_lower = link.lower()
                        if any(kw in link_lower for kw in ["kontakt", "contact", "formularz", "form"]):
                            contact_links.append(link)
                        else:
                            other_links.append(link)
                    
                    print(f"DEBUG: Found {len(contact_links)} contact links: {contact_links}")
                    
                    # Explore contact links first
                    for link in contact_links[:5]:  # Check up to 5 contact links
                        if len(self._explored_urls) >= self.max_pages:
                            break
                        print(f"DEBUG: Exploring contact link: {link}")
                        result = self._explore_recursive(
                            page=page,
                            url=link,
                            depth=1,
                            intent=intent,
                            explored_pages=explored_pages,
                            base_domain=urlparse(url).netloc,
                        )
                        if result and result.has_form:
                            print(f"DEBUG: Found contact form at: {link}")
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
                        if result and result.has_form:
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
            if best_page and best_page.has_form:
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
            # Navigate and analyze page - wait longer for dynamic content
            page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
            page.wait_for_timeout(self.dynamic_wait_ms)  # Wait for JS frameworks
            
            # Try to dismiss popups first
            self._dismiss_popups(page)
            
            page_info = self._analyze_page(page, url)
            explored_pages.append(page_info)
            
            # If target content found, return immediately (except for contact - we want to check contact links first)
            if self._has_content_type(page_info, intent) and intent != "contact":
                return page_info
            
            # For contact intent, always explore contact links first even if main page has form
            if intent == "contact":
                # Check if this page has contact-related URL - if yes, return it
                url_lower = url.lower()
                if any(kw in url_lower for kw in ["kontakt", "contact", "formularz", "form"]):
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
                    if result and (result.has_form or self._has_content_type(result, intent)):
                        return result
            
            return None
            
        except Exception as e:
            # Log error but continue exploring
            return None
    
    def _analyze_page(self, page: Any, url: str, console: Optional[Any] = None) -> PageInfo:
        """Analyze a page for forms, iframes, and links."""
        info = PageInfo(url=url)
        
        try:
            # Get page title
            info.title = page.title() or ""
        except Exception:
            pass
        
        # Count form fields in main document
        try:
            inputs = page.query_selector_all('input:not([type="hidden"])')
            textareas = page.query_selector_all('textarea')
            selects = page.query_selector_all('select')
            
            info.form_count = len(inputs) + len(textareas) + len(selects)
            info.has_form = info.form_count > 0
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
    
    def _has_content_type(self, page_info: PageInfo, content_type: str) -> bool:
        """Check if page contains the target content type."""
        if content_type == "contact":
            return page_info.has_form
        elif content_type in ["article", "product", "docs"]:
            # For non-contact content, check if page has relevant content indicators
            return page_info.score > 1.0  # Has some relevant keywords
        return False
    
    def _find_best_content_candidate(
        self,
        pages: list[PageInfo],
        content_type: str,
        search_term: Optional[str] = None,
    ) -> Optional[PageInfo]:
        """Find the best page with content based on scores."""
        # Filter pages with relevant content
        relevant_pages = [p for p in pages if self._has_content_type(p, content_type)]
        if not relevant_pages:
            return None
        
        # If search term provided, prioritize pages containing it
        if search_term:
            for page in relevant_pages:
                try:
                    page_content = f"{page.title} {page.url}".lower()
                    if search_term.lower() in page_content:
                        page.score += 2.0  # Boost for matching search term
                except Exception:
                    pass
        
        # Sort by score descending
        relevant_pages.sort(key=lambda p: p.score, reverse=True)
        return relevant_pages[0]

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
            contact_urls = [p for p in form_pages if any(
                kw in p.url.lower() for kw in ["kontakt", "contact", "formularz", "form"]
            )]
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
