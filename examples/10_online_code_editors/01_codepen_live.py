#!/usr/bin/env python3
"""
01_codepen_live — Write HTML/CSS/JS on CodePen with live preview.

CodePen (codepen.io/pen) is a free online code editor with instant preview.
No login required for basic usage.

Demonstrates:
- Opening CodePen in a browser
- Injecting HTML, CSS, and JS code into the editors
- Viewing the live preview result
- Taking screenshots of the result

Usage:
    python3 01_codepen_live.py
    python3 01_codepen_live.py --html "<h1>Hello</h1>" --css "h1{color:red}"
    python3 01_codepen_live.py --code "animated gradient"
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add parent examples directory for _verbose_helper
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from _verbose_helper import init_verbose, vlog, dump_page_schema, ensure_playwright_browsers_async, dump_selectors, vlog_decision

# Preset code snippets
PRESETS = {
    "hello": {
        "html": '<div class="container">\n  <h1>Hello from NLP2CMD!</h1>\n  <p>This code was written by browser automation.</p>\n  <button id="btn">Click me</button>\n  <p id="output"></p>\n</div>',
        "css": '* { margin: 0; padding: 0; box-sizing: border-box; }\nbody { font-family: system-ui, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }\n.container { text-align: center; padding: 2rem; }\nh1 { font-size: 2.5rem; margin-bottom: 1rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }\np { font-size: 1.2rem; margin-bottom: 1rem; }\nbutton { padding: 12px 24px; font-size: 1rem; border: none; border-radius: 8px; background: white; color: #764ba2; cursor: pointer; transition: transform 0.2s; }\nbutton:hover { transform: scale(1.05); }',
        "js": 'let count = 0;\ndocument.getElementById("btn").addEventListener("click", () => {\n  count++;\n  document.getElementById("output").textContent = `Clicked ${count} time${count > 1 ? "s" : ""}!`;\n});',
    },
    "animated_gradient": {
        "html": '<div class="gradient-box">\n  <h1>Animated Gradient</h1>\n  <p>Pure CSS animation</p>\n</div>',
        "css": '.gradient-box {\n  width: 100vw; height: 100vh;\n  display: flex; flex-direction: column;\n  justify-content: center; align-items: center;\n  background: linear-gradient(-45deg, #ee7752, #e73c7e, #23a6d5, #23d5ab);\n  background-size: 400% 400%;\n  animation: gradient 8s ease infinite;\n  color: white; font-family: system-ui;\n}\nh1 { font-size: 3rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }\np { font-size: 1.2rem; margin-top: 1rem; }\n@keyframes gradient {\n  0% { background-position: 0% 50%; }\n  50% { background-position: 100% 50%; }\n  100% { background-position: 0% 50%; }\n}',
        "js": '// No JS needed for this example\nconsole.log("Animated gradient loaded!");',
    },
    "clock": {
        "html": '<div class="clock-container">\n  <div id="clock">00:00:00</div>\n  <p>Real-time clock</p>\n</div>',
        "css": 'body { display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #1a1a2e; margin: 0; }\n.clock-container { text-align: center; }\n#clock { font-family: "Courier New", monospace; font-size: 4rem; color: #00ff88; text-shadow: 0 0 20px rgba(0,255,136,0.5); }\np { color: #666; font-family: system-ui; margin-top: 1rem; }',
        "js": 'function updateClock() {\n  const now = new Date();\n  const h = String(now.getHours()).padStart(2, "0");\n  const m = String(now.getMinutes()).padStart(2, "0");\n  const s = String(now.getSeconds()).padStart(2, "0");\n  document.getElementById("clock").textContent = `${h}:${m}:${s}`;\n}\nupdateClock();\nsetInterval(updateClock, 1000);',
    },
    "todo": {
        "html": '<div class="app">\n  <h1>Todo List</h1>\n  <div class="input-row">\n    <input id="input" type="text" placeholder="Add a task...">\n    <button id="add">Add</button>\n  </div>\n  <ul id="list"></ul>\n</div>',
        "css": 'body { font-family: system-ui; background: #f0f4f8; display: flex; justify-content: center; padding-top: 3rem; margin: 0; }\n.app { width: 400px; background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }\nh1 { color: #333; margin-bottom: 1rem; }\n.input-row { display: flex; gap: 8px; margin-bottom: 1rem; }\ninput { flex: 1; padding: 10px; border: 2px solid #ddd; border-radius: 8px; font-size: 1rem; }\nbutton { padding: 10px 20px; background: #4f46e5; color: white; border: none; border-radius: 8px; cursor: pointer; }\nbutton:hover { background: #4338ca; }\nul { list-style: none; padding: 0; }\nli { padding: 10px; border-bottom: 1px solid #eee; cursor: pointer; }\nli.done { text-decoration: line-through; color: #aaa; }',
        "js": 'const input = document.getElementById("input");\nconst addBtn = document.getElementById("add");\nconst list = document.getElementById("list");\n\nfunction addTask(text) {\n  if (!text.trim()) return;\n  const li = document.createElement("li");\n  li.textContent = text;\n  li.addEventListener("click", () => li.classList.toggle("done"));\n  list.appendChild(li);\n  input.value = "";\n}\n\naddBtn.addEventListener("click", () => addTask(input.value));\ninput.addEventListener("keypress", e => { if (e.key === "Enter") addTask(input.value); });\n\n// Pre-populate\n["Learn NLP2CMD", "Automate browser tasks", "Build cool projects"].forEach(addTask);',
    },
}


async def type_into_codepen_editor(page, panel_selector: str, code: str):
    """Type code into a CodePen editor panel using CodeMirror API."""
    # CodePen uses CodeMirror — inject code via JS evaluation
    try:
        # Try CodeMirror 6 API first
        await page.evaluate(f'''
            (() => {{
                const panel = document.querySelector('{panel_selector}');
                if (panel) {{
                    const cm = panel.querySelector('.CodeMirror');
                    if (cm && cm.CodeMirror) {{
                        cm.CodeMirror.setValue({repr(code)});
                        return true;
                    }}
                }}
                return false;
            }})()
        ''')
    except Exception:
        pass

    # Fallback: click on the panel and type
    try:
        panel = page.locator(panel_selector).first
        if await panel.count() > 0:
            textarea = panel.locator("textarea").first
            if await textarea.count() > 0:
                await textarea.click()
                await textarea.fill("")
                await textarea.type(code, delay=5)
                return True
    except Exception:
        pass

    return False


def generate_code_from_description(description: str) -> dict:
    """Generate simple HTML/CSS/JS from natural language description."""
    # Simple rule-based generation for common patterns
    desc = description.lower()
    
    if "hello" in desc or "world" in desc:
        return {
            "html": '<div class="container">\n  <h1>Hello World!</h1>\n  <p>Generated from: "' + description + '"</p>\n</div>',
            "css": '* { margin: 0; padding: 0; box-sizing: border-box; }\nbody { font-family: system-ui, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }\n.container { text-align: center; padding: 2rem; }\nh1 { font-size: 2.5rem; margin-bottom: 1rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }\np { font-size: 1.2rem; opacity: 0.8; }',
            "js": 'console.log("Hello World page loaded!");'
        }
    elif "button" in desc:
        return {
            "html": '<div class="container">\n  <h1>Interactive Page</h1>\n  <button id="btn">Click me!</button>\n  <p id="output"></p>\n</div>',
            "css": '* { margin: 0; padding: 0; box-sizing: border-box; }\nbody { font-family: system-ui, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #f0f4f8; }\n.container { text-align: center; padding: 2rem; }\nh1 { color: #333; margin-bottom: 2rem; }\nbutton { padding: 12px 24px; font-size: 1rem; border: none; border-radius: 8px; background: #4f46e5; color: white; cursor: pointer; transition: transform 0.2s; }\nbutton:hover { transform: scale(1.05); }\n#output { margin-top: 1rem; font-size: 1.1rem; color: #666; }',
            "js": 'document.getElementById("btn").addEventListener("click", () => {\n  document.getElementById("output").textContent = "Button clicked!";\n});'
        }
    else:
        # Default simple page
        return {
            "html": '<div class="container">\n  <h1>Generated Page</h1>\n  <p>From description: "' + description + '"</p>\n</div>',
            "css": '* { margin: 0; padding: 0; box-sizing: border-box; }\nbody { font-family: system-ui, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #f8f9fa; }\n.container { text-align: center; padding: 2rem; }\nh1 { color: #333; margin-bottom: 1rem; }\np { color: #666; }',
            "js": 'console.log("Generated page loaded!");'
        }


async def main():
    parser = argparse.ArgumentParser(description="Write code on CodePen")
    parser.add_argument("--preset", default="hello",
                        choices=list(PRESETS.keys()),
                        help="Preset code snippet")
    parser.add_argument("--html", default=None, help="Custom HTML code")
    parser.add_argument("--css", default=None, help="Custom CSS code")
    parser.add_argument("--js", default=None, help="Custom JS code")
    parser.add_argument("--code", default=None, help="Generate code from description")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--screenshot-dir", default="screenshots")
    parser.add_argument("--url", default="https://codepen.io/pen/",
                        help="CodePen URL")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show page schema, editor detection, and decision logs")
    args = parser.parse_args()

    init_verbose(args.verbose)

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: pip install playwright")
        sys.exit(1)

    # Auto-install browsers if needed
    if not await ensure_playwright_browsers_async(auto_install=True):
        sys.exit(1)

    # Get code from preset, args, or generated description
    if args.code:
        generated = generate_code_from_description(args.code)
        html_code = args.html or generated["html"]
        css_code = args.css or generated["css"]
        js_code = args.js or generated["js"]
        preset_name = "generated"
    else:
        preset = PRESETS[args.preset]
        html_code = args.html or preset["html"]
        css_code = args.css or preset["css"]
        js_code = args.js or preset["js"]
        preset_name = args.preset

    print(f"=== CodePen Live Editor ===")
    print(f"Preset: {preset_name}")
    print(f"HTML: {len(html_code)} chars")
    print(f"CSS:  {len(css_code)} chars")
    print(f"JS:   {len(js_code)} chars")
    print()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=args.headless)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})

        print("1. Opening CodePen...")
        await page.goto(args.url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        vlog(f"Page loaded: {page.url}")

        # Dismiss cookie/signup banners
        for selector in [
            "button:has-text('Accept')", "button:has-text('OK')",
            ".cookie-banner button", "[data-testid='close']",
            "button:has-text('No thanks')", "button:has-text('×')",
        ]:
            try:
                btn = page.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    vlog(f"Dismissed dialog via: {selector}")
                    await page.wait_for_timeout(300)
            except Exception:
                continue

        await page.wait_for_timeout(2000)

        # Inspect page schema
        await dump_page_schema(page)
        await dump_selectors(page, {
            "codemirror": ".CodeMirror",
            "monaco": ".monaco-editor",
            "ace": ".ace_editor",
            "textarea": "textarea",
            "result_iframe": "iframe#result, iframe[name='result']",
        })

        # Inject code into editors
        print("2. Injecting HTML...")
        # CodePen has three main editor panels: HTML, CSS, JS
        # Try to find the CodeMirror instances and set their values
        try:
            await page.evaluate(f'''
                (() => {{
                    // CodePen exposes editors via __NEXT_DATA__ or CodeMirror instances
                    const cms = document.querySelectorAll('.CodeMirror');
                    if (cms.length >= 3) {{
                        cms[0].CodeMirror.setValue({json_safe(html_code)});
                        cms[1].CodeMirror.setValue({json_safe(css_code)});
                        cms[2].CodeMirror.setValue({json_safe(js_code)});
                        return true;
                    }}
                    return false;
                }})()
            ''')
            print("   Injected via CodeMirror API")
        except Exception as e:
            print(f"   CodeMirror API not available: {e}")
            # Fallback: use textarea typing
            editors = page.locator("textarea.code-editor, .editor textarea, .CodeMirror textarea")
            count = await editors.count()
            print(f"   Found {count} editor textareas, trying click+type...")

            # Try clicking on editor sections and typing
            sections = page.locator('[class*="editor"], [data-editor]')
            sec_count = await sections.count()
            codes = [html_code, css_code, js_code]
            labels = ["HTML", "CSS", "JS"]

            for i, (code, label) in enumerate(zip(codes, labels)):
                try:
                    # Try to find editor by label
                    header = page.locator(f'button:has-text("{label}"), [data-type="{label.lower()}"]').first
                    if await header.count() > 0:
                        await header.click()
                        await page.wait_for_timeout(500)

                    # Find and fill textarea
                    ta = page.locator("textarea").nth(i)
                    if await ta.count() > 0:
                        await ta.click()
                        await ta.fill(code)
                        print(f"   {label}: typed {len(code)} chars")
                except Exception as ex:
                    print(f"   {label}: could not inject ({ex})")

        await page.wait_for_timeout(2000)

        # Screenshot
        print("3. Saving screenshot...")
        ss_dir = Path(args.screenshot_dir)
        ss_dir.mkdir(parents=True, exist_ok=True)
        path = ss_dir / f"codepen_{preset_name}.png"
        await page.screenshot(path=str(path))
        print(f"   Screenshot: {path}")

        # Try to capture preview iframe screenshot
        try:
            preview = page.frame_locator("iframe#result, iframe[name='result'], iframe.result")
            preview_el = page.locator("iframe#result, iframe[name='result'], iframe.result").first
            if await preview_el.count() > 0:
                path2 = ss_dir / f"codepen_{preset_name}_preview.png"
                await preview_el.screenshot(path=str(path2))
                print(f"   Preview screenshot: {path2}")
        except Exception:
            pass

        await browser.close()

    print()
    print(f"Done! Preset: {preset_name}")


def json_safe(s: str) -> str:
    """Escape string for safe JS injection."""
    import json
    return json.dumps(s)


if __name__ == "__main__":
    asyncio.run(main())
