#!/usr/bin/env python3
"""Test Oferteo page loading and company link detection"""
import sys
sys.path.insert(0, 'src')

from playwright.sync_api import sync_playwright

with open('/tmp/oferteo_debug.log', 'w') as f:
    f.write("Starting Oferteo test...\n")
    f.flush()
    
    try:
        with sync_playwright() as p:
            f.write("Launching browser...\n")
            f.flush()
            browser = p.chromium.launch(headless=True)
            
            f.write("Creating context...\n")
            f.flush()
            context = browser.new_context()
            page = context.new_page()
            
            f.write("Navigating to Oferteo...\n")
            f.flush()
            page.goto('https://www.oferteo.pl/katalog-firm', wait_until='networkidle')
            page.wait_for_timeout(5000)  # Wait longer for JS to load
            
            f.write("Page loaded, checking content...\n")
            f.flush()
            
            # Check page title
            title = page.title()
            f.write(f"Page title: {title}\n")
            f.flush()
            
            # Check for company links
            links = page.evaluate("""() => {
                const allLinks = Array.from(document.querySelectorAll('a[href]'));
                return {
                    total: allLinks.length,
                    withFirma: allLinks.filter(a => a.href.includes('/firma/')).length,
                    sample: allLinks.slice(0, 10).map(a => ({
                        text: a.textContent.trim().slice(0, 30),
                        href: a.getAttribute('href')
                    }))
                };
            }""")
            
            f.write(f"Total links: {links['total']}\n")
            f.write(f"Links with /firma/: {links['withFirma']}\n")
            f.write("Sample links:\n")
            for link in links['sample']:
                f.write(f"  - {link['text'][:30]:30} | {link['href'][:50]}\n")
            
            browser.close()
            f.write("\n=== SUCCESS ===\n")
            f.flush()
    except Exception as e:
        f.write(f"\n=== ERROR: {e} ===\n")
        import traceback
        f.write(traceback.format_exc())
