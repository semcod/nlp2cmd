"""Page schema inspection helpers extracted from _verbose_helper."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from _verbose_helper import vlog

PAGE_SCHEMA_EVAL_JS = """() => {
    const result = {};
    const tags = ['canvas', 'iframe', 'button', 'input', 'textarea',
                   'select', 'a', 'form', 'video', 'img', 'svg', 'div'];
    tags.forEach(tag => {
        const count = document.querySelectorAll(tag).length;
        if (count > 0) result[tag] = count;
    });
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
    result._canvases = [];
    document.querySelectorAll('canvas').forEach(el => {
        result._canvases.push({
            id: el.id || '',
            width: el.width, height: el.height,
            class: el.className ? String(el.className).slice(0, 60) : '',
            visible: el.offsetWidth > 0 && el.offsetHeight > 0,
        });
    });
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
    result._iframes = [];
    document.querySelectorAll('iframe').forEach(el => {
        result._iframes.push({
            id: el.id || '',
            name: el.name || '',
            src: (el.src || '').slice(0, 100),
        });
    });
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
    if (result._output_containers.length > 20) {
        result._output_containers = result._output_containers.slice(0, 20);
        result._output_containers_truncated = true;
    }
    result._editors = {
        codemirror: document.querySelectorAll('.CodeMirror').length,
        monaco: document.querySelectorAll('.monaco-editor').length,
        ace: document.querySelectorAll('.ace_editor').length,
    };
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
}"""


def _log_list(vlog, title: str, items: list[dict[str, Any]], formatter, limit: int | None = None) -> None:
    if not items:
        return
    vlog(f"{title} ({len(items)}):")
    shown = items if limit is None else items[:limit]
    for item in shown:
        vlog(formatter(item), indent=1)
    if limit and len(items) > limit:
        vlog(f"  ... and {len(items) - limit} more", indent=1)


def log_schema_summary(schema: dict[str, Any], vlog) -> None:
    vlog("Elements found:")
    for tag in ["canvas", "iframe", "button", "input", "textarea", "select", "form", "svg"]:
        count = schema.get(tag, 0)
        if count:
            vlog(f"  <{tag}>: {count}", indent=1)

    _log_list(
        vlog,
        "Canvas elements",
        schema.get("_canvases", []),
        lambda c: (
            f"id={c['id']!r} {c['width']}×{c['height']} class={c['class']!r} "
            f"[{'visible' if c.get('visible') else 'HIDDEN'}]"
        ),
    )
    _log_list(
        vlog,
        "Buttons/actions",
        schema.get("_buttons", []),
        lambda b: f"[{b['tag']}] text={b['text']!r} id={b['id']!r} title={b['title']!r}",
        limit=15,
    )

    pickers = schema.get("_color_pickers", [])
    if pickers:
        _log_list(
            vlog,
            "Color pickers",
            pickers,
            lambda p: f"<{p['tag']}> type={p['type']!r} value={p['value']!r} id={p['id']!r}",
        )
    else:
        vlog("Color pickers: NONE found")

    editors = {k: v for k, v in schema.get("_editors", {}).items() if v > 0}
    if editors:
        vlog(f"Code editors: {editors}")

    _log_list(
        vlog,
        "Toolbar items",
        schema.get("_toolbars", []),
        lambda t: f"tool={t['tool']!r} title={t['title']!r} text={t['text']!r}",
        limit=10,
    )
    _log_list(
        vlog,
        "Inputs",
        schema.get("_inputs", []),
        lambda inp: (
            f"type={inp['type']!r} id={inp['id']!r} name={inp['name']!r} "
            f"placeholder={inp['placeholder']!r}"
        ),
        limit=10,
    )
    _log_list(
        vlog,
        "Iframes",
        schema.get("_iframes", []),
        lambda f: f"id={f['id']!r} name={f['name']!r} src={f['src']!r}",
    )

    outputs = schema.get("_output_containers", [])
    if outputs:
        suffix = "+" if schema.get("_output_containers_truncated") else ""
        vlog(f"Output containers ({len(outputs)}{suffix}):")
        for output in outputs:
            vis = "visible" if output.get("visible") else "hidden"
            preview = output["preview"][:60] if output.get("preview") else ""
            vlog(
                f"  <{output['tag']}> id={output['id']!r} class={output['class']!r} "
                f"[{vis}, {output['textLen']} chars] {preview!r}",
                indent=1,
            )
    else:
        vlog("Output containers: NONE found (<pre>, <code>, [id*=output], etc.)")
