"""Browser Connector for Playwright CDP connections."""

from __future__ import annotations
import logging
from typing import Any, Optional

from .base import BrowserConfig, BrowserConnectionResult, ConnectionStatus

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover
    sync_playwright = None  # type: ignore[assignment]

log = logging.getLogger("nlp2cmd.browser_manager.connector")


class BrowserConnector:
    """Connect to browsers via Playwright CDP protocol."""
    
    def __init__(self, config: Optional[BrowserConfig] = None) -> None:
        self.config = config or BrowserConfig()
    
    def connect(
        self,
        port: int,
        verbose: bool = False,
        console: Optional[Any] = None,
    ) -> BrowserConnectionResult:
        """Connect to browser on specified CDP port.
        
        Args:
            port: CDP port to connect to
            verbose: Whether to log detailed output
            console: Optional Rich console for formatted output
            
        Returns:
            BrowserConnectionResult with connection details
        """
        result = BrowserConnectionResult(cdp_port=port)
        
        if sync_playwright is None:
            result.status = ConnectionStatus.PLAYWRIGHT_MISSING
            result.error = "Playwright not installed"
            if console and verbose:
                console.print("[red]     ✗ Playwright not installed[/red]")
            return result
        
        if console and verbose:
            console.print(f"[cyan]     → Connecting via Playwright to port {port}...[/cyan]")
        
        try:
            with sync_playwright() as p:
                # Try Chrome/Chromium first
                browser, browser_type = self._try_connect_chrome(p, port, verbose, console)
                
                if not browser:
                    # Try Firefox as fallback
                    browser, browser_type = self._try_connect_firefox(p, port, verbose, console)
                
                if not browser:
                    result.status = ConnectionStatus.CONNECTION_FAILED
                    result.error = "Failed to connect to any browser type"
                    return result
                
                result.browser = browser
                result.browser_type = browser_type
                
                # Create context and page
                if console and verbose:
                    console.print(f"[dim]     Creating browser context...[/dim]")
                
                try:
                    context = browser.new_context()
                    page = context.new_page()
                    
                    result.context = context
                    result.page = page
                    result.success = True
                    result.status = ConnectionStatus.SUCCESS
                    
                    if console and verbose:
                        console.print(f"[green]     ✓ Browser context created[/green]")
                except Exception as e:
                    result.status = ConnectionStatus.CONTEXT_FAILED
                    result.success = False
                    result.error = f"Failed to create context: {e}"
                    if console and verbose:
                        console.print(f"[red]     ✗ Failed to create browser context: {e}[/red]")
                    return result
                
                return result
                
        except ImportError as e:
            # Specific case when Playwright is not installed
            result.status = ConnectionStatus.PLAYWRIGHT_MISSING
            result.success = False
            result.error = str(e)
            if console and verbose:
                console.print(f"[red]     ✗ Playwright not installed: {e}[/red]")
            return result
        except Exception as e:
            result.status = ConnectionStatus.ERROR
            result.success = False
            result.error = str(e)
            if console and verbose:
                console.print(f"[red]     ✗ CDP connection error: {e}[/red]")
            return result
    
    def _try_connect_chrome(
        self,
        playwright: Any,
        port: int,
        verbose: bool,
        console: Optional[Any],
    ) -> tuple[Optional[Any], str]:
        """Try to connect to Chrome/Chromium browser."""
        try:
            browser = playwright.chromium.connect_over_cdp(f"http://localhost:{port}")
            if console and verbose:
                console.print(f"[green]     ✓ Connected to Chrome/Chromium via CDP[/green]")
            return browser, "chromium"
        except Exception as chrome_err:
            if console and verbose:
                console.print(f"[dim]     Chromium CDP failed: {str(chrome_err)[:50]}...[/dim]")
            return None, ""
    
    def _try_connect_firefox(
        self,
        playwright: Any,
        port: int,
        verbose: bool,
        console: Optional[Any],
    ) -> tuple[Optional[Any], str]:
        """Try to connect to Firefox browser."""
        try:
            browser = playwright.firefox.connect_over_cdp(f"http://localhost:{port}")
            if console and verbose:
                console.print(f"[green]     ✓ Connected to Firefox via CDP[/green]")
            return browser, "firefox"
        except Exception as firefox_err:
            if console and verbose:
                console.print(f"[red]     ✗ CDP connection failed for both browsers[/red]")
            return None, ""
