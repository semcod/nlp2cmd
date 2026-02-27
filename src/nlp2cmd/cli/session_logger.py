"""
Session Logger — generates Markdown reports with base64 thumbnail screenshots.

Creates a .md file documenting each step of a desktop/browser automation session
with inline base64-encoded 256px thumbnail images.

Usage:
    logger = SessionLogger("my_session")
    logger.start("Desktop GUI Demo")
    logger.step("Open terminal", page=page)
    logger.info("Typed command: echo hello")
    logger.step("Run calculator", page=page)
    logger.end()
    # → my_session.md with inline thumbnails
"""

from __future__ import annotations

import base64
import io
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


def _resize_to_thumbnail(png_bytes: bytes, max_width: int = 256) -> bytes:
    """Resize PNG to thumbnail using Pillow or fallback to raw."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(png_bytes))
        ratio = max_width / img.width
        new_size = (max_width, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
    except ImportError:
        # No Pillow — return original (larger but still works)
        return png_bytes


def _png_to_base64_md(png_bytes: bytes, alt: str = "screenshot", max_width: int = 256) -> str:
    """Convert PNG bytes to a Markdown inline base64 image (thumbnail)."""
    thumb = _resize_to_thumbnail(png_bytes, max_width=max_width)
    b64 = base64.b64encode(thumb).decode("ascii")
    return f"![{alt}](data:image/png;base64,{b64})"


class SessionLogger:
    """Logs automation sessions to Markdown with inline base64 screenshots."""

    def __init__(
        self,
        name: str = "session",
        *,
        output_dir: Optional[Path] = None,
        thumbnail_width: int = 256,
        save_full_screenshots: bool = True,
    ):
        self.name = name
        self.output_dir = Path(output_dir) if output_dir else Path(".")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnail_width = thumbnail_width
        self.save_full_screenshots = save_full_screenshots

        self._lines: list[str] = []
        self._step_count = 0
        self._start_time: float = 0.0
        self._screenshots_dir = self.output_dir / f"{name}_screenshots"
        if save_full_screenshots:
            self._screenshots_dir.mkdir(parents=True, exist_ok=True)

    def start(self, title: str, *, description: str = "") -> None:
        """Start a new session log."""
        self._start_time = time.time()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self._lines.append(f"# {title}\n")
        self._lines.append(f"**Date:** {now}  ")
        self._lines.append(f"**Session:** `{self.name}`  ")
        if description:
            self._lines.append(f"**Description:** {description}  ")
        self._lines.append(f"**Thumbnail size:** {self.thumbnail_width}px  ")
        self._lines.append("")
        self._lines.append("---\n")

    def step(
        self,
        description: str,
        *,
        page: Any = None,
        screenshot_bytes: Optional[bytes] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log a step with optional screenshot from Playwright page or raw bytes."""
        self._step_count += 1
        elapsed = time.time() - self._start_time if self._start_time else 0.0
        step_id = f"{self._step_count:02d}"

        self._lines.append(f"## Step {step_id}: {description}\n")
        self._lines.append(f"*Time: +{elapsed:.1f}s*\n")

        # Capture screenshot
        png_bytes = screenshot_bytes
        if png_bytes is None and page is not None:
            try:
                png_bytes = page.screenshot()
            except Exception as e:
                self._lines.append(f"> ⚠️ Screenshot failed: {e}\n")

        if png_bytes:
            # Save full screenshot to disk
            if self.save_full_screenshots:
                full_path = self._screenshots_dir / f"{step_id}_{_slugify(description)}.png"
                full_path.write_bytes(png_bytes)

            # Embed thumbnail as base64
            md_img = _png_to_base64_md(
                png_bytes,
                alt=f"Step {step_id}: {description}",
                max_width=self.thumbnail_width,
            )
            self._lines.append(md_img)
            self._lines.append("")

        if extra:
            self._lines.append("```yaml")
            for k, v in extra.items():
                self._lines.append(f"{k}: {v}")
            self._lines.append("```\n")

        self._lines.append("")

    def info(self, text: str) -> None:
        """Add an info line to the log."""
        self._lines.append(f"- {text}")

    def warning(self, text: str) -> None:
        """Add a warning to the log."""
        self._lines.append(f"- ⚠️ {text}")

    def code(self, text: str, language: str = "bash") -> None:
        """Add a code block to the log."""
        self._lines.append(f"```{language}")
        self._lines.append(text)
        self._lines.append("```\n")

    def section(self, title: str) -> None:
        """Add a section header."""
        self._lines.append(f"\n### {title}\n")

    def end(self, *, summary: Optional[dict[str, Any]] = None) -> Path:
        """Finalize the session log and write to .md file.

        Returns the path to the written file.
        """
        total = time.time() - self._start_time if self._start_time else 0.0
        self._lines.append("\n---\n")
        self._lines.append("## Summary\n")
        self._lines.append(f"- **Total steps:** {self._step_count}")
        self._lines.append(f"- **Total time:** {total:.1f}s")

        if summary:
            for k, v in summary.items():
                self._lines.append(f"- **{k}:** {v}")

        if self.save_full_screenshots:
            self._lines.append(f"- **Full screenshots:** `{self._screenshots_dir}/`")

        self._lines.append("")

        md_path = self.output_dir / f"{self.name}.md"
        md_path.write_text("\n".join(self._lines), encoding="utf-8")
        return md_path

    def get_markdown(self) -> str:
        """Return the current markdown content as string."""
        return "\n".join(self._lines)


def _slugify(text: str) -> str:
    """Convert text to a safe filename slug."""
    import re
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "_", slug)
    return slug[:50]
