"""Tests for desktop_executor package."""

import pytest
from unittest.mock import MagicMock, patch, mock_open
import time

from nlp2cmd.desktop_executor import (
    DesktopBackend,
    ActionResult,
    ActionStatus,
    ExecutionConfig,
    BackendDetector,
    WindowManager,
    KeyboardController,
    BrowserController,
    EnvManager,
    DesktopActionExecutor,
)


class TestDesktopBackend:
    """Test DesktopBackend enum."""
    
    def test_backend_values(self):
        """Test backend enum values."""
        assert DesktopBackend.YDOTOOL.value == "ydotool"
        assert DesktopBackend.XDOTOOL.value == "xdotool"
        assert DesktopBackend.WMCTRL.value == "wmctrl"
        assert DesktopBackend.NONE.value == "none"


class TestActionResult:
    """Test ActionResult dataclass."""
    
    def test_default_creation(self):
        """Test creating empty result."""
        result = ActionResult()
        assert result.success is False
        assert result.status == ActionStatus.FAILED
        assert result.error is None
    
    def test_success_result(self):
        """Test success factory method."""
        result = ActionResult.success_result("output", DesktopBackend.XDOTOOL)
        assert result.success is True
        assert result.status == ActionStatus.SUCCESS
        assert result.result == "output"
        assert result.backend_used == DesktopBackend.XDOTOOL
    
    def test_failed_result(self):
        """Test failed factory method."""
        result = ActionResult.failed_result("error message", DesktopBackend.YDOTOOL)
        assert result.success is False
        assert result.status == ActionStatus.FAILED
        assert result.error == "error message"
        assert result.backend_used == DesktopBackend.YDOTOOL
    
    def test_unsupported_result(self):
        """Test unsupported factory method."""
        result = ActionResult.unsupported_result("unknown_action")
        assert result.success is False
        assert result.status == ActionStatus.UNSUPPORTED
        assert "unknown_action" in result.error


class TestExecutionConfig:
    """Test ExecutionConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration."""
        config = ExecutionConfig()
        assert config.key_delay == 20
        assert config.focus_wait == 0.3
        assert config.session_wait == 2.0
        assert config.default_wait_ms == 500
    
    def test_custom_values(self):
        """Test custom configuration."""
        config = ExecutionConfig(key_delay=50, focus_wait=1.0)
        assert config.key_delay == 50
        assert config.focus_wait == 1.0


class TestBackendDetector:
    """Test BackendDetector class."""
    
    def test_init(self):
        """Test initialization."""
        detector = BackendDetector()
        assert detector._cached_backend is None
    
    @patch('nlp2cmd.desktop_executor.backend_detector.shutil.which')
    def test_detect_ydotool(self, mock_which):
        """Test detecting ydotool."""
        mock_which.side_effect = lambda x: x == "ydotool"
        
        detector = BackendDetector()
        backend = detector.detect()
        
        assert backend == DesktopBackend.YDOTOOL
    
    @patch('nlp2cmd.desktop_executor.backend_detector.shutil.which')
    def test_detect_xdotool(self, mock_which):
        """Test detecting xdotool (fallback)."""
        mock_which.side_effect = lambda x: x in ["xdotool", "wmctrl"]
        
        detector = BackendDetector()
        backend = detector.detect()
        
        assert backend == DesktopBackend.XDOTOOL
    
    @patch('nlp2cmd.desktop_executor.backend_detector.shutil.which')
    def test_detect_none(self, mock_which):
        """Test detecting no backend."""
        mock_which.return_value = None
        
        detector = BackendDetector()
        backend = detector.detect()
        
        assert backend == DesktopBackend.NONE
    
    @patch('nlp2cmd.desktop_executor.backend_detector.shutil.which')
    def test_caching(self, mock_which):
        """Test that detection is cached."""
        mock_which.side_effect = lambda x: x == "ydotool"
        
        detector = BackendDetector()
        backend1 = detector.detect()
        backend2 = detector.detect()
        
        assert backend1 == backend2
        assert mock_which.call_count == 1  # Only called once due to caching
    
    @patch('nlp2cmd.desktop_executor.backend_detector.shutil.which')
    def test_is_available_true(self, mock_which):
        """Test is_available when backend exists."""
        mock_which.return_value = "/usr/bin/xdotool"
        
        detector = BackendDetector()
        assert detector.is_available() is True
    
    @patch('nlp2cmd.desktop_executor.backend_detector.shutil.which')
    def test_is_available_false(self, mock_which):
        """Test is_available when no backend exists."""
        mock_which.return_value = None
        
        detector = BackendDetector()
        assert detector.is_available() is False
    
    def test_get_error_message(self):
        """Test error message content."""
        detector = BackendDetector()
        msg = detector.get_error_message()
        
        assert "ydotool" in msg
        assert "xdotool" in msg


class TestWindowManager:
    """Test WindowManager class."""
    
    def test_init_with_backend(self):
        """Test initialization with backend."""
        manager = WindowManager(DesktopBackend.XDOTOOL)
        assert manager.backend == DesktopBackend.XDOTOOL
    
    @patch('nlp2cmd.desktop_executor.window_manager.subprocess.run')
    def test_focus_with_ydotool(self, mock_run):
        """Test focus with ydotool backend."""
        manager = WindowManager(DesktopBackend.YDOTOOL)
        result = manager.focus_window("Firefox", wait=0.1, verbose=False)
        
        assert result.success is True
        assert result.backend_used == DesktopBackend.YDOTOOL
        mock_run.assert_called_once()
    
    @patch('nlp2cmd.desktop_executor.window_manager.shutil.which')
    @patch('nlp2cmd.desktop_executor.window_manager.subprocess.run')
    @patch('nlp2cmd.desktop_executor.window_manager.subprocess.check_output')
    def test_focus_with_xdotool(self, mock_check, mock_run, mock_which):
        """Test focus with xdotool backend."""
        mock_which.return_value = None  # No wmctrl
        mock_check.return_value = "12345\n"
        
        manager = WindowManager(DesktopBackend.XDOTOOL)
        result = manager.focus_window("Firefox", wait=0.1, verbose=False)
        
        assert result.success is True
        assert result.backend_used == DesktopBackend.XDOTOOL
    
    @patch('nlp2cmd.desktop_executor.window_manager.shutil.which')
    @patch('nlp2cmd.desktop_executor.window_manager.subprocess.run')
    def test_focus_with_wmctrl(self, mock_run, mock_which):
        """Test focus with wmctrl backend."""
        mock_which.return_value = "/usr/bin/wmctrl"
        
        manager = WindowManager(DesktopBackend.WMCTRL)
        result = manager.focus_window("Firefox", verbose=False)
        
        assert result.success is True
        assert result.backend_used == DesktopBackend.WMCTRL


class TestKeyboardController:
    """Test KeyboardController class."""
    
    def test_init_with_backend(self):
        """Test initialization with backend."""
        controller = KeyboardController(DesktopBackend.YDOTOOL)
        assert controller.backend == DesktopBackend.YDOTOOL
    
    @patch('nlp2cmd.desktop_executor.keyboard_controller.subprocess.run')
    def test_send_shortcut_ydotool(self, mock_run):
        """Test shortcut with ydotool."""
        controller = KeyboardController(DesktopBackend.YDOTOOL)
        result = controller.send_shortcut("ctrl+t", verbose=False)
        
        assert result.success is True
        assert result.backend_used == DesktopBackend.YDOTOOL
    
    @patch('nlp2cmd.desktop_executor.keyboard_controller.subprocess.run')
    def test_send_shortcut_xdotool(self, mock_run):
        """Test shortcut with xdotool."""
        controller = KeyboardController(DesktopBackend.XDOTOOL)
        result = controller.send_shortcut("ctrl+t", verbose=False)
        
        assert result.success is True
        assert result.backend_used == DesktopBackend.XDOTOOL
        mock_run.assert_called_with(["xdotool", "key", "ctrl+t"], check=True)
    
    @patch('nlp2cmd.desktop_executor.keyboard_controller.subprocess.run')
    def test_send_key_xdotool(self, mock_run):
        """Test single key with xdotool."""
        controller = KeyboardController(DesktopBackend.XDOTOOL)
        result = controller.send_key("Return", verbose=False)
        
        assert result.success is True
        mock_run.assert_called_with(["xdotool", "key", "Return"], check=True)
    
    @patch('nlp2cmd.desktop_executor.keyboard_controller.subprocess.run')
    def test_type_text_xdotool(self, mock_run):
        """Test typing with xdotool."""
        controller = KeyboardController(DesktopBackend.XDOTOOL)
        result = controller.type_text("hello", delay_ms=30, verbose=False)
        
        assert result.success is True
        mock_run.assert_called_with(
            ["xdotool", "type", "--delay", "30", "hello"],
            check=True
        )
    
    def test_type_empty_text(self):
        """Test typing empty text returns success."""
        controller = KeyboardController(DesktopBackend.XDOTOOL)
        result = controller.type_text("", verbose=False)
        
        assert result.success is True
        assert result.result is None
    
    def test_convert_keys_to_ydotool(self):
        """Test key name conversion."""
        result = KeyboardController._convert_keys_to_ydotool("ctrl+t")
        
        assert "29:1" in result  # ctrl press
        assert "20:1" in result  # t press
        assert "20:0" in result  # t release
        assert "29:0" in result  # ctrl release


class TestBrowserController:
    """Test BrowserController class."""
    
    @patch('nlp2cmd.desktop_executor.browser_controller.shutil.which')
    def test_find_firefox(self, mock_which):
        """Test finding Firefox executable."""
        mock_which.return_value = "/usr/bin/firefox"
        
        controller = BrowserController()
        path = controller._find_firefox()
        
        assert path == "/usr/bin/firefox"
    
    @patch('nlp2cmd.desktop_executor.browser_controller.shutil.which')
    def test_is_available_true(self, mock_which):
        """Test is_available when Firefox exists."""
        mock_which.return_value = "/usr/bin/firefox"
        
        controller = BrowserController()
        assert controller.is_available() is True
    
    @patch('nlp2cmd.desktop_executor.browser_controller.shutil.which')
    def test_is_available_false(self, mock_which):
        """Test is_available when Firefox doesn't exist."""
        mock_which.return_value = None
        
        controller = BrowserController()
        assert controller.is_available() is False
    
    @patch('nlp2cmd.desktop_executor.browser_controller.shutil.which')
    @patch('nlp2cmd.desktop_executor.browser_controller.subprocess.run')
    def test_open_tab_success(self, mock_run, mock_which):
        """Test opening tab successfully."""
        mock_which.return_value = "/usr/bin/firefox"
        
        controller = BrowserController()
        result = controller.open_tab("https://example.com", verbose=False)
        
        assert result.success is True
        mock_run.assert_called_with(
            ["/usr/bin/firefox", "--new-tab", "https://example.com"],
            check=True
        )
    
    @patch('nlp2cmd.desktop_executor.browser_controller.shutil.which')
    def test_open_tab_no_firefox(self, mock_which):
        """Test opening tab without Firefox."""
        mock_which.return_value = None
        
        controller = BrowserController()
        result = controller.open_tab("https://example.com", verbose=False)
        
        assert result.success is False
        assert "Firefox executable not found" in result.error
    
    def test_open_tab_empty_url(self):
        """Test opening tab with empty URL."""
        controller = BrowserController()
        result = controller.open_tab("", verbose=False)
        
        assert result.success is True  # Nothing to do is considered success
    
    @patch('nlp2cmd.desktop_executor.browser_controller.time.sleep')
    def test_check_session(self, mock_sleep):
        """Test check session action."""
        controller = BrowserController()
        result = controller.check_session("huggingface", wait_seconds=0.1, verbose=False)
        
        assert result.success is True
        assert result.result == "desktop_skipped"
        mock_sleep.assert_called_once_with(0.1)


class TestEnvManager:
    """Test EnvManager class."""
    
    def test_init_with_default_file(self):
        """Test initialization with default file."""
        manager = EnvManager()
        assert manager.default_file == ".env"
    
    def test_init_with_custom_file(self):
        """Test initialization with custom file."""
        manager = EnvManager("custom.env")
        assert manager.default_file == "custom.env"
    
    def test_verify_env_in_variables(self):
        """Test verifying env var from variables dict."""
        manager = EnvManager()
        variables = {"HF_TOKEN": "hf_test_token"}
        
        result = manager.verify_env("HF_TOKEN", ".env", variables)
        
        assert result.success is True
    
    @patch('builtins.open', mock_open(read_data='HF_TOKEN=loaded_token\n'))
    @patch('pathlib.Path.exists')
    def test_verify_env_from_file(self, mock_exists):
        """Test verifying env var from .env file."""
        mock_exists.return_value = True
        
        manager = EnvManager()
        variables = {}
        
        result = manager.verify_env("HF_TOKEN", ".env", variables)
        
        assert result.success is True
    
    def test_verify_env_not_found(self):
        """Test verifying non-existent env var."""
        manager = EnvManager()
        variables = {}
        
        with patch('pathlib.Path.exists', return_value=False):
            result = manager.verify_env("MISSING_VAR", ".env", variables)
        
        assert result.success is False
        assert "MISSING_VAR" in result.error
    
    def test_validate_hf_token(self):
        """Test HF token validation."""
        manager = EnvManager()
        
        valid = manager._validate_value("hf_abc123", "HF_TOKEN")
        invalid = manager._validate_value("invalid", "HF_TOKEN")
        
        assert valid is True
        assert invalid is False
    
    @patch('builtins.open', mock_open(read_data='KEY1=value1\nKEY2=value2\n'))
    def test_load_env_file(self):
        """Test loading .env file."""
        manager = EnvManager()
        
        from pathlib import Path
        env_vars = manager._load_env_file(Path(".env"))
        
        assert env_vars["KEY1"] == "value1"
        assert env_vars["KEY2"] == "value2"


class TestDesktopActionExecutor:
    """Test DesktopActionExecutor orchestrator."""
    
    @patch('nlp2cmd.desktop_executor.backend_detector.shutil.which')
    def test_init_detects_backend(self, mock_which):
        """Test initialization detects backend."""
        mock_which.side_effect = lambda x: x == "xdotool"
        
        executor = DesktopActionExecutor()
        
        assert executor.backend == DesktopBackend.XDOTOOL
        assert executor.backend_detector is not None
    
    @patch('nlp2cmd.desktop_executor.backend_detector.shutil.which')
    def test_is_available(self, mock_which):
        """Test is_available method."""
        mock_which.return_value = "/usr/bin/xdotool"
        
        executor = DesktopActionExecutor()
        assert executor.is_available() is True
    
    @patch('nlp2cmd.desktop_executor.backend_detector.shutil.which')
    def test_execute_no_backend(self, mock_which):
        """Test execute with no backend available."""
        mock_which.return_value = None
        
        executor = DesktopActionExecutor()
        result = executor.execute("desktop_type", {"text": "hello"}, {})
        
        assert result.success is False
        assert "ydotool" in result.error or "xdotool" in result.error
    
    @patch('nlp2cmd.desktop_executor.backend_detector.shutil.which')
    @patch('nlp2cmd.desktop_executor.desktop_action_executor.time.sleep')
    def test_execute_wait(self, mock_sleep, mock_which):
        """Test execute wait action."""
        mock_which.return_value = "/usr/bin/xdotool"
        
        executor = DesktopActionExecutor()
        result = executor.execute("wait", {"ms": 1000}, {}, verbose=False)
        
        assert result.success is True
        mock_sleep.assert_called_once_with(1.0)
    
    @patch('nlp2cmd.desktop_executor.backend_detector.shutil.which')
    @patch('nlp2cmd.desktop_executor.desktop_action_executor.subprocess.run')
    def test_execute_echo(self, mock_run, mock_which):
        """Test execute echo action."""
        mock_which.return_value = "/usr/bin/xdotool"
        
        executor = DesktopActionExecutor()
        result = executor.execute("echo", {"message": "test"}, {}, verbose=False)
        
        assert result.success is True
    
    @patch('nlp2cmd.desktop_executor.backend_detector.shutil.which')
    def test_execute_unsupported(self, mock_which):
        """Test execute unsupported action."""
        mock_which.return_value = "/usr/bin/xdotool"
        
        executor = DesktopActionExecutor()
        result = executor.execute("unknown_action", {}, {}, verbose=False)
        
        assert result.success is False
        assert result.status == ActionStatus.UNSUPPORTED
    
    @patch('nlp2cmd.desktop_executor.backend_detector.shutil.which')
    def test_execute_special_cases(self, mock_which):
        """Test execute for special cases requiring external context."""
        mock_which.return_value = "/usr/bin/xdotool"
        
        executor = DesktopActionExecutor()
        
        # prompt_secret requires external execution
        result = executor.execute("prompt_secret", {}, {}, verbose=False)
        assert result.status == ActionStatus.UNSUPPORTED
        
        # save_env requires external execution
        result = executor.execute("save_env", {}, {}, verbose=False)
        assert result.status == ActionStatus.UNSUPPORTED
    
    @patch('nlp2cmd.desktop_executor.backend_detector.shutil.which')
    def test_get_backend_info(self, mock_which):
        """Test get_backend_info method."""
        mock_which.side_effect = lambda x: x in ["xdotool", "wmctrl"]
        
        executor = DesktopActionExecutor()
        primary, fallback = executor.get_backend_info()
        
        assert primary == DesktopBackend.XDOTOOL
        assert fallback == DesktopBackend.WMCTRL
