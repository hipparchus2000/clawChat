# LLM Bridge for ClawChat

Persistent AI conversation support for ClawChat. The LLM Bridge maintains conversation history even when clients disconnect and reconnect.

## Features

- **Persistent Sessions**: Conversation history survives client disconnections
- **Multiple Providers**: DeepSeek, OpenAI, Anthropic (Claude)
- **Configurable**: Set provider via command line or environment
- **Secure**: All communication encrypted end-to-end
- **Stdin/Stdout Interface**: Simple interface for integration

## Quick Start

### 1. Configure API Key

Copy `.env.example` to `.env` and add your API key:

```powershell
cd udp_hole_punching
copy .env.example .env
```

Edit `.env` and add your API key:
```
DEEPSEEK_API_KEY=sk-your-actual-api-key-here
```

**Or set environment variable:**
```powershell
$env:DEEPSEEK_API_KEY="your-deepseek-api-key"
```

**OpenAI:**
```powershell
$env:OPENAI_API_KEY="your-openai-api-key"
```

**Anthropic:**
```powershell
$env:ANTHROPIC_API_KEY="your-anthropic-api-key"
```

### 2. Start LLM Server

```powershell
cd udp_hole_punching
python run_llm_server.py --provider deepseek
```

### 3. Connect with GUI Client

```powershell
python run_gui_client.py
```

Click **Connect** → Select the security file → Start chatting with AI!

## Configuration

### Server Options

```bash
python run_llm_server.py \
  --provider deepseek \          # LLM provider: deepseek, openai, anthropic
  --ip 127.0.0.1 \               # Server IP
  --port 55555 \                 # Server port (random if not specified)
  --security-dir ./security \    # Security files directory
  --llm-session session.json     # Conversation save file
```

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `DEEPSEEK_API_KEY` | API key for DeepSeek |
| `OPENAI_API_KEY` | API key for OpenAI |
| `ANTHROPIC_API_KEY` | API key for Anthropic |
| `CLAWCHAT_BOOTSTRAP_KEY` | Bootstrap key for security files |

## Architecture

```
[ClawChat GUI] ←→ [ClawChat Server] ←→ [LLM Bridge] ←→ [DeepSeek/OpenAI/Anthropic]
                        ↑                  ↑
                   UDP encrypted       Maintains history
                   connection          & context
```

### Persistence

The LLM Bridge saves conversation history to a JSON file (default: `llm_session.json`).

- **Between reconnections**: Client disconnects, reconnects → Same conversation continues
- **System restarts**: Stop server, restart → History preserved
- **Clear history**: Send `/clear` command or delete the JSON file

## Test Without API Keys

Use the mock bridge for testing:

```powershell
python test_llm_bridge.py
```

This runs without API keys and provides fake responses.

## How It Works

1. **Server starts** → Creates security file for client authentication
2. **LLM Bridge starts** → Loads previous conversation history (if exists)
3. **Client connects** → Authenticates with security file
4. **User sends message** → Encrypted, sent to server, forwarded to LLM Bridge
5. **LLM processes** → API call made, response received
6. **Response returned** → Encrypted, sent back to client
7. **History saved** → Conversation persisted to file

## Commands

In the chat, you can type:

| Command | Action |
|---------|--------|
| `/clear` | Clear conversation history |
| `/history` | Show conversation history |
| `/quit` | Disconnect |

## Troubleshooting

### "API key not set"
Set the appropriate environment variable for your provider.

### "No response from AI"
- Check internet connection
- Verify API key is valid
- Check API rate limits

### "Failed to decrypt"
Client and server using different bootstrap keys. Use the same key.

## Implementation Details

- **File**: `src/llm_bridge.py`
- **Server**: `src/server/llm_server.py`
- **History format**: JSON with role, content, timestamp
- **Context window**: Last 20 messages sent to API (configurable)

## Future Enhancements

- Streaming responses for real-time typing effect
- Multi-user support with separate sessions
- File attachment support for analysis
- Custom system prompts per session
