"""
NLP2CMD Auto-Repair System - Automatic error recovery via Doctor.

This module provides a catch-all error handler that:
1. Intercepts any command execution failure
2. Invokes Doctor to diagnose and auto-fix the issue
3. Retries the original user command after successful repair

Usage:
    from nlp2cmd.cli.auto_repair import with_auto_repair
    
    @with_auto_repair
    def execute_user_command(query, **kwargs):
        # ... command execution ...
        pass
"""

from __future__ import annotations

import os
import sys
import traceback
import time
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar
from functools import wraps
from dataclasses import dataclass
from enum import Enum

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    Console = None

T = TypeVar('T')


class ErrorCategory(Enum):
    """Categories of errors that Doctor can handle."""
    MISSING_TOKEN = "missing_token"
    MISSING_DEPENDENCY = "missing_dependency"
    SERVICE_UNAVAILABLE = "service_unavailable"
    NETWORK_ERROR = "network_error"
    PERMISSION_DENIED = "permission_denied"
    CONFIGURATION_ERROR = "configuration_error"
    RESOURCE_NOT_FOUND = "resource_not_found"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class RepairResult:
    """Result of auto-repair attempt."""
    success: bool
    category: ErrorCategory
    fix_applied: str
    message: str
    retry_recommended: bool = False


class AutoRepairSystem:
    """Automatic error diagnosis and repair system."""
    
    def __init__(self, console: Optional[Console] = None, auto_confirm: bool = False):
        self.console = console
        self.auto_confirm = auto_confirm
        self.max_retries = 3
        self.retry_delay = 2.0
    
    def _print(self, message: str, style: str = ""):
        """Print with or without rich."""
        if self.console and HAS_RICH:
            self.console.print(message, style=style)
        else:
            print(message)
    
    def categorize_error(self, error: Exception, context: dict) -> ErrorCategory:
        """Categorize an error based on exception type and message."""
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        # Check for token/auth issues
        if any(x in error_str for x in ['token', 'hf_token', 'huggingface', 'authentication', 'unauthenticated']):
            return ErrorCategory.MISSING_TOKEN
        
        # Check for missing dependencies
        if any(x in error_str for x in ['modulenotfound', 'importerror', 'no module named']):
            return ErrorCategory.MISSING_DEPENDENCY
        
        # Check for service unavailable
        if any(x in error_str for x in ['connection', 'refused', 'timeout', 'unreachable', 'ollama']):
            return ErrorCategory.SERVICE_UNAVAILABLE
        
        # Check for network errors
        if any(x in error_str for x in ['network', 'dns', 'internet', 'offline']):
            return ErrorCategory.NETWORK_ERROR
        
        # Check for permissions
        if any(x in error_str for x in ['permission', 'access denied', 'forbidden', '401', '403']):
            return ErrorCategory.PERMISSION_DENIED
        
        # Check for configuration errors
        if any(x in error_str for x in ['config', 'configuration', 'env', 'variable']):
            return ErrorCategory.CONFIGURATION_ERROR
        
        # Check for resource not found
        if any(x in error_str for x in ['not found', '404', 'missing', 'does not exist']):
            return ErrorCategory.RESOURCE_NOT_FOUND
        
        return ErrorCategory.UNKNOWN
    
    def attempt_repair(self, category: ErrorCategory, error: Exception, context: dict) -> RepairResult:
        """Attempt to repair a specific category of error."""
        
        if category == ErrorCategory.MISSING_TOKEN:
            return self._repair_missing_token(context)
        
        elif category == ErrorCategory.MISSING_DEPENDENCY:
            return self._repair_missing_dependency(error, context)
        
        elif category == ErrorCategory.SERVICE_UNAVAILABLE:
            return self._repair_service_unavailable(error, context)
        
        elif category == ErrorCategory.CONFIGURATION_ERROR:
            return self._repair_configuration_error(error, context)
        
        elif category == ErrorCategory.PERMISSION_DENIED:
            return self._repair_permission_denied(error, context)
        
        else:
            return RepairResult(
                success=False,
                category=category,
                fix_applied="none",
                message=f"Cannot auto-fix {category.value} errors",
                retry_recommended=False
            )
    
    def _repair_missing_token(self, context: dict) -> RepairResult:
        """Repair missing HF_TOKEN by opening browser."""
        self._print("\n[cyan]🔧 Doctor: Missing HF_TOKEN detected[/cyan]", "cyan")
        
        # Check if we can use browser automation
        execute_web = context.get('execute_web', False)
        
        if not execute_web:
            self._print(
                "[yellow]   Cannot auto-fix without --execute-web flag.[/yellow]\n"
                "   Run with --execute-web to enable browser automation."
            )
            return RepairResult(
                success=False,
                category=ErrorCategory.MISSING_TOKEN,
                fix_applied="skipped",
                message="Needs --execute-web flag",
                retry_recommended=False
            )
        
        # Prompt user
        if not self.auto_confirm:
            self._print("[cyan]   I can automatically get HF_TOKEN from Hugging Face.[/cyan]")
            try:
                response = input("   Proceed? [Y/n]: ").strip().lower()
                if response not in ('', 'y', 'yes'):
                    return RepairResult(
                        success=False,
                        category=ErrorCategory.MISSING_TOKEN,
                        fix_applied="user_declined",
                        message="User declined auto-fix",
                        retry_recommended=False
                    )
            except (EOFError, KeyboardInterrupt):
                return RepairResult(
                    success=False,
                    category=ErrorCategory.MISSING_TOKEN,
                    fix_applied="user_aborted",
                    message="User aborted",
                    retry_recommended=False
                )
        
        # Attempt browser-based token retrieval
        try:
            from nlp2cmd.cli.commands.doctor import get_hf_token_via_browser
            
            self._print("[cyan]   Opening browser to get HF_TOKEN...[/cyan]")
            token = get_hf_token_via_browser(self.console)
            
            if token:
                # Save to .env
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
                
                # Set for current session
                os.environ["HF_TOKEN"] = token
                
                self._print("[green]✓ HF_TOKEN saved successfully![/green]")
                
                return RepairResult(
                    success=True,
                    category=ErrorCategory.MISSING_TOKEN,
                    fix_applied="browser_token_retrieval",
                    message="HF_TOKEN obtained and saved",
                    retry_recommended=True
                )
            else:
                return RepairResult(
                    success=False,
                    category=ErrorCategory.MISSING_TOKEN,
                    fix_applied="token_retrieval_failed",
                    message="Could not get token from browser",
                    retry_recommended=False
                )
                
        except Exception as e:
            self._print(f"[red]   Error during token retrieval: {e}[/red]")
            return RepairResult(
                success=False,
                category=ErrorCategory.MISSING_TOKEN,
                fix_applied="exception",
                message=str(e),
                retry_recommended=False
            )
    
    def _repair_missing_dependency(self, error: Exception, context: dict) -> RepairResult:
        """Attempt to install missing Python dependency."""
        error_str = str(error)
        
        # Extract module name
        module_match = None
        if "No module named" in error_str:
            module_match = error_str.split("'")[-2] if "'" in error_str else None
        elif "ModuleNotFoundError" in str(type(error)):
            module_match = error_str.strip().split()[-1]
        
        if not module_match:
            return RepairResult(
                success=False,
                category=ErrorCategory.MISSING_DEPENDENCY,
                fix_applied="none",
                message="Could not identify missing module",
                retry_recommended=False
            )
        
        self._print(f"\n[cyan]🔧 Doctor: Missing dependency '{module_match}'[/cyan]", "cyan")
        
        if not self.auto_confirm:
            try:
                response = input(f"   Install {module_match}? [Y/n]: ").strip().lower()
                if response not in ('', 'y', 'yes'):
                    return RepairResult(
                        success=False,
                        category=ErrorCategory.MISSING_DEPENDENCY,
                        fix_applied="user_declined",
                        message="User declined installation",
                        retry_recommended=False
                    )
            except (EOFError, KeyboardInterrupt):
                return RepairResult(
                    success=False,
                    category=ErrorCategory.MISSING_DEPENDENCY,
                    fix_applied="user_aborted",
                    message="User aborted",
                    retry_recommended=False
                )
        
        # Attempt installation
        import subprocess
        try:
            self._print(f"[cyan]   Installing {module_match}...[/cyan]")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", module_match],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                self._print(f"[green]✓ {module_match} installed successfully![/green]")
                return RepairResult(
                    success=True,
                    category=ErrorCategory.MISSING_DEPENDENCY,
                    fix_applied="pip_install",
                    message=f"Installed {module_match}",
                    retry_recommended=True
                )
            else:
                self._print(f"[red]✗ Installation failed: {result.stderr[:200]}[/red]")
                return RepairResult(
                    success=False,
                    category=ErrorCategory.MISSING_DEPENDENCY,
                    fix_applied="pip_install_failed",
                    message=result.stderr[:200],
                    retry_recommended=False
                )
        except Exception as e:
            return RepairResult(
                success=False,
                category=ErrorCategory.MISSING_DEPENDENCY,
                fix_applied="exception",
                message=str(e),
                retry_recommended=False
            )
    
    def _repair_service_unavailable(self, error: Exception, context: dict) -> RepairResult:
        """Attempt to start missing services like Ollama."""
        error_str = str(error).lower()
        
        # Check for Ollama
        if 'ollama' in error_str or '11434' in error_str:
            self._print("\n[cyan]🔧 Doctor: Ollama service unavailable[/cyan]", "cyan")
            
            if not self.auto_confirm:
                try:
                    response = input("   Start Ollama? [Y/n]: ").strip().lower()
                    if response not in ('', 'y', 'yes'):
                        return RepairResult(
                            success=False,
                            category=ErrorCategory.SERVICE_UNAVAILABLE,
                            fix_applied="user_declined",
                            message="User declined to start Ollama",
                            retry_recommended=False
                        )
                except (EOFError, KeyboardInterrupt):
                    return RepairResult(
                        success=False,
                        category=ErrorCategory.SERVICE_UNAVAILABLE,
                        fix_applied="user_aborted",
                        message="User aborted",
                        retry_recommended=False
                    )
            
            import subprocess
            try:
                self._print("[cyan]   Starting Ollama in background...[/cyan]")
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                time.sleep(3)  # Wait for startup
                
                # Check if it's running
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(("localhost", 11434))
                sock.close()
                
                if result == 0:
                    self._print("[green]✓ Ollama started successfully![/green]")
                    return RepairResult(
                        success=True,
                        category=ErrorCategory.SERVICE_UNAVAILABLE,
                        fix_applied="ollama_start",
                        message="Ollama service started",
                        retry_recommended=True
                    )
                else:
                    return RepairResult(
                        success=False,
                        category=ErrorCategory.SERVICE_UNAVAILABLE,
                        fix_applied="ollama_start_failed",
                        message="Ollama failed to start",
                        retry_recommended=False
                    )
            except Exception as e:
                return RepairResult(
                    success=False,
                    category=ErrorCategory.SERVICE_UNAVAILABLE,
                    fix_applied="exception",
                    message=str(e),
                    retry_recommended=False
                )
        
        return RepairResult(
            success=False,
            category=ErrorCategory.SERVICE_UNAVAILABLE,
            fix_applied="unrecognized_service",
            message="Unknown service error",
            retry_recommended=False
        )
    
    def _repair_configuration_error(self, error: Exception, context: dict) -> RepairResult:
        """Attempt to fix configuration errors."""
        # Try to create default .env if missing
        env_file = Path(".env")
        if not env_file.exists():
            self._print("\n[cyan]🔧 Doctor: Missing .env file[/cyan]", "cyan")
            
            try:
                # Copy from .env.example if exists
                example = Path(".env.example")
                if example.exists():
                    env_file.write_text(example.read_text())
                    self._print("[green]✓ Created .env from .env.example[/green]")
                    return RepairResult(
                        success=True,
                        category=ErrorCategory.CONFIGURATION_ERROR,
                        fix_applied="create_env_from_example",
                        message="Created .env file",
                        retry_recommended=True
                    )
            except Exception:
                pass
        
        return RepairResult(
            success=False,
            category=ErrorCategory.CONFIGURATION_ERROR,
            fix_applied="none",
            message="Could not auto-fix configuration",
            retry_recommended=False
        )
    
    def _repair_permission_denied(self, error: Exception, context: dict) -> RepairResult:
        """Suggest fixes for permission errors."""
        self._print("\n[cyan]🔧 Doctor: Permission denied[/cyan]", "cyan")
        self._print("[yellow]   You may need to:[/yellow]")
        self._print("   - Run with sudo (careful!)")
        self._print("   - Check file permissions")
        self._print("   - Check directory ownership")
        
        return RepairResult(
            success=False,
            category=ErrorCategory.PERMISSION_DENIED,
            fix_applied="advice_only",
            message="Manual permission fix required",
            retry_recommended=False
        )
    
    def handle_error(self, error: Exception, context: dict, original_func: Callable, *args, **kwargs) -> Any:
        """Main error handling entry point."""
        # Print error
        if self.console and HAS_RICH:
            self.console.print(f"\n[red]✗ Error:[/red] {error}")
        else:
            print(f"\n✗ Error: {error}")
        
        # Categorize
        category = self.categorize_error(error, context)
        
        if category == ErrorCategory.UNKNOWN:
            self._print(f"[dim]   Full traceback:[/dim]")
            traceback.print_exc()
            return None  # Cannot auto-fix
        
        # Attempt repair
        result = self.attempt_repair(category, error, context)
        
        if result.success and result.retry_recommended:
            self._print(f"\n[cyan]🔄 Retrying your command...[/cyan]\n")
            time.sleep(1)  # Brief pause before retry
            
            try:
                return original_func(*args, **kwargs)
            except Exception as retry_error:
                self._print(f"[red]✗ Retry failed: {retry_error}[/red]")
                return None
        else:
            self._print(f"\n[yellow]⚠ Could not auto-fix. Please resolve manually.[/yellow]")
            return None


def with_auto_repair(auto_confirm: bool = False, console: Optional[Console] = None):
    """Decorator that adds auto-repair capability to any function.
    
    Usage:
        @with_auto_repair(auto_confirm=True)
        def my_command(query: str, execute_web: bool = False):
            # ... implementation ...
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            repair_system = AutoRepairSystem(console=console, auto_confirm=auto_confirm)
            
            # Build context from kwargs
            context = {
                'execute_web': kwargs.get('execute_web', False),
                'auto_confirm': kwargs.get('auto_confirm', False),
                'args': args,
                'kwargs': kwargs,
            }
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return repair_system.handle_error(e, context, func, *args, **kwargs)
        
        return wrapper
    return decorator


def execute_with_auto_recovery(
    func: Callable[..., T],
    *args,
    auto_confirm: bool = False,
    console: Optional[Console] = None,
    **kwargs
) -> Optional[T]:
    """Execute a function with automatic error recovery.
    
    This is the imperative version of the with_auto_repair decorator.
    
    Args:
        func: Function to execute
        *args: Positional arguments
        auto_confirm: Whether to auto-confirm fixes
        console: Rich console for output
        **kwargs: Keyword arguments (including execute_web for context)
    
    Returns:
        Function result or None if repair failed
    """
    repair_system = AutoRepairSystem(console=console, auto_confirm=auto_confirm)
    
    # Extract execute_web from kwargs for context, don't pass to function
    execute_web = kwargs.pop('execute_web', False)
    
    context = {
        'execute_web': execute_web,
        'auto_confirm': auto_confirm,
        'args': args,
        'kwargs': kwargs,
    }
    
    try:
        return func(*args, **kwargs)
    except Exception as e:
        return repair_system.handle_error(e, context, func, *args, **kwargs)
