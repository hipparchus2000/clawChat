#!/usr/bin/env python3
"""
Cron Scheduler for ClawChat LLM Bridge

Parses CRON.md, watches for changes, and schedules jobs
to run through the LLM session.
"""

import os
import re
import time
import json
import threading
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Optional, Callable, Dict
import hashlib


@dataclass
class CronJob:
    """Represents a single cron job."""
    name: str
    schedule: str
    command: str
    enabled: bool
    context: str
    last_run: Optional[float] = None
    last_result: Optional[str] = None
    run_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'schedule': self.schedule,
            'command': self.command,
            'enabled': self.enabled,
            'context': self.context,
            'last_run': self.last_run,
            'last_result': self.last_result,
            'run_count': self.run_count
        }


class CronParser:
    """Parses CRON.md file into CronJob objects."""
    
    @staticmethod
    def parse(cron_file: Path) -> List[CronJob]:
        """Parse CRON.md and return list of jobs."""
        if not cron_file.exists():
            return []
        
        content = cron_file.read_text(encoding='utf-8')
        jobs = []
        
        # Split by --- (job separator)
        job_sections = re.split(r'\n---+\n', content)
        
        for section in job_sections:
            section = section.strip()
            if not section:
                continue
            
            job = CronParser._parse_job(section)
            if job:
                jobs.append(job)
        
        return jobs
    
    @staticmethod
    def _parse_job(section: str) -> Optional[CronJob]:
        """Parse a single job section."""
        # Must have **Command** to be a valid job
        command_match = re.search(r'\*\*Command\*\*:\s*(.+?)(?=\*\*|$)', section, re.MULTILINE | re.IGNORECASE | re.DOTALL)
        if not command_match:
            return None  # Skip sections without Command (like documentation)
        
        command = command_match.group(1).strip()
        
        # Extract name (## Name)
        name_match = re.search(r'^##\s+(.+)$', section, re.MULTILINE)
        if not name_match:
            return None
        
        name = name_match.group(1).strip()
        
        # Extract schedule
        schedule_match = re.search(r'\*\*Schedule\*\*:\s*(.+?)$', section, re.MULTILINE | re.IGNORECASE)
        schedule = schedule_match.group(1).strip() if schedule_match else "0 0 * * *"
        
        # Extract enabled
        enabled_match = re.search(r'\*\*Enabled\*\*:\s*(true|false)', section, re.MULTILINE | re.IGNORECASE)
        enabled = enabled_match.group(1).lower() == 'true' if enabled_match else True
        
        # Extract context (remaining text after --- or before next section)
        context = ""
        lines = section.split('\n')
        in_context = False
        for line in lines:
            if '**' in line and not in_context:
                continue
            if line.strip() and not line.startswith('##'):
                in_context = True
            if in_context:
                context += line + '\n'
        
        context = context.strip()
        
        return CronJob(
            name=name,
            schedule=schedule,
            command=command,
            enabled=enabled,
            context=context
        )


class CronScheduler:
    """
    Schedules and executes cron jobs through LLM.
    
    Features:
    - Watches CRON.md for changes and reloads automatically
    - Executes jobs at scheduled times
    - Persists job state
    - Provides API for clients to view job list
    """
    
    def __init__(self, cron_file: str, llm_bridge=None, save_file: str = 'cron_state.json'):
        """
        Initialize cron scheduler.
        
        Args:
            cron_file: Path to CRON.md
            llm_bridge: LLMBridge instance to use for execution
            save_file: Path to save job state
        """
        self.cron_file = Path(cron_file)
        self.llm_bridge = llm_bridge
        self.save_file = Path(save_file)
        
        self.jobs: List[CronJob] = []
        self.running = False
        self.check_interval = 30  # seconds
        
        self._file_mtime: Optional[float] = None
        self._file_hash: Optional[str] = None
        self._scheduler_thread: Optional[threading.Thread] = None
        self._watcher_thread: Optional[threading.Thread] = None
        
        # Callbacks
        self.on_job_execute: Optional[Callable[[CronJob], None]] = None
        self.on_job_complete: Optional[Callable[[CronJob, str], None]] = None
        
        # Load initial state
        self._load_state()
        self._check_and_reload()
    
    def _get_file_hash(self) -> str:
        """Get MD5 hash of cron file."""
        if not self.cron_file.exists():
            return ""
        content = self.cron_file.read_bytes()
        return hashlib.md5(content).hexdigest()
    
    def _check_and_reload(self):
        """Check if file changed and reload if needed."""
        if not self.cron_file.exists():
            return
        
        current_mtime = self.cron_file.stat().st_mtime
        current_hash = self._get_file_hash()
        
        # Check if changed
        if (self._file_mtime != current_mtime or 
            self._file_hash != current_hash):
            
            print(f"[Cron] Reloading {self.cron_file.name}...")
            
            # Parse new jobs
            new_jobs = CronParser.parse(self.cron_file)
            
            # Preserve state for existing jobs
            job_state = {j.name: (j.last_run, j.run_count) for j in self.jobs}
            
            for job in new_jobs:
                if job.name in job_state:
                    job.last_run, job.run_count = job_state[job.name]
            
            self.jobs = new_jobs
            self._file_mtime = current_mtime
            self._file_hash = current_hash
            
            self._save_state()
            
            print(f"[Cron] Loaded {len(self.jobs)} jobs")
    
    def _save_state(self):
        """Save job state to file."""
        try:
            data = {
                'jobs': [j.to_dict() for j in self.jobs],
                'last_save': time.time()
            }
            with open(self.save_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[Cron] Failed to save state: {e}")
    
    def _load_state(self):
        """Load job state from file."""
        if not self.save_file.exists():
            return
        
        try:
            with open(self.save_file, 'r') as f:
                data = json.load(f)
            
            # We only load run history, not job definitions
            # (those come from CRON.md)
            job_history = {}
            for j in data.get('jobs', []):
                job_history[j['name']] = {
                    'last_run': j.get('last_run'),
                    'last_result': j.get('last_result'),
                    'run_count': j.get('run_count', 0)
                }
            
            self._job_history = job_history
            
        except Exception as e:
            print(f"[Cron] Failed to load state: {e}")
            self._job_history = {}
    
    def start(self):
        """Start the scheduler."""
        if self.running:
            return
        
        self.running = True
        
        # Start file watcher
        self._watcher_thread = threading.Thread(target=self._watcher_loop, daemon=True)
        self._watcher_thread.start()
        
        # Start scheduler
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        
        print(f"[Cron] Scheduler started, watching {self.cron_file}")
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        
        if self._watcher_thread:
            self._watcher_thread.join(timeout=1)
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=1)
        
        self._save_state()
        print("[Cron] Scheduler stopped")
    
    def _watcher_loop(self):
        """Watch for file changes."""
        while self.running:
            self._check_and_reload()
            time.sleep(5)  # Check every 5 seconds
    
    def _scheduler_loop(self):
        """Main scheduling loop."""
        while self.running:
            now = datetime.now()
            
            for job in self.jobs:
                if not job.enabled:
                    continue
                
                # Check if should run
                if self._should_run(job, now):
                    self._execute_job(job)
            
            time.sleep(self.check_interval)
    
    def _should_run(self, job: CronJob, now: datetime) -> bool:
        """Check if job should run now."""
        # Parse schedule
        schedule = job.schedule.strip()
        
        # Handle special schedules
        if schedule == '@reboot':
            return False  # Only at startup
        if schedule == '@hourly':
            schedule = '0 * * * *'
        elif schedule == '@daily':
            schedule = '0 0 * * *'
        elif schedule == '@weekly':
            schedule = '0 0 * * 0'
        
        parts = schedule.split()
        if len(parts) != 5:
            return False
        
        minute, hour, day, month, dow = parts
        
        # Check if time matches
        if not self._match_field(minute, now.minute):
            return False
        if not self._match_field(hour, now.hour):
            return False
        if not self._match_field(day, now.day):
            return False
        if not self._match_field(month, now.month):
            return False
        if not self._match_field(dow, now.weekday()):
            return False
        
        # Check if already ran this minute
        if job.last_run:
            last_run_dt = datetime.fromtimestamp(job.last_run)
            if (last_run_dt.year == now.year and
                last_run_dt.month == now.month and
                last_run_dt.day == now.day and
                last_run_dt.hour == now.hour and
                last_run_dt.minute == now.minute):
                return False
        
        return True
    
    def _match_field(self, pattern: str, value: int) -> bool:
        """Check if value matches cron pattern."""
        pattern = pattern.strip()
        
        # Wildcard
        if pattern == '*':
            return True
        
        # Specific value
        if pattern.isdigit():
            return int(pattern) == value
        
        # List (e.g., "1,2,3")
        if ',' in pattern:
            return value in [int(x) for x in pattern.split(',')]
        
        # Range (e.g., "1-5")
        if '-' in pattern:
            start, end = pattern.split('-')
            return int(start) <= value <= int(end)
        
        # Step (e.g., */5)
        if pattern.startswith('*/'):
            step = int(pattern[2:])
            return value % step == 0
        
        return False
    
    def _execute_job(self, job: CronJob):
        """Execute a cron job through LLM."""
        print(f"[Cron] Executing: {job.name}")
        
        job.last_run = time.time()
        job.run_count += 1
        
        if self.on_job_execute:
            self.on_job_execute(job)
        
        # Build prompt for LLM
        prompt = f"""Cron Job Execution: {job.name}

Task: {job.command}

Context:
{job.context}

Execute this task and provide a concise summary of what was done and any findings.
"""
        
        # Execute through LLM bridge if available
        if self.llm_bridge:
            try:
                self.llm_bridge.write(prompt)
                
                # Wait for response (with timeout)
                response = None
                for _ in range(120):  # 60 second timeout
                    response = self.llm_bridge.read(timeout=0.5)
                    if response:
                        break
                
                if response:
                    job.last_result = response
                    print(f"[Cron] {job.name} completed")
                    
                    # Log result
                    self._log_result(job, response)
                    
                    if self.on_job_complete:
                        self.on_job_complete(job, response)
                else:
                    job.last_result = "[Timeout - no response from LLM]"
                    print(f"[Cron] {job.name} timed out")
                    
            except Exception as e:
                job.last_result = f"[Error: {e}]"
                print(f"[Cron] {job.name} error: {e}")
        else:
            job.last_result = "[No LLM bridge available]"
        
        self._save_state()
    
    def _log_result(self, job: CronJob, result: str):
        """Log cron job result to file."""
        log_dir = Path('logs/cron')
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"{datetime.now().strftime('%Y-%m')}.log"
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"""
[{timestamp}] {job.name}
Command: {job.command}
Result: {result[:500]}{'...' if len(result) > 500 else ''}
---
"""
        
        with open(log_file, 'a') as f:
            f.write(log_entry)
    
    # ============== API for Clients ==============
    
    def get_jobs(self) -> List[Dict]:
        """Get list of all jobs (for API)."""
        return [j.to_dict() for j in self.jobs]
    
    def get_job(self, name: str) -> Optional[Dict]:
        """Get specific job by name."""
        for job in self.jobs:
            if job.name == name:
                return job.to_dict()
        return None
    
    def run_job_now(self, name: str) -> bool:
        """Manually trigger a job to run immediately."""
        for job in self.jobs:
            if job.name == name:
                threading.Thread(target=self._execute_job, args=(job,), daemon=True).start()
                return True
        return False
    
    def reload(self):
        """Force reload of cron file."""
        self._file_mtime = None
        self._file_hash = None
        self._check_and_reload()


# Example usage
if __name__ == '__main__':
    import sys
    
    cron_file = sys.argv[1] if len(sys.argv) > 1 else './context/CRON.md'
    
    scheduler = CronScheduler(cron_file)
    
    # Print parsed jobs
    print("Parsed Jobs:")
    for job in scheduler.jobs:
        status = "enabled" if job.enabled else "disabled"
        print(f"  [{status}] {job.name}: {job.schedule}")
        print(f"           {job.command[:60]}...")
    
    # Test scheduling
    print("\nTesting schedule matching...")
    now = datetime.now()
    print(f"Current time: {now}")
    
    for job in scheduler.jobs:
        should_run = scheduler._should_run(job, now)
        print(f"  {job.name}: {'WOULD RUN' if should_run else 'skip'}")
