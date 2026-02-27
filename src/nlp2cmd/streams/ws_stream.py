"""
WebSocket Stream Adapter — real-time bidirectional communication.

Usage:
    nlp2cmd --source ws://host:8080/stream "send hello"
    nlp2cmd --source wss://api.example.com/ws "subscribe to updates"
"""

from __future__ import annotations

import json
from typing import Any, Optional

from nlp2cmd.streams.base import StreamAdapter, StreamResult, SourceURI


class WSStreamAdapter(StreamAdapter):
    PROTOCOL = "ws"

    def __init__(self, source: SourceURI):
        super().__init__(source)
        self._ws = None

    def _build_url(self) -> str:
        scheme = self.source.scheme  # ws or wss
        host = self.source.host
        port = f":{self.source.port}" if self.source.port else ""
        path = self.source.path or "/"
        return f"{scheme}://{host}{port}{path}"

    def connect(self) -> StreamResult:
        url = self._build_url()
        try:
            import websocket
            self._ws = websocket.create_connection(url, timeout=10)
            self._connected = True
            return StreamResult(success=True, output=f"WebSocket connected: {url}")
        except ImportError:
            # Fallback: just mark as ready, execute will use subprocess/curl
            self._connected = True
            return StreamResult(
                success=True,
                output=f"WebSocket target: {url} (install websocket-client for full support)",
            )
        except Exception as e:
            return StreamResult(success=False, error=f"WebSocket connection failed: {e}")

    def execute(self, task: str, **kwargs) -> StreamResult:
        task_lower = task.lower()

        if any(w in task_lower for w in ["send", "wyślij", "emit"]):
            msg = task.split(maxsplit=1)[-1] if len(task.split()) > 1 else task
            return self._send(msg)
        elif any(w in task_lower for w in ["receive", "read", "listen", "odbierz", "czytaj"]):
            return self._receive(timeout=kwargs.get("timeout", 5))
        elif any(w in task_lower for w in ["subscribe", "subskrybuj"]):
            return self._send(json.dumps({"type": "subscribe", "channel": task.split()[-1]}))
        else:
            return self._send(task)

    def _send(self, message: str) -> StreamResult:
        if self._ws:
            try:
                self._ws.send(message)
                return StreamResult(success=True, output=f"Sent: {message[:200]}")
            except Exception as e:
                return StreamResult(success=False, error=str(e))
        return StreamResult(success=False, error="Not connected (install websocket-client)")

    def _receive(self, timeout: float = 5) -> StreamResult:
        if self._ws:
            try:
                self._ws.settimeout(timeout)
                data = self._ws.recv()
                return StreamResult(success=True, output=data[:1000], data={"raw": data})
            except Exception as e:
                return StreamResult(success=False, error=str(e))
        return StreamResult(success=False, error="Not connected")

    def query(self, question: str, **kwargs) -> StreamResult:
        return self._receive(timeout=kwargs.get("timeout", 3))

    def disconnect(self) -> None:
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None
        self._connected = False
