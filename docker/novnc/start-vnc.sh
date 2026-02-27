#!/bin/bash
# Start VNC server + noVNC websocket proxy
set -e

# Create VNC password
mkdir -p ~/.vnc
echo "$VNC_PASSWORD" | vncpasswd -f > ~/.vnc/passwd
chmod 600 ~/.vnc/passwd

# Create xstartup
cat > ~/.vnc/xstartup << 'EOF'
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
exec startxfce4 &
EOF
chmod +x ~/.vnc/xstartup

# Start VNC server
vncserver :1 \
    -geometry "$VNC_RESOLUTION" \
    -depth 24 \
    -SecurityTypes VncAuth \
    -localhost no

echo "VNC server started on :1 (port $VNC_PORT)"

# Start noVNC websocket proxy
websockify --web=/usr/share/novnc/ \
    "$NOVNC_PORT" \
    "localhost:$VNC_PORT" &

echo "noVNC started on http://0.0.0.0:$NOVNC_PORT"
echo "VNC password: $VNC_PASSWORD"

# Start video recording in background (for demo)
mkdir -p /home/nlp2cmd/recordings

# Keep container running
tail -f /dev/null
