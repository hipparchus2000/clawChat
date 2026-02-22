# ClawChat Security Protocol Specification
## Version 1.0 - Security Architect Agent

## 1. Overview

This document specifies the complete security protocol for ClawChat, including encryption algorithms, key exchange mechanisms, threat models, and mitigation strategies. The protocol ensures end-to-end encryption, secure discovery, and dynamic port rotation.

## 2. Design Principles

1. **Defense in Depth**: Multiple layers of security
2. **Zero Trust**: Verify everything, trust nothing
3. **Forward Secrecy**: Compromised keys don't expose past communications
4. **Minimal Attack Surface**: Expose only necessary functionality
5. **Fail Secure**: Default to secure state on failure

## 3. Threat Model

### 3.1 Adversarial Capabilities
- **Network Eavesdropper**: Can intercept all network traffic
- **Active MITM**: Can modify, inject, or drop packets
- **Server Compromise**: Attacker gains control of server
- **Client Compromise**: Attacker gains control of client device
- **Storage Compromise**: Attacker accesses Mega.nz or local storage

### 3.2 Attack Vectors
1. **Port Scanning**: Discovery of open ports
2. **Replay Attacks**: Reusing captured messages
3. **Key Guessing**: Brute force attacks on keys
4. **Timing Attacks**: Side-channel analysis
5. **DoS**: Resource exhaustion attacks

## 4. Encryption Algorithms

### 4.1 Transport Layer Security
- **Protocol**: TLS 1.3 (RFC 8446)
- **Cipher Suites** (in order of preference):
  1. `TLS_AES_256_GCM_SHA384`
  2. `TLS_CHACHA20_POLY1305_SHA256`
  3. `TLS_AES_128_GCM_SHA256`
- **Key Exchange**: X25519 (Curve25519)
- **Authentication**: Ed25519 signatures

### 4.2 Message-Level Encryption
- **Algorithm**: AES-256-GCM
- **Key Size**: 256 bits
- **IV Generation**: Cryptographically secure random (96-bit)
- **Authentication Tag**: 128-bit GCM tag
- **Mode**: Authenticated Encryption with Associated Data (AEAD)

### 4.3 Key Derivation
- **Algorithm**: HKDF-SHA256 (RFC 5869)
- **Salt**: Random 256-bit value
- **Info**: Context-specific string
- **Output**: Multiple keys for different purposes

### 4.4 Hashing
- **Primary**: SHA-256
- **Keyed Hashing**: HMAC-SHA256
- **Password Hashing**: Argon2id (for future user authentication)

## 5. Key Exchange Protocol

### 5.1 Initial Key Distribution
```
┌─────────┐                    ┌─────────┐
│ Client  │                    │ Server  │
└────┬────┘                    └────┬────┘
     │        Secure Channel        │
     │  (Slack DM, TUI, bash, etc.) │
     │──────────────────────────────>│
     │    Shared Secret (32 bytes)   │
     │<──────────────────────────────│
     │                               │
```

### 5.2 Connection Establishment
```
1. Client retrieves encrypted connection file from Mega.nz
2. Client decrypts using shared secret
3. Client connects via WebSocket (wss://)
4. TLS handshake (Server presents Ed25519 certificate)
5. Client verifies server identity
6. Perform X25519 key exchange for session keys
7. Derive encryption keys using HKDF
8. Begin encrypted messaging
```

### 5.3 Session Key Derivation
```python
def derive_session_keys(shared_secret, server_public, client_public):
    # Perform X25519 key exchange
    dh_secret = x25519(server_private, client_public)
    
    # HKDF expansion
    salt = sha256(server_public + client_public)
    info = b"ClawChat v1.0 Session Keys"
    
    # Derive multiple keys
    master_key = hkdf_extract(salt, dh_secret)
    
    keys = hkdf_expand(
        master_key,
        info=info,
        length=128  # 4x 32-byte keys
    )
    
    # Split into individual keys
    enc_key = keys[0:32]    # Encryption key
    mac_key = keys[32:64]   # MAC key (for future use)
    iv_key = keys[64:96]    # IV generation key
    next_key = keys[96:128] # Next session key seed
    
    return {
        'encryption_key': enc_key,
        'mac_key': mac_key,
        'iv_key': iv_key,
        'next_key_seed': next_key
    }
```

## 6. Connection File Format

### 6.1 JSON Structure (Before Encryption)
```json
{
  "version": "1.0",
  "protocol": "clawchat-secure-v1",
  "server_id": "cc-550e8400-e29b-41d4-a716-446655440000",
  "server_name": "OpenClaw Production",
  "ip_address": "192.168.1.100",
  "port": 54321,
  "public_key": "base64-encoded-ed25519-public-key",
  "timestamp": 1678886400,
  "valid_from": 1678886400,
  "valid_until": 1678890000,
  "next_rotation": 1678890000,
  "grace_period": 300,
  "supported_ciphers": [
    "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256"
  ],
  "metadata": {
    "location": "vm6042",
    "region": "us-east",
    "load": 0.15
  }
}
```

### 6.2 Encryption Process
```python
def encrypt_connection_file(data_json, shared_secret):
    # Convert JSON to bytes
    plaintext = json.dumps(data_json).encode('utf-8')
    
    # Generate random IV
    iv = os.urandom(12)  # 96 bits for AES-GCM
    
    # Derive file encryption key
    salt = b"clawchat-connection-file"
    file_key = hkdf_extract(salt, shared_secret)
    
    # Encrypt with AES-256-GCM
    cipher = AES.new(file_key, AES.MODE_GCM, nonce=iv)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    
    # Create encrypted package
    encrypted_package = {
        'iv': base64.b64encode(iv).decode(),
        'ciphertext': base64.b64encode(ciphertext).decode(),
        'tag': base64.b64encode(tag).decode(),
        'algorithm': 'aes-256-gcm',
        'timestamp': time.time()
    }
    
    return json.dumps(encrypted_package)
```

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
4. At T + 3480: Publish new connection file
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
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            sock.bind(('0.0.0.0', port))
            sock.close()
            return port
        except OSError:
            continue
    
    raise RuntimeError("Could not find available port")
```

## 8. Message Format

### 8.1 Encrypted Message Structure
```
+----------------+----------------+----------------+----------------+
|   Version      |   Message ID   |   Timestamp    |   Message Type |
|   (1 byte)     |   (16 bytes)   |   (8 bytes)    |   (1 byte)     |
+----------------+----------------+----------------+----------------+
|   IV           |   Ciphertext   |   Auth Tag     |   Padding      |
|   (12 bytes)   |   (variable)   |   (16 bytes)   |   (0-15 bytes) |
+----------------+----------------+----------------+----------------+
```

### 8.2 Message Types
- `0x01`: Chat message
- `0x02`: File transfer
- `0x03`: Presence update
- `0x04`: Key rotation request
- `0x05`: Port rotation notification
- `0x06`: Error message
- `0x07`: Keepalive ping
- `0x08`: Keepalive pong

## 9. Key Management

### 9.1 Key Hierarchy
```
┌─────────────────────────────────────────────┐
│            Long-term Shared Secret          │
│          (distributed via secure channel)   │
└──────────────────────┬──────────────────────┘
                       │
           ┌───────────┴───────────┐
           ▼                       ▼
┌─────────────────────┐   ┌─────────────────────┐
│ Connection File Key │   │   Session Master    │
│   (HKDF-derived)    │   │       Key           │
└─────────────────────┘   └─────────────────────┘
                                   │
                     ┌─────────────┴─────────────┐
                     ▼             ▼             ▼
          ┌─────────────────┐ ┌─────────┐ ┌─────────────┐
          │ Encryption Key  │ │ MAC Key │ │ Next Key    │
          │   (32 bytes)    │ │(32 bytes)│ │ Seed (32B) │
          └─────────────────┘ └─────────┘ └─────────────┘
```

### 9.2 Key Rotation
- **Session Keys**: Rotate every 24 hours or 1GB of data
- **Forward Secrecy**: New DH exchange for each rotation
- **Key Revocation**: Publish revocation list to Mega.nz

## 10. Security Controls

### 10.1 Authentication
- **Server Authentication**: Ed25519 certificates
- **Client Authentication**: Optional (future feature)
- **Message Authentication**: AES-GCM tags

### 10.2 Authorization
- **Connection Limits**: Max 100 concurrent connections
- **Rate Limiting**: Per-IP and per-client limits
- **Geo-blocking**: Configurable (future feature)

### 10.3 Auditing
- **Security Events**: Log all authentication attempts
- **Connection Logs**: Source IP, duration, data volume
- **Error Logs**: Failed decryption attempts, invalid messages

### 10.4 Monitoring
- **Port Scanning Detection**: Alert on rapid connection attempts
- **Anomaly Detection**: Unusual traffic patterns
- **Resource Monitoring**: CPU, memory, connection counts

## 11. Implementation Requirements

### 11.1 Python Backend
- `cryptography` library for all crypto operations
- `aiohttp` for async HTTP/WebSocket
- `mega.py` for Mega.nz integration
- Custom TLS context with specific cipher suites

### 11.2 JavaScript Frontend
- Web Crypto API for browser-side encryption
- `libsodium.js` for Curve25519 operations
- Service Worker for offline discovery cache

### 11.3 Storage Requirements
- **Mega.nz**: Primary storage for connection files
- **Local Cache**: Encrypted cache of recent connection files
- **Fallback**: HTTPS endpoint with same encrypted files

## 12. Compliance & Standards

### 12.1 Cryptographic Standards
- NIST SP 800-57 (Key Management)
- NIST SP 800-131A (Transitioning Cryptographic Algorithms)
- RFC 8446 (TLS 1.3)
- RFC 7748 (Elliptic Curves for Security)

### 12.2 Security Best Practices
- OWASP Top 10 compliance
- Principle of least privilege
- Secure default configurations
- Regular security updates

## 13. Testing Requirements

### 13.1 Unit Tests
- Cryptographic primitives
- Key derivation functions
- Message encryption/decryption
- Port rotation logic

### 13.2 Integration Tests
- End-to-end encrypted communication
- Port rotation scenarios
- Discovery file retrieval and parsing
- Error handling and recovery

### 13.3 Security Tests
- Penetration testing
- Fuzz testing of message parsing
- Timing attack analysis
- Memory safety analysis

## 14. Deployment Considerations

### 14.1 Initial Setup
1. Generate server key pair
2. Distribute initial shared secret
3. Configure Mega.nz credentials
4. Set up port rotation cron job
5. Deploy updated server and client

### 14.2 Key Distribution Channels
1. **Primary**: OpenClaw TUI (most secure)
2. **Secondary**: Slack DM (encrypted)
3. **Tertiary**: Secure bash script
4. **Emergency**: Physical transfer (QR code)

### 14.3 Disaster Recovery
- Backup of server private key (encrypted)
- Multiple Mega.nz accounts
- Manual port configuration override
- Client-side connection cache

## 15. Future Enhancements

### 15.1 Planned Features
- Multi-factor authentication
- Client certificate authentication
- Quantum-resistant algorithms (post-quantum crypto)
- Distributed discovery (IPFS, DHT)
- Anonymous routing (Tor support)

### 15.2 Scalability Improvements
- Load balancing across multiple ports
- Geographic distribution
- Client-side load detection
- Adaptive port rotation intervals

## 16. References

1. [TLS 1.3 RFC 8446](https://tools.ietf.org/html/rfc8446)
2. [X25519 RFC 7748](https://tools.ietf.org/html/rfc7748)
3. [AES-GCM Specification](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf)
4. [HKDF RFC 5869](https://tools.ietf.org/html/rfc5869)
5. [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)

## 17. Revision History

| Version | Date       | Author               | Changes                        |
|---------|------------|----------------------|--------------------------------|
| 1.0     | 2026-02-16 | Security Architect   | Initial specification          |

---

**Next Steps**: This specification should be implemented by the specialized agents, with the Security Architect agent available for consultation on cryptographic decisions and threat modeling.