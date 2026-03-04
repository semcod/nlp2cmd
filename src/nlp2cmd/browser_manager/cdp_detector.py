"""CDP Detector for finding Chrome DevTools Protocol ports."""

from __future__ import annotations
import socket
import logging
from typing import Any, Optional

from .base import BrowserConfig

log = logging.getLogger("nlp2cmd.browser_manager.cdp")


class CdpDetector:
    """Detect and verify CDP ports for browser connections."""
    
    def __init__(self, config: Optional[BrowserConfig] = None) -> None:
        self.config = config or BrowserConfig()
    
    def find_cdp_port(
        self,
        verbose: bool = False,
        console: Optional[Any] = None,
    ) -> Optional[int]:
        """Find first available CDP port.
        
        Args:
            verbose: Whether to log detailed output
            console: Optional Rich console for formatted output
            
        Returns:
            Port number if found, None otherwise
        """
        if console and verbose:
            console.print("[dim]   [Stage 1/3] Checking for existing browser...[/dim]")
        
        for port in self.config.cdp_ports:
            if console and verbose:
                console.print(f"[dim]     Checking port {port}...[/dim]")
            
            if self._check_port(port):
                if console and verbose:
                    console.print(f"[green]     ✓ Found browser on port {port}[/green]")
                return port
            else:
                if console and verbose:
                    console.print(f"[dim]     Port {port}: not available[/dim]")
        
        if console and verbose:
            console.print("[dim]     ℹ No existing browser with CDP found[/dim]")
            console.print("[dim]       Tip: Run 'firefox --remote-debugging-port=9222' first[/dim]")
        
        return None
    
    def _check_port(self, port: int) -> bool:
        """Check if a specific port is open and responds to CDP.
        
        Args:
            port: Port number to check
            
        Returns:
            True if port is open and responds to CDP
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.socket_timeout)
            result = sock.connect_ex(("localhost", port))
            sock.close()
            
            return result == 0
        except Exception as e:
            log.debug("Port %d check failed: %s", port, e)
            return False
    
    def verify_cdp_protocol(
        self,
        port: int,
        timeout: float = 3.0,
    ) -> bool:
        """Verify that port is actually a CDP endpoint.
        
        Args:
            port: Port to verify
            timeout: HTTP request timeout
            
        Returns:
            True if port responds with valid CDP protocol
        """
        try:
            import urllib.request
            response = urllib.request.urlopen(
                f"http://localhost:{port}/json/version",
                timeout=timeout
            )
            cdp_info = response.read().decode('utf-8')
            return 'Browser' in cdp_info or 'Protocol-Version' in cdp_info
        except Exception as e:
            log.debug("CDP protocol verification failed for port %d: %s", port, e)
            return False
