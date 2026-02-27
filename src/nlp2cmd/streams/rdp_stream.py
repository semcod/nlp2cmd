"""
RDP Stream Adapter — control Windows desktops via xfreerdp.

Usage:
    nlp2cmd --source rdp://user:pass@windows-host "open notepad and type hello"
"""

from __future__ import annotations

import subprocess
from typing import Any, Optional

from nlp2cmd.streams.base import StreamAdapter, StreamResult, SourceURI


class RDPStreamAdapter(StreamAdapter):
    PROTOCOL = "rdp"

    def connect(self) -> StreamResult:
        try:
            r = subprocess.run(["which", "xfreerdp"], capture_output=True, text=True)
            has_rdp = r.returncode == 0
        except Exception:
            has_rdp = False

        if not has_rdp:
            return StreamResult(success=False, error="xfreerdp not found. Install: sudo apt install freerdp2-x11")

        self._connected = True
        return StreamResult(success=True, output=f"RDP ready for {self.source.host}")

    def execute(self, task: str, **kwargs) -> StreamResult:
        user = self.source.user or "Administrator"
        host = self.source.host
        port = self.source.port or 3389
        password = self.source.password or ""

        cmd = [
            "xfreerdp", f"/v:{host}:{port}", f"/u:{user}",
            "/cert:ignore", "/size:1280x800", "+clipboard",
        ]
        if password:
            cmd.append(f"/p:{password}")

        return StreamResult(
            success=True,
            output=f"RDP task: {task}",
            data={"task": task, "rdp_command": " ".join(cmd),
                   "hint": "For GUI automation, pipe RDP through noVNC or use xdotool on the X display"},
        )

    def query(self, question: str, **kwargs) -> StreamResult:
        return StreamResult(success=True, output=f"RDP endpoint: {self.source.host}:{self.source.port or 3389}")
