"""Re-exports from split password_store.py module."""

from typing import Optional

from nlp2cmd.automation.credential import Credential
from nlp2cmd.automation.firefox_password_reader import FirefoxPasswordReader
from nlp2cmd.automation.kee_pass_xc_reader import KeePassXCReader
from nlp2cmd.automation.bitwarden_reader import BitwardenReader
from nlp2cmd.automation.env_password_reader import EnvPasswordReader
from nlp2cmd.automation.session_password_store import SessionPasswordStore

__all__ = [
    "Credential",
    "FirefoxPasswordReader",
    "KeePassXCReader",
    "BitwardenReader",
    "EnvPasswordReader",
    "SessionPasswordStore",
    "get_password_store",
]



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
