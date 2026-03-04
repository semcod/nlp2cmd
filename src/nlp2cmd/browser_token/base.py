"""Base classes for browser token retrieval."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BrowserTokenResult:
    """Result of browser token retrieval attempt."""
    success: bool
    token: str = ""
    browser_type: str = ""  # "firefox", "chromium"
    message: str = ""
    error: str = ""
    page_url: str = ""
    
    @property
    def failed(self) -> bool:
        """Check if retrieval failed."""
        return not self.success


@dataclass
class TokenConfig:
    """Configuration for token retrieval."""
    # URL configuration
    tokens_url: str = "https://huggingface.co/settings/tokens"
    login_url_pattern: str = "huggingface.co/login"
    domain_pattern: str = "huggingface.co"
    
    # UI strings
    token_name: str = "nlp2cmd"
    token_role: str = "read"
    
    # Instructions
    instructions: list[str] = field(default_factory=lambda: [
        "1. Login to Hugging Face if needed",
        "2. Click 'New token' button",
        "3. Set name: 'nlp2cmd'",
        "4. Select 'Read' role",
        "5. Click 'Generate token'",
        "6. Copy the token and paste it here",
    ])
    
    # Timeouts
    navigation_timeout: int = 30000
    input_timeout: int = 600  # seconds
    
    # Prompt text
    prompt_text: str = "🔑 Paste HF_TOKEN here: "
    separator_char: str = "="
    separator_length: int = 60
