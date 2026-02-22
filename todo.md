# ClawChat

## Objective
Build an HTML app and listener so Slack etc. isn't needed.

## Features to Consider

- [ ] Basic chat interface (HTML/CSS/JS)
- [ ] Message listener/notification system
- [ ] Integration with OpenClaw backend
- [ ] Audio call capability
- [ ] Speakerphone support
- [ ] Mobile-responsive design
- [ ] PWA capabilities (installable)

## Technical Tasks

- [ ] Design UI/UX mockups
- [ ] Set up WebSocket or polling for real-time messages
- [ ] Implement authentication/security
- [ ] Audio call research (WebRTC?)
- [ ] Speakerphone integration research
- [ ] Test on mobile devices

## Security Mechanism Task (NEW - 2026-02-17)

**DECISION MADE:** Python UDP Hole Punching with Mega.nz Signaling
**WEB CLIENT:** Frozen for later consideration

**Objective:** Replace current security mechanism with Python-based UDP hole punching using Mega.nz as secure signaling channel.

**Architecture Selected:** Python client/server (not browser-based) with:
1. Mega.nz encrypted file drop for handshake signaling
2. UDP hole punching for direct P2P connections
3. Hourly port rotation for security
4. Dark server compatible (no open ports)

**Web Client Status:** ❌ **FROZEN** - JavaScript/browser limitations make UDP impossible. Will revisit later with WebRTC or alternative approach.

**Implementation Plan:** See `python-udp-hole-punching-plan.md` for detailed Kimi K2.5 CLI development plan.

**Workflow:**
1. **Client → Mega.nz:** Drops encrypted handshake file (IP, port, proposed time)
2. **Server → Mega.nz:** Picks up file, decrypts, drops response file
3. **Client → Mega.nz:** Picks up response file, reads server details
4. **Both at agreed time:** UDP hole punching establishes direct connection
5. **Continuous:** Encrypted UDP communication with hourly port changes

**Technical Requirements:**
- [ ] Mega.nz API integration for file upload/download
- [ ] AES-256-GCM encryption/decryption system
- [ ] UDP hole punching implementation (Python socket)
- [ ] NAT type detection and traversal strategies
- [ ] Time synchronization and connection scheduling
- [ ] Hourly port rotation mechanism
- [ ] Error handling and reconnection logic

**Benefits:**
- ✅ No JavaScript/browser limitations (full Python control)
- ✅ No TURN servers needed (direct P2P via hole punching)
- ✅ Dark server compatible (server initiates outbound only)
- ✅ Mega.nz secure drop (encrypted, time-limited files)
- ✅ Hourly port rotation (built-in security)
- ✅ Full control over NAT traversal logic

**Web Client Future Considerations:**
- WebRTC Data Channels (requires TURN servers)
- WebSocket fallback (not P2P, needs relay)
- Hybrid approach (Python backend + WebSocket to browser)
- **Decision:** Address after Python implementation proven

**Status:** Planning complete, ready for Kimi K2.5 CLI implementation tomorrow.

**Implementation Notes:**
- Use existing Mega.nz credentials from workspace (`mega.creds`)
- Consider Python `cryptography` library for encryption
- Test with different NAT types (full-cone, restricted, symmetric)
- Add logging for debugging connection issues

## Notes

*Add technical decisions and architecture notes here.*
