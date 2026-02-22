# ClawChat Security Architecture Implementation Plan
## Updated: File-Based Security Exchange (No Mega.nz)

## Overview
This document coordinates the implementation of enhanced security features for ClawChat UDP hole punching, including:
- **File-based security exchange** (removed Mega.nz due to paywall)
- Dynamic port rotation
- End-to-end encryption
- Compromised Protocol for emergency key rotation

---

## Current Architecture Analysis

### Existing Components:
1. **Backend Server** (`backend/server.py`): WebSocket server (TCP) - **TO BE REPLACED**
2. **Port Rotation** (`backend/port_rotation.py`): TCP port rotation - **NEEDS UDP ADAPTATION**
3. **Security Module** (`backend/security.py`): File API security - **CAN BE REUSED**
4. **Configuration**: YAML-based config system - **CAN BE REUSED**

### Architecture Changes:
| Old Component | New Component | Status |
|--------------|---------------|--------|
| WebSocket Server (TCP) | UDP Hole Punching Server | New |
| Mega.nz Discovery | File-based Discovery | New |
| Browser Client | Python Client with GUI | New |
| TCP Port Rotation | UDP Port Rotation | Adapted |

---

## Implementation Phases

### Phase 1: Security Protocol Design
**Status:** ✅ Complete (see SECURITY_PROTOCOL_SPECIFICATION.md v2.0)

**Key Changes:**
- Removed Mega.nz integration (paywall)
- Added file-based security exchange
- Added Compromised Protocol for emergency key rotation
- In-band key rotation after initial connection

### Phase 2: Network Protocol Implementation
**Agent:** Network Protocol Agent

**Tasks:**
- Implement dynamic UDP port allocation (random ports 49152-65535)
- Design UDP port rotation system (hourly changes with grace period)
- Create UDP hole punching algorithm
- Handle NAT/firewall traversal (STUN)
- Implement encrypted UDP packet format

### Phase 3: File-Based Discovery System
**Agent:** File Discovery Agent

**Tasks:**
- Create server-side security file generation
- Implement file encryption (AES-256-GCM)
- Design file format with version, IP, port, secret
- Set up `/home/openclaw/clawchat/security/` directory
- Implement client file browser (Tkinter)
- Add file validation and integrity checking

### Phase 4: Encryption Implementation
**Agent:** Encryption Implementation Agent

**Tasks:**
- Implement AES-256-GCM for security files
- Implement AES-256-GCM for UDP packets
- Create secure handshake using shared secret
- Implement in-band key rotation
- Create Compromised Protocol handler

### Phase 5: Client/Server Integration
**Agent:** Client/Server Integration Agent

**Tasks:**
- Create new UDP server with security features
- Build Python client with file browser GUI
- Integrate file-based discovery
- Implement port rotation notification
- Add Compromised Protocol command
- Create error handling for connection failures

### Phase 6: Testing & Deployment
**Agent:** Testing & Deployment Agent

**Tasks:**
- Create comprehensive test suite
- Test port rotation scenarios
- Verify encryption implementation
- Test Compromised Protocol
- Create deployment documentation
- Create systemd service configuration

---

## Technical Specifications

### 1. Security File Format (Encrypted)
```json
{
  "version": "2.0",
  "protocol": "clawchat-file-v2",
  "server_id": "unique-server-identifier",
  "server_public_ip": "45.135.36.44",
  "server_udp_port": 54321,
  "shared_secret": "base64-encoded-32-byte-secret",
  "bootstrap_key_id": "bootstrap-001",
  "timestamp": 1678886400,
  "valid_until": 1678890000,
  "next_rotation": 1678890000,
  "protocol_version": "udp-hole-punch-v1"
}
```

### 2. UDP Port Rotation Algorithm
- Generate random port between 49152-65535
- Rotate every hour (3600 seconds)
- 5-minute grace period for existing connections
- In-band notification of new port (encrypted)

### 3. Key Exchange Protocol
1. **Initial (Out-of-Band):**
   - Server creates encrypted security file
   - User transfers file via secure channel
   - Client loads file via file browser
   - Extract shared secret, IP, port

2. **Subsequent (In-Band):**
   - New keys derived from next_key_seed
   - Exchanged through encrypted UDP channel
   - No file transfer needed

3. **Emergency (Compromised Protocol):**
   - Client sends COMPROMISED signal
   - Both sides delete keys immediately
   - Server generates new security file
   - User transfers new file out-of-band

### 4. Encryption Stack
- **Security Files**: AES-256-GCM with PBKDF2 key derivation
- **UDP Packets**: AES-256-GCM with session keys
- **Key Derivation**: HKDF-SHA256
- **Hashing**: SHA-256

---

## File Structure Changes

### New Files to Create:
1. `udp_hole_punching/src/security/file_manager.py` - File operations
2. `udp_hole_punching/src/security/encryption.py` - AES-256-GCM
3. `udp_hole_punching/src/security/key_rotation.py` - In-band rotation
4. `udp_hole_punching/src/networking/udp_hole_punch.py` - Hole punching
5. `udp_hole_punching/src/networking/nat_detection.py` - NAT detection
6. `udp_hole_punching/src/client/file_browser.py` - Tkinter file browser
7. `udp_hole_punching/src/client/main.py` - Client entry point
8. `udp_hole_punching/src/server/file_generator.py` - Security file creation
9. `udp_hole_punching/src/server/main.py` - Server entry point
10. `udp_hole_punching/src/protocol/compromised.py` - Compromised Protocol
11. `udp_hole_punching/scripts/install_service.sh` - Systemd installer
12. `udp_hole_punching/config/server.yaml` - Server config
13. `udp_hole_punching/config/client.yaml` - Client config

### Files to Archive (Old WebSocket/Browser Approach):
- `frontend/` → `frontend-archive/` (done)
- `backend/server.py` - Can be kept for reference
- `clawchat-simple-server.py` - Archive
- `clawchat-port-8088.py` - Archive

---

## Dependencies Required

### Python Backend/Client:
```txt
cryptography>=41.0.0
pycryptodome>=3.19.0
pyside6>=6.6.0  # Alternative to Tkinter for better GUI
# OR just use built-in tkinter
tkinter  # Built-in
```

### Server System Dependencies:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3-pip python3-venv python3-tk

# Create user
sudo useradd -r -s /bin/false openclaw
```

---

## Directory Structure (Server)

```
/home/openclaw/clawchat/
├── venv/                           # Python virtual environment
├── src/                            # Source code (symlink or copy)
├── config/
│   ├── server.yaml                 # Server configuration
│   └── bootstrap.key               # Bootstrap key (permissions 600)
├── security/
│   ├── clawchat-20260222-143022.sec   # Active security file
│   ├── clawchat-20260222-153022.sec   # Previous (to be deleted)
│   └── archive/                    # Optional archive
├── logs/
│   └── clawchat.log                # Server logs
├── run_server.py                   # Entry point
└── requirements.txt                # Python dependencies
```

---

## Timeline & Milestones

### Week 1: Core Infrastructure
- [ ] File-based security exchange
- [ ] UDP hole punching engine
- [ ] Basic client/server communication

### Week 2: Security & Features
- [ ] AES-256-GCM encryption
- [ ] In-band key rotation
- [ ] Port rotation system
- [ ] Compromised Protocol

### Week 3: Client & GUI
- [ ] Tkinter file browser
- [ ] Client GUI interface
- [ ] Connection status display
- [ ] Compromised Protocol UI

### Week 4: Testing & Deployment
- [ ] Comprehensive testing
- [ ] Systemd service
- [ ] Documentation
- [ ] Deployment guide

---

## Success Criteria

1. **Security**: All communications encrypted end-to-end
2. **File Exchange**: Secure files work without Mega.nz
3. **Reliability**: Seamless port rotation without dropped connections
4. **Usability**: Easy file selection with GUI
5. **Emergency Response**: Compromised Protocol works within 10 seconds
6. **Performance**: <100ms overhead for encryption/decryption

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| File interception during transfer | High | Short validity (1 hour), encrypted file |
| Symmetric NAT traversal fails | High | Implement TURN fallback |
| Key compromise | High | Compromised Protocol for immediate rotation |
| Port conflicts | Low | Dynamic port selection |
| File permission errors | Medium | Proper setup scripts, validation |
| User loses security file | Medium | Server can generate new file on request |

---

## Coordination Notes

All agents should:
1. Update this document with progress
2. Follow the updated specification (v2.0)
3. Coordinate on interfaces between components
4. Follow existing code style and patterns
5. Write comprehensive tests
6. Document all security decisions

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-16 | 1.0 | Initial plan with Mega.nz discovery |
| 2026-02-22 | 2.0 | Removed Mega.nz, added file-based exchange |
| 2026-02-22 | 2.1 | Added Compromised Protocol |

---

## Contact & Communication

- **Main Coordinator**: OpenClaw
- **Location**: `/home/openclaw/.openclaw/workspace/projects/clawchat/`
- **Security Files**: `/home/openclaw/clawchat/security/`

Let's build a secure, robust ClawChat system! 🚀
