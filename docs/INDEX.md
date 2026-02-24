# ClawChat Documentation Index

## 📂 Documentation Organization

This directory contains historical documentation from v1.0. **For current documentation, see the main project README and `udp_hole_punching/` docs.**

## 🚀 Current Implementation (v2.0)

Located in [`udp_hole_punching/`](../udp_hole_punching/):

| Document | Description |
|----------|-------------|
| [README.md](../udp_hole_punching/README.md) | UDP hole punching implementation guide |
| [CONTEXT_SYSTEM.md](../udp_hole_punching/CONTEXT_SYSTEM.md) | OpenClaw-style AI context loading |
| [CRON_SYSTEM.md](../udp_hole_punching/CRON_SYSTEM.md) | Automated AI task scheduling |
| [FILE_PROTOCOL.md](../udp_hole_punching/FILE_PROTOCOL.md) | File manager protocol specification |
| [LLM_BRIDGE.md](../udp_hole_punching/LLM_BRIDGE.md) | LLM integration (DeepSeek/OpenAI/Anthropic) |
| [INSTALL.md](../udp_hole_punching/INSTALL.md) | Installation instructions |
| [TEST_LOCAL.md](../udp_hole_punching/TEST_LOCAL.md) | Local testing guide |

## 📜 Archived Documentation (v1.0)

These documents describe the original WebSocket/Mega.nz implementation:

| Document | Description | Status |
|----------|-------------|--------|
| [README.md](README.md) | Original PWA/WebSocket documentation | ⚠️ Archived |
| [PROJECT_SPEC.md](PROJECT_SPEC.md) | v1.0 technical specification | ⚠️ Archived |
| [CHAT_INTERFACE.md](CHAT_INTERFACE.md) | Chat interface design | ⚠️ Archived |
| [SECURITY_ARCHITECTURE_PLAN.md](SECURITY_ARCHITECTURE_PLAN.md) | Security planning | ⚠️ Archived |
| [SECURITY_PROTOCOL_SPECIFICATION.md](SECURITY_PROTOCOL_SPECIFICATION.md) | Security protocol details | ⚠️ Archived |

## 📋 Project Management

| Document | Description |
|----------|-------------|
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines (still relevant) |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Community guidelines (still relevant) |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [TODO.md](todo.md) | Task tracking |
| [TASK_PROGRESS.md](TASK_PROGRESS.md) | Detailed progress tracking |

## 🔒 Security

| Document | Description | Status |
|----------|-------------|--------|
| [SECURITY.md](SECURITY.md) | Security overview | Still relevant |
| [potential_security.md](potential_security.md) | Security considerations | Reference |
| [security-mechanism-mega-udp.md](security-mechanism-mega-udp.md) | Security mechanism comparison | Reference |

## 📊 Project History

| Document | Description |
|----------|-------------|
| [FINAL_COMPLETION_REPORT.md](FINAL_COMPLETION_REPORT.md) | v1.0 completion summary |
| [PHASE2_TESTING_SUMMARY.md](PHASE2_TESTING_SUMMARY.md) | Testing results |
| [GITHUB_PREPARATION_SUMMARY.md](GITHUB_PREPARATION_SUMMARY.md) | GitHub setup notes |

## 🏗️ Architecture Decision Records

| Document | Description |
|----------|-------------|
| [python-udp-hole-punching-plan.md](python-udp-hole-punching-plan.md) | Why UDP hole punching was chosen |
| [SECURITY_IMPLEMENTATION_COORDINATION.md](SECURITY_IMPLEMENTATION_COORDINATION.md) | Security implementation planning |
| [kimi-swarm-instruction.md](kimi-swarm-instruction.md) | AI coordination notes |

## 📝 Templates

| Document | Description |
|----------|-------------|
| [ISSUE_TEMPLATE.md](ISSUE_TEMPLATE.md) | GitHub issue template |
| [PULL_REQUEST_TEMPLATE.md](PULL_REQUEST_TEMPLATE.md) | PR template |
| [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) | Release process |

## 🗺️ Navigation Guide

### Getting Started
1. Start with [../README.md](../README.md) for project overview
2. Read [../udp_hole_punching/README.md](../udp_hole_punching/README.md) for implementation details
3. Follow [../udp_hole_punching/INSTALL.md](../udp_hole_punching/INSTALL.md) for setup

### Understanding the System
1. [../udp_hole_punching/CONTEXT_SYSTEM.md](../udp_hole_punching/CONTEXT_SYSTEM.md) - AI context system
2. [../udp_hole_punching/CRON_SYSTEM.md](../udp_hole_punching/CRON_SYSTEM.md) - Task automation
3. [../udp_hole_punching/FILE_PROTOCOL.md](../udp_hole_punching/FILE_PROTOCOL.md) - File operations

### Contributing
1. [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute
2. [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) - Community standards
3. [CHANGELOG.md](CHANGELOG.md) - What's changed

## ⚠️ Deprecation Notice

Documentation marked with ⚠️ **Archived** describes the v1.0 implementation which used:
- WebSocket communication (replaced with UDP hole punching)
- Mega.nz config storage (replaced with file-based security exchange)
- Browser PWA client (replaced with Tkinter GUI)

These documents are kept for historical reference but may contain outdated information.
