#!/usr/bin/env python3
"""
04_jsfiddle_frontend — Write HTML/CSS/JS on JSFiddle via Playwright.

JSFiddle (jsfiddle.net) is a free front-end code playground.
No login required for basic usage.

Demonstrates:
- Opening JSFiddle in a browser
- Injecting HTML, CSS, and JS code into separate panels
- Clicking Run to see the preview
- Taking screenshots of the result

Usage:
    python3 04_jsfiddle_frontend.py
    python3 04_jsfiddle_frontend.py --preset particles
    python3 04_jsfiddle_frontend.py --preset calculator
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from _verbose_helper import init_verbose, vlog, dump_page_schema, dump_selectors, vlog_decision

PRESETS = {
    "hello": {
        "html": '<div id="app">\n  <h1>JSFiddle + NLP2CMD</h1>\n  <p>Automated code injection via Playwright</p>\n  <div id="counter">0</div>\n  <button onclick="increment()">+1</button>\n</div>',
        "css": '#app { font-family: system-ui; text-align: center; padding: 2rem; }\nh1 { color: #2563eb; }\n#counter { font-size: 3rem; font-weight: bold; color: #059669; margin: 1rem 0; }\nbutton { padding: 10px 30px; font-size: 1.2rem; background: #2563eb; color: white; border: none; border-radius: 8px; cursor: pointer; }\nbutton:hover { background: #1d4ed8; }',
        "js": 'let count = 0;\nfunction increment() {\n  count++;\n  document.getElementById("counter").textContent = count;\n}',
    },
    "particles": {
        "html": '<canvas id="canvas"></canvas>',
        "css": 'body { margin: 0; overflow: hidden; background: #0a0a2a; }\ncanvas { display: block; }',
        "js": (
            'const canvas = document.getElementById("canvas");\n'
            'const ctx = canvas.getContext("2d");\n'
            'canvas.width = window.innerWidth;\n'
            'canvas.height = window.innerHeight;\n'
            '\n'
            'const particles = [];\n'
            'for (let i = 0; i < 100; i++) {\n'
            '  particles.push({\n'
            '    x: Math.random() * canvas.width,\n'
            '    y: Math.random() * canvas.height,\n'
            '    vx: (Math.random() - 0.5) * 2,\n'
            '    vy: (Math.random() - 0.5) * 2,\n'
            '    r: Math.random() * 3 + 1,\n'
            '    color: `hsl(${Math.random() * 360}, 80%, 60%)`\n'
            '  });\n'
            '}\n'
            '\n'
            'function animate() {\n'
            '  ctx.fillStyle = "rgba(10, 10, 42, 0.1)";\n'
            '  ctx.fillRect(0, 0, canvas.width, canvas.height);\n'
            '  particles.forEach(p => {\n'
            '    p.x += p.vx;\n'
            '    p.y += p.vy;\n'
            '    if (p.x < 0 || p.x > canvas.width) p.vx *= -1;\n'
            '    if (p.y < 0 || p.y > canvas.height) p.vy *= -1;\n'
            '    ctx.beginPath();\n'
            '    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);\n'
            '    ctx.fillStyle = p.color;\n'
            '    ctx.fill();\n'
            '  });\n'
            '  requestAnimationFrame(animate);\n'
            '}\n'
            'animate();\n'
        ),
    },
    "calculator": {
        "html": (
            '<div class="calc">\n'
            '  <input id="display" type="text" readonly value="0">\n'
            '  <div class="buttons">\n'
            '    <button onclick="clear_()">C</button>\n'
            '    <button onclick="append(\'(\')">(</button>\n'
            '    <button onclick="append(\')\')">)</button>\n'
            '    <button onclick="append(\'/\')">/</button>\n'
            '    <button onclick="append(\'7\')">7</button>\n'
            '    <button onclick="append(\'8\')">8</button>\n'
            '    <button onclick="append(\'9\')">9</button>\n'
            '    <button onclick="append(\'*\')">*</button>\n'
            '    <button onclick="append(\'4\')">4</button>\n'
            '    <button onclick="append(\'5\')">5</button>\n'
            '    <button onclick="append(\'6\')">6</button>\n'
            '    <button onclick="append(\'-\')">-</button>\n'
            '    <button onclick="append(\'1\')">1</button>\n'
            '    <button onclick="append(\'2\')">2</button>\n'
            '    <button onclick="append(\'3\')">3</button>\n'
            '    <button onclick="append(\'+\')">+</button>\n'
            '    <button onclick="append(\'0\')" class="wide">0</button>\n'
            '    <button onclick="append(\'.\')">.</button>\n'
            '    <button onclick="calc()" class="eq">=</button>\n'
            '  </div>\n'
            '</div>'
        ),
        "css": (
            'body { display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #1e293b; margin: 0; font-family: system-ui; }\n'
            '.calc { background: #334155; border-radius: 16px; padding: 1.5rem; box-shadow: 0 10px 40px rgba(0,0,0,0.4); }\n'
            '#display { width: 100%; box-sizing: border-box; padding: 15px; font-size: 1.8rem; text-align: right; border: none; border-radius: 8px; background: #0f172a; color: #22d3ee; margin-bottom: 1rem; }\n'
            '.buttons { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }\n'
            'button { padding: 15px; font-size: 1.2rem; border: none; border-radius: 8px; background: #475569; color: white; cursor: pointer; transition: background 0.2s; }\n'
            'button:hover { background: #64748b; }\n'
            '.wide { grid-column: span 2; }\n'
            '.eq { background: #22d3ee; color: #0f172a; font-weight: bold; }\n'
            '.eq:hover { background: #06b6d4; }'
        ),
        "js": (
            'let expr = "";\n'
            'function append(ch) { expr += ch; document.getElementById("display").value = expr; }\n'
            'function clear_() { expr = ""; document.getElementById("display").value = "0"; }\n'
            'function calc() {\n'
            '  try { document.getElementById("display").value = eval(expr); expr = String(eval(expr)); }\n'
            '  catch(e) { document.getElementById("display").value = "Error"; expr = ""; }\n'
            '}'
        ),
    },
}


async def main():
    parser = argparse.ArgumentParser(description="Write code on JSFiddle")
    parser.add_argument("--preset", default="hello", choices=list(PRESETS.keys()))
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--screenshot-dir", default="screenshots")
    parser.add_argument("--url", default="https://jsfiddle.net/")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show page schema, editor detection, and decision logs")
    args = parser.parse_args()

    init_verbose(args.verbose)

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: pip install playwright && playwright install chromium")
        sys.exit(1)

    preset = PRESETS[args.preset]
    html_code = preset["html"]
    css_code = preset["css"]
    js_code = preset["js"]

    print(f"=== JSFiddle Editor ===")
    print(f"Preset: {args.preset}")
    print(f"HTML: {len(html_code)} chars, CSS: {len(css_code)} chars, JS: {len(js_code)} chars")
    print()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=args.headless)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})

        print("1. Opening JSFiddle...")
        await page.goto(args.url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        vlog(f"Page loaded: {page.url}")

        # Dismiss popups/cookie banners
        for sel in [
            "button:has-text('Accept')", "button:has-text('OK')",
            "button:has-text('I agree')", ".cc-compliance a",
            "button:has-text('Got it')", "button:has-text('Consent')",
        ]:
            try:
                btn = page.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    vlog(f"Dismissed dialog via: {sel}")
                    await page.wait_for_timeout(300)
            except Exception:
                continue

        await page.wait_for_timeout(2000)

        # Inspect page schema
        await dump_page_schema(page)
        await dump_selectors(page, {
            "panel_html_cm": "#panel-html .CodeMirror",
            "panel_css_cm": "#panel-css .CodeMirror",
            "panel_js_cm": "#panel-js .CodeMirror",
            "codemirror_any": ".CodeMirror",
            "run_btn": "#run, button:has-text('Run')",
            "result_iframe": "iframe[name='result'], #result-iframe",
        })

        # JSFiddle uses CodeMirror editors in panels
        print("2. Injecting code into editors...")

        # Panel mapping: JSFiddle has panels for HTML, CSS, JS
        panels = [
            ("HTML", html_code, "#panel-html .CodeMirror", "html"),
            ("CSS", css_code, "#panel-css .CodeMirror", "css"),
            ("JS", js_code, "#panel-js .CodeMirror", "js"),
        ]

        for label, code, selector, panel_id in panels:
            code_escaped = json.dumps(code)
            try:
                # Try CodeMirror API injection
                result = await page.evaluate(f'''
                    (() => {{
                        const cm = document.querySelector('{selector}');
                        if (cm && cm.CodeMirror) {{
                            cm.CodeMirror.setValue({code_escaped});
                            return true;
                        }}
                        return false;
                    }})()
                ''')
                if result:
                    print(f"   {label}: injected via CodeMirror ({len(code)} chars)")
                    vlog_decision(f"{label}: CodeMirror injection", f"Selector '{selector}' matched")
                    continue
                else:
                    vlog(f"{label}: CodeMirror selector '{selector}' not found")
            except Exception as e:
                vlog(f"{label}: CodeMirror injection error: {e}")

            # Fallback: try finding textarea by panel
            try:
                panel = page.locator(f"#{panel_id}, [data-panel='{panel_id}']").first
                if await panel.count() > 0:
                    ta = panel.locator("textarea").first
                    if await ta.count() > 0:
                        await ta.click()
                        await ta.fill(code)
                        print(f"   {label}: injected via textarea ({len(code)} chars)")
                        vlog_decision(f"{label}: textarea injection", f"Panel #{panel_id} textarea fallback")
                        continue
                else:
                    vlog(f"{label}: panel #{panel_id} not found")
            except Exception as e:
                vlog(f"{label}: textarea fallback error: {e}")

            print(f"   {label}: could not inject")
            vlog(f"{label}: all injection methods failed")

        await page.wait_for_timeout(1000)

        # Click Run button
        print("3. Clicking Run...")
        run_selectors = [
            "#run", "button:has-text('Run')", "[data-action='run']",
            ".actionItem a:has-text('Run')",
        ]
        for run_sel in run_selectors:
            try:
                btn = page.locator(run_sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    print(f"   Run clicked")
                    vlog_decision(f"Run button: {run_sel}", "First visible match", alternatives=run_selectors)
                    break
                else:
                    vlog(f"Run selector '{run_sel}': no visible match")
            except Exception:
                continue

        await page.wait_for_timeout(3000)

        # Screenshot
        print("4. Saving screenshot...")
        ss_dir = Path(args.screenshot_dir)
        ss_dir.mkdir(parents=True, exist_ok=True)
        path = ss_dir / f"jsfiddle_{args.preset}.png"
        await page.screenshot(path=str(path))
        print(f"   Screenshot: {path}")

        # Try to capture result iframe
        try:
            result_frame = page.locator("iframe[name='result'], #result-iframe, .result-frame").first
            if await result_frame.count() > 0:
                path2 = ss_dir / f"jsfiddle_{args.preset}_result.png"
                await result_frame.screenshot(path=str(path2))
                print(f"   Result screenshot: {path2}")
        except Exception:
            pass

        await browser.close()

    print()
    print(f"Done! Preset: {args.preset}")


if __name__ == "__main__":
    asyncio.run(main())
