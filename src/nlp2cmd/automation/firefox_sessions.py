"""
Firefox session importer for Playwright automation.

Copies cookies, localStorage, and session data from the user's local
Firefox profile into a Playwright-compatible profile directory, so that
automated browser tasks can access already-logged-in portals without
requiring complex login flows.

Supports:
- Standard Firefox on Ubuntu (~/.mozilla/firefox/)
- Snap Firefox on Ubuntu (~/snap/firefox/common/.mozilla/firefox/)
- Flatpak Firefox (~/.var/app/org.mozilla.firefox/.mozilla/firefox/)

Usage:
    from nlp2cmd.automation.firefox_sessions import FirefoxSessionImporter

    importer = FirefoxSessionImporter()
    profile_dir = importer.prepare_playwright_profile()
    # Use profile_dir as user_data_dir in Playwright launch_persistent_context
"""

from __future__ import annotations

import configparser
import logging
import os
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("nlp2cmd.firefox_sessions")

# Files that carry session/cookie state in a Firefox profile
_SESSION_FILES = [
    "cookies.sqlite",
    "cookies.sqlite-wal",
    "cookies.sqlite-shm",
    "webappsstore.sqlite",       # localStorage
    "webappsstore.sqlite-wal",
    "webappsstore.sqlite-shm",
    "permissions.sqlite",
    "content-prefs.sqlite",
    "formhistory.sqlite",
    "cert9.db",                  # SSL certificates
    "key4.db",                   # encrypted credentials
    "logins.json",               # saved passwords (encrypted)
    "sessionstore.jsonlz4",      # active session tabs
    "sessionCheckpoints.json",
    "storage.sqlite",
    "favicons.sqlite",
]

# Directories with per-site storage (localStorage, IndexedDB, etc.)
_SESSION_DIRS = [
    "storage",
    "sessionstore-backups",
]

# Known Firefox profile base paths on Linux
_FIREFOX_ROOTS = [
    Path.home() / ".mozilla" / "firefox",                              # Standard
    Path.home() / "snap" / "firefox" / "common" / ".mozilla" / "firefox",  # Snap
    Path.home() / ".var" / "app" / "org.mozilla.firefox" / ".mozilla" / "firefox",  # Flatpak
]


class FirefoxSessionImporter:
    """Import Firefox sessions into Playwright browser profiles.

    Finds the active Firefox profile, copies session-relevant files
    into a Playwright-compatible directory, and provides the path
    for use with launch_persistent_context().
    """

    def __init__(
        self,
        *,
        target_dir: Optional[str | Path] = None,
        firefox_profile: Optional[str | Path] = None,
        browser: str = "firefox",
    ) -> None:
        """
        Args:
            target_dir: Where to create the Playwright profile copy.
                        Defaults to ~/.nlp2cmd/firefox_playwright_profile
            firefox_profile: Explicit path to Firefox profile to copy from.
                            If None, auto-detects the default profile.
            browser: Which Playwright browser to target: "firefox" or "chromium".
                     Firefox profiles work directly with pw.firefox.
                     For Chromium, cookies are converted.
        """
        self._target_dir = Path(target_dir) if target_dir else (
            Path.home() / ".nlp2cmd" / "firefox_playwright_profile"
        )
        self._firefox_profile = Path(firefox_profile) if firefox_profile else None
        self._browser = browser
        self._source_profile: Optional[Path] = None

    @property
    def target_dir(self) -> Path:
        return self._target_dir

    @property
    def source_profile(self) -> Optional[Path]:
        return self._source_profile

    # ------------------------------------------------------------------
    # Profile detection
    # ------------------------------------------------------------------
    @staticmethod
    def find_firefox_roots() -> list[Path]:
        """Find all existing Firefox root directories on the system."""
        roots = []
        for root in _FIREFOX_ROOTS:
            if root.is_dir():
                roots.append(root)
        return roots

    @staticmethod
    def find_default_profile(firefox_root: Path) -> Optional[Path]:
        """Find the default-release profile in a Firefox root.

        Reads profiles.ini to find the profile marked as Default=1,
        or falls back to the first profile with 'default-release' in its name.
        """
        ini_path = firefox_root / "profiles.ini"
        if ini_path.exists():
            config = configparser.ConfigParser()
            try:
                config.read(str(ini_path))
                # Look for Default=1 profile
                for section in config.sections():
                    if config.get(section, "Default", fallback="0") == "1":
                        path_val = config.get(section, "Path", fallback="")
                        is_relative = config.get(section, "IsRelative", fallback="1") == "1"
                        if path_val:
                            if is_relative:
                                candidate = firefox_root / path_val
                            else:
                                candidate = Path(path_val)
                            if candidate.is_dir():
                                return candidate
            except Exception as e:
                log.warning("Failed to parse profiles.ini: %s", e)

        # Fallback: find *default-release* directory
        for d in sorted(firefox_root.iterdir()):
            if d.is_dir() and "default-release" in d.name:
                return d

        # Last resort: any directory with cookies.sqlite
        for d in sorted(firefox_root.iterdir()):
            if d.is_dir() and (d / "cookies.sqlite").exists():
                return d

        return None

    def detect_source_profile(self) -> Optional[Path]:
        """Auto-detect the Firefox profile to copy from."""
        if self._firefox_profile:
            p = Path(self._firefox_profile)
            if p.is_dir() and (p / "cookies.sqlite").exists():
                self._source_profile = p
                return p
            log.warning("Specified profile %s not found or has no cookies.sqlite", p)
            return None

        for root in self.find_firefox_roots():
            profile = self.find_default_profile(root)
            if profile:
                log.info("Detected Firefox profile: %s", profile)
                self._source_profile = profile
                return profile

        log.warning("No Firefox profile found in any standard location")
        return None

    # ------------------------------------------------------------------
    # Session copying
    # ------------------------------------------------------------------
    def copy_session_files(
        self,
        source: Path,
        target: Path,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        """Copy session-relevant files from Firefox profile to target.

        Args:
            source: Firefox profile directory
            target: Playwright profile directory
            force: If True, overwrite existing files. If False, skip if
                   target files are newer than source.

        Returns:
            Summary dict with copied/skipped/failed counts.
        """
        target.mkdir(parents=True, exist_ok=True)
        summary = {"copied": [], "skipped": [], "failed": [], "dirs_copied": []}

        for fname in _SESSION_FILES:
            src = source / fname
            dst = target / fname
            if not src.exists():
                continue
            try:
                if not force and dst.exists():
                    if dst.stat().st_mtime >= src.stat().st_mtime:
                        summary["skipped"].append(fname)
                        continue
                shutil.copy2(str(src), str(dst))
                summary["copied"].append(fname)
            except Exception as e:
                log.warning("Failed to copy %s: %s", fname, e)
                summary["failed"].append(fname)

        for dirname in _SESSION_DIRS:
            src_dir = source / dirname
            dst_dir = target / dirname
            if not src_dir.is_dir():
                continue
            try:
                if dst_dir.exists():
                    shutil.rmtree(str(dst_dir))
                shutil.copytree(str(src_dir), str(dst_dir))
                summary["dirs_copied"].append(dirname)
            except Exception as e:
                log.warning("Failed to copy directory %s: %s", dirname, e)
                summary["failed"].append(f"dir:{dirname}")

        return summary

    def cleanup_locks(self, profile_dir: Path) -> None:
        """Remove lock files that prevent Playwright from opening the profile."""
        for lock_file in ["lock", ".parentlock", "parent.lock"]:
            p = profile_dir / lock_file
            if p.exists():
                try:
                    p.unlink()
                    log.debug("Removed lock file: %s", p)
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Cookie export (for Chromium target)
    # ------------------------------------------------------------------
    def export_cookies_for_chromium(
        self,
        firefox_cookies_db: Path,
    ) -> list[dict[str, Any]]:
        """Read cookies from Firefox cookies.sqlite and return as dicts.

        These can be injected into a Chromium context via
        context.add_cookies(cookies).
        """
        if not firefox_cookies_db.exists():
            return []

        cookies = []
        try:
            conn = sqlite3.connect(str(firefox_cookies_db))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT host, name, value, path, expiry, isSecure, isHttpOnly, "
                "sameSite FROM moz_cookies"
            )
            for row in cursor:
                host = row["host"]
                # Playwright expects domain without leading dot for exact match
                domain = host.lstrip(".")

                same_site_map = {0: "None", 1: "Lax", 2: "Strict"}
                same_site = same_site_map.get(row["sameSite"], "None")

                cookie = {
                    "name": row["name"],
                    "value": row["value"],
                    "domain": domain,
                    "path": row["path"] or "/",
                    "secure": bool(row["isSecure"]),
                    "httpOnly": bool(row["isHttpOnly"]),
                    "sameSite": same_site,
                }
                # Only set expires if not a session cookie
                if row["expiry"] and row["expiry"] > 0:
                    cookie["expires"] = row["expiry"]

                cookies.append(cookie)

            conn.close()
        except Exception as e:
            log.warning("Failed to read Firefox cookies: %s", e)

        return cookies

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def prepare_playwright_profile(
        self,
        *,
        force_refresh: bool = False,
        max_age_hours: int = 24,
    ) -> Optional[Path]:
        """Prepare a Playwright profile with Firefox sessions.

        For Firefox target: copies entire session files.
        For Chromium target: exports cookies for injection via add_cookies().

        Args:
            force_refresh: Always re-copy even if profile exists.
            max_age_hours: Re-copy if existing profile is older than this.

        Returns:
            Path to the prepared profile directory, or None on failure.
        """
        source = self.detect_source_profile()
        if not source:
            log.error("Cannot prepare Playwright profile: no Firefox profile found")
            return None

        log.info(
            "Preparing Playwright %s profile from Firefox: %s → %s",
            self._browser, source, self._target_dir,
        )

        # Check if existing profile is fresh enough
        marker = self._target_dir / ".nlp2cmd_session_copied"
        if not force_refresh and marker.exists():
            age_hours = (time.time() - marker.stat().st_mtime) / 3600
            if age_hours < max_age_hours:
                log.info(
                    "Existing profile is %.1f hours old (max=%d), skipping re-copy",
                    age_hours, max_age_hours,
                )
                return self._target_dir

        # Copy session files
        summary = self.copy_session_files(source, self._target_dir, force=force_refresh)
        self.cleanup_locks(self._target_dir)

        # Write marker
        marker.write_text(
            f"copied_from={source}\n"
            f"timestamp={time.time()}\n"
            f"copied={summary['copied']}\n"
            f"browser={self._browser}\n"
        )

        log.info(
            "Session copy complete: %d files copied, %d skipped, %d failed, %d dirs",
            len(summary["copied"]),
            len(summary["skipped"]),
            len(summary["failed"]),
            len(summary["dirs_copied"]),
        )

        return self._target_dir

    def get_chromium_cookies(self) -> list[dict[str, Any]]:
        """Get Firefox cookies in Playwright Chromium format.

        Use with: context.add_cookies(importer.get_chromium_cookies())
        """
        source = self.detect_source_profile()
        if not source:
            return []
        cookies_db = source / "cookies.sqlite"
        return self.export_cookies_for_chromium(cookies_db)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------
    def diagnose(self) -> dict[str, Any]:
        """Return diagnostic info about Firefox profile detection."""
        result: dict[str, Any] = {
            "firefox_roots": [],
            "detected_profile": None,
            "session_files": {},
            "cookie_count": 0,
            "cookie_domains": [],
        }

        for root in _FIREFOX_ROOTS:
            entry = {"path": str(root), "exists": root.is_dir()}
            if root.is_dir():
                profiles = [d.name for d in root.iterdir() if d.is_dir()]
                entry["profiles"] = profiles
            result["firefox_roots"].append(entry)

        source = self.detect_source_profile()
        if source:
            result["detected_profile"] = str(source)
            for fname in _SESSION_FILES:
                f = source / fname
                result["session_files"][fname] = {
                    "exists": f.exists(),
                    "size": f.stat().st_size if f.exists() else 0,
                }

            # Count cookies
            cookies_db = source / "cookies.sqlite"
            if cookies_db.exists():
                try:
                    conn = sqlite3.connect(str(cookies_db))
                    count = conn.execute("SELECT COUNT(*) FROM moz_cookies").fetchone()[0]
                    domains = [
                        row[0] for row in conn.execute(
                            "SELECT DISTINCT host FROM moz_cookies ORDER BY host LIMIT 20"
                        )
                    ]
                    conn.close()
                    result["cookie_count"] = count
                    result["cookie_domains"] = domains
                except Exception as e:
                    result["cookie_error"] = str(e)

        return result
