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


# ═══════════════════════════════════════════════════════════════════
# Backend 1: Firefox Password Reader (NSS decryption)
# ═══════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════
# Backend 2: KeePassXC CLI
# ═══════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════
# Backend 3: Bitwarden CLI
# ═══════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════
# Backend 4: Environment Variables
# ═══════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════
# Session Password Store — Combines All Backends
# ═══════════════════════════════════════════════════════════════════

class SessionPasswordStore:
    """Multi-backend password store with in-memory session cache.

    Priority order (configurable via NLP2CMD_PASSWORD_BACKEND):
    1. Environment variables (.env) — always checked first
    2. Firefox saved passwords — if libnss3 available
    3. KeePassXC CLI — if installed and DB configured
    4. Bitwarden CLI — if installed and session active

    Credentials are cached in memory for the session duration.
    """

    def __init__(self, backend: Optional[str] = None):
        self._backend = backend or os.environ.get("NLP2CMD_PASSWORD_BACKEND", "auto")
        self._cache: dict[str, Credential] = {}
        self._all_loaded = False
        self._firefox_reader: Optional[FirefoxPasswordReader] = None
        self._keepassxc_reader: Optional[KeePassXCReader] = None
        self._bitwarden_reader: Optional[BitwardenReader] = None
        self._env_reader = EnvPasswordReader()

    def _ensure_loaded(self) -> None:
        """Lazily load all credentials from configured backends."""
        if self._all_loaded:
            return
        self._all_loaded = True

        backend = self._backend.lower()

        # Always load env vars
        # (individual lookups, not bulk — done in get_credentials)

        if backend in ("auto", "firefox"):
            try:
                self._firefox_reader = FirefoxPasswordReader()
                creds = self._firefox_reader.read_passwords()
                for c in creds:
                    key = f"{c.hostname}:{c.username}".lower()
                    if key not in self._cache:
                        self._cache[key] = c
                if creds:
                    log.info("Loaded %d Firefox passwords into session store", len(creds))
            except Exception as e:
                log.debug("Firefox password reader failed: %s", e)

        if backend in ("auto", "keepassxc"):
            try:
                self._keepassxc_reader = KeePassXCReader()
                if self._keepassxc_reader.available():
                    # KeePassXC requires master password — we don't bulk-load
                    # Instead, search on demand in get_credentials
                    log.info("KeePassXC available for on-demand lookups")
            except Exception as e:
                log.debug("KeePassXC reader init failed: %s", e)

        if backend in ("auto", "bitwarden"):
            try:
                self._bitwarden_reader = BitwardenReader()
                if self._bitwarden_reader.available():
                    log.info("Bitwarden CLI available for on-demand lookups")
            except Exception as e:
                log.debug("Bitwarden reader init failed: %s", e)

    def get_credentials(self, domain: str) -> Optional[Credential]:
        """Get credentials for a domain. Tries all backends in priority order.

        Args:
            domain: Domain name or URL (e.g. "openrouter.ai", "https://huggingface.co")

        Returns:
            Credential if found, None otherwise.
        """
        # Normalize domain
        domain_lower = domain.lower().strip()
        try:
            parsed = urlparse(domain_lower if "://" in domain_lower else f"https://{domain_lower}")
            hostname = parsed.hostname or domain_lower
        except Exception:
            hostname = domain_lower

        # 1. Check env vars first (fastest, highest priority)
        env_cred = self._env_reader.get_credentials(hostname)
        if env_cred and (env_cred.username or env_cred.password):
            log.info("Found credentials for %s in environment", hostname)
            return env_cred

        # 2. Check session cache (pre-loaded from Firefox)
        self._ensure_loaded()
        for key, cred in self._cache.items():
            if cred.matches_domain(hostname):
                log.info("Found cached credentials for %s (source: %s)", hostname, cred.source)
                return cred

        # 3. On-demand KeePassXC search
        if self._keepassxc_reader and self._keepassxc_reader.available():
            try:
                results = self._keepassxc_reader.search(hostname)
                if results:
                    cred = results[0]
                    # Cache for future lookups
                    self._cache[f"{cred.hostname}:{cred.username}".lower()] = cred
                    log.info("Found credentials for %s in KeePassXC", hostname)
                    return cred
            except Exception as e:
                log.debug("KeePassXC search failed: %s", e)

        # 4. On-demand Bitwarden search
        if self._bitwarden_reader and self._bitwarden_reader.available():
            try:
                results = self._bitwarden_reader.search(hostname)
                if results:
                    cred = results[0]
                    self._cache[f"{cred.hostname}:{cred.username}".lower()] = cred
                    log.info("Found credentials for %s in Bitwarden", hostname)
                    return cred
            except Exception as e:
                log.debug("Bitwarden search failed: %s", e)

        log.info("No credentials found for %s in any backend", hostname)
        return None

    def get_all_for_domain(self, domain: str) -> list[Credential]:
        """Get ALL credentials matching a domain (not just first match)."""
        self._ensure_loaded()

        hostname = domain.lower().strip()
        try:
            parsed = urlparse(hostname if "://" in hostname else f"https://{hostname}")
            hostname = parsed.hostname or hostname
        except Exception:
            pass

        results: list[Credential] = []

        # Env
        env_cred = self._env_reader.get_credentials(hostname)
        if env_cred:
            results.append(env_cred)

        # Cache (Firefox)
        for cred in self._cache.values():
            if cred.matches_domain(hostname):
                results.append(cred)

        return results

    def list_backends(self) -> dict[str, bool]:
        """List available password backends and their status."""
        self._ensure_loaded()
        return {
            "env": True,  # Always available
            "firefox": self._firefox_reader is not None and bool(self._cache),
            "keepassxc": self._keepassxc_reader is not None and self._keepassxc_reader.available(),
            "bitwarden": self._bitwarden_reader is not None and self._bitwarden_reader.available(),
        }

    @property
    def cached_count(self) -> int:
        """Number of credentials in session cache."""
        return len(self._cache)

    def diagnose_providers(
        self,
        providers: Optional[dict[str, dict[str, Any]]] = None,
    ) -> list[dict[str, Any]]:
        """Check credential availability for known API providers.

        Returns a list of dicts with provider status info, sorted by availability.
        """
        if providers is None:
            try:
                from nlp2cmd.automation.service_configs import KNOWN_SERVICES
                providers = KNOWN_SERVICES
            except ImportError:
                providers = {}

        results: list[dict[str, Any]] = []
        for svc_name, svc_config in sorted(providers.items()):
            env_var = svc_config.get("env_var", "")
            base_url = svc_config.get("base_url", "")
            keys_url = svc_config.get("keys_url", "")

            has_api_key = bool(os.environ.get(env_var, ""))
            cred = self.get_credentials(svc_name)

            has_login = bool(cred and cred.username and cred.password)
            has_user_only = bool(cred and cred.username and not cred.password)

            can_auto_login = has_login
            can_extract_key = has_api_key or has_login

            results.append({
                "service": svc_name,
                "base_url": base_url,
                "keys_url": keys_url,
                "env_var": env_var,
                "has_api_key": has_api_key,
                "has_login": has_login,
                "has_user_only": has_user_only,
                "login_source": cred.source if cred else None,
                "login_user": cred.username if cred else None,
                "can_auto_login": can_auto_login,
                "can_extract_key": can_extract_key,
            })

        # Sort: fully available first, then partial, then none
        results.sort(key=lambda r: (
            -(2 if r["has_api_key"] else 0)
            - (1 if r["has_login"] else 0)
        ))
        return results

    def print_diagnosis(self, *, verbose: bool = False) -> None:
        """Print a human-readable credential diagnosis to console."""
        from rich.console import Console
        from rich.table import Table

        console = Console()
        self._ensure_loaded()

        # Backends table
        backends = self.list_backends()
        console.print("\n[bold]🔐 Password Store — Backends[/bold]")
        for name, active in backends.items():
            icon = "[green]✓[/green]" if active else "[dim]✗[/dim]"
            extra = ""
            if name == "firefox" and active:
                extra = f" ({self.cached_count} haseł)"
            elif name == "keepassxc" and not active:
                extra = " [dim](ustaw NLP2CMD_KEEPASSXC_DB)[/dim]"
            elif name == "bitwarden" and not active:
                extra = " [dim](ustaw BW_SESSION)[/dim]"
            console.print(f"  {icon} {name}{extra}")

        # Provider table
        results = self.diagnose_providers()
        table = Table(title="\n🌐 API Provider Credentials", show_lines=False)
        table.add_column("Status", width=3)
        table.add_column("Provider", style="bold")
        table.add_column("API Key")
        table.add_column("Login (auto)")
        table.add_column("Source")

        for r in results:
            if r["has_api_key"] and r["has_login"]:
                status = "🟢"
            elif r["has_api_key"] or r["has_login"]:
                status = "🟡"
            else:
                status = "🔴"

            key_col = f"[green]✓ ${r['env_var']}[/green]" if r["has_api_key"] else "[dim]—[/dim]"

            if r["has_login"]:
                user_short = (r["login_user"] or "")[:25]
                login_col = f"[green]✓ {user_short}[/green]"
            elif r["has_user_only"]:
                user_short = (r["login_user"] or "")[:25]
                login_col = f"[yellow]½ {user_short} (no pass)[/yellow]"
            else:
                login_col = "[dim]—[/dim]"

            source_col = r["login_source"] or "[dim]—[/dim]"

            table.add_row(status, r["service"], key_col, login_col, source_col)

        console.print(table)

        # Summary
        total = len(results)
        full = sum(1 for r in results if r["has_api_key"] and r["has_login"])
        partial = sum(1 for r in results if (r["has_api_key"] or r["has_login"]) and not (r["has_api_key"] and r["has_login"]))
        none_ = sum(1 for r in results if not r["has_api_key"] and not r["has_login"])

        console.print(f"\n  [bold]Podsumowanie:[/bold] {full}🟢 {partial}🟡 {none_}🔴 z {total} providerów")

        # Actionable suggestions
        if none_ > 0:
            no_cred = [r["service"] for r in results if not r["has_api_key"] and not r["has_login"]]
            console.print(f"  [dim]Brak danych: {', '.join(no_cred)}[/dim]")
            console.print(f"  [dim]Tip: Zaloguj się na te serwisy w Firefox, aby nlp2cmd mógł użyć auto-login.[/dim]")

        if verbose:
            console.print(f"\n  [dim]Łącznie haseł w cache: {self.cached_count}[/dim]")
            console.print(f"  [dim]Konfiguracja: NLP2CMD_PASSWORD_BACKEND={self._backend}[/dim]")


# ═══════════════════════════════════════════════════════════════════
# Module-level singleton
# ═══════════════════════════════════════════════════════════════════

_store: Optional[SessionPasswordStore] = None


def get_password_store() -> SessionPasswordStore:
    """Get the singleton password store instance."""
    global _store
    if _store is None:
        _store = SessionPasswordStore()
    return _store
