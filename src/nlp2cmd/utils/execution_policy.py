"""Shell execution policy dataclass for safety controls."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from nlp2cmd.utils.data_files import find_data_file


@dataclass
class ShellExecutionPolicy:
    allowlist: set[str] = field(default_factory=set)
    blocked_regex: list[str] = field(
        default_factory=lambda: [
            r"\brm\s+-rf\s+/\b",
            r"\brm\s+-rf\s+/\*\b",
            r"\bmkfs\b",
            r"\bdd\s+if=/dev/zero\b",
            r":\(\)\{:\|:&\};:",
        ]
    )
    require_confirm_regex: list[str] = field(
        default_factory=lambda: [
            r"\brm\b",
            r"\brmdir\b",
            r"\bkill\b",
            r"\bkillall\b",
            r"\bshutdown\b",
            r"\breboot\b",
            r"\bsystemctl\s+stop\b",
            r"\bdocker\s+rm\b",
            r"\bdocker\s+rmi\b",
        ]
    )
    allow_sudo: bool = False
    allow_pipes: bool = False

    def load_from_data(self, path: str = "./data/shell_execution_policy.json") -> None:
        """Optionally load policy configuration from JSON in data/."""

        p = find_data_file(explicit_path=path, default_filename="shell_execution_policy.json")
        if not p:
            return

        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(raw, dict):
            return

        ar = raw.get("allowlist")
        if isinstance(ar, list):
            self.allowlist = {x.strip() for x in ar if isinstance(x, str) and x.strip()}

        br = raw.get("blocked_regex")
        if isinstance(br, list):
            self.blocked_regex = [x for x in br if isinstance(x, str) and x.strip()]

        rr = raw.get("require_confirm_regex")
        if isinstance(rr, list):
            self.require_confirm_regex = [x for x in rr if isinstance(x, str) and x.strip()]

        asu = raw.get("allow_sudo")
        if isinstance(asu, bool):
            self.allow_sudo = asu

        ap = raw.get("allow_pipes")
        if isinstance(ap, bool):
            self.allow_pipes = ap
