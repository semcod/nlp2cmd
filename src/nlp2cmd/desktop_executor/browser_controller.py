"""Browser Controller for Firefox operations."""

from __future__ import annotations
import time
import subprocess
import shutil
import logging
from typing import Optional

from .base import ActionResult, DesktopBackend

log = logging.getLogger("nlp2cmd.desktop_executor.browser")


class BrowserController:
    """Control Firefox browser via command-line interface."""
    
    def __init__(self) -> None:
        self._firefox_path: Optional[str] = None
    
    def open_tab(
        self,
        url: str,
        verbose: bool = False,
    ) -> ActionResult:
        """Open a new tab in existing Firefox instance.
        
        Args:
            url: URL to open
            verbose: Whether to log debug info
            
        Returns:
            ActionResult indicating success/failure
        """
        if not url.strip():
            return ActionResult.success_result()  # Nothing to open
        
        firefox_path = self._find_firefox()
        if not firefox_path:
            return ActionResult.failed_result("Firefox executable not found in PATH")
        
        try:
            if verbose:
                log.debug(f"Opening Firefox tab: {url}")
            
            # Try new-tab first (more reliable for existing instances)
            try:
                subprocess.run(
                    [firefox_path, "--new-tab", url],
                    check=True
                )
                return ActionResult.success_result()
            except Exception:
                # Fallback to new-window
                subprocess.run(
                    [firefox_path, "--new-window", url],
                    check=True
                )
                return ActionResult.success_result()
                
        except Exception as e:
            return ActionResult.failed_result(str(e))
    
    def check_session(
        self,
        service: str,
        wait_seconds: float = 2.0,
        verbose: bool = False,
    ) -> ActionResult:
        """Check browser session - informs user to verify login.
        
        In desktop mode we opened the URL in the user's real Firefox.
        We don't have a Playwright page to inspect, so just inform the user.
        
        Args:
            service: Service name being checked
            wait_seconds: Time to wait for user to check
            verbose: Whether to log debug info
            
        Returns:
            ActionResult with 'desktop_skipped' result
        """
        if verbose:
            log.debug(f"Checking session for {service}")
        
        print(f"\n  🔍 Strona {service} została otwarta w Twojej przeglądarce.")
        print(f"     Sprawdź, czy jesteś zalogowany. Jeśli nie — zaloguj się teraz.")
        
        time.sleep(wait_seconds)
        
        return ActionResult.success_result(result="desktop_skipped")
    
    def _find_firefox(self) -> Optional[str]:
        """Find Firefox executable path.
        
        Returns:
            Path to Firefox executable or None if not found
        """
        if self._firefox_path:
            return self._firefox_path
        
        self._firefox_path = shutil.which("firefox")
        return self._firefox_path
    
    def is_available(self) -> bool:
        """Check if Firefox is available.
        
        Returns:
            True if Firefox is installed
        """
        return self._find_firefox() is not None
