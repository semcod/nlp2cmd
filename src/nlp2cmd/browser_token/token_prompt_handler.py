"""Token prompt handler for user input."""

from __future__ import annotations
from typing import Optional
import logging

log = logging.getLogger("nlp2cmd.browser_token.prompt")


class TokenPromptHandler:
    """Handle interactive prompts for token input."""
    
    def __init__(
        self,
        prompt_text: str = "🔑 Paste HF_TOKEN here: ",
        separator_char: str = "=",
        separator_length: int = 60,
        header_text: str = "🔐 ENTER YOUR HF_TOKEN BELOW 🔐",
    ) -> None:
        self.prompt_text = prompt_text
        self.separator_char = separator_char
        self.separator_length = separator_length
        self.header_text = header_text
    
    def show_instructions(self, instructions: list[str]) -> None:
        """Display instructions to the user."""
        print("\n📋 Instructions:")
        for instruction in instructions:
            print(f"   {instruction}")
    
    def prompt_for_token(self) -> Optional[str]:
        """Prompt user for token input.
        
        Returns:
            Token string or None if input failed/cancelled
        """
        # Print visible separator to catch attention
        separator = self.separator_char * self.separator_length
        print(f"\n{separator}")
        print(self.header_text)
        print(separator)
        
        try:
            token = input(self.prompt_text).strip()
            print(separator)
            
            if token:
                log.debug("Token received (length: %d)", len(token))
                return token
            else:
                log.debug("No token entered")
                return None
                
        except EOFError:
            log.debug("EOFError (no input available)")
            return None
        except KeyboardInterrupt:
            log.debug("User cancelled (KeyboardInterrupt)")
            return None
        except Exception as e:
            log.error("Error getting input: %s", e)
            return None
    
    def prompt_with_cleanup(self, page: Optional[Any] = None) -> Optional[str]:
        """Prompt for token and handle cleanup on failure.
        
        Args:
            page: Optional Playwright page to close on failure
            
        Returns:
            Token string or None
        """
        try:
            token = self.prompt_for_token()
            
            if token:
                return token
            else:
                # Cleanup on no input
                self._cleanup_page(page)
                return None
                
        except Exception:
            self._cleanup_page(page)
            return None
    
    def _cleanup_page(self, page: Optional[Any]) -> None:
        """Close page if provided."""
        if page:
            try:
                page.close()
            except Exception:
                pass
