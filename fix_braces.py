import re

file_path = "/home/tom/github/wronai/nlp2cmd/src/nlp2cmd/pipeline_runner.py"
with open(file_path, "r") as f:
    content = f.read()

# Fix braces in pickCanvas inside f-strings
old_pick_canvas = """const pickCanvas = () => {
                        const all = Array.from(document.querySelectorAll('canvas'));
                        if (!all.length) return null;
                        const main = document.querySelector('.main-canvas');
                        if (main && main instanceof HTMLCanvasElement) return main;
                        let best = null;
                        let bestArea = -1;
                        for (const c of all) {
                            if (!(c instanceof HTMLCanvasElement)) continue;
                            const r = c.getBoundingClientRect();
                            if (!r || r.width <= 64 || r.height <= 64) continue;
                            const style = window.getComputedStyle(c);
                            if (style && (style.visibility === 'hidden' || style.display === 'none')) continue;
                            const area = r.width * r.height;
                            if (area > bestArea) {
                                bestArea = area;
                                best = c;
                            }
                        }
                        return best;
                    };"""

new_pick_canvas = """const pickCanvas = () => {{
                        const all = Array.from(document.querySelectorAll('canvas'));
                        if (!all.length) return null;
                        const main = document.querySelector('.main-canvas');
                        if (main && main instanceof HTMLCanvasElement) return main;
                        let best = null;
                        let bestArea = -1;
                        for (const c of all) {{
                            if (!(c instanceof HTMLCanvasElement)) continue;
                            const r = c.getBoundingClientRect();
                            if (!r || r.width <= 64 || r.height <= 64) continue;
                            const style = window.getComputedStyle(c);
                            if (style && (style.visibility === 'hidden' || style.display === 'none')) continue;
                            const area = r.width * r.height;
                            if (area > bestArea) {{
                                bestArea = area;
                                best = c;
                            }}
                        }}
                        return best;
                    }};"""

content = content.replace(old_pick_canvas, new_pick_canvas)

# Let's ensure ctx.fillStyle and strokeStyle also use proper braces for color variables 
# wait, window.__nlp2cmd_foreground isn't an f-string python variable, so we don't need to change that.
# we replaced: ctx.fillStyle = (window.__nlp2cmd_foreground || (window.__nlp2cmd_foreground || (window.colors && window.colors.foreground)) || '#000');
# This is fine.

with open(file_path, "w") as f:
    f.write(content)
print("Fixed braces")
