"""Session and authentication step handlers."""

from __future__ import annotations
import time
import json
from typing import TYPE_CHECKING

from .base import StepHandler, HandlerContext, HandlerResult
from .registry import register_handler

if TYPE_CHECKING:
    pass


@register_handler("check_session")
class CheckSessionHandler(StepHandler):
    """Check if user is logged into a service with auto-login via password store."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        service = ctx.params.get("service", "unknown")
        session_indicators = ctx.params.get("session_indicators", [])
        login_indicators = ctx.params.get("login_indicators", [])
        login_url = ctx.params.get("login_url", "")
        keys_url = ctx.params.get("keys_url", "")
        
        self._debug(f"check_session: checking {service} session state", ctx)
        ctx.console.print(f"  [dim]🔍 Sprawdzam sesję {service}...[/dim]")
        
        try:
            body_text = ctx.page.text_content("body") or ""
            current_url = ctx.page.url
            
            # Check login indicators first (are we on a login page?)
            is_login_page = any(ind.lower() in body_text.lower() for ind in login_indicators)
            if login_url and login_url in current_url:
                is_login_page = True
            
            # Check session indicators (are we logged in?)
            has_session = any(ind.lower() in body_text.lower() for ind in session_indicators)
            
            if has_session and not is_login_page:
                ctx.console.print(f"  [green]✓[/green] Zalogowany na {service}")
                return HandlerResult(success=True, value="logged_in")
            elif is_login_page:
                ctx.console.print(f"  [yellow]![/yellow] Niezalogowany na {service}")
                return self._handle_login_page(ctx, service, keys_url)
            else:
                ctx.console.print(f"  [dim]?[/dim] Nie udało się określić stanu sesji {service}")
                return HandlerResult(success=True, value="unknown")
                
        except Exception as e:
            self._debug(f"check_session error: {e}", ctx)
            return HandlerResult(success=False, error=str(e))
    
    def _handle_login_page(self, ctx: HandlerContext, service: str, keys_url: str) -> HandlerResult:
        """Try auto-login or prompt user when on login page."""
        _auto_logged_in = False
        
        # Try auto-login via password store
        try:
            from nlp2cmd.automation.password_store import get_password_store
            pw_store = get_password_store()
            cred = pw_store.get_credentials(service)
            if cred and cred.username and cred.password:
                ctx.console.print(f"  [dim]🔐 Znaleziono dane logowania ({cred.source}: {cred.username})[/dim]")
                
                # Fill email/username field
                _email_selectors = [
                    'input[type="email"]', 'input[name*="email"]',
                    'input[name*="login"]', 'input[name*="user"]',
                ]
                for _sel in _email_selectors:
                    try:
                        _el = ctx.page.query_selector(_sel)
                        if _el and _el.is_visible():
                            _el.fill(cred.username)
                            break
                    except Exception:
                        continue
                
                # Fill password field
                try:
                    _pw_el = ctx.page.query_selector('input[type="password"]')
                    if _pw_el and _pw_el.is_visible():
                        _pw_el.fill(cred.password)
                        
                        # Submit form
                        _submit_selectors = [
                            'button[type="submit"]',
                            'button:has-text("Sign in")',
                            'button:has-text("Log in")',
                        ]
                        for _sub_sel in _submit_selectors:
                            try:
                                _sub = ctx.page.locator(_sub_sel).first
                                if _sub.is_visible(timeout=2000):
                                    _sub.click(timeout=5000)
                                    ctx.page.wait_for_timeout(3000)
                                    break
                            except Exception:
                                continue
                        
                        # Check if login succeeded
                        ctx.page.wait_for_timeout(2000)
                        body_after = ctx.page.text_content("body") or ""
                        still_login = any("login" in body_after.lower() for _ in [1])
                        if not still_login:
                            ctx.console.print(f"  [green]✓[/green] Auto-login na {service} powiódł się!")
                            _auto_logged_in = True
                            if keys_url:
                                try:
                                    ctx.page.goto(keys_url, wait_until="domcontentloaded", timeout=15000)
                                    ctx.page.wait_for_timeout(1000)
                                except Exception:
                                    pass
                            return HandlerResult(success=True, value="logged_in")
                        else:
                            ctx.console.print(f"  [yellow]⚠[/yellow] Auto-login nie powiódł się (2FA/captcha?)")
                except Exception:
                    pass
            
        except ImportError:
            pass
        except Exception as _pw_err:
            self._debug(f"check_session: password store error: {_pw_err}", ctx)
        
        if not _auto_logged_in:
            ctx.console.print(f"  [dim]   Zaloguj się ręcznie w przeglądarce, potem kontynuuj[/dim]")
        
        return HandlerResult(success=True, value="needs_login")


@register_handler("submit_and_extract_key")
class SubmitAndExtractKeyHandler(StepHandler):
    """Submit form and poll for API key extraction."""
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        submit_selector = ctx.params.get("selector", "")
        key_pattern = ctx.params.get("key_pattern", "")
        poll_timeout = ctx.params.get("timeout", 60000)  # ms
        key_selectors = ctx.params.get("selectors", ["code", "pre", "input[readonly]"])
        
        ctx.console.print(f"  [dim]🔑 Klikam submit i szukam klucza...[/dim]")
        
        # Click submit (non-blocking)
        click_ok = self._click_submit(ctx, submit_selector)
        
        # Poll page body for key pattern
        found_key = self._poll_for_key(ctx, key_pattern, key_selectors, poll_timeout)
        
        if found_key:
            ctx.console.print(f"  [green]✓[/green] Klucz przechwycony! ({len(found_key)} znaków)")
            self._copy_to_clipboard(ctx, found_key)
            return HandlerResult(success=True, value=found_key)
        
        ctx.console.print(f"  [yellow]⚠[/yellow] Klucz nie pojawił się w ciągu {poll_timeout/1000:.0f}s")
        return HandlerResult(success=False, error="Key not found after timeout")
    
    def _click_submit(self, ctx: HandlerContext, submit_selector: str) -> bool:
        """Click submit button with fallbacks."""
        if submit_selector:
            for sel_candidate in submit_selector.split(","):
                sel_candidate = sel_candidate.strip()
                if not sel_candidate:
                    continue
                try:
                    loc = ctx.page.locator(sel_candidate).first
                    if loc.is_visible(timeout=2000):
                        loc.click(no_wait_after=True, timeout=5000)
                        return True
                except Exception:
                    continue
        
        # JS fallback: find Create button
        try:
            ctx.page.evaluate("""
                (() => {
                    const btns = [...document.querySelectorAll('button')];
                    const create = btns.find(b => b.textContent.trim() === 'Create' && !b.disabled);
                    if (create) create.click();
                })()
            """)
            return True
        except Exception:
            pass
        
        return False
    
    def _poll_for_key(
        self,
        ctx: HandlerContext,
        key_pattern: str,
        key_selectors: list,
        timeout_ms: int
    ) -> Optional[str]:
        """Poll page for key extraction."""
        import re
        
        poll_interval = 500  # ms
        elapsed = 0
        
        while elapsed < timeout_ms:
            ctx.page.wait_for_timeout(poll_interval)
            elapsed += poll_interval
            
            # Check DOM selectors
            for sel in key_selectors:
                try:
                    elements = ctx.page.query_selector_all(sel)
                    for el in elements:
                        text = (el.text_content() or "").strip()
                        if text and key_pattern and re.search(key_pattern, text):
                            return re.search(key_pattern, text).group(0)
                        elif text and not key_pattern and len(text) > 30:
                            return text
                except Exception:
                    continue
            
            # Check full body
            if not key_pattern:
                continue
            try:
                body = ctx.page.text_content("body") or ""
                m = re.search(key_pattern, body)
                if m:
                    return m.group(0)
            except Exception:
                pass
        
        return None
    
    def _copy_to_clipboard(self, ctx: HandlerContext, key: str) -> None:
        """Copy key to clipboard via JS."""
        try:
            ctx.page.evaluate(f"navigator.clipboard.writeText({json.dumps(key)})")
        except Exception:
            pass


@register_handler("discover_service_section")
class DiscoverServiceSectionHandler(StepHandler):
    """Discover service section (e.g., API keys page) by link discovery."""
    
    DEFAULT_HINTS = [
        "api key", "api keys", "token", "tokens", "access token",
        "developer", "credential", "secret", "settings",
        "klucz", "klucze", "tokeny", "ustawienia",
    ]
    
    COMMON_PATHS = [
        "/settings/tokens",
        "/settings/token",
        "/settings/keys",
        "/settings/api-keys",
        "/settings/access-tokens",
        "/account/api-tokens",
        "/account/api-keys",
        "/account/tokens",
        "/api-keys",
        "/tokens",
        "/keys",
    ]
    
    def execute(self, ctx: HandlerContext) -> HandlerResult:
        from urllib.parse import urljoin
        
        service = str(ctx.params.get("service") or "service")
        section = str(ctx.params.get("section") or "keys").lower()
        base_url = str(ctx.params.get("base_url") or "").strip()
        keys_url = str(ctx.params.get("keys_url") or "").strip()
        raw_hints = ctx.params.get("hints", [])
        
        # Build hints list
        if isinstance(raw_hints, str):
            hints = [raw_hints]
        elif isinstance(raw_hints, list):
            hints = [str(h) for h in raw_hints if str(h).strip()]
        else:
            hints = []
        hint_terms = {h.lower() for h in (hints + self.DEFAULT_HINTS) if h}
        
        current_url = ctx.page.url or ""
        if keys_url and keys_url in current_url:
            return HandlerResult(success=True, value=current_url)
        
        # Ensure we are at least on the provider domain
        if current_url in ("", "about:blank"):
            seed_url = base_url or keys_url
            if seed_url:
                if not seed_url.startswith("http"):
                    seed_url = f"https://{seed_url}"
                ctx.page.goto(seed_url, wait_until="domcontentloaded", timeout=15000)
                ctx.page.wait_for_timeout(700)
                current_url = ctx.page.url or ""
        
        # Find best link by scoring
        best_link = self._find_best_link(ctx, hint_terms, section)
        
        # Build candidate URLs
        candidate_urls = []
        if best_link:
            candidate_urls.append(best_link)
        if keys_url:
            candidate_urls.append(keys_url)
        
        if base_url:
            normalized_base = base_url if base_url.startswith("http") else f"https://{base_url}"
            for path in self.COMMON_PATHS:
                candidate_urls.append(urljoin(normalized_base, path))
        
        # Deduplicate and try candidates
        seen = set()
        for cand in candidate_urls:
            if cand and cand not in seen:
                seen.add(cand)
                result = self._try_candidate(ctx, cand, hint_terms, service, section)
                if result:
                    return HandlerResult(success=True, value=result)
        
        # Last resort: use PageAnalyzer
        result = self._try_page_analyzer(ctx, service)
        if result:
            return HandlerResult(success=True, value=result)
        
        self._debug(
            f"discover_service_section: could not resolve {service}/{section}; staying on {ctx.page.url}",
            ctx
        )
        return HandlerResult(success=True, value=ctx.page.url or current_url)
    
    def _find_best_link(self, ctx: HandlerContext, hint_terms: set, section: str) -> str:
        """Find best matching link on current page."""
        best_link = ""
        best_score = -1
        
        try:
            links = ctx.page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a[href]')).slice(0, 300).map(a => ({
                    href: a.href || '',
                    text: (a.innerText || a.textContent || '').trim(),
                    aria: (a.getAttribute('aria-label') || '').trim(),
                }));
            }""")
        except Exception:
            return ""
        
        if not isinstance(links, list):
            return ""
        
        for item in links:
            if not isinstance(item, dict):
                continue
            href = str(item.get("href") or "").strip()
            if not href or href.startswith("javascript:") or href.startswith("mailto:"):
                continue
            text_blob = " ".join([
                href,
                str(item.get("text") or ""),
                str(item.get("aria") or ""),
            ]).lower()
            score = sum(1 for term in hint_terms if term in text_blob)
            if section == "keys" and any(k in text_blob for k in ("key", "token", "api", "secret")):
                score += 1
            if score > best_score:
                best_score = score
                best_link = href
        
        return best_link
    
    def _try_candidate(
        self,
        ctx: HandlerContext,
        cand: str,
        hint_terms: set,
        service: str,
        section: str
    ) -> Optional[str]:
        """Try a candidate URL and return it if it matches."""
        try:
            ctx.page.goto(cand, wait_until="domcontentloaded", timeout=12000)
            ctx.page.wait_for_timeout(600)
            now_url = (ctx.page.url or "").lower()
            body = (ctx.page.text_content("body") or "").lower()
            score = sum(1 for term in hint_terms if term in (now_url + " " + body))
            if score > 0 or any(k in now_url for k in ("key", "token", "api", "credential")):
                resolved = ctx.page.url or cand
                self._debug(f"discover_service_section: resolved {service}/{section} -> {resolved}", ctx)
                return resolved
        except Exception:
            pass
        return None
    
    def _try_page_analyzer(self, ctx: HandlerContext, service: str) -> Optional[str]:
        """Try using PageAnalyzer as last resort."""
        try:
            from nlp2cmd.automation.feedback_loop import PageAnalyzer
            pa_url = PageAnalyzer.find_api_keys_section(ctx.page)
            if pa_url:
                self._debug(f"discover_service_section: PageAnalyzer found {pa_url}", ctx)
                ctx.page.goto(pa_url, wait_until="domcontentloaded", timeout=12000)
                ctx.page.wait_for_timeout(600)
                return ctx.page.url or pa_url
        except Exception:
            pass
        return None
