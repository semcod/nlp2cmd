"""Utilities for printing CLI output as Markdown code blocks."""

from __future__ import annotations

import io
from typing import Any, Optional

from rich.console import Console


def _render_to_text(renderable: Any) -> str:
    """Render any Rich renderable or string to plain text."""
    if renderable is None:
        return ""
    if isinstance(renderable, str):
        return renderable.rstrip()
    stream = io.StringIO()
    capture_console = Console(record=True, force_terminal=False, color_system=None, file=stream)
    capture_console.print(renderable)
    return capture_console.export_text().rstrip()


def _infer_markdown_title(*, language: str, body: str, title: Optional[str]) -> str:
    if isinstance(title, str) and title.strip():
        t = title.strip()
        # If caller passed a markdown header already, normalize it to a plain title.
        t = t.lstrip("#").strip()
        return t

    if language.lower() == "yaml":
        for line in body.splitlines()[:20]:
            if line.startswith("status:"):
                value = line.split(":", 1)[1].strip()
                if value:
                    return f"status: {value}"

    if language.lower() == "bash":
        return "run"
    if language.lower() == "text":
        return "output"
    return language


def print_markdown_block(
    renderable: Any,
    *,
    language: str = "text",
    title: Optional[str] = None,
    console: Optional[Console] = None,
) -> None:
    """Print a renderable or string wrapped in a Markdown code block."""
    console = console or Console()
    body = _render_to_text(renderable)

    md_title = _infer_markdown_title(language=language, body=body, title=title)
    if md_title:
        console.print(f"\n### {md_title}", markup=False)
    lines = [f"```{language}"]
    if body:
        lines.append(body)
    lines.append("```")
    console.print("\n".join(lines), markup=False)


def print_yaml_block(data: Any, *, console: Optional[Console] = None) -> None:
    from nlp2cmd.utils.yaml_compat import yaml

    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).rstrip()
    print_markdown_block(text, language="yaml", console=console)


class MarkdownConsoleProxy:
    """Proxy that forces all console.print output into markdown code blocks."""

    def __init__(self, console: Console, *, language: str = "text") -> None:
        self._console = console
        self._language = language

    def print(self, renderable: Any, *args, **kwargs) -> None:  # type: ignore[override]
        # Ignore extra args/kwargs for simplicity and rely on markdown blocks
        print_markdown_block(renderable, language=self._language, console=self._console)

    def input(self, *args, **kwargs):  # type: ignore[override]
        return self._console.input(*args, **kwargs)

    def __getattr__(self, item: str):
        return getattr(self._console, item)


class MarkdownBlockStream:
    """Context manager that streams multiple prints inside a single Markdown block."""

    def __init__(
        self,
        console: Optional[Console] = None,
        *,
        language: str = "text",
        title: Optional[str] = None,
    ) -> None:
        self._console = console or Console()
        self._language = language
        self._title = title.rstrip() if isinstance(title, str) else None
        self._open = False

    def __enter__(self) -> "MarkdownBlockStream":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _ensure_open(self) -> None:
        if not self._open:
            body_preview = ""  # no content yet; still provide a stable title
            md_title = _infer_markdown_title(language=self._language, body=body_preview, title=self._title)
            if md_title:
                self._console.print(f"\n### {md_title}", markup=False)
            self._console.print(f"```{self._language}", markup=False)
            self._open = True

    def print(self, renderable: Any) -> None:
        body = _render_to_text(renderable)
        self._ensure_open()
        if body:
            self._console.print(body, markup=False)
        else:
            self._console.print("", markup=False)

    def close(self) -> None:
        if self._open:
            self._console.print("```", markup=False)
            self._open = False
