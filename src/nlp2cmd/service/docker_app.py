"""Compatibility exports for the WebOps voice service app.

The WebOps service currently lives outside the installable ``nlp2cmd`` package
under ``webops/docker_app.py``. Some integration tests and older callers import
it through ``nlp2cmd.service.docker_app``, so keep that import path working
without duplicating the WebOps implementation.
"""

from __future__ import annotations

try:
    from webops.docker_app import (
        ShellExecutor,
        VoiceCommandRequest,
        VoiceCommandResponse,
        VoiceServiceManager,
        app,
        create_voice_app,
        health_check,
        process_voice_command,
        root,
        websocket_endpoint,
    )
except (ImportError, TypeError) as exc:
    raise ImportError(
        "nlp2cmd.service.docker_app requires the WebOps source module and "
        "its optional FastAPI service dependencies."
    ) from exc

__all__ = [
    "ShellExecutor",
    "VoiceCommandRequest",
    "VoiceCommandResponse",
    "VoiceServiceManager",
    "app",
    "create_voice_app",
    "health_check",
    "process_voice_command",
    "root",
    "websocket_endpoint",
]
