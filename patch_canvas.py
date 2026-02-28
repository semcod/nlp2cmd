with open("src/nlp2cmd/pipeline_runner.py", "r") as f:
    text = f.read()

# Add missing drawing action handlers to `_execute_plan_step` in `pipeline_runner.py`
# Specifically: wait_for_canvas, get_canvas_center, select_tool, set_color, 
# draw_circle, draw_ellipse, draw_filled_ellipse, draw_rectangle, draw_line, click_canvas, type_text

actions_to_insert = """
        elif action == "wait_for_canvas":
            page.wait_for_selector("canvas", state="visible", timeout=15000)
            
        elif action == "get_canvas_center":
            canvas = page.query_selector("canvas")
            if canvas:
                box = canvas.bounding_box()
                if box:
                    # Storing implicitly in playwright page context via evaluate or just log
                    _debug(f"Canvas: {box}")
                    # We usually don't need to return it unless another step needs it dynamically,
                    # but our drawing steps just pass fixed coords or calculate inside.
                    # Since our instructions say offset from center, we should compute center
                    # and store it in variables if we want, OR let the drawing steps do it.
                    variables["canvas_cx"] = str(box["x"] + box["width"] / 2)
                    variables["canvas_cy"] = str(box["y"] + box["height"] / 2)

        elif action == "select_tool":
            tool = params.get("tool", "")
            # map tool names to jspaint classes
            tool_map = {
                "ellipse": "ellipse",
                "rectangle": "rectangle",
                "line": "line",
                "brush": "brush",
                "pencil": "pencil",
                "fill": "fill",
                "text": "text",
            }
            mapped = tool_map.get(tool, tool)
            # jspaint uses elements with class "tool" and title containing the tool name
            try:
                page.evaluate(f'''() => {{
                    const tools = document.querySelectorAll('.tool');
                    for (const t of tools) {{
                        if (t.title && t.title.toLowerCase().includes('{mapped}')) {{
                            t.click();
                            return;
                        }}
                    }}
                }}''')
                page.wait_for_timeout(500)
            except Exception as e:
                _debug(f"Tool selection error: {e}")

        elif action == "set_color":
            color = params.get("color", "#000000")
            try:
                # jspaint has an input[type=color] we might trigger, or use evaluate
                page.evaluate(f'''() => {{
                    // Set both colors for simplicity
                    if (window.colors) {{
                        window.colors.foreground = '{color}';
                        window.colors.background = '{color}';
                    }}
                }}''')
                page.wait_for_timeout(200)
            except Exception as e:
                _debug(f"Color set error: {e}")

        elif action == "draw_circle":
            radius = float(params.get("radius", 10))
            offset = params.get("offset", [0, 0])
            try:
                page.evaluate(f'''() => {{
                    const canvas = document.querySelector('canvas');
                    const ctx = canvas.getContext('2d');
                    if (!ctx) return;
                    const rect = canvas.getBoundingClientRect();
                    const cx = rect.width / 2 + {offset[0]};
                    const cy = rect.height / 2 + {offset[1]};
                    ctx.beginPath();
                    ctx.arc(cx, cy, {radius}, 0, 2 * Math.PI);
                    if (window.colors && window.colors.foreground) {{
                        ctx.fillStyle = window.colors.foreground;
                    }}
                    ctx.fill();
                }}''')
                page.wait_for_timeout(200)
            except Exception as e:
                _debug(f"Draw circle error: {e}")
                
        elif action == "draw_filled_ellipse":
            rx = float(params.get("rx", 10))
            ry = float(params.get("ry", 10))
            try:
                page.evaluate(f'''() => {{
                    const canvas = document.querySelector('canvas');
                    const ctx = canvas.getContext('2d');
                    if (!ctx) return;
                    const rect = canvas.getBoundingClientRect();
                    const cx = rect.width / 2;
                    const cy = rect.height / 2;
                    ctx.beginPath();
                    ctx.ellipse(cx, cy, {rx}, {ry}, 0, 0, 2 * Math.PI);
                    if (window.colors && window.colors.foreground) {{
                        ctx.fillStyle = window.colors.foreground;
                    }}
                    ctx.fill();
                }}''')
                page.wait_for_timeout(200)
            except Exception as e:
                _debug(f"Draw filled ellipse error: {e}")

        elif action == "draw_rectangle":
            w = float(params.get("width", 50))
            h = float(params.get("height", 50))
            offset = params.get("offset", [0, 0])
            try:
                page.evaluate(f'''() => {{
                    const canvas = document.querySelector('canvas');
                    const ctx = canvas.getContext('2d');
                    if (!ctx) return;
                    const rect = canvas.getBoundingClientRect();
                    const cx = rect.width / 2 + {offset[0]};
                    const cy = rect.height / 2 + {offset[1]};
                    if (window.colors && window.colors.foreground) {{
                        ctx.fillStyle = window.colors.foreground;
                        ctx.strokeStyle = window.colors.foreground;
                    }}
                    ctx.fillRect(cx - {w}/2, cy - {h}/2, {w}, {h});
                }}''')
                page.wait_for_timeout(200)
            except Exception as e:
                _debug(f"Draw rectangle error: {e}")

        elif action == "draw_line":
            fo = params.get("from_offset", [0, 0])
            to = params.get("to_offset", [0, 0])
            try:
                page.evaluate(f'''() => {{
                    const canvas = document.querySelector('canvas');
                    const ctx = canvas.getContext('2d');
                    if (!ctx) return;
                    const rect = canvas.getBoundingClientRect();
                    const cx = rect.width / 2;
                    const cy = rect.height / 2;
                    ctx.beginPath();
                    ctx.moveTo(cx + {fo[0]}, cy + {fo[1]});
                    ctx.lineTo(cx + {to[0]}, cy + {to[1]});
                    if (window.colors && window.colors.foreground) {{
                        ctx.strokeStyle = window.colors.foreground;
                    }}
                    ctx.stroke();
                }}''')
                page.wait_for_timeout(200)
            except Exception as e:
                _debug(f"Draw line error: {e}")

        elif action == "draw_ellipse":
            rx = float(params.get("rx", 10))
            ry = float(params.get("ry", 10))
            offset = params.get("offset", [0, 0])
            try:
                page.evaluate(f'''() => {{
                    const canvas = document.querySelector('canvas');
                    const ctx = canvas.getContext('2d');
                    if (!ctx) return;
                    const rect = canvas.getBoundingClientRect();
                    const cx = rect.width / 2 + {offset[0]};
                    const cy = rect.height / 2 + {offset[1]};
                    ctx.beginPath();
                    ctx.ellipse(cx, cy, {rx}, {ry}, 0, 0, 2 * Math.PI);
                    if (window.colors && window.colors.foreground) {{
                        ctx.strokeStyle = window.colors.foreground;
                    }}
                    ctx.stroke();
                }}''')
                page.wait_for_timeout(200)
            except Exception as e:
                _debug(f"Draw ellipse error: {e}")
                
        elif action == "fill_at":
            offset = params.get("offset", [0, 0])
            try:
                page.evaluate(f'''() => {{
                    // JSPaint doesn't expose fill easily via context, best we can do is dispatch click
                    const canvas = document.querySelector('canvas');
                    const rect = canvas.getBoundingClientRect();
                    const cx = rect.width / 2 + {offset[0]};
                    const cy = rect.height / 2 + {offset[1]};
                    const ev = new MouseEvent('pointerdown', {{
                        clientX: rect.left + cx,
                        clientY: rect.top + cy,
                        bubbles: true
                    }});
                    canvas.dispatchEvent(ev);
                    setTimeout(() => {{
                        const up = new MouseEvent('pointerup', {{
                            clientX: rect.left + cx,
                            clientY: rect.top + cy,
                            bubbles: true
                        }});
                        canvas.dispatchEvent(up);
                    }}, 50);
                }}''')
                page.wait_for_timeout(200)
            except Exception as e:
                _debug(f"Fill at error: {e}")

        elif action == "click_canvas":
            offset = params.get("offset", [0, 0])
            try:
                page.evaluate(f'''() => {{
                    const canvas = document.querySelector('canvas');
                    const rect = canvas.getBoundingClientRect();
                    const cx = rect.width / 2 + {offset[0]};
                    const cy = rect.height / 2 + {offset[1]};
                    const ev = new MouseEvent('pointerdown', {{
                        clientX: rect.left + cx,
                        clientY: rect.top + cy,
                        bubbles: true
                    }});
                    canvas.dispatchEvent(ev);
                    setTimeout(() => {{
                        const up = new MouseEvent('pointerup', {{
                            clientX: rect.left + cx,
                            clientY: rect.top + cy,
                            bubbles: true
                        }});
                        canvas.dispatchEvent(up);
                    }}, 50);
                }}''')
                page.wait_for_timeout(200)
            except Exception as e:
                _debug(f"Click canvas error: {e}")
"""

text = text.replace("        elif action == \"wait\":", actions_to_insert + "\n        elif action == \"wait\":")

with open("src/nlp2cmd/pipeline_runner.py", "w") as f:
    f.write(text)
