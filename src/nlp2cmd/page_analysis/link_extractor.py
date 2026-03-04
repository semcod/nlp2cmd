"""Link extractor for extracting and normalizing page links."""

from __future__ import annotations
from typing import Any, Optional
from urllib.parse import urljoin, urlparse
import logging

log = logging.getLogger("nlp2cmd.page_analysis.links")


class LinkExtractor:
    """Extract and normalize links from page."""
    
    EXCLUDED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mp3', '.zip'}
    
    def __init__(self, max_links: int = 10) -> None:
        self.max_links = max_links
    
    def extract(self, page: Any, base_url: str) -> list[str]:
        """Extract links from page.
        
        Args:
            page: Playwright page object
            base_url: Base URL for resolving relative links
            
        Returns:
            List of normalized absolute URLs
        """
        links: list[str] = []
        
        try:
            # Try different selector groups in order of priority
            selector_groups = [
                'nav a[href], header a[href], [role="navigation"] a[href]',
                'footer a[href]',
                'a[href]',
            ]
            
            base_domain = urlparse(base_url).netloc
            
            for selector in selector_groups:
                try:
                    link_elements = page.query_selector_all(selector)
                    for link in link_elements:
                        try:
                            href = link.get_attribute('href')
                            if href:
                                absolute_url = urljoin(base_url, href)
                                parsed = urlparse(absolute_url)
                                
                                # Only include same-domain links
                                if parsed.netloc == base_domain:
                                    # Exclude file extensions
                                    path_lower = parsed.path.lower()
                                    if not any(path_lower.endswith(ext) for ext in self.EXCLUDED_EXTENSIONS):
                                        links.append(absolute_url)
                        except Exception:
                            continue
                except Exception:
                    continue
                    
        except Exception as e:
            log.debug("Link extraction failed: %s", e)
        
        # Deduplicate and limit
        return self._deduplicate_and_limit(links)
    
    def _deduplicate_and_limit(self, links: list[str]) -> list[str]:
        """Remove duplicates and limit number of links."""
        seen = set()
        unique_links = []
        
        for link in links:
            normalized = self._normalize_url(link)
            if normalized not in seen:
                seen.add(normalized)
                unique_links.append(normalized)
                
                if len(unique_links) >= self.max_links:
                    break
        
        return unique_links
    
    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize URL for comparison."""
        # Remove fragment
        url = url.split('#')[0]
        # Remove trailing slash
        url = url.rstrip('/')
        return url
