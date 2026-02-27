"""
Stream Router — dispatches tasks to the appropriate protocol handler.

Usage:
    router = StreamRouter()
    result = router.execute("ssh://user@host", "list files in /var/log")
    result = router.execute("rtsp://cam:554/stream", "what colors are dominant?")
    result = router.execute("libvirt:///system", "create ubuntu VM")
"""

from __future__ import annotations

import time
from typing import Any, Optional

from nlp2cmd.streams.base import StreamAdapter, StreamResult, SourceURI, parse_source_uri


# Registry of protocol → adapter class (lazy imports)
_PROTOCOL_MAP: dict[str, str] = {
    "ssh": "nlp2cmd.streams.ssh_stream.SSHStreamAdapter",
    "vnc": "nlp2cmd.streams.vnc_stream.VNCStreamAdapter",
    "novnc": "nlp2cmd.streams.vnc_stream.VNCStreamAdapter",
    "spice": "nlp2cmd.streams.spice_stream.SPICEStreamAdapter",
    "rdp": "nlp2cmd.streams.rdp_stream.RDPStreamAdapter",
    "ftp": "nlp2cmd.streams.ftp_stream.FTPStreamAdapter",
    "sftp": "nlp2cmd.streams.ssh_stream.SSHStreamAdapter",
    "http": "nlp2cmd.streams.http_stream.HTTPStreamAdapter",
    "https": "nlp2cmd.streams.http_stream.HTTPStreamAdapter",
    "ws": "nlp2cmd.streams.ws_stream.WSStreamAdapter",
    "wss": "nlp2cmd.streams.ws_stream.WSStreamAdapter",
    "rtsp": "nlp2cmd.streams.rtsp_stream.RTSPStreamAdapter",
    "libvirt": "nlp2cmd.streams.libvirt_stream.LibvirtStreamAdapter",
}


def _load_adapter_class(dotted_path: str) -> type:
    """Dynamically import an adapter class."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class StreamRouter:
    """Routes --source URIs to the correct protocol handler."""

    def __init__(self, *, logger=None):
        self.logger = logger
        self._adapters: dict[str, StreamAdapter] = {}

    def get_adapter(self, source: str | SourceURI) -> StreamAdapter:
        """Get or create an adapter for the given source."""
        if isinstance(source, str):
            source = parse_source_uri(source)

        key = source.raw
        if key in self._adapters:
            return self._adapters[key]

        dotted = _PROTOCOL_MAP.get(source.scheme)
        if not dotted:
            raise ValueError(
                f"Unsupported protocol: {source.scheme}://\n"
                f"Supported: {', '.join(sorted(_PROTOCOL_MAP.keys()))}"
            )

        cls = _load_adapter_class(dotted)
        adapter = cls(source)
        self._adapters[key] = adapter
        return adapter

    def execute(self, source: str, task: str, **kwargs) -> StreamResult:
        """Execute a task on the given source stream.

        Args:
            source: URI string like "ssh://user@host" or "rtsp://cam/stream"
            task: Natural language task or command to execute
            **kwargs: Protocol-specific options

        Returns:
            StreamResult with output, data, optional screenshot
        """
        started = time.time()
        uri = parse_source_uri(source)

        try:
            adapter = self.get_adapter(uri)

            if not adapter._connected:
                connect_result = adapter.connect()
                if not connect_result.success:
                    return connect_result

            result = adapter.execute(task, **kwargs)
            result.duration_ms = (time.time() - started) * 1000
            result.metadata["source"] = source
            result.metadata["protocol"] = uri.scheme
            return result

        except Exception as e:
            return StreamResult(
                success=False,
                error=str(e),
                duration_ms=(time.time() - started) * 1000,
                metadata={"source": source, "protocol": uri.scheme},
            )

    def query(self, source: str, question: str, **kwargs) -> StreamResult:
        """Ask a question about a stream (metadata, analysis, status)."""
        started = time.time()
        uri = parse_source_uri(source)

        try:
            adapter = self.get_adapter(uri)
            if not adapter._connected:
                adapter.connect()

            result = adapter.query(question, **kwargs)
            result.duration_ms = (time.time() - started) * 1000
            return result
        except Exception as e:
            return StreamResult(
                success=False,
                error=str(e),
                duration_ms=(time.time() - started) * 1000,
            )

    def close_all(self):
        """Disconnect all active adapters."""
        for adapter in self._adapters.values():
            try:
                adapter.disconnect()
            except Exception:
                pass
        self._adapters.clear()

    @staticmethod
    def supported_protocols() -> list[str]:
        return sorted(_PROTOCOL_MAP.keys())
