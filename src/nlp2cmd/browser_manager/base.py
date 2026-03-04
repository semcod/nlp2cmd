"""Base classes for browser management."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class ConnectionStatus(Enum):
    """Status of browser connection attempt."""
    SUCCESS = "success"
    NO_CDP = "no_cdp"
    CONNECTION_FAILED = "connection_failed"
    CONTEXT_FAILED = "context_failed"
    PLAYWRIGHT_MISSING = "playwright_missing"
    ERROR = "error"


@dataclass
class BrowserConfig:
    """Configuration for browser connection."""
    cdp_ports: list[int] = field(default_factory=lambda: [9222, 9223, 9224, 9333])
    timeout_ms: int = 30000
    socket_timeout: float = 1.0
    
    # URL patterns for verification
    target_url: str = "https://huggingface.co/settings/tokens"
    target_pattern: str = "huggingface.co/settings/tokens"
    domain_pattern: str = "huggingface.co"
    login_pattern: str = "huggingface.co/login"


@dataclass
class BrowserConnectionResult:
    """Result of browser connection attempt."""
    success: bool = False
    status: ConnectionStatus = ConnectionStatus.ERROR
    browser: Optional[Any] = None
    page: Optional[Any] = None
    context: Optional[Any] = None
    browser_type: str = ""  # "chrome", "firefox", "chromium"
    cdp_port: int = 0
    actual_url: str = ""
    error: Optional[str] = None
    
    def close(self) -> None:
        """Clean up resources."""
        try:
            if self.page:
                self.page.close()
        except Exception:
            pass
        
        try:
            if self.context:
                self.context.close()
        except Exception:
            pass
        
        try:
            if self.browser:
                self.browser.close()
        except Exception:
            pass
