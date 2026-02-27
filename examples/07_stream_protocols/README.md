# Stream Protocol Examples

NLP2CMD can execute tasks on **any data stream** via the `--source` flag.

## Supported Protocols

| Protocol | URI Format | Use Case |
|----------|-----------|----------|
| **SSH** | `ssh://user@host` | Remote shell commands |
| **VNC** | `vnc://host:5901` | Desktop GUI control |
| **noVNC** | `novnc://host:6080` | Desktop GUI via browser |
| **SPICE** | `spice://host:5900` | VM desktop (libvirt) |
| **RDP** | `rdp://user:pass@host` | Windows desktop |
| **libvirt** | `libvirt:///system` | VM lifecycle management |
| **FTP** | `ftp://user:pass@host/path` | File operations |
| **SFTP** | `sftp://user@host/path` | Secure file operations |
| **HTTP** | `http://api.host/endpoint` | REST API interaction |
| **WebSocket** | `ws://host:8080/stream` | Real-time messaging |
| **RTSP** | `rtsp://cam:554/stream` | Video stream analysis |

## Quick Examples

```bash
# SSH: run commands on remote server
nlp2cmd --source ssh://admin@192.168.1.100 -q "check disk usage"

# libvirt: manage VMs
nlp2cmd --source libvirt:///system -q "list running VMs"
nlp2cmd --source libvirt:///system --run -q "create ubuntu VM with 4GB RAM"

# VNC: control desktop via noVNC
nlp2cmd --source novnc://localhost:6080 --run -q "open terminal and run htop"

# RTSP: analyze camera stream
nlp2cmd --source rtsp://camera:554/stream -q "what colors are dominant?"
nlp2cmd --source rtsp://camera:554/live -q "is there motion?"

# HTTP: interact with APIs
nlp2cmd --source http://jsonplaceholder.typicode.com -q "get /posts"

# FTP: file operations
nlp2cmd --source ftp://user:pass@fileserver/data -q "list files"
```

## Examples in this directory

| Script | Protocol | Description |
|--------|----------|-------------|
| `example_ssh.py` | SSH | Remote command execution |
| `example_libvirt.py` | libvirt | VM creation and management |
| `example_rtsp.py` | RTSP | Video stream color/motion analysis |
| `example_http_api.py` | HTTP | REST API interaction |
| `example_multi_stream.py` | Mixed | Multi-protocol workflow |
