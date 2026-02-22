# ClawChat - Agent Context

This file contains project-specific context that persists across conversations. Kimi Code CLI reads this automatically on startup.

---

## Project Overview

**ClawChat** - A chat application with UDP hole punching for P2P communication.

### Tech Stack
- **Server**: Python UDP hole punching server (in `udp_hole_punching/`)
- **Client**: Python with Tkinter GUI (file browser for security files)
- **Key Features**: P2P communication, UDP hole punching, file-based security exchange
- **Security**: AES-256-GCM encryption, in-band key rotation, Compromised Protocol

### Architecture
- UDP-based peer-to-peer messaging
- Security mechanisms for connection establishment
- See `docs/SECURITY_ARCHITECTURE_PLAN.md` for detailed security design

---

## Directory Structure

```
├── udp_hole_punching/     - ACTIVE: UDP hole punching implementation
│   ├── src/               - Source code
│   ├── config/            - Configuration files
│   └── scripts/           - Installation scripts
├── backend-archive/       - ARCHIVED: Legacy WebSocket server
├── frontend-archive/      - ARCHIVED: Original browser client
├── docs/                  - Documentation (markdown files)
├── tests/                 - Test files
├── scripts/               - Utility scripts
├── config.yaml.example    - Configuration template
└── .env.example           - Environment variables template
```

---

## Development Conventions

### Code Style
- Python: Follow PEP 8
- Use meaningful variable names
- Add docstrings for public functions

### Security Considerations
- See `docs/SECURITY_PROTOCOL_SPECIFICATION.md`
- All security mechanisms documented in `docs/security-*.md` files

### Testing
- Run tests with `run_tests.sh` or `pytest`
- Configuration in `pytest.ini`

---

## Key Configuration Files

| File | Purpose |
|------|---------|
| `config.yaml.example` | Application configuration template |
| `.env.example` | Environment variables template |
| `pytest.ini` | Test configuration |

---

## Important Notes

<!-- Add any persistent notes here that I should remember -->

### User Preferences
- **Operating System**: Windows 11
- **Shell**: Use PowerShell commands (not bash/unix commands)
- **Path separator**: Use backslashes (`\`) or forward slashes, but be mindful of Windows conventions

### Common Commands
- (To be filled by user)

### Known Issues / TODOs
- See `docs/todo.md` for task tracking

### Architecture Changes (2026-02-22)
- **REMOVED**: Mega.nz integration (paywall issues)
- **NEW**: File-based security exchange in `/home/openclaw/clawchat/security/`
- **NEW**: Compromised Protocol for emergency key rotation
- **ARCHIVED**: Original browser client → `frontend-archive/`
- **ARCHIVED**: Legacy WebSocket backend → `backend-archive/`
- **ACTIVE**: Python UDP hole punching client/server in `udp_hole_punching/`

---

## Reference Documentation

Key documents in `docs/`:
- `README.md` - Project overview
- `PROJECT_SPEC.md` - Full specification
- `SECURITY.md` - Security overview
- `CONTRIBUTING.md` - Contribution guidelines
- `CHANGELOG.md` - Version history

---

*Last updated: 2026-02-22*
*To update: Tell me what to add/change and I'll edit this file*
