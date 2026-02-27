"""
Libvirt Stream Adapter — VM lifecycle + desktop control via SPICE/VNC.

Usage:
    nlp2cmd --source libvirt:///system "create ubuntu VM with 2GB RAM"
    nlp2cmd --source libvirt:///system "list running VMs"
    nlp2cmd --source spice://localhost:5900 "open terminal and run htop"
"""

from __future__ import annotations

import json
import subprocess
import shlex
import xml.etree.ElementTree as ET
from typing import Any, Optional

from nlp2cmd.streams.base import StreamAdapter, StreamResult, SourceURI


# Minimal libvirt XML template for creating a VM
_VM_XML_TEMPLATE = """\
<domain type='kvm'>
  <name>{name}</name>
  <memory unit='MiB'>{memory_mb}</memory>
  <vcpu>{vcpus}</vcpu>
  <os>
    <type arch='x86_64'>hvm</type>
    <boot dev='cdrom'/>
    <boot dev='hd'/>
  </os>
  <features><acpi/><apic/></features>
  <devices>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source file='{disk_path}'/>
      <target dev='vda' bus='virtio'/>
    </disk>
    <disk type='file' device='cdrom'>
      <driver name='qemu' type='raw'/>
      <source file='{iso_path}'/>
      <target dev='sda' bus='sata'/>
      <readonly/>
    </disk>
    <interface type='network'>
      <source network='default'/>
      <model type='virtio'/>
    </interface>
    <graphics type='{graphics}' port='-1' autoport='yes' listen='0.0.0.0'/>
    <video><model type='virtio'/></video>
    <channel type='spicevmc'>
      <target type='virtio' name='com.redhat.spice.0'/>
    </channel>
  </devices>
</domain>"""


class LibvirtStreamAdapter(StreamAdapter):
    """Manage VMs via libvirt and control their desktops via SPICE/VNC."""

    PROTOCOL = "libvirt"

    def __init__(self, source: SourceURI):
        super().__init__(source)
        self._uri = self._build_libvirt_uri()

    def _build_libvirt_uri(self) -> str:
        transport = self.source.params.get("transport", "local")
        if transport == "local":
            return f"qemu:///system"
        elif transport == "ssh":
            user = self.source.user or "root"
            return f"qemu+ssh://{user}@{self.source.host}/system"
        else:
            return f"qemu+{transport}://{self.source.host}/system"

    def _virsh(self, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
        cmd = ["virsh", "-c", self._uri] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def connect(self) -> StreamResult:
        try:
            r = self._virsh("version")
            if r.returncode == 0:
                self._connected = True
                return StreamResult(success=True, output=r.stdout.strip(),
                                    metadata={"libvirt_uri": self._uri})
            return StreamResult(success=False, error=r.stderr.strip())
        except FileNotFoundError:
            return StreamResult(success=False,
                                error="virsh not found. Install libvirt: sudo apt install libvirt-clients")
        except Exception as e:
            return StreamResult(success=False, error=str(e))

    def execute(self, task: str, **kwargs) -> StreamResult:
        task_lower = task.lower()

        if any(w in task_lower for w in ["list", "pokaż", "show"]) and any(w in task_lower for w in ["vm", "maszyn", "domain"]):
            return self._list_vms()
        elif any(w in task_lower for w in ["create", "utwórz", "stwórz", "nowa"]):
            return self._create_vm(task, **kwargs)
        elif any(w in task_lower for w in ["start", "uruchom", "włącz"]):
            return self._start_vm(task)
        elif any(w in task_lower for w in ["stop", "zatrzymaj", "wyłącz", "shutdown"]):
            return self._stop_vm(task)
        elif any(w in task_lower for w in ["delete", "usuń", "destroy", "undefine"]):
            return self._delete_vm(task)
        elif any(w in task_lower for w in ["info", "status", "stan"]):
            return self._vm_info(task)
        elif any(w in task_lower for w in ["connect", "połącz", "spice", "vnc", "console"]):
            return self._connect_display(task)
        else:
            return StreamResult(success=False,
                                error=f"Unknown libvirt task: {task}",
                                data={"supported": ["list", "create", "start", "stop", "delete", "info", "connect"]})

    def query(self, question: str, **kwargs) -> StreamResult:
        return self._list_vms()

    def _list_vms(self) -> StreamResult:
        r = self._virsh("list", "--all")
        if r.returncode == 0:
            return StreamResult(success=True, output=r.stdout.strip())
        return StreamResult(success=False, error=r.stderr.strip())

    def _extract_vm_name(self, task: str) -> str:
        import re
        m = re.search(r"(?:vm|maszyn[ęa]|domain)\s+['\"]?(\w[\w-]*)", task.lower())
        if m:
            return m.group(1)
        words = task.split()
        return words[-1] if words else "nlp2cmd-vm"

    def _create_vm(self, task: str, **kwargs) -> StreamResult:
        import re

        name = kwargs.get("name") or self._extract_vm_name(task) or "nlp2cmd-vm"

        m_ram = re.search(r"(\d+)\s*(?:gb|GB)", task)
        memory_mb = int(m_ram.group(1)) * 1024 if m_ram else 2048

        m_cpu = re.search(r"(\d+)\s*(?:cpu|vcpu|cores|rdzeni)", task)
        vcpus = int(m_cpu.group(1)) if m_cpu else 2

        disk_path = kwargs.get("disk", f"/var/lib/libvirt/images/{name}.qcow2")
        iso_path = kwargs.get("iso", "")
        graphics = kwargs.get("graphics", "spice")

        # Create disk image if not exists
        try:
            subprocess.run(
                ["qemu-img", "create", "-f", "qcow2", disk_path, "20G"],
                capture_output=True, text=True, timeout=30,
            )
        except Exception:
            pass

        xml = _VM_XML_TEMPLATE.format(
            name=name, memory_mb=memory_mb, vcpus=vcpus,
            disk_path=disk_path, iso_path=iso_path, graphics=graphics,
        )

        r = self._virsh("define", "/dev/stdin", timeout=15)
        # virsh define reads from file, so we use a temp approach
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml)
            f.flush()
            r = self._virsh("define", f.name)

        if r.returncode == 0:
            return StreamResult(
                success=True,
                output=f"VM '{name}' defined: {memory_mb}MB RAM, {vcpus} vCPUs, {graphics}",
                data={"name": name, "memory_mb": memory_mb, "vcpus": vcpus,
                      "disk": disk_path, "graphics": graphics},
            )
        return StreamResult(success=False, error=r.stderr.strip())

    def _start_vm(self, task: str) -> StreamResult:
        name = self._extract_vm_name(task)
        r = self._virsh("start", name)
        if r.returncode == 0:
            return StreamResult(success=True, output=f"VM '{name}' started")
        return StreamResult(success=False, error=r.stderr.strip())

    def _stop_vm(self, task: str) -> StreamResult:
        name = self._extract_vm_name(task)
        r = self._virsh("shutdown", name)
        if r.returncode == 0:
            return StreamResult(success=True, output=f"VM '{name}' shutting down")
        return StreamResult(success=False, error=r.stderr.strip())

    def _delete_vm(self, task: str) -> StreamResult:
        name = self._extract_vm_name(task)
        self._virsh("destroy", name)  # force stop
        r = self._virsh("undefine", name, "--remove-all-storage")
        if r.returncode == 0:
            return StreamResult(success=True, output=f"VM '{name}' deleted")
        return StreamResult(success=False, error=r.stderr.strip())

    def _vm_info(self, task: str) -> StreamResult:
        name = self._extract_vm_name(task)
        r = self._virsh("dominfo", name)
        if r.returncode == 0:
            return StreamResult(success=True, output=r.stdout.strip())
        return StreamResult(success=False, error=r.stderr.strip())

    def _connect_display(self, task: str) -> StreamResult:
        name = self._extract_vm_name(task)
        r = self._virsh("domdisplay", name)
        if r.returncode == 0:
            display_url = r.stdout.strip()
            return StreamResult(
                success=True,
                output=f"Display URL for '{name}': {display_url}",
                data={"display_url": display_url, "vm": name},
            )
        return StreamResult(success=False, error=r.stderr.strip())
