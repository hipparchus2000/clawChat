# ClawChat - Secure PWA Chat & File Management System

## Project Overview
A secure, single-page web application (PWA) that communicates with OpenClaw via a rotating-port Python service. Features chat messaging and full file management capabilities for the projects folder.

## Core Architecture

### 1. **Frontend (Browser PWA)**
- Single HTML page web app
- Progressive Web App (PWA) - installable on phone/PC
- Two main tabs: Messages & Files
- Responsive design (mobile + desktop)

### 2. **Backend (Python WebSocket Service)**
- Python service running on OpenClaw host
- WebSocket communication with frontend
- **Port rotation:** Changes port number every hour
- Port info encrypted and stored on Mega.nz
- Initial key exchange via bash/OpenClaw TUI/Slack

### 3. **Security Model**
- Hourly port rotation for service discovery
- Encrypted port configuration file on Mega.nz
- Initial key exchange via secure channel (bash/TUI/Slack)
- No keys in source code (GitHub-safe)
- Secure WebSocket communication (wss://)

## Feature Requirements

### A. **Messages Tab**
- Real-time chat interface
- Message history
- User presence/status
- Typing indicators
- Message delivery/read receipts
- File attachments in chat

### B. **Files Tab** (Projects Folder Management)
- **Directory browser** for `/root/.openclaw/workspace/projects/`
- **File operations:**
  - Create new files/folders
  - Rename files/folders
  - Delete files/folders
  - Move/copy files
  - Upload files from device
  - Download files to device
  - Edit text files in browser
- **File previews** for common formats
- **Search/filter** functionality
- **Bulk operations**

### C. **Security Features**
- Encrypted port configuration
- Secure key exchange
- Session management
- Authentication/authorization
- Audit logging

### D. **PWA Features**
- Installable on mobile/desktop
- Offline capabilities
- Push notifications
- Service worker for caching
- Manifest file

## Technical Stack

### Frontend
- **HTML5/CSS3/JavaScript (ES6+)**
- **Framework:** Vanilla JS or lightweight framework (Preact/Svelte)
- **WebSocket API** for real-time communication
- **File API** for upload/download
- **Service Worker** for PWA
- **IndexedDB** for offline storage

### Backend
- **Python 3.8+**
- **WebSocket library:** `websockets` or `aiohttp`
- **File system operations:** `pathlib`, `shutil`
- **Encryption:** `cryptography` library
- **Configuration:** JSON/YAML

### Infrastructure
- **Port rotation service** (cron/systemd timer)
- **Mega.nz API** for encrypted config storage
- **OpenClaw integration** for initial key exchange
- **GitHub repository** (public, no secrets)

## Security Implementation

### Port Rotation System
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Python Service │    │  Encrypted Config │   │     Mega.nz     │
│   Port: 8765     │───▶│  {port: 8765,     │───▶│   /clawchat/    │
│   (Current Hour) │    │   key: "abc123"}  │   │   config.enc    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Client PWA     │    │  Initial Key    │   │  Secure Channel  │
│  Downloads      │◀───│  Exchange via   │◀───│  (bash/TUI/     │
│  config.enc     │    │  OpenClaw/Slack │   │   Slack DM)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Key Exchange Flow
1. **Initial setup:** User gets initial decryption key via secure channel
2. **Hourly rotation:** Service generates new port, encrypts config, uploads to Mega
3. **Client discovery:** PWA downloads encrypted config from Mega, decrypts with key
4. **Connection:** PWA connects to WebSocket on discovered port
5. **Re-keying:** If key expires, request new key via secure channel

## Development Phases

### Phase 1: Foundation (Week 1)
- Project structure and architecture
- Basic WebSocket server with echo functionality
- Simple HTML client with connection management
- Port rotation mechanism (basic)

### Phase 2: Core Features (Week 2)
- Complete chat interface
- File browser UI
- Basic file operations (list, download)
- PWA setup (manifest, service worker)

### Phase 3: Advanced Features (Week 3)
- Full file management (create, rename, delete, move)
- Text file editor
- Upload functionality
- Search and filtering

### Phase 4: Security & Polish (Week 4)
- Encryption/decryption system
- Key exchange via OpenClaw
- Error handling and logging
- Mobile optimization
- Unit tests

### Phase 5: Deployment & Docs (Week 5)
- Deployment scripts
- Documentation
- GitHub repository setup
- User guide

## Task Breakdown

### A. **Backend Tasks**
1. **WebSocket Server Framework**
   - Basic echo server
   - Connection management
   - Message routing
   - Error handling

2. **Port Rotation Service**
   - Hourly port change
   - Config generation
   - Encryption/decryption
   - Mega.nz upload

3. **File System API**
   - Directory listing
   - File operations (CRUD)
   - Path validation
   - Permission checking

4. **Security Layer**
   - Authentication middleware
   - Request validation
   - Audit logging
   - Rate limiting

### B. **Frontend Tasks**
1. **PWA Foundation**
   - HTML structure
   - CSS styling (mobile-first)
   - Service worker
   - Manifest file

2. **UI Components**
   - Tab navigation
   - Chat interface
   - File browser
   - Modal dialogs

3. **WebSocket Client**
   - Connection management
   - Message handling
   - Reconnection logic
   - Error recovery

4. **File Operations UI**
   - File upload/download
   - Text editor
   - Context menus
   - Drag-and-drop

### C. **Integration Tasks**
1. **OpenClaw Integration**
   - Key exchange via TUI
   - Slack DM fallback
   - Bash script alternative

2. **Mega.nz Integration**
   - Config file upload
   - Config file download
   - Error handling for missing files

3. **Deployment**
   - Service installation script
   - Startup configuration
   - Log rotation
   - Monitoring

## Testing Strategy

### Unit Tests
- WebSocket message handling
- File operations
- Encryption/decryption
- Port rotation logic

### Integration Tests
- End-to-end chat flow
- File upload/download
- Key exchange process
- PWA installation

### Security Tests
- Encryption validation
- Authentication bypass attempts
- File path traversal attempts
- Rate limiting effectiveness

## Deployment Requirements

### Server Side
- Python 3.8+ installed
- Mega.nz CLI configured
- OpenClaw running
- Systemd/cron for service management
- Firewall rules for port range

### Client Side
- Modern browser with WebSocket support
- HTTPS for PWA features
- Mega.nz access for config downloads

## GitHub Considerations
- **No secrets in code** - all configs external
- **README.md** with setup instructions
- **LICENSE** file (MIT recommended)
- **.gitignore** for sensitive files
- **CI/CD pipeline** for testing

## Success Metrics
- ✅ Secure communication between browser and OpenClaw
- ✅ Hourly port rotation working
- ✅ Full file management capabilities
- ✅ PWA installable on mobile/desktop
- ✅ No secrets in GitHub repository
- ✅ Unit tests passing
- ✅ Documentation complete

## Risks & Mitigations

### Security Risks
- **Key leakage:** Use secure channels for initial exchange
- **Port scanning:** Random port selection, hourly rotation
- **File system access:** Strict path validation, permission checks

### Technical Risks
- **WebSocket stability:** Implement reconnection logic
- **PWA compatibility:** Test on multiple browsers/devices
- **File size limits:** Implement chunking for large files

### Operational Risks
- **Service downtime:** Health checks, automatic restart
- **Config sync issues:** Versioning in encrypted config
- **Mega.nz availability:** Fallback to local cache

---

**Project Start Date:** February 14, 2026  
**Target Completion:** March 20, 2026 (5 weeks)  
**Primary Developer:** Richard De Clawbeaux (with sub-agent orchestration)  
**Repository:** Public GitHub (after security review)