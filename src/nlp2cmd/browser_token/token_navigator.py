"""Token navigator for handling page navigation to token pages."""

from __future__ import annotations
from typing import Any, Optional
from enum import Enum
import logging

log = logging.getLogger("nlp2cmd.browser_token.navigator")


class NavigationStatus(Enum):
    """Status of navigation attempt."""
    SUCCESS = "success"  # Reached exact target URL
    LOGIN_REQUIRED = "login_required"  # On login page
    DOMAIN_REACHED = "domain_reached"  # On correct domain but different path
    WRONG_DOMAIN = "wrong_domain"  # Completely different domain
    FAILED = "failed"  # Navigation failed


class TokenNavigator:
    """Navigate to token pages with URL verification."""
    
    def __init__(
        self,
        tokens_url: str = "https://huggingface.co/settings/tokens",
        login_url_pattern: str = "huggingface.co/login",
        domain_pattern: str = "huggingface.co",
        timeout: int = 30000,
    ) -> None:
        self.tokens_url = tokens_url
        self.login_url_pattern = login_url_pattern
        self.domain_pattern = domain_pattern
        self.timeout = timeout
    
    def navigate(self, page: Any) -> tuple[NavigationStatus, str, str]:
        """Navigate to tokens page and verify result.
        
        Args:
            page: Playwright page instance
            
        Returns:
            Tuple of (status, message, actual_url)
        """
        actual_url = ""
        
        try:
            log.debug("Navigating to %s", self.tokens_url)
            page.goto(self.tokens_url, timeout=self.timeout)
            actual_url = page.url
            
            return self._classify_result(actual_url)
            
        except Exception as e:
            log.warning("Navigation failed: %s", e)
            if actual_url:
                # Check if we at least got somewhere
                return self._classify_result(actual_url)
            return NavigationStatus.FAILED, f"Navigation failed: {e}", ""
    
    def _classify_result(self, actual_url: str) -> tuple[NavigationStatus, str, str]:
        """Classify navigation result based on actual URL."""
        # Success case
        if self.tokens_url in actual_url or actual_url.endswith("/settings/tokens"):
            return (
                NavigationStatus.SUCCESS,
                "Page loaded at correct URL",
                actual_url
            )
        
        # Login required
        if self.login_url_pattern in actual_url:
            return (
                NavigationStatus.LOGIN_REQUIRED,
                "Page loaded but requires login first",
                actual_url
            )
        
        # Domain reached but different path
        if self.domain_pattern in actual_url:
            return (
                NavigationStatus.DOMAIN_REACHED,
                "Page loaded on correct domain but different path",
                actual_url
            )
        
        # Wrong domain
        return (
            NavigationStatus.WRONG_DOMAIN,
            "Page loaded but unexpected URL",
            actual_url
        )
    
    def can_proceed(self, status: NavigationStatus) -> bool:
        """Check if we can proceed with token retrieval based on status."""
        return status in (
            NavigationStatus.SUCCESS,
            NavigationStatus.LOGIN_REQUIRED,
            NavigationStatus.DOMAIN_REACHED,
        )
