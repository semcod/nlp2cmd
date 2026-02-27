#!/bin/bash
# Start VNC server + noVNC websocket proxy

echo "=== NLP2CMD Desktop Environment ==="
echo "User: $(whoami) | Home: $HOME"

# Create xstartup
mkdir -p "$HOME/.vnc" || true
cat > "$HOME/.vnc/xstartup" << 'XEOF'
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
startxfce4
XEOF
chmod +x "$HOME/.vnc/xstartup"

# Kill any existing VNC server on :1
vncserver -kill :1 2>/dev/null || true
sleep 1

# Start VNC server (no auth — local Docker demo only)
echo "Starting VNC server on :1 (${VNC_RESOLUTION})..."
vncserver :1 \
    -geometry "$VNC_RESOLUTION" \
    -depth 24 \
    -SecurityTypes None \
    --I-KNOW-THIS-IS-INSECURE \
    -localhost no

echo "VNC server started on :1 (port $VNC_PORT)"

# Wait for VNC to be ready
sleep 2

# Start noVNC websocket proxy
echo "Starting noVNC websocket proxy on port $NOVNC_PORT..."
websockify --web=/usr/share/novnc/ \
    "$NOVNC_PORT" \
    "localhost:$VNC_PORT" &

echo ""
echo "=== Ready ==="
echo "noVNC:  http://0.0.0.0:$NOVNC_PORT/vnc.html?autoconnect=true&password=$VNC_PASSWORD"
echo "VNC:    localhost:$VNC_PORT (password: $VNC_PASSWORD)"
echo ""

# Ensure recordings dir exists
mkdir -p "$HOME/recordings" || true

# Keep container running
exec tail -f /dev/null
