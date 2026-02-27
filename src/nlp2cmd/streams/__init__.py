"""
Stream protocol handlers for NLP2CMD.

Provides unified --source interface for executing tasks on different streams:
- vnc://     — Desktop GUI control via VNC/noVNC
- spice://   — VM desktop control via SPICE (libvirt)
- rdp://     — Windows desktop control via RDP (xfreerdp)
- ssh://     — Remote shell commands via SSH
- ftp://     — File operations via FTP/SFTP
- http://    — HTTP/REST API interaction
- ws://      — WebSocket real-time streams
- rtsp://    — Video stream analysis (color, motion, objects)
- libvirt:// — VM lifecycle management (create, start, stop)

Usage:
    from nlp2cmd.streams import StreamRouter, parse_source_uri
    router = StreamRouter()
    result = router.execute("ssh://user@host", "list files in /var/log")
"""

from nlp2cmd.streams.base import StreamAdapter, StreamResult, parse_source_uri
from nlp2cmd.streams.router import StreamRouter

__all__ = [
    "StreamAdapter",
    "StreamResult",
    "StreamRouter",
    "parse_source_uri",
]
