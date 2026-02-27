#!/usr/bin/env python3
"""
Example: libvirt stream — create and manage VMs, connect via SPICE/VNC.

Prerequisites:
    sudo apt install libvirt-clients libvirt-daemon-system qemu-kvm virt-viewer

Usage:
    python3 examples/07_stream_protocols/example_libvirt.py
    # Or via CLI:
    nlp2cmd --source libvirt:///system -q "list VMs"
    nlp2cmd --source libvirt:///system --run -q "create ubuntu VM with 4GB RAM"
"""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from nlp2cmd.streams import StreamRouter, parse_source_uri


def main():
    router = StreamRouter()

    print("=== libvirt Stream Examples ===\n")

    # Example 1: Parse libvirt URIs
    uris = [
        "libvirt:///system",
        "libvirt+ssh://root@hypervisor/system",
        "libvirt+tcp://cluster-node/system",
    ]
    for raw in uris:
        uri = parse_source_uri(raw)
        print(f"  {raw}")
        print(f"    → scheme={uri.scheme}, host={uri.host}, user={uri.user}, path={uri.path}")
        print(f"    → transport={uri.params.get('transport', 'local')}\n")

    # Example 2: VM lifecycle commands
    print("--- VM Lifecycle Commands ---")
    commands = [
        ("list running VMs", "List all VMs"),
        ("create ubuntu VM with 4GB RAM and 2 CPUs", "Create a new VM"),
        ("start vm nlp2cmd-vm", "Start a VM"),
        ("info vm nlp2cmd-vm", "Get VM details"),
        ("connect to vm nlp2cmd-vm", "Get SPICE/VNC display URL"),
        ("stop vm nlp2cmd-vm", "Graceful shutdown"),
        ("delete vm nlp2cmd-vm", "Remove VM and storage"),
    ]

    for cmd, desc in commands:
        print(f"\n  {desc}:")
        print(f"    nlp2cmd --source libvirt:///system --run -q \"{cmd}\"")

    # Example 3: Remote libvirt via SSH
    print("\n\n--- Remote Hypervisor ---")
    print("  nlp2cmd --source libvirt+ssh://root@hypervisor/system -q 'list VMs'")
    print("  nlp2cmd --source libvirt+ssh://admin@kvm-host/system --run -q 'create windows VM with 8GB RAM'")

    # Example 4: Connect to VM desktop
    print("\n--- Desktop Control via SPICE ---")
    print("  # After VM is running, get display URL:")
    print("  nlp2cmd --source libvirt:///system -q 'connect to vm ubuntu-desktop'")
    print("  # → spice://localhost:5900")
    print("")
    print("  # Then control the VM desktop:")
    print("  nlp2cmd --source spice://localhost:5900 --run -q 'open terminal and run htop'")
    print("  nlp2cmd --source novnc://localhost:6080 --run -q 'open firefox'")

    # Example 5: Full workflow
    print("\n\n--- Full Workflow: Create + Start + Control ---")
    print("  # 1. Create VM")
    print("  nlp2cmd --source libvirt:///system --run -q 'create ubuntu VM with 2GB RAM'")
    print("  # 2. Start VM")
    print("  nlp2cmd --source libvirt:///system --run -q 'start vm ubuntu'")
    print("  # 3. Get SPICE URL")
    print("  nlp2cmd --source libvirt:///system -q 'connect vm ubuntu'")
    print("  # 4. Control desktop")
    print("  nlp2cmd --source spice://localhost:5900 --run -q 'open calculator'")


if __name__ == "__main__":
    main()
