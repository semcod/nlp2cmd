"""HuggingFace token retriever - main orchestrator."""

from __future__ import annotations
from typing import Optional, Any
import logging

from .base import BrowserTokenResult, TokenConfig
from .browser_launcher import BrowserLauncher
from .token_navigator import TokenNavigator, NavigationStatus
from .token_prompt_handler import TokenPromptHandler

log = logging.getLogger("nlp2cmd.browser_token.hf")


class HFTokenRetriever:
    """Main orchestrator for retrieving HuggingFace tokens via browser."""
    
    def __init__(self, config: Optional[TokenConfig] = None) -> None:
        self.config = config or TokenConfig()
        self.launcher = BrowserLauncher(headless=False)
        self.navigator = TokenNavigator(
            tokens_url=self.config.tokens_url,
            login_url_pattern=self.config.login_url_pattern,
            domain_pattern=self.config.domain_pattern,
            timeout=self.config.navigation_timeout,
        )
        self.prompt_handler = TokenPromptHandler(
            prompt_text=self.config.prompt_text,
            separator_char=self.config.separator_char,
            separator_length=self.config.separator_length,
        )
    
    def retrieve(self) -> BrowserTokenResult:
        """Retrieve HF token via browser automation.
        
        Returns:
            BrowserTokenResult with success status and token (if successful)
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return BrowserTokenResult(
                success=False,
                error="Playwright not installed"
            )
        
        try:
            with sync_playwright() as p:
                # Launch browser
                try:
                    browser, browser_type = self.launcher.launch(p)
                except RuntimeError as e:
                    return BrowserTokenResult(
                        success=False,
                        error=str(e)
                    )
                
                # Create context and page
                context, page = self.launcher.create_context_and_page(browser)
                
                # Navigate to tokens page
                status, message, actual_url = self.navigator.navigate(page)
                
                if not self.navigator.can_proceed(status):
                    return BrowserTokenResult(
                        success=False,
                        browser_type=browser_type,
                        message=message,
                        page_url=actual_url,
                        error=f"Cannot proceed: {message}"
                    )
                
                # Show instructions and get token
                self.prompt_handler.show_instructions(self.config.instructions)
                
                token = self.prompt_handler.prompt_with_cleanup(page)
                
                if token:
                    # Try to close page gracefully
                    try:
                        page.close()
                    except Exception:
                        pass
                    
                    return BrowserTokenResult(
                        success=True,
                        token=token,
                        browser_type=browser_type,
                        message="Token retrieved successfully",
                        page_url=actual_url
                    )
                else:
                    return BrowserTokenResult(
                        success=False,
                        browser_type=browser_type,
                        message="No token entered by user",
                        page_url=actual_url,
                        error="User cancelled or no input"
                    )
                    
        except Exception as e:
            log.error("Token retrieval failed: %s", e)
            return BrowserTokenResult(
                success=False,
                error=str(e)
            )
        finally:
            # Ensure cleanup
            self.launcher.cleanup()
