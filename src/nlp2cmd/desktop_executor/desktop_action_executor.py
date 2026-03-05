"""Desktop Action Executor - main orchestrator for desktop automation."""

from __future__ import annotations
import time
import logging
from typing import Any, Optional

from .base import DesktopBackend, ActionResult, ActionStatus, ExecutionConfig
from .backend_detector import BackendDetector
from .window_manager import WindowManager
from .keyboard_controller import KeyboardController
from .browser_controller import BrowserController
from .env_manager import EnvManager

log = logging.getLogger("nlp2cmd.desktop_executor.executor")


class DesktopActionExecutor:
    """Main orchestrator for executing desktop automation actions.
    
    Coordinates multiple controllers to execute ActionPlan steps via
    local desktop automation (ydotool/xdotool/wmctrl).
    """
    
    def __init__(self, config: Optional[ExecutionConfig] = None) -> None:
        self.config = config or ExecutionConfig()
        
        # Initialize detector and get backend
        self.backend_detector = BackendDetector()
        self.backend, self.fallback = self.backend_detector.detect_with_fallback()
        
        # Initialize controllers
        self.window_manager = WindowManager(self.backend)
        self.keyboard_controller = KeyboardController(self.backend)
        self.browser_controller = BrowserController()
        self.env_manager = EnvManager()
    
    def execute(
        self,
        action: str,
        params: dict[str, Any],
        variables: dict[str, Any],
        verbose: bool = False,
    ) -> ActionResult:
        """Execute a desktop automation action.
        
        Args:
            action: Action type (desktop_focus_app, desktop_shortcut, etc.)
            params: Action parameters
            variables: Execution variables for substitution
            verbose: Whether to log debug info
            
        Returns:
            ActionResult indicating success/failure
        """
        # Check if backend is available
        if self.backend == DesktopBackend.NONE:
            return ActionResult.failed_result(
                self.backend_detector.get_error_message()
            )
        
        # Execute based on action type
        action_map = {
            "desktop_focus_app": self._execute_focus_app,
            "desktop_shortcut": self._execute_shortcut,
            "desktop_key": self._execute_key,
            "desktop_type": self._execute_type,
            "wait": self._execute_wait,
            "desktop_wait": self._execute_wait,
            "open_firefox_tab": self._execute_open_tab,
            "check_session": self._execute_check_session,
            "echo": self._execute_echo,
            "verify_env": self._execute_verify_env,
        }
        
        handler = action_map.get(action)
        if handler:
            return handler(params, variables, verbose)
        
        # Handle special cases that need external execution
        if action in ("prompt_secret", "save_env"):
            # These need to be handled by the caller (PipelineRunner)
            return ActionResult(
                success=False,
                status=ActionStatus.UNSUPPORTED,
                error=f"Action '{action}' requires external execution context"
            )
        
        return ActionResult.unsupported_result(action)
    
    def _execute_focus_app(
        self,
        params: dict[str, Any],
        variables: dict[str, Any],
        verbose: bool,
    ) -> ActionResult:
        """Execute desktop_focus_app action."""
        title = str(params.get("title") or "Firefox")
        return self.window_manager.focus_window(
            title,
            wait=self.config.focus_wait,
            verbose=verbose
        )
    
    def _execute_shortcut(
        self,
        params: dict[str, Any],
        variables: dict[str, Any],
        verbose: bool,
    ) -> ActionResult:
        """Execute desktop_shortcut action."""
        keys = str(params.get("keys") or "").strip() or "ctrl+t"
        return self.keyboard_controller.send_shortcut(
            keys,
            delay_ms=self.config.key_delay,
            verbose=verbose
        )
    
    def _execute_key(
        self,
        params: dict[str, Any],
        variables: dict[str, Any],
        verbose: bool,
    ) -> ActionResult:
        """Execute desktop_key action."""
        key = str(params.get("key") or "Return").strip() or "Return"
        return self.keyboard_controller.send_key(
            key,
            delay_ms=self.config.key_delay,
            verbose=verbose
        )
    
    def _execute_type(
        self,
        params: dict[str, Any],
        variables: dict[str, Any],
        verbose: bool,
    ) -> ActionResult:
        """Execute desktop_type action."""
        text = str(params.get("text") or "")
        return self.keyboard_controller.type_text(
            text,
            delay_ms=self.config.key_delay,
            verbose=verbose
        )
    
    def _execute_wait(
        self,
        params: dict[str, Any],
        variables: dict[str, Any],
        verbose: bool,
    ) -> ActionResult:
        """Execute wait/desktop_wait action."""
        ms = int(params.get("ms", self.config.default_wait_ms))
        time.sleep(max(ms, 0) / 1000.0)
        return ActionResult.success_result()
    
    def _execute_open_tab(
        self,
        params: dict[str, Any],
        variables: dict[str, Any],
        verbose: bool,
    ) -> ActionResult:
        """Execute open_firefox_tab action."""
        url = str(params.get("url") or "").strip()
        return self.browser_controller.open_tab(url, verbose=verbose)
    
    def _execute_check_session(
        self,
        params: dict[str, Any],
        variables: dict[str, Any],
        verbose: bool,
    ) -> ActionResult:
        """Execute check_session action."""
        service = params.get("service", "unknown")
        return self.browser_controller.check_session(
            service,
            wait_seconds=self.config.session_wait,
            verbose=verbose
        )
    
    def _execute_echo(
        self,
        params: dict[str, Any],
        variables: dict[str, Any],
        verbose: bool,
    ) -> ActionResult:
        """Execute echo action."""
        msg = str(params.get("message", "") or params.get("text", ""))
        if msg:
            if verbose:
                log.debug(msg)
            for line in msg.split("\n"):
                print(f"  {line}")
        return ActionResult.success_result()
    
    def _execute_verify_env(
        self,
        params: dict[str, Any],
        variables: dict[str, Any],
        verbose: bool,
    ) -> ActionResult:
        """Execute verify_env action."""
        var_name = params.get("var_name", "UNKNOWN")
        file_path = params.get("file", ".env")
        return self.env_manager.verify_env(var_name, file_path, variables)
    
    def is_available(self) -> bool:
        """Check if desktop automation is available.
        
        Returns:
            True if at least one backend is available
        """
        return self.backend_detector.is_available()
    
    def get_backend_info(self) -> tuple[DesktopBackend, Optional[DesktopBackend]]:
        """Get information about detected backends.
        
        Returns:
            Tuple of (primary_backend, fallback_backend or None)
        """
        return self.backend, self.fallback
