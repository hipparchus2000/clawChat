# ClawChat Security Architecture Implementation Plan

## Overview
This document coordinates the implementation of enhanced security features for ClawChat, including dynamic port rotation, encrypted discovery via Mega.nz, and end-to-end encryption.

## Current Architecture Analysis

### Existing Components:
1. **Backend Server** (`backend/server.py`): Python WebSocket server with basic connection management
2. **Frontend Client** (`frontend/websocket-client.js`): JavaScript WebSocket client with reconnection logic
3. **Security Module** (`backend/security.py`): Basic security utilities for file operations
4. **Configuration**: YAML-based config system

### Security Gaps Identified:
1. Static port configuration (8765)
2. No encrypted discovery mechanism
3. No dynamic port rotation
4. Basic WebSocket without end-to-end encryption
5. No secure key exchange protocol

## Implementation Phases

### Phase 1: Security Protocol Design
**Agent: Security Architect**
- Design complete security protocol specification
- Define encryption algorithms (TLS 1.3, AES-256-GCM, X25519 for key exchange)
- Create threat model and mitigation strategies
- Specify key exchange mechanism

### Phase 2: Network Protocol Implementation
**Agent: Network Protocol Agent**
- Implement dynamic port allocation (random ports 49152-65535)
- Design port rotation system (hourly changes with grace period)
- Create connection negotiation protocol
- Handle NAT/firewall traversal (UPnP, hole punching)

### Phase 3: Encrypted Discovery System
**Agent: File Discovery Agent**
- Implement Mega.nz integration for connection file storage
- Create encrypted file format for {ip, port, secret, timestamp, signature}
- Design file synchronization and update mechanism
- Implement alternative storage options (local file, HTTPS endpoint)

### Phase 4: Encryption Implementation
**Agent: Encryption Implementation Agent**
- Implement end-to-end encryption for WebSocket communications
- Create secure handshake using shared secret
- Implement data encryption in transit (message-level encryption)
- Add encryption for stored connection files

### Phase 5: Client/Server Integration
**Agent: Client/Server Integration Agent**
- Update existing ClawChat server with new security features
- Modify client to retrieve and use connection files
- Implement port rotation notification system
- Add error handling for connection failures

### Phase 6: Testing & Deployment
**Agent: Testing & Deployment Agent**
- Create comprehensive test suite for security features
- Test port rotation scenarios
- Verify encryption implementation
- Create deployment documentation

## Technical Specifications

### 1. Connection File Format (Encrypted)
```json
{
  "version": "1.0",
  "server_id": "unique-server-identifier",
  "ip": "192.168.1.100",
  "port": 54321,
  "secret": "base64-encrypted-shared-secret",
  "timestamp": 1678886400,
  "valid_until": 1678890000,
  "signature": "hmac-sha256-signature",
  "next_rotation": 1678890000,
  "protocol_version": "tls1.3"
}
```

### 2. Port Rotation Algorithm
- Generate random port between 49152-65535
- Rotate every hour (3600 seconds)
- 5-minute grace period for existing connections
- Publish new connection file 2 minutes before rotation

### 3. Key Exchange Protocol
1. Initial secret shared via secure channel (Slack DM, TUI, bash)
2. Client retrieves encrypted connection file from Mega.nz
3. Client decrypts using shared secret
4. Establish WebSocket connection with TLS
5. Perform Diffie-Hellman key exchange for session keys
6. Use session keys for message-level encryption

### 4. Encryption Stack
- **Transport**: TLS 1.3 for WebSocket
- **Message**: AES-256-GCM for individual messages
- **Key Exchange**: X25519 (Curve25519)
- **Signatures**: Ed25519
- **Hashing**: SHA-256

## File Structure Changes

### New Files to Create:
1. `backend/port_rotation.py` - Port rotation management
2. `backend/discovery_service.py` - Mega.nz integration and file publishing
3. `backend/encryption.py` - End-to-end encryption implementation
4. `backend/key_exchange.py` - Secure key exchange protocol
5. `frontend/discovery-client.js` - Client-side discovery and connection management
6. `frontend/encryption-client.js` - Client-side encryption
7. `scripts/rotate_ports.py` - Port rotation script (cron job)
8. `tests/test_port_rotation.py` - Port rotation tests
9. `tests/test_encryption.py` - Encryption tests
10. `tests/test_discovery.py` - Discovery system tests

### Files to Modify:
1. `backend/server.py` - Add security features, dynamic port binding
2. `backend/security.py` - Enhance with new security protocols
3. `frontend/websocket-client.js` - Integrate with discovery and encryption
4. `config.yaml.example` - Add security configuration options
5. `requirements.txt` - Add new dependencies (cryptography, mega.py)

## Dependencies Required

### Python Backend:
```txt
cryptography>=41.0.0
mega.py>=1.0.9
pycryptodome>=3.19.0
aiohttp>=3.9.0
aiofiles>=23.2.0
```

### JavaScript Frontend:
```txt
libsodium-wrappers (for crypto in browser)
mega-js (for Mega.nz API in browser)
```

## Timeline & Milestones

### Week 1: Design & Core Infrastructure
- Complete security protocol specification
- Implement port rotation system
- Create encrypted file format

### Week 2: Encryption & Discovery
- Implement end-to-end encryption
- Integrate Mega.nz storage
- Create client-side discovery

### Week 3: Integration & Testing
- Update server and client with security features
- Comprehensive testing suite
- Performance optimization

### Week 4: Deployment & Documentation
- Create deployment scripts
- Write user documentation
- Security audit and penetration testing

## Success Criteria

1. **Security**: All communications encrypted end-to-end
2. **Reliability**: Seamless port rotation without dropped connections
3. **Usability**: Easy setup with secure key exchange
4. **Performance**: <100ms overhead for encryption/decryption
5. **Compatibility**: Works with existing ClawChat features

## Risk Mitigation

1. **Mega.nz Unavailability**: Fallback to local file or HTTPS endpoint
2. **Port Conflicts**: Retry with different port if binding fails
3. **Clock Skew**: Use NTP synchronization, include timestamps with tolerance
4. **Key Compromise**: Implement key rotation and revocation
5. **DoS Attacks**: Rate limiting and connection quotas

## Coordination Notes

All agents should:
1. Update this document with progress
2. Create detailed specifications in their respective areas
3. Coordinate on interfaces between components
4. Follow existing code style and patterns
5. Write comprehensive tests
6. Document all security decisions and trade-offs

## Contact & Communication

- **Main Coordinator**: Subagent (this session)
- **Location**: `/home/openclaw/.openclaw/workspace/projects/clawchat/`
- **Reference**: Existing ClawChat codebase and this plan

Let's build a secure, robust ClawChat system!