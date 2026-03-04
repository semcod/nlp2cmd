"""Browser launcher with Firefox/Chromium fallback."""

from __future__ import annotations
from typing import Any, Optional
import logging

log = logging.getLogger("nlp2cmd.browser_token.launcher")


class BrowserLauncher:
    """Launch browser with automatic fallback from Firefox to Chromium."""
    
    def __init__(self, headless: bool = False) -> None:
        self.headless = headless
        self.browser_type: str = ""
        self._playwright: Any = None
        self._browser: Any = None
    
    def launch(self, p: Any) -> tuple[Any, str]:
        """Launch browser, trying Firefox first then Chromium.
        
        Args:
            p: Playwright instance (from sync_playwright())
            
        Returns:
            Tuple of (browser instance, browser_type string)
            
        Raises:
            RuntimeError: If both browsers fail to launch
        """
        # Try Firefox first (better privacy)
        self.browser_type = "firefox"
        try:
            log.debug("Launching Firefox...")
            browser = p.firefox.launch(headless=self.headless)
            log.debug("Firefox launched successfully")
            self._browser = browser
            return browser, self.browser_type
        except Exception as firefox_err:
            log.debug("Firefox failed: %s", firefox_err)
            
            # Fallback to Chromium
            log.debug("Trying Chromium...")
            try:
                browser = p.chromium.launch(headless=self.headless)
                self.browser_type = "chromium"
                log.debug("Chromium launched successfully")
                self._browser = browser
                return browser, self.browser_type
            except Exception as chromium_err:
                log.error("Both browsers failed - Firefox: %s, Chromium: %s", 
                         firefox_err, chromium_err)
                raise RuntimeError(
                    f"Failed to launch any browser. "
                    f"Firefox error: {firefox_err}, "
                    f"Chromium error: {chromium_err}"
                )
    
    def create_context_and_page(self, browser: Any) -> tuple[Any, Any]:
        """Create browser context and new page.
        
        Args:
            browser: Browser instance from launch()
            
        Returns:
            Tuple of (context, page)
        """
        context = browser.new_context()
        page = context.new_page()
        return context, page
    
    def cleanup(self) -> None:
        """Cleanup browser resources."""
        if self._browser:
            try:
                self._browser.close()
            except Exception as e:
                log.debug("Error closing browser: %s", e)
            finally:
                self._browser = None
