"""Browser Manager Package — Modular browser connection and token retrieval.

This package provides modular components for connecting to existing browsers
via CDP, launching new browser instances, and navigating to token pages.
"""

from .base import BrowserConnectionResult, BrowserConfig, ConnectionStatus
from .cdp_detector import CdpDetector
from .browser_connector import BrowserConnector
from .token_navigator import TokenNavigator, NavigationStatus
from .existing_browser_manager import ExistingBrowserManager

__all__ = [
    "BrowserConnectionResult",
    "BrowserConfig",
    "ConnectionStatus",
    "CdpDetector",
    "BrowserConnector",
    "TokenNavigator",
    "NavigationStatus",
    "ExistingBrowserManager",
]
