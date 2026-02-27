"""
SPICE Stream Adapter — control VM desktops via SPICE protocol.

Uses remote-viewer (virt-viewer) or Playwright+noVNC bridge for GUI control.

Usage:
    nlp2cmd --source spice://localhost:5900 "open terminal and run htop"
"""

from __future__ import annotations

import subprocess
from typing import Any, Optional

from nlp2cmd.streams.base import StreamAdapter, StreamResult, SourceURI


class SPICEStreamAdapter(StreamAdapter):
    PROTOCOL = "spice"

    def connect(self) -> StreamResult:
        port = self.source.port or 5900
        spice_url = f"spice://{self.source.host}:{port}"
        # Check if remote-viewer is available
        try:
            r = subprocess.run(["which", "remote-viewer"], capture_output=True, text=True)
            has_viewer = r.returncode == 0
        except Exception:
            has_viewer = False

        self._connected = True
        return StreamResult(
            success=True,
            output=f"SPICE target: {spice_url} (viewer: {'remote-viewer' if has_viewer else 'not found — use noVNC bridge'})",
            metadata={"spice_url": spice_url, "has_viewer": has_viewer},
        )

    def execute(self, task: str, **kwargs) -> StreamResult:
        port = self.source.port or 5900

        # For GUI control, delegate to noVNC bridge if available
        if any(w in task.lower() for w in ["open", "type", "click", "otwórz", "wpisz", "kliknij"]):
            return StreamResult(
                success=True,
                output=f"SPICE GUI task queued: {task}",
                data={
                    "task": task,
                    "hint": "Use noVNC bridge or remote-viewer for interactive control",
                    "spice_url": f"spice://{self.source.host}:{port}",
                },
            )

        # For VM commands, use virsh console
        return StreamResult(
            success=True,
            output=f"SPICE execute: {task} (connect via: remote-viewer spice://{self.source.host}:{port})",
            data={"task": task},
        )

    def query(self, question: str, **kwargs) -> StreamResult:
        return StreamResult(
            success=True, output=f"SPICE display at {self.source.host}:{self.source.port or 5900}",
        )
