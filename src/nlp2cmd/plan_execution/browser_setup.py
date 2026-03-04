"""Browser setup and session management for plan execution."""

from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Playwright


@dataclass
class BrowserContextOptions:
    """Options for browser context creation."""
    headless: bool = True
    user_data_dir: Optional[str] = None
    record_video_dir: Optional[str] = None
    record_video_size: dict[str, int] | None = None
    viewport: dict[str, int] | None = None


class BrowserSetup:
    """Handles browser setup, session management, and context creation.
    
    This class manages:
    - Firefox session import and cookie injection
    - Browser selection (Firefox vs Chromium)
    - Context options and launch
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._ff_session_importer: Any = None
        self._ff_chromium_cookies: list[dict] = []
        self._browser_type: str = "chromium"
        self._user_data_dir: Path | None = None
    
    def setup_firefox_sessions(self, console: Any) -> None:
        """Setup Firefox session importing based on environment variables."""
        use_ff_sessions = os.environ.get("NLP2CMD_USE_FIREFOX_SESSIONS", "").strip()
        ff_profile_override = os.environ.get("NLP2CMD_FIREFOX_PROFILE", "").strip() or None
        
        if not use_ff_sessions:
            return
        
        try:
            from nlp2cmd.automation.firefox_sessions import FirefoxSessionImporter
            
            importer_kwargs: dict[str, Any] = {}
            if ff_profile_override:
                importer_kwargs["firefox_profile"] = ff_profile_override
            
            if use_ff_sessions == "firefox":
                # Full Firefox profile mode
                importer_kwargs["browser"] = "firefox"
                self._ff_session_importer = FirefoxSessionImporter(**importer_kwargs)
                ff_profile_dir = self._ff_session_importer.prepare_playwright_profile()
                if ff_profile_dir:
                    console.print(f"[dim]🦊 Skopiowano sesje Firefox → {ff_profile_dir}[/dim]")
                    self._browser_type = "firefox"
                else:
                    console.print("[yellow]⚠ Nie znaleziono profilu Firefox[/yellow]")
                    self._ff_session_importer = None
            else:
                # Cookie injection mode
                importer_kwargs["browser"] = "chromium"
                self._ff_session_importer = FirefoxSessionImporter(**importer_kwargs)
                self._ff_chromium_cookies = self._ff_session_importer.get_chromium_cookies()
                if self._ff_chromium_cookies:
                    console.print(
                        f"[dim]🦊 Załadowano {len(self._ff_chromium_cookies)} ciasteczek "
                        f"z Firefox do Chromium[/dim]"
                    )
                else:
                    console.print("[yellow]⚠ Nie znaleziono ciasteczek Firefox[/yellow]")
        except Exception as e:
            from nlp2cmd.pipeline_runner_utils import _debug
            _debug(f"Firefox session import failed: {e}")
            console.print(f"[yellow]⚠ Import sesji Firefox: {e}[/yellow]")
    
    def get_user_data_dir(self) -> Path:
        """Get or create user data directory for persistent browser context."""
        if self._ff_session_importer and self._browser_type == "firefox":
            return self._ff_session_importer.target_dir
        
        user_data_dir = Path.home() / ".nlp2cmd" / "browser_profile"
        user_data_dir.mkdir(parents=True, exist_ok=True)
        return user_data_dir
    
    def create_context_options(
        self,
        video_dir: str | None = None,
        record_video: bool = False,
    ) -> dict[str, Any]:
        """Create browser context options."""
        user_data_dir = self.get_user_data_dir()
        
        ctx_opts: dict[str, Any] = {
            "user_data_dir": str(user_data_dir),
            "headless": self.headless,
            "viewport": {"width": 1280, "height": 720},
        }
        
        if record_video and video_dir:
            ctx_opts["record_video_dir"] = video_dir
            ctx_opts["record_video_size"] = {"width": 1280, "height": 720}
        
        return ctx_opts
    
    def launch_context(
        self,
        pw: Any,
        ctx_opts: dict[str, Any],
        console: Any,
    ) -> Any:
        """Launch browser context with fallback handling."""
        context = None
        
        # Try Firefox first if configured
        if self._browser_type == "firefox":
            console.print("[dim]🦊 Uruchamiam Playwright Firefox z sesjami...[/dim]")
            for headless_try in ([self.headless] if self.headless else [False, True]):
                try:
                    ctx_opts["headless"] = headless_try
                    context = pw.firefox.launch_persistent_context(**ctx_opts)
                    break
                except Exception as ff_err:
                    ff_err_str = str(ff_err)
                    if "Executable doesn't exist" in ff_err_str:
                        console.print(
                            "[yellow]⚠ Playwright Firefox nie zainstalowany "
                            "(uruchom: playwright install firefox)[/yellow]"
                        )
                        console.print(
                            "[dim]   ↳ Fallback: Chromium + wstrzykiwanie ciasteczek Firefox[/dim]"
                        )
                        self._browser_type = "chromium"
                        if not self._ff_chromium_cookies and self._ff_session_importer:
                            self._ff_chromium_cookies = self._ff_session_importer.get_chromium_cookies()
                        # Reset to Chromium profile
                        user_data_dir = Path.home() / ".nlp2cmd" / "browser_profile"
                        user_data_dir.mkdir(parents=True, exist_ok=True)
                        ctx_opts["user_data_dir"] = str(user_data_dir)
                        break
                    if headless_try:
                        raise
        
        # Chromium path (default or fallback)
        if context is None:
            for headless_try in ([self.headless] if self.headless else [False, True]):
                try:
                    ctx_opts["headless"] = headless_try
                    context = pw.chromium.launch_persistent_context(**ctx_opts)
                    break
                except Exception:
                    if headless_try:
                        raise
        
        return context
    
    def inject_cookies(self, context: Any, console: Any) -> None:
        """Inject Firefox cookies into Chromium context if available."""
        if self._ff_chromium_cookies and self._browser_type == "chromium":
            try:
                context.add_cookies(self._ff_chromium_cookies)
                console.print(
                    f"[dim]🦊 Wstrzyknięto {len(self._ff_chromium_cookies)} "
                    f"ciasteczek Firefox do Chromium[/dim]"
                )
            except Exception as e:
                from nlp2cmd.pipeline_runner_utils import _debug
                _debug(f"Cookie injection failed: {e}")
    
    @property
    def browser_type(self) -> str:
        """Get the selected browser type."""
        return self._browser_type
    
    @property
    def has_ff_cookies(self) -> bool:
        """Check if Firefox cookies are available for injection."""
        return len(self._ff_chromium_cookies) > 0
