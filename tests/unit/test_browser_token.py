"""Tests for browser_token package."""

import pytest
from unittest.mock import MagicMock, patch, Mock

from nlp2cmd.browser_token import (
    BrowserTokenResult,
    TokenConfig,
    BrowserLauncher,
    TokenNavigator,
    NavigationStatus,
    TokenPromptHandler,
    HFTokenRetriever,
)


class TestBrowserTokenResult:
    """Test BrowserTokenResult dataclass."""
    
    def test_success_result(self):
        """Test successful result."""
        result = BrowserTokenResult(
            success=True,
            token="hf_test_token",
            browser_type="firefox",
            message="Success"
        )
        assert result.success is True
        assert result.token == "hf_test_token"
        assert result.browser_type == "firefox"
        assert result.failed is False
    
    def test_failed_result(self):
        """Test failed result."""
        result = BrowserTokenResult(
            success=False,
            error="Browser not found"
        )
        assert result.success is False
        assert result.failed is True
        assert result.error == "Browser not found"


class TestTokenConfig:
    """Test TokenConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = TokenConfig()
        assert config.tokens_url == "https://huggingface.co/settings/tokens"
        assert config.token_name == "nlp2cmd"
        assert config.token_role == "read"
        assert len(config.instructions) == 6
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = TokenConfig(
            tokens_url="https://example.com/tokens",
            token_name="my-app",
            navigation_timeout=60000
        )
        assert config.tokens_url == "https://example.com/tokens"
        assert config.token_name == "my-app"
        assert config.navigation_timeout == 60000


class TestBrowserLauncher:
    """Test BrowserLauncher."""
    
    def test_launch_firefox_success(self):
        """Test launching Firefox successfully."""
        launcher = BrowserLauncher(headless=False)
        
        # Mock Playwright and Firefox
        mock_browser = MagicMock()
        mock_p = MagicMock()
        mock_p.firefox.launch.return_value = mock_browser
        
        browser, browser_type = launcher.launch(mock_p)
        
        assert browser == mock_browser
        assert browser_type == "firefox"
        mock_p.firefox.launch.assert_called_once_with(headless=False)
    
    def test_launch_chromium_fallback(self):
        """Test falling back to Chromium when Firefox fails."""
        launcher = BrowserLauncher(headless=False)
        
        # Mock Playwright - Firefox fails, Chromium succeeds
        mock_browser = MagicMock()
        mock_p = MagicMock()
        mock_p.firefox.launch.side_effect = Exception("Firefox not found")
        mock_p.chromium.launch.return_value = mock_browser
        
        browser, browser_type = launcher.launch(mock_p)
        
        assert browser == mock_browser
        assert browser_type == "chromium"
        mock_p.firefox.launch.assert_called_once()
        mock_p.chromium.launch.assert_called_once_with(headless=False)
    
    def test_launch_both_fail(self):
        """Test error when both browsers fail."""
        launcher = BrowserLauncher()
        
        mock_p = MagicMock()
        mock_p.firefox.launch.side_effect = Exception("Firefox not found")
        mock_p.chromium.launch.side_effect = Exception("Chromium not found")
        
        with pytest.raises(RuntimeError) as exc_info:
            launcher.launch(mock_p)
        
        assert "Failed to launch any browser" in str(exc_info.value)
    
    def test_create_context_and_page(self):
        """Test creating context and page."""
        launcher = BrowserLauncher()
        
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_browser = MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        context, page = launcher.create_context_and_page(mock_browser)
        
        assert context == mock_context
        assert page == mock_page
    
    def test_cleanup(self):
        """Test browser cleanup."""
        launcher = BrowserLauncher()
        mock_browser = MagicMock()
        launcher._browser = mock_browser
        
        launcher.cleanup()
        
        mock_browser.close.assert_called_once()


class TestTokenNavigator:
    """Test TokenNavigator."""
    
    def test_navigate_success(self):
        """Test successful navigation to tokens page."""
        navigator = TokenNavigator()
        
        mock_page = MagicMock()
        mock_page.url = "https://huggingface.co/settings/tokens"
        
        status, message, url = navigator.navigate(mock_page)
        
        assert status == NavigationStatus.SUCCESS
        assert "correct URL" in message
        assert url == "https://huggingface.co/settings/tokens"
    
    def test_navigate_login_required(self):
        """Test navigation to login page."""
        navigator = TokenNavigator()
        
        mock_page = MagicMock()
        mock_page.url = "https://huggingface.co/login"  # Pure login URL without tokens path
        
        status, message, url = navigator.navigate(mock_page)
        
        assert status == NavigationStatus.LOGIN_REQUIRED
        assert "requires login" in message
    
    def test_navigate_domain_reached(self):
        """Test navigation to different path on same domain."""
        navigator = TokenNavigator()
        
        mock_page = MagicMock()
        mock_page.url = "https://huggingface.co/models"
        
        status, message, url = navigator.navigate(mock_page)
        
        assert status == NavigationStatus.DOMAIN_REACHED
        assert "different path" in message
    
    def test_navigate_wrong_domain(self):
        """Test navigation to wrong domain."""
        navigator = TokenNavigator()
        
        mock_page = MagicMock()
        mock_page.url = "https://example.com/something"
        
        status, message, url = navigator.navigate(mock_page)
        
        assert status == NavigationStatus.WRONG_DOMAIN
        assert "unexpected URL" in message
    
    def test_navigate_failure(self):
        """Test navigation failure."""
        navigator = TokenNavigator()
        
        mock_page = MagicMock()
        mock_page.goto.side_effect = Exception("Timeout")
        
        status, message, url = navigator.navigate(mock_page)
        
        assert status == NavigationStatus.FAILED
        assert "Navigation failed" in message
    
    def test_can_proceed_success(self):
        """Test can_proceed with success status."""
        navigator = TokenNavigator()
        assert navigator.can_proceed(NavigationStatus.SUCCESS) is True
    
    def test_can_proceed_login_required(self):
        """Test can_proceed with login required."""
        navigator = TokenNavigator()
        assert navigator.can_proceed(NavigationStatus.LOGIN_REQUIRED) is True
    
    def test_can_proceed_wrong_domain(self):
        """Test can_proceed with wrong domain."""
        navigator = TokenNavigator()
        assert navigator.can_proceed(NavigationStatus.WRONG_DOMAIN) is False


class TestTokenPromptHandler:
    """Test TokenPromptHandler."""
    
    def test_show_instructions(self, capsys):
        """Test showing instructions."""
        handler = TokenPromptHandler()
        handler.show_instructions([
            "1. Step one",
            "2. Step two",
        ])
        
        captured = capsys.readouterr()
        assert "Instructions:" in captured.out
        assert "1. Step one" in captured.out
        assert "2. Step two" in captured.out
    
    def test_prompt_for_token_success(self):
        """Test successful token input."""
        handler = TokenPromptHandler()
        
        with patch('builtins.input', return_value='hf_test_token_123'):
            token = handler.prompt_for_token()
        
        assert token == 'hf_test_token_123'
    
    def test_prompt_for_token_empty(self):
        """Test empty token input."""
        handler = TokenPromptHandler()
        
        with patch('builtins.input', return_value=''):
            token = handler.prompt_for_token()
        
        assert token is None
    
    def test_prompt_for_token_whitespace(self):
        """Test whitespace-only token input."""
        handler = TokenPromptHandler()
        
        with patch('builtins.input', return_value='   '):
            token = handler.prompt_for_token()
        
        assert token is None
    
    def test_prompt_for_token_eof(self):
        """Test EOF during token input."""
        handler = TokenPromptHandler()
        
        with patch('builtins.input', side_effect=EOFError()):
            token = handler.prompt_for_token()
        
        assert token is None
    
    def test_prompt_for_token_keyboard_interrupt(self):
        """Test keyboard interrupt during token input."""
        handler = TokenPromptHandler()
        
        with patch('builtins.input', side_effect=KeyboardInterrupt()):
            token = handler.prompt_for_token()
        
        assert token is None
    
    def test_cleanup_page(self):
        """Test page cleanup."""
        handler = TokenPromptHandler()
        mock_page = MagicMock()
        
        handler._cleanup_page(mock_page)
        
        mock_page.close.assert_called_once()
    
    def test_cleanup_page_none(self):
        """Test cleanup with no page."""
        handler = TokenPromptHandler()
        # Should not raise
        handler._cleanup_page(None)


class TestHFTokenRetriever:
    """Test HFTokenRetriever."""
    
    def test_init_default_config(self):
        """Test initialization with default config."""
        retriever = HFTokenRetriever()
        assert retriever.config.tokens_url == "https://huggingface.co/settings/tokens"
    
    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = TokenConfig(tokens_url="https://custom.com/tokens")
        retriever = HFTokenRetriever(config)
        assert retriever.config.tokens_url == "https://custom.com/tokens"
    
    def test_retrieve_playwright_not_installed(self):
        """Test retrieval when Playwright not installed."""
        retriever = HFTokenRetriever()
        
        with patch.dict('sys.modules', {'playwright.sync_api': None}):
            result = retriever.retrieve()
        
        assert result.success is False
        assert "Playwright not installed" in result.error
    
    def test_retrieve_browser_launch_failure(self):
        """Test retrieval when browser launch fails."""
        retriever = HFTokenRetriever()
        
        mock_p = MagicMock()
        mock_p.firefox.launch.side_effect = Exception("Firefox not found")
        mock_p.chromium.launch.side_effect = Exception("Chromium not found")
        
        with patch('playwright.sync_api.sync_playwright') as mock_sync:
            mock_sync.return_value.__enter__ = MagicMock(return_value=mock_p)
            result = retriever.retrieve()
        
        assert result.success is False
        assert "Failed to launch" in result.error


class TestIntegration:
    """Integration tests."""
    
    def test_full_flow_success(self):
        """Test full successful token retrieval flow."""
        retriever = HFTokenRetriever()
        
        # Mock browser
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.url = "https://huggingface.co/settings/tokens"
        
        # Setup mocks
        retriever.launcher.create_context_and_page = MagicMock(return_value=(mock_context, mock_page))
        retriever.launcher.launch = MagicMock(return_value=(mock_browser, "firefox"))
        retriever.launcher._browser = mock_browser
        
        # Mock input
        with patch('builtins.input', return_value='hf_success_token_12345'):
            with patch('playwright.sync_api.sync_playwright') as mock_sync:
                mock_sync.return_value.__enter__ = MagicMock(return_value=MagicMock())
                result = retriever.retrieve()
        
        # Verify flow executed
        assert retriever.launcher.launch.called
        assert retriever.launcher.create_context_and_page.called
    
    def test_navigation_failure_flow(self):
        """Test flow when navigation fails."""
        navigator = TokenNavigator()
        
        # Test that failed navigation is properly classified
        mock_page = MagicMock()
        mock_page.goto.side_effect = Exception("Network error")
        
        status, message, url = navigator.navigate(mock_page)
        
        assert status == NavigationStatus.FAILED
        assert navigator.can_proceed(status) is False
