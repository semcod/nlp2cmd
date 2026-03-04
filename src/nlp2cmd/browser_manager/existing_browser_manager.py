"""Existing Browser Manager - orchestrator for connecting to existing browsers."""

from __future__ import annotations
import logging
from typing import Any, Optional

from .base import BrowserConfig, BrowserConnectionResult, ConnectionStatus
from .cdp_detector import CdpDetector
from .browser_connector import BrowserConnector
from .token_navigator import TokenNavigator, NavigationStatus

log = logging.getLogger("nlp2cmd.browser_manager.existing")


class ExistingBrowserManager:
    """Orchestrator for connecting to existing browser via CDP.
    
    Coordinates CDP detection, browser connection, and navigation.
    """
    
    def __init__(self, config: Optional[BrowserConfig] = None) -> None:
        self.config = config or BrowserConfig()
        self.cdp_detector = CdpDetector(self.config)
        self.browser_connector = BrowserConnector(self.config)
        self.token_navigator = TokenNavigator(self.config)
    
    def connect_and_navigate(
        self,
        verbose: bool = True,
        console: Optional[Any] = None,
    ) -> BrowserConnectionResult:
        """Find existing browser, connect, and navigate to token page.
        
        Args:
            verbose: Whether to log detailed output
            console: Optional Rich console for formatted output
            
        Returns:
            BrowserConnectionResult with connection details and page
        """
        # Stage 1: Find CDP port
        port = self.cdp_detector.find_cdp_port(verbose=verbose, console=console)
        
        if not port:
            result = BrowserConnectionResult()
            result.status = ConnectionStatus.NO_CDP
            result.error = "No existing browser with CDP found"
            return result
        
        # Stage 2: Connect to browser
        result = self.browser_connector.connect(port, verbose=verbose, console=console)
        
        if not result.success:
            return result
        
        if not result.page:
            result.status = ConnectionStatus.CONTEXT_FAILED
            result.error = "Browser connected but page creation failed"
            return result
        
        # Stage 3: Navigate to tokens page
        nav_status, actual_url = self.token_navigator.navigate(
            result.page, verbose=verbose, console=console
        )
        
        result.actual_url = actual_url
        
        if nav_status == NavigationStatus.FAILED:
            result.success = False
            result.error = f"Navigation failed, last URL: {actual_url}"
        elif nav_status == NavigationStatus.WRONG_PAGE:
            # Still proceed - user can navigate manually
            log.debug("Navigated to unexpected URL: %s", actual_url)
        
        return result
    
    def get_token_interactive(
        self,
        result: BrowserConnectionResult,
        verbose: bool = True,
        console: Optional[Any] = None,
    ) -> Optional[str]:
        """Get token from user via interactive prompt.
        
        Args:
            result: BrowserConnectionResult with connected page
            verbose: Whether to log detailed output
            console: Optional Rich console for formatted output
            
        Returns:
            Token string if entered, None otherwise
        """
        if not result.page:
            return None
        
        if console and verbose:
            console.print(f"[dim]       [Token Step 1/4] Navigated to: {result.actual_url}[/dim]")
            console.print(f"[cyan]       [Token Step 2/4] Showing instructions:[/cyan]")
            console.print("         1. Login to Hugging Face if needed")
            console.print("         2. Click 'New token' button")
            console.print("         3. Set name: 'nlp2cmd'")
            console.print("         4. Select 'Read' role")
            console.print("         5. Click 'Generate token'")
            console.print("         6. Copy the token and paste it here")
        else:
            print("\n📋 Instructions:")
            print("   1. Login to Hugging Face if needed")
            print("   2. Click 'New token' button")
            print("   3. Set name: 'nlp2cmd'")
            print("   4. Select 'Read' role")
            print("   5. Click 'Generate token'")
            print("   6. Copy the token and paste it here")
        
        if console and verbose:
            console.print(f"[cyan]       [Token Step 3/4] Waiting for user input...[/cyan]")
            console.print(f"[bold yellow]       ⚠️  CHECK YOUR TERMINAL - waiting for token input![/bold yellow]")
        
        try:
            # Print visible separator
            print("\n" + "="*60)
            print("🔐 ENTER YOUR HF_TOKEN BELOW 🔐")
            print("="*60)
            
            token = input("🔑 Paste HF_TOKEN here: ").strip()
            
            print("="*60)
            
            if console and verbose:
                console.print(f"[dim]       Input received: {'Yes' if token else 'No'}[/dim]")
            
            if token:
                if console and verbose:
                    console.print(f"[cyan]       [Token Step 4/4] Closing browser page...[/cyan]")
                
                try:
                    result.close()
                    if console and verbose:
                        console.print(f"[green]       ✓ Browser connection closed[/green]")
                except Exception as e:
                    if console and verbose:
                        console.print(f"[dim]       Note: Could not close cleanly: {e}[/dim]")
                
                return token
            else:
                if console and verbose:
                    console.print(f"[yellow]       ⚠ No token entered[/yellow]")
                    
        except EOFError:
            if console and verbose:
                console.print(f"[red]       ✗ EOFError (no input available)[/red]")
        except KeyboardInterrupt:
            if console and verbose:
                console.print(f"[yellow]       ⚠ User cancelled (KeyboardInterrupt)[/yellow]")
        except Exception as e:
            if console and verbose:
                console.print(f"[red]       ✗ Error getting input: {e}[/red]")
        
        # Cleanup on failure
        result.close()
        return None
