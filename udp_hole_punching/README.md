# ClawChat UDP Hole Punching

A secure P2P communication system using UDP hole punching with file-based security exchange.

## Features

- 🔒 **File-Based Security Exchange** - No cloud dependency (removed Mega.nz)
- 🕳️ **UDP Hole Punching** - Direct P2P connections through NAT
- 🔐 **AES-256-GCM Encryption** - End-to-end encryption
- 🔄 **In-Band Key Rotation** - Automatic hourly key rotation
- 🚨 **Compromised Protocol** - Emergency key destruction
- 🖥️ **Tkinter GUI** - File browser for selecting security files
- 🐧 **Systemd Service** - Run as service on Ubuntu VPS

## Architecture

```
[Client]                           [Server]
   |                                    |
   |<--(1) User selects .sec file       |
   |    via file browser                |
   |                                    |
   |<--(2) Load server IP, port,        |
   |    shared secret from file         |
   |                                    |
   |---(3) UDP hole punch-------------->|
   |<--(4) Encrypted connection---------|
   |                                    |
   |---(5) In-band key rotation-------->|
   |<--(6) Hourly port rotation---------|
```

## Quick Start

### Server (Ubuntu VPS)

```bash
# 1. Clone repository
cd /opt
git clone <repository> clawchat
cd clawchat/udp_hole_punching

# 2. Run installer
sudo bash scripts/install_server.sh

# 3. Copy source code to installation directory
sudo cp -r src /home/openclaw/clawchat/
sudo cp run_server.py /home/openclaw/clawchat/
sudo chown -R openclaw:openclaw /home/openclaw/clawchat

# 4. Start service
sudo systemctl start clawchat-server
sudo systemctl enable clawchat-server

# 5. Check status
sudo systemctl status clawchat-server
sudo journalctl -u clawchat-server -f
```

The server will create a security file in `/home/openclaw/clawchat/security/`.
Transfer this file to the client securely.

### Client (Windows/Linux/Mac)

```bash
# 1. Clone repository
git clone <repository> clawchat
cd clawchat/udp_hole_punching

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run client
python run_client.py

# 4. Select security file via file browser popup
# 5. Connection established automatically
```

## Directory Structure

```
udp_hole_punching/
├── src/
│   ├── security/           # Encryption and file management
│   ├── networking/         # UDP hole punching and NAT detection
│   ├── protocol/           # Message protocols
│   ├── client/             # Client implementation
│   └── server/             # Server implementation
├── scripts/
│   ├── install_server.sh   # Ubuntu VPS installer
│   └── clawchat-server.service  # Systemd service file
├── config/
│   ├── server.yaml         # Server configuration
│   └── client.yaml         # Client configuration
├── run_server.py           # Server entry point
├── run_client.py           # Client entry point
└── requirements.txt        # Python dependencies
```

## Security File Format

Security files (`.sec`) are encrypted JSON containing:

```json
{
  "version": "2.0",
  "server_public_ip": "45.135.36.44",
  "server_udp_port": 54321,
  "shared_secret": "base64-encoded-secret",
  "timestamp": 1234567890,
  "valid_until": 1234571490
}
```

- Files are encrypted with AES-256-GCM
- Valid for 11 minutes by default
- Auto-regenerates every 10 minutes if no client connects
- Stored with 600 permissions (owner read/write only)

## Compromised Protocol

If keys are suspected compromised:

1. Client sends `COMPROMISED` signal through encrypted channel
2. Both sides immediately destroy all keys
3. Server generates new security file
4. User manually transfers new file to client
5. New connection established

```bash
# In client, type:
> /compromised
Type 'YES' to confirm: YES
```

## Runtime User

The server runs as `openclaw` user (NOT root):

```bash
# Create user
sudo useradd -r -s /bin/false openclaw

# Directory permissions
/home/openclaw/clawchat/        700 (drwx------)
/home/openclaw/clawchat/security/ 700 (drwx------)
*.sec files                     600 (-rw-------)
```

## Ports

- Server uses random ephemeral ports (49152-65535)
- Ports rotate every hour
- No persistent listening ports (dark server)

## Systemd Service

```bash
# Start/stop/restart
sudo systemctl start clawchat-server
sudo systemctl stop clawchat-server
sudo systemctl restart clawchat-server

# View logs
sudo journalctl -u clawchat-server -f

# Check status
sudo systemctl status clawchat-server
```

## Configuration

### Server (`config/server.yaml`)

```yaml
server:
  id: "clawchat-server"
  ip: "0.0.0.0"
  port: null  # Random if null

security:
  directory: "/home/openclaw/clawchat/security"
  file_validity_minutes: 11  # Session key valid for 11 minutes
  auto_regenerate_minutes: 10  # Regenerate every 10 min if no client

encryption:
  key_rotation_interval: 3600  # seconds
```

### Client (`config/client.yaml`)

```yaml
client:
  use_gui: true  # Tkinter file browser

networking:
  hole_punch_timeout: 60
  nat_detection: true
```

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Run server manually
python run_server.py --ip 0.0.0.0 --port 54321

# Run client manually
python run_client.py --file /path/to/security.sec
```

## Troubleshooting

### Server won't start

```bash
# Check logs
sudo journalctl -u clawchat-server -n 50

# Check permissions
ls -la /home/openclaw/clawchat/

# Test manually
sudo -u openclaw python3 /home/openclaw/clawchat/run_server.py
```

### Client can't connect

1. Verify security file is valid and not expired
2. Check NAT type: symmetric NAT may fail
3. Verify firewall allows UDP outbound
4. Check server is running and accessible

### Compromised Protocol triggered accidentally

1. Server generates new security file automatically
2. Check `/home/openclaw/clawchat/security/` for new file
3. Transfer new file to client
4. Client loads new file and reconnects

## Security Considerations

- **Bootstrap Key**: Protect the bootstrap key used to encrypt security files
- **File Transfer**: Transfer `.sec` files securely (USB, encrypted message)
- **File Validity**: Security files expire after 11 minutes (configurable)
- **Auto-Regeneration**: New file generated every 10 minutes until client connects
- **Key Rotation**: Keys rotate automatically every hour after connection
- **Compromised Protocol**: Use immediately if keys are suspected stolen

## License

MIT License - See LICENSE file

## Changelog

### v2.0.0 (2026-02-22)
- Removed Mega.nz integration (paywall)
- Added file-based security exchange
- Added Compromised Protocol
- Initial UDP hole punching implementation
