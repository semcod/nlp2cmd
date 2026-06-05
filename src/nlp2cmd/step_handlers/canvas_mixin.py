# CanvasMixin - extracted from drawing.py
"""Drawing and canvas step handlers."""
from __future__ import annotations
import json
from typing import TYPE_CHECKING
from .base import StepHandler, HandlerContext, HandlerResult
from .registry import register_handler
if TYPE_CHECKING:
    pass
class CanvasMixin:
    """Mixin providing canvas selection logic."""
    
    def _pick_canvas_js(self) -> str:
        """Return JavaScript function to select the best canvas element."""
        return """
        () => {
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
        }
        """
    
    def _get_color_js(self) -> str:
        """Return JavaScript to get the current color."""
        return "(window.__nlp2cmd_foreground || (window.colors && window.colors.foreground) || '#000')"

    def _pixel_stats_js(self) -> str:
        """Return JavaScript that captures a compact canvas pixel summary."""
        pick_canvas = self._pick_canvas_js()
        return f"""
        () => {{
            const pickCanvas = {pick_canvas};
            const canvas = pickCanvas();
            if (!canvas) return {{error: 'No canvas found'}};
            const ctx = canvas.getContext('2d');
            if (!ctx) return {{error: 'Canvas 2D context unavailable'}};
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            let nonWhite = 0;
            for (let i = 0; i < imageData.data.length; i += 400) {{
                if (imageData.data[i] !== 255 || imageData.data[i+1] !== 255 || imageData.data[i+2] !== 255) {{
                    nonWhite++;
                }}
            }}
            return {{nonWhitePixels: nonWhite, isBlank: nonWhite <= 10, width: canvas.width, height: canvas.height}};
        }}
        """
