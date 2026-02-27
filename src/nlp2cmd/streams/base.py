"""
Base classes for stream protocol handlers.

Every protocol (VNC, SPICE, RDP, SSH, FTP, HTTP, WS, RTSP, libvirt)
implements StreamAdapter and returns StreamResult.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs


@dataclass
class StreamResult:
    """Result of a stream operation."""
    success: bool = False
    output: str = ""
    error: Optional[str] = None
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    screenshot: Optional[bytes] = None  # PNG bytes if visual stream
    duration_ms: float = 0.0


@dataclass
class SourceURI:
    """Parsed --source URI."""
    scheme: str = ""          # vnc, spice, rdp, ssh, ftp, http, https, ws, wss, rtsp, libvirt
    host: str = ""
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    path: str = ""
    params: dict[str, str] = field(default_factory=dict)
    raw: str = ""

    @property
    def is_visual(self) -> bool:
        """True if this stream has a visual component (desktop/video)."""
        return self.scheme in ("vnc", "spice", "rdp", "rtsp", "novnc")

    @property
    def is_shell(self) -> bool:
        """True if this stream supports shell command execution."""
        return self.scheme in ("ssh", "libvirt")

    @property
    def is_file(self) -> bool:
        """True if this stream supports file operations."""
        return self.scheme in ("ftp", "sftp", "ssh", "http", "https")

    @property
    def netloc(self) -> str:
        parts = []
        if self.user:
            parts.append(f"{self.user}@")
        parts.append(self.host)
        if self.port:
            parts.append(f":{self.port}")
        return "".join(parts)


def parse_source_uri(uri: str) -> SourceURI:
    """Parse a --source URI string into SourceURI.

    Supports:
        ssh://user@host:port/path
        vnc://host:5901
        spice://host:5900
        rdp://user:pass@host
        ftp://user:pass@host/path
        http://host:8080/api/endpoint
        ws://host:8080/stream
        rtsp://host:554/stream
        libvirt:///system  (local)
        libvirt+ssh://user@host/system
    """
    raw = uri.strip()

    # Handle libvirt special URIs like libvirt:///system
    if raw.startswith("libvirt"):
        return _parse_libvirt_uri(raw)

    parsed = urlparse(raw)
    scheme = parsed.scheme.lower()

    # Normalize common aliases
    scheme_map = {
        "sftp": "sftp",
        "scp": "ssh",
        "wss": "wss",
        "https": "https",
        "novnc": "novnc",
    }
    scheme = scheme_map.get(scheme, scheme)

    user = parsed.username
    password = parsed.password
    host = parsed.hostname or "localhost"
    port = parsed.port
    path = parsed.path or ""
    params = {}
    if parsed.query:
        for k, v in parse_qs(parsed.query).items():
            params[k] = v[0] if v else ""

    return SourceURI(
        scheme=scheme,
        host=host,
        port=port,
        user=user,
        password=password,
        path=path,
        params=params,
        raw=raw,
    )


def _parse_libvirt_uri(raw: str) -> SourceURI:
    """Parse libvirt:// style URIs."""
    # libvirt:///system → local QEMU
    # libvirt+ssh://user@host/system → remote via SSH
    m = re.match(r"libvirt(?:\+(\w+))?://(?:(\w+)@)?([\w.-]*)(/.+)?", raw)
    if not m:
        return SourceURI(scheme="libvirt", raw=raw)

    transport = m.group(1)  # ssh, tcp, etc
    user = m.group(2)
    host = m.group(3) or "localhost"
    path = m.group(4) or "/system"

    return SourceURI(
        scheme="libvirt",
        host=host,
        user=user,
        path=path,
        params={"transport": transport or "local"},
        raw=raw,
    )


class StreamAdapter:
    """Base class for all stream protocol handlers.

    Subclasses implement:
    - connect() — establish connection
    - execute(task) — run a task on the stream
    - query(question) — ask a question about the stream
    - disconnect() — clean up
    """

    PROTOCOL: str = ""  # e.g. "ssh", "vnc", "rtsp"

    def __init__(self, source: SourceURI):
        self.source = source
        self._connected = False

    def connect(self) -> StreamResult:
        """Establish connection to the stream."""
        raise NotImplementedError

    def execute(self, task: str, **kwargs) -> StreamResult:
        """Execute a task on the stream (command, action, query)."""
        raise NotImplementedError

    def query(self, question: str, **kwargs) -> StreamResult:
        """Ask a question about the stream (metadata, status, analysis)."""
        raise NotImplementedError

    def screenshot(self) -> Optional[bytes]:
        """Capture screenshot if visual stream. Returns PNG bytes or None."""
        return None

    def disconnect(self) -> None:
        """Clean up connection."""
        self._connected = False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.disconnect()
