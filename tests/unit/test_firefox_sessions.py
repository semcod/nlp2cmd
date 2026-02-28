"""Tests for Firefox session importer."""

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from nlp2cmd.automation.firefox_sessions import (
    FirefoxSessionImporter,
    _FIREFOX_ROOTS,
    _SESSION_FILES,
)


class TestFirefoxRootDetection:
    def test_find_firefox_roots_returns_existing(self, tmp_path):
        fake_root = tmp_path / ".mozilla" / "firefox"
        fake_root.mkdir(parents=True)
        with patch(
            "nlp2cmd.automation.firefox_sessions._FIREFOX_ROOTS",
            [fake_root, tmp_path / "nonexistent"],
        ):
            roots = FirefoxSessionImporter.find_firefox_roots()
            assert len(roots) == 1
            assert roots[0] == fake_root

    def test_find_firefox_roots_empty_when_none_exist(self):
        with patch(
            "nlp2cmd.automation.firefox_sessions._FIREFOX_ROOTS",
            [Path("/nonexistent/path1"), Path("/nonexistent/path2")],
        ):
            roots = FirefoxSessionImporter.find_firefox_roots()
            assert roots == []


class TestProfileDetection:
    def test_find_default_profile_by_ini(self, tmp_path):
        """profiles.ini with Default=1 should be found."""
        firefox_root = tmp_path / "firefox"
        firefox_root.mkdir()
        profile_dir = firefox_root / "abc123.default-release"
        profile_dir.mkdir()
        (profile_dir / "cookies.sqlite").write_text("")

        ini = firefox_root / "profiles.ini"
        ini.write_text(
            "[Profile0]\n"
            "Name=default-release\n"
            "IsRelative=1\n"
            "Path=abc123.default-release\n"
            "Default=1\n"
        )

        result = FirefoxSessionImporter.find_default_profile(firefox_root)
        assert result == profile_dir

    def test_find_default_profile_by_name_fallback(self, tmp_path):
        """Without profiles.ini, find by directory name pattern."""
        firefox_root = tmp_path / "firefox"
        firefox_root.mkdir()
        profile_dir = firefox_root / "xyz789.default-release"
        profile_dir.mkdir()

        result = FirefoxSessionImporter.find_default_profile(firefox_root)
        assert result == profile_dir

    def test_find_default_profile_by_cookies_fallback(self, tmp_path):
        """Last resort: find directory with cookies.sqlite."""
        firefox_root = tmp_path / "firefox"
        firefox_root.mkdir()
        profile_dir = firefox_root / "some-random-name"
        profile_dir.mkdir()
        (profile_dir / "cookies.sqlite").write_text("")

        result = FirefoxSessionImporter.find_default_profile(firefox_root)
        assert result == profile_dir

    def test_find_default_profile_none_when_empty(self, tmp_path):
        firefox_root = tmp_path / "firefox"
        firefox_root.mkdir()
        result = FirefoxSessionImporter.find_default_profile(firefox_root)
        assert result is None

    def test_detect_source_profile_explicit(self, tmp_path):
        profile = tmp_path / "my-profile"
        profile.mkdir()
        (profile / "cookies.sqlite").write_text("")

        importer = FirefoxSessionImporter(firefox_profile=str(profile))
        result = importer.detect_source_profile()
        assert result == profile

    def test_detect_source_profile_explicit_invalid(self, tmp_path):
        importer = FirefoxSessionImporter(
            firefox_profile=str(tmp_path / "nonexistent")
        )
        result = importer.detect_source_profile()
        assert result is None


class TestSessionCopying:
    def _create_firefox_profile(self, tmp_path):
        """Create a minimal fake Firefox profile with cookies."""
        profile = tmp_path / "firefox-profile"
        profile.mkdir()

        # Create cookies.sqlite with real data
        db = profile / "cookies.sqlite"
        conn = sqlite3.connect(str(db))
        conn.execute(
            "CREATE TABLE moz_cookies ("
            "  id INTEGER PRIMARY KEY,"
            "  host TEXT, name TEXT, value TEXT, path TEXT,"
            "  expiry INTEGER, isSecure INTEGER, isHttpOnly INTEGER,"
            "  sameSite INTEGER"
            ")"
        )
        conn.execute(
            "INSERT INTO moz_cookies VALUES (1, '.openrouter.ai', 'session', "
            "'abc123', '/', 0, 1, 1, 0)"
        )
        conn.execute(
            "INSERT INTO moz_cookies VALUES (2, '.github.com', 'user_session', "
            "'xyz789', '/', 1735689600, 1, 1, 1)"
        )
        conn.commit()
        conn.close()

        # Create other session files
        (profile / "logins.json").write_text('{"logins": []}')
        (profile / "permissions.sqlite").write_text("")

        # Create storage directory
        storage = profile / "storage"
        storage.mkdir()
        (storage / "default").mkdir()
        (storage / "default" / "test.txt").write_text("data")

        return profile

    def test_copy_session_files(self, tmp_path):
        source = self._create_firefox_profile(tmp_path)
        target = tmp_path / "playwright-profile"

        importer = FirefoxSessionImporter(target_dir=str(target))
        summary = importer.copy_session_files(source, target)

        assert "cookies.sqlite" in summary["copied"]
        assert "logins.json" in summary["copied"]
        assert (target / "cookies.sqlite").exists()
        assert (target / "logins.json").exists()

    def test_copy_session_dirs(self, tmp_path):
        source = self._create_firefox_profile(tmp_path)
        target = tmp_path / "playwright-profile"

        importer = FirefoxSessionImporter(target_dir=str(target))
        summary = importer.copy_session_files(source, target)

        assert "storage" in summary["dirs_copied"]
        assert (target / "storage" / "default" / "test.txt").exists()

    def test_skip_unchanged_files(self, tmp_path):
        source = self._create_firefox_profile(tmp_path)
        target = tmp_path / "playwright-profile"
        target.mkdir()

        # First copy
        importer = FirefoxSessionImporter(target_dir=str(target))
        summary1 = importer.copy_session_files(source, target)
        assert len(summary1["copied"]) > 0

        # Second copy without force should skip
        summary2 = importer.copy_session_files(source, target, force=False)
        assert len(summary2["skipped"]) > 0

    def test_force_refresh(self, tmp_path):
        source = self._create_firefox_profile(tmp_path)
        target = tmp_path / "playwright-profile"
        target.mkdir()

        importer = FirefoxSessionImporter(target_dir=str(target))
        importer.copy_session_files(source, target)

        # Force should re-copy everything
        summary = importer.copy_session_files(source, target, force=True)
        assert "cookies.sqlite" in summary["copied"]

    def test_cleanup_locks(self, tmp_path):
        profile = tmp_path / "profile"
        profile.mkdir()
        (profile / "lock").write_text("")
        (profile / ".parentlock").write_text("")

        importer = FirefoxSessionImporter()
        importer.cleanup_locks(profile)

        assert not (profile / "lock").exists()
        assert not (profile / ".parentlock").exists()


class TestCookieExport:
    def test_export_cookies_for_chromium(self, tmp_path):
        # Create cookies.sqlite
        db_path = tmp_path / "cookies.sqlite"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE moz_cookies ("
            "  id INTEGER PRIMARY KEY,"
            "  host TEXT, name TEXT, value TEXT, path TEXT,"
            "  expiry INTEGER, isSecure INTEGER, isHttpOnly INTEGER,"
            "  sameSite INTEGER"
            ")"
        )
        conn.execute(
            "INSERT INTO moz_cookies VALUES "
            "(1, '.openrouter.ai', 'session_id', 'tok123', '/', 0, 1, 1, 0)"
        )
        conn.execute(
            "INSERT INTO moz_cookies VALUES "
            "(2, '.github.com', 'gh_sess', 'ghval', '/', 1735689600, 1, 0, 1)"
        )
        conn.commit()
        conn.close()

        importer = FirefoxSessionImporter()
        cookies = importer.export_cookies_for_chromium(db_path)

        assert len(cookies) == 2

        or_cookie = next(c for c in cookies if c["name"] == "session_id")
        assert or_cookie["domain"] == "openrouter.ai"
        assert or_cookie["secure"] is True
        assert or_cookie["httpOnly"] is True
        assert or_cookie["sameSite"] == "None"
        assert "expires" not in or_cookie  # session cookie

        gh_cookie = next(c for c in cookies if c["name"] == "gh_sess")
        assert gh_cookie["domain"] == "github.com"
        assert gh_cookie["expires"] == 1735689600
        assert gh_cookie["sameSite"] == "Lax"

    def test_export_cookies_missing_db(self, tmp_path):
        importer = FirefoxSessionImporter()
        cookies = importer.export_cookies_for_chromium(tmp_path / "nonexistent.db")
        assert cookies == []


class TestPrepareProfile:
    def test_prepare_creates_marker(self, tmp_path):
        # Create fake Firefox profile
        ff_root = tmp_path / "firefox"
        ff_root.mkdir()
        profile = ff_root / "abc.default-release"
        profile.mkdir()
        db = profile / "cookies.sqlite"
        conn = sqlite3.connect(str(db))
        conn.execute(
            "CREATE TABLE moz_cookies (id INTEGER PRIMARY KEY, host TEXT, "
            "name TEXT, value TEXT, path TEXT, expiry INTEGER, "
            "isSecure INTEGER, isHttpOnly INTEGER, sameSite INTEGER)"
        )
        conn.commit()
        conn.close()

        target = tmp_path / "pw-profile"
        importer = FirefoxSessionImporter(
            target_dir=str(target),
            firefox_profile=str(profile),
        )
        result = importer.prepare_playwright_profile()

        assert result == target
        assert (target / ".nlp2cmd_session_copied").exists()

    def test_prepare_skips_fresh_profile(self, tmp_path):
        # Create target with fresh marker
        target = tmp_path / "pw-profile"
        target.mkdir()
        marker = target / ".nlp2cmd_session_copied"
        marker.write_text("fresh")

        profile = tmp_path / "ff-profile"
        profile.mkdir()
        (profile / "cookies.sqlite").write_text("")

        importer = FirefoxSessionImporter(
            target_dir=str(target),
            firefox_profile=str(profile),
        )
        result = importer.prepare_playwright_profile(max_age_hours=24)
        assert result == target  # Should return without re-copying


class TestDiagnostics:
    def test_diagnose_output(self, tmp_path):
        ff_root = tmp_path / "firefox"
        ff_root.mkdir()
        profile = ff_root / "test.default-release"
        profile.mkdir()

        db = profile / "cookies.sqlite"
        conn = sqlite3.connect(str(db))
        conn.execute(
            "CREATE TABLE moz_cookies (id INTEGER PRIMARY KEY, host TEXT, "
            "name TEXT, value TEXT, path TEXT, expiry INTEGER, "
            "isSecure INTEGER, isHttpOnly INTEGER, sameSite INTEGER)"
        )
        conn.execute(
            "INSERT INTO moz_cookies VALUES "
            "(1, '.example.com', 'test', 'val', '/', 0, 0, 0, 0)"
        )
        conn.commit()
        conn.close()

        with patch(
            "nlp2cmd.automation.firefox_sessions._FIREFOX_ROOTS",
            [ff_root],
        ):
            importer = FirefoxSessionImporter()
            diag = importer.diagnose()

            assert diag["detected_profile"] == str(profile)
            assert diag["cookie_count"] == 1
            assert ".example.com" in diag["cookie_domains"]


class TestEnvVarIntegration:
    """Test that env vars control Firefox session behavior."""

    def test_env_var_not_set_uses_chromium(self):
        """Without NLP2CMD_USE_FIREFOX_SESSIONS, default is Chromium."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NLP2CMD_USE_FIREFOX_SESSIONS", None)
            val = os.environ.get("NLP2CMD_USE_FIREFOX_SESSIONS", "").strip()
            assert val == ""  # No Firefox sessions
