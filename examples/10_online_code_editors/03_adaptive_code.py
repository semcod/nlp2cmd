#!/usr/bin/env python3
"""
03_adaptive_code — LLM-guided code generation with adaptive routing.

Demonstrates:
1. Takes a natural language code request (PL or EN)
2. Routes to LLM for code generation (remote → local fallback)
3. Learns from failures (credit exhaustion, timeouts) and adapts
4. Writes the generated code on myCompiler.io and runs it
5. Captures output and verifies correctness

Usage:
    python3 03_adaptive_code.py --query "napisz program w Pythonie który liczy silnię"
    python3 03_adaptive_code.py --query "create a JS function that reverses a string"
    python3 03_adaptive_code.py --query "napisz quicksort w Pythonie" --lang python
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from _verbose_helper import init_verbose, vlog, dump_page_schema, dump_selectors, vlog_decision, ensure_playwright_browsers_async

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

LANGUAGE_URLS = {
    "python": "https://www.mycompiler.io/new/python",
    "javascript": "https://www.mycompiler.io/new/nodejs",
    "cpp": "https://www.mycompiler.io/new/cpp",
    "go": "https://www.mycompiler.io/new/go",
    "rust": "https://www.mycompiler.io/new/rust",
}

# Language detection from query
LANG_KEYWORDS = {
    "python": ["python", "pythonie", "py", "pythona"],
    "javascript": ["javascript", "js", "node", "nodejs"],
    "cpp": ["c++", "cpp", "cplusplus"],
    "go": ["golang", "go "],
    "rust": ["rust", "ruście"],
}

# Fallback code templates (when LLM is unavailable)
FALLBACK_TEMPLATES = {
    "factorial": {
        "python": 'def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n\nfor i in range(1, 11):\n    print(f"{i}! = {factorial(i)}")\n',
        "javascript": 'function factorial(n) {\n    if (n <= 1) return 1;\n    return n * factorial(n - 1);\n}\nfor (let i = 1; i <= 10; i++) console.log(`${i}! = ${factorial(i)}`);\n',
    },
    "fibonacci": {
        "python": 'def fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        yield a\n        a, b = b, a + b\n\nprint(list(fib(15)))\n',
        "javascript": 'function* fib(n) {\n    let a = 0, b = 1;\n    for (let i = 0; i < n; i++) {\n        yield a;\n        [a, b] = [b, a + b];\n    }\n}\nconsole.log([...fib(15)]);\n',
    },
    "sort": {
        "python": 'import random\ndef quicksort(a):\n    if len(a) <= 1: return a\n    p = a[len(a)//2]\n    return quicksort([x for x in a if x<p]) + [x for x in a if x==p] + quicksort([x for x in a if x>p])\n\ndata = [random.randint(1,100) for _ in range(20)]\nprint("Input: ", data)\nprint("Sorted:", quicksort(data))\n',
        "javascript": 'function quicksort(a) {\n    if (a.length <= 1) return a;\n    const p = a[Math.floor(a.length/2)];\n    return [...quicksort(a.filter(x=>x<p)), ...a.filter(x=>x===p), ...quicksort(a.filter(x=>x>p))];\n}\nconst data = Array.from({length:20}, ()=>Math.floor(Math.random()*100)+1);\nconsole.log("Input: ", data);\nconsole.log("Sorted:", quicksort(data));\n',
    },
    "reverse": {
        "python": 'def reverse_string(s):\n    return s[::-1]\n\ntests = ["hello", "NLP2CMD", "racecar", "Python"]\nfor t in tests:\n    print(f"{t} -> {reverse_string(t)}")\n',
        "javascript": 'function reverseString(s) {\n    return s.split("").reverse().join("");\n}\n["hello", "NLP2CMD", "racecar", "JavaScript"].forEach(t => console.log(`${t} -> ${reverseString(t)}`));\n',
    },
}


def detect_language(query: str) -> str:
    """Detect programming language from query."""
    q = query.lower()
    for lang, keywords in LANG_KEYWORDS.items():
        for kw in keywords:
            if kw in q:
                return lang
    return "python"


def detect_task(query: str) -> str:
    """Detect coding task from query keywords."""
    q = query.lower()
    task_keywords = {
        "factorial": ["silni", "factorial", "silnię"],
        "fibonacci": ["fibonacci", "fib"],
        "sort": ["sort", "sortow", "quicksort", "sortuj"],
        "reverse": ["revers", "odwróć", "odwroc", "reverse"],
    }
    for task, kws in task_keywords.items():
        for kw in kws:
            if kw in q:
                return task
    return "factorial"


async def generate_code_with_llm(query: str, lang: str) -> str | None:
    """Generate code using LLM Router with adaptive learning."""
    try:
        from nlp2cmd.llm.router import LLMRouter

        router = LLMRouter(adaptive_learning=True)

        system_prompt = (
            f"You are a {lang} code generator. Given a description, "
            f"write a complete, runnable {lang} program.\n"
            f"The program should include example output via print/console.log.\n"
            f"Reply with ONLY the code, no markdown fences, no explanation."
        )

        resp = await router.completion(
            query,
            task="coding",
            system=system_prompt,
            max_tokens=1000,
            temperature=0.1,
        )

        if resp.success and resp.content:
            code = resp.content.strip()
            # Strip markdown fences if present
            if code.startswith("```"):
                lines = code.split("\n")
                lines = lines[1:]  # Remove opening fence
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                code = "\n".join(lines)

            print(f"  LLM model: {resp.model}")
            print(f"  Latency: {resp.latency_ms:.0f}ms")
            if resp.fallback_used:
                print(f"  (fallback used — remote model unavailable)")
            return code
        else:
            print(f"  LLM failed: {resp.error}")
            return None

    except ImportError:
        print("  LLM Router not available")
        return None
    except Exception as e:
        print(f"  LLM error: {e}")
        return None


async def main():
    parser = argparse.ArgumentParser(description="Adaptive LLM code generation + online execution")
    parser.add_argument("--query", required=True, help="Natural language code request")
    parser.add_argument("--lang", default=None, help="Language (auto-detected if not set)")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--screenshot-dir", default="screenshots")
    parser.add_argument("--wait-output", type=int, default=10)
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

    lang = args.lang or detect_language(args.query)
    task = detect_task(args.query)

    print(f"=== Adaptive Code Generation ===")
    print(f"Query: {args.query}")
    print(f"Language: {lang}")
    print(f"Detected task: {task}")
    print()
    vlog_decision(f"Language: {lang}", "Auto-detected from query keywords", alternatives=list(LANG_KEYWORDS.keys()))
    vlog_decision(f"Task: {task}", "Matched from query keywords")

    # Step 1: Try LLM code generation
    print("1. Generating code with LLM Router...")
    t0 = time.time()
    code = await generate_code_with_llm(args.query, lang)
    gen_time = (time.time() - t0) * 1000

    if code:
        print(f"   LLM generated {len(code)} chars ({gen_time:.0f}ms)")
    else:
        print(f"   Using template fallback ({gen_time:.0f}ms)")
        templates = FALLBACK_TEMPLATES.get(task, FALLBACK_TEMPLATES["factorial"])
        code = templates.get(lang, templates.get("python", "print('hello')"))

    print(f"   Code preview:")
    for line in code.split("\n")[:8]:
        print(f"     {line}")
    if code.count("\n") > 8:
        print(f"     ... ({code.count(chr(10)) + 1} lines total)")
    print()

    # Step 2: Open myCompiler and run
    url = LANGUAGE_URLS.get(lang, LANGUAGE_URLS["python"])

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=args.headless)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        print(f"2. Opening myCompiler.io ({lang})...")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        vlog(f"Page loaded: {page.url}")

        # Dismiss popups
        for sel in [
            "button:has-text('Accept')", "button:has-text('OK')",
            "button:has-text('I agree')", "button:has-text('Got it')",
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
            "run_btn": "button:has-text('Run')",
            "output": "#output, .output",
        })

        # Inject code
        print("3. Injecting code...")
        code_escaped = json.dumps(code)
        injected = False

        editor_apis = [
            # CodeMirror 5 (legacy)
            ("CodeMirror5", f'(() => {{ const cm = document.querySelector(".CodeMirror"); if (cm && cm.CodeMirror) {{ cm.CodeMirror.setValue({code_escaped}); return true; }} return false; }})()'),
            # CodeMirror 6 — select all + synthetic paste (preserves newlines/indent)
            ("CodeMirror6", None),  # handled specially below
            # Monaco
            ("Monaco", f'(() => {{ const e = window.monaco && window.monaco.editor.getEditors(); if (e && e.length) {{ e[0].setValue({code_escaped}); return true; }} return false; }})()'),
            # Ace
            ("Ace", f'(() => {{ const a = document.querySelector(".ace_editor"); if (a && a.env && a.env.editor) {{ a.env.editor.setValue({code_escaped}, -1); return true; }} return false; }})()'),
        ]
        for api_name, js_api in editor_apis:
            try:
                if api_name == "CodeMirror6":
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
                        injected = True
                        print("   Injected via CodeMirror6 (paste)")
                        vlog_decision("Injected code via CodeMirror6", "Select-all + synthetic paste into .cm-content")
                        break
                    else:
                        vlog("Editor API CodeMirror6: paste dispatch returned false")
                    continue

                if await page.evaluate(js_api):
                    injected = True
                    print(f"   Injected via {api_name} API")
                    vlog_decision(f"Injected code via {api_name}", f"{api_name} detected and setValue() succeeded")
                    break
                else:
                    vlog(f"Editor API {api_name}: not found or returned false")
            except Exception as e:
                vlog(f"Editor API {api_name}: error — {e}")
                continue

        if not injected:
            vlog("All editor APIs failed, trying textarea fallback")
            try:
                ta = page.locator("textarea:not(#stdin)").first
                if await ta.count() == 0:
                    ta = page.locator("textarea").first
                if await ta.count() > 0:
                    await ta.click()
                    await ta.fill(code)
                    injected = True
                    print("   Injected via textarea")
                    vlog_decision("Injected via textarea", "Fallback after editor APIs failed")
            except Exception as e:
                print("   WARNING: Could not inject code")
                vlog(f"textarea fallback error: {e}")

        await page.wait_for_timeout(1000)

        # Click Run
        print("4. Running code...")
        for run_sel in [
            "button:has-text('Run')", "#run-btn", ".run-button",
            "button[title='Run']", "[data-action='run']",
        ]:
            try:
                btn = page.locator(run_sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    print(f"   Run button clicked")
                    break
            except Exception:
                continue

        print(f"   Waiting {args.wait_output}s for output...")
        await page.wait_for_timeout(args.wait_output * 1000)

        # Dump page schema after execution to discover output containers
        await dump_page_schema(page)

        # Capture output — broad selector list
        output = ""
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
                el = page.locator(out_sel).first
                if await el.count() > 0:
                    output = await el.inner_text()
                    if output.strip():
                        vlog_decision(f"Captured output via '{out_sel}'", f"{len(output)} chars")
                        break
                    else:
                        vlog(f"Output selector '{out_sel}': matched but empty")
                else:
                    vlog(f"Output selector '{out_sel}': no match")
            except Exception as e:
                vlog(f"Output selector '{out_sel}': error — {e}")
                continue

        if output.strip():
            print(f"5. Output captured:")
            for line in output.strip().split("\n")[:10]:
                print(f"     {line}")
        else:
            print("5. No output captured (may need longer wait)")
            vlog("No output selector matched with non-empty content")

        # Screenshot
        print("6. Saving screenshot...")
        ss_dir = Path(args.screenshot_dir)
        ss_dir.mkdir(parents=True, exist_ok=True)
        path = ss_dir / f"adaptive_code_{lang}_{task}.png"
        await page.screenshot(path=str(path))
        print(f"   Screenshot: {path}")

        # Show adaptive learning report
        try:
            from nlp2cmd.llm.router import LLMRouter
            router = LLMRouter(adaptive_learning=True)
            stats = router.get_stats()
            al = stats.get("adaptive_learning", {})
            if al:
                print(f"\n7. Adaptive Learning Report:")
                models = al.get("models", {})
                for key, m in models.items():
                    if m["total_calls"] > 0:
                        print(f"   {key}: success={m['success_rate']:.0%}, "
                              f"avg={m['avg_latency_ms']:.0f}ms, "
                              f"health={m['health_score']:.2f}, "
                              f"pref={m['learned_preference']:.2f}")
                pairs = al.get("fallback_pairs", {})
                if pairs:
                    print(f"   Learned fallbacks: {pairs}")
                errs = al.get("error_summary", {})
                if errs:
                    print(f"   Errors: {errs}")
        except Exception:
            pass

        await browser.close()

    print()
    print(f"Done! Language: {lang}, Task: {task}")


if __name__ == "__main__":
    asyncio.run(main())
