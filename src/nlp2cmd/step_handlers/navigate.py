"""Navigate step handler."""

from __future__ import annotations
from typing import TYPE_CHECKING

from .base import StepHandler, HandlerContext, HandlerResult
from .registry import register_handler

if TYPE_CHECKING:
    pass


@register_handler("navigate")
class NavigateHandler(StepHandler):
    """Handle navigate action - navigate to URL with security checkup handling."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        """Navigate to URL with security checkup handling."""
        url = ctx.params.get("url", "")
        
        if not url or url in ("https://", "http://"):
            return HandlerResult(
                success=False,
                error=f"navigate: empty or invalid URL '{url}'. Add url parameter."
            )
        
        if not url.startswith("http"):
            url = f"https://{url}"
        
        try:
            ctx.page.goto(url, wait_until="domcontentloaded", timeout=15000)
            ctx.page.wait_for_timeout(1000)
            
            # Handle security-checkup redirects (e.g. HuggingFace)
            current_url = ctx.page.url or ""
            if "security-checkup" in current_url and "security-checkup" not in url:
                self._handle_security_checkup(ctx, url)
            
            return HandlerResult(success=True)
        except Exception as e:
            return HandlerResult(success=False, error=str(e), retry_allowed=True)
    
    def _handle_security_checkup(self, ctx: HandlerContext, original_url: str) -> None:
        """Try to pass through security checkup pages."""
        self._debug("navigate: security-checkup redirect detected, trying to pass through", ctx)
        
        # Try clicking common "continue" / "skip" / "confirm" buttons
        _security_passed = False
        for _btn_text in ["Continue", "Skip", "Confirm", "Kontynuuj", "Pomiń", "I understand"]:
            try:
                _btn = ctx.page.get_by_text(_btn_text, exact=False).first
                if _btn.is_visible(timeout=1500):
                    _btn.click(timeout=3000)
                    ctx.page.wait_for_timeout(2000)
                    _security_passed = True
                    self._debug(f"navigate: clicked '{_btn_text}' on security-checkup", ctx)
                    break
            except Exception:
                continue
        
        # Re-navigate to original target after passing security check
        new_url = ctx.page.url or ""
        if new_url != original_url and "security-checkup" not in new_url:
            # Security check redirected us somewhere else — try target again
            try:
                ctx.page.goto(original_url, wait_until="domcontentloaded", timeout=15000)
                ctx.page.wait_for_timeout(1000)
            except Exception:
                pass
        elif "security-checkup" in new_url:
            # Still stuck on security — try direct navigation anyway
            try:
                ctx.page.goto(original_url, wait_until="domcontentloaded", timeout=15000)
                ctx.page.wait_for_timeout(1000)
            except Exception:
                pass
