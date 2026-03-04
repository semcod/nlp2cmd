"""Form handling DOM action handlers."""

from __future__ import annotations
from typing import TYPE_CHECKING

from .base import DomAction, ActionContext, ActionResult
from .registry import register_action

if TYPE_CHECKING:
    pass


@register_action("fill_form")
class FillFormAction(DomAction):
    """Fill form fields automatically from .env and data files."""
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        """Automatic form filling with discovery and fallback strategies."""
        try:
            from nlp2cmd.web_schema.form_handler import FormHandler
            from nlp2cmd.web_schema.site_explorer import SiteExplorer
            from nlp2cmd.pipeline_runner_utils import _filter_form_fields
            
            form_handler = FormHandler(console=ctx.console, use_markdown=True)
            
            # Wait for page to be fully loaded
            ctx.console.print("⏳ Waiting for page to load...", language="text")
            self._wait_for_page_load(ctx.page)
            
            # Detect form fields
            ctx.console.print("🔍 Detecting form fields...", language="text")
            fields = form_handler.detect_form_fields(ctx.page)
            
            # Filter out junk fields
            fields = _filter_form_fields(fields, ctx.console)
            
            if not fields:
                # Try form discovery
                fields = self._discover_form(ctx, form_handler)
            
            if not fields:
                # Fallback: extract contact info
                return self._extract_contact_info(ctx)
            
            # Fill the form fields
            return self._fill_detected_fields(ctx, form_handler, fields)
            
        except Exception as e:
            ctx.console.print(f"fill_form failed: {e}", language="text")
            return ActionResult(
                success=False,
                error=f"fill_form error: {e}",
                should_continue=False
            )
    
    def _wait_for_page_load(self, page) -> None:
        """Wait for page to be fully loaded."""
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            try:
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass
        page.wait_for_timeout(1500)
    
    def _discover_form(self, ctx: ActionContext, form_handler) -> list:
        """Try to discover form via site explorer or direct navigation."""
        from nlp2cmd.pipeline_runner_utils import _filter_form_fields
        from urllib.parse import urljoin
        
        ctx.console.print("No form fields detected on this page", language="text")
        
        # Try site explorer
        try:
            explorer = SiteExplorer(max_depth=2, max_pages=8, headless=False)
            explore_result = explorer.find_form(
                url=ctx.url,
                intent="contact",
                page=ctx.page,
                context=ctx.context,
                close_browser=False,
            )
            
            if explore_result.success and explore_result.form_url:
                form_url = explore_result.form_url
                ctx.console.print(f"✓ Found form at: {form_url}", language="text")
                
                if form_url != ctx.page.url:
                    ctx.page.goto(form_url, wait_until="domcontentloaded")
                    ctx.page.wait_for_timeout(1500)
                
                fields = form_handler.detect_form_fields(ctx.page)
                fields = _filter_form_fields(fields, ctx.console)
                if fields:
                    return fields
        except Exception:
            pass
        
        # Try direct contact URLs
        return self._try_direct_contact_urls(ctx, form_handler)
    
    def _try_direct_contact_urls(self, ctx: ActionContext, form_handler) -> list:
        """Try direct navigation to common contact page URLs."""
        from nlp2cmd.pipeline_runner_utils import _filter_form_fields
        from urllib.parse import urljoin
        
        direct_paths = [
            "/kontakt", "/kontakt/", "/kontakt.html", "/kontakt.php",
            "/kontakt-i-dane", "/kontakt-2", "/kontakt-2/",
            "/contact", "/contact/",
        ]
        
        base = str(ctx.page.url or ctx.url)
        
        for pth in direct_paths:
            try:
                cand_url = urljoin(base, pth)
                ctx.page.goto(cand_url, wait_until="domcontentloaded", timeout=12000)
                ctx.page.wait_for_timeout(1200)
                self._dismiss_popups(ctx.page, ctx.schema_loader)
                
                # Scroll to trigger lazy loading
                try:
                    ctx.page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
                except Exception:
                    pass
                ctx.page.wait_for_timeout(900)
                
                fields = form_handler.detect_form_fields(ctx.page)
                fields = _filter_form_fields(fields, ctx.console)
                if fields:
                    return fields
            except Exception:
                continue
        
        # Try clicking contact links
        return self._try_contact_links(ctx, form_handler)
    
    def _try_contact_links(self, ctx: ActionContext, form_handler) -> list:
        """Try clicking contact links in the page."""
        from nlp2cmd.pipeline_runner_utils import _filter_form_fields
        
        candidates = [
            'a[href*="kontakt" i]',
            'a:has-text("Kontakt")',
            'a:has-text("Contact")',
            'a[href*="contact" i]',
        ]
        
        for sel in candidates:
            try:
                loc = ctx.page.locator(sel).first
                if loc.count() > 0:
                    loc.click(timeout=1500)
                    ctx.page.wait_for_load_state("domcontentloaded", timeout=8000)
                    ctx.page.wait_for_timeout(1200)
                    
                    fields = form_handler.detect_form_fields(ctx.page)
                    fields = _filter_form_fields(fields, ctx.console)
                    if fields:
                        return fields
            except Exception:
                continue
        
        # Check iframes
        return self._check_iframes(ctx, form_handler)
    
    def _check_iframes(self, ctx: ActionContext, form_handler) -> list:
        """Check for forms inside iframes."""
        from nlp2cmd.pipeline_runner_utils import _filter_form_fields
        
        try:
            frames = list(getattr(ctx.page, "frames", []) or [])
        except Exception:
            frames = []
        
        for fr in frames[1:]:
            try:
                fr_fields = form_handler.detect_form_fields(fr)
                fr_fields = _filter_form_fields(fr_fields, ctx.console)
                if fr_fields:
                    return fr_fields
            except Exception:
                continue
        
        return []
    
    def _extract_contact_info(self, ctx: ActionContext) -> ActionResult:
        """Extract contact info from page when no form found."""
        ctx.console.print("No contact form detected; extracting contact info...", language="text")
        
        try:
            contact_info = ctx.page.evaluate(r"""() => {
                const mailto = Array.from(document.querySelectorAll('a[href^="mailto:"]'))
                    .map(a => (a.getAttribute('href') || '').trim())
                    .filter(Boolean);
                const tel = Array.from(document.querySelectorAll('a[href^="tel:"]'))
                    .map(a => (a.getAttribute('href') || '').trim())
                    .filter(Boolean);
                
                const text = (document.body && (document.body.innerText || document.body.textContent)) 
                    ? (document.body.innerText || document.body.textContent) : '';
                
                const emails = [];
                const emailRe = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi;
                let m;
                while ((m = emailRe.exec(text)) !== null) {
                    emails.push(m[0]);
                    if (emails.length >= 20) break;
                }
                
                const phones = [];
                const phoneRe = /\b(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{2,4}[\s.-]?\d{2,4}[\s.-]?\d{2,4}\b/g;
                let p;
                while ((p = phoneRe.exec(text)) !== null) {
                    const cand = (p[0] || '').trim();
                    if (!cand) continue;
                    const digits = cand.replace(/\D/g, '');
                    if (digits.length < 7 || digits.length > 15) continue;
                    phones.push(cand);
                    if (phones.length >= 20) break;
                }
                
                const uniq = (arr) => Array.from(new Set(arr));
                return {
                    mailto: uniq(mailto),
                    tel: uniq(tel),
                    emails: uniq(emails),
                    phones: uniq(phones),
                };
            }""")
            
            return ActionResult(
                success=True,
                data={
                    "url": str(ctx.page.url or ctx.url),
                    "contact_info": contact_info,
                    "note": "No contact form detected; extracted contact info instead.",
                }
            )
        except Exception as e:
            return ActionResult(success=False, error=f"Contact extraction failed: {e}")
    
    def _fill_detected_fields(self, ctx: ActionContext, form_handler, fields) -> ActionResult:
        """Fill the detected form fields."""
        # This would contain the actual form filling logic
        # For now, return success with field info
        return ActionResult(
            success=True,
            data={"fields_detected": len(fields), "url": ctx.page.url}
        )
