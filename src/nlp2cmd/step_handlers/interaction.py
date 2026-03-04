"""Click and form interaction handlers."""

from __future__ import annotations
import re
from typing import TYPE_CHECKING

from .base import StepHandler, HandlerContext, HandlerResult
from .registry import register_handler

if TYPE_CHECKING:
    pass


@register_handler("click")
class ClickHandler(StepHandler):
    """Handle click action with retry logic for detached elements."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        """Execute click with retry logic."""
        selector = ctx.params.get("selector")
        text = ctx.params.get("text")
        timeout = int(ctx.params.get("timeout", 10000))
        max_retries = int(ctx.params.get("retries", 3))
        
        # Normalize common LLM selector mistake: CSS :contains('...') is not valid
        if (not text) and isinstance(selector, str) and ":contains(" in selector:
            m = re.search(r":contains\((['\"])(.+?)\1\)", selector)
            if m:
                text = m.group(2)
                selector = None
                self._debug(f"click: normalized :contains() -> text={text!r}", ctx)
        
        # Wait for page to stabilize (SPA re-renders)
        try:
            ctx.page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        try:
            ctx.page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
        
        last_err = None
        for attempt in range(1, max_retries + 1):
            try:
                if text:
                    locator = ctx.page.get_by_text(text).first
                    locator.wait_for(state="visible", timeout=timeout)
                    locator.click(timeout=timeout)
                elif selector:
                    ctx.page.wait_for_selector(selector, state="visible", timeout=timeout)
                    ctx.page.click(selector, timeout=timeout)
                last_err = None
                break
            except Exception as click_err:
                last_err = click_err
                err_str = str(click_err)
                if "detached from the DOM" in err_str and attempt < max_retries:
                    self._debug(f"click: element detached, retry {attempt}/{max_retries}", ctx)
                    ctx.page.wait_for_timeout(1000)
                    continue
                if "Target page, context or browser has been closed" in err_str:
                    return HandlerResult(success=False, error=err_str, retry_allowed=False)
                if attempt < max_retries:
                    self._debug(f"click: attempt {attempt} failed: {click_err}", ctx)
                    ctx.page.wait_for_timeout(500)
                    continue
                # Last attempt: try force click
                try:
                    if text:
                        ctx.page.get_by_text(text).first.click(force=True, timeout=timeout)
                    elif selector:
                        ctx.page.click(selector, force=True, timeout=timeout)
                    last_err = None
                except Exception as force_err:
                    last_err = force_err
        
        if last_err:
            return HandlerResult(success=False, error=str(last_err))
        
        return HandlerResult(success=True)


@register_handler("click_radio")
class ClickRadioHandler(StepHandler):
    """Handle click_radio action for radio button selection."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        """Click a radio button by selector."""
        selector = ctx.params.get("selector")
        timeout = int(ctx.params.get("timeout", 5000))
        
        if not selector:
            return HandlerResult(success=False, error="click_radio requires selector")
        
        try:
            ctx.page.wait_for_selector(selector, state="visible", timeout=timeout)
            ctx.page.click(selector, timeout=timeout)
            return HandlerResult(success=True)
        except Exception as e:
            return HandlerResult(success=False, error=str(e))


@register_handler("dismiss_overlay")
class DismissOverlayHandler(StepHandler):
    """Handle dismiss_overlay action for cookie banners and dialogs."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        """Dismiss cookie consent banners and overlay dialogs."""
        self._debug("dismiss_overlay: scanning for overlay buttons", ctx)
        dismissed = False
        
        # Common cookie/consent button texts
        dismiss_texts = ["Accept", "Decline", "OK", "Got it", "Close",
                         "Akceptuję", "Zamknij", "Zgadzam się"]
        
        for txt in dismiss_texts:
            try:
                btn = ctx.page.get_by_text(txt, exact=True).first
                if btn.is_visible(timeout=500):
                    btn.click(timeout=2000)
                    self._debug(f"dismiss_overlay: clicked '{txt}'", ctx)
                    dismissed = True
                    ctx.page.wait_for_timeout(300)
                    break
            except Exception:
                continue
        
        # Fallback: try common CSS selectors for close buttons
        if not dismissed:
            for sel in ["[aria-label='Close']", "[aria-label='Dismiss']",
                        "button.close", ".cookie-banner button", "[id*='cookie'] button"]:
                try:
                    el = ctx.page.query_selector(sel)
                    if el and el.is_visible():
                        el.click()
                        self._debug(f"dismiss_overlay: clicked selector '{sel}'", ctx)
                        dismissed = True
                        break
                except Exception:
                    continue
        
        if not dismissed:
            self._debug("dismiss_overlay: no overlay found to dismiss", ctx)
        
        return HandlerResult(success=True)


@register_handler("type_text")
class TypeTextHandler(StepHandler):
    """Handle type_text action with fallback selectors."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        """Type text into an input field with fallback selectors."""
        selector = ctx.params.get("selector", "input")
        text = ctx.params.get("text", "")
        timeout = int(ctx.params.get("timeout", 30000))
        alt_selectors = ctx.params.get("alt_selectors", [])
        
        filled = False
        last_err = None
        
        # Try primary selector
        try:
            ctx.page.fill(selector, text, timeout=timeout)
            filled = True
        except Exception as primary_err:
            last_err = primary_err
            self._debug(f"type_text: primary selector '{selector}' failed: {primary_err}", ctx)
        
        # Try alternative selectors if primary failed
        if not filled and alt_selectors:
            for alt in alt_selectors:
                try:
                    self._debug(f"type_text: trying alt selector '{alt}'", ctx)
                    ctx.page.fill(alt, text, timeout=5000)
                    filled = True
                    self._debug(f"type_text: alt selector '{alt}' worked", ctx)
                    break
                except Exception:
                    continue
        
        # Last resort: try first visible text input
        if not filled:
            try:
                self._debug("type_text: trying first visible text input", ctx)
                loc = ctx.page.locator("input[type='text']:visible").first
                loc.fill(text, timeout=5000)
                filled = True
                self._debug("type_text: first visible text input worked", ctx)
            except Exception:
                pass
        
        if not filled and last_err:
            return HandlerResult(success=False, error=str(last_err))
        
        return HandlerResult(success=True)


@register_handler("fill_form")
class FillFormHandler(StepHandler):
    """Handle fill_form action for multiple fields."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        """Fill multiple form fields."""
        fields = ctx.params.get("fields", {})
        
        for selector, value in fields.items():
            try:
                ctx.page.fill(selector, str(value))
            except Exception:
                pass  # Continue with other fields
        
        return HandlerResult(success=True)


@register_handler("submit_form")
class SubmitFormHandler(StepHandler):
    """Handle submit_form action."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        """Submit a form by clicking submit button."""
        submit = ctx.page.query_selector(
            'button[type="submit"], input[type="submit"], form button'
        )
        if submit:
            submit.click()
        
        return HandlerResult(success=True)


@register_handler("login")
class LoginHandler(StepHandler):
    """Handle login action with email and password."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        """Fill login form with email and password."""
        email = ctx.params.get("email", "")
        password = ctx.params.get("password", "")
        
        # Fill email field
        email_field = ctx.page.query_selector(
            'input[type="email"], input[name*="email"], input[name*="login"]'
        )
        if email_field:
            email_field.fill(email)
        
        # Fill password field
        pass_field = ctx.page.query_selector('input[type="password"]')
        if pass_field:
            pass_field.fill(password)
        
        # Click submit
        submit = ctx.page.query_selector(
            'button[type="submit"], input[type="submit"]'
        )
        if submit:
            submit.click()
        
        return HandlerResult(success=True)


@register_handler("new_tab")
class NewTabHandler(StepHandler):
    """Handle new_tab action."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        """Open a new browser tab."""
        new_page = ctx.context.new_page()
        try:
            new_page.bring_to_front()
        except Exception:
            pass
        return HandlerResult(success=True, value="new_tab_opened")


@register_handler("wait")
class WaitHandler(StepHandler):
    """Handle wait action."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        """Wait for specified milliseconds."""
        ms = int(ctx.params.get("ms", 1000))
        ctx.page.wait_for_timeout(ms)
        return HandlerResult(success=True)


@register_handler("screenshot")
class ScreenshotHandler(StepHandler):
    """Handle screenshot action."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        """Take a screenshot of the page."""
        import time
        path = ctx.params.get(
            "path", f"/tmp/nlp2cmd_screenshot_{int(time.time())}.png"
        )
        ctx.page.screenshot(path=path, full_page=True)
        return HandlerResult(success=True, value=path)
