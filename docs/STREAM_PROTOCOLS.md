# Stream Protocols — `--source` Interface

**Status:** v1.0.90 · **Date:** 2026-02-27

---

## Overview

NLP2CMD can execute tasks on **any data stream** using the unified `--source` flag.
Instead of only generating shell commands, it connects to remote systems, APIs,
video streams, and virtual machines — and executes tasks directly.

```bash
nlp2cmd --source <protocol>://<target> -q "<task>"
nlp2cmd --source <protocol>://<target> --run -q "<task>"
```

## Supported Protocols

| Protocol | URI | Use Case | Requirements |
|----------|-----|----------|-------------|
| **SSH** | `ssh://user@host:port` | Remote shell commands | `ssh` client |
| **VNC** | `vnc://host:5901` | Desktop GUI control | VNC server |
| **noVNC** | `novnc://host:6080` | Desktop GUI via browser | noVNC + Playwright |
| **SPICE** | `spice://host:5900` | VM desktop (libvirt) | `remote-viewer` |
| **RDP** | `rdp://user:pass@host` | Windows desktop | `xfreerdp` |
| **libvirt** | `libvirt:///system` | VM lifecycle | `virsh`, `qemu-kvm` |
| **FTP** | `ftp://user:pass@host/path` | File operations | `curl` |
| **SFTP** | `sftp://user@host/path` | Secure file operations | `ssh` |
| **HTTP** | `http://host:port/path` | REST API interaction | `curl` |
| **HTTPS** | `https://host/path` | Secure API | `curl` |
| **WebSocket** | `ws://host:port/path` | Real-time streams | `websocket-client` (optional) |
| **RTSP** | `rtsp://host:554/stream` | Video analysis | `opencv-python` |

## Architecture

```
User: nlp2cmd --source ssh://admin@server -q "check disk"
                    ↓
              parse_source_uri("ssh://admin@server")
                    ↓
              StreamRouter.execute()
                    ↓
              SSHStreamAdapter.execute("check disk")
                    ↓
              NLP2CMD pipeline → "df -h" → ssh admin@server "df -h"
                    ↓
              StreamResult(output="...", data={...})
```

## Usage Examples

### SSH — Remote Commands

```bash
# Execute commands
nlp2cmd --source ssh://admin@server -q "check disk usage"
nlp2cmd --source ssh://root@192.168.1.100:22 --run -q "restart nginx"

# Natural language → auto-converted to shell command
nlp2cmd --source ssh://deploy@prod -q "find large log files"
# → ssh deploy@prod "find /var/log -type f -size +100M"
```

### libvirt — VM Management

```bash
# List VMs
nlp2cmd --source libvirt:///system -q "list running VMs"

# Create VM
nlp2cmd --source libvirt:///system --run -q "create ubuntu VM with 4GB RAM and 2 CPUs"

# Start/stop
nlp2cmd --source libvirt:///system --run -q "start vm ubuntu-desktop"
nlp2cmd --source libvirt:///system --run -q "stop vm ubuntu-desktop"

# Get SPICE display URL
nlp2cmd --source libvirt:///system -q "connect to vm ubuntu-desktop"
# → spice://localhost:5900

# Remote hypervisor via SSH
nlp2cmd --source libvirt+ssh://root@hypervisor/system -q "list VMs"
```

### SPICE/VNC — Desktop Control

```bash
# Control VM desktop via SPICE
nlp2cmd --source spice://localhost:5900 --run -q "open terminal"

# Control desktop via noVNC (Docker)
docker compose -f docker/novnc/docker-compose.yml up -d
nlp2cmd --source novnc://localhost:6080 --run -q "open calculator"

# Type text in desktop app
nlp2cmd --source novnc://localhost:6080 --run -q "type hello world"
```

### RDP — Windows Desktop

```bash
nlp2cmd --source rdp://admin:P4ss@windows-pc --run -q "open notepad"
nlp2cmd --source rdp://user@192.168.1.50:3389 --run -q "open cmd and run ipconfig"
```

### RTSP — Video Stream Analysis

```bash
# Color analysis
nlp2cmd --source rtsp://camera:554/stream -q "what colors are dominant?"
# → "Dominant colors: green: 35.2%, blue: 28.1%, red: 15.4%"

# Motion detection
nlp2cmd --source rtsp://camera:554/live -q "is there motion?"
# → "Motion detected (12.4% changed, 3 regions)"

# Object detection
nlp2cmd --source rtsp://cam/stream -q "what objects are visible?"

# Brightness
nlp2cmd --source rtsp://cam/stream -q "is it bright or dark?"
# → "Lighting: normal (brightness: 142/255)"

# Frame capture
nlp2cmd --source rtsp://cam/stream -q "capture frame"
```

### HTTP — REST APIs

```bash
nlp2cmd --source http://jsonplaceholder.typicode.com -q "get /posts"
nlp2cmd --source https://api.github.com -q "get /users/wronai"
nlp2cmd --source http://localhost:8080/api --run -q "create /users"
```

### WebSocket — Real-time

```bash
nlp2cmd --source ws://echo.websocket.org --run -q "send hello"
nlp2cmd --source wss://stream.binance.com/ws -q "receive"
```

### FTP/SFTP — File Operations

```bash
nlp2cmd --source ftp://user:pass@fileserver/data -q "list files"
nlp2cmd --source sftp://admin@backup/mnt -q "download latest.tar.gz"
```

## Python API

```python
from nlp2cmd.streams import StreamRouter, parse_source_uri

router = StreamRouter()

# SSH
result = router.execute("ssh://admin@server", "df -h")
print(result.output)

# RTSP
result = router.query("rtsp://camera:554/stream", "what colors are dominant?")
print(result.data["colors"])

# libvirt
result = router.execute("libvirt:///system", "list running VMs")
print(result.output)

# HTTP
result = router.execute("https://api.github.com", "get /users/wronai")
print(result.data)

# Cleanup
router.close_all()
```

## URI Parsing

```python
from nlp2cmd.streams import parse_source_uri

uri = parse_source_uri("ssh://admin@192.168.1.100:2222/var/log")
# uri.scheme = "ssh"
# uri.host = "192.168.1.100"
# uri.port = 2222
# uri.user = "admin"
# uri.path = "/var/log"
# uri.is_shell = True
# uri.is_visual = False

uri = parse_source_uri("rtsp://admin:pass@camera.local:554/live")
# uri.scheme = "rtsp"
# uri.is_visual = True
```

## Files

```
src/nlp2cmd/streams/
├── __init__.py          # Package exports
├── base.py              # StreamAdapter, StreamResult, SourceURI, parse_source_uri
├── router.py            # StreamRouter — dispatches to protocol handlers
├── ssh_stream.py        # SSH remote commands
├── libvirt_stream.py    # VM lifecycle + SPICE/VNC display
├── rtsp_stream.py       # Video analysis (color, motion, objects)
├── spice_stream.py      # SPICE desktop control
├── rdp_stream.py        # RDP Windows desktop
├── vnc_stream.py        # VNC/noVNC desktop control
├── ftp_stream.py        # FTP/SFTP file operations
├── http_stream.py       # HTTP/HTTPS REST API
└── ws_stream.py         # WebSocket real-time

examples/07_stream_protocols/
├── README.md
├── example_ssh.py
├── example_libvirt.py
├── example_rtsp.py
├── example_http_api.py
└── example_multi_stream.py
```
