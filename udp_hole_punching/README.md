# ClawChat UDP Hole Punching

A secure P2P communication system using UDP hole punching with AI-powered assistance, file management, and automated task scheduling.

## Features

- 🔒 **File-Based Security Exchange** - No cloud dependency (removed Mega.nz)
- 🕳️ **UDP Hole Punching** - Direct P2P connections through NAT
- 🔐 **AES-256-GCM Encryption** - End-to-end encryption with forward secrecy
- 🤖 **LLM Bridge** - DeepSeek/OpenAI/Anthropic AI integration
- 📝 **Context System** - OpenClaw-style agentic loop for AI context
- ⏰ **Cron Scheduler** - Automated AI task execution
- 📁 **File Manager** - Full remote file operations (list, download, upload, delete, rename)
- 🔄 **In-Band Key Rotation** - Automatic hourly key rotation
- 🚨 **Compromised Protocol** - Emergency key destruction
- 🖥️ **Tkinter GUI** - Three-tab interface (Chat, Files, Crontab)
- 🐧 **Systemd Service** - Run as service on Ubuntu VPS

## Three-Tier Architecture

ClawChat uses a three-tier architecture:

```
[GUI Client] ←→ [Hole Punching Server] ←→ [LLM Server]
   (User)         (NAT Traversal)         (AI Processing)
```

| Component | Script | Purpose | Exposure |
|-----------|--------|---------|----------|
| **GUI Client** | `run_gui_client.py` | User interface | User's machine |
| **Hole Punching Server** | `run_server.py` | NAT traversal, relay | Public UDP port |
| **LLM Server** | `run_llm_server.py` | AI processing | Localhost only |

**Important**: Client NEVER connects directly to LLM server. All communication goes through hole punching server which acts as a relay.

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

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

### Development (3 Terminals Required)

```bash
# Terminal 1: LLM Server (wait for "Listening on UDP" message)
python run_llm_server.py
# Should show: "Listening on UDP 127.0.0.1:55556"

# Terminal 2: Hole Punching Server (wait for LLM server to be ready)
python run_server.py --ip 127.0.0.1
# Should show: "LLM connection established"

# Terminal 3: GUI Client
python run_gui_client.py
# Select the .sec file when prompted
```

### Production Server (Ubuntu VPS)

```bash
# 1. Clone repository
cd /opt
git clone <repository> clawchat
cd clawchat/udp_hole_punching

# 2. Configure environment
sudo cp .env.example .env
sudo nano .env  # Add API keys

# 3. Run installer
sudo bash scripts/install_server.sh

# 4. Start services
sudo systemctl start clawchat-llm
sudo systemctl start clawchat-server

# 5. Check status
sudo journalctl -u clawchat-server -f
```

The hole punching server creates `clawchat-current.sec` in `/home/openclaw/clawchat/security/`.
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
│   ├── protocol/           # Message protocols (CHAT, FILE_*, CRON_*)
│   ├── client/             # Client implementation
│   ├── server/             # Server implementation
│   ├── llm_bridge.py       # LLM integration (DeepSeek/OpenAI/Anthropic)
│   ├── context_loader.py   # OpenClaw-style context system
│   └── cron_scheduler.py   # Automated task scheduler
├── context/                # AI context files
│   ├── SOUL.md             # Core AI identity
│   ├── AGENTS.md           # Operational rules
│   ├── USER.md             # User preferences
│   ├── MEMORY.md           # Long-term memory
│   ├── CRON.md             # Scheduled AI tasks
│   └── memory/             # Daily conversation logs
├── scripts/
│   ├── install_server.sh   # Ubuntu VPS installer
│   └── clawchat-server.service  # Systemd service file
├── config/
│   ├── server.yaml         # Server configuration
│   └── client.yaml         # Client configuration
├── run_server.py           # Standard server entry point
├── run_llm_server.py       # LLM-enabled server
├── run_client.py           # CLI client
├── run_gui_client.py       # Tkinter GUI client
└── requirements.txt        # Python dependencies
```

## Security File Format

Security files (`.sec`) are encrypted JSON containing connection credentials:

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

### Properties

- **Encryption**: AES-256-GCM with bootstrap key
- **Validity**: 11 minutes
- **Auto-regeneration**: New file every 10 minutes if no client connects
- **Filename**: Fixed at `clawchat-current.sec` (overwritten on regeneration)
- **Permissions**: 600 (owner read/write only)

### Location

- **Server**: `/home/openclaw/clawchat/security/clawchat-current.sec`
- **Client**: Selected via file browser (transfer securely from server)

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

### Environment Setup

Create `.env` file in `udp_hole_punching/`:

```ini
# LLM Configuration
CLAWCHAT_LLM_PROVIDER=deepseek      # deepseek, openai, or anthropic
DEEPSEEK_API_KEY=sk-your-key-here
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-your-key-here

# Security
CLAWCHAT_BOOTSTRAP_KEY=your-bootstrap-key-32bytes!

# Optional
CLAWCHAT_CONTEXT_DIR=./context
CLAWCHAT_BASE_PATH=./clawchat_data
```

### Running the System

```bash
# Install dependencies
pip install -r requirements.txt

# Run LLM-enabled server (uses CLAWCHAT_LLM_PROVIDER from .env)
python run_llm_server.py

# Or specify provider manually
python run_llm_server.py --provider openai

# Run standard server (echo only)
python run_server.py --ip 127.0.0.1 --port 55555

# Run GUI client
python run_gui_client.py

# Run tests
python -m pytest tests/
```

## Documentation

| Document | Description |
|----------|-------------|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | **Three-tier system architecture** |
| [`CONTEXT_SYSTEM.md`](CONTEXT_SYSTEM.md) | OpenClaw-style AI context system |
| [`CRON_SYSTEM.md`](CRON_SYSTEM.md) | Automated AI task scheduling |
| [`FILE_PROTOCOL.md`](FILE_PROTOCOL.md) | File manager protocol spec |
| [`LLM_BRIDGE.md`](LLM_BRIDGE.md) | LLM integration guide |

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

### v2.1.0 (2026-02-24)
- **LLM Bridge**: AI integration with DeepSeek, OpenAI, Anthropic
- **Context System**: OpenClaw-style agentic loop (SOUL → AGENTS → USER → MEMORY)
- **Cron Scheduler**: Automated AI task execution via CRON.md
- **File Manager**: Complete file operations protocol (list, download, upload, delete, rename)
- **GUI Client**: Three-tab interface (Chat, Files, Crontab)
- **Security File**: Fixed filename `clawchat-current.sec`
- **Auto-regeneration**: 11 min validity, 10 min regen interval

### v2.0.0 (2026-02-22)
- Removed Mega.nz integration (paywall)
- Added file-based security exchange
- Added Compromised Protocol
- Initial UDP hole punching implementation
