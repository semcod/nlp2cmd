"""Tests for markdown CLI output helpers."""

from __future__ import annotations

import io

from rich.console import Console

from nlp2cmd.cli.markdown_output import _render_to_text, print_markdown_block


class TestRenderToText:
    def test_plain_string_unchanged(self):
        assert _render_to_text("hello world") == "hello world"

    def test_rich_markup_stripped(self):
        text = _render_to_text("[cyan]▸ Krok 1/14:[/cyan] Otwórz jspaint  [dim](navigate)[/dim]")
        assert "[cyan]" not in text
        assert "[/cyan]" not in text
        assert "[dim]" not in text
        assert "▸ Krok 1/14:" in text
        assert "Otwórz jspaint" in text
        assert "(navigate)" in text

    def test_green_check_rendered(self):
        text = _render_to_text("  [green]✓[/green] OK")
        assert "[green]" not in text
        assert "✓" in text
        assert "OK" in text


class TestPrintMarkdownBlock:
    def test_rich_string_in_block_has_no_markup_tags(self):
        buf = io.StringIO()
        console = Console(file=buf, force_terminal=True, color_system=None)
        print_markdown_block(
            "[bold]📊 Podsumowanie planu:[/bold]\n  [green]✓[/green] OK",
            language="text",
            console=console,
        )
        out = buf.getvalue()
        assert "### output" in out
        assert "```text" in out
        assert "[bold]" not in out
        assert "[green]" not in out
        assert "Podsumowanie planu:" in out
        assert "✓" in out
