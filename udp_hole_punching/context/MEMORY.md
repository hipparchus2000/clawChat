# MEMORY - Long-Term Knowledge

## Project Facts: ClawChat

### Architecture Decisions

#### Why UDP Hole Punching?
- Avoids centralized servers for messaging
- Works through most NATs (except symmetric)
- Lower latency than relay servers
- Dark server compatible (no open ports)

#### Why File-Based Security Exchange?
- Mega.nz added paywall
- Out-of-band transfer is secure (USB, encrypted message)
- No cloud dependency
- User controls key distribution

#### Why AES-256-GCM?
- Authenticated encryption (prevents tampering)
- Hardware acceleration on modern CPUs
- Well-vetted, industry standard
- Single key for encryption + integrity

### Technical Specifications

#### Port Range
- **Ephemeral**: 49152-65535 (IANA recommended)
- **Rotation**: Every hour (3600 seconds)
- **Grace Period**: 5 minutes for existing connections

#### Encryption Keys
- **Bootstrap Key**: Derives security file encryption
- **Shared Secret**: 32 bytes, generated per session
- **Session Keys**: Derived via HKDF-SHA256
- **Key Rotation**: Hourly, in-band via encrypted channel

#### Message Format
```
[Type:1][Timestamp:8][ID_Len:1][ID][Payload_Len:4][Payload]
Encrypted with AES-256-GCM
```

### Known Issues & Solutions

#### Symmetric NAT
**Problem**: UDP hole punching fails on symmetric NAT
**Solution**: Document limitation, suggest alternatives (TURN, VPN)
**Status**: Acceptable limitation for v1

#### Message Encoding Bug
**Problem**: Unicode errors in message parsing (`'utf-8' codec can't decode`)
**Solution**: Fixed struct format from `!Bdf` to `!BdB`
**Location**: `src/protocol/messages.py`

#### Bootstrap Key Mismatch
**Problem**: Client can't decrypt security file
**Cause**: Different keys in server vs client
**Solution**: Use `.env` file for consistent keys
**Status**: Resolved with python-dotenv

#### Hole Punching on Localhost
**Problem**: WinError 10049 on 127.0.0.1
**Cause**: Hole punching designed for NAT, not localhost
**Solution**: Use direct UDP connection for localhost testing
**Status**: Works with direct connection fallback

### Successful Patterns

#### Testing Local Changes
```powershell
cd udp_hole_punching
python test_local_simple.py  # Quick verification
python test_context.py       # Check context loading
python interactive_test.py   # Manual testing
```

#### Server Deployment (VPS)
```bash
# 1. Create user
sudo useradd -r -s /bin/false openclaw

# 2. Set up directories
mkdir -p /home/openclaw/clawchat/{security,logs}

# 3. Install service
sudo cp scripts/clawchat-server.service /etc/systemd/system/
sudo systemctl enable clawchat-server
```

#### Security Best Practices
- Bootstrap key: 32 bytes exactly
- Security files: 600 permissions (owner only)
- Directory: 700 permissions
- Never commit `.env`

### Library Versions
- `cryptography>=41.0.0` - For AES-GCM
- `python-dotenv>=1.0.0` - For .env file support
- `requests>=2.31.0` - For LLM API calls

### API Endpoints (LLM)

#### DeepSeek
```
Base: https://api.deepseek.com/v1
Model: deepseek-chat
Key Env: DEEPSEEK_API_KEY
```

#### OpenAI
```
Base: https://api.openai.com/v1
Model: gpt-3.5-turbo
Key Env: OPENAI_API_KEY
```

#### Anthropic
```
Base: https://api.anthropic.com/v1
Model: claude-3-haiku-20240307
Key Env: ANTHROPIC_API_KEY
```

### User Habits (Learned)

#### Development Flow
1. Tests locally first (Windows)
2. Archives old code before major changes
3. Prefers working code over perfect docs
4. Updates AGENTS.md when process changes

#### Communication Style
- Uses "swarm:" prefix for multi-agent tasks
- Short, direct requests
- Security-conscious (asks about key handling)
- Patient with debugging

#### Common Commands
```powershell
# Check running processes
Get-Process python | Select-Object Id, CommandLine

# View server logs
tail -f C:\temp\clawchat\logs\server.log

# Test connection
python test_local_simple.py
```

### Project Conventions

#### Naming
- Security files: `clawchat-YYYYMMDD-HHMMSS.sec`
- Session saves: `llm_session.json`
- Context files: UPPERCASE.md

#### Directory Structure
```
udp_hole_punching/
├── src/           # Source code
├── context/       # LLM personality files
│   ├── SOUL.md
│   ├── AGENTS.md
│   ├── USER.md
│   ├── MEMORY.md
│   └── memory/    # Daily conversation logs
├── scripts/       # Installation scripts
└── config/        # YAML configs
```

### Historical Decisions

#### Why Removed Mega.nz?
- Paywall introduced
- Privacy concerns
- Dependency on external service
- File-based exchange is simpler

#### Why Not WebRTC?
- Requires TURN servers (complexity)
- Browser-based (we wanted Python client)
- UDP hole punching is lighter weight

#### Why Tkinter for GUI?
- Built into Python (no dependencies)
- Cross-platform
- Good enough for this use case
- No web browser needed

### Tips for Future Me

#### When Adding New Features
1. Check AGENTS.md for workflow
2. Update .env.example if new config needed
3. Add to requirements.txt if new dependency
4. Test on localhost first
5. Document in appropriate .md file

#### When Debugging Connection Issues
1. Verify server is running (`Get-Process python`)
2. Check security file exists and is recent
3. Confirm bootstrap keys match
4. Test with `test_local_simple.py`
5. Check firewall (Windows Defender)

#### When Updating Context Files
1. Edit file
2. Restart server to reload
3. Test with `test_context.py`
4. Commit changes to git

---

*Last Updated: 2026-02-22*
*This file is curated - add distilled wisdom, not raw logs*
