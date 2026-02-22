# Python UDP Hole Punching Implementation Plan
## For Kimi K2.5 CLI Development Session (2026-02-17)

**Objective:** Replace current ClawChat security mechanism with Python-based UDP hole punching using Mega.nz as secure signaling channel.

**Date:** 2026-02-17  
**Tools:** Kimi K2.5 Code CLI + OpenClaw coordination  
**Status:** Planning complete, ready for implementation

---

## **Architecture Overview**

### **Components:**
1. **Mega.nz Secure Signaling** - Encrypted file drop for handshake
2. **Python Client** - Runs on user's PC, initiates connections
3. **Python Server** - Dark server (no open ports), responds to connections
4. **UDP Hole Punching Engine** - Establishes direct P2P connections
5. **Encrypted UDP Communication** - Secure data channel
6. **Hourly Port Rotation** - Security through port changes

### **Workflow:**
```
[CLIENT]                           [MEGA.NZ]                           [SERVER]
   |                                   |                                   |
   |---(1) Drop encrypted handshake--->|                                   |
   |                                   |<--(2) Server monitors folder------|
   |                                   |---(3) Server responds------------>|
   |<--(4) Client picks up response----|                                   |
   |                                   |                                   |
   |---(5) UDP hole punch at agreed time--------------------------------->|
   |<--(6) Server responds via UDP----------------------------------------|
   |                                                                      |
   |---(7) Encrypted UDP communication----------------------------------->|
   |<--(8) Hourly port rotation-------------------------------------------|
```

---

## **Phase 1: Mega.nz Secure Signaling**

### **File Structure on Mega.nz:**
```
/temp-share/clawchat-connections/
├── handshake-[timestamp]-[random].bin    (client → server)
├── response-[connection-id].bin          (server → client)
└── cleanup/                              (expired files)
```

### **Encrypted File Format (JSON):**

**Client Handshake:**
```json
{
  "version": "1.0",
  "type": "client_handshake",
  "connection_id": "clawchat-20260217-abc123",
  "client_public_ip": "123.456.789.012",      // From STUN or detection
  "client_udp_port": 54321,                   // Proposed port
  "proposed_time_utc": "2026-02-17T10:00:00Z", // When to connect
  "secret_hash": "sha256(shared_secret + connection_id)",
  "timestamp": "2026-02-17T09:58:00Z",
  "expires": "2026-02-17T10:03:00Z",          // 5-minute expiry
  "nat_type": "full_cone"                     // Optional: detected NAT type
}
```

**Server Response:**
```json
{
  "version": "1.0",
  "type": "server_response",
  "connection_id": "clawchat-20260217-abc123",
  "server_public_ip": "987.654.321.098",
  "server_udp_port": 12345,
  "agreed_time_utc": "2026-02-17T10:00:00Z",   // Confirmed connection time
  "time_window_seconds": 60,                   // Attempt connection for 60s
  "secret_hash": "sha256(shared_secret + connection_id)",
  "timestamp": "2026-02-17T09:59:00Z",
  "expires": "2026-02-17T10:04:00Z",
  "next_port_change": "2026-02-17T11:00:00Z"   // Hourly rotation
}
```

### **Encryption Scheme:**
- **Algorithm:** AES-256-GCM
- **Key:** Derived from shared secret + connection_id
- **Authentication:** GCM provides encryption + integrity
- **Time-limited:** Files auto-expire after 5 minutes

---

## **Phase 2: UDP Hole Punching Implementation**

### **Connection Algorithm:**
```python
# Pseudo-code for hole punching
def establish_udp_connection(client_ip, client_port, server_ip, server_port, agreed_time):
    # Both sides run this at agreed_time ±30 seconds
    
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', local_port))
    sock.settimeout(10)
    
    # Attempt connection for 60 seconds
    start_time = time.time()
    while time.time() - start_time < 60:
        # Send packet to other side
        sock.sendto(b'PUNCH', (other_ip, other_port))
        
        # Try to receive
        try:
            data, addr = sock.recvfrom(1024)
            if data == b'PUNCH_ACK':
                return sock  # Connection established
        except socket.timeout:
            continue
    
    return None  # Failed
```

### **NAT Traversal Strategies:**
1. **Simultaneous transmission** - Both send at same time
2. **Multiple attempts** - Try different port combinations
3. **STUN discovery** - Use Google STUN to find public IP/port
4. **Fallback options** - If hole punching fails after 3 attempts

---

## **Phase 3: Python Implementation Details**

### **Required Python Modules:**
```python
# Core dependencies
import socket          # UDP networking
import json            # Message formatting
import time            # Timing and synchronization
import hashlib         # Secret hashing
import threading       # Concurrent operations

# Encryption
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Mega.nz integration
import mega            # Or use mega-cmd via subprocess
# Alternative: Use workspace scripts/mega-* commands
```

### **Project Structure:**
```
clawchat-python-udp/
├── src/
│   ├── __init__.py
│   ├── signaling/
│   │   ├── mega_client.py      # Mega.nz file operations
│   │   ├── encryption.py       # AES-256-GCM encryption
│   │   └── message_format.py   # JSON message structures
│   ├── networking/
│   │   ├── udp_hole_punch.py   # Hole punching engine
│   │   ├── nat_detection.py    # Detect NAT type
│   │   └── stun_client.py      # Google STUN for IP discovery
│   ├── client/
│   │   ├── main.py             # Client entry point
│   │   └── connection_mgr.py   # Manage connections
│   └── server/
│       ├── main.py             # Server entry point
│       └── session_mgr.py      # Manage client sessions
├── config/
│   ├── settings.yaml           # Configuration
│   └── secrets.example.yaml    # Template for secrets
├── tests/
│   ├── test_signaling.py
│   ├── test_networking.py
│   └── integration_test.py
├── requirements.txt
├── README.md
└── run_client.py / run_server.py
```

---

## **Phase 4: Development Tasks for Kimi K2.5 CLI**

### **Task 1: Mega.nz Signaling Module** (2-3 hours)
- [ ] Create `mega_client.py` with upload/download functions
- [ ] Implement file monitoring with polling/notification
- [ ] Add encryption/decryption with AES-256-GCM
- [ ] Create message format validation
- [ ] Implement file cleanup (remove expired files)

### **Task 2: UDP Hole Punching Engine** (2-3 hours)
- [ ] Create `udp_hole_punch.py` with connection algorithm
- [ ] Implement NAT type detection
- [ ] Add Google STUN integration for IP discovery
- [ ] Create connection state machine
- [ ] Implement retry logic with exponential backoff

### **Task 3: Client Implementation** (1-2 hours)
- [ ] Create client CLI interface
- [ ] Implement handshake initiation
- [ ] Add connection monitoring
- [ ] Create status display
- [ ] Implement graceful shutdown

### **Task 4: Server Implementation** (1-2 hours)
- [ ] Create server daemon
- [ ] Implement Mega.nz folder monitoring
- [ ] Add session management
- [ ] Create logging system
- [ ] Implement hourly port rotation

### **Task 5: Integration & Testing** (1-2 hours)
- [ ] End-to-end testing
- [ ] NAT traversal testing (different NAT types)
- [ ] Security testing (encryption validation)
- [ ] Performance testing (latency, throughput)
- [ ] Documentation and examples

---

## **Phase 5: Security Considerations**

### **Encryption:**
- Use AES-256-GCM for file encryption
- Derive keys from shared secret + connection_id
- Include timestamps to prevent replay attacks
- Implement key rotation (hourly with port change)

### **Authentication:**
- Shared secret established out-of-band (initial setup)
- Hash verification in each message
- Time-limited validity (5-minute windows)
- Connection ID uniqueness

### **Network Security:**
- UDP packets encrypted with session keys
- Rate limiting to prevent DoS
- Port rotation every hour
- No persistent listening ports

### **Mega.nz Security:**
- Use temporary folders only
- Automatic cleanup of old files
- Encrypted file names (optional)
- Monitor for unauthorized access

---

## **Phase 6: Testing Strategy**

### **Unit Tests:**
1. Encryption/decryption correctness
2. Message format validation
3. Mega.nz file operations
4. UDP socket operations
5. NAT detection logic

### **Integration Tests:**
1. Complete handshake flow (client → Mega.nz → server)
2. UDP hole punching success scenarios
3. Failure scenarios (timeouts, NAT failures)
4. Port rotation mechanism
5. Reconnection after network drop

### **Real-world Testing:**
1. Different NAT types (full-cone, restricted, symmetric)
2. Various network conditions (latency, packet loss)
3. Multiple concurrent connections
4. Long-running stability (24+ hours)
5. Cross-platform testing (Windows, Linux, macOS)

---

## **Phase 7: Deployment Plan**

### **Initial Deployment:**
1. **Week 1:** Prototype with basic functionality
2. **Week 2:** Add error handling and logging
3. **Week 3:** Security hardening and testing
4. **Week 4:** Documentation and user guides

### **Migration from Current System:**
1. Run both systems in parallel
2. Gradual migration of users
3. Fallback to old system if new one fails
4. Complete switchover after 2 weeks of stability

### **Monitoring:**
- Connection success rates
- NAT traversal statistics
- Mega.nz API usage
- Error rates and types
- Performance metrics (latency, throughput)

---

## **Phase 8: Kimi K2.5 CLI Session Plan - AGGRESSIVE TIMELINE**

### **Phase 1: Core Implementation (30 minutes)**
- **Focus:** Bare essentials for working prototype
- **Task:** Create minimal viable implementation
- **Deliverables:** Basic end-to-end connection working

### **Phase 2: Essential Features (20 minutes)**
- **Focus:** Add critical functionality
- **Task:** Enhance with encryption and error handling
- **Deliverables:** Reliable connection with security basics

### **Phase 3: Testing & Polish (10 minutes)**
- **Focus:** Make it work reliably
- **Task:** Final touches and basic testing
- **Deliverables:** Working prototype ready for testing

**TOTAL TIME:** **1 HOUR MAX** - Kimi is fast, focus on core functionality only

---

## **Resources & References**

### **Python Libraries:**
- `cryptography` - AES-256-GCM encryption
- `mega.py` - Mega.nz API (or use `mega-cmd`)
- `stun` - STUN client for NAT detection
- `python-socketio` - Optional for WebSocket fallback

### **Documentation:**
- UDP Hole Punching: RFC 5128
- AES-GCM: NIST SP 800-38D
- Mega.nz API: https://github.com/odwyersoftware/mega.py
- Python socket: https://docs.python.org/3/library/socket.html

### **Workspace Assets:**
- Mega.nz credentials: `/home/openclaw/.openclaw/workspace/mega.creds`
- Existing scripts: `/home/openclaw/.openclaw/workspace/scripts/`
- ClawChat codebase: `/home/openclaw/.openclaw/workspace/projects/clawchat/`

---

## **Success Criteria**

### **Minimum Viable Product:**
1. ✅ Secure handshake via Mega.nz (encrypted, time-limited)
2. ✅ UDP hole punching establishes direct connection
3. ✅ Encrypted UDP communication
4. ✅ Hourly port rotation
5. ✅ Basic error handling

### **Stretch Goals:**
1. ✅ NAT type detection and adaptive strategies
2. ✅ WebSocket fallback for restrictive networks
3. ✅ GUI interface (Tkinter or web-based)
4. ✅ Mobile client support (Termux on Android)
5. ✅ Integration with existing ClawChat features

---

## **Risks & Mitigations**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Symmetric NAT traversal fails | High | Implement TURN fallback, multiple attempts |
| Mega.nz API changes | Medium | Abstract API layer, monitor for updates |
| Time synchronization issues | Medium | Use NTP, allow ±30 second windows |
| Encryption vulnerabilities | High | Use standard libraries, security audit |
| UDP packet loss | Medium | Implement retransmission, FEC |
| Port conflicts | Low | Dynamic port selection, conflict detection |

---

## **Ready for Kimi K2.5 CLI Session**

**Next Steps Tomorrow:**
1. **Morning:** Start with Task 1 (Mega.nz signaling)
2. **Afternoon:** Move to Task 2 (UDP hole punching)  
3. **Evening:** Integrate and test
4. **Document:** Update ClawChat with new architecture

**Preparation Needed:**
- Ensure Kimi CLI has access to workspace
- Verify Mega.nz credentials work
- Test Python environment (3.8+ with required libraries)
- Review existing ClawChat code for integration points

---

*Plan created: 2026-02-17 01:17 UTC*  
*For implementation: 2026-02-17 (Tomorrow)*  
*Using: Kimi K2.5 Code CLI + OpenClaw coordination*  

**Let's build a robust, secure P2P communication system!** 🚀