#!/usr/bin/env python3
"""
Example: SSH stream — execute commands on remote hosts.

Usage:
    python3 examples/07_stream_protocols/example_ssh.py
    # Or via CLI:
    nlp2cmd --source ssh://user@host -q "check disk usage"
"""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from nlp2cmd.streams import StreamRouter, parse_source_uri


def main():
    router = StreamRouter()

    print("=== SSH Stream Examples ===\n")

    # Example 1: Parse URI
    uri = parse_source_uri("ssh://admin@192.168.1.100:22")
    print(f"Parsed URI: scheme={uri.scheme}, host={uri.host}, user={uri.user}, port={uri.port}")
    print(f"  is_shell={uri.is_shell}, is_visual={uri.is_visual}, is_file={uri.is_file}\n")

    # Example 2: Execute on localhost (safe demo)
    print("--- Execute commands via SSH (localhost demo) ---")
    tasks = [
        "uname -a",
        "df -h /",
        "free -h",
        "find large log files",  # NL → auto-converted to shell command
    ]

    for task in tasks:
        print(f"\n  Task: {task}")
        # NOTE: This would actually SSH to localhost; skip if no SSH server
        # result = router.execute("ssh://localhost", task)
        # print(f"  Output: {result.output[:200]}")
        print(f"  → Would execute: nlp2cmd --source ssh://localhost -q \"{task}\"")

    # Example 3: Query system info
    print("\n--- Query remote system info ---")
    queries = ["uptime", "disk", "memory", "os", "processes"]
    for q in queries:
        print(f"  Query '{q}' → nlp2cmd --source ssh://admin@server -q \"{q}\"")

    print("\n=== CLI Usage ===")
    print("  nlp2cmd --source ssh://user@host -q 'check disk usage'")
    print("  nlp2cmd --source ssh://root@192.168.1.100 --run -q 'restart nginx'")
    print("  nlp2cmd --source ssh://deploy@prod:2222 -q 'tail -f /var/log/app.log'")


if __name__ == "__main__":
    main()
