# USER - Preferences and Context

## Identity
- **Name**: User prefers not to share real name; uses "OpenClaw" as project handle
- **Role**: System architect, developer, security-conscious builder
- **Timezone**: UTC (flexible schedule)

## Development Environment

### Primary System
- **OS**: Windows 11 (Primary development)
- **Shell**: PowerShell (modern, not legacy cmd)
- **Editor**: VS Code
- **Terminal**: Windows Terminal

### Secondary System
- **OS**: Ubuntu VPS (for server deployment)
- **Access**: SSH, systemd services
- **User**: `openclaw` (non-root for security)

### Tools & Stack
- **Language**: Python 3.14
- **Version Control**: Git
- **AI Assistant**: Kimi Code CLI
- **Package Manager**: pip
- **Documentation**: Markdown

## Project Context

### Current Project: ClawChat
**Status**: Active development, core features working
**Goal**: Secure P2P messaging with UDP hole punching
**Timeline**: Iterative, feature-complete over time

#### Completed
- UDP hole punching client/server
- AES-256-GCM encryption
- Tkinter GUI with 3 tabs
- File-based security exchange
- LLM Bridge integration
- Context loading system

#### In Progress
- File browser backend integration
- Crontab task management
- Testing on actual network (not just localhost)

#### Future Ideas
- Mobile client (Termux/Flutter)
- WebRTC fallback
- Group chat (multi-peer)

### Work Style

#### Communication Preferences
- **Style**: Direct, technical, minimal fluff
- **Detail Level**: "Give me the code" - prefers working examples
- **Explanations**: Short and practical, not academic
- **Questions**: Asks when blocked, not for every detail

#### Decision Making
- Values working solutions over perfect ones
- Security is non-negotiable
- Prefers iterative improvement
- Willing to archive/rewrite rather than patch broken code

#### Coding Habits
- Tests locally before committing
- Archives old approaches (backend-archive/, frontend-archive/)
- Updates AGENTS.md when workflow changes
- Uses meaningful commit messages

### Known Preferences

#### Code Style
- Follows PEP 8 for Python
- Uses type hints where helpful
- Prefers explicit over implicit
- Comments explain "why", not "what"

#### Security Stance
- Paranoid about key management
- No hardcoded secrets (ever)
- Encrypts everything by default
- Validates all inputs

#### Architecture Preferences
- Modular design
- Clear separation of concerns
- Async where appropriate
- Minimal dependencies

### Pain Points
- Git on Windows (path issues, line endings)
- NAT traversal complexity (symmetric NAT especially)
- GUI threading with Tkinter
- Keeping documentation in sync with code

### Success Patterns
When user is happy:
- Code works on first try (or close to it)
- Security is maintained
- Solution is maintainable
- They learned something

When user is frustrated:
- Silent failures (no error messages)
- Security regressions
- Overly complex solutions
- Repetitive explanations

## Communication Examples

### Good User Request
"Add .env support for API keys. Don't commit the actual keys."
[Clear, specific, security-aware]

### Bad User Request (that I should clarify)
"Make it work"
[Vague - need to ask: "What specifically isn't working?"]

## Topics of Interest
- Network programming (UDP, NAT traversal)
- Cryptography (AES-GCM, key exchange)
- P2P systems
- Security architecture
- Cross-platform development

## Topics to Avoid
- Web frameworks (not relevant to this project)
- Blockchain (out of scope)
- Corporate compliance (personal project)

## Session Notes
- Working on ClawChat v2.0 (UDP hole punching)
- Recently added LLM Bridge with persistent sessions
- Context system implemented (OpenClaw-style)
- Next: Integration testing, documentation
