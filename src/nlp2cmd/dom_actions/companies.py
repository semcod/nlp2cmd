"""Company extraction DOM action handlers."""

from __future__ import annotations
import time
from typing import TYPE_CHECKING

from .base import DomAction, ActionContext, ActionResult
from .registry import register_action

if TYPE_CHECKING:
    pass


@register_action("extract_companies")
@register_action("extract_company_websites_deep")
class ExtractCompaniesAction(DomAction):
    """Extract company information from catalog pages."""
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        """Navigate to company profiles and extract their external websites."""
        try:
            self._debug("extract_company_websites_deep: starting deep extraction")
            
            # Wait for dynamically loaded content
            self._wait_for_content(ctx.page)
            
            # Dismiss popups
            self._dismiss_popups(ctx.page, ctx.schema_loader)
            
            max_companies = ctx.action_spec.get("max_companies", 20)
            base_url = ctx.page.url
            
            # Handle Oferteo-specific navigation
            if "oferteo.pl" in base_url:
                base_url = self._handle_oferteo_navigation(ctx)
            
            # Wait for company links to appear
            self._wait_for_company_links(ctx.page)
            
            # Find company profile links
            company_links = self._find_company_links(ctx, base_url)
            
            if not company_links:
                return ActionResult(
                    success=False,
                    error="No company profile links found"
                )
            
            # Process profiles and extract websites
            companies_data = self._extract_websites(ctx, company_links, max_companies, base_url)
            
            # Store for save_to_file action
            ctx.extracted_data.extend(companies_data)
            
            # Display results
            ctx.console.print(f"\n✅ Extracted {len(companies_data)} companies with websites:", language="text")
            for c in companies_data[:10]:
                website = c.get("website", "N/A")
                ctx.console.print(f"  • {c['name']}: {website}", language="text")
            if len(companies_data) > 10:
                ctx.console.print(f"  ... and {len(companies_data) - 10} more", language="text")
            
            return ActionResult(success=True, data={"companies": companies_data})
            
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Deep company extraction failed: {e}"
            )
    
    def _wait_for_content(self, page) -> None:
        """Wait for page content to load."""
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
        page.wait_for_timeout(1200)
    
    def _handle_oferteo_navigation(self, ctx: ActionContext) -> str:
        """Handle Oferteo-specific navigation to find company listings."""
        cur = ""
        try:
            cur = str(ctx.page.url or "")
        except Exception:
            cur = ""
        
        # If on homepage, try to jump to city listing
        from urllib.parse import urlparse
        try:
            cur_path = urlparse(cur).path or ""
        except Exception:
            cur_path = ""
        
        if "oferteo.pl" in cur and cur_path in {"", "/"}:
            for cand in [
                "https://www.oferteo.pl/firmy/gdansk",
                "https://www.oferteo.pl/firmy/gda%C5%84sk",
                "https://www.oferteo.pl/firmy-gdansk",
                "https://www.oferteo.pl/firmy-budowlane/gdansk",
            ]:
                try:
                    ctx.page.goto(cand, wait_until="domcontentloaded", timeout=15000)
                    ctx.page.wait_for_timeout(900)
                    self._dismiss_popups(ctx.page, ctx.schema_loader)
                    
                    cur_after = str(ctx.page.url or "")
                    if urlparse(cur_after).path.strip("/") != "":
                        return ctx.page.url
                except Exception:
                    continue
        
        # If on global catalog, jump to city listing
        if "oferteo.pl" in cur and "/katalog-firm" in urlparse(cur).path:
            try:
                ctx.page.goto("https://www.oferteo.pl/firmy/gdansk", wait_until="domcontentloaded", timeout=15000)
                ctx.page.wait_for_timeout(1200)
                self._dismiss_popups(ctx.page, ctx.schema_loader)
                return ctx.page.url
            except Exception:
                pass
        
        return ctx.page.url
    
    def _wait_for_company_links(self, page) -> None:
        """Wait for company profile links to appear."""
        try:
            start_t = time.time()
            last_seen = 0
            while (time.time() - start_t) < 15.0:
                try:
                    cnt = page.evaluate(
                        r"""() => Array.from(document.querySelectorAll('a[href]'))
                            .map(a => (a.getAttribute('href') || '').toLowerCase())
                            .filter(h => h.includes('/firma')).length"""
                    )
                except Exception:
                    cnt = 0
                
                if isinstance(cnt, int) and cnt > 0:
                    self._debug(f"extract_company_websites_deep: detected {cnt} '/firma/' links")
                    break
                
                # Scroll to trigger lazy loading
                if isinstance(cnt, int) and cnt == last_seen:
                    try:
                        page.evaluate("() => window.scrollBy(0, Math.max(600, window.innerHeight))")
                    except Exception:
                        pass
                if isinstance(cnt, int):
                    last_seen = cnt
                page.wait_for_timeout(900)
        except Exception:
            pass
    
    def _find_company_links(self, ctx: ActionContext, base_url: str) -> list[dict[str, str]]:
        """Find company profile links on the catalog page."""
        from urllib.parse import urljoin
        
        company_links: list[dict[str, str]] = []
        seen_hrefs: set[str] = set()
        
        for pass_idx in range(4):
            batch = self._collect_company_links(ctx.page)
            for item in batch:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", "")).strip()
                href = str(item.get("href", "")).strip()
                if not name or not href:
                    continue
                
                # Make URL absolute
                if not href.startswith("http"):
                    href = urljoin(base_url, href)
                
                key = href.lower()
                if key in seen_hrefs:
                    continue
                seen_hrefs.add(key)
                company_links.append({"name": name, "href": href})
            
            if len(company_links) >= 120:
                break
            
            # Scroll to load more
            try:
                ctx.page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
                ctx.page.wait_for_timeout(900)
            except Exception:
                break
        
        self._debug(f"extract_company_websites_deep: found {len(company_links)} potential companies")
        return company_links
    
    def _collect_company_links(self, page) -> list[dict[str, str]]:
        """Collect company links from the page."""
        res = page.evaluate(r"""() => {
            const links = [];
            const seen = new Set();
            
            // Prefer the main listings area if present
            const roots = document.querySelectorAll('main, [role="main"], .results, .listing, #content, .companies, .firmy');
            const root = roots.length > 0 ? roots[0] : document.body;
            
            const allLinks = Array.from(root.querySelectorAll('a[href]'));
            for (const el of allLinks) {
                const href = (el.getAttribute('href') || '').trim();
                const text = (el.textContent || '').trim().replace(/\s+/g, ' ');
                if (!href || !text) continue;
                if (text.length < 2 || text.length > 140) continue;
                if (/^(#|javascript:|mailto:|tel:)/i.test(href)) continue;
                
                const hrefLower = href.toLowerCase();
                // Exclude categories/listings and noise
                if (hrefLower.includes('/firma-')) continue;
                if (hrefLower.includes('/firmy-')) continue;
                if (hrefLower.includes('/firmy/')) continue;
                if (hrefLower.includes('/katalog') || hrefLower.includes('/kategorie')) continue;
                if (hrefLower.includes('facebook.com') || hrefLower.includes('instagram.com')) continue;
                
                // Company profiles
                const looksLikeCompany = (
                    hrefLower.includes('/firma') ||
                    hrefLower.includes('/company/') ||
                    hrefLower.includes('/wykonawca') ||
                    hrefLower.includes('/profil')
                );
                if (!looksLikeCompany) continue;
                
                if (seen.has(hrefLower)) continue;
                seen.add(hrefLower);
                links.push({name: text, href: href});
            }
            return links;
        }""")
        return res if isinstance(res, list) else []
    
    def _extract_websites(
        self,
        ctx: ActionContext,
        company_links: list[dict[str, str]],
        max_companies: int,
        base_url: str
    ) -> list[dict[str, str]]:
        """Visit company profiles and extract external websites."""
        from urllib.parse import urljoin, parse_qs, unquote, urlparse
        
        companies_data: list[dict[str, str]] = []
        profile_fallback: list[dict[str, str]] = []
        
        _max_companies_int = max(1, min(int(max_companies), 200))
        
        # Build fallback list
        for company in company_links[:_max_companies_int]:
            try:
                name = str(company.get("name", "")).strip()
                href = str(company.get("href", "")).strip()
                if not href:
                    continue
                if not href.startswith("http"):
                    href = urljoin(base_url, href)
                profile_fallback.append({"name": name, "oferteo_url": href, "website": ""})
            except Exception:
                continue
        
        # Visit profiles and extract websites
        action_deadline = time.time() + 85.0
        probe_profiles = min(25, _max_companies_int)
        
        for idx, company in enumerate(company_links[:probe_profiles], 1):
            try:
                if time.time() >= action_deadline:
                    self._debug("extract_company_websites_deep: time budget exceeded")
                    break
                
                name = str(company.get("name", "")).strip()
                href = str(company.get("href", "")).strip()
                if not name or not href:
                    continue
                
                if not href.startswith("http"):
                    href = urljoin(base_url, href)
                
                ctx.console.print(f"[{idx}/{min(len(company_links), probe_profiles)}] Checking: {name}", language="text")
                
                # Navigate to company profile
                ctx.page.goto(href, wait_until="domcontentloaded", timeout=7000)
                ctx.page.wait_for_timeout(250)
                self._dismiss_popups(ctx.page, ctx.schema_loader)
                
                # Find external website
                external_site = self._find_external_website(ctx.page)
                
                if external_site:
                    companies_data.append({
                        "name": name,
                        "oferteo_url": href,
                        "website": external_site
                    })
                    ctx.console.print(f"   ✓ Found website: {external_site}", language="text")
                    
                    # Stop early when we have enough
                    real_websites = [c for c in companies_data if c.get("website")]
                    if len(real_websites) >= _max_companies_int:
                        break
                else:
                    ctx.console.print(f"   ⚠ No external website found", language="text")
                    companies_data.append({
                        "name": name,
                        "oferteo_url": href,
                        "website": ""
                    })
                
                # Go back to catalog
                try:
                    ctx.page.go_back(wait_until="domcontentloaded", timeout=9000)
                    ctx.page.wait_for_timeout(200)
                except Exception:
                    ctx.page.goto(base_url, wait_until="domcontentloaded", timeout=15000)
                    ctx.page.wait_for_timeout(300)
                    
            except Exception as e:
                self._debug(f"Error processing company: {e}")
                continue
        
        # If no real websites found, use fallback
        real_websites_cnt = len([c for c in companies_data if str(c.get("website") or "").strip()])
        if real_websites_cnt == 0 and profile_fallback:
            companies_data = profile_fallback
        
        return companies_data
    
    def _find_external_website(self, page) -> str | None:
        """Find external website link on a company profile page."""
        external_site = page.evaluate(r"""() => {
            const externalPatterns = [
                'a[href^="http"]:not([href*="oferteo.pl"]):not([href*="facebook.com"])',
                'a[href*="oferteo.pl"][href*="redirect"]',
                'a[href*="oferteo.pl"][href*="url="]',
                '.website a', '.www a', '.company-website a',
            ];
            for (const pattern of externalPatterns) {
                const links = document.querySelectorAll(pattern);
                for (const link of links) {
                    const href = link.getAttribute('href');
                    if (href && href.startsWith('http') && 
                        !href.includes('oferteo.pl') &&
                        !href.includes('facebook.com')) {
                        return href;
                    }
                    if (href && href.includes('oferteo.pl') && (href.includes('redirect') || href.includes('url='))) {
                        return href;
                    }
                }
            }
            return null;
        }""")
        
        if not external_site or not isinstance(external_site, str):
            return None
        
        raw_ext = external_site.strip()
        ext_low = raw_ext.lower()
        
        # If it's a bare domain, normalize to https://
        if ext_low and (not ext_low.startswith("http")) and "." in ext_low and "/" not in ext_low:
            raw_ext = f"https://{raw_ext}"
            ext_low = raw_ext.lower()
        
        # Decode oferteo redirect links
        try:
            from urllib.parse import parse_qs, unquote, urlparse
            parsed = urlparse(raw_ext)
            if "oferteo.pl" in (parsed.netloc or ""):
                qs = parse_qs(parsed.query or "")
                for key in ("url", "u", "target", "redirect"):
                    if key in qs and qs[key]:
                        cand = unquote(str(qs[key][0]))
                        if cand.startswith("http"):
                            raw_ext = cand
                            ext_low = raw_ext.lower()
                            break
        except Exception:
            pass
        
        # Filter out bad domains
        bad_domains = [
            "apps.apple.com", "play.google.com", "itunes.apple.com",
            "oferteo.pl", "facebook.com", "instagram.com",
            "linkedin.com", "twitter.com", "x.com", "youtube.com",
            "tiktok.com", "goo.gl", "bit.ly",
        ]
        if any(b in ext_low for b in bad_domains):
            return None
        
        return raw_ext
