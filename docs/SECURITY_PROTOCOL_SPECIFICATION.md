# ClawChat Security Protocol Specification
## Version 2.0 - File-Based Security Exchange (No Mega.nz)

## 1. Overview

This document specifies the complete security protocol for ClawChat UDP hole punching, including:
- **File-based security exchange** (replaced Mega.nz due to paywall)
- Encryption algorithms and key exchange mechanisms
- Compromised Protocol for emergency key rotation
- Threat models and mitigation strategies

The protocol ensures end-to-end encryption, secure discovery via file exchange, and dynamic port rotation.

---

## 2. Design Principles

1. **Defense in Depth**: Multiple layers of security
2. **Zero Trust**: Verify everything, trust nothing
3. **Forward Secrecy**: Compromised keys don't expose past communications
4. **Minimal Attack Surface**: Expose only necessary functionality
5. **Fail Secure**: Default to secure state on failure
6. **Out-of-Band Initial Exchange**: Security files transferred manually
7. **In-Band Key Rotation**: Subsequent exchanges through encrypted channel

---

## 3. Threat Model

### 3.1 Adversarial Capabilities
- **Network Eavesdropper**: Can intercept all network traffic
- **Active MITM**: Can modify, inject, or drop packets
- **Server Compromise**: Attacker gains control of server
- **Client Compromise**: Attacker gains control of client device
- **File Interception**: Attacker intercepts security file during transfer

### 3.2 Attack Vectors
1. **Port Scanning**: Discovery of open ports
2. **Replay Attacks**: Reusing captured messages
3. **Key Guessing**: Brute force attacks on keys
4. **Timing Attacks**: Side-channel analysis
5. **DoS**: Resource exhaustion attacks
6. **File Theft**: Interception of security files

---

## 4. Encryption Algorithms

### 4.1 Transport Layer Security (UDP)
- **Protocol**: Encrypted UDP (no TLS - UDP is connectionless)
- **Algorithm**: AES-256-GCM for packet encryption
- **Key Size**: 256 bits
- **IV Generation**: Cryptographically secure random (96-bit)
- **Authentication Tag**: 128-bit GCM tag
- **Mode**: Authenticated Encryption with Associated Data (AEAD)

### 4.2 Security File Encryption
- **Algorithm**: AES-256-GCM
- **Key Size**: 256 bits
- **Key Derivation**: PBKDF2-HMAC-SHA256 with 100,000 iterations
- **Salt**: Random 256-bit value per file
- **File Permissions**: 600 (owner read/write only)

### 4.3 Key Derivation
- **Algorithm**: HKDF-SHA256 (RFC 5869)
- **Salt**: Random 256-bit value
- **Info**: Context-specific string ("ClawChat-v2-Session")
- **Output**: Multiple keys for different purposes

### 4.4 Hashing
- **Primary**: SHA-256
- **Keyed Hashing**: HMAC-SHA256
- **Password Hashing**: Argon2id (for future use)

---

## 5. Key Exchange Protocol

### 5.1 Initial Key Distribution (Out-of-Band)
```
┌─────────┐                    ┌─────────┐
│ Client  │                    │ Server  │
└────┬────┘                    └────┬────┘
     │                              │
     │<─(1) Server creates file─────│
     │    /home/openclaw/clawchat/  │
     │    security/clawchat-*.sec   │
     │                              │
     │<─(2) User transfers file─────│
     │    USB / encrypted message   │
     │                              │
     │──(3) Client loads file──────>│
     │    File browser popup        │
     │                              │
     │<─(4) Extract keys────────────│
     │    shared_secret, ip, port   │
```

### 5.2 Connection Establishment
```
1. Client reads security file via file browser
2. Client decrypts using pre-shared bootstrap key
3. Extract: server_ip, server_port, shared_secret
4. Perform UDP hole punching
5. Establish encrypted UDP channel
6. Begin secure messaging
```

### 5.3 Session Key Derivation
```python
def derive_session_keys(shared_secret, connection_id, timestamp):
    # Combine shared secret with connection context
    context = f"{connection_id}:{timestamp}".encode()
    
    # HKDF extraction
    salt = sha256(shared_secret + context)
    info = b"ClawChat v2.0 Session Keys"
    
    # Derive multiple keys
    master_key = hkdf_extract(salt, shared_secret)
    
    keys = hkdf_expand(
        master_key,
        info=info,
        length=128  # 4x 32-byte keys
    )
    
    # Split into individual keys
    enc_key = keys[0:32]      # Encryption key
    mac_key = keys[32:64]     # MAC key
    iv_key = keys[64:96]      # IV generation key
    next_key = keys[96:128]   # Next session key seed
    
    return {
        'encryption_key': enc_key,
        'mac_key': mac_key,
        'iv_key': iv_key,
        'next_key_seed': next_key
    }
```

### 5.4 In-Band Key Rotation
```
[CLIENT]                              [SERVER]
   │                                      │
   │<──(1) Hourly rotation triggered─────│
   │                                      │
   │──(2) Generate new keys──────────────>│
   │    Derive from next_key_seed         │
   │                                      │
   │<──(3) Exchange new public keys───────│
   │    Through encrypted channel         │
   │                                      │
   │──(4) Acknowledge and switch────────>│
   │    Both sides switch to new keys     │
```

---

## 6. Security File Format

### 6.1 File Location
- **Path**: `/home/openclaw/clawchat/security/`
- **Permissions**: 700 (directory), 600 (files)
- **Owner**: `openclaw:openclaw`
- **Naming**: `clawchat-[YYYYMMDD-HHMMSS].sec`

### 6.2 JSON Structure (Before Encryption)
```json
{
  "version": "2.0",
  "protocol": "clawchat-file-v2",
  "server_id": "cc-550e8400-e29b-41d4-a716-446655440000",
  "server_name": "OpenClaw Production",
  "server_public_ip": "45.135.36.44",
  "server_udp_port": 54321,
  "shared_secret": "base64-encoded-32-byte-secret",
  "bootstrap_key_id": "bootstrap-001",
  "timestamp": 1678886400,
  "valid_from": 1678886400,
  "valid_until": 1678890000,
  "next_rotation": 1678890000,
  "grace_period": 300,
  "supported_ciphers": [
    "AES-256-GCM"
  ],
  "nat_traversal": {
    "stun_servers": [
      "stun.l.google.com:19302"
    ],
    "hole_punch_timeout": 60
  },
  "compromised_protocol": {
    "signal": "CLAWCHAT_COMPROMISED_V2",
    "response_timeout": 10
  }
}
```

### 6.3 Encryption Process
```python
def encrypt_security_file(data_json, bootstrap_key):
    # Convert JSON to bytes
    plaintext = json.dumps(data_json).encode('utf-8')
    
    # Generate random salt and IV
    salt = os.urandom(32)
    iv = os.urandom(12)  # 96 bits for AES-GCM
    
    # Derive file encryption key from bootstrap key
    file_key = pbkdf2_hmac(
        'sha256',
        bootstrap_key,
        salt,
        iterations=100000,
        dklen=32
    )
    
    # Encrypt with AES-256-GCM
    cipher = AES.new(file_key, AES.MODE_GCM, nonce=iv)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    
    # Create encrypted package
    encrypted_package = {
        'version': '2.0',
        'salt': base64.b64encode(salt).decode(),
        'iv': base64.b64encode(iv).decode(),
        'ciphertext': base64.b64encode(ciphertext).decode(),
        'tag': base64.b64encode(tag).decode(),
        'algorithm': 'aes-256-gcm-pbkdf2',
        'iterations': 100000,
        'timestamp': time.time()
    }
    
    return json.dumps(encrypted_package)
```

---

## 7. Port Rotation Protocol

### 7.1 Rotation Schedule
- **Rotation Interval**: 3600 seconds (1 hour)
- **Grace Period**: 300 seconds (5 minutes)
- **Announcement Time**: 120 seconds before rotation
- **Max Port Age**: 3900 seconds (65 minutes)

### 7.2 Rotation Process
```
1. Current time: T
2. Next rotation: T + 3600
3. At T + 3480 (2 minutes before): Generate new port
4. At T + 3480: Derive new session keys
5. At T + 3600: Start accepting connections on new port
6. Until T + 3900: Accept connections on both ports
7. At T + 3900: Close old port
```

### 7.3 Port Selection Algorithm
```python
def select_random_port():
    import random
    import socket
    
    # Ephemeral port range (IANA)
    min_port = 49152
    max_port = 65535
    
    for attempt in range(10):
        port = random.randint(min_port, max_port)
        
        # Check if port is available
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        try:
            sock.bind(('0.0.0.0', port))
            sock.close()
            return port
        except OSError:
            continue
    
    raise RuntimeError("Could not find available port")
```

---

## 8. Compromised Protocol

### 8.1 Purpose
Emergency key rotation when keys are suspected compromised. Allows immediate invalidation of current keys and generation of new security file.

### 8.2 Protocol Flow
```
[CLIENT]                              [SERVER]
   │                                      │
   │──(1) Send COMPROMISED signal───────>│
   │    CLAWCHAT_COMPROMISED_V2           │
   │    Signed with current key           │
   │                                      │
   │<──(2) Acknowledge───────────────────│
   │    COMPROMISED_ACK                   │
   │                                      │
   │──(3) Both delete keys───────────────│
   │    - Session keys                    │
   │    - Security files                  │
   │    - Connection state                │
   │                                      │
   │<──(4) Connection terminated─────────│
   │                                      │
   │──(5) Server generates new file──────>│
   │    /home/openclaw/clawchat/security/ │
   │                                      │
   │<──(6) User transfers new file───────│
   │    Out-of-band (USB, etc.)           │
   │                                      │
   │──(7) Client loads new file──────────>│
   │    File browser popup                │
   │                                      │
   │<──(8) New connection established────│
```

### 8.3 Compromised Signal Format
```json
{
  "type": "compromised",
  "version": "2.0",
  "signal": "CLAWCHAT_COMPROMISED_V2",
  "timestamp": 1678886400,
  "connection_id": "clawchat-20260222-abc123",
  "reason": "user_initiated",
  "signature": "hmac-sha256-signature"
}
```

### 8.4 Server Response
```json
{
  "type": "compromised_ack",
  "version": "2.0",
  "timestamp": 1678886400,
  "connection_id": "clawchat-20260222-abc123",
  "action": "keys_deleted",
  "new_file_ready": true,
  "signature": "hmac-sha256-signature"
}
```

### 8.5 Cleanup Actions
Both sides MUST:
1. Delete all session keys from memory
2. Close UDP sockets
3. Delete local security file copies
4. Clear connection state
5. Server generates new security file
6. Client waits for new file transfer

---

## 9. Message Format

### 9.1 Encrypted UDP Packet Structure
```
+----------------+----------------+----------------+----------------+
|   Version      |   Message ID   |   Timestamp    |   Message Type |
|   (1 byte)     |   (16 bytes)   |   (8 bytes)    |   (1 byte)     |
+----------------+----------------+----------------+----------------+
|   IV           |   Ciphertext   |   Auth Tag     |   Padding      |
|   (12 bytes)   |   (variable)   |   (16 bytes)   |   (0-15 bytes) |
+----------------+----------------+----------------+----------------+
```

### 9.2 Message Types
- `0x01`: Chat message
- `0x02`: File transfer
- `0x03`: Presence update
- `0x04`: Key rotation request
- `0x05`: Port rotation notification
- `0x06`: Error message
- `0x07`: Keepalive ping
- `0x08`: Keepalive pong
- `0x09`: Compromised signal
- `0x0A`: Compromised acknowledge

---

## 10. Key Management

### 10.1 Key Hierarchy
```
┌─────────────────────────────────────────────┐
│         Bootstrap Key (Pre-shared)          │
│     (distributed via secure out-of-band)    │
└──────────────────────┬──────────────────────┘
                       │
           ┌───────────┴───────────┐
           ▼                       ▼
┌─────────────────────┐   ┌─────────────────────┐
│ Security File Key   │   │   Session Master    │
│   (PBKDF2-derived)  │   │       Key           │
└─────────────────────┘   └─────────────────────┘
                                   │
                     ┌─────────────┴─────────────┐
                     ▼             ▼             ▼
          ┌─────────────────┐ ┌─────────┐ ┌─────────────┐
          │ Encryption Key  │ │ MAC Key │ │ Next Key    │
          │   (32 bytes)    │ │(32 bytes)│ │ Seed (32B) │
          └─────────────────┘ └─────────┘ └─────────────┘
```

### 10.2 Key Rotation
- **Session Keys**: Rotate every hour or 1GB of data
- **Forward Secrecy**: New keys derived from next_key_seed
- **Compromised Keys**: Immediate rotation via Compromised Protocol

---

## 11. Security Controls

### 11.1 Authentication
- **Server Authentication**: Shared secret in security file
- **Client Authentication**: Shared secret verification
- **Message Authentication**: AES-GCM tags

### 11.2 Authorization
- **Connection Limits**: Max 100 concurrent connections
- **Rate Limiting**: Per-IP and per-client limits
- **File Access**: Owner-only (600 permissions)

### 11.3 Auditing
- **Security Events**: Log all authentication attempts
- **Connection Logs**: Source IP, duration, data volume
- **Error Logs**: Failed decryption attempts, invalid messages
- **Compromised Events**: Log all key rotations

### 11.4 Monitoring
- **Port Scanning Detection**: Alert on rapid connection attempts
- **Anomaly Detection**: Unusual traffic patterns
- **Resource Monitoring**: CPU, memory, connection counts

---

## 12. Implementation Requirements

### 12.1 Python Backend
- `cryptography` library for all crypto operations
- `aiohttp` for async operations (optional)
- Custom UDP socket handling
- Tkinter for client file browser

### 12.2 Python Client
- Tkinter for file browser GUI
- `cryptography` library for decryption
- UDP socket for hole punching

### 12.3 Storage Requirements
- **Server**: `/home/openclaw/clawchat/security/` (owner-only)
- **Client**: User-selected via file browser
- **Permissions**: 600 for security files

---

## 13. Compliance & Standards

### 13.1 Cryptographic Standards
- NIST SP 800-57 (Key Management)
- NIST SP 800-131A (Transitioning Cryptographic Algorithms)
- RFC 5869 (HKDF)
- RFC 7748 (Elliptic Curves for Security)

### 13.2 Security Best Practices
- OWASP Top 10 compliance
- Principle of least privilege
- Secure default configurations
- Regular security updates

---

## 14. Testing Requirements

### 14.1 Unit Tests
- Cryptographic primitives
- Key derivation functions
- Message encryption/decryption
- Port rotation logic
- Compromised Protocol

### 14.2 Integration Tests
- End-to-end encrypted communication
- Port rotation scenarios
- Security file generation and loading
- Error handling and recovery
- Compromised Protocol flow

### 14.3 Security Tests
- Penetration testing
- Fuzz testing of message parsing
- Timing attack analysis
- Memory safety analysis
- File permission verification

---

## 15. Deployment Considerations

### 15.1 Initial Setup
1. Create `openclaw` user
2. Generate bootstrap key
3. Create `/home/openclaw/clawchat/` directory structure
4. Set proper permissions (700, 600)
5. Generate initial security file
6. Install systemd service

### 15.2 Key Distribution
1. **Primary**: Physical transfer (USB drive)
2. **Secondary**: Encrypted messaging (Signal, etc.)
3. **Tertiary**: Secure cloud (encrypted ZIP)
4. **Emergency**: Manual entry (base64 encoded)

### 15.3 Disaster Recovery
- Backup of bootstrap key (encrypted, offline)
- Multiple security file copies
- Manual port configuration override
- Compromised Protocol for immediate rotation

---

## 16. Revision History

| Version | Date       | Author               | Changes                        |
|---------|------------|----------------------|--------------------------------|
| 1.0     | 2026-02-16 | Security Architect   | Initial specification          |
| 2.0     | 2026-02-22 | OpenClaw             | Removed Mega.nz, added file-based exchange |
| 2.1     | 2026-02-22 | OpenClaw             | Added Compromised Protocol     |

---

**Next Steps**: Implement according to this specification, with Security Architect agent available for consultation on cryptographic decisions.
