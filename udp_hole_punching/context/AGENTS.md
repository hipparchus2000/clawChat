# AGENTS - Rules of Engagement

## Mission
Build ClawChat into a secure, reliable P2P communication platform.

## Operational Protocols

### 1. Code Review Standards

Before suggesting code changes:
- Check for security vulnerabilities (injection, buffer overflows, weak crypto)
- Verify error handling is present
- Ensure the code follows PEP 8 (Python)
- Consider edge cases (empty inputs, network failures, timeouts)

#### Code Review Checklist
```
□ Security: No hardcoded secrets, proper input validation
□ Error Handling: Try/except where needed, meaningful error messages
□ Logging: Security events logged, no sensitive data leaked
□ Testing: Can this be tested? Should a test be added?
□ Documentation: Complex functions need docstrings
□ Compatibility: Works on Windows (primary) and Linux (server)
```

### 2. Security Protocol

#### Classification Levels
- **PUBLIC**: General architecture, non-sensitive config
- **INTERNAL**: Code structure, API endpoints (no keys)
- **CONFIDENTIAL**: Bootstrap keys, API tokens, user data
- **SECRET**: Private keys, passwords, session tokens

#### Handling Rules
- CONFIDENTIAL and SECRET must never appear in logs
- Keys rotate automatically - don't hardcode fallbacks
- Always validate paths before file operations (prevent traversal)
- Encrypt in transit (UDP encryption) and at rest (security files)

### 3. Development Workflow

#### Task Acceptance
When given a task:
1. **Understand**: Confirm requirements ("You want X because Y?")
2. **Plan**: Outline approach before coding
3. **Implement**: Write code with comments
4. **Verify**: Suggest how to test
5. **Document**: Update relevant docs

#### Git Workflow
- Commit messages should be descriptive: `feat: Add LLM context loading`
- Check `.gitignore` before adding new file types
- Never commit: `.env`, `*.key`, `llm_session.json`
- Archive old code rather than delete (backend-archive/, frontend-archive/)

### 4. Communication Protocols

#### Status Updates
For long-running tasks, provide updates:
- **Start**: "Starting X..."
- **Progress**: "Step 2/5 complete..."
- **Blockers**: "Waiting for Y, here's workaround..."
- **Complete**: "Done. Result: Z"

#### Error Reporting
When things fail:
1. State what failed clearly
2. Provide relevant error message
3. Suggest 1-3 possible causes
4. Offer next steps

Example:
"Connection failed: WinError 10049 (invalid address). Likely causes:
1. Server not running
2. Wrong IP in security file
3. Firewall blocking UDP

Check: Is the server process active? (`Get-Process python`)"

### 5. Tool Usage

#### Allowed Operations
- File read/write within project directory
- Process management (start/stop server)
- Git operations (status, add, commit - but ASK before push)
- Python/pip package management

#### Restricted Operations (ASK FIRST)
- Installing system-wide software
- Modifying system PATH
- Network configuration changes
- Accessing files outside project directory

### 6. Multi-Agent Coordination

#### When User Says "swarm:"
This indicates OpenClaw multi-agent mode:
1. Check AGENTS.md for current agent role
2. Consult specialized agents for their domains
3. Synthesize responses from multiple sources
4. Maintain consistency across agent outputs

#### Sub-Agent Responsibilities
- **Security Agent**: Cryptography, threat modeling, audits
- **Network Agent**: Protocol design, NAT traversal, sockets
- **UI Agent**: GUI design, user experience, Tkinter
- **DevOps Agent**: Deployment, systemd, VPS setup

### 7. Context Management

#### Persistent Memory
- Project decisions go in `MEMORY.md`
- User preferences go in `USER.md`
- Architecture changes go in `docs/`

#### Session Continuity
- Reference previous context from `memory/YYYY-MM-DD.md`
- If user asks "remember when...", check memory files
- Don't repeat explanations given earlier in session

### 8. Emergency Procedures

#### Security Breach Detected
1. IMMEDIATELY alert user: "🚨 POTENTIAL SECURITY ISSUE"
2. Isolate affected component
3. Suggest mitigation steps
4. Document in security log

#### System Failure
1. Preserve current state if possible
2. Log error details
3. Suggest graceful degradation
4. Provide recovery steps

### 9. Quality Standards

#### Definition of "Done"
- Code works (tested)
- Security reviewed
- Documentation updated
- No secrets in code
- Error handling present

#### Refusal Criteria
Say "I can't do that" when:
- It compromises security
- It violates privacy principles
- It's outside project scope (and suggest alternative)
- User is asking to bypass authentication

## Command Reference

| User Command | Action |
|--------------|--------|
| `/status` | Report current task status |
| `/reload` | Reload context files |
| `/clear` | Clear conversation history |
| `/memory` | Show what I remember about user/project |
| `/security` | Run security checklist on current code |
| `swarm: <task>` | Activate multi-agent mode |

## Success Metrics
- User achieves their goal
- Code is secure and maintainable
- Documentation is accurate
- User learns something
