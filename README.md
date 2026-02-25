# ClawChat - Secure P2P Communication System

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/github/license/hipparchus2000/clawChat)

A secure peer-to-peer communication system featuring UDP hole punching, end-to-end encryption, and AI-powered assistance.

## 🚀 Current Implementation

**The active implementation is in [`udp_hole_punching/`](udp_hole_punching/)** - a Python-based UDP hole punching system with Tkinter GUI client.

### What's New in v2.1

- 🤖 **LLM Bridge** - DeepSeek/OpenAI/Anthropic integration
- 📝 **Context System** - OpenClaw-style agentic loop (SOUL → AGENTS → USER → MEMORY)
- ⏰ **Cron Scheduler** - Automated AI task execution via CRON.md
- 📁 **File Manager** - Full remote file operations (list, download, upload, delete, rename)
- 🖥️ **GUI Client** - Three-tab interface (Chat, Files, Crontab)
- 🔒 **Fixed Security File** - Single `clawchat-current.sec` filename
- ⏱️ **Shorter Validity** - 11 minute validity with 10 minute auto-regeneration

### v2.0 Features

- 🔒 **File-Based Security Exchange** - No cloud dependency (replaced Mega.nz)
- 🕳️ **UDP Hole Punching** - Direct P2P connections through NAT
- 🔐 **AES-256-GCM Encryption** - End-to-end encryption
- 🔄 **In-Band Key Rotation** - Automatic hourly key rotation
- 🚨 **Compromised Protocol** - Emergency key destruction

## 📁 Repository Structure

```
clawChat/
├── udp_hole_punching/          # ACTIVE: UDP hole punching implementation
│   ├── src/                    # Source code (client, server, protocol)
│   ├── context/                # AI context files (SOUL.md, AGENTS.md, etc.)
│   ├── docs/                   # Implementation-specific docs
│   └── scripts/                # Installation scripts
│
├── docs/                       # ARCHIVED: Original WebSocket documentation
│   └── README.md               # See archive notice
│
├── backend-archive/            # ARCHIVED: WebSocket backend
├── frontend-archive/           # ARCHIVED: Browser PWA client
│
├── tests/                      # Test files
├── AGENTS.md                   # Agent context for AI assistants
└── README.md                   # This file
```

## 🏃 Quick Start

### Server (Ubuntu VPS)

```bash
cd udp_hole_punching
sudo bash scripts/install_server.sh
sudo systemctl start clawchat-server
```

See [`udp_hole_punching/README.md`](udp_hole_punching/README.md) for full server setup.

### Client (Windows/Linux/Mac)

```bash
cd udp_hole_punching
pip install -r requirements.txt
python run_client.py  # or run_gui_client.py for GUI
```

Select the `.sec` security file via the file browser to connect.

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [`udp_hole_punching/README.md`](udp_hole_punching/README.md) | Main implementation guide |
| [`udp_hole_punching/CONTEXT_SYSTEM.md`](udp_hole_punching/CONTEXT_SYSTEM.md) | OpenClaw-style AI context system |
| [`udp_hole_punching/CRON_SYSTEM.md`](udp_hole_punching/CRON_SYSTEM.md) | Automated AI task scheduling |
| [`udp_hole_punching/FILE_PROTOCOL.md`](udp_hole_punching/FILE_PROTOCOL.md) | File manager protocol spec |
| [`udp_hole_punching/LLM_BRIDGE.md`](udp_hole_punching/LLM_BRIDGE.md) | LLM integration guide |
| [`AGENTS.md`](AGENTS.md) | Agent context for AI assistants |

## 🏗️ Architecture

```
┌─────────────────┐      Encrypted UDP       ┌─────────────────┐
│   GUI Client    │◀───────────────────────▶│  ClawChat Server│
│   (Tkinter)     │    AES-256-GCM + PFS    │  (Python/UDP)   │
└─────────────────┘                         └────────┬────────┘
       │                                             │
       │ 1. Select .sec file                         │
       │ 2. Load IP, port, shared secret             │
       │ 3. Establish encrypted connection           │
       │                                             │
       │                    ┌───────────────────────┘
       │                    │ LLM Bridge (DeepSeek/OpenAI/Anthropic)
       │                    │ Cron Scheduler (AI task automation)
       │                    │ File Protocol Handler
       │                    ▼
                   ┌─────────────────┐
                   │  AI Assistant   │
                   │  Context-Aware  │
                   └─────────────────┘
```

## 🔐 Security Model

- **Bootstrap Key**: Protect the key used to encrypt security files (from `.env`)
- **Security Files**: `clawchat-current.sec` contains ephemeral connection credentials
- **File Transfer**: Transfer `.sec` files securely (USB, encrypted message)
- **Validity**: Security files expire after 11 minutes
- **Auto-Regeneration**: New file generated every 10 minutes until client connects
- **Key Rotation**: Session keys rotate automatically every hour after connection
- **Compromised Protocol**: Emergency key destruction if suspected breach

## 🛠️ Development

```bash
# Install dependencies
cd udp_hole_punching
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env and add your API keys

# Run LLM server (with AI - uses CLAWCHAT_LLM_PROVIDER from .env)
python run_llm_server.py

# Or specify provider manually
python run_llm_server.py --provider deepseek

# Run standard server (echo only)
python run_server.py --ip 127.0.0.1 --port 55555

# Run GUI client
python run_gui_client.py
```

## 📦 Project History

- **v1.0**: WebSocket-based chat with Mega.nz config storage
- **v2.0**: UDP hole punching, file-based security exchange
- **v2.1**: LLM Bridge, Context System, Cron Scheduler, File Manager Protocol

See [`docs/README.md`](docs/README.md) for archived v1.0 documentation.

## 🤝 Contributing

See [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) for contribution guidelines.

## 📄 License

MIT License - See [LICENSE](LICENSE) file

## 🆘 Support

- Check [`udp_hole_punching/README.md`](udp_hole_punching/README.md) troubleshooting section
- Review logs: `sudo journalctl -u clawchat-server -f`
- See archived docs in `docs/` for historical reference
