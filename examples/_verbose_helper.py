"""
Shared verbose/debug helper for NLP2CMD examples.

When --verbose is passed, enables:
  1. NLP2CMD_DEBUG=1 — turns on internal module debug logs (router, adapters, etc.)
  2. Page schema inspection — dumps DOM structure, interactive elements, canvases
  3. Decision logging — shows selector matching, color picker detection, tool selection

Usage in example scripts:
    from _verbose_helper import init_verbose, vlog, dump_page_schema, dump_selectors

    args = parser.parse_args()
    init_verbose(args.verbose)
    ...
    await dump_page_schema(page)
    await dump_selectors(page, {"canvas": "canvas", "run": "#run-btn"})
"""

from __future__ import annotations

import os
import sys
from typing import Any

_VERBOSE = False


def init_verbose(enabled: bool) -> None:
    """Initialize verbose mode. Call early, before importing nlp2cmd modules."""
    global _VERBOSE
    _VERBOSE = enabled
    if enabled:
        os.environ["NLP2CMD_DEBUG"] = "1"
        os.environ["NLP2CMD_ROUTER_VERBOSE"] = "1"
        vlog("Verbose mode ON — NLP2CMD_DEBUG=1, NLP2CMD_ROUTER_VERBOSE=1")


def vlog(msg: str, indent: int = 0) -> None:
    """Print a verbose log message (only when --verbose is active)."""
    if not _VERBOSE:
        return
    prefix = "  " * indent
    print(f"[VERBOSE] {prefix}{msg}", flush=True)


async def dump_page_schema(page, max_depth: int = 3) -> dict[str, Any]:
    """
    Inspect the page DOM and print a schema summary.
    Returns a dict with page structure info.
    """
    if not _VERBOSE:
        return {}

    vlog("─── Page Schema Inspection ───")

    info: dict[str, Any] = {}

    # Basic page info
    title = await page.title()
    url = page.url
    vlog(f"URL:   {url}")
    vlog(f"Title: {title}")
    info["url"] = url
    info["title"] = title

    # Viewport
    vp = page.viewport_size
    if vp:
        vlog(f"Viewport: {vp['width']}×{vp['height']}")
        info["viewport"] = vp

    # Count key element types
    schema = await page.evaluate('''() => {
        const result = {};

        // Count elements by tag
        const tags = ['canvas', 'iframe', 'button', 'input', 'textarea',
                       'select', 'a', 'form', 'video', 'img', 'svg', 'div'];
        tags.forEach(tag => {
            const count = document.querySelectorAll(tag).length;
            if (count > 0) result[tag] = count;
        });

        // Interactive elements with details
        result._buttons = [];
        document.querySelectorAll('button, [role="button"], input[type="button"], input[type="submit"]').forEach(el => {
            const text = (el.textContent || el.value || '').trim().slice(0, 50);
            const id = el.id || '';
            const cls = el.className ? String(el.className).slice(0, 60) : '';
            const title = el.title || '';
            if (text || id) {
                result._buttons.push({text, id, class: cls, title, tag: el.tagName.toLowerCase()});
            }
        });

        // Canvas elements
        result._canvases = [];
        document.querySelectorAll('canvas').forEach(el => {
            result._canvases.push({
                id: el.id || '',
                width: el.width, height: el.height,
                class: el.className ? String(el.className).slice(0, 60) : '',
                visible: el.offsetWidth > 0 && el.offsetHeight > 0,
            });
        });

        // Inputs
        result._inputs = [];
        document.querySelectorAll('input, textarea, select').forEach(el => {
            result._inputs.push({
                type: el.type || el.tagName.toLowerCase(),
                id: el.id || '',
                name: el.name || '',
                placeholder: (el.placeholder || '').slice(0, 40),
                class: el.className ? String(el.className).slice(0, 40) : '',
            });
        });

        // Color pickers specifically
        result._color_pickers = [];
        document.querySelectorAll('input[type="color"], [data-color], .color-picker').forEach(el => {
            result._color_pickers.push({
                tag: el.tagName.toLowerCase(),
                type: el.type || '',
                id: el.id || '',
                value: el.value || '',
                class: el.className ? String(el.className).slice(0, 60) : '',
            });
        });

        // Iframes
        result._iframes = [];
        document.querySelectorAll('iframe').forEach(el => {
            result._iframes.push({
                id: el.id || '',
                name: el.name || '',
                src: (el.src || '').slice(0, 100),
            });
        });

        // Output / result containers (<pre>, <code>, divs with output/result/console/terminal/stdout)
        result._output_containers = [];
        const outSel = 'pre, code, [id*="output"], [id*="result"], [id*="console"], [id*="terminal"], [id*="stdout"], [class*="output"], [class*="result"], [class*="console"], [class*="terminal"], [class*="stdout"]';
        document.querySelectorAll(outSel).forEach(el => {
            const text = (el.textContent || '').trim();
            if (text.length > 0 || el.id || el.className) {
                result._output_containers.push({
                    tag: el.tagName.toLowerCase(),
                    id: el.id || '',
                    class: el.className ? String(el.className).slice(0, 80) : '',
                    textLen: text.length,
                    preview: text.slice(0, 80),
                    visible: el.offsetWidth > 0 && el.offsetHeight > 0,
                });
            }
        });
        // Cap to avoid flooding
        if (result._output_containers.length > 20) {
            result._output_containers = result._output_containers.slice(0, 20);
            result._output_containers_truncated = true;
        }

        // CodeMirror / Monaco / Ace editors
        result._editors = {
            codemirror: document.querySelectorAll('.CodeMirror').length,
            monaco: document.querySelectorAll('.monaco-editor').length,
            ace: document.querySelectorAll('.ace_editor').length,
        };

        // Toolbar elements
        result._toolbars = [];
        document.querySelectorAll('[class*="tool"], [data-tool], [role="toolbar"]').forEach(el => {
            const tool = el.getAttribute('data-tool') || '';
            const title = el.title || '';
            const text = (el.textContent || '').trim().slice(0, 30);
            if (tool || title) {
                result._toolbars.push({tool, title, text, tag: el.tagName.toLowerCase()});
            }
        });

        return result;
    }''')

    info["schema"] = schema

    # Print summary
    vlog("Elements found:")
    for tag in ['canvas', 'iframe', 'button', 'input', 'textarea', 'select', 'form', 'svg']:
        count = schema.get(tag, 0)
        if count:
            vlog(f"  <{tag}>: {count}", indent=1)

    # Canvases
    canvases = schema.get("_canvases", [])
    if canvases:
        vlog(f"Canvas elements ({len(canvases)}):")
        for c in canvases:
            vis = "visible" if c.get("visible") else "HIDDEN"
            vlog(f"  id={c['id']!r} {c['width']}×{c['height']} class={c['class']!r} [{vis}]", indent=1)

    # Buttons
    buttons = schema.get("_buttons", [])
    if buttons:
        vlog(f"Buttons/actions ({len(buttons)}):")
        for b in buttons[:15]:
            vlog(f"  [{b['tag']}] text={b['text']!r} id={b['id']!r} title={b['title']!r}", indent=1)
        if len(buttons) > 15:
            vlog(f"  ... and {len(buttons) - 15} more", indent=1)

    # Color pickers
    pickers = schema.get("_color_pickers", [])
    if pickers:
        vlog(f"Color pickers ({len(pickers)}):")
        for p in pickers:
            vlog(f"  <{p['tag']}> type={p['type']!r} value={p['value']!r} id={p['id']!r}", indent=1)
    else:
        vlog("Color pickers: NONE found")

    # Editors
    editors = schema.get("_editors", {})
    found_editors = {k: v for k, v in editors.items() if v > 0}
    if found_editors:
        vlog(f"Code editors: {found_editors}")

    # Toolbars
    toolbars = schema.get("_toolbars", [])
    if toolbars:
        vlog(f"Toolbar items ({len(toolbars)}):")
        for t in toolbars[:10]:
            vlog(f"  tool={t['tool']!r} title={t['title']!r} text={t['text']!r}", indent=1)
        if len(toolbars) > 10:
            vlog(f"  ... and {len(toolbars) - 10} more", indent=1)

    # Inputs
    inputs = schema.get("_inputs", [])
    if inputs:
        vlog(f"Inputs ({len(inputs)}):")
        for inp in inputs[:10]:
            vlog(f"  type={inp['type']!r} id={inp['id']!r} name={inp['name']!r} placeholder={inp['placeholder']!r}", indent=1)

    # Iframes
    iframes = schema.get("_iframes", [])
    if iframes:
        vlog(f"Iframes ({len(iframes)}):")
        for f in iframes:
            vlog(f"  id={f['id']!r} name={f['name']!r} src={f['src']!r}", indent=1)

    # Output containers
    outputs = schema.get("_output_containers", [])
    if outputs:
        vlog(f"Output containers ({len(outputs)}{'+' if schema.get('_output_containers_truncated') else ''}):'")
        for o in outputs:
            vis = "visible" if o.get("visible") else "hidden"
            preview = o["preview"][:60] if o.get("preview") else ""
            vlog(f"  <{o['tag']}> id={o['id']!r} class={o['class']!r} "
                 f"[{vis}, {o['textLen']} chars] {preview!r}", indent=1)
    else:
        vlog("Output containers: NONE found (<pre>, <code>, [id*=output], etc.)")

    vlog("─── End Schema ───")
    return info


async def dump_selectors(page, selectors: dict[str, str]) -> dict[str, int]:
    """
    Try each selector and report which ones matched elements.
    Returns {name: count} for found elements.
    """
    if not _VERBOSE:
        return {}

    vlog("─── Selector Matching ───")
    results = {}
    for name, selector in selectors.items():
        try:
            count = await page.locator(selector).count()
            status = f"✓ {count} match(es)" if count > 0 else "✗ no match"
            vlog(f"  {name:20s} → {selector:50s} {status}")
            results[name] = count
        except Exception as e:
            vlog(f"  {name:20s} → {selector:50s} ERROR: {e}")
            results[name] = 0
    vlog("─── End Selectors ───")
    return results


def vlog_decision(action: str, reason: str, alternatives: list[str] | None = None) -> None:
    """Log a decision made during automation."""
    if not _VERBOSE:
        return
    vlog(f"DECISION: {action}")
    vlog(f"  reason: {reason}", indent=1)
    if alternatives:
        vlog(f"  alternatives considered: {alternatives}", indent=1)
