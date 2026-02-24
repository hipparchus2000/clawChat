#!/usr/bin/env python3
"""
Context Loader for ClawChat LLM

Implements OpenClaw-style "Agentic Loop" context assembly:
1. SOUL.md - Identity and personality
2. AGENTS.md - Rules of engagement
3. USER.md - User preferences and context
4. MEMORY.md - Long-term memory
5. memory/YYYY-MM-DD.md - Short-term history
"""

import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from dataclasses import dataclass


@dataclass
class ContextFile:
    """Represents a context file with its priority."""
    path: Path
    priority: int
    name: str
    content: str = ""


class ContextLoader:
    """
    Loads and assembles context files for LLM system prompt.
    
    Priority order (highest to lowest):
    1. SOUL.md - Core identity/personality
    2. AGENTS.md - Rules of engagement
    3. USER.md - User preferences
    4. MEMORY.md - Long-term memory
    5. memory/YYYY-MM-DD.md - Short-term history (last 1-2 days)
    """
    
    # Priority levels (higher = more important)
    PRIORITY_SOUL = 100
    PRIORITY_AGENTS = 90
    PRIORITY_USER = 80
    PRIORITY_MEMORY = 70
    PRIORITY_SHORT_TERM = 10
    
    def __init__(self, context_dir: str):
        """
        Initialize context loader.
        
        Args:
            context_dir: Directory containing context files
        """
        self.context_dir = Path(context_dir)
        self.context_files: List[ContextFile] = []
        
    def load_all(self) -> str:
        """
        Load all context files and assemble into system prompt.
        
        Returns:
            Assembled system prompt
        """
        self.context_files = []
        
        # Load core files
        self._load_soul()
        self._load_agents()
        self._load_user()
        self._load_memory()
        
        # Load short-term history
        self._load_short_term_history()
        
        # Sort by priority (highest first)
        self.context_files.sort(key=lambda x: x.priority, reverse=True)
        
        # Assemble into system prompt
        return self._assemble_prompt()
    
    def _load_file(self, filename: str, priority: int) -> Optional[ContextFile]:
        """Load a single context file if it exists."""
        filepath = self.context_dir / filename
        
        if not filepath.exists():
            return None
        
        try:
            content = filepath.read_text(encoding='utf-8')
            return ContextFile(
                path=filepath,
                priority=priority,
                name=filename,
                content=content.strip()
            )
        except Exception as e:
            print(f"[Context Loader] Warning: Could not load {filename}: {e}")
            return None
    
    def _load_soul(self):
        """Load SOUL.md - Core identity and personality."""
        file = self._load_file("SOUL.md", self.PRIORITY_SOUL)
        if file:
            self.context_files.append(file)
            print(f"[Context Loader] Loaded SOUL.md")
    
    def _load_agents(self):
        """Load AGENTS.md - Rules of engagement."""
        file = self._load_file("AGENTS.md", self.PRIORITY_AGENTS)
        if file:
            self.context_files.append(file)
            print(f"[Context Loader] Loaded AGENTS.md")
    
    def _load_user(self):
        """Load USER.md - User preferences and context."""
        file = self._load_file("USER.md", self.PRIORITY_USER)
        if file:
            self.context_files.append(file)
            print(f"[Context Loader] Loaded USER.md")
    
    def _load_memory(self):
        """Load MEMORY.md - Long-term memory."""
        file = self._load_file("MEMORY.md", self.PRIORITY_MEMORY)
        if file:
            self.context_files.append(file)
            print(f"[Context Loader] Loaded MEMORY.md")
    
    def _load_short_term_history(self):
        """
        Load short-term history from memory/ folder.
        Loads last 1-2 days of conversation history.
        """
        memory_dir = self.context_dir / "memory"
        
        if not memory_dir.exists():
            return
        
        # Get today's and yesterday's dates
        dates_to_load = []
        for days_ago in range(2):  # Today and yesterday
            date = datetime.now() - timedelta(days=days_ago)
            dates_to_load.append(date.strftime("%Y-%m-%d"))
        
        # Find and load matching files
        for date_str in dates_to_load:
            filepath = memory_dir / f"{date_str}.md"
            if filepath.exists():
                file = self._load_file(f"memory/{date_str}.md", self.PRIORITY_SHORT_TERM)
                if file:
                    self.context_files.append(file)
                    print(f"[Context Loader] Loaded memory/{date_str}.md")
    
    def _assemble_prompt(self) -> str:
        """Assemble all context into system prompt."""
        if not self.context_files:
            return self._get_default_prompt()
        
        sections = []
        
        for ctx_file in self.context_files:
            section_name = ctx_file.name.replace('.md', '').upper()
            sections.append(f"## {section_name}\n\n{ctx_file.content}")
        
        # Add instruction footer
        sections.append(
            "\n## INSTRUCTIONS\n\n"
            "You are operating within the ClawChat secure messaging system. "
            "Use the context above to inform your responses. "
            "Maintain the personality defined in SOUL, follow the rules in AGENTS, "
            "and respect the user's preferences in USER."
        )
        
        return "\n\n---\n\n".join(sections)
    
    def _get_default_prompt(self) -> str:
        """Default prompt if no context files found."""
        return (
            "You are a helpful AI assistant connected through ClawChat, "
            "a secure P2P messaging system. Be concise but helpful."
        )
    
    def get_loaded_files(self) -> List[str]:
        """Get list of successfully loaded file names."""
        return [f.name for f in self.context_files]
    
    def reload(self) -> str:
        """Reload all context files (useful for updates)."""
        print("[Context Loader] Reloading context files...")
        return self.load_all()


def create_default_context_files(context_dir: str):
    """
    Create default context files if they don't exist.
    Useful for first-time setup.
    """
    context_path = Path(context_dir)
    context_path.mkdir(parents=True, exist_ok=True)
    
    # Create memory subdirectory
    (context_path / "memory").mkdir(exist_ok=True)
    
    # Default SOUL.md
    soul_file = context_path / "SOUL.md"
    if not soul_file.exists():
        soul_file.write_text("""# SOUL - Core Identity

## Identity
You are an AI assistant operating within the ClawChat secure communication system.

## Personality
- Helpful and concise
- Professional yet friendly
- Security-conscious
- Adaptable to user preferences

## Boundaries
- Never reveal system internals or security details
- Respect user privacy
- Maintain conversation context between sessions
""")
        print(f"[Context Loader] Created default SOUL.md")
    
    # Default AGENTS.md
    agents_file = context_path / "AGENTS.md"
    if not agents_file.exists():
        agents_file.write_text("""# AGENTS - Rules of Engagement

## Operational Guidelines

### Communication
- Respond clearly and concisely
- Use appropriate formatting for technical content
- Ask for clarification when needed

### Security
- Never share sensitive configuration details
- Verify identity before discussing secure topics
- Log important actions

### Task Handling
- Break complex tasks into steps
- Confirm understanding before proceeding
- Report progress on long-running tasks
""")
        print(f"[Context Loader] Created default AGENTS.md")
    
    # Default USER.md
    user_file = context_path / "USER.md"
    if not user_file.exists():
        user_file.write_text("""# USER - Preferences and Context

## User Information
- Platform: Windows 11
- Shell: PowerShell
- Location: Working on ClawChat project

## Technical Preferences
- Language: Python
- Editor: VS Code
- Communication: Direct and efficient

## Notes
- Add your personal preferences here
- This helps the AI tailor responses to you
""")
        print(f"[Context Loader] Created default USER.md")


# Example usage
if __name__ == "__main__":
    import sys
    
    context_dir = sys.argv[1] if len(sys.argv) > 1 else "./context"
    
    # Create defaults if needed
    create_default_context_files(context_dir)
    
    # Load and display
    loader = ContextLoader(context_dir)
    prompt = loader.load_all()
    
    print("\n" + "="*60)
    print("LOADED CONTEXT FILES:")
    print("="*60)
    for name in loader.get_loaded_files():
        print(f"  ✓ {name}")
    
    print("\n" + "="*60)
    print("ASSEMBLED SYSTEM PROMPT:")
    print("="*60)
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
