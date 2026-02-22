# ClawChat UDP Server Installation Guide

## Ubuntu VPS Installation

### Prerequisites

- Ubuntu 20.04 or later
- Root access
- Public IP address
- Python 3.8+

### Automated Installation

```bash
# 1. Download the repository
cd /opt
sudo git clone <repository> clawchat
cd clawchat/udp_hole_punching

# 2. Run the installer
sudo bash scripts/install_server.sh

# 3. Copy source files
sudo cp -r src /home/openclaw/clawchat/
sudo cp run_server.py requirements.txt /home/openclaw/clawchat/
sudo chown -R openclaw:openclaw /home/openclaw/clawchat

# 4. Install Python dependencies
sudo -u openclaw /home/openclaw/clawchat/venv/bin/pip install -r /home/openclaw/clawchat/requirements.txt

# 5. Start the service
sudo systemctl start clawchat-server
sudo systemctl enable clawchat-server
```

### Manual Installation

#### 1. Create User

```bash
sudo useradd -r -s /bin/false -m openclaw
```

#### 2. Create Directory Structure

```bash
sudo mkdir -p /home/openclaw/clawchat/{src,config,security,logs}
sudo chmod 700 /home/openclaw/clawchat
sudo chmod 700 /home/openclaw/clawchat/security
sudo chown -R openclaw:openclaw /home/openclaw/clawchat
```

#### 3. Install Dependencies

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv python3-tk curl openssl
```

#### 4. Create Virtual Environment

```bash
sudo python3 -m venv /home/openclaw/clawchat/venv
sudo -u openclaw /home/openclaw/clawchat/venv/bin/pip install cryptography pycryptodome
```

#### 5. Copy Source Code

```bash
sudo cp -r src /home/openclaw/clawchat/
sudo cp run_server.py /home/openclaw/clawchat/
sudo chown -R openclaw:openclaw /home/openclaw/clawchat/src
sudo chown openclaw:openclaw /home/openclaw/clawchat/run_server.py
```

#### 6. Generate Bootstrap Key

```bash
BOOTSTRAP_KEY=$(openssl rand -base64 32)
echo "Bootstrap Key: $BOOTSTRAP_KEY"

# Save securely
sudo -u openclaw tee /home/openclaw/clawchat/.bootstrap_key <<< "$BOOTSTRAP_KEY"
sudo chmod 400 /home/openclaw/clawchat/.bootstrap_key
```

#### 7. Create Systemd Service

```bash
sudo tee /etc/systemd/system/clawchat-server.service << 'EOF'
[Unit]
Description=ClawChat UDP Hole Punching Server
After=network.target

[Service]
Type=simple
User=openclaw
Group=openclaw
WorkingDirectory=/home/openclaw/clawchat
Environment=PYTHONPATH=/home/openclaw/clawchat
Environment=CLAWCHAT_BOOTSTRAP_KEY=<YOUR_BOOTSTRAP_KEY>
ExecStart=/home/openclaw/clawchat/venv/bin/python /home/openclaw/clawchat/run_server.py --ip 0.0.0.0
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=clawchat-server

NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/openclaw/clawchat/security /home/openclaw/clawchat/logs
PrivateTmp=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
```

Replace `<YOUR_BOOTSTRAP_KEY>` with the actual key.

#### 8. Start Service

```bash
sudo systemctl start clawchat-server
sudo systemctl enable clawchat-server
```

### Verification

```bash
# Check service status
sudo systemctl status clawchat-server

# View logs
sudo journalctl -u clawchat-server -f

# Check security files
sudo ls -la /home/openclaw/clawchat/security/

# Test manually
sudo -u openclaw /home/openclaw/clawchat/venv/bin/python /home/openclaw/clawchat/run_server.py --ip 0.0.0.0
```

## Client Installation

### Windows

```powershell
# 1. Install Python 3.8+ from python.org

# 2. Clone repository
git clone <repository> clawchat
cd clawchat\udp_hole_punching

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run client
python run_client.py
```

### Linux/Mac

```bash
# 1. Clone repository
git clone <repository> clawchat
cd clawchat/udp_hole_punching

# 2. Install dependencies
pip3 install -r requirements.txt

# 3. Run client
python3 run_client.py
```

## Initial Connection

### 1. Start Server

```bash
sudo systemctl start clawchat-server
```

### 2. Transfer Security File

The server creates a security file in `/home/openclaw/clawchat/security/`.

Transfer this file to the client securely:
- USB drive
- Encrypted email/message
- Secure file sharing

### 3. Connect Client

```bash
python run_client.py
```

Select the security file via the file browser popup. The client will:
1. Load the security file
2. Detect NAT type
3. Perform UDP hole punching
4. Establish encrypted connection

## Post-Installation

### Security File Transfer

```bash
# On server, copy to accessible location
sudo cp /home/openclaw/clawchat/security/clawchat-*.sec /tmp/
sudo chmod 644 /tmp/clawchat-*.sec

# Transfer to client (example: scp)
scp /tmp/clawchat-*.sec user@client:/path/

# Remove from /tmp
sudo rm /tmp/clawchat-*.sec
```

### Firewall Configuration

If using UFW:

```bash
# Allow UDP ephemeral ports
sudo ufw allow 49152:65535/udp

# Or allow specific port if configured
sudo ufw allow 54321/udp
```

### Monitoring

```bash
# Watch logs
sudo journalctl -u clawchat-server -f

# Check resource usage
sudo systemctl show clawchat-server --property=MemoryCurrent,CPUUsageNSec

# Monitor connections
sudo ss -uln | grep clawchat
```

### Backup

```bash
# Backup bootstrap key
sudo cp /home/openclaw/clawchat/.bootstrap_key /secure/backup/location/

# Backup configuration
sudo cp -r /home/openclaw/clawchat/config /secure/backup/location/
```

## Troubleshooting

### Service fails to start

```bash
# Check for errors
sudo journalctl -u clawchat-server -n 50

# Test manually
sudo -u openclaw bash -c 'cd /home/openclaw/clawchat && source venv/bin/activate && python run_server.py'

# Check permissions
sudo ls -laR /home/openclaw/clawchat/
```

### Client can't connect

1. Verify server is running: `sudo systemctl is-active clawchat-server`
2. Check firewall rules allow UDP
3. Verify security file is valid and not expired
4. Check NAT type: `python -c "from src.networking.nat_detection import NATDetector; print(NATDetector().detect())"`

### Permission denied errors

```bash
# Fix ownership
sudo chown -R openclaw:openclaw /home/openclaw/clawchat

# Fix permissions
sudo chmod 700 /home/openclaw/clawchat
sudo chmod 700 /home/openclaw/clawchat/security
sudo find /home/openclaw/clawchat -name "*.sec" -exec chmod 600 {} \;
```

## Uninstallation

```bash
# Stop and disable service
sudo systemctl stop clawchat-server
sudo systemctl disable clawchat-server
sudo rm /etc/systemd/system/clawchat-server.service
sudo systemctl daemon-reload

# Remove files
sudo rm -rf /home/openclaw/clawchat

# Remove user (optional)
sudo userdel openclaw
```
