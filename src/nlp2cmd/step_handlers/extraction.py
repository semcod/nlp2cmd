"""Extraction and environment step handlers."""

from __future__ import annotations
import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

from .base import StepHandler, HandlerContext, HandlerResult
from .registry import register_handler

if TYPE_CHECKING:
    pass


@register_handler("extract_key")
class ExtractKeyHandler(StepHandler):
    """Extract API key from page DOM and clipboard."""
    
    DEFAULT_SELECTORS = [
        "code", "pre", "input[readonly]", "input[type='text'][readonly]",
        ".api-key", "[data-testid*='key']", "[class*='key']",
        ".token", "[data-testid*='token']",
    ]
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        key_pattern = ctx.params.get("key_pattern", "")
        key_selectors = ctx.params.get("selectors", self.DEFAULT_SELECTORS)
        service = ctx.params.get("service", "")
        
        ctx.console.print(f"  [dim]🔍 Szukam klucza API na stronie {service}...[/dim]")
        
        # Strategy 1: Search DOM elements
        for sel in key_selectors:
            try:
                elements = ctx.page.query_selector_all(sel)
                for el in elements:
                    text = (el.text_content() or "").strip()
                    if not text or len(text) < 10:
                        continue
                    if key_pattern and re.match(key_pattern, text):
                        ctx.console.print(f"  [green]✓[/green] Znaleziono klucz w DOM ({sel}, {len(text)} znaków)")
                        self._copy_to_clipboard(ctx, text)
                        return HandlerResult(success=True, value=text)
                    if not key_pattern and re.match(r'^[a-zA-Z0-9_\-]{20,}$', text):
                        ctx.console.print(f"  [green]✓[/green] Potencjalny klucz w DOM ({sel}, {len(text)} znaków)")
                        self._copy_to_clipboard(ctx, text)
                        return HandlerResult(success=True, value=text)
            except Exception:
                continue
        
        # Strategy 2: Check clipboard
        try:
            from nlp2cmd.automation.step_validator import StepValidator
            clipboard = StepValidator.get_clipboard()
            if clipboard and len(clipboard) >= 10:
                if key_pattern and re.match(key_pattern, clipboard):
                    ctx.console.print(f"  [green]✓[/green] Klucz znaleziony w schowku ({len(clipboard)} znaków)")
                    return HandlerResult(success=True, value=clipboard)
                elif not key_pattern and re.match(r'^[a-zA-Z0-9_\-]{20,}$', clipboard):
                    ctx.console.print(f"  [green]✓[/green] Potencjalny klucz w schowku ({len(clipboard)} znaków)")
                    return HandlerResult(success=True, value=clipboard)
        except Exception as e:
            self._debug(f"extract_key: clipboard check failed: {e}", ctx)
        
        # Strategy 3: Full body regex scan
        try:
            body = ctx.page.text_content("body") or ""
            if key_pattern:
                match = re.search(key_pattern, body)
                if match:
                    found = match.group(0)
                    ctx.console.print(f"  [green]✓[/green] Klucz znaleziony w treści strony ({len(found)} znaków)")
                    self._copy_to_clipboard(ctx, found)
                    return HandlerResult(success=True, value=found)
        except Exception as e:
            self._debug(f"extract_key: body scan failed: {e}", ctx)
        
        ctx.console.print(f"  [yellow]⚠[/yellow] Nie znaleziono klucza na stronie")
        return HandlerResult(success=False, error="Key not found")
    
    def _copy_to_clipboard(self, ctx: HandlerContext, key: str) -> None:
        """Copy key to clipboard via JS."""
        try:
            ctx.page.evaluate(f"navigator.clipboard.writeText({json.dumps(key)})")
            self._debug(f"extract_key: copied key to clipboard ({len(key)} chars)", ctx)
        except Exception as ce:
            self._debug(f"extract_key: clipboard copy failed: {ce}", ctx)


@register_handler("extract_api_key")
class ExtractApiKeyHandler(StepHandler):
    """Disabled safety-only alias for API key extraction."""

    def execute(self, ctx: HandlerContext) -> HandlerResult:
        raise ValueError("extract_api_key is disabled for safety. Use prompt_secret to paste the key.")


@register_handler("check_clipboard")
class CheckClipboardHandler(StepHandler):
    """Validate clipboard content against key pattern."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        key_pattern = ctx.params.get("key_pattern", "")
        env_var = ctx.params.get("env_var", "")
        
        ctx.console.print(f"  [dim]📋 Sprawdzam schowek...[/dim]")
        
        try:
            from nlp2cmd.automation.step_validator import StepValidator
            clipboard = StepValidator.get_clipboard()
            if clipboard and len(clipboard) >= 10:
                if key_pattern and re.match(key_pattern, clipboard):
                    ctx.console.print(f"  [green]✓[/green] Klucz w schowku pasuje do wzorca ({len(clipboard)} znaków)")
                    return HandlerResult(success=True, value=clipboard)
                elif key_pattern:
                    ctx.console.print(f"  [yellow]⚠[/yellow] Schowek nie pasuje do wzorca")
                    return HandlerResult(success=True, value=None)
                elif len(clipboard) >= 20:
                    ctx.console.print(f"  [dim]   Schowek zawiera {len(clipboard)} znaków[/dim]")
                    return HandlerResult(success=True, value=clipboard)
            ctx.console.print(f"  [yellow]⚠[/yellow] Schowek pusty lub za krótki")
            return HandlerResult(success=True, value=None)
        except Exception as e:
            ctx.console.print(f"  [yellow]⚠[/yellow] Nie można odczytać schowka: {e}")
            return HandlerResult(success=False, error=str(e))


@register_handler("save_env")
class SaveEnvHandler(StepHandler):
    """Save value to .env file."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        var_name = ctx.params.get("var_name", "UNKNOWN_KEY")
        value = ctx.params.get("value", "")
        file_path = ctx.params.get("file", ".env")
        
        self._debug(f"save_env: var_name={var_name}, file={file_path}", ctx)
        
        # Resolve $variable references
        if isinstance(value, str) and value.startswith("$"):
            ref_name = value[1:]
            value = ctx.variables.get(ref_name, "")
            self._debug(f"save_env: resolved ${ref_name} → {'<empty>' if not value else f'{len(value)} chars'}", ctx)
        
        # Fallback: try well-known variable names if $ref was empty
        if not value:
            for _fallback_var in ("extracted_key", "api_key", "clipboard_key"):
                _fv = ctx.variables.get(_fallback_var, "")
                if _fv and len(_fv) >= 10:
                    value = _fv
                    self._debug(f"save_env: fallback resolved from ${_fallback_var} ({len(value)} chars)", ctx)
                    break
        
        if not value:
            return HandlerResult(success=False, error=f"Brak wartości do zapisania dla {var_name}")
        
        env_path = Path(file_path).resolve()
        existing = env_path.read_text() if env_path.exists() else ""
        
        if f"{var_name}=" in existing:
            updated = re.sub(
                rf"{re.escape(var_name)}=.*",
                f'{var_name}="{value}"',
                existing,
            )
            env_path.write_text(updated)
            self._debug(f"save_env: updated existing {var_name} in {env_path}", ctx)
        else:
            with open(env_path, "a") as f:
                f.write(f'\n{var_name}="{value}"\n')
            self._debug(f"save_env: appended {var_name} to {env_path}", ctx)
        
        # Also set in current process environment
        os.environ[var_name] = value
        self._debug(f"save_env: os.environ[{var_name}] set ({len(value)} chars)", ctx)
        
        # Verify the file was actually written
        try:
            verify_content = env_path.read_text()
            if f'{var_name}="{value}"' not in verify_content and f"{var_name}={value}" not in verify_content:
                ctx.console.print(f"  [red]⚠ Weryfikacja: {var_name} NIE znaleziony w {env_path}![/red]")
            else:
                self._debug(f"save_env: verified {var_name} present in {env_path}", ctx)
        except Exception as ve:
            self._debug(f"save_env: verification read failed: {ve}", ctx)
        
        return HandlerResult(success=True, value=value)


@register_handler("verify_env")
class VerifyEnvHandler(StepHandler):
    """Verify that env var was saved to .env file."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        var_name = ctx.params.get("var_name", "UNKNOWN")
        file_path = ctx.params.get("file", ".env")
        
        env_path = Path(file_path).resolve()
        self._debug(f"verify_env: checking {var_name} in {env_path}", ctx)
        
        # Check .env file exists and contains the variable
        if env_path.exists():
            try:
                content = env_path.read_text()
                if f"{var_name}=" in content:
                    match = re.search(rf'{re.escape(var_name)}="?([^"\n]*)"?', content)
                    val_preview = ""
                    if match:
                        val = match.group(1)
                        val_preview = f"{val[:8]}...{val[-4:]}" if len(val) > 16 else f"{len(val)} chars"
                    ctx.console.print(f"  [green]✓[/green] Plik {env_path}: {var_name} znaleziony ({val_preview})")
                    return HandlerResult(success=True, value="verified")
                else:
                    ctx.console.print(f"  [yellow]⚠[/yellow] {var_name} nie znaleziony w {env_path}")
                    return HandlerResult(success=False, error=f"{var_name} not found in {env_path}")
            except Exception as e:
                return HandlerResult(success=False, error=str(e))
        else:
            ctx.console.print(f"  [yellow]⚠[/yellow] Plik {env_path} nie istnieje")
            return HandlerResult(success=False, error=f"File {env_path} not found")


@register_handler("prompt_secret")
class PromptSecretHandler(StepHandler):
    """Prompt user for secret/API key with timeout and validation."""
    
    _PROMPT_TIMEOUT = int(os.environ.get("NLP2CMD_PROMPT_TIMEOUT", "60"))
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        prompt = str(ctx.params.get("prompt") or "Enter secret: ")
        env_var = str(ctx.params.get("env_var") or "").strip()
        key_pattern = str(ctx.params.get("key_pattern") or "").strip()
        
        # Skip if key was already extracted in a prior step
        for _var_name in ("extracted_key", "api_key", "clipboard_key"):
            _existing = ctx.variables.get(_var_name, "")
            if _existing and len(_existing) >= 10:
                if key_pattern and (not re.match(key_pattern, str(_existing).strip())):
                    continue
                self._debug(f"prompt_secret: SKIP — key already in ${_var_name} ({len(_existing)} chars)", ctx)
                ctx.console.print(f"  [green]✓[/green] Klucz już pobrany (${_var_name}, {len(_existing)} znaków) — pomijam prompt")
                return HandlerResult(success=True, value=_existing)
        
        # Check if stdin is a TTY
        import sys
        try:
            is_tty = bool(getattr(sys.stdin, "isatty", lambda: False)())
        except Exception:
            is_tty = False
        
        # Non-interactive fallback: use env var ONLY when no TTY available
        if not is_tty:
            if env_var:
                env_val = os.environ.get(env_var, "").strip()
                if env_val:
                    self._debug(f"prompt_secret: non-TTY, using {env_var} from environment", ctx)
                    ctx.console.print(f"  [dim]ℹ Użyto istniejącej wartości {env_var} z os.environ (brak TTY)[/dim]")
                    return HandlerResult(success=True, value=env_val)
            return HandlerResult(success=False, error="prompt_secret requires interactive TTY")
        
        # Interactive mode — prompt with timeout
        timeout_sec = self._PROMPT_TIMEOUT
        self._debug(f"prompt_secret: TTY available, prompting user (timeout={timeout_sec}s)", ctx)
        
        if timeout_sec > 0:
            ctx.console.print(f"  [dim]⏱ Timeout: {timeout_sec}s[/dim]")
        
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            val = self._getpass_with_timeout(prompt, timeout_sec)
            
            if val is None:
                ctx.console.print(f"  [yellow]⚠ Timeout ({timeout_sec}s) — użytkownik nie odpowiedział.[/yellow]")
                if env_var:
                    env_val = os.environ.get(env_var, "").strip()
                    if env_val:
                        ctx.console.print(f"  [dim]ℹ Używam istniejącej wartości {env_var}[/dim]")
                        return HandlerResult(success=True, value=env_val)
                return HandlerResult(success=False, error="Timeout waiting for input")
            
            val = str(val or "").strip()
            if not val:
                if attempt < max_attempts:
                    ctx.console.print(f"  [yellow]⚠ Pusty klucz. Próba {attempt}/{max_attempts}.[/yellow]")
                    continue
                return HandlerResult(success=False, error="No key provided after 3 attempts")
            
            # Validate against key pattern if provided
            if key_pattern:
                if re.match(key_pattern, val):
                    self._debug(f"prompt_secret: key matches pattern {key_pattern}", ctx)
                    ctx.console.print(f"  [green]✓ Klucz pasuje do wzorca {key_pattern}[/green]")
                else:
                    ctx.console.print(f"  [yellow]⚠ Klucz nie pasuje do wzorca: {key_pattern}[/yellow]")
                    if attempt < max_attempts:
                        ctx.console.print(f"  [yellow]  Próba {attempt}/{max_attempts}.[/yellow]")
                        continue
            
            self._debug(f"prompt_secret: got {len(val)} chars", ctx)
            return HandlerResult(success=True, value=val)
        
        return HandlerResult(success=False, error="Failed to get valid key")
    
    def _getpass_with_timeout(self, prompt_str: str, timeout: int) -> str | None:
        """Run getpass in a thread with timeout. Returns None on timeout."""
        import threading
        import getpass
        
        result_box = [None]
        error_box = [None]
        
        def _reader():
            try:
                result_box[0] = getpass.getpass(prompt_str)
            except Exception as exc:
                error_box[0] = exc
        
        t = threading.Thread(target=_reader, daemon=True)
        t.start()
        t.join(timeout=timeout if timeout > 0 else None)
        if t.is_alive():
            return None  # timeout
        if error_box[0]:
            raise error_box[0]
        return result_box[0]


@register_handler("echo")
class EchoHandler(StepHandler):
    """Echo a message to the console."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        msg = ctx.params.get("message", "") or ctx.params.get("text", "")
        if msg:
            self._debug(msg, ctx)
            for line in str(msg).split("\n"):
                ctx.console.print(f"  [dim]{line}[/dim]")
        return HandlerResult(success=True)


@register_handler("extract_text")
class ExtractTextHandler(StepHandler):
    """Extract text from page elements."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        pattern = ctx.params.get("pattern")
        selectors = ctx.params.get("selectors", ["code", "pre", ".api-key"])
        
        for sel in selectors:
            try:
                elements = ctx.page.query_selector_all(sel)
                for el in elements:
                    text = (el.text_content() or "").strip()
                    if pattern and re.search(pattern, text):
                        return HandlerResult(success=True, value=re.search(pattern, text).group(0))
                    elif not pattern and len(text) > 10:
                        return HandlerResult(success=True, value=text)
            except Exception:
                continue
        
        # Fallback: regex on full body
        body = ctx.page.text_content("body") or ""
        if pattern:
            match = re.search(pattern, body)
            if match:
                return HandlerResult(success=True, value=match.group(0))
        
        return HandlerResult(success=False, error="Text not found")
