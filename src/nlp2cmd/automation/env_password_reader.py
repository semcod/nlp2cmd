# EnvPasswordReader - extracted from password_store.py
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

class EnvPasswordReader:
    """Read credentials from environment variables and .env files.

    Convention:
    - {SERVICE}_EMAIL or {SERVICE}_USERNAME
    - {SERVICE}_PASSWORD
    - {SERVICE}_API_KEY

    Example:
    - OPENROUTER_EMAIL=user@example.com
    - OPENROUTER_PASSWORD=secret
    - HUGGINGFACE_USERNAME=myuser
    - HUGGINGFACE_PASSWORD=mypass
    """

    # Known service name → env var prefix mappings
    SERVICE_PREFIXES: dict[str, list[str]] = {
        "openrouter": ["OPENROUTER"],
        "anthropic": ["ANTHROPIC"],
        "openai": ["OPENAI"],
        "huggingface": ["HUGGINGFACE", "HF"],
        "github": ["GITHUB", "GH"],
        "groq": ["GROQ"],
        "mistral": ["MISTRAL"],
        "deepseek": ["DEEPSEEK"],
        "google": ["GOOGLE"],
    }

    def get_credentials(self, domain: str) -> Optional[Credential]:
        """Get credentials for a domain from environment variables."""
        # Load .env if python-dotenv available
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        # Determine service prefix from domain
        domain_lower = domain.lower()
        prefixes = []
        for svc, pfx_list in self.SERVICE_PREFIXES.items():
            if svc in domain_lower:
                prefixes.extend(pfx_list)

        # Also try domain-based prefix
        try:
            hostname = urlparse(domain).hostname or domain
            base = hostname.split(".")[0].upper()
            if base not in prefixes:
                prefixes.append(base)
        except Exception:
            pass

        for prefix in prefixes:
            username = (
                os.environ.get(f"{prefix}_EMAIL")
                or os.environ.get(f"{prefix}_USERNAME")
                or os.environ.get(f"{prefix}_USER")
                or ""
            )
            password = os.environ.get(f"{prefix}_PASSWORD", "")

            if username or password:
                return Credential(
                    url=domain,
                    hostname=domain,
                    username=username,
                    password=password,
                    source="env",
                )

        return None
