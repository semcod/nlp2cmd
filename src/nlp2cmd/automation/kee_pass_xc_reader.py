# KeePassXCReader - extracted from password_store.py
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

class KeePassXCReader:
    """Read passwords from KeePassXC database via CLI.

    Requirements:
    - keepassxc-cli installed (sudo apt install keepassxc)
    - Database path set via NLP2CMD_KEEPASSXC_DB env var
    - Database unlocked (password provided via stdin or keyfile)

    KeePassXC can import passwords from Firefox and Chrome via:
    - Database → Import → Firefox/Chrome
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        keyfile: Optional[str] = None,
    ):
        self._db_path = db_path or os.environ.get("NLP2CMD_KEEPASSXC_DB", "")
        self._keyfile = keyfile or os.environ.get("NLP2CMD_KEEPASSXC_KEYFILE", "")

    def available(self) -> bool:
        """Check if keepassxc-cli is available and database is configured."""
        return bool(
            shutil.which("keepassxc-cli")
            and self._db_path
            and Path(self._db_path).exists()
        )

    def read_passwords(self, master_password: str = "") -> list[Credential]:
        """Read all entries from KeePassXC database."""
        if not self.available():
            return []

        cmd = ["keepassxc-cli", "ls", "-R", "-f", self._db_path]
        if self._keyfile:
            cmd.extend(["--key-file", self._keyfile])

        try:
            proc = subprocess.run(
                cmd,
                input=master_password + "\n",
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode != 0:
                log.warning("keepassxc-cli ls failed: %s", proc.stderr.strip())
                return []
        except Exception as e:
            log.warning("keepassxc-cli error: %s", e)
            return []

        # Parse entry paths
        entries = [
            line.strip() for line in proc.stdout.strip().split("\n")
            if line.strip() and not line.strip().endswith("/")
        ]

        credentials: list[Credential] = []
        for entry_path in entries:
            cred = self._read_entry(entry_path, master_password)
            if cred:
                credentials.append(cred)

        log.info("Read %d credentials from KeePassXC", len(credentials))
        return credentials

    def search(self, domain: str, master_password: str = "") -> list[Credential]:
        """Search KeePassXC for entries matching a domain."""
        if not self.available():
            return []

        cmd = ["keepassxc-cli", "search", self._db_path, domain]
        if self._keyfile:
            cmd.extend(["--key-file", self._keyfile])

        try:
            proc = subprocess.run(
                cmd,
                input=master_password + "\n",
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode != 0:
                return []
        except Exception:
            return []

        entries = [
            line.strip() for line in proc.stdout.strip().split("\n")
            if line.strip()
        ]

        credentials: list[Credential] = []
        for entry_path in entries:
            cred = self._read_entry(entry_path, master_password)
            if cred:
                credentials.append(cred)
        return credentials

    def _read_entry(self, entry_path: str, master_password: str) -> Optional[Credential]:
        """Read a single entry from KeePassXC."""
        cmd = ["keepassxc-cli", "show", "-s", self._db_path, entry_path]
        if self._keyfile:
            cmd.extend(["--key-file", self._keyfile])

        try:
            proc = subprocess.run(
                cmd,
                input=master_password + "\n",
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode != 0:
                return None
        except Exception:
            return None

        fields: dict[str, str] = {}
        for line in proc.stdout.strip().split("\n"):
            if ": " in line:
                key, _, value = line.partition(": ")
                fields[key.strip().lower()] = value.strip()

        url = fields.get("url", "")
        username = fields.get("username", fields.get("user name", ""))
        password = fields.get("password", "")

        if not (username or password):
            return None

        try:
            hostname = urlparse(url).hostname or url
        except Exception:
            hostname = url

        return Credential(
            url=url,
            hostname=hostname,
            username=username,
            password=password,
            source="keepassxc",
        )
