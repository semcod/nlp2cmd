#!/usr/bin/env python3
"""
02_mycompiler_run — Write and run code on myCompiler.io via Playwright.

myCompiler.io supports 27+ languages with no login required.
This example writes code, runs it, and captures the output.

Usage:
    python3 02_mycompiler_run.py --lang python --code "print('Hello NLP2CMD')"
    python3 02_mycompiler_run.py --lang javascript --code "console.log(42)"
    python3 02_mycompiler_run.py --lang python --preset fibonacci
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add parent examples directory for _verbose_helper
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from _verbose_helper import init_verbose, vlog, dump_page_schema, dump_selectors, vlog_decision

LANGUAGE_URLS = {
    "python": "https://www.mycompiler.io/new/python",
    "javascript": "https://www.mycompiler.io/new/nodejs",
    "java": "https://www.mycompiler.io/new/java",
    "cpp": "https://www.mycompiler.io/new/cpp",
    "c": "https://www.mycompiler.io/new/c",
    "go": "https://www.mycompiler.io/new/go",
    "rust": "https://www.mycompiler.io/new/rust",
    "ruby": "https://www.mycompiler.io/new/ruby",
    "php": "https://www.mycompiler.io/new/php",
    "typescript": "https://www.mycompiler.io/new/typescript",
}

PRESETS = {
    "hello": {
        "python": 'print("Hello from NLP2CMD!")\nprint("Browser automation is awesome.")',
        "javascript": 'console.log("Hello from NLP2CMD!");\nconsole.log("Browser automation is awesome.");',
        "cpp": '#include <iostream>\nint main() {\n    std::cout << "Hello from NLP2CMD!" << std::endl;\n    return 0;\n}',
    },
    "fibonacci": {
        "python": (
            'def fibonacci(n):\n'
            '    """Generate first n Fibonacci numbers."""\n'
            '    a, b = 0, 1\n'
            '    result = []\n'
            '    for _ in range(n):\n'
            '        result.append(a)\n'
            '        a, b = b, a + b\n'
            '    return result\n'
            '\n'
            'fib = fibonacci(15)\n'
            'print(f"First 15 Fibonacci numbers: {fib}")\n'
            'print(f"Sum: {sum(fib)}")\n'
        ),
        "javascript": (
            'function fibonacci(n) {\n'
            '    const result = [];\n'
            '    let a = 0, b = 1;\n'
            '    for (let i = 0; i < n; i++) {\n'
            '        result.push(a);\n'
            '        [a, b] = [b, a + b];\n'
            '    }\n'
            '    return result;\n'
            '}\n'
            '\n'
            'const fib = fibonacci(15);\n'
            'console.log(`First 15 Fibonacci numbers: ${fib}`);\n'
            'console.log(`Sum: ${fib.reduce((a, b) => a + b, 0)}`);\n'
        ),
    },
    "factorial": {
        "python": (
            'def factorial(n):\n'
            '    if n <= 1:\n'
            '        return 1\n'
            '    return n * factorial(n - 1)\n'
            '\n'
            'for i in range(1, 11):\n'
            '    print(f"{i}! = {factorial(i)}")\n'
        ),
        "javascript": (
            'function factorial(n) {\n'
            '    if (n <= 1) return 1;\n'
            '    return n * factorial(n - 1);\n'
            '}\n'
            '\n'
            'for (let i = 1; i <= 10; i++) {\n'
            '    console.log(`${i}! = ${factorial(i)}`);\n'
            '}\n'
        ),
    },
    "sorting": {
        "python": (
            'import random\n'
            '\n'
            'def quicksort(arr):\n'
            '    if len(arr) <= 1:\n'
            '        return arr\n'
            '    pivot = arr[len(arr) // 2]\n'
            '    left = [x for x in arr if x < pivot]\n'
            '    mid = [x for x in arr if x == pivot]\n'
            '    right = [x for x in arr if x > pivot]\n'
            '    return quicksort(left) + mid + quicksort(right)\n'
            '\n'
            'data = [random.randint(1, 100) for _ in range(20)]\n'
            'print(f"Original:  {data}")\n'
            'print(f"Sorted:    {quicksort(data)}")\n'
        ),
        "javascript": (
            'function quicksort(arr) {\n'
            '    if (arr.length <= 1) return arr;\n'
            '    const pivot = arr[Math.floor(arr.length / 2)];\n'
            '    const left = arr.filter(x => x < pivot);\n'
            '    const mid = arr.filter(x => x === pivot);\n'
            '    const right = arr.filter(x => x > pivot);\n'
            '    return [...quicksort(left), ...mid, ...quicksort(right)];\n'
            '}\n'
            '\n'
            'const data = Array.from({length: 20}, () => Math.floor(Math.random() * 100) + 1);\n'
            'console.log(`Original:  ${data}`);\n'
            'console.log(`Sorted:    ${quicksort(data)}`);\n'
        ),
    },
}


async def main():
    parser = argparse.ArgumentParser(description="Run code on myCompiler.io")
    parser.add_argument("--lang", default="python", choices=list(LANGUAGE_URLS.keys()))
    parser.add_argument("--code", default=None, help="Code to run (inline)")
    parser.add_argument("--preset", default="hello", choices=list(PRESETS.keys()))
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--screenshot-dir", default="screenshots")
    parser.add_argument("--wait-output", type=int, default=10,
                        help="Seconds to wait for output after clicking Run")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show page schema, editor detection, and decision logs")
    args = parser.parse_args()

    init_verbose(args.verbose)

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: pip install playwright && playwright install chromium")
        sys.exit(1)

    # Resolve code
    if args.code:
        code = args.code
    else:
        preset_codes = PRESETS.get(args.preset, PRESETS["hello"])
        code = preset_codes.get(args.lang, preset_codes.get("python", "print('hello')"))

    url = LANGUAGE_URLS.get(args.lang, LANGUAGE_URLS["python"])

    print(f"=== myCompiler.io: {args.lang} ===")
    print(f"URL: {url}")
    print(f"Code ({len(code)} chars):")
    for line in code.split("\n")[:5]:
        print(f"  {line}")
    if code.count("\n") > 5:
        print(f"  ... ({code.count(chr(10)) + 1} lines total)")
    print()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=args.headless)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        print("1. Opening myCompiler.io...")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        vlog(f"Page loaded: {page.url}")

        # Dismiss cookie/ad banners
        for sel in [
            "button:has-text('Accept')", "button:has-text('OK')",
            "button:has-text('I agree')", ".cookie-consent button",
            "button:has-text('Got it')", "button:has-text('Dismiss')",
        ]:
            try:
                btn = page.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    vlog(f"Dismissed dialog via: {sel}")
                    await page.wait_for_timeout(300)
            except Exception:
                continue

        await page.wait_for_timeout(1000)

        # Inspect page schema
        await dump_page_schema(page)
        await dump_selectors(page, {
            "codemirror": ".CodeMirror",
            "monaco": ".monaco-editor",
            "ace": ".ace_editor",
            "textarea": "textarea",
            "textarea#editor": "textarea#editor",
            "textarea.editor": "textarea.editor",
            "code_editor_div": "[id*='editor'], [class*='editor']",
            "run_btn": "button:has-text('Run')",
            "run_btn_id": "#run-button",
            "output": "#output, .output",
            "output_terminal": "#output-terminal",
        })

        # Inject code into the editor
        print("2. Injecting code...")
        import json as _json
        code_escaped = _json.dumps(code)

        injected = False
        editor_apis = [
            # CodeMirror 5 (legacy)
            ("CodeMirror5", f'(() => {{ const cm = document.querySelector(".CodeMirror"); if (cm && cm.CodeMirror) {{ cm.CodeMirror.setValue({code_escaped}); return true; }} return false; }})()'),
            # CodeMirror 6 — select all + synthetic paste (preserves newlines/indent)
            ("CodeMirror6", None),  # handled specially below
            # Monaco
            ("Monaco", f'(() => {{ const editors = window.monaco && window.monaco.editor.getEditors(); if (editors && editors.length) {{ editors[0].setValue({code_escaped}); return true; }} return false; }})()'),
            # Ace
            ("Ace", f'(() => {{ const ace = document.querySelector(".ace_editor"); if (ace && ace.env && ace.env.editor) {{ ace.env.editor.setValue({code_escaped}, -1); return true; }} return false; }})()'),
        ]
        for api_name, js_inject in editor_apis:
            try:
                if api_name == "CodeMirror6":
                    # CM6: click, select all, then paste via synthetic ClipboardEvent
                    cm_content = page.locator(".cm-content")
                    if await cm_content.count() == 0:
                        vlog("Editor API CodeMirror6: no .cm-content element")
                        continue
                    await cm_content.click()
                    await page.keyboard.press("Control+a")
                    await page.wait_for_timeout(100)
                    result = await page.evaluate('''(code) => {
                        const el = document.querySelector('.cm-content');
                        if (!el) return false;
                        el.focus();
                        const dt = new DataTransfer();
                        dt.setData('text/plain', code);
                        const ev = new ClipboardEvent('paste', {
                            clipboardData: dt, bubbles: true, cancelable: true,
                        });
                        el.dispatchEvent(ev);
                        return true;
                    }''', code)
                    if result:
                        print(f"   Code injected via CodeMirror6 (paste)")
                        vlog_decision("Injected code via CodeMirror6", "Select-all + synthetic paste into .cm-content")
                        injected = True
                        break
                    else:
                        vlog("Editor API CodeMirror6: paste dispatch returned false")
                    continue

                result = await page.evaluate(js_inject)
                if result:
                    print(f"   Code injected via {api_name} API")
                    vlog_decision(f"Injected code via {api_name}", f"{api_name} editor detected and setValue() succeeded")
                    injected = True
                    break
                else:
                    vlog(f"Editor API {api_name}: not found or returned false")
            except Exception as e:
                vlog(f"Editor API {api_name}: error — {e}")
                continue

        if not injected:
            # Fallback: try textarea — prefer editor-specific over generic
            vlog("All editor APIs failed, trying textarea fallback")
            ta_selectors = [
                ("textarea#editor", "textarea with id='editor'"),
                ("textarea.editor", "textarea with class='editor'"),
                ("[id*='editor'] textarea", "textarea inside editor container"),
                ("textarea:not(#stdin)", "first textarea that is NOT stdin"),
                ("textarea", "first textarea (generic)"),
            ]
            for ta_sel, ta_desc in ta_selectors:
                try:
                    ta = page.locator(ta_sel).first
                    if await ta.count() > 0:
                        await ta.click()
                        await ta.fill(code)
                        print(f"   Code injected via {ta_desc}")
                        vlog_decision(f"Injected code via {ta_desc}", f"Selector: {ta_sel}")
                        injected = True
                        break
                    else:
                        vlog(f"Textarea selector '{ta_sel}': no match")
                except Exception as e:
                    vlog(f"Textarea selector '{ta_sel}': error — {e}")
                    continue

        if not injected:
            print("   WARNING: Could not inject code into editor")
            vlog("FAILED: no injection method worked")

        await page.wait_for_timeout(1000)

        # Click Run button
        print("3. Clicking Run...")
        run_clicked = False
        run_selectors = [
            "button:has-text('Run')", "#run-btn", ".run-button",
            "button[title='Run']", "button:has-text('Execute')",
            "[data-action='run']", "button.btn-run",
        ]
        for run_sel in run_selectors:
            try:
                btn = page.locator(run_sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    run_clicked = True
                    print(f"   Clicked: {run_sel}")
                    vlog_decision(f"Run button: {run_sel}", "First visible matching selector", alternatives=run_selectors)
                    break
                else:
                    vlog(f"Run selector '{run_sel}': no visible match")
            except Exception:
                continue

        if not run_clicked:
            print("   WARNING: Could not find Run button")
            vlog("FAILED: no Run button selector matched")

        # Wait for output
        print(f"4. Waiting {args.wait_output}s for output...")
        await page.wait_for_timeout(args.wait_output * 1000)

        # Dump page schema again after execution to discover output containers
        await dump_page_schema(page)

        # Try to capture output — broad selector list for mycompiler.io and similar
        output_text = ""
        output_selectors = [
            "#output-terminal", "#output", ".output", "#output-text",
            "#execution-output", ".console-output", ".terminal-output",
            ".output-container", "[data-output]", ".result-container",
            "pre.output", "pre",
            "[id*='output']", "[class*='output']",
            "[id*='result']", "[class*='result']",
            "[id*='console']", "[class*='console']",
            "[id*='stdout']", "[class*='stdout']",
            "[id*='terminal']", "[class*='terminal']",
        ]
        for out_sel in output_selectors:
            try:
                out_el = page.locator(out_sel).first
                if await out_el.count() > 0:
                    output_text = await out_el.inner_text()
                    if output_text.strip():
                        print(f"   Output ({out_sel}):")
                        vlog_decision(f"Captured output via '{out_sel}'", f"{len(output_text)} chars", alternatives=output_selectors[:9])
                        for line in output_text.strip().split("\n")[:10]:
                            print(f"     {line}")
                        break
                    else:
                        vlog(f"Output selector '{out_sel}': matched but empty")
                else:
                    vlog(f"Output selector '{out_sel}': no match")
            except Exception as e:
                vlog(f"Output selector '{out_sel}': error — {e}")
                continue

        if not output_text.strip():
            print("   (no output captured — may need longer wait or different selector)")
            vlog("No output selector matched with non-empty content")

        # Screenshot
        print("5. Saving screenshot...")
        ss_dir = Path(args.screenshot_dir)
        ss_dir.mkdir(parents=True, exist_ok=True)
        path = ss_dir / f"mycompiler_{args.lang}_{args.preset}.png"
        await page.screenshot(path=str(path))
        print(f"   Screenshot: {path}")

        await browser.close()

    print()
    print(f"Done! Language: {args.lang}, Preset: {args.preset}")


if __name__ == "__main__":
    asyncio.run(main())
