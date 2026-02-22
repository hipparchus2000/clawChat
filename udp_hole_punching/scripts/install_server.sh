#!/bin/bash
#
# ClawChat UDP Server Installation Script
# For Ubuntu VPS
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}ClawChat UDP Server Installer${NC}"
echo "=============================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Configuration
OPENCLAW_USER="openclaw"
INSTALL_DIR="/home/openclaw/clawchat"
SERVICE_NAME="clawchat-server"

# Get server IP
echo ""
echo -e "${YELLOW}Server Configuration${NC}"
read -p "Enter server public IP (auto-detect): " SERVER_IP

if [ -z "$SERVER_IP" ]; then
    SERVER_IP=$(curl -s ifconfig.me || echo "0.0.0.0")
    echo "Auto-detected IP: $SERVER_IP"
fi

# Generate bootstrap key
echo ""
echo -e "${YELLOW}Generating bootstrap key...${NC}"
BOOTSTRAP_KEY=$(openssl rand -base64 32)
echo "Bootstrap key generated (save this securely)"

# Create user
echo ""
echo -e "${YELLOW}Creating user: $OPENCLAW_USER${NC}"
if id "$OPENCLAW_USER" &>/dev/null; then
    echo "User already exists"
else
    useradd -r -s /bin/false -m "$OPENCLAW_USER"
    echo "User created"
fi

# Create directory structure
echo ""
echo -e "${YELLOW}Creating directory structure...${NC}"
mkdir -p "$INSTALL_DIR"/{src,config,security,logs,scripts}
chown -R "$OPENCLAW_USER:$OPENCLAW_USER" "$INSTALL_DIR"
chmod 700 "$INSTALL_DIR"
chmod 700 "$INSTALL_DIR/security"

# Install dependencies
echo ""
echo -e "${YELLOW}Installing system dependencies...${NC}"
apt-get update
apt-get install -y python3 python3-pip python3-venv python3-tk curl openssl

# Create virtual environment
echo ""
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
python3 -m venv "$INSTALL_DIR/venv"
chown -R "$OPENCLAW_USER:$OPENCLAW_USER" "$INSTALL_DIR/venv"

# Install Python packages
echo ""
echo -e "${YELLOW}Installing Python packages...${NC}"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install cryptography pycryptodome

# Copy source files
echo ""
echo -e "${YELLOW}Copying source files...${NC}"
# Note: In production, copy from your build directory
# For now, create placeholder
cat > "$INSTALL_DIR/requirements.txt" << 'EOF'
cryptography>=41.0.0
pycryptodome>=3.19.0
EOF

# Create config
cat > "$INSTALL_DIR/config/server.yaml" << EOF
server:
  id: "clawchat-server"
  name: "ClawChat Server"
  ip: "$SERVER_IP"
  port: null

security:
  directory: "$INSTALL_DIR/security"
  file_validity_hours: 1
  cleanup_interval_hours: 24

logging:
  level: "INFO"
  file: "$INSTALL_DIR/logs/server.log"
EOF

chown -R "$OPENCLAW_USER:$OPENCLAW_USER" "$INSTALL_DIR/config"

# Create wrapper script
cat > "$INSTALL_DIR/run_server.sh" << 'EOF'
#!/bin/bash
cd /home/openclaw/clawchat
source venv/bin/activate
export CLAWCHAT_BOOTSTRAP_KEY="${CLAWCHAT_BOOTSTRAP_KEY:-bootstrap-key-32bytes-change-in-production!}"
python3 run_server.py --ip 0.0.0.0 "$@"
EOF
chmod +x "$INSTALL_DIR/run_server.sh"
chown "$OPENCLAW_USER:$OPENCLAW_USER" "$INSTALL_DIR/run_server.sh"

# Create systemd service
echo ""
echo -e "${YELLOW}Creating systemd service...${NC}"
cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=ClawChat UDP Hole Punching Server
After=network.target

[Service]
Type=simple
User=$OPENCLAW_USER
Group=$OPENCLAW_USER
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONPATH=$INSTALL_DIR
Environment=CLAWCHAT_BOOTSTRAP_KEY=$BOOTSTRAP_KEY
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/run_server.py --ip 0.0.0.0
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=clawchat-server

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR/security $INSTALL_DIR/logs
PrivateTmp=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Set permissions
chown -R "$OPENCLAW_USER:$OPENCLAW_USER" "$INSTALL_DIR"
find "$INSTALL_DIR" -type d -exec chmod 700 {} \;
find "$INSTALL_DIR" -type f -exec chmod 600 {} \;
chmod +x "$INSTALL_DIR/run_server.sh"

# Summary
echo ""
echo -e "${GREEN}Installation Complete!${NC}"
echo "=============================="
echo ""
echo "Server IP: $SERVER_IP"
echo "Install directory: $INSTALL_DIR"
echo "Service name: $SERVICE_NAME"
echo ""
echo -e "${YELLOW}IMPORTANT: Save this bootstrap key securely!${NC}"
echo "Bootstrap Key: $BOOTSTRAP_KEY"
echo ""
echo "Next steps:"
echo "1. Copy the source code to $INSTALL_DIR/src/"
echo "2. Start the service: sudo systemctl start $SERVICE_NAME"
echo "3. Enable auto-start: sudo systemctl enable $SERVICE_NAME"
echo "4. Check status: sudo systemctl status $SERVICE_NAME"
echo "5. View logs: sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "Security files will be created in: $INSTALL_DIR/security/"
echo "Transfer these files to clients securely (USB, encrypted message, etc.)"
echo ""

# Save key to file
KEY_FILE="$INSTALL_DIR/.bootstrap_key"
echo "$BOOTSTRAP_KEY" > "$KEY_FILE"
chmod 400 "$KEY_FILE"
chown "$OPENCLAW_USER:$OPENCLAW_USER" "$KEY_FILE"
echo "Bootstrap key saved to: $KEY_FILE (permissions 400)"
