"""
HTTP Stream Adapter — interact with REST/HTTP APIs.

Usage:
    nlp2cmd --source http://api.example.com/v1 "get users"
    nlp2cmd --source https://jsonplaceholder.typicode.com "list posts"
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, Optional

from nlp2cmd.streams.base import StreamAdapter, StreamResult, SourceURI


class HTTPStreamAdapter(StreamAdapter):
    PROTOCOL = "http"

    def connect(self) -> StreamResult:
        self._connected = True
        base = f"{self.source.scheme}://{self.source.host}"
        if self.source.port:
            base += f":{self.source.port}"
        return StreamResult(success=True, output=f"HTTP target: {base}{self.source.path}")

    def execute(self, task: str, **kwargs) -> StreamResult:
        base = f"{self.source.scheme}://{self.source.host}"
        if self.source.port:
            base += f":{self.source.port}"
        base += self.source.path

        task_lower = task.lower()
        method = "GET"
        endpoint = ""
        body = None

        if any(w in task_lower for w in ["post", "create", "utwórz", "dodaj"]):
            method = "POST"
        elif any(w in task_lower for w in ["put", "update", "aktualizuj"]):
            method = "PUT"
        elif any(w in task_lower for w in ["delete", "usuń", "skasuj"]):
            method = "DELETE"

        # Extract endpoint from task
        words = task.split()
        for w in words:
            if w.startswith("/"):
                endpoint = w
                break

        url = f"{base}{endpoint}"
        cmd = ["curl", "-s", "-X", method, url, "-H", "Accept: application/json"]

        if method in ("POST", "PUT") and kwargs.get("data"):
            cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(kwargs["data"])]

        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            output = r.stdout.strip()
            try:
                data = json.loads(output)
            except Exception:
                data = {"raw": output}

            return StreamResult(
                success=r.returncode == 0,
                output=output[:500],
                data=data if isinstance(data, dict) else {"response": data},
                metadata={"method": method, "url": url},
            )
        except Exception as e:
            return StreamResult(success=False, error=str(e))

    def query(self, question: str, **kwargs) -> StreamResult:
        return self.execute(f"GET {self.source.path or '/'}", **kwargs)
