# Kimi K2.5 CLI Swarm Instruction
## Python UDP Hole Punching Implementation
### For Execution: 2026-02-17

**Target:** Implement Python-based UDP hole punching with Mega.nz signaling for ClawChat
**Model:** Kimi K2.5 Code CLI
**Context:** Full plan in `python-udp-hole-punching-plan.md`
**Time Estimate:** **1 HOUR MAX** - Kimi is fast, focus on core functionality
**Important:** Web client approach is FROZEN - focus only on Python implementation
**Priority:** Working prototype > perfection

---

## **SWARM ACTIVATION COMMAND**

When ready to begin, run Kimi K2.5 CLI with this instruction:

```
Implement Python UDP hole punching system for ClawChat with Mega.nz signaling.

WORKSPACE: /home/openclaw/.openclaw/workspace/projects/clawchat/
PLAN: Read python-udp-hole-punching-plan.md first
TARGET: Create production-ready Python implementation

CORE REQUIREMENTS:
1. Mega.nz secure signaling (encrypted file drop)
2. UDP hole punching for direct P2P connections
3. Dark server compatible (no open ports)
4. Hourly port rotation
5. AES-256-GCM encryption

DELIVERABLES:
1. Complete Python codebase in clawchat-python-udp/ folder
2. Working client and server implementations
3. Documentation and examples
4. Testing suite

REFERENCE FILES:
- python-udp-hole-punching-plan.md (detailed implementation guide)
- security-mechanism-mega-udp.md (original concept)
- todo.md (updated task list)
- Existing ClawChat codebase for integration points

WORKSPACE ASSETS:
- Mega.nz credentials: /home/openclaw/.openclaw/workspace/mega.creds
- Python scripts: /home/openclaw/.openclaw/workspace/scripts/
- Kimi CLI wrapper: /home/openclaw/.openclaw/workspace/kimi/

START WITH: Phase 1 - Mega.nz Signaling Module
```

---

## **AGGRESSIVE TIMELINE (1 HOUR TOTAL)**

### **Phase 1: Core Implementation (30 minutes)**
```
Focus: Bare essentials for working prototype
Task: Create minimal viable implementation:
  - mega_simple.py: Basic Mega.nz file upload/download
  - udp_simple.py: UDP hole punching with fixed ports
  - client_simple.py: Client that initiates connection
  - server_simple.py: Server that responds
Goal: Basic end-to-end connection working
```

### **Phase 2: Essential Features (20 minutes)**
```
Focus: Add critical functionality
Task: Enhance with:
  - Simple encryption (AES-256 basic)
  - Time synchronization (UTC timestamps)
  - Basic error handling
  - Connection status display
Goal: Reliable connection with security basics
```

### **Phase 3: Testing & Polish (10 minutes)**
```
Focus: Make it work reliably
Task: Final touches:
  - Local testing script
  - Basic documentation
  - Fix any obvious bugs
  - Create run instructions
Goal: Working prototype ready for testing
```

---

## **TECHNICAL SPECIFICATIONS (QUICK REFERENCE)**

### **Encryption:**
- Algorithm: AES-256-GCM
- Key derivation: PBKDF2 from shared secret + connection_id
- File format: JSON with timestamp and expiry

### **Mega.nz Integration:**
- Use `mega.py` library or `mega-cmd` commands
- Folder: `/temp-share/clawchat-connections/`
- File naming: `handshake-[timestamp]-[random].bin`
- Cleanup: Remove files > 5 minutes old

### **UDP Hole Punching:**
- Python `socket` module
- Simultaneous transmission at agreed time
- NAT type detection and adaptive strategies
- Fallback after 3 failed attempts

### **Message Format (Decrypted):**
```json
{
  "version": "1.0",
  "type": "client_handshake|server_response",
  "connection_id": "string",
  "public_ip": "string",
  "udp_port": number,
  "agreed_time_utc": "ISO8601",
  "secret_hash": "sha256",
  "timestamp": "ISO8601",
  "expires": "ISO8601"
}
```

---

## **DEPENDENCIES TO INSTALL**

```bash
# Core Python libraries
pip install cryptography          # AES-256-GCM encryption
pip install mega.py               # Mega.nz API (or use mega-cmd)
pip install stun                  # STUN client for NAT detection
pip install python-socketio       # Optional WebSocket fallback

# Development tools
pip install pytest                # Testing framework
pip install black                 # Code formatting
pip install mypy                  # Type checking
```

---

## **TESTING COMMANDS**

```bash
# Unit tests
python -m pytest tests/test_signaling.py -v
python -m pytest tests/test_networking.py -v

# Integration test
python tests/integration_test.py

# Run client
python run_client.py --config config/settings.yaml

# Run server
python run_server.py --config config/settings.yaml
```

---

## **SUCCESS VALIDATION**

Run these checks before declaring completion:

1. **File Encryption Test:**
```bash
python -c "from src.signaling.encryption import test_encryption; test_encryption()"
```

2. **Mega.nz Connectivity Test:**
```bash
python -c "from src.signaling.mega_client import test_connectivity; test_connectivity()"
```

3. **UDP Hole Punch Test (Local):**
```bash
python tests/local_hole_punch_test.py
```

4. **End-to-End Test:**
```bash
# Terminal 1: Start server
python run_server.py --test-mode

# Terminal 2: Start client
python run_client.py --test-mode --connect-to localhost

# Should establish connection within 60 seconds
```

---

## **INTEGRATION WITH EXISTING CLAWCHAT**

### **Migration Path:**
1. New system runs alongside old WebSocket system
2. Gradual user migration
3. Fallback to old system if new one fails
4. Complete switchover after stability confirmed

### **Configuration Bridge:**
- Read existing ClawChat configs
- Convert to new Python UDP format
- Maintain backward compatibility during transition

### **Feature Parity:**
- Chat messaging over encrypted UDP
- File transfer capabilities
- User presence indicators
- Connection status monitoring

---

## **TROUBLESHOOTING GUIDE**

### **Common Issues & Solutions:**

**Issue 1: Mega.nz authentication fails**
- Check credentials in `mega.creds`
- Test with `mega-ls /temp-share`
- Ensure internet connectivity

**Issue 2: UDP hole punching fails**
- Check NAT type (run `src/networking/nat_detection.py`)
- Try different port ranges
- Increase connection attempt window
- Consider TURN fallback for symmetric NAT

**Issue 3: Time synchronization issues**
- Use NTP time synchronization
- Increase time window (±60 seconds)
- Add clock drift compensation

**Issue 4: Encryption/decryption fails**
- Verify shared secret is identical
- Check timestamp freshness (within 5 minutes)
- Ensure same key derivation algorithm

---

## **PERFORMANCE OPTIMIZATION TIPS**

1. **Connection Establishment:**
   - Cache NAT type detection results
   - Reuse UDP sockets when possible
   - Parallelize Mega.nz operations

2. **Mega.nz Usage:**
   - Batch file operations
   - Use efficient polling intervals
   - Implement exponential backoff for errors

3. **UDP Communication:**
   - Use MTU-sized packets (1472 bytes)
   - Implement congestion control
   - Add forward error correction for lossy networks

---

## **SECURITY CHECKS**

Before deployment, verify:

1. **Encryption:**
   - No hardcoded secrets in code
   - Proper key derivation
   - Fresh randomness for each connection

2. **Network Security:**
   - Rate limiting implemented
   - Port rotation working
   - No information leakage in error messages

3. **Mega.nz Security:**
   - Files properly encrypted
   - Automatic cleanup working
   - No sensitive data in file names

---

## **DELIVERY CHECKLIST**

Before marking task complete:

- [ ] All code in `clawchat-python-udp/` folder
- [ ] Working client (`run_client.py`)
- [ ] Working server (`run_server.py`)
- [ ] Complete test suite (`tests/`)
- [ ] Documentation (`README.md`, `INSTALL.md`)
- [ ] Configuration examples (`config/`)
- [ ] Integration guide with existing ClawChat
- [ ] Performance benchmarks
- [ ] Security audit report

---

## **NEXT STEPS AFTER IMPLEMENTATION**

1. **Testing Phase:** 1-2 days of rigorous testing
2. **Beta Deployment:** Limited user testing
3. **Production Rollout:** Gradual migration
4. **Monitoring Setup:** Track success rates, performance
5. **Maintenance Plan:** Updates, bug fixes, improvements

---

## **CONTACT & SUPPORT**

**For issues during implementation:**
- Refer to `python-udp-hole-punching-plan.md`
- Check existing ClawChat code for patterns
- Use workspace scripts as reference
- Document any problems encountered

**Integration questions:**
- Review ClawChat architecture in `README.md`
- Check `security-mechanism-mega-udp.md` for original concept
- Refer to `todo.md` for overall project context

---

**READY FOR SWARM ACTIVATION - 1 HOUR CHALLENGE**

When you begin:
1. **SKIM** `python-udp-hole-punching-plan.md` for architecture
2. **FOCUS** on core functionality only
3. **BUILD** working prototype first
4. **OPTIMIZE** for speed over perfection
5. **TEST** locally before adding features

**Kimi can do this in under an hour!** Focus on:
- ✅ Mega.nz file drop/retrieval (simple)
- ✅ UDP hole punching (basic implementation)
- ✅ Client/server communication (minimal)
- ✅ Encryption (AES-256 basic)

**Skip for now:**
- ❌ Extensive error handling
- ❌ Fancy logging
- ❌ Complex configuration
- ❌ Production hardening

**GO FOR SPEED!** 🚀💨

---

*Swarm instruction created: 2026-02-17 01:19 UTC*
*For execution: 2026-02-17*
*Using: Kimi K2.5 Code CLI swarm approach*