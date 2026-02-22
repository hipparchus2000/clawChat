# Python UDP Hole Punching Implementation Plan
## Updated: File-Based Security Exchange (No Mega.nz)

**Objective:** Replace current ClawChat security mechanism with Python-based UDP hole punching using **file-based security exchange** (removed Mega.nz due to paywall).

**Date:** 2026-02-22  
**Status:** Architecture Updated, Ready for Implementation

---

## **Architecture Overview (Updated)**

### **Components:**
1. **File-Based Security Exchange** - Server creates encrypted security files in `/home/openclaw/clawchat/`
2. **Python Client** - Runs on user's PC, uses file browser to select security file
3. **Python Server** - Dark server (no open ports), creates security files
4. **UDP Hole Punching Engine** - Establishes direct P2P connections
5. **Encrypted UDP Communication** - Secure data channel
6. **Hourly Port Rotation** - Security through port changes
7. **Compromised Protocol** - Emergency key rotation via in-band signaling

### **Initial Connection Workflow:**
```
[SERVER]                                [CLIENT]
   |                                         |
   |--(1) Create security file-------------->|
   |   /home/openclaw/clawchat/              |
   |   clawchat-[timestamp].sec              |
   |                                         |
   |--(2) User transfers file via           |
   |   secure channel (USB, encrypted msg)   |
   |                                         |
   |<--(3) Client loads file via --------<---|
   |    file browser popup                   |
   |                                         |
   |--(4) UDP hole punch at agreed time---->|
   |<--(5) Server responds via UDP--------<--|
   |                                         |
   |--(6) Encrypted UDP communication------>|
   |<--(7) Hourly port rotation----------<---|
```

### **Subsequent Security Exchange (In-Band):**
- New security packets exchanged through the encrypted UDP connection
- No file transfer needed after initial connection
- Automatic key rotation every hour

### **Compromised Protocol:**
```
[CLIENT]                                [SERVER]
   |                                         |
   |--(1) Send "COMPROMISED" signal-------->|
   |    through encrypted channel            |
   |                                         |
   |<--(2) Acknowledge, delete keys------<--|
   |    both sides delete security files     |
   |                                         |
   |--(3) Server creates new security file->|
   |                                         |
   |<--(4) User transfers new file -------<--|
   |    via secure out-of-band channel       |
```

---

## **Phase 1: File-Based Security Exchange**

### **Server Directory Structure:**
```
/home/openclaw/clawchat/
├── security/
│   ├── clawchat-20260222-143022.sec    # Active security file
│   ├── clawchat-20260222-153022.sec    # Previous (expired)
│   └── archive/                        # Old files (optional)
├── logs/
│   └── clawchat.log
└── config/
    └── settings.yaml
```

### **Security File Format (Encrypted JSON):**

**File Name:** `clawchat-[YYYYMMDD-HHMMSS].sec`

**Contents (encrypted with AES-256-GCM):**
```json
{
  "version": "1.0",
  "type": "initial_handshake",
  "connection_id": "clawchat-20260222-abc123",
  "server_public_ip": "45.135.36.44",
  "server_udp_port": 54321,
  "shared_secret": "base64-encoded-32-byte-secret",
  "timestamp": "2026-02-22T14:30:00Z",
  "valid_until": "2026-02-22T15:30:00Z",
  "next_rotation": "2026-02-22T15:00:00Z",
  "protocol_version": "udp-hole-punch-v1"
}
```

### **Encryption Scheme:**
- **Algorithm:** AES-256-GCM
- **Key:** Pre-shared master key (distributed separately) OR initial bootstrap key
- **File Permissions:** 600 (owner read/write only)
- **Validity:** 1 hour (matching port rotation)

---

## **Phase 2: UDP Hole Punching Implementation**

### **Connection Algorithm:**
```python
# Pseudo-code for hole punching
def establish_udp_connection(server_ip, server_port, shared_secret):
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 0))  # Bind to any available port
    sock.settimeout(10)
    
    local_port = sock.getsockname()[1]
    
    # Attempt connection for 60 seconds
    start_time = time.time()
    while time.time() - start_time < 60:
        # Send encrypted PUNCH packet
        packet = encrypt_packet(b'PUNCH', shared_secret)
        sock.sendto(packet, (server_ip, server_port))
        
        # Try to receive
        try:
            data, addr = sock.recvfrom(1024)
            decrypted = decrypt_packet(data, shared_secret)
            if decrypted == b'PUNCH_ACK':
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
import tkinter         # File browser GUI
from tkinter import filedialog

# Encryption
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
```

### **Project Structure:**
```
udp_hole_punching/
├── src/
│   ├── __init__.py
│   ├── security/
│   │   ├── file_manager.py     # File-based security exchange
│   │   ├── encryption.py       # AES-256-GCM encryption
│   │   └── key_rotation.py     # In-band key rotation
│   ├── networking/
│   │   ├── udp_hole_punch.py   # Hole punching engine
│   │   ├── nat_detection.py    # Detect NAT type
│   │   └── stun_client.py      # Google STUN for IP discovery
│   ├── client/
│   │   ├── main.py             # Client entry point
│   │   ├── file_browser.py     # Tkinter file browser
│   │   └── connection_mgr.py   # Manage connections
│   ├── server/
│   │   ├── main.py             # Server entry point
│   │   ├── file_generator.py   # Create security files
│   │   └── session_mgr.py      # Manage client sessions
│   └── protocol/
│       ├── compromised.py      # Compromised protocol handler
│       └── messages.py         # Message format definitions
├── config/
│   ├── client.yaml             # Client configuration
│   └── server.yaml             # Server configuration
├── scripts/
│   ├── install_service.sh      # Systemd service installer
│   └── generate_security_file.py  # Manual security file generator
├── requirements.txt
├── README.md
├── INSTALL.md                  # Installation guide
└── run_client.py / run_server.py
```

---

## **Phase 4: Development Tasks**

### **Task 1: File-Based Security Module** (2-3 hours)
- [ ] Create `file_manager.py` for reading/writing security files
- [ ] Implement AES-256-GCM encryption/decryption
- [ ] Create Tkinter file browser popup for client
- [ ] Add file validation and integrity checking
- [ ] Implement automatic file cleanup (expired files)

### **Task 2: UDP Hole Punching Engine** (2-3 hours)
- [ ] Create `udp_hole_punch.py` with connection algorithm
- [ ] Implement NAT type detection
- [ ] Add Google STUN integration for IP discovery
- [ ] Create connection state machine
- [ ] Implement retry logic with exponential backoff

### **Task 3: Client Implementation** (1-2 hours)
- [ ] Create client CLI/GUI interface
- [ ] Implement file browser for security file selection
- [ ] Add connection monitoring
- [ ] Create status display
- [ ] Implement graceful shutdown

### **Task 4: Server Implementation** (1-2 hours)
- [ ] Create server daemon
- [ ] Implement security file generation
- [ ] Add session management
- [ ] Create logging system
- [ ] Implement hourly port rotation

### **Task 5: Compromised Protocol** (1 hour)
- [ ] Implement "COMPROMISED" signal detection
- [ ] Add immediate key deletion on both sides
- [ ] Create new security file generation
- [ ] Add notification system for user

### **Task 6: Integration & Testing** (1-2 hours)
- [ ] End-to-end testing
- [ ] NAT traversal testing (different NAT types)
- [ ] Security testing (encryption validation)
- [ ] Compromised protocol testing
- [ ] Performance testing (latency, throughput)

---

## **Phase 5: Security Considerations**

### **Encryption:**
- Use AES-256-GCM for file encryption
- In-band key rotation through encrypted UDP channel
- Include timestamps to prevent replay attacks
- Implement hourly key rotation (with port change)

### **Authentication:**
- Shared secret in initial security file (out-of-band transfer)
- Hash verification in each message
- Time-limited validity (1-hour windows)
- Connection ID uniqueness

### **Network Security:**
- UDP packets encrypted with session keys
- Rate limiting to prevent DoS
- Port rotation every hour
- No persistent listening ports

### **File Security:**
- Files stored in `/home/openclaw/clawchat/` (owner-only access)
- File permissions: 600 (read/write owner only)
- Automatic cleanup of expired files
- No world-readable files

### **Compromised Protocol:**
- Immediate key deletion on both sides
- New security file generated server-side
- Requires manual out-of-band transfer
- Connection terminated until new keys exchanged

---

## **Phase 6: Deployment Plan**

### **Server Setup (Ubuntu VPS):**

1. **Create user and directory:**
```bash
sudo useradd -r -s /bin/false openclaw
sudo mkdir -p /home/openclaw/clawchat/security
sudo chown -R openclaw:openclaw /home/openclaw/clawchat
sudo chmod 700 /home/openclaw/clawchat
```

2. **Install Python dependencies:**
```bash
sudo apt update
sudo apt install python3-pip python3-venv
python3 -m venv /home/openclaw/clawchat/venv
source /home/openclaw/clawchat/venv/bin/activate
pip install -r requirements.txt
```

3. **Install systemd service:**
```bash
sudo cp scripts/clawchat-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable clawchat-server
sudo systemctl start clawchat-server
```

### **Initial Security File Transfer:**
1. Server generates initial security file
2. User securely transfers file to client (USB, encrypted message, etc.)
3. Client uses file browser to select security file
4. Connection established via UDP hole punching

### **Client Setup:**
```bash
# Install dependencies
pip install -r requirements.txt

# Run client
python run_client.py
# File browser will popup to select security file
```

---

## **Phase 7: Systemd Service Configuration**

### **Service File:** `/etc/systemd/system/clawchat-server.service`
```ini
[Unit]
Description=ClawChat UDP Hole Punching Server
After=network.target

[Service]
Type=simple
User=openclaw
Group=openclaw
WorkingDirectory=/home/openclaw/clawchat
Environment=PYTHONPATH=/home/openclaw/clawchat
Environment=CLAWCHAT_CONFIG=/home/openclaw/clawchat/config/server.yaml
ExecStart=/home/openclaw/clawchat/venv/bin/python /home/openclaw/clawchat/run_server.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=clawchat

# Security hardening
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
```

---

## **Success Criteria**

### **Minimum Viable Product:**
1. ✅ Server creates encrypted security files in `/home/openclaw/clawchat/`
2. ✅ Client uses file browser to select security file
3. ✅ UDP hole punching establishes direct connection
4. ✅ Encrypted UDP communication
5. ✅ Hourly port rotation
6. ✅ In-band key rotation (no file transfer needed after initial)
7. ✅ Compromised protocol for emergency key rotation

### **Stretch Goals:**
1. ✅ NAT type detection and adaptive strategies
2. ✅ GUI client (Tkinter)
3. ✅ Mobile client support (Termux on Android)
4. ✅ Integration with existing ClawChat features
5. ✅ Automatic security file backup

---

## **Risks & Mitigations**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Symmetric NAT traversal fails | High | Implement TURN fallback, multiple attempts |
| Security file interception | High | Short validity (1 hour), encrypted contents |
| Time synchronization issues | Medium | Allow ±30 second windows, NTP sync |
| Encryption vulnerabilities | High | Use standard libraries, security audit |
| UDP packet loss | Medium | Implement retransmission, FEC |
| Port conflicts | Low | Dynamic port selection, conflict detection |
| Compromised keys | Medium | Compromised protocol for immediate rotation |

---

## **Changelog**

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-17 | 1.0 | Initial plan with Mega.nz signaling |
| 2026-02-22 | 2.0 | Removed Mega.nz (paywall), switched to file-based exchange |
| 2026-02-22 | 2.1 | Added Compromised Protocol for emergency key rotation |

---

**Ready for Implementation** 🚀
