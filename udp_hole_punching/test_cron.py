#!/usr/bin/env python3
"""
Test the cron system
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, 'src')

from cron_scheduler import CronParser, CronScheduler
from datetime import datetime


def main():
    print("="*60)
    print("Cron System Test")
    print("="*60)
    print()
    
    # Test 1: Parse CRON.md
    print("[1] Parsing CRON.md...")
    cron_file = Path('context/CRON.md')
    jobs = CronParser.parse(cron_file)
    
    print(f"    Found {len(jobs)} jobs:")
    for job in jobs:
        status = "[ON]" if job.enabled else "[OFF]"
        print(f"      - {job.name}: {job.schedule} ({status})")
    print()
    
    # Test 2: Schedule matching
    print("[2] Testing schedule matching...")
    now = datetime.now()
    print(f"    Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create mock scheduler to test matching
    scheduler = CronScheduler(cron_file, llm_bridge=None)
    
    for job in jobs:
        should_run = scheduler._should_run(job, now)
        indicator = "[RUN]" if should_run else "[skip]"
        print(f"      {indicator}: {job.name}")
    print()
    
    # Test 3: File watching
    print("[3] Testing file watch...")
    print("    Starting file watcher for 10 seconds...")
    print("    (Try editing context/CRON.md to see reload)")
    
    scheduler._check_and_reload()
    initial_mtime = scheduler._file_mtime
    
    for i in range(10):
        time.sleep(1)
        scheduler._check_and_reload()
        if scheduler._file_mtime != initial_mtime:
            print(f"    [OK] File changed and reloaded!")
            break
        print(f"    {10-i} seconds remaining...")
    else:
        print("    (No changes detected)")
    
    print()
    print("[4] Job details:")
    for job in scheduler.jobs:
        print(f"\n    {job.name}:")
        print(f"      Schedule: {job.schedule}")
        print(f"      Command: {job.command[:50]}...")
        print(f"      Context: {job.context[:50] if job.context else '(none)'}...")
    
    print()
    print("="*60)
    print("Test complete!")
    print("="*60)


if __name__ == '__main__':
    main()
