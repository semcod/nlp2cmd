# SessionPasswordStore - extracted from password_store.py
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
from nlp2cmd.automation.bitwarden_reader import BitwardenReader
from nlp2cmd.automation.credential import Credential
from nlp2cmd.automation.env_password_reader import EnvPasswordReader
from nlp2cmd.automation.firefox_password_reader import FirefoxPasswordReader
from nlp2cmd.automation.kee_pass_xc_reader import KeePassXCReader

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
