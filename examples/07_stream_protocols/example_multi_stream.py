#!/usr/bin/env python3
"""
Example: Multi-stream workflow — combine protocols in one session.

Demonstrates using multiple stream protocols together:
1. SSH to check server health
2. HTTP to query an API
3. libvirt to manage a VM
4. RTSP to check a camera

Usage:
    python3 examples/07_stream_protocols/example_multi_stream.py
"""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from nlp2cmd.streams import StreamRouter, parse_source_uri


def main():
    router = StreamRouter()

    print("=== Multi-Stream Workflow Example ===\n")
    print("This example shows how to combine multiple protocols.\n")

    # Show all supported protocols
    print(f"Supported protocols: {', '.join(router.supported_protocols())}\n")

    # Workflow steps
    steps = [
        ("ssh://admin@web-server", "check disk usage", "1. Check web server disk"),
        ("http://web-server:8080/api", "get /health", "2. Check API health"),
        ("ssh://admin@db-server", "check memory usage", "3. Check DB server memory"),
        ("libvirt:///system", "list running VMs", "4. List running VMs"),
        ("rtsp://camera:554/stream", "is there motion?", "5. Check security camera"),
        ("ftp://backup@nas/backups", "list files", "6. List backup files"),
    ]

    print("--- Workflow Steps ---\n")
    for source, task, desc in steps:
        uri = parse_source_uri(source)
        print(f"  {desc}")
        print(f"    Source: {source}")
        print(f"    Task: {task}")
        print(f"    Protocol: {uri.scheme} (visual={uri.is_visual}, shell={uri.is_shell})")
        print(f"    CLI: nlp2cmd --source {source} -q \"{task}\"\n")

    # Demonstrate URI parsing for all protocols
    print("\n--- URI Parsing for All Protocols ---\n")
    test_uris = [
        "ssh://deploy@prod:2222/var/log",
        "vnc://desktop:5901",
        "novnc://localhost:6080",
        "spice://kvm-host:5900",
        "rdp://admin:P4ssw0rd@windows-pc",
        "libvirt:///system",
        "libvirt+ssh://root@hypervisor/system",
        "ftp://user:pass@fileserver/data",
        "sftp://admin@backup-host/mnt/backups",
        "http://api.example.com:8080/v2",
        "https://secure-api.example.com/graphql",
        "ws://realtime.example.com:3000/events",
        "wss://stream.binance.com/ws",
        "rtsp://admin:admin@camera.local:554/live",
    ]

    for raw in test_uris:
        uri = parse_source_uri(raw)
        flags = []
        if uri.is_visual:
            flags.append("visual")
        if uri.is_shell:
            flags.append("shell")
        if uri.is_file:
            flags.append("file")
        print(f"  {raw}")
        print(f"    → {uri.scheme}://{uri.netloc}{uri.path}  [{', '.join(flags) or 'data'}]")

    router.close_all()
    print("\n\nAll protocols supported via unified --source interface.")


if __name__ == "__main__":
    main()
