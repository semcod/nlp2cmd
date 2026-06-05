# Credential - extracted from password_store.py
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


@dataclass
class Credential:
    """Single credential entry."""
    url: str
    hostname: str
    username: str
    password: str
    source: str = ""  # "firefox", "keepassxc", "bitwarden", "env"

    def matches_domain(self, domain: str) -> bool:
        """Check if this credential matches a domain (fuzzy)."""
        domain = domain.lower().strip()
        hostname = self.hostname.lower()
        url_lower = self.url.lower()
        return (
            domain in hostname
            or domain in url_lower
            or hostname.endswith(domain)
            or domain.endswith(hostname.lstrip("."))
        )
