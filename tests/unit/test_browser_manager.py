"""Tests for browser_manager package."""

import pytest
from unittest.mock import MagicMock, patch
import socket

from nlp2cmd.browser_manager import (
    BrowserConnectionResult,
    BrowserConfig,
    ConnectionStatus,
    CdpDetector,
    BrowserConnector,
    TokenNavigator,
    NavigationStatus,
    ExistingBrowserManager,
)


class TestBrowserConfig:
    """Test BrowserConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = BrowserConfig()
        assert config.cdp_ports == [9222, 9223, 9224, 9333]
        assert config.timeout_ms == 30000
        assert config.target_url == "https://huggingface.co/settings/tokens"
    
    def test_custom_values(self):
        """Test custom configuration."""
        config = BrowserConfig(cdp_ports=[8080], timeout_ms=5000)
        assert config.cdp_ports == [8080]
        assert config.timeout_ms == 5000


class TestBrowserConnectionResult:
    """Test BrowserConnectionResult dataclass."""
    
    def test_default_creation(self):
        """Test creating empty result."""
        result = BrowserConnectionResult()
        assert result.success is False
        assert result.status == ConnectionStatus.ERROR
        assert result.browser is None
        assert result.page is None
    
    def test_close_method(self):
        """Test cleanup method."""
        result = BrowserConnectionResult()
        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_browser = MagicMock()
        
        result.page = mock_page
        result.context = mock_context
        result.browser = mock_browser
        
        result.close()
        
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()


class TestCdpDetector:
    """Test CdpDetector class."""
    
    def test_init_with_defaults(self):
        """Test initialization with default config."""
        detector = CdpDetector()
        assert detector.config.cdp_ports == [9222, 9223, 9224, 9333]
    
    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = BrowserConfig(cdp_ports=[8080])
        detector = CdpDetector(config)
        assert detector.config.cdp_ports == [8080]
    
    @patch('socket.socket')
    def test_check_port_open(self, mock_socket_class):
        """Test port check when port is open."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket
        
        detector = CdpDetector()
        result = detector._check_port(9222)
        
        assert result is True
        mock_socket.settimeout.assert_called_once()
        mock_socket.connect_ex.assert_called_once_with(("localhost", 9222))
    
    @patch('socket.socket')
    def test_check_port_closed(self, mock_socket_class):
        """Test port check when port is closed."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 1
        mock_socket_class.return_value = mock_socket
        
        detector = CdpDetector()
        result = detector._check_port(9222)
        
        assert result is False
    
    @patch('socket.socket')
    def test_find_cdp_port_success(self, mock_socket_class):
        """Test finding CDP port when available."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket
        
        detector = CdpDetector()
        port = detector.find_cdp_port(verbose=False)
        
        assert port == 9222
    
    @patch('socket.socket')
    def test_find_cdp_port_none_available(self, mock_socket_class):
        """Test finding CDP port when none available."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 1
        mock_socket_class.return_value = mock_socket
        
        detector = CdpDetector()
        port = detector.find_cdp_port(verbose=False)
        
        assert port is None
    
    @patch('urllib.request.urlopen')
    def test_verify_cdp_protocol_success(self, mock_urlopen):
        """Test CDP protocol verification success."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"Browser": "Chrome"}'
        mock_urlopen.return_value = mock_response
        
        detector = CdpDetector()
        result = detector.verify_cdp_protocol(9222)
        
        assert result is True
    
    @patch('urllib.request.urlopen')
    def test_verify_cdp_protocol_failure(self, mock_urlopen):
        """Test CDP protocol verification failure."""
        mock_urlopen.side_effect = Exception("Connection refused")
        
        detector = CdpDetector()
        result = detector.verify_cdp_protocol(9222)
        
        assert result is False


class TestBrowserConnector:
    """Test BrowserConnector class."""
    
    def test_init_with_defaults(self):
        """Test initialization."""
        connector = BrowserConnector()
        assert connector.config is not None
    
    @patch('nlp2cmd.browser_manager.browser_connector.sync_playwright')
    def test_connect_playwright_missing(self, mock_sync_playwright):
        """Test connection when Playwright not installed."""
        mock_sync_playwright.side_effect = ImportError("No module named 'playwright'")
        
        connector = BrowserConnector()
        result = connector.connect(9222, verbose=False)
        
        assert result.status == ConnectionStatus.PLAYWRIGHT_MISSING
        assert result.success is False
    
    @patch('nlp2cmd.browser_manager.browser_connector.sync_playwright')
    def test_connect_chrome_success(self, mock_sync_playwright):
        """Test successful Chrome connection."""
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        
        mock_playwright.chromium.connect_over_cdp.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        mock_sync_playwright.return_value.__enter__ = MagicMock(return_value=mock_playwright)
        mock_sync_playwright.return_value.__exit__ = MagicMock(return_value=False)
        
        connector = BrowserConnector()
        result = connector.connect(9222, verbose=False)
        
        assert result.success is True
        assert result.status == ConnectionStatus.SUCCESS
        assert result.browser_type == "chromium"
        assert result.browser == mock_browser
        assert result.page == mock_page
    
    @patch('nlp2cmd.browser_manager.browser_connector.sync_playwright')
    def test_connect_firefox_fallback(self, mock_sync_playwright):
        """Test Firefox fallback when Chrome fails."""
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        
        # Chrome fails
        mock_playwright.chromium.connect_over_cdp.side_effect = Exception("Chrome not found")
        # Firefox succeeds
        mock_playwright.firefox.connect_over_cdp.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        mock_sync_playwright.return_value.__enter__ = MagicMock(return_value=mock_playwright)
        mock_sync_playwright.return_value.__exit__ = MagicMock(return_value=False)
        
        connector = BrowserConnector()
        result = connector.connect(9222, verbose=False)
        
        assert result.success is True
        assert result.browser_type == "firefox"
    
    @patch('nlp2cmd.browser_manager.browser_connector.sync_playwright')
    def test_connect_context_failure(self, mock_sync_playwright):
        """Test handling when context creation fails."""
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        
        mock_playwright.chromium.connect_over_cdp.return_value = mock_browser
        mock_browser.new_context.side_effect = Exception("Context failed")
        
        mock_sync_playwright.return_value.__enter__ = MagicMock(return_value=mock_playwright)
        mock_sync_playwright.return_value.__exit__ = MagicMock(return_value=False)
        
        connector = BrowserConnector()
        result = connector.connect(9222, verbose=False)
        
        assert result.success is False
        assert result.status == ConnectionStatus.CONTEXT_FAILED


class TestTokenNavigator:
    """Test TokenNavigator class."""
    
    def test_init_with_defaults(self):
        """Test initialization."""
        navigator = TokenNavigator()
        assert navigator.config.target_url == "https://huggingface.co/settings/tokens"
    
    def test_navigate_success(self):
        """Test successful navigation to tokens page."""
        mock_page = MagicMock()
        mock_page.url = "https://huggingface.co/settings/tokens"
        
        navigator = TokenNavigator()
        status, url = navigator.navigate(mock_page, verbose=False)
        
        assert status == NavigationStatus.SUCCESS
        assert url == "https://huggingface.co/settings/tokens"
        mock_page.goto.assert_called_once_with(
            "https://huggingface.co/settings/tokens",
            timeout=30000
        )
    
    def test_navigate_login_required(self):
        """Test navigation when login is required."""
        mock_page = MagicMock()
        mock_page.url = "https://huggingface.co/login?next=/settings/tokens"
        
        navigator = TokenNavigator()
        status, url = navigator.navigate(mock_page, verbose=False)
        
        assert status == NavigationStatus.LOGIN_REQUIRED
        assert "huggingface.co/login" in url
    
    def test_navigate_wrong_page(self):
        """Test navigation to unexpected URL."""
        mock_page = MagicMock()
        mock_page.url = "https://example.com"
        
        navigator = TokenNavigator()
        status, url = navigator.navigate(mock_page, verbose=False)
        
        assert status == NavigationStatus.WRONG_PAGE
        assert url == "https://example.com"
    
    def test_navigate_failure(self):
        """Test navigation when goto fails."""
        mock_page = MagicMock()
        mock_page.goto.side_effect = Exception("Navigation timeout")
        
        navigator = TokenNavigator()
        status, url = navigator.navigate(mock_page, verbose=False)
        
        assert status == NavigationStatus.FAILED
    
    def test_is_valid_destination(self):
        """Test URL validation."""
        navigator = TokenNavigator()
        
        assert navigator.is_valid_destination("https://huggingface.co/settings/tokens") is True
        assert navigator.is_valid_destination("https://huggingface.co/login") is True
        assert navigator.is_valid_destination("https://example.com") is False


class TestExistingBrowserManager:
    """Test ExistingBrowserManager orchestrator."""
    
    def test_init(self):
        """Test initialization creates components."""
        manager = ExistingBrowserManager()
        assert manager.cdp_detector is not None
        assert manager.browser_connector is not None
        assert manager.token_navigator is not None
    
    @patch.object(CdpDetector, 'find_cdp_port')
    def test_connect_no_cdp(self, mock_find_port):
        """Test when no CDP port is found."""
        mock_find_port.return_value = None
        
        manager = ExistingBrowserManager()
        result = manager.connect_and_navigate(verbose=False)
        
        assert result.success is False
        assert result.status == ConnectionStatus.NO_CDP
    
    @patch.object(CdpDetector, 'find_cdp_port')
    @patch.object(BrowserConnector, 'connect')
    def test_connect_success(self, mock_connect, mock_find_port):
        """Test successful connection flow."""
        mock_find_port.return_value = 9222
        
        mock_result = BrowserConnectionResult(
            success=True,
            status=ConnectionStatus.SUCCESS,
            browser=MagicMock(),
            page=MagicMock(),
        )
        mock_connect.return_value = mock_result
        
        manager = ExistingBrowserManager()
        result = manager.connect_and_navigate(verbose=False)
        
        assert result.success is True
    
    def test_get_token_interactive(self):
        """Test interactive token input."""
        manager = ExistingBrowserManager()
        
        mock_result = MagicMock()
        mock_result.page = MagicMock()
        mock_result.actual_url = "https://huggingface.co/settings/tokens"
        
        with patch('builtins.input', return_value="hf_test_token_123"):
            token = manager.get_token_interactive(mock_result, verbose=False)
        
        assert token == "hf_test_token_123"
        mock_result.close.assert_called_once()
    
    def test_get_token_interactive_empty(self):
        """Test interactive token input with empty response."""
        manager = ExistingBrowserManager()
        
        mock_result = MagicMock()
        mock_result.page = MagicMock()
        
        with patch('builtins.input', return_value=""):
            token = manager.get_token_interactive(mock_result, verbose=False)
        
        assert token is None
        mock_result.close.assert_called_once()
    
    def test_get_token_interactive_keyboard_interrupt(self):
        """Test handling of KeyboardInterrupt."""
        manager = ExistingBrowserManager()
        
        mock_result = MagicMock()
        mock_result.page = MagicMock()
        
        with patch('builtins.input', side_effect=KeyboardInterrupt()):
            token = manager.get_token_interactive(mock_result, verbose=False)
        
        assert token is None


class TestIntegration:
    """Integration tests."""
    
    def test_full_flow_simulation(self):
        """Test full flow with mocked components."""
        config = BrowserConfig(cdp_ports=[9222])
        manager = ExistingBrowserManager(config)
        
        # Mock CDP detection
        with patch.object(manager.cdp_detector, 'find_cdp_port', return_value=9222):
            # Mock browser connection
            mock_result = BrowserConnectionResult(
                success=True,
                status=ConnectionStatus.SUCCESS,
                browser=MagicMock(),
                page=MagicMock(),
                actual_url="https://huggingface.co/settings/tokens"
            )
            with patch.object(manager.browser_connector, 'connect', return_value=mock_result):
                # Mock navigation
                with patch.object(manager.token_navigator, 'navigate', return_value=(NavigationStatus.SUCCESS, "https://huggingface.co/settings/tokens")):
                    result = manager.connect_and_navigate(verbose=False)
                    
                    assert result.success is True
                    assert result.actual_url == "https://huggingface.co/settings/tokens"
