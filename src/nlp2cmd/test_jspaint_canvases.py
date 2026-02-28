from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://jspaint.app")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        canvases = page.evaluate('''() => {
            const canvases = document.querySelectorAll('canvas');
            return Array.from(canvases).map(c => {
                return {
                    id: c.id,
                    className: c.className,
                    width: c.width,
                    height: c.height,
                    offsetWidth: c.offsetWidth,
                    offsetHeight: c.offsetHeight
                };
            });
        }''')
        print("Canvases found:", canvases)
        browser.close()

if __name__ == "__main__":
    run()
