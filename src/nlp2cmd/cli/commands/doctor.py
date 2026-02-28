"""
NLP2CMD Doctor - System diagnostic and repair tool.

Checks and fixes common issues before running nlp2cmd:
- Ollama availability and required models
- HuggingFace token configuration
- Python dependencies
- Playwright/browser setup
- Environment variables
"""

from __future__ import annotations

import os
import sys
import json
import socket
import subprocess
import shutil
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    Console = None


class Status(Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"
    FIXED = "fixed"


@dataclass
class CheckResult:
    name: str
    status: Status
    message: str
    details: dict = field(default_factory=dict)
    fix_applied: bool = False
    fix_command: Optional[str] = None


class NP2CMDDoctor:
    """System diagnostic and auto-repair for nlp2cmd."""

    def __init__(self, console: Optional[Console] = None, auto_fix: bool = False):
        self.console = console
        self.auto_fix = auto_fix
        self.results: list[CheckResult] = []
        self.ollama_host = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.required_models = ["qwen2.5:3b", "llama3.2", "mistral"]

    def _print(self, message: str, style: str = ""):
        """Print with or without rich."""
        if self.console and HAS_RICH:
            self.console.print(message, style=style)
        else:
            print(message)

    def _check_port(self, host: str, port: int, timeout: float = 2.0) -> bool:
        """Check if a port is open."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host.replace("http://", "").replace("https://", ""), port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def check_ollama_server(self) -> CheckResult:
        """Check if Ollama server is running."""
        host = self.ollama_host.replace("http://", "").replace("https://", "").split(":")[0]
        port = 11434

        if not self._check_port(host, port):
            # Try to auto-start Ollama
            if self.auto_fix:
                try:
                    # Check if ollama binary exists
                    result = subprocess.run(
                        ["which", "ollama"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        self._print("   Starting Ollama server...", "yellow")
                        # Start ollama in background
                        subprocess.Popen(
                            ["ollama", "serve"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True
                        )
                        time.sleep(3)  # Wait for startup

                        # Check again
                        if self._check_port(host, port):
                            return CheckResult(
                                name="Ollama Server",
                                status=Status.FIXED,
                                message="Ollama server was not running - started automatically",
                                fix_applied=True
                            )
                except Exception as e:
                    pass

            return CheckResult(
                name="Ollama Server",
                status=Status.ERROR,
                message=f"Ollama server not running on {self.ollama_host}",
                details={"host": host, "port": port},
                fix_command="ollama serve"
            )

        return CheckResult(
            name="Ollama Server",
            status=Status.OK,
            message=f"Ollama server running on {self.ollama_host}"
        )

    def check_ollama_models(self) -> CheckResult:
        """Check if required Ollama models are available."""
        if not HAS_REQUESTS:
            return CheckResult(
                name="Ollama Models",
                status=Status.WARNING,
                message="Cannot check models - requests library not available"
            )

        try:
            resp = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            if resp.status_code != 200:
                return CheckResult(
                    name="Ollama Models",
                    status=Status.ERROR,
                    message=f"Cannot list models: HTTP {resp.status_code}"
                )

            data = resp.json()
            available_models = [m.get("name", "") for m in data.get("models", [])]

            # Check for configured model first
            configured_model = os.getenv("NLP2CMD_PLANNER_MODEL", "qwen2.5:3b")

            if configured_model in available_models:
                return CheckResult(
                    name="Ollama Models",
                    status=Status.OK,
                    message=f"Required model '{configured_model}' is available",
                    details={"available": available_models, "required": configured_model}
                )

            # Check for any fallback model
            for model in self.required_models:
                if model in available_models:
                    return CheckResult(
                        name="Ollama Models",
                        status=Status.WARNING,
                        message=f"Preferred model '{configured_model}' not found, but '{model}' is available",
                        details={"available": available_models, "preferred": configured_model, "using": model}
                    )

            # No suitable model found - try to pull
            if self.auto_fix:
                model_to_pull = configured_model if ":" in configured_model else "qwen2.5:3b"
                self._print(f"   Pulling model {model_to_pull}...", "yellow")
                try:
                    result = subprocess.run(
                        ["ollama", "pull", model_to_pull],
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    if result.returncode == 0:
                        return CheckResult(
                            name="Ollama Models",
                            status=Status.FIXED,
                            message=f"Model '{model_to_pull}' pulled successfully",
                            fix_applied=True
                        )
                except Exception as e:
                    pass

            return CheckResult(
                name="Ollama Models",
                status=Status.ERROR,
                message=f"No suitable model found. Required: {configured_model}",
                details={"available": available_models, "required": configured_model},
                fix_command=f"ollama pull {configured_model}"
            )

        except requests.exceptions.ConnectionError:
            return CheckResult(
                name="Ollama Models",
                status=Status.ERROR,
                message="Cannot connect to Ollama server"
            )
        except Exception as e:
            return CheckResult(
                name="Ollama Models",
                status=Status.ERROR,
                message=f"Error checking models: {e}"
            )

    def check_hf_token(self) -> CheckResult:
        """Check HuggingFace token configuration."""
        token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")

        if token:
            # Mask token for display
            masked = token[:4] + "..." + token[-4:] if len(token) > 8 else "***"
            return CheckResult(
                name="HF Token",
                status=Status.OK,
                message=f"HF_TOKEN configured ({masked})",
                details={"token_length": len(token)}
            )

        # Check if huggingface-cli is configured
        hf_home = Path.home() / ".huggingface"
        token_file = hf_home / "token"

        if token_file.exists():
            return CheckResult(
                name="HF Token",
                status=Status.WARNING,
                message="Token found in ~/.huggingface/token but HF_TOKEN not set",
                details={"token_file": str(token_file)},
                fix_command="export HF_TOKEN=$(cat ~/.huggingface/token)"
            )

        return CheckResult(
            name="HF Token",
            status=Status.WARNING,
            message="HF_TOKEN not set - unauthenticated requests may be rate limited",
            details={"hint": "Get token from https://huggingface.co/settings/tokens"},
            fix_command="export HF_TOKEN=your_token_here"
        )

    def check_playwright(self) -> CheckResult:
        """Check Playwright browser installation."""
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browsers = []
                for browser_type in [p.chromium, p.firefox, p.webkit]:
                    try:
                        browser_type.executable_path
                        browsers.append(browser_type.name)
                    except Exception:
                        pass

                if browsers:
                    return CheckResult(
                        name="Playwright",
                        status=Status.OK,
                        message=f"Playwright ready with {', '.join(browsers)}",
                        details={"browsers": browsers}
                    )
                else:
                    return CheckResult(
                        name="Playwright",
                        status=Status.ERROR,
                        message="No browsers installed",
                        fix_command="playwright install chromium"
                    )
        except ImportError:
            return CheckResult(
                name="Playwright",
                status=Status.WARNING,
                message="Playwright not installed - web automation will use fallback",
                fix_command="pip install playwright && playwright install chromium"
            )
        except Exception as e:
            if "sync api inside the asyncio loop" in str(e).lower():
                return CheckResult(
                    name="Playwright",
                    status=Status.WARNING,
                    message="Playwright check skipped in active asyncio loop (runtime may still be OK)",
                    details={"error": str(e)},
                    fix_command="Run `nlp2cmd doctor` from a regular shell (outside async loop) for full check",
                )
            return CheckResult(
                name="Playwright",
                status=Status.ERROR,
                message=f"Playwright error: {e}",
                fix_command="playwright install"
            )

    def check_visual_stream_tools(self) -> CheckResult:
        """Check prerequisites for visual stream recording (vnc/novnc/xvfb)."""
        vnc_server = shutil.which("vncserver")
        novnc_proxy = shutil.which("novnc_proxy")
        xvfb_run = shutil.which("xvfb-run")

        details = {
            "vncserver": bool(vnc_server),
            "novnc_proxy": bool(novnc_proxy),
            "xvfb_run": bool(xvfb_run),
        }

        if vnc_server and novnc_proxy:
            return CheckResult(
                name="Visual Streams",
                status=Status.OK,
                message="VNC/noVNC tooling detected",
                details=details,
            )

        if xvfb_run:
            return CheckResult(
                name="Visual Streams",
                status=Status.WARNING,
                message="VNC/noVNC not fully configured (xvfb-run available as fallback)",
                details=details,
                fix_command="Install VNC + noVNC for --source vnc/novnc video recording",
            )

        return CheckResult(
            name="Visual Streams",
            status=Status.WARNING,
            message="No visual stream backend detected (vnc/novnc/xvfb)",
            details=details,
            fix_command="Install at least one backend (recommended: VNC + noVNC, or xvfb-run)",
        )

    def check_environment(self) -> CheckResult:
        """Check environment configuration."""
        issues = []
        details = {}

        # Check Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        details["python_version"] = python_version

        if sys.version_info < (3, 9):
            issues.append(f"Python {python_version} is old (recommend 3.9+)")

        # Check .env file
        env_file = Path(".env")
        if env_file.exists():
            details["env_file"] = str(env_file)
        else:
            details["env_file"] = None

        # Check for common env vars
        env_vars = {
            "OLLAMA_BASE_URL": os.getenv("OLLAMA_BASE_URL", "default: http://localhost:11434"),
            "NLP2CMD_PLANNER_MODEL": os.getenv("NLP2CMD_PLANNER_MODEL", "default: qwen2.5:3b"),
            "CANVAS_LLM_TIMEOUT": os.getenv("CANVAS_LLM_TIMEOUT", "default: 60"),
        }
        details["env_vars"] = env_vars

        if issues:
            return CheckResult(
                name="Environment",
                status=Status.WARNING,
                message="; ".join(issues),
                details=details
            )

        return CheckResult(
            name="Environment",
            status=Status.OK,
            message=f"Python {python_version}, configuration OK",
            details=details
        )

    def check_dependencies(self) -> CheckResult:
        """Check critical Python dependencies."""
        critical_deps = [
            "requests",
            "transformers",
            "torch",
            "sentence_transformers",
            "click",
            "rich",
        ]

        missing = []
        installed = []

        for dep in critical_deps:
            try:
                __import__(dep)
                installed.append(dep)
            except ImportError:
                missing.append(dep)

        if missing:
            return CheckResult(
                name="Dependencies",
                status=Status.ERROR,
                message=f"Missing: {', '.join(missing)}",
                details={"installed": installed, "missing": missing},
                fix_command=f"pip install {' '.join(missing)}"
            )

        return CheckResult(
            name="Dependencies",
            status=Status.OK,
            message=f"All critical dependencies installed ({len(installed)} packages)"
        )

    def run_all_checks(self) -> list[CheckResult]:
        """Run all diagnostic checks."""
        checks = [
            self.check_ollama_server,
            self.check_ollama_models,
            self.check_hf_token,
            self.check_playwright,
            self.check_visual_stream_tools,
            self.check_environment,
            self.check_dependencies,
        ]

        self._print("\n[bold cyan]🔍 NLP2CMD System Doctor[/bold cyan]\n" if HAS_RICH else "\n🔍 NLP2CMD System Doctor\n")

        for check_func in checks:
            result = check_func()
            self.results.append(result)
            self._display_result(result)

        return self.results

    def _display_result(self, result: CheckResult):
        """Display a check result."""
        if HAS_RICH and self.console:
            icons = {
                Status.OK: "[green]✓[/green]",
                Status.WARNING: "[yellow]⚠[/yellow]",
                Status.ERROR: "[red]✗[/red]",
                Status.INFO: "[blue]ℹ[/blue]",
                Status.FIXED: "[green]🔧[/green]",
            }
            icon = icons.get(result.status, "?")
            self.console.print(f"{icon} [bold]{result.name}:[/bold] {result.message}")

            if result.fix_command and not result.fix_applied:
                self.console.print(f"   [dim]Fix: {result.fix_command}[/dim]")
        else:
            icons = {
                Status.OK: "✓",
                Status.WARNING: "⚠",
                Status.ERROR: "✗",
                Status.INFO: "ℹ",
                Status.FIXED: "🔧",
            }
            icon = icons.get(result.status, "?")
            print(f"{icon} {result.name}: {result.message}")
            if result.fix_command and not result.fix_applied:
                print(f"   Fix: {result.fix_command}")

    def print_summary(self):
        """Print summary of all checks."""
        ok = sum(1 for r in self.results if r.status == Status.OK)
        fixed = sum(1 for r in self.results if r.status == Status.FIXED)
        warnings = sum(1 for r in self.results if r.status == Status.WARNING)
        errors = sum(1 for r in self.results if r.status == Status.ERROR)

        if HAS_RICH and self.console:
            table = Table(title="Summary")
            table.add_column("Status", justify="center")
            table.add_column("Count", justify="right")
            table.add_row("[green]OK[/green]", str(ok))
            if fixed:
                table.add_row("[green]Fixed[/green]", str(fixed))
            if warnings:
                table.add_row("[yellow]Warnings[/yellow]", str(warnings))
            if errors:
                table.add_row("[red]Errors[/red]", str(errors))

            self.console.print("\n")
            self.console.print(table)

            if errors > 0:
                self.console.print("\n[red bold]❌ System has errors - fix before running nlp2cmd[/red bold]")
            elif warnings > 0:
                self.console.print("\n[yellow bold]⚠ System has warnings - nlp2cmd may work with limitations[/yellow bold]")
            else:
                self.console.print("\n[green bold]✅ System is ready![/green bold]")
        else:
            print(f"\n--- Summary ---")
            print(f"OK: {ok}")
            if fixed:
                print(f"Fixed: {fixed}")
            if warnings:
                print(f"Warnings: {warnings}")
            if errors:
                print(f"Errors: {errors}")

            if errors > 0:
                print("\n❌ System has errors - fix before running nlp2cmd")
            elif warnings > 0:
                print("\n⚠ System has warnings - nlp2cmd may work with limitations")
            else:
                print("\n✅ System is ready!")

    def generate_fix_script(self) -> str:
        """Generate a shell script with all fixes."""
        commands = []
        for result in self.results:
            if result.fix_command and not result.fix_applied:
                commands.append(f"# {result.name}: {result.message}")
                commands.append(result.fix_command)
                commands.append("")

        if not commands:
            return "# No fixes needed - system is ready!"

        return "#!/bin/bash\n# NLP2CMD Doctor Fix Script\n\n" + "\n".join(commands)


def run_doctor(auto_fix: bool = False, output_json: bool = False, fix_script: Optional[str] = None):
    """Run the doctor diagnostic."""
    console = Console() if HAS_RICH else None

    doctor = NP2CMDDoctor(console=console, auto_fix=auto_fix)
    results = doctor.run_all_checks()
    doctor.print_summary()

    if output_json:
        # JSON output for programmatic use
        output = {
            "results": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "message": r.message,
                    "details": r.details,
                    "fix_applied": r.fix_applied,
                    "fix_command": r.fix_command,
                }
                for r in results
            ],
            "summary": {
                "ok": sum(1 for r in results if r.status == Status.OK),
                "fixed": sum(1 for r in results if r.status == Status.FIXED),
                "warnings": sum(1 for r in results if r.status == Status.WARNING),
                "errors": sum(1 for r in results if r.status == Status.ERROR),
                "ready": not any(r.status == Status.ERROR for r in results),
            }
        }
        print(json.dumps(output, indent=2))
        return output["summary"]["ready"]

    if fix_script:
        script = doctor.generate_fix_script()
        Path(fix_script).write_text(script)
        print(f"\nFix script written to: {fix_script}")
        print("Run with: bash " + fix_script)

    # Return exit code based on errors
    has_errors = any(r.status == Status.ERROR for r in results)
    return not has_errors


def get_hf_token_via_browser(console: Optional[Console] = None) -> Optional[str]:
    """Open browser to help user get HF_TOKEN from Hugging Face.
    
    Browser priority:
    1. Connect to existing browser (Firefox/Chrome via CDP)
    2. Open new system browser (firefox/chrome commands)
    3. Use Playwright (requires manual login)
    
    Returns the token if successfully retrieved.
    """
    if console:
        console.print("[cyan]🌐 Opening Hugging Face in browser...[/cyan]")
    else:
        print("🌐 Opening Hugging Face in browser...")
    
    # Try priority 1: Connect to existing browser
    token = _try_existing_browser(console)
    if token:
        return token
    
    # Try priority 2: Open new system browser
    token = _try_system_browser(console)
    if token:
        return token
    
    # Try priority 3: Use Playwright
    token = _try_playwright_browser(console)
    if token:
        return token
    
    return None


def _try_existing_browser(console: Optional[Console] = None) -> Optional[str]:
    """Try to connect to existing browser via CDP with detailed logging."""
    import socket
    
    if console:
        console.print("[dim]   [Stage 1/3] Checking for existing browser...[/dim]")
    
    # Check common CDP ports
    cdp_ports = [9222, 9223, 9224, 9333]
    found_port = None
    
    for port in cdp_ports:
        if console:
            console.print(f"[dim]     Checking port {port}...[/dim]")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", port))
            sock.close()
            
            if result == 0:
                found_port = port
                if console:
                    console.print(f"[green]     ✓ Found browser on port {port}[/green]")
                break
            else:
                if console:
                    console.print(f"[dim]     Port {port}: not available[/dim]")
        except Exception as e:
            if console:
                console.print(f"[dim]     Port {port}: error - {e}[/dim]")
    
    if not found_port:
        if console:
            console.print("[dim]     ℹ No existing browser with CDP found[/dim]")
            console.print("[dim]       Tip: Run 'firefox --remote-debugging-port=9222' first[/dim]")
        return None
    
    # Try to connect via Playwright CDP
    if console:
        console.print(f"[cyan]     → Connecting via Playwright to port {found_port}...[/cyan]")
    
    connection_success = False
    browser = None
    browser_type = None
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # Try Chrome/Chromium first
            try:
                browser = p.chromium.connect_over_cdp(f"http://localhost:{found_port}")
                browser_type = "Chrome/Chromium"
                connection_success = True
                if console:
                    console.print(f"[green]     ✓ Connected to {browser_type} via CDP[/green]")
            except Exception as chrome_err:
                if console:
                    console.print(f"[dim]     Chromium CDP failed: {str(chrome_err)[:50]}...[/dim]")
                
                # Try Firefox
                try:
                    browser = p.firefox.connect_over_cdp(f"http://localhost:{found_port}")
                    browser_type = "Firefox"
                    connection_success = True
                    if console:
                        console.print(f"[green]     ✓ Connected to Firefox via CDP[/green]")
                except Exception as firefox_err:
                    if console:
                        console.print(f"[red]     ✗ CDP connection failed for both browsers[/red]")
                        console.print(f"[dim]       Chrome error: {str(chrome_err)[:30]}...[/dim]")
                        console.print(f"[dim]       Firefox error: {str(firefox_err)[:30]}...[/dim]")
                    return None
            
            if not connection_success or not browser:
                if console:
                    console.print(f"[red]     ✗ Browser connection established but browser object is None[/red]")
                return None
            
            # Create new context and page
            if console:
                console.print(f"[dim]     Creating browser context...[/dim]")
            
            try:
                context = browser.new_context()
                page = context.new_page()
                if console:
                    console.print(f"[green]     ✓ Browser context created[/green]")
            except Exception as ctx_err:
                if console:
                    console.print(f"[red]     ✗ Failed to create browser context: {ctx_err}[/red]")
                return None
            
            # Navigate
            if console:
                console.print(f"[cyan]     → Navigating to huggingface.co...[/cyan]")
            
            nav_success = False
            expected_url_pattern = "huggingface.co/settings/tokens"
            actual_url = None
            
            try:
                page.goto("https://huggingface.co/settings/tokens", timeout=30000)
                actual_url = page.url
                
                # Verify we reached the expected page (or at least HF domain)
                if expected_url_pattern in actual_url:
                    nav_success = True
                    if console:
                        console.print(f"[green]     ✓ Page loaded at correct URL[/green]")
                elif "huggingface.co/login" in actual_url:
                    # This is expected if not logged in, but we should warn
                    nav_success = True  # Page loaded, just needs login
                    if console:
                        console.print(f"[yellow]     ⚠ Page loaded but requires login first[/yellow]")
                        console.print(f"[dim]       URL: {actual_url}[/dim]")
                elif "huggingface.co" in actual_url:
                    nav_success = True
                    if console:
                        console.print(f"[yellow]     ⚠ Page loaded on HF domain but different path[/yellow]")
                        console.print(f"[dim]       URL: {actual_url}[/dim]")
                else:
                    if console:
                        console.print(f"[red]     ✗ Page loaded but unexpected URL[/red]")
                        console.print(f"[dim]       Expected: {expected_url_pattern}[/dim]")
                        console.print(f"[dim]       Actual: {actual_url}[/dim]")
                        
            except Exception as e:
                if console:
                    console.print(f"[red]     ✗ Navigation failed: {e}[/red]")
                    if actual_url:
                        console.print(f"[dim]       Last URL: {actual_url}[/dim]")
                    nav_success = False
            
    except ImportError:
        if console:
            console.print(f"[red]     ✗ Playwright not installed[/red]")
        return None
    except Exception as e:
        if console:
            console.print(f"[red]     ✗ CDP connection error: {e}[/red]")
        return None


def _try_system_browser(console: Optional[Console] = None) -> Optional[str]:
    """Try to open new system browser with detailed stage logging."""
    import subprocess
    import time
    import socket
    
    if console:
        console.print("[dim]   [Stage 2/3] Opening system browser...[/dim]")
    
    # Try to open Firefox or Chrome/Chromium
    browsers_to_try = [
        ("firefox", ["firefox", "--new-window", "--remote-debugging-port=9222"]),
        ("google-chrome", ["google-chrome", "--new-window", "--remote-debugging-port=9222"]),
        ("chromium", ["chromium", "--new-window", "--remote-debugging-port=9222"]),
        ("chromium-browser", ["chromium-browser", "--new-window", "--remote-debugging-port=9222"]),
    ]
    
    for browser_name, cmd in browsers_to_try:
        try:
            # Stage 2.1: Check if browser binary exists
            if console:
                console.print(f"[dim]     Checking {browser_name}...[/dim]")
            
            result = subprocess.run(["which", browser_name], capture_output=True, timeout=5)
            if result.returncode != 0:
                if console:
                    console.print(f"[dim]     ✗ {browser_name} not found[/dim]")
                continue
            
            if console:
                console.print(f"[cyan]     → Launching {browser_name}...[/cyan]")
            
            # Stage 2.2: Launch browser with CDP enabled
            try:
                process = subprocess.Popen(
                    cmd + ["about:blank"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                if console:
                    console.print(f"[dim]     PID: {process.pid}[/dim]")
            except Exception as e:
                if console:
                    console.print(f"[red]     ✗ Failed to launch: {e}[/red]")
                continue
            
            # Stage 2.3: Wait for browser to initialize
            if console:
                console.print("[dim]     Waiting for browser to start (3s)...[/dim]")
            time.sleep(3)
            
            # Stage 2.4: Try to connect via CDP (with actual protocol verification)
            if console:
                console.print("[dim]     Checking CDP port 9222 (with protocol verification)...[/dim]")
            
            cdp_available = False
            for attempt in range(5):
                try:
                    # First: basic TCP check
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex(("localhost", 9222))
                    sock.close()
                    
                    if result == 0:
                        # Second: verify it's actually a CDP endpoint by making HTTP request
                        import urllib.request
                        try:
                            response = urllib.request.urlopen(
                                "http://localhost:9222/json/version", 
                                timeout=3
                            )
                            cdp_info = response.read().decode('utf-8')
                            if 'Browser' in cdp_info or 'Protocol-Version' in cdp_info:
                                cdp_available = True
                                if console:
                                    console.print(f"[green]     ✓ CDP port 9222 ready (verified protocol)[/green]")
                                break
                            else:
                                if console:
                                    console.print(f"[dim]     Attempt {attempt+1}/5: port open but not CDP protocol[/dim]")
                        except Exception as http_err:
                            if console:
                                console.print(f"[dim]     Attempt {attempt+1}/5: port open but CDP check failed: {str(http_err)[:40]}[/dim]")
                    else:
                        if console:
                            console.print(f"[dim]     Attempt {attempt+1}/5: port not ready (code: {result})[/dim]")
                except Exception as e:
                    if console:
                        console.print(f"[dim]     Attempt {attempt+1}/5: {str(e)[:40]}[/dim]")
                time.sleep(1)
            
            if not cdp_available:
                if console:
                    console.print(f"[yellow]     ✗ CDP not available after 5 attempts[/yellow]")
                    console.print(f"[dim]       Browser launched but CDP protocol not responding[/dim]")
                continue
            
            # Stage 2.5: Connect with Playwright
            if console:
                console.print(f"[cyan]     → Connecting via Playwright CDP...[/cyan]")
            
            connection_success = False
            browser = None
            
            try:
                from playwright.sync_api import sync_playwright
                
                with sync_playwright() as p:
                    try:
                        browser = p.chromium.connect_over_cdp("http://localhost:9222")
                        connection_success = True
                        if console:
                            console.print(f"[green]     ✓ Connected to {browser_name} via CDP[/green]")
                    except Exception as e:
                        if console:
                            console.print(f"[yellow]     ⚠ CDP connect failed: {str(e)[:50]}...[/yellow]")
                            console.print(f"[dim]     Falling back to manual mode...[/dim]")
                        return _manual_browser_instructions(console, browser_name)
                    
                    if not connection_success or not browser:
                        if console:
                            console.print(f"[red]     ✗ Connection reported success but browser is None[/red]")
                        return _manual_browser_instructions(console, browser_name)
                    
                    try:
                        context = browser.new_context()
                        page = context.new_page()
                        if console:
                            console.print(f"[green]     ✓ Browser context created[/green]")
                    except Exception as ctx_err:
                        if console:
                            console.print(f"[red]     ✗ Failed to create context: {ctx_err}[/red]")
                        return _manual_browser_instructions(console, browser_name)
                    
                    # Stage 2.6: Navigate to HF
                    if console:
                        console.print(f"[cyan]     → Navigating to huggingface.co...[/cyan]")
                    
                    nav_success = False
                    expected_url_pattern = "huggingface.co/settings/tokens"
                    actual_url = None
                    
                    try:
                        page.goto("https://huggingface.co/settings/tokens", timeout=30000)
                        actual_url = page.url
                        
                        # Verify we reached the expected page (or at least HF domain)
                        if expected_url_pattern in actual_url:
                            nav_success = True
                            if console:
                                console.print(f"[green]     ✓ Page loaded at correct URL[/green]")
                        elif "huggingface.co/login" in actual_url:
                            nav_success = True  # Page loaded, just needs login
                            if console:
                                console.print(f"[yellow]     ⚠ Page loaded but requires login first[/yellow]")
                                console.print(f"[dim]       URL: {actual_url}[/dim]")
                        elif "huggingface.co" in actual_url:
                            nav_success = True
                            if console:
                                console.print(f"[yellow]     ⚠ Page loaded on HF domain but different path[/yellow]")
                                console.print(f"[dim]       URL: {actual_url}[/dim]")
                        else:
                            if console:
                                console.print(f"[red]     ✗ Page loaded but unexpected URL[/red]")
                                console.print(f"[dim]       Expected: {expected_url_pattern}[/dim]")
                                console.print(f"[dim]       Actual: {actual_url}[/dim]")
                                
                    except Exception as e:
                        if console:
                            console.print(f"[red]     ✗ Navigation failed: {e}[/red]")
                            if actual_url:
                                console.print(f"[dim]       Last URL: {actual_url}[/dim]")
                        nav_success = False
                    
                    # Stage 2.7: Get token from user (even if nav had issues, let user try)
                    if nav_success or actual_url:  # Only proceed if we at least loaded something
                        return _navigate_and_get_token(page, console, browser_name)
                    else:
                        if console:
                            console.print(f"[red]     ✗ Cannot proceed - page did not load[/red]")
                        return None
                    
            except ImportError:
                if console:
                    console.print(f"[red]     ✗ Playwright not installed[/red]")
                return _manual_browser_instructions(console, browser_name)
            except Exception as e:
                if console:
                    console.print(f"[red]     ✗ Playwright error: {e}[/red]")
                return _manual_browser_instructions(console, browser_name)
                        
        except Exception as e:
            if console:
                console.print(f"[red]   ✗ Error with {browser_name}: {e}[/red]")
            continue
    
    if console:
        console.print("[red]   ✗ No system browser could be opened[/red]")
    return None


def _try_playwright_browser(console: Optional[Console] = None) -> Optional[str]:
    """Last resort: Use Playwright to launch browser with detailed logging."""
    try:
        from playwright.sync_api import sync_playwright
        
        if console:
            console.print("[dim]   [Stage 3/3] Using Playwright (last resort)...[/dim]")
            console.print("[yellow]     ⚠ Note: You'll need to login manually[/yellow]")
        else:
            print("   [Stage 3/3] Using Playwright (you may need to login manually)...")
        
        with sync_playwright() as p:
            # Try Firefox first (better privacy)
            browser_type = "firefox"
            try:
                if console:
                    console.print("[dim]     Launching Firefox...[/dim]")
                browser = p.firefox.launch(headless=False)
                if console:
                    console.print("[green]     ✓ Firefox launched[/green]")
            except Exception as firefox_err:
                if console:
                    console.print(f"[dim]     Firefox failed: {firefox_err}[/dim]")
                    console.print("[dim]     Trying Chromium...[/dim]")
                
                try:
                    browser = p.chromium.launch(headless=False)
                    browser_type = "chromium"
                    if console:
                        console.print("[green]     ✓ Chromium launched[/green]")
                except Exception as chromium_err:
                    if console:
                        console.print(f"[red]     ✗ Both browsers failed[/red]")
                    return None
            
            # Create context and page
            if console:
                console.print("[dim]     Creating browser context...[/dim]")
            
            context = browser.new_context()
            page = context.new_page()
            
            # Navigate
            if console:
                console.print(f"[cyan]     → Navigating to huggingface.co...[/cyan]")
            
            nav_success = False
            expected_url_pattern = "huggingface.co/settings/tokens"
            actual_url = None
            
            try:
                page.goto("https://huggingface.co/settings/tokens", timeout=30000)
                actual_url = page.url
                
                # Verify we reached the expected page (or at least HF domain)
                if expected_url_pattern in actual_url:
                    nav_success = True
                    if console:
                        console.print(f"[green]     ✓ Page loaded at correct URL[/green]")
                elif "huggingface.co/login" in actual_url:
                    nav_success = True
                    if console:
                        console.print(f"[yellow]     ⚠ Page loaded but requires login first[/yellow]")
                        console.print(f"[dim]       URL: {actual_url}[/dim]")
                elif "huggingface.co" in actual_url:
                    nav_success = True
                    if console:
                        console.print(f"[yellow]     ⚠ Page loaded on HF domain but different path[/yellow]")
                        console.print(f"[dim]       URL: {actual_url}[/dim]")
                else:
                    if console:
                        console.print(f"[red]     ✗ Page loaded but unexpected URL[/red]")
                        console.print(f"[dim]       Expected: {expected_url_pattern}[/dim]")
                        console.print(f"[dim]       Actual: {actual_url}[/dim]")
                        
            except Exception as e:
                if console:
                    console.print(f"[red]     ✗ Navigation failed: {e}[/red]")
                    if actual_url:
                        console.print(f"[dim]       Last URL: {actual_url}[/dim]")
                nav_success = False
            
            # Only proceed if page loaded
            if nav_success or actual_url:
                return _navigate_and_get_token(page, console, browser_type)
            else:
                if console:
                    console.print(f"[red]     ✗ Cannot proceed - page did not load[/red]")
                return None
            
    except ImportError:
        if console:
            console.print("[red]     ✗ Playwright not installed[/red]")
        else:
            print("     ✗ Playwright not installed")
        return None
    except Exception as e:
        if console:
            console.print(f"[red]     ✗ Playwright error: {e}[/red]")
        else:
            print(f"     ✗ Playwright error: {e}")
        return None


def _navigate_and_get_token(page, console: Optional[Console], browser_type: str) -> Optional[str]:
    """Navigate to HuggingFace and get token from user."""
    
    if console:
        console.print(f"[dim]       [Token Step 1/4] Already navigated to HF tokens page[/dim]")
    
    # Verify page loaded by checking URL
    try:
        current_url = page.url
        if console:
            console.print(f"[dim]       Current URL: {current_url}[/dim]")
    except Exception as e:
        if console:
            console.print(f"[yellow]       ⚠ Could not get URL: {e}[/yellow]")
    
    # Show instructions
    if console:
        console.print(f"[cyan]       [Token Step 2/4] Showing instructions:[/cyan]")
        console.print("         1. Login to Hugging Face if needed")
        console.print("         2. Click 'New token' button")
        console.print("         3. Set name: 'nlp2cmd'")
        console.print("         4. Select 'Read' role")
        console.print("         5. Click 'Generate token'")
        console.print("         6. Copy the token and paste it here")
    else:
        print("\n📋 Instructions:")
        print("   1. Login to Hugging Face if needed")
        print("   2. Click 'New token' button")
        print("   3. Set name: 'nlp2cmd'")
        print("   4. Select 'Read' role")
        print("   5. Click 'Generate token'")
        print("   6. Copy the token and paste it here")
    
    # Interactive prompt for token
    if console:
        console.print(f"[cyan]       [Token Step 3/4] Waiting for user input...[/cyan]")
        console.print(f"[bold yellow]       ⚠️  CHECK YOUR TERMINAL - waiting for token input![/bold yellow]")
        console.print(f"[bold]       The browser should be open.[/bold]")
        console.print(f"[bold]       After you create the token in the browser, come back here and paste it below.[/bold]")
    
    try:
        # Print visible separator to catch attention
        print("\n" + "="*60)
        print("🔐 ENTER YOUR HF_TOKEN BELOW 🔐")
        print("="*60)
        
        token = input("🔑 Paste HF_TOKEN here: ").strip()
        
        print("="*60)
        
        if console:
            console.print(f"[dim]       Input received: {'Yes' if token else 'No'}[/dim]")
        
        if token:
            if console:
                console.print(f"[cyan]       [Token Step 4/4] Closing browser page...[/cyan]")
            
            try:
                page.close()
                if console:
                    console.print(f"[green]       ✓ Page closed[/green]")
            except Exception as e:
                if console:
                    console.print(f"[dim]       Note: Could not close page: {e}[/dim]")
            
            return token
        else:
            if console:
                console.print(f"[yellow]       ⚠ No token entered[/yellow]")
    except EOFError:
        if console:
            console.print(f"[red]       ✗ EOFError (no input available)[/red]")
    except KeyboardInterrupt:
        if console:
            console.print(f"[yellow]       ⚠ User cancelled (KeyboardInterrupt)[/yellow]")
    except Exception as e:
        if console:
            console.print(f"[red]       ✗ Error getting input: {e}[/red]")
    
    # Cleanup on failure
    if console:
        console.print(f"[dim]       Cleaning up...[/dim]")
    
    try:
        page.close()
    except Exception:
        pass
    
    return None


def _manual_browser_instructions(console: Optional[Console], browser_name: str) -> Optional[str]:
    """Show manual instructions when browser automation fails."""
    if console:
        console.print(f"\n[cyan]📋 {browser_name} opened. Please:[/cyan]")
        console.print("   1. Go to: https://huggingface.co/settings/tokens")
        console.print("   2. Login if not logged in")
        console.print("   3. Create new token (name: nlp2cmd, role: read)")
        console.print("   4. Copy the token")
    else:
        print(f"\n📋 {browser_name} opened. Please:")
        print("   1. Go to: https://huggingface.co/settings/tokens")
        print("   2. Login if not logged in")
        print("   3. Create new token (name: nlp2cmd, role: read)")
        print("   4. Copy the token")
    
    try:
        token = input("\n🔑 Paste HF_TOKEN here: ").strip()
        if token:
            return token
    except (EOFError, KeyboardInterrupt):
        pass
    
    return None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="NLP2CMD System Doctor")
    parser.add_argument("--fix", action="store_true", help="Auto-fix issues where possible")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of formatted text")
    parser.add_argument("--fix-script", type=str, help="Generate fix script to file")
    parser.add_argument("--get-token", action="store_true", help="Open browser to get HF_TOKEN")
    args = parser.parse_args()

    if args.get_token:
        console = Console() if HAS_RICH else None
        token = get_hf_token_via_browser(console)
        if token:
            # Save token
            env_file = Path(".env")
            if env_file.exists():
                content = env_file.read_text()
                if "HF_TOKEN=" in content:
                    lines = content.split("\n")
                    new_lines = [f"HF_TOKEN={token}" if l.startswith("HF_TOKEN=") else l for l in lines]
                    content = "\n".join(new_lines)
                else:
                    content += f"\nHF_TOKEN={token}\n"
                env_file.write_text(content)
            else:
                env_file.write_text(f"HF_TOKEN={token}\n")
            
            os.environ["HF_TOKEN"] = token
            if console:
                console.print(f"[green]✓ HF_TOKEN saved to {env_file}[/green]")
            else:
                print(f"✓ HF_TOKEN saved to {env_file}")
            sys.exit(0)
        else:
            print("✗ Failed to get token")
            sys.exit(1)

    success = run_doctor(auto_fix=args.fix, output_json=args.json, fix_script=args.fix_script)
    sys.exit(0 if success else 1)


# Click CLI integration
try:
    import click

    @click.command(name="doctor")
    @click.option("--fix", is_flag=True, help="Auto-fix issues where possible")
    @click.option("--json", "output_json", is_flag=True, help="Output JSON instead of formatted text")
    @click.option("--fix-script", type=click.Path(), help="Generate fix script to file")
    @click.option("--set-token", help="Set HF_TOKEN to .env file")
    @click.option("--get-token", is_flag=True, help="Open browser to get HF_TOKEN from Hugging Face")
    @click.pass_context
    def doctor_command(ctx, fix: bool, output_json: bool, fix_script: Optional[str], set_token: Optional[str], get_token: bool):
        """Diagnose and fix nlp2cmd system issues."""
        console = Console() if HAS_RICH else None
        
        if get_token:
            token = get_hf_token_via_browser(console)
            if token:
                # Save token
                env_file = Path(".env")
                if env_file.exists():
                    content = env_file.read_text()
                    if "HF_TOKEN=" in content:
                        lines = content.split("\n")
                        new_lines = [f"HF_TOKEN={token}" if l.startswith("HF_TOKEN=") else l for l in lines]
                        content = "\n".join(new_lines)
                    else:
                        content += f"\nHF_TOKEN={token}\n"
                    env_file.write_text(content)
                else:
                    env_file.write_text(f"HF_TOKEN={token}\n")
                
                os.environ["HF_TOKEN"] = token
                if console:
                    console.print(f"[green]✓ HF_TOKEN saved to {env_file}[/green]")
                else:
                    print(f"✓ HF_TOKEN saved to {env_file}")
                ctx.exit(0)
            else:
                print("✗ Failed to get token")
                ctx.exit(1)
        
        if set_token:
            # Write token to .env file
            env_file = Path(".env")
            token_line = f"HF_TOKEN={set_token}\n"
            
            if env_file.exists():
                content = env_file.read_text()
                # Replace existing HF_TOKEN or append
                if "HF_TOKEN=" in content:
                    lines = content.split("\n")
                    new_lines = []
                    for line in lines:
                        if line.startswith("HF_TOKEN="):
                            new_lines.append(f"HF_TOKEN={set_token}")
                        else:
                            new_lines.append(line)
                    content = "\n".join(new_lines)
                else:
                    content += f"\n{token_line}"
                env_file.write_text(content)
            else:
                env_file.write_text(token_line)
            
            # Also set for current session
            os.environ["HF_TOKEN"] = set_token
            
            if console:
                console.print(f"[green]✓ HF_TOKEN saved to {env_file} and set for current session[/green]")
            else:
                print(f"✓ HF_TOKEN saved to {env_file}")
            ctx.exit(0)
        
        success = run_doctor(auto_fix=fix, output_json=output_json, fix_script=fix_script)
        ctx.exit(0 if success else 1)

except ImportError:
    # Click not available - define stub
    def doctor_command(*args, **kwargs):
        pass
