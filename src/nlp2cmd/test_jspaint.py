from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://jspaint.app")
        page.wait_for_load_state("networkidle")
        print("Page loaded")
        time.sleep(2)
        
        # Draw circle directly via canvas evaluate
        try:
            page.evaluate('''() => {
                const canvas = document.querySelector('canvas');
                console.log("Canvas:", canvas);
                if (!canvas) return;
                const ctx = canvas.getContext('2d');
                console.log("Ctx:", ctx);
                const rect = canvas.getBoundingClientRect();
                const cx = rect.width / 2;
                const cy = rect.height / 2;
                ctx.beginPath();
                ctx.arc(cx, cy, 100, 0, 2 * Math.PI);
                ctx.fillStyle = 'red';
                ctx.fill();
            }''')
            print("Canvas evaluate ran")
            page.screenshot(path="jspaint_test.png")
        except Exception as e:
            print(f"Error: {e}")
            
        time.sleep(1)
        browser.close()

if __name__ == "__main__":
    run()
