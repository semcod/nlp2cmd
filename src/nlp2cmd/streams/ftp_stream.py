"""
FTP/SFTP Stream Adapter — file operations on remote servers.

Usage:
    nlp2cmd --source ftp://user:pass@host/path "list files"
    nlp2cmd --source sftp://user@host "download /var/log/syslog"
"""

from __future__ import annotations

import subprocess
from typing import Any, Optional

from nlp2cmd.streams.base import StreamAdapter, StreamResult, SourceURI


class FTPStreamAdapter(StreamAdapter):
    PROTOCOL = "ftp"

    def connect(self) -> StreamResult:
        self._connected = True
        scheme = self.source.scheme
        host = self.source.host
        return StreamResult(success=True, output=f"{scheme.upper()} ready for {host}")

    def execute(self, task: str, **kwargs) -> StreamResult:
        task_lower = task.lower()
        path = self.source.path or "/"

        if self.source.scheme == "sftp":
            return self._sftp_execute(task, **kwargs)

        # FTP via curl
        user = self.source.user or "anonymous"
        password = self.source.password or ""
        host = self.source.host
        port = self.source.port or 21

        if any(w in task_lower for w in ["list", "ls", "pokaż", "wyświetl"]):
            cmd = ["curl", "-s", f"ftp://{user}:{password}@{host}:{port}{path}"]
        elif any(w in task_lower for w in ["download", "pobierz", "get"]):
            fname = task.split()[-1] if len(task.split()) > 1 else "file"
            cmd = ["curl", "-s", "-o", fname, f"ftp://{user}:{password}@{host}:{port}{path}/{fname}"]
        elif any(w in task_lower for w in ["upload", "wyślij", "put"]):
            fname = task.split()[-1] if len(task.split()) > 1 else "file"
            cmd = ["curl", "-s", "-T", fname, f"ftp://{user}:{password}@{host}:{port}{path}/"]
        else:
            return StreamResult(success=False, error=f"Unknown FTP task: {task}")

        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return StreamResult(
                success=r.returncode == 0,
                output=r.stdout.strip(),
                error=r.stderr.strip() if r.returncode != 0 else None,
                data={"command": " ".join(cmd)},
            )
        except Exception as e:
            return StreamResult(success=False, error=str(e))

    def _sftp_execute(self, task: str, **kwargs) -> StreamResult:
        user = self.source.user or "root"
        host = self.source.host
        port = self.source.port or 22
        task_lower = task.lower()

        if any(w in task_lower for w in ["list", "ls"]):
            remote_cmd = f"ls -la {self.source.path or '/'}"
        elif any(w in task_lower for w in ["download", "pobierz"]):
            fname = task.split()[-1]
            remote_cmd = f"get {fname}"
        else:
            remote_cmd = task

        cmd = ["ssh", "-p", str(port), f"{user}@{host}", remote_cmd]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return StreamResult(
                success=r.returncode == 0,
                output=r.stdout.strip(),
                error=r.stderr.strip() if r.returncode != 0 else None,
            )
        except Exception as e:
            return StreamResult(success=False, error=str(e))

    def query(self, question: str, **kwargs) -> StreamResult:
        return self.execute(f"list {self.source.path or '/'}", **kwargs)
