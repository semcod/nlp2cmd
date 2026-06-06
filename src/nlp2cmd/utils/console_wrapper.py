"""Markdown console wrapper for capturing output into code blocks."""

from __future__ import annotations

from rich.console import Console


class _MarkdownConsoleWrapper:
    """Context manager that captures console output into Markdown code blocks."""

    def __init__(self, console: Console, *, enable_markdown: bool, default_language: str = "text") -> None:
        self.console = console
        self.enable_markdown = enable_markdown
        self.default_language = default_language
        self._buffer: list[str] = []
        self._stream_block = None
        # Import inside class to avoid circular dependency
        from nlp2cmd.cli.markdown_output import print_markdown_block, MarkdownBlockStream
        self.print_markdown_block = print_markdown_block
        self._MarkdownBlockStream = MarkdownBlockStream

    def print(self, renderable, *, language: str | None = None) -> None:
        if self.enable_markdown:
            if language and language != self.default_language:
                self._flush_stream()
                self.print_markdown_block(
                    renderable,
                    language=language or self.default_language,
                    console=self.console,
                )
                return
            if self._stream_block is None:
                self._stream_block = self._MarkdownBlockStream(
                    self.console,
                    language=self.default_language,
                    title="output",
                )
                self._stream_block.__enter__()
            self._stream_block.print(renderable)
        else:
            self.console.print(renderable)

    def _flush_stream(self) -> None:
        if self._stream_block is not None:
            self._stream_block.close()
            self._stream_block = None

    def flush(self) -> None:
        """Close any open streaming markdown block."""
        self._flush_stream()

    def capture(self):
        """Return context manager that captures printed text into a single block."""
        wrapper = self

        class _Capture:
            def __enter__(self):
                wrapper._buffer = []
                return wrapper._buffer

            def __exit__(self, exc_type, exc, tb):
                wrapper._flush_stream()
                if wrapper.enable_markdown and wrapper._buffer:
                    wrapper.print_markdown_block("\n".join(wrapper._buffer), language=wrapper.default_language, console=wrapper.console)
                elif wrapper._buffer:
                    wrapper.console.print("\n".join(wrapper._buffer))

        return _Capture()
