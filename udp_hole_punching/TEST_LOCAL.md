# Local Testing Guide

Test both client and server on the same Windows PC.

## Quick Start (Automated)

```powershell
# Open terminal in udp_hole_punching folder
cd C:\Users\hippa\src\clawChat\udp_hole_punching

# Install dependencies if not done
pip install cryptography pycryptodome

# Run automated test
python test_local.py
```

## Manual Test (Two Terminals)

### Terminal 1 - Start Server

```powershell
cd C:\Users\hippa\src\clawChat\udp_hole_punching

# Set environment variable
$env:CLAWCHAT_BOOTSTRAP_KEY="local-test-key-32bytes-long!!!"

# Create security directory
mkdir C:\temp\clawchat\security

# Run server
python run_server.py --ip 127.0.0.1 --port 55555
```

You'll see output like:
```
============================================================
  ClawChat UDP Hole Punching Server v2.0
============================================================

[Server] Security file created: C:\temp\clawchat\security\clawchat-20260222-213022.sec
[Server] Transfer this file to client securely
[Server] Listening on UDP 127.0.0.1:55555
[Server] Waiting for hole punch...
```

### Terminal 2 - Start Client

Copy the security file path from the server output, then:

```powershell
cd C:\Users\hippa\src\clawChat\udp_hole_punching

# Set same bootstrap key
$env:CLAWCHAT_BOOTSTRAP_KEY="local-test-key-32bytes-long!!!"

# Run client with the security file (replace with actual path)
python run_client.py --file "C:\temp\clawchat\security\clawchat-20260222-213022.sec"
```

Or use the GUI:
```powershell
python run_client.py
# File browser will open, select the .sec file
```

## Expected Output

### Server Terminal
```
[Server] Peer connected: ('127.0.0.1', 54321)
[Chat] client: Hello server!
[Server] Punch from ('127.0.0.1', 54321) acknowledged
```

### Client Terminal
```
[Client] Connected! Latency: 0.5ms
[Client] Local port: 54321
> Hello server!
[server] Echo: Hello server!
>
```

## Testing Commands

Once connected, type these in the client:

| Command | What Happens |
|---------|--------------|
| `Hello!` | Server echoes back "Echo: Hello!" |
| `/compromised` | Triggers emergency key destruction |
| `/quit` | Disconnects and exits |

## Troubleshooting

### "Address already in use"
The port is still in use. Wait a few seconds or use a different port:
```powershell
python run_server.py --ip 127.0.0.1 --port 55556
```

### "Failed to load security file"
Make sure you copied the exact path and the file exists.

### Nothing happens after connecting
Since both are on localhost, hole punching isn't really needed. The connection should be instant. If stuck, check Windows Firewall isn't blocking Python.

## Stop Testing

- **Client**: Type `/quit` or press Ctrl+C
- **Server**: Press Ctrl+C
