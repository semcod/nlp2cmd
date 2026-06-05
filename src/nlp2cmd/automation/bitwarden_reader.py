# BitwardenReader - extracted from password_store.py
"""
Password Store for NLP2CMD — Multi-Backend Credential Reader.

Provides credentials for automated login flows by reading from:
1. Firefox saved passwords (logins.json + NSS decryption via libnss3)
2. KeePassXC CLI (keepassxc-cli)
3. Bitwarden CLI (bw)
4. Environment variables (.env / os.environ)

All passwords are cached in-memory for the session duration only.
No passwords are written to disk.

Usage:
    from nlp2cmd.automation.password_store import get_password_store

    store = get_password_store()
    cred = store.get_credentials("openrouter.ai")
    if cred:
        print(cred.username, cred.password)

Environment variables:
    NLP2CMD_PASSWORD_BACKEND=firefox|keepassxc|bitwarden|env|auto (default: auto)
    NLP2CMD_KEEPASSXC_DB=/path/to/db.kdbx
    NLP2CMD_KEEPASSXC_KEYFILE=/path/to/keyfile (optional)
    NLP2CMD_BITWARDEN_SESSION=<session_key> (from `bw unlock`)
"""

from __future__ import annotations

import ctypes
import ctypes.util
import json
import logging
import os
import shutil
import sqlite3
import subprocess
import tempfile
from base64 import b64decode
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

log = logging.getLogger("nlp2cmd.password_store")
from nlp2cmd.automation.credential import Credential

class BitwardenReader:
    """Read passwords from Bitwarden via CLI.

    Requirements:
    - bw CLI installed (npm install -g @bitwarden/cli)
    - Session key set via NLP2CMD_BITWARDEN_SESSION or BW_SESSION
    - Or: bw unlock (interactive) to get session key

    Bitwarden can import passwords from Firefox and Chrome via:
    - Tools → Import Data → Firefox/Chrome
    """

    def __init__(self, session: Optional[str] = None):
        self._session = session or os.environ.get(
            "NLP2CMD_BITWARDEN_SESSION",
            os.environ.get("BW_SESSION", ""),
        )

    def available(self) -> bool:
        """Check if bw CLI is available and session is active."""
        return bool(shutil.which("bw") and self._session)

    def search(self, domain: str) -> list[Credential]:
        """Search Bitwarden for entries matching a domain."""
        if not self.available():
            return []

        env = os.environ.copy()
        env["BW_SESSION"] = self._session

        try:
            proc = subprocess.run(
                ["bw", "list", "items", "--search", domain],
                capture_output=True,
                text=True,
                timeout=15,
                env=env,
            )
            if proc.returncode != 0:
                log.warning("bw search failed: %s", proc.stderr.strip())
                return []

            items = json.loads(proc.stdout)
        except Exception as e:
            log.warning("Bitwarden CLI error: %s", e)
            return []

        credentials: list[Credential] = []
        for item in items:
            login = item.get("login", {})
            if not login:
                continue

            username = login.get("username", "")
            password = login.get("password", "")
            uris = login.get("uris", [])
            url = uris[0].get("uri", "") if uris else ""

            if not (username or password):
                continue

            try:
                hostname = urlparse(url).hostname or url
            except Exception:
                hostname = url

            credentials.append(Credential(
                url=url,
                hostname=hostname,
                username=username,
                password=password,
                source="bitwarden",
            ))

        log.info("Found %d Bitwarden credentials for '%s'", len(credentials), domain)
        return credentials
