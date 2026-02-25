# ClawChat Architecture

## Three-Tier Architecture

ClawChat uses a three-tier architecture with clear separation of concerns:

```
┌─────────────────┐     UDP Hole Punching      ┌─────────────────┐     Local/Internal      ┌─────────────────┐
│   GUI Client    │◀──────────────────────────▶│  Hole Punching  │◀─────────────────────▶│   LLM Server    │
│  (run_gui_      │    Encrypted (AES-256)     │     Server      │    (HTTP/UDP/IPC)     │ (run_llm_       │
│   client.py)    │                            │ (run_server.py) │                       │  server.py)     │
└─────────────────┘                            └─────────────────┘                       └─────────────────┘
       │                                              │                                         │
       │                                              │                                         │
   - Chat messages                              - Forwards chat to LLM                   - AI processing
   - File operations                            - Relays LLM responses                  - Context system
   - Crontab management                         - Handles key rotation                  - Cron scheduler
   - Security file (.sec)                       - Manages client connection             - File protocol
```

## Component Roles

### 1. GUI Client (`run_gui_client.py`)

**Purpose**: User interface for chat, file management, and crontab

**Connects to**: Hole Punching Server only (NEVER directly to LLM Server)

**Features**:
- Three-tab interface: Chat, Files, Crontab
- File browser for selecting `.sec` security files
- Encrypted UDP communication via hole punching
- Message display, file operations, cron job management

**Configuration**: None required (uses security file from server)

### 2. Hole Punching Server (`run_server.py`)

**Purpose**: NAT traversal proxy that relays between client and LLM server

**Listens on**: Public UDP port (random ephemeral, 49152-65535)

**Connects to**: LLM Server on localhost/internal port

**Responsibilities**:
1. **NAT Traversal**: UDP hole punching for client connections
2. **Security**: Key rotation, compromised protocol
3. **Relay**: Forward client messages to LLM server
4. **Response Relay**: Return LLM responses to client
5. **Connection Management**: Handle client connect/disconnect

**Key Behaviors**:
- Generates `clawchat-current.sec` security file (valid 11 min, regenerates every 10 min)
- Maintains encrypted UDP connection with client
- Forwards chat messages to LLM server via local connection
- Relays LLM responses back to client
- Handles key rotation without dropping LLM context

**Command Line**:
```bash
python run_server.py \
  --ip 0.0.0.0 \           # Public IP for clients
  --port 54321 \           # Public port (random if not set)
  --llm-ip 127.0.0.1 \     # LLM server IP (localhost)
  --llm-port 55556         # LLM server port
```

**Environment Variables**:
- `CLAWCHAT_BOOTSTRAP_KEY` - Key for encrypting security files
- `CLAWCHAT_SECURITY_DIR` - Directory for security files

### 3. LLM Server (`run_llm_server.py`)

**Purpose**: AI processing with persistent conversation context

**Listens on**: Local port only (default: 55556, NOT exposed to internet)

**Connects to**: No external connections (receives via hole punching server)

**Responsibilities**:
1. **AI Processing**: DeepSeek/OpenAI/Anthropic API integration
2. **Context System**: OpenClaw-style SOUL/AGENTS/USER/MEMORY loading
3. **Cron Scheduler**: Automated AI task execution
4. **File Protocol**: Remote file operations
5. **Session Persistence**: Maintains conversation across client reconnections

**Key Behaviors**:
- Persists conversation history to `llm_session.json`
- Loads context files from `context/` directory
- Processes cron jobs from `context/CRON.md`
- Handles file operations in sandboxed directory
- Survives client disconnections (session persists)

**Configuration** (`.env`):
```ini
CLAWCHAT_LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-...
CLAWCHAT_CONTEXT_DIR=./context
```

## Communication Flow

### Chat Message Flow

```
1. User types message in GUI
   ↓
2. GUI Client encrypts → sends to Hole Punching Server (UDP public)
   ↓
3. Hole Punching Server decrypts → relays to LLM Server (UDP localhost)
   ↓
4. LLM Server processes with AI → generates response
   ↓
5. LLM Server returns response to Hole Punching Server
   ↓
6. Hole Punching Server encrypts → sends to GUI Client (UDP)
   ↓
7. GUI Client displays response
```

**Important**: Hole punching server acts as a transparent relay. It does NOT process chat messages - all AI processing happens in LLM Server.

### File Operation Flow

```
1. User clicks "Download" in GUI File tab
   ↓
2. GUI Client sends FILE_DOWNLOAD request to Hole Punching Server
   ↓
3. Hole Punching Server relays to LLM Server
   ↓
4. LLM Server reads file → returns chunk
   ↓
5. Hole Punching Server relays response to GUI Client
   ↓
6. GUI Client saves file to local disk
```

### Relay Behavior

The Hole Punching Server is a **transparent relay**:

1. **Receives** encrypted message from client
2. **Decrypts** using session keys
3. **Forwards** plaintext message to LLM server via localhost UDP
4. **Waits** for LLM response (up to 60s for AI processing)
5. **Receives** plaintext response from LLM
6. **Encrypts** response using session keys
7. **Sends** encrypted response to client

**Messages relayed**:
- `CHAT` → AI conversation
- `FILE_LIST`, `FILE_DOWNLOAD`, `FILE_UPLOAD`, etc. → File operations
- `CRON_LIST`, `CRON_RUN`, `CRON_RELOAD` → Cron management

### Error Handling

**LLM Server Unreachable**:
```
[Server] ERROR: Cannot reach LLM server
[Server] Please ensure LLM server is running:
    python run_llm_server.py
```
- Hole punching server exits if LLM is not available on startup
- Client receives `[Error: Cannot reach LLM server]` if relay fails mid-session

### Cron Job Flow

```
1. Cron Scheduler triggers (based on CRON.md schedule)
   ↓
2. LLM Server executes job through LLM Bridge
   ↓
3. Job result logged to logs/cron/
   ↓
4. (Optional) GUI Client can view cron status via Hole Punching Server
```

## Security Model

### Layer 1: Client ↔ Hole Punching Server

- **Encryption**: AES-256-GCM with ephemeral keys
- **Key Exchange**: File-based (`.sec` security file)
- **Validity**: 11 minutes with 10-minute auto-regeneration
- **Rotation**: In-band key rotation every hour
- **Protocol**: Custom UDP with hole punching for NAT traversal

### Layer 2: Hole Punching Server ↔ LLM Server

- **Transport**: UDP on localhost (not exposed to network)
- **Port**: 55556 (default, configurable)
- **Encryption**: None (localhost is trusted)
- **Authentication**: None required (same machine)
- **Protocol**: Same Message protocol as client-server

**Note**: LLM server is REQUIRED. If hole punching server cannot connect, it exits with error.

### Layer 3: LLM Server ↔ AI APIs

- **Transport**: HTTPS to DeepSeek/OpenAI/Anthropic
- **Authentication**: API keys from `.env`
- **Data**: Conversation history, context files

## Port Configuration

| Component | Default Port | Exposure | Purpose |
|-----------|-------------|----------|---------|
| Hole Punching Server | Random (49152-65535) | Public | Client connections |
| LLM Server | 55556 | Localhost only | Receives traffic from hole punching server |

## Deployment Scenario

### Single Machine (Development)

```
[GUI Client] ←→ [Hole Punching Server] ←→ [LLM Server]
    ↓                    ↓                      ↓
  Localhost          Localhost              Localhost
  Port A             Port B                 Port 55556
```

### Production (VPS)

```
[GUI Client] ←──Internet──→ [Hole Punching Server] ←→ [LLM Server]
    (User)      (UDP Hole       (VPS Public IP)      (Same VPS
                Punching)       Port 54321           Localhost)
```

## Important Notes

### Client Isolation
- GUI Client **NEVER** connects directly to LLM Server
- All communication goes through Hole Punching Server
- This ensures NAT traversal works and security is maintained

### Session Persistence
- LLM Server maintains conversation history in `llm_session.json`
- Survives client disconnections and reconnections
- Hole Punching Server can reconnect to same LLM session

### Key Rotation Behavior
- Hole Punching Server rotates keys every hour
- During rotation, client connection may briefly pause
- LLM Server session persists (not affected by key rotation)
- Client automatically handles rotation messages

### Security File Regeneration
- New `clawchat-current.sec` generated every 10 min (if no client)
- Once client connects, regeneration stops
- File contains ephemeral connection credentials only
- Does NOT contain LLM context or conversation history

## Implementation Files

| Component | Main File | Supporting Files |
|-----------|-----------|------------------|
| GUI Client | `src/gui_client.py` | `run_gui_client.py` |
| Hole Punching Server | `src/server/main.py` | `run_server.py` |
| LLM Server | `src/server/llm_server.py` | `run_llm_server.py` |
| Protocol | `src/protocol/messages.py` | Message types, encryption |
| Security | `src/security/*.py` | File manager, key rotation |
| Context | `src/context_loader.py` | SOUL/AGENTS/USER/MEMORY |
| Cron | `src/cron_scheduler.py` | Job scheduling |
| File Protocol | `src/server/file_protocol_handler.py` | File operations |

## Running the System

```bash
# Terminal 1: Start LLM Server (local only)
python run_llm_server.py

# Terminal 2: Start Hole Punching Server (public)
python run_server.py --ip 0.0.0.0

# Terminal 3: Start GUI Client
python run_gui_client.py
# Select the .sec file from hole punching server
```

## Future Enhancements

- **Multiple LLM Servers**: Load balancing across AI backends
- **Hole Punching Cluster**: Multiple relay servers for redundancy
- **WebSocket Bridge**: Alternative transport for hole punching server ↔ LLM server
- **gRPC**: High-performance internal communication
