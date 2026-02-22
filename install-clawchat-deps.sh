#!/bin/bash
# Install ClawChat WebSocket dependencies

echo "🔧 Installing ClawChat WebSocket dependencies..."

# Wait for apt to be available
echo "⏳ Waiting for apt to be available..."
while fuser /var/lib/apt/lists/lock >/dev/null 2>&1 ; do
    echo "   apt is locked, waiting..."
    sleep 10
done

# Install required packages
echo "📦 Installing Python packages..."
apt-get update
apt-get install -y python3-pip python3-venv

# Create virtual environment
echo "🐍 Creating virtual environment..."
python3 -m venv /opt/clawchat-venv

# Install WebSocket dependencies
echo "📡 Installing WebSocket dependencies..."
/opt/clawchat-venv/bin/pip install websockets pyyaml

# Create proper WebSocket service
echo "🚀 Creating WebSocket service..."
cat > /etc/systemd/system/clawchat-websocket.service << EOF
[Unit]
Description=ClawChat WebSocket Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/.openclaw/workspace/projects/clawchat/backend
ExecStart=/opt/clawchat-venv/bin/python3 server.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=clawchat-websocket

# Security
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Stop temporary HTTP server
echo "🛑 Stopping temporary HTTP server..."
systemctl stop clawchat.service 2>/dev/null || true

# Start WebSocket server
echo "🚀 Starting WebSocket server..."
systemctl daemon-reload
systemctl enable clawchat-websocket.service
systemctl start clawchat-websocket.service

echo "✅ ClawChat WebSocket server installed and started!"
echo "📡 WebSocket server running on port 8765"
echo "🌐 Access at: ws://45.135.36.44:8765"
echo "📊 Check status: systemctl status clawchat-websocket.service"