# FirefoxPasswordReader - extracted from password_store.py
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

@dataclass
class FirefoxPasswordReader:
    """Read saved passwords from Firefox profile using NSS library.

    Firefox stores passwords in logins.json, encrypted with keys from key4.db.
    We use libnss3 (Mozilla NSS) to decrypt them — same library Firefox uses.

    Requirements:
    - libnss3 installed (sudo apt install libnss3 — usually already present)
    - Firefox profile with saved passwords
    - No master password set (or master password provided)
    """

    def __init__(self, profile_path: Optional[Path] = None):
        self._profile_path = profile_path
        self._nss_initialized = False
        self._nss_lib = None

    def _find_profile(self) -> Optional[Path]:
        """Find Firefox profile using same logic as firefox_sessions.py."""
        if self._profile_path and self._profile_path.is_dir():
            return self._profile_path

        try:
            from nlp2cmd.automation.firefox_sessions import FirefoxSessionImporter
            importer = FirefoxSessionImporter()
            return importer.detect_source_profile()
        except ImportError:
            pass

        # Manual fallback
        from nlp2cmd.automation.firefox_sessions import _FIREFOX_ROOTS
        import configparser
        for root in _FIREFOX_ROOTS:
            if not root.is_dir():
                continue
            ini = root / "profiles.ini"
            if ini.exists():
                config = configparser.ConfigParser()
                try:
                    config.read(str(ini))
                    for section in config.sections():
                        if config.get(section, "Default", fallback="0") == "1":
                            path_val = config.get(section, "Path", fallback="")
                            is_rel = config.get(section, "IsRelative", fallback="1") == "1"
                            if path_val:
                                p = (root / path_val) if is_rel else Path(path_val)
                                if p.is_dir():
                                    return p
                except Exception:
                    pass
            for d in sorted(root.iterdir()):
                if d.is_dir() and (d / "logins.json").exists():
                    return d
        return None

    def _init_nss(self, profile_dir: Path) -> bool:
        """Initialize Mozilla NSS library for decryption."""
        if self._nss_initialized:
            return True

        # Find libnss3
        nss_name = ctypes.util.find_library("nss3")
        if not nss_name:
            # Try common paths
            for candidate in [
                "/usr/lib/x86_64-linux-gnu/libnss3.so",
                "/usr/lib/libnss3.so",
                "/usr/lib64/libnss3.so",
                # Snap Firefox ships its own NSS
                "/snap/firefox/current/usr/lib/x86_64-linux-gnu/libnss3.so",
            ]:
                if Path(candidate).exists():
                    nss_name = candidate
                    break

        if not nss_name:
            log.warning("libnss3 not found. Install: sudo apt install libnss3")
            return False

        try:
            self._nss_lib = ctypes.CDLL(nss_name)
        except OSError as e:
            log.warning("Failed to load libnss3: %s", e)
            return False

        # NSS_Init with profile directory (needed to access key4.db)
        # We need to copy key4.db + cert9.db to a temp dir (Firefox may have them locked)
        tmp_dir = Path(tempfile.mkdtemp(prefix="nlp2cmd_nss_"))
        for f in ("key4.db", "cert9.db", "logins.json"):
            src = profile_dir / f
            if src.exists():
                shutil.copy2(str(src), str(tmp_dir / f))
            # Also copy WAL/SHM files for SQLite
            for ext in ("-wal", "-shm"):
                wal = profile_dir / (f + ext)
                if wal.exists():
                    shutil.copy2(str(wal), str(tmp_dir / (f + ext)))

        config_dir = f"sql:{tmp_dir}"
        rc = self._nss_lib.NSS_Init(config_dir.encode("utf-8"))
        if rc != 0:
            log.warning("NSS_Init failed (rc=%d). Profile may have a master password.", rc)
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return False

        self._nss_initialized = True
        self._tmp_dir = tmp_dir
        return True

    def _decrypt_field(self, encrypted_b64: str) -> str:
        """Decrypt a single NSS-encrypted field (base64 encoded)."""
        if not self._nss_lib or not encrypted_b64:
            return ""

        class SECItem(ctypes.Structure):
            _fields_ = [
                ("type", ctypes.c_uint),
                ("data", ctypes.c_void_p),
                ("len", ctypes.c_uint),
            ]

        try:
            encrypted_bytes = b64decode(encrypted_b64)
        except Exception:
            return ""

        input_item = SECItem()
        input_item.type = 0
        input_item.data = ctypes.cast(
            ctypes.create_string_buffer(encrypted_bytes, len(encrypted_bytes)),
            ctypes.c_void_p,
        )
        input_item.len = len(encrypted_bytes)

        output_item = SECItem()

        rc = self._nss_lib.PK11SDR_Decrypt(
            ctypes.byref(input_item),
            ctypes.byref(output_item),
            None,
        )

        if rc != 0:
            return ""

        try:
            decrypted = ctypes.string_at(output_item.data, output_item.len)
            return decrypted.decode("utf-8", errors="replace")
        finally:
            # Free the decrypted buffer
            try:
                self._nss_lib.SECITEM_FreeItem(ctypes.byref(output_item), 0)
            except Exception:
                pass

    def _shutdown_nss(self):
        """Clean up NSS resources."""
        if self._nss_initialized and self._nss_lib:
            try:
                self._nss_lib.NSS_Shutdown()
            except Exception:
                pass
            self._nss_initialized = False
        if hasattr(self, "_tmp_dir"):
            shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def read_passwords(self) -> list[Credential]:
        """Read all saved passwords from Firefox profile."""
        profile = self._find_profile()
        if not profile:
            log.info("No Firefox profile found")
            return []

        logins_file = profile / "logins.json"
        if not logins_file.exists():
            log.info("No logins.json in Firefox profile")
            return []

        if not self._init_nss(profile):
            log.info("NSS init failed — cannot decrypt Firefox passwords")
            return []

        try:
            data = json.loads(logins_file.read_text(encoding="utf-8"))
            logins = data.get("logins", [])
        except Exception as e:
            log.warning("Failed to read logins.json: %s", e)
            self._shutdown_nss()
            return []

        credentials: list[Credential] = []
        for login in logins:
            hostname = login.get("hostname", "")
            encrypted_user = login.get("encryptedUsername", "")
            encrypted_pass = login.get("encryptedPassword", "")

            username = self._decrypt_field(encrypted_user)
            password = self._decrypt_field(encrypted_pass)

            if username or password:
                # Extract clean hostname
                try:
                    parsed = urlparse(hostname)
                    clean_host = parsed.hostname or hostname
                except Exception:
                    clean_host = hostname

                credentials.append(Credential(
                    url=hostname,
                    hostname=clean_host,
                    username=username,
                    password=password,
                    source="firefox",
                ))

        self._shutdown_nss()
        log.info("Read %d credentials from Firefox", len(credentials))
        return credentials
