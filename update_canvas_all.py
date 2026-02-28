import re

file_path = "/home/tom/github/wronai/nlp2cmd/src/nlp2cmd/pipeline_runner.py"
with open(file_path, "r") as f:
    content = f.read()

# The helper pickCanvas is already inside `draw_circle` and `draw_filled_ellipse` but not in others.
# We will just replace `const canvas = (document.querySelector('.main-canvas') || document.querySelector('canvas'));` 
# with the robust pickCanvas logic in all drawing functions.

pick_canvas_js = """const pickCanvas = () => {
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
                    };
                    const canvas = pickCanvas();"""

content = content.replace("const canvas = (document.querySelector('.main-canvas') || document.querySelector('canvas'));", pick_canvas_js)

with open(file_path, "w") as f:
    f.write(content)
print("Updated all canvas selectors")
