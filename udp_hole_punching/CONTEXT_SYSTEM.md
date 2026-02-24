# Context System - OpenClaw-Style Agentic Loop

ClawChat implements an OpenClaw-style "Agentic Loop" context loading system that assembles the LLM's system prompt from multiple files in priority order.

## File Priority Order

Files are loaded and assembled in this priority (highest to lowest):

| Priority | File | Purpose |
|----------|------|---------|
| 100 | `SOUL.md` | **Identity** - Core personality, tone, boundaries |
| 90 | `AGENTS.md` | **Rules** - Operational logic, how to handle tasks |
| 80 | `USER.md` | **Context** - User preferences, timezone, tech setup |
| 70 | `MEMORY.md` | **Long-term Memory** - Distilled wisdom, learned facts |
| 10 | `memory/YYYY-MM-DD.md` | **Short-term History** - Last 1-2 days of conversation |

## File Descriptions

### SOUL.md - The Identity (Priority: Highest)

Defines the agent's core personality, tone, and "unbreakable" boundaries. This is the first thing injected into the system prompt.

**Example:**
```markdown
# SOUL - Core Identity

## Identity
You are a security-focused AI assistant specializing in network protocols.

## Personality
- Concise and precise
- Security-conscious
- Patient with technical questions

## Boundaries
- Never reveal cryptographic keys
- Don't execute commands without confirmation
- Maintain professional tone
```

### AGENTS.md - Rules of Engagement (Priority: High)

Standing orders for how to operate. Contains operational logic for sub-agents, permissions, and formatting.

**Example:**
```markdown
# AGENTS - Rules of Engagement

## Task Handling
- Break complex tasks into numbered steps
- Ask for confirmation before destructive operations
- Report progress every 30 seconds on long tasks

## Communication
- Use code blocks for technical content
- Summarize long outputs
- Highlight security warnings

## Security Protocols
- Verify identity before discussing sensitive topics
- Log all file system modifications
- Confirm before network operations
```

### USER.md - The Context (Priority: Medium)

Who the agent is talking to. Contains user preferences, environment, and personal context.

**Example:**
```markdown
# USER - Preferences and Context

## Environment
- OS: Windows 11
- Shell: PowerShell
- Editor: VS Code
- Working Dir: C:\Users\hippa\src\clawChat

## Technical Stack
- Language: Python 3.14
- Project: ClawChat (UDP hole punching)
- Tools: Git, Kimi CLI

## Preferences
- Preferred communication: Direct and efficient
- Skill level: Advanced programmer
- Interests: Networking, security, P2P systems
```

### MEMORY.md - Long-Term Memory (Priority: Medium/Low)

Curated distilled wisdom. Facts the agent has learned that should persist.

**Example:**
```markdown
# MEMORY - Long-Term Knowledge

## Project Facts
- ClawChat uses UDP hole punching for NAT traversal
- Security files use AES-256-GCM encryption
- Default port range: 49152-65535

## User Habits
- Prefers PowerShell over cmd
- Uses Windows but familiar with Linux
- Tests code before committing

## Lessons Learned
- Hole punching fails on symmetric NAT
- Always validate paths before file operations
- Keep bootstrap keys out of git
```

### memory/YYYY-MM-DD.md - Short-Term History (Priority: Lowest)

Raw conversation logs from the last 1-2 days for immediate continuity.

**Example:** `memory/2026-02-22.md`
```markdown
# Conversation Log - 2026-02-22

## Session 1
- User started LLM server
- Tested connection with GUI client
- Fixed bootstrap key mismatch issue
- Successfully connected to DeepSeek API

## Session 2
- Worked on context loading system
- Created SOUL.md and AGENTS.md
- Tested file priority loading
```

## Configuration

Set the context directory in `.env`:

```ini
CLAWCHAT_CONTEXT_DIR=./context
```

Or use default (`./context` in the project directory).

## Automatic File Creation

If files don't exist, the system creates defaults on first run:

```
context/
├── SOUL.md              # Created with default identity
├── AGENTS.md            # Created with default rules
├── USER.md              # Created with template
├── MEMORY.md            # Optional - create manually
└── memory/              # Created automatically
    └── 2026-02-22.md    # Created for daily logs
```

## Usage

### 1. Create Context Directory

```powershell
cd udp_hole_punching
mkdir context
mkdir context\memory
```

### 2. Edit Context Files

```powershell
notepad context/SOUL.md
notepad context/AGENTS.md
notepad context/USER.md
```

### 3. Start Server

```powershell
python run_llm_server.py
```

The server will:
1. Load all context files in priority order
2. Assemble into system prompt
3. Start LLM with full context

### 4. View Loaded Context

```powershell
python -c "
from context_loader import ContextLoader
loader = ContextLoader('./context')
prompt = loader.load_all()
print(prompt)
"
```

## Updating Context

Context is loaded **once at startup**. To update:

1. Edit the files
2. Restart the server: `Ctrl+C`, then `python run_llm_server.py`

Or use the reload command (if implemented in client):

```
> /reload
```

## Best Practices

### SOUL.md
- Keep identity consistent
- Define clear boundaries
- Be specific about tone

### AGENTS.md
- Update as workflows change
- Add new operational patterns
- Document security procedures

### USER.md
- Update when environment changes
- Add new preferences as learned
- Include relevant project context

### MEMORY.md
- Add distilled facts, not raw logs
- Update when new patterns emerge
- Keep concise (LLM has context limits)

### memory/*.md
- Let the system auto-create these
- Review periodically for important facts to promote to MEMORY.md
- Archive old files (system loads last 2 days only)

## Context Size Limits

Be mindful of total context size:
- **SOUL**: ~500 tokens
- **AGENTS**: ~1000 tokens
- **USER**: ~500 tokens
- **MEMORY**: ~1000 tokens
- **History**: ~2000 tokens (last 2 days)

**Total**: ~5000 tokens

If exceeding limits, the system will truncate from lowest priority first.

## Security Notes

- **Never commit SOUL.md or USER.md if they contain sensitive info**
- Add to `.gitignore`:
  ```
  context/SOUL.md
  context/USER.md
  context/MEMORY.md
  context/memory/
  ```
- Keep templates in version control, personal files local
