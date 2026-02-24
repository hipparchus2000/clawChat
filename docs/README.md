# ⚠️ ARCHIVED - v1.0 Documentation

> **This documentation is for the archived WebSocket/Mega.nz implementation (v1.0).**
>
> **For the current UDP hole punching implementation (v2.0), see:**
> - [`../udp_hole_punching/README.md`](../udp_hole_punching/README.md) - Current implementation
> - [`../README.md`](../README.md) - Project overview
>
> **Migration Notes:**
> - Mega.nz integration was removed (paywall issues)
> - WebSocket replaced with UDP hole punching
> - Browser PWA replaced with Tkinter GUI client
> - File-based security exchange replaces cloud config storage

---

# ClawChat - Secure PWA Chat & File Management System (v1.0 - ARCHIVED)

![GitHub](https://img.shields.io/github/license/hipparchus2000/clawChat)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![Tests](https://github.com/hipparchus2000/clawChat/actions/workflows/ci-cd.yml/badge.svg)
![Coverage](https://img.shields.io/badge/coverage-80%25-brightgreen)
![Security](https://img.shields.io/badge/security-scanning-success)
![Release](https://img.shields.io/github/v/release/hipparchus2000/clawChat)

## 📋 Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [🚀 Quick Start](#-quick-start)
- [Architecture](#architecture)
- [Security Model](#security-model)
- [Development](#development)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)
- [Support](#support)

## Overview
ClawChat is a secure, single-page web application (PWA) that provides chat messaging and full file management capabilities for the OpenClaw projects folder. It features hourly port rotation for enhanced security and communicates via encrypted WebSocket connections.

**Production-ready • Open-source • Security-first**

## Key Features

### 🔒 **Security First**
- **Hourly Port Rotation:** WebSocket service changes port every hour
- **Encrypted Configuration:** Port info encrypted and stored on Mega.nz
- **Secure Key Exchange:** Initial key via OpenClaw TUI, Slack DM, or bash
- **No Secrets in Code:** GitHub-safe public repository

### 💬 **Chat Interface**
- Real-time messaging with WebSocket
- Message history and presence indicators
- Typing indicators and read receipts
- File attachments in chat

### 📁 **File Management**
- Full directory browser for projects folder
- Create, rename, delete, move files and folders
- Upload/download files from device
- In-browser text editor with syntax highlighting
- Search and filtering capabilities

### 📱 **Progressive Web App**
- Installable on mobile and desktop
- Offline capabilities with service worker
- Responsive design for all screen sizes
- Push notifications support

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Browser PWA   │◀──▶│ Python WebSocket │    │   Mega.nz      │
│   (HTML/JS/CSS) │    │     Service      │───▶│   Config Store │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                       │
         │                       │
         └───────────────────────┘
         Secure Key Exchange via:
         - OpenClaw TUI
         - Slack DM
         - Bash command
```

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+** (with pip)
- **Git** (for cloning)
- **Modern web browser** (Chrome 90+, Firefox 88+, Safari 14+)
- **Mega.nz account** (for encrypted config storage - optional for development)

### Installation Methods

#### Method 1: Quick Install (Development)
```bash
# Clone the repository
git clone https://github.com/hipparchus2000/clawChat.git
cd clawchat

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
pip install -r tests/requirements.txt

# Start the server
python backend/server.py

# Open in browser
# Navigate to http://localhost:8765 (or the port shown in console)
```

#### Method 2: Docker (Production)
```bash
# Pull the Docker image
docker pull ghcr.io/hipparchus2000/clawChat:latest

# Run with default configuration
docker run -p 8765:8765 ghcr.io/hipparchus2000/clawChat

# Run with custom configuration
docker run -p 8765:8765 \
  -v ./config:/app/config \
  -e ENCRYPTION_KEY="your-encryption-key" \
  ghcr.io/hipparchus2000/clawChat
```

#### Method 3: System Package (Linux)
```bash
# Add repository (example for Debian/Ubuntu)
curl -s https://packages.clawchat.example.com/key.gpg | sudo apt-key add -
echo "deb https://packages.clawchat.example.com/ stable main" | sudo tee /etc/apt/sources.list.d/clawchat.list

# Install
sudo apt update
sudo apt install clawchat

# Start service
sudo systemctl start clawchat
sudo systemctl enable clawchat
```

### First-Time Setup

1. **Generate Encryption Key** (optional for development):
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   # Save this key securely
   ```

2. **Configure Mega.nz** (for production):
   ```bash
   # Install MEGAcmd
   # See: https://mega.nz/cmd
   
   # Login
   mega-login your-email@example.com
   ```

3. **Start Services**:
   ```bash
   # Backend server
   python backend/server.py
   
   # In another terminal, start frontend dev server (optional)
   cd frontend
   python -m http.server 8000
   ```

4. **Access the Application**:
   - Open browser to: `http://localhost:8765`
   - Or frontend dev server: `http://localhost:8000`

### Configuration

Create `config.yaml` in the backend directory:

```yaml
# config.yaml
server:
  host: "0.0.0.0"
  port_range: [8000, 9000]
  max_connections: 100
  
security:
  encryption_key: "${ENCRYPTION_KEY}"  # Use environment variable
  rotation_interval: 3600  # 1 hour
  
logging:
  level: "INFO"
  file: "/var/log/clawchat/server.log"
  
mega:
  email: "${MEGA_EMAIL}"
  password: "${MEGA_PASSWORD}"
  config_path: "/clawchat/config.enc"
```

Set environment variables:
```bash
export ENCRYPTION_KEY="your-encryption-key"
export MEGA_EMAIL="your-email@example.com"
export MEGA_PASSWORD="your-password"
```

### Verify Installation

Run the verification script:
```bash
./scripts/verify-installation.sh
```

Expected output:
```
✅ Python version check: 3.8.0+
✅ Dependencies installed
✅ Server starts successfully
✅ Frontend files present
✅ Configuration valid
✅ Security checks passed
```

### Troubleshooting

**Common Issues:**

1. **Port already in use:**
   ```bash
   # Find process using port
   sudo lsof -i :8765
   # Kill process or change port in config
   ```

2. **Missing dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r backend/requirements.txt
   ```

3. **Permission errors:**
   ```bash
   sudo chmod +x scripts/*.sh
   sudo chown -R $(whoami) .
   ```

4. **Browser security warnings:**
   - Use `http://localhost` not IP address
   - For HTTPS, use reverse proxy or development certificate

**Need Help?**
- Check [Troubleshooting Guide](docs/troubleshooting.md)
- Open a [GitHub Issue](https://github.com/hipparchus2000/clawChat/issues)
- Join our [Community Discord](https://discord.gg/clawchat)

## Security Model

### Port Rotation
- Service runs on a random port (8000-9000 range)
- Port changes every hour at :00 minutes
- New port encrypted and uploaded to Mega.nz
- Clients download and decrypt config to discover port

### Key Exchange
1. **Initial Setup:** Get decryption key via secure channel
2. **Client Discovery:** Download encrypted config from Mega.nz
3. **Connection:** Connect to WebSocket on discovered port
4. **Re-keying:** Request new key if current key expires

### Secure Channels for Initial Key
- **OpenClaw TUI:** Built-in terminal interface
- **Slack DM:** Direct message via Slack bot
- **Bash Script:** Manual key entry script

## Development

### Project Structure
```
clawchat/
├── backend/           # Python WebSocket service
│   ├── server.py     # Main WebSocket server
│   ├── config.yaml   # Service configuration
│   └── requirements.txt
├── frontend/         # Browser PWA
│   ├── index.html    # Main HTML file
│   ├── style.css     # Styles
│   ├── app.js        # Main application logic
│   └── service-worker.js
├── scripts/          # Utility scripts
├── tests/            # Unit and integration tests
├── integration/      # OpenClaw integration
├── docs/             # Documentation
└── deploy/           # Deployment scripts
```

### Running Tests

ClawChat includes a comprehensive testing framework with unit tests, integration tests, and coverage reporting.

```bash
# Run all tests with coverage
./run_tests.sh

# Run only unit tests
./run_tests.sh unit

# Run only integration tests
./run_tests.sh integration

# Quick run without coverage
./run_tests.sh quick

# Run with verbose output
./run_tests.sh verbose

# CI mode (strict, fail-fast)
./run_tests.sh ci
```

#### Using pytest directly:
```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ --cov=backend --cov-report=html --cov-report=term

# Run only unit tests
python -m pytest tests/test_websocket.py -v

# Run only integration tests
python -m pytest tests/test_integration.py -v

# Run with specific markers
python -m pytest tests/ -m "not slow"
```

#### Test Structure:
- **`tests/test_websocket.py`** - Unit tests for WebSocket server (connection handling, message types, errors)
- **`tests/test_integration.py`** - Integration tests for client-server communication
- **`tests/mock_mega.py`** - Mock Mega.nz API for testing without real network calls
- **`tests/conftest.py`** - Shared pytest fixtures and configuration

See `tests/README.md` for detailed testing documentation.

### Building for Production
```bash
# Install deployment dependencies
./deploy/install.sh

# Set up as system service
sudo cp deploy/clawchat.service /etc/systemd/system/
sudo systemctl enable clawchat
sudo systemctl start clawchat
```

## Configuration

### Backend Configuration (`config.yaml`)
```yaml
server:
  host: "0.0.0.0"
  port_range: [8000, 9000]
  max_connections: 100
  
security:
  encryption_key: ""  # Set via environment variable
  rotation_interval: 3600  # Seconds (1 hour)
  
logging:
  level: "INFO"
  file: "/var/log/clawchat/server.log"
  
mega:
  config_path: "/clawchat/config.enc"
```

### Frontend Configuration
Configure via `frontend/config.js` (generated during setup):
```javascript
const config = {
  megaConfigUrl: "https://mega.nz/file/...",
  defaultHost: "localhost",
  reconnectInterval: 5000,
  maxRetries: 10
};
```

## API Documentation

### WebSocket Messages

#### Chat Messages
```json
{
  "type": "chat_message",
  "id": "msg_123",
  "timestamp": "2026-02-14T15:30:00Z",
  "sender": "user123",
  "content": "Hello, world!",
  "attachments": []
}
```

#### File Operations
```json
{
  "type": "file_list",
  "path": "/projects",
  "files": [...]
}

{
  "type": "file_upload",
  "filename": "document.pdf",
  "content": "base64_encoded_data",
  "path": "/projects/docs"
}
```

#### System Messages
```json
{
  "type": "connection_status",
  "status": "connected",
  "port": 8765,
  "rotation_time": "2026-02-14T16:00:00Z"
}
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure all code follows the project's coding standards and includes appropriate tests.

## Security

### Reporting Vulnerabilities
If you discover a security vulnerability, please report it responsibly:
1. **DO NOT** create a public GitHub issue
2. Email security@example.com with details
3. Include steps to reproduce and potential impact

### Security Features
- All configuration encrypted at rest
- No secrets stored in source code
- Input validation on all endpoints
- Path traversal protection
- Rate limiting on connections
- Audit logging of all operations

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built for the OpenClaw ecosystem
- Inspired by secure communication systems
- Thanks to all contributors and testers

## Support

- **Documentation:** [docs/](docs/)
- **Issues:** [GitHub Issues](https://github.com/hipparchus2000/clawChat/issues)
- **Discussions:** [GitHub Discussions](https://github.com/hipparchus2000/clawChat/discussions)

---

**Project Status:** 🚀 Active Development  
**Version:** 0.1.0-alpha  
**Last Updated:** February 14, 2026