import re

# Update `src/nlp2cmd/cli/commands/generate.py`
with open("src/nlp2cmd/cli/commands/generate.py", "r") as f:
    text = f.read()

missing_ellipse_str = """
                    elif action == 'draw_line':"""

new_ellipse_str = """
                    elif action == 'draw_ellipse':
                        rx = params.get('rx', 50)
                        ry = params.get('ry', 50)
                        offset = params.get('offset', [0, 0])
                        x = canvas_center['x'] + offset[0]
                        y = canvas_center['y'] + offset[1]
                        console.print(f"    Drawing ellipse at ({x}, {y}) rx={rx}, ry={ry}")

                        # We don't have _js_draw_ellipse but we can reuse _js_draw_filled_ellipse with transparent fill or just use the mouse
                        page.evaluate(_js_select_tool('ellipse'))
                        page.wait_for_timeout(200)
                        page.mouse.move(x - rx, y - ry)
                        page.mouse.down()
                        page.wait_for_timeout(50)
                        page.mouse.move(x + rx, y + ry, steps=5)
                        page.mouse.up()
                        page.wait_for_timeout(300)

                    elif action == 'draw_line':"""

if "elif action == 'draw_ellipse':" not in text:
    text = text.replace(missing_ellipse_str, new_ellipse_str)
    with open("src/nlp2cmd/cli/commands/generate.py", "w") as f:
        f.write(text)

