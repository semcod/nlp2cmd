"""
Automatic Playwright installation helper.

Detects if Playwright is needed and installs it automatically with user confirmation.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console

try:
    from nlp2cmd.cli.markdown_output import print_yaml_block
except Exception:  # pragma: no cover
    def print_yaml_block(data, *, console: Optional[Console] = None) -> None:  # type: ignore
        try:
            (console or Console()).print(str(data))
        except Exception:
            return


def is_playwright_installed() -> bool:
    """Check if Playwright is installed."""
    try:
        import playwright
        return True
    except ImportError:
        return False


def is_playwright_browsers_installed() -> bool:
    """Check if Playwright browsers are installed by looking for the executable."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Check if browser executable exists on disk rather than trying to launch it
            # This avoids false negatives when browser is installed but can't launch
            # (e.g., missing system dependencies, sandbox issues)
            try:
                # Get the browser executable path without launching
                browser_path = p.chromium.executable_path
                if browser_path and Path(browser_path).exists():
                    return True
            except Exception:
                pass
            
            # Fallback: try to launch chromium to verify it works
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                return True
            except Exception:
                return False
    except Exception:
        return False


def install_playwright(console: Optional[Console] = None) -> bool:
    """
    Install Playwright package.
    
    Args:
        console: Rich console for output
    
    Returns:
        True if installation succeeded, False otherwise
    """
    if console is None:
        console = Console()

    print_yaml_block(
        {
            "status": "installing_dependency",
            "dependency": "playwright",
        },
        console=console,
    )
    
    try:
        # Install playwright package
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "playwright", "-q"],
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            print_yaml_block(
                {
                    "status": "dependency_installed",
                    "dependency": "playwright",
                    "success": True,
                },
                console=console,
            )
            return True
        else:
            print_yaml_block(
                {
                    "status": "dependency_install_failed",
                    "dependency": "playwright",
                    "success": False,
                    "returncode": int(result.returncode),
                    "stderr": (result.stderr or "").strip(),
                },
                console=console,
            )
            return False
    except Exception as e:
        print_yaml_block(
            {
                "status": "dependency_install_error",
                "dependency": "playwright",
                "success": False,
                "error": str(e),
            },
            console=console,
        )
        return False


def install_playwright_browsers(console: Optional[Console] = None) -> bool:
    """
    Install Playwright browsers (chromium).
    
    Args:
        console: Rich console for output
    
    Returns:
        True if installation succeeded, False otherwise
    """
    if console is None:
        console = Console()

    print_yaml_block(
        {
            "status": "installing_browser",
            "browser": "chromium",
            "download_mb_estimate": 170,
        },
        console=console,
    )
    
    try:
        # Install chromium browser
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            print_yaml_block(
                {
                    "status": "browser_installed",
                    "browser": "chromium",
                    "success": True,
                },
                console=console,
            )
            return True
        else:
            print_yaml_block(
                {
                    "status": "browser_install_failed",
                    "browser": "chromium",
                    "success": False,
                    "returncode": int(result.returncode),
                    "stderr": (result.stderr or "").strip(),
                },
                console=console,
            )
            return False
    except Exception as e:
        print_yaml_block(
            {
                "status": "browser_install_error",
                "browser": "chromium",
                "success": False,
                "error": str(e),
            },
            console=console,
        )
        return False


def ensure_playwright_installed(
    console: Optional[Console] = None,
    auto_install: bool = False,
) -> bool:
    """
    Ensure Playwright is installed, prompting user if needed.
    
    Args:
        console: Rich console for output
        auto_install: If True, install without asking
    
    Returns:
        True if Playwright is ready, False otherwise
    """
    if console is None:
        console = Console()
    
    # Check if package is installed
    if not is_playwright_installed():
        if not auto_install:
            print_yaml_block(
                {
                    "status": "dependency_required",
                    "dependency": "playwright",
                    "reason": "browser_automation",
                },
                console=console,
            )
            response = console.input("[cyan]Install Playwright now? [Y/n]: [/cyan]").strip().lower()
            if response not in ("", "y", "yes", "tak"):
                print_yaml_block(
                    {
                        "status": "browser_automation_skipped",
                        "reason": "user_declined_playwright_install",
                    },
                    console=console,
                )
                return False
        
        if not install_playwright(console):
            return False
    
    # Check if browsers are installed
    if not is_playwright_browsers_installed():
        if not auto_install:
            print_yaml_block(
                {
                    "status": "browser_required",
                    "browser": "chromium",
                    "reason": "browser_automation",
                },
                console=console,
            )
            response = console.input("[cyan]Install Chromium now? [Y/n]: [/cyan]").strip().lower()
            if response not in ("", "y", "yes", "tak"):
                print_yaml_block(
                    {
                        "status": "browser_automation_skipped",
                        "reason": "user_declined_chromium_install",
                    },
                    console=console,
                )
                return False
        
        if not install_playwright_browsers(console):
            return False
    
    print_yaml_block(
        {
            "status": "playwright_ready",
            "success": True,
            "playwright_installed": True,
            "chromium_installed": True,
        },
        console=console,
    )
    return True
