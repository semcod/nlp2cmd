"""Token Navigator for navigating to HF token pages."""

from __future__ import annotations
from enum import Enum
import logging
from typing import Any, Optional

from .base import BrowserConfig

log = logging.getLogger("nlp2cmd.browser_manager.navigator")


class NavigationStatus(Enum):
    """Status of navigation attempt."""
    SUCCESS = "success"
    LOGIN_REQUIRED = "login_required"
    WRONG_PAGE = "wrong_page"
    FAILED = "failed"


class TokenNavigator:
    """Navigate to HuggingFace token settings page."""
    
    def __init__(self, config: Optional[BrowserConfig] = None) -> None:
        self.config = config or BrowserConfig()
    
    def navigate(
        self,
        page: Any,
        verbose: bool = False,
        console: Optional[Any] = None,
    ) -> tuple[NavigationStatus, str]:
        """Navigate to HF tokens page and verify.
        
        Args:
            page: Playwright page object
            verbose: Whether to log detailed output
            console: Optional Rich console for formatted output
            
        Returns:
            Tuple of (NavigationStatus, actual_url)
        """
        if console and verbose:
            console.print(f"[cyan]     → Navigating to huggingface.co...[/cyan]")
        
        actual_url = ""
        
        try:
            page.goto(self.config.target_url, timeout=self.config.timeout_ms)
            actual_url = page.url
            
            # Verify we reached the expected page
            if self.config.target_pattern in actual_url:
                if console and verbose:
                    console.print(f"[green]     ✓ Page loaded at correct URL[/green]")
                return NavigationStatus.SUCCESS, actual_url
            
            elif self.config.login_pattern in actual_url:
                # This is expected if not logged in
                if console and verbose:
                    console.print(f"[yellow]     ⚠ Page loaded but requires login first[/yellow]")
                    console.print(f"[dim]       URL: {actual_url}[/dim]")
                return NavigationStatus.LOGIN_REQUIRED, actual_url
            
            elif self.config.domain_pattern in actual_url:
                # On HF domain but different path
                if console and verbose:
                    console.print(f"[yellow]     ⚠ Page loaded on HF domain but different path[/yellow]")
                    console.print(f"[dim]       URL: {actual_url}[/dim]")
                return NavigationStatus.SUCCESS, actual_url
            
            else:
                # Unexpected URL
                if console and verbose:
                    console.print(f"[red]     ✗ Page loaded but unexpected URL[/red]")
                    console.print(f"[dim]       Expected: {self.config.target_pattern}[/dim]")
                    console.print(f"[dim]       Actual: {actual_url}[/dim]")
                return NavigationStatus.WRONG_PAGE, actual_url
                
        except Exception as e:
            if console and verbose:
                console.print(f"[red]     ✗ Navigation failed: {e}[/red]")
                if actual_url:
                    console.print(f"[dim]       Last URL: {actual_url}[/dim]")
            log.debug("Navigation failed: %s", e)
            return NavigationStatus.FAILED, actual_url
    
    def is_valid_destination(self, url: str) -> bool:
        """Check if URL is a valid navigation destination.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is on HF domain
        """
        return self.config.domain_pattern in url
