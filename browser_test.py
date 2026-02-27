#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')

with open('/tmp/browser_test.log', 'w') as f:
    f.write("Step 1: Starting browser test\n")
    f.flush()
    
    try:
        f.write("Step 2: Importing playwright...\n")
        f.flush()
        from playwright.sync_api import sync_playwright
        f.write("Step 3: Playwright imported\n")
        f.flush()
        
        f.write("Step 4: Starting browser...\n")
        f.flush()
        with sync_playwright() as p:
            f.write("Step 5: Launching chromium...\n")
            f.flush()
            browser = p.chromium.launch(headless=True)
            f.write("Step 6: Browser launched\n")
            f.flush()
            
            f.write("Step 7: Creating context...\n")
            f.flush()
            context = browser.new_context()
            f.write("Step 8: Context created\n")
            f.flush()
            
            f.write("Step 9: Creating page...\n")
            f.flush()
            page = context.new_page()
            f.write("Step 10: Page created\n")
            f.flush()
            
            f.write("Step 11: Navigating to Google...\n")
            f.flush()
            page.goto('https://www.google.com', wait_until='domcontentloaded')
            f.write("Step 12: Navigation complete\n")
            f.flush()
            
            browser.close()
            f.write("\n=== SUCCESS ===\n")
            f.flush()
    except Exception as e:
        f.write(f"\n=== ERROR: {e} ===\n")
        import traceback
        f.write(traceback.format_exc())
