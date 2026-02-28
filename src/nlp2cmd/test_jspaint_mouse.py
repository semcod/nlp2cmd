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
        
        # Test if we can draw by dispatching mouse events on the main canvas
        page.evaluate('''() => {
            const canvas = document.querySelector('.main-canvas') || document.querySelector('canvas');
            const rect = canvas.getBoundingClientRect();
            
            // Draw a line using MouseEvents (simulating user interaction instead of raw ctx manipulation)
            const eventOpts = { bubbles: true, cancelable: true, view: window };
            
            const mousedown = new MouseEvent('mousedown', { ...eventOpts, clientX: rect.left + 100, clientY: rect.top + 100 });
            const mousemove = new MouseEvent('mousemove', { ...eventOpts, clientX: rect.left + 200, clientY: rect.top + 200 });
            const mouseup = new MouseEvent('mouseup', { ...eventOpts, clientX: rect.left + 200, clientY: rect.top + 200 });
            
            canvas.dispatchEvent(mousedown);
            canvas.dispatchEvent(mousemove);
            canvas.dispatchEvent(mouseup);
        }''')
        
        time.sleep(2)
        page.screenshot(path="jspaint_mouse_test.png")
        print("Mouse test done")
        browser.close()

if __name__ == "__main__":
    run()
