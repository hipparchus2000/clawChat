# Security Mechanism: Mega.nz + UDP Hole Punching

**Date Added:** 2026-02-17  
**Priority:** High  
**Status:** Pending  
**Assigned To:** TBD (needs developer/agent assignment)

## Overview

Replace current ClawChat security mechanism with a decentralized system using Mega.nz as a secure message drop and UDP hole punching for direct peer-to-peer connections.

## Problem Statement

Current security mechanism (unspecified) needs replacement with a more robust, decentralized approach that enables direct client-server communication without central relay servers.

## Proposed Solution

### Phase 1: Secure Message Exchange via Mega.nz

**Step 1 - Server Initiation:**
```
Server → Mega.nz:
  - Upload: encrypted_time_limited_file.bin
  - Contents: {server_ip, secret_key, udp_port, timestamp, expiry}
  - Encryption: AES-256 with pre-shared key or public-key crypto
  - Location: /temp-share/clawchat-connection-[random-id]/
```

**Step 2 - Client Response:**
```
Client (monitoring Mega.nz folder):
  - Download: encrypted_time_limited_file.bin
  - Decrypt: using shared secret
  - Verify: timestamp freshness (e.g., < 5 minutes)
  - Create Response: encrypted_response_file.bin
  - Contents: {client_ip, client_udp_port, verification_token}
  - Upload: to same Mega.nz location
```

**Step 3 - Server Retrieval:**
```
Server (polling Mega.nz):
  - Download: encrypted_response_file.bin
  - Decrypt: using shared secret
  - Verify: token matches expected pattern
  - Extract: client_ip, client_udp_port
```

### Phase 2: UDP Hole Punching

**Step 4 - Connection Establishment:**
```
Both sides now have:
  - Server knows: client_ip, client_udp_port
  - Client knows: server_ip, server_udp_port
  
UDP Hole Punching Process:
  1. Both send UDP packets to each other's addresses
  2. NAT devices create temporary forwarding rules
  3. Direct peer-to-peer UDP connection established
  4. Use keep-alive packets to maintain NAT mappings
```

**Step 5 - Secure Communication:**
```
Once UDP connection established:
  - Switch to encrypted UDP stream (DTLS or custom encryption)
  - Implement heartbeat/keep-alive mechanism
  - Handle reconnection if NAT mappings expire
```

## Architecture Decisions

### **Current Decision: Python UDP Solution**
**Web Client:** ❌ **FROZEN** for now due to JavaScript UDP limitations
**Focus:** Python client/server implementation only

### **JavaScript UDP Limitations:**
- **Browser JavaScript:** ❌ NO direct UDP support (security restrictions)
- **Node.js JavaScript:** ✅ FULL UDP support via `dgram` module
- **ClawChat Current:** Browser PWA + Python backend (WebSocket/TCP)

### **Implementation Path:**

#### **Phase 1: Python UDP Implementation (CURRENT FOCUS)**
- **Platform:** Python client/server (desktop applications)
- **Mechanism:** 
  1. Mega.nz for signaling/connection setup
  2. UDP hole punching for direct P2P connections
  3. Hourly port rotation for security
- **Pros:** Full control, no browser limitations, dark server compatible
- **Status:** Active development with Kimi K2.5 CLI

#### **Phase 2: Web Client Future (FROZEN)**
- **Considerations for later:**
  1. WebRTC Data Channels (requires TURN servers)
  2. WebSocket fallback (not P2P, needs relay)
  3. Hybrid approach (Python backend + WebSocket to browser)
- **Timing:** Revisit after Python implementation proven stable
- **Rationale:** JavaScript UDP limitations make browser P2P challenging

## Technical Specifications

### 1. Mega.nz Integration
- **API:** Use `mega-cmd` or Python `mega.py` library
- **Credentials:** Load from `/home/openclaw/.openclaw/workspace/mega.creds`
- **Folder Structure:**
  ```
  /temp-share/clawchat-connections/
    ├── pending-[connection-id].bin
    ├── response-[connection-id].bin
    └── cleanup script (remove files > 10 minutes old)
  ```

### 2. Encryption Scheme
- **Option A:** Pre-shared symmetric key (simpler)
  - AES-256-GCM for encryption + authentication
  - Key derived from master secret + connection ID
- **Option B:** Public-key cryptography (more secure)
  - Server: RSA public key in initial file
  - Client: Encrypt response with server's public key
  - Server: Decrypt with private key

### 3. Time-Limited Files
- **Expiry:** 5 minutes maximum
- **Cleanup:** Automated script removes old files
- **Timestamp:** Include in encrypted payload for verification

### 4. UDP Hole Punching Implementation
- **Library:** Python `socket` for UDP
- **NAT Types:** Handle full-cone, restricted, port-restricted, symmetric
- **Fallback:** If hole punching fails, fall back to current mechanism
- **Testing:** Test with different network configurations

### 5. Security Considerations
- **Replay Attacks:** Prevented by timestamps and connection IDs
- **MITM Attacks:** Prevented by encryption and verification tokens
- **DoS Protection:** Rate limiting on Mega.nz file creation
- **Key Management:** Secure storage of encryption keys

## Implementation Tasks

### High Priority:
1. [ ] Mega.nz file upload/download module
2. [ ] Encryption/decryption system
3. [ ] UDP socket implementation with hole punching
4. [ ] Connection state machine

### Medium Priority:
5. [ ] NAT type detection
6. [ ] Fallback mechanism
7. [ ] Logging and debugging tools
8. [ ] Automated testing suite

### Low Priority:
9. [ ] Performance optimization
10. [ ] Mobile client support
11. [ ] WebRTC integration (alternative to UDP)
12. [ ] GUI for connection status

## Dependencies

1. **Mega.nz Access:** Working credentials (`hipparchus2000@gmail.com`)
2. **Python Libraries:**
   - `cryptography` for encryption
   - `mega.py` or `mega-cmd` for file operations
   - `socket` for UDP networking
3. **Network Requirements:**
   - UDP ports must be accessible (configurable)
   - Mega.nz API must be reachable

## Testing Plan

### Unit Tests:
1. File encryption/decryption
2. Mega.nz upload/download
3. Timestamp validation
4. UDP packet sending/receiving

### Integration Tests:
1. Complete connection flow (server → Mega.nz → client → UDP)
2. NAT traversal with different NAT types
3. Reconnection after network failure
4. Security attack simulations

### Performance Tests:
1. Connection establishment time
2. File transfer speed over UDP
3. Memory usage with multiple connections
4. Mega.nz API rate limits

## Success Metrics

1. **Connection Success Rate:** > 90% across different NAT types
2. **Establishment Time:** < 10 seconds end-to-end
3. **Security:** No successful attacks in penetration testing
4. **Reliability:** < 1% connection drop rate
5. **Backward Compatibility:** Seamless transition from old system

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Mega.nz API changes | High | Abstract API layer, monitor for changes |
| NAT traversal fails | Medium | Fallback to current system, STUN server backup |
| Encryption vulnerabilities | High | Use standard libraries, security audit |
| UDP packet loss | Medium | Implement retransmission, FEC |
| Key management issues | High | Secure storage, key rotation |

## Next Steps

1. **Assign developer/agent** to implement prototype
2. **Create proof-of-concept** with basic Mega.nz + UDP
3. **Test with simple chat application**
4. **Integrate into ClawChat** once stable
5. **Phase out old security mechanism**

## References

- **UDP Hole Punching:** RFC 5128, STUN protocol
- **Mega.nz API:** https://github.com/odwyersoftware/mega.py
- **Python Cryptography:** https://cryptography.io/
- **NAT Types:** https://en.wikipedia.org/wiki/Network_address_translation

---

*Last Updated: 2026-02-17*  
*Author: Jeff Davies (concept), Richard De Clawbeaux (documentation)*