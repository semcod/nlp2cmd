"""
Pipeline Runner utility functions and classes.

Extracted from pipeline_runner.py (Sprint 4) for better modularity.
Contains:
- Debug helpers
- EPIPE retry logic
- Form field filtering (junk/contact detection)
- Markdown console wrapper
- ShellExecutionPolicy
- RunnerResult dataclass
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from nlp2cmd.adapters.base import SafetyPolicy
from nlp2cmd.utils.data_files import find_data_file
from rich.console import Console
from nlp2cmd.utils.yaml_compat import yaml

_DEBUG = os.environ.get("NLP2CMD_DEBUG", "").lower() in ("1", "true", "yes")


def _debug(msg: str) -> None:
    """Print debug message to stderr when NLP2CMD_DEBUG=1."""
    if _DEBUG:
        print(f"DEBUG [PipelineRunner] {msg}", file=sys.stderr, flush=True)


def _with_epipe_retry(func, max_retries: int = 3, backoff_ms: int = 500):
    """Execute a Playwright operation with retry logic for EPIPE errors.
    
    EPIPE (broken pipe) errors occur when the Node.js process communication
    breaks. We retry with exponential backoff to allow the connection to recover.
    
    Args:
        func: Callable that performs the Playwright operation
        max_retries: Maximum number of retry attempts
        backoff_ms: Initial backoff in milliseconds (doubles each retry)
    
    Returns:
        The result of func() if successful
    
    Raises:
        The last exception if all retries fail
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            is_epipe = "epipe" in err_str or "broken pipe" in err_str or "econnreset" in err_str
            
            if not is_epipe:
                # Not an EPIPE error, fail immediately
                raise
            
            # EPIPE error - retry with backoff
            wait_ms = min(backoff_ms * (2 ** attempt), 5000)  # Cap at 5 seconds
            _debug(f"EPIPE error on attempt {attempt + 1}/{max_retries}, waiting {wait_ms}ms before retry: {e}")
            time.sleep(wait_ms / 1000)
    
    # All retries exhausted
    raise last_error if last_error else RuntimeError("EPIPE retry failed")


# ---------------------------------------------------------------------------
# Form-field filtering helpers (used in multiple places during form filling)
# ---------------------------------------------------------------------------

def _field_attrs(f: object) -> tuple[str, str, str, str, str, str]:
    """Extract common field attributes as lowered strings.

    Returns (field_type, name, fid, label, placeholder, selector).
    """
    try:
        field_type = str(getattr(f, "field_type", "") or "").strip().lower()
        name = str(getattr(f, "name", "") or "").strip().lower()
        fid = str(getattr(f, "id", "") or "").strip().lower()
        label = str(getattr(f, "label", "") or "").strip().lower()
        placeholder = str(getattr(f, "placeholder", "") or "").strip().lower()
        selector = str(getattr(f, "selector", "") or "").strip().lower()
    except Exception:
        return ("", "", "", "", "", "")
    return (field_type, name, fid, label, placeholder, selector)


def _is_junk_field(f: object) -> bool:
    """Return True if a detected field is search/cookie/captcha/comment junk."""
    field_type, name, fid, label, placeholder, _ = _field_attrs(f)
    hay = " ".join([name, fid, label, placeholder])

    if field_type == "search":
        return True
    if name in {"s", "q", "search", "query"}:
        return True
    if "search" in hay or "szukaj" in hay or "wyszuki" in hay:
        return True
    if "cookie" in hay or "consent" in hay:
        return True
    if fid.startswith("cky") or "cky" in hay:
        return True
    if fid.startswith("cmplz") or "cmplz" in hay:
        return True
    if "captcha" in hay or "recaptcha" in hay or "g-recaptcha" in hay or "hcaptcha" in hay:
        return True
    if name in {"comment", "author", "url", "wp-comment-cookies-consent"}:
        return True
    if "comment" in hay:
        return True
    if name.startswith("apbct__") or "cleantalk" in hay:
        return True
    return False


def _is_contact_relevant_field(f: object) -> bool:
    """Return True if a field looks like part of a contact form."""
    if _is_junk_field(f):
        return False

    field_type, name, fid, label, placeholder, _ = _field_attrs(f)
    if field_type in {"email", "tel"}:
        return True
    if field_type not in {"text", "textarea", "email", "tel"}:
        return False

    hay = " ".join([name, fid, label, placeholder])
    contact_tokens = [
        "email", "e-mail", "mail", "telefon", "phone",
        "wiadomo", "message", "imi", "name", "temat", "subject",
    ]
    return any(t in hay for t in contact_tokens)


def _looks_like_comment_form(fields: list) -> bool:
    """Return True if *fields* look like a WordPress comment form."""
    try:
        for f in fields:
            _, name, fid, _, label, selector = _field_attrs(f)
            placeholder = str(getattr(f, "placeholder", "") or "").strip().lower()
            hay = " ".join([name, fid, selector, label, placeholder])
            if "comment" in hay or name in {"author", "email", "url"}:
                return True
    except Exception:
        pass
    return False


def _filter_form_fields(
    fields: list,
    console_wrapper: Optional[Any] = None,
) -> list:
    """Filter out junk / comment / non-contact fields, log via *console_wrapper*.

    Returns the (possibly empty) filtered list.
    """
    if not fields:
        return fields

    if _looks_like_comment_form(fields):
        if console_wrapper is not None:
            try:
                console_wrapper.print(
                    yaml.safe_dump(
                        {"status": "form_fields_ignored_as_comment_form", "detected_count": len(fields)},
                        sort_keys=False, allow_unicode=True,
                    ).rstrip(),
                    language="yaml",
                )
            except Exception:
                pass
        return []

    contact_like = [f for f in fields if _is_contact_relevant_field(f)]
    if not contact_like:
        if console_wrapper is not None:
            try:
                console_wrapper.print(
                    yaml.safe_dump(
                        {"status": "form_fields_ignored_as_non_contact", "detected_count": len(fields)},
                        sort_keys=False, allow_unicode=True,
                    ).rstrip(),
                    language="yaml",
                )
            except Exception:
                pass
        return []

    return fields


class _MarkdownConsoleWrapper:
    """Context manager that captures console output into Markdown code blocks."""

    def __init__(self, console: Console, *, enable_markdown: bool, default_language: str = "text") -> None:
        self.console = console
        self.enable_markdown = enable_markdown
        self.default_language = default_language
        self._buffer: list[str] = []
        # Import inside class to avoid circular dependency
        from nlp2cmd.cli.markdown_output import print_markdown_block
        self.print_markdown_block = print_markdown_block

    def print(self, renderable, *, language: str | None = None) -> None:
        if self.enable_markdown:
            self.print_markdown_block(renderable, language=language or self.default_language, console=self.console)
        else:
            self.console.print(renderable)

    def capture(self):
        """Return context manager that captures printed text into a single block."""
        wrapper = self

        class _Capture:
            def __enter__(self):
                wrapper._buffer = []
                return wrapper._buffer

            def __exit__(self, exc_type, exc, tb):
                if wrapper.enable_markdown and wrapper._buffer:
                    wrapper.print_markdown_block("\n".join(wrapper._buffer), language=wrapper.default_language, console=wrapper.console)
                elif wrapper._buffer:
                    wrapper.console.print("\n".join(wrapper._buffer))

        return _Capture()


@dataclass
class ShellExecutionPolicy:
    allowlist: set[str] = field(default_factory=set)
    blocked_regex: list[str] = field(
        default_factory=lambda: [
            r"\brm\s+-rf\s+/\b",
            r"\brm\s+-rf\s+/\*\b",
            r"\bmkfs\b",
            r"\bdd\s+if=/dev/zero\b",
            r":\(\)\{:\|:&\};:",
        ]
    )
    require_confirm_regex: list[str] = field(
        default_factory=lambda: [
            r"\brm\b",
            r"\brmdir\b",
            r"\bkill\b",
            r"\bkillall\b",
            r"\bshutdown\b",
            r"\breboot\b",
            r"\bsystemctl\s+stop\b",
            r"\bdocker\s+rm\b",
            r"\bdocker\s+rmi\b",
        ]
    )
    allow_sudo: bool = False
    allow_pipes: bool = False

    def load_from_data(self, path: str = "./data/shell_execution_policy.json") -> None:
        """Optionally load policy configuration from JSON in data/."""

        p = find_data_file(explicit_path=path, default_filename="shell_execution_policy.json")
        if not p:
            return

        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(raw, dict):
            return

        ar = raw.get("allowlist")
        if isinstance(ar, list):
            self.allowlist = {x.strip() for x in ar if isinstance(x, str) and x.strip()}

        br = raw.get("blocked_regex")
        if isinstance(br, list):
            self.blocked_regex = [x for x in br if isinstance(x, str) and x.strip()]

        rr = raw.get("require_confirm_regex")
        if isinstance(rr, list):
            self.require_confirm_regex = [x for x in rr if isinstance(x, str) and x.strip()]

        asu = raw.get("allow_sudo")
        if isinstance(asu, bool):
            self.allow_sudo = asu

        ap = raw.get("allow_pipes")
        if isinstance(ap, bool):
            self.allow_pipes = ap


@dataclass
class RunnerResult:
    success: bool
    kind: str
    data: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0


# -----------------------------------------------------------------------------
# Screenshot and Video Recording utilities
# -----------------------------------------------------------------------------

def get_timestamp() -> str:
    """Generate timestamp string for filenames."""
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists, create if not."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def ask_for_screenshot(console: Any, default_path: str) -> tuple[bool, str]:
    """
    Ask user if they want to take a screenshot.
    
    Returns:
        Tuple of (should_take_screenshot, final_path)
    """
    try:
        response = console.input(
            f"[yellow]Zrobić zrzut ekranu? [T/n]: [/yellow]"
        ).strip().lower()
        
        if response in ("", "y", "yes", "t", "tak"):
            custom_path = console.input(
                f"[cyan]Ścieżka zapisu [{default_path}]: [/cyan]"
            ).strip()
            
            if custom_path:
                return True, custom_path
            return True, default_path
        
        return False, ""
    except Exception:
        return False, ""


def take_screenshot(page: Any, path: str, console: Optional[Any] = None) -> Optional[str]:
    """
    Take a screenshot of current page state.
    
    Args:
        page: Playwright page object
        path: Path to save screenshot
        console: Optional console for output
        
    Returns:
        Path to saved screenshot or None if failed
    """
    try:
        # Ensure directory exists
        filepath = Path(path)
        ensure_dir(filepath.parent)
        
        # Take screenshot
        page.screenshot(path=str(filepath), full_page=True)
        
        if console:
            console.print(f"[green]📸 Zrzut ekranu zapisany: {filepath.resolve()}[/green]")
        
        return str(filepath)
    except Exception as e:
        if console:
            console.print(f"[red]❌ Błąd zrzutu ekranu: {e}[/red]")
        return None


class VideoRecorder:
    """Video recording manager for Playwright browser automation."""
    
    def __init__(self, output_dir: str = "./recordings"):
        """
        Initialize video recorder.
        
        Args:
            output_dir: Directory to save recordings
        """
        self.output_dir = Path(output_dir)
        self.video_path: Optional[str] = None
        self.is_recording = False
        
    def start_recording(self, name_prefix: str = "automation") -> Optional[str]:
        """
        Start video recording.
        
        Args:
            name_prefix: Prefix for video filename
            
        Returns:
            Expected path to video file or None
        """
        try:
            timestamp = get_timestamp()
            self.video_path = str(self.output_dir / f"{name_prefix}_{timestamp}.webm")
            self.is_recording = True
            
            # Ensure directory exists
            ensure_dir(self.output_dir)
            
            return self.video_path
        except Exception:
            self.is_recording = False
            return None
    
    def stop_recording(self, console: Optional[Any] = None) -> Optional[str]:
        """
        Stop recording and return video path.
        
        Args:
            console: Optional console for output
            
        Returns:
            Path to saved video or None
        """
        if not self.is_recording:
            return None
            
        try:
            if console and self.video_path:
                console.print(f"[green]🎥 Nagranie zapisane: {self.video_path}[/green]")
            return self.video_path
        except Exception as e:
            if console:
                console.print(f"[red]❌ Błąd zapisu nagrania: {e}[/red]")
            return None
        finally:
            self.is_recording = False


def ask_for_video_recording(console: Any) -> tuple[bool, str]:
    """
    Ask user if they want to record video.
    
    Returns:
        Tuple of (should_record, output_dir)
    """
    try:
        response = console.input(
            f"[yellow]Nagrać wideo z procesu? [T/n]: [/yellow]"
        ).strip().lower()
        
        if response in ("", "y", "yes", "t", "tak"):
            custom_dir = console.input(
                f"[cyan]Folder zapisu [./recordings]: [/cyan]"
            ).strip()
            
            if custom_dir:
                return True, custom_dir
            return True, "./recordings"
        
        return False, ""
    except Exception:
        return False, ""
