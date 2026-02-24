# Cron System Documentation

## Overview

The ClawChat Cron System allows scheduling tasks that run through the LLM session. Jobs are defined in `context/CRON.md`, automatically reloaded when changed, and executed at scheduled times.

## Architecture

```
context/CRON.md
      ↓
[CronScheduler] ← watches for changes
      ↓
[LLM Bridge] ← executes at scheduled times
      ↓
[GUI Client] ← displays status & allows manual trigger
```

## Components

### 1. CRON.md Format

```markdown
## Job Name

**Schedule**: 0 9 * * *
**Command**: Task description for LLM
**Enabled**: true

Optional context for the LLM...

---
```

### 2. CronScheduler (`src/cron_scheduler.py`)

Features:
- **Auto-reload**: Watches file and reloads on changes
- **Standard cron format**: Minute Hour Day Month DayOfWeek
- **Special schedules**: `@hourly`, `@daily`, `@weekly`, `@reboot`
- **State persistence**: Saves run history
- **Logging**: Logs results to `logs/cron/`

### 3. API Integration

Message types for client-server communication:
- `CRON_LIST` - Request/response job list
- `CRON_RUN` - Trigger job immediately
- `CRON_RELOAD` - Force reload of cron file

## Current Jobs

| Job | Schedule | Status | Description |
|-----|----------|--------|-------------|
| Daily Summary | 0 9 * * * | Enabled | Morning code review |
| Security Check | 0 */6 * * * | Enabled | Every 6 hours |
| Weekly Architecture | 0 10 * * 1 | Disabled | Mondays at 10am |
| Daily Memory Update | 0 23 * * * | Enabled | Extract facts at 11pm |

## How It Works

### Server-Side

1. **Startup**:
   ```python
   cron_scheduler = CronScheduler(
       cron_file='./context/CRON.md',
       llm_bridge=self.llm_bridge
   )
   cron_scheduler.start()
   ```

2. **File Watching**: Checks every 5 seconds for changes

3. **Job Execution**:
   - Parses cron schedule
   - Checks every 30 seconds if jobs should run
   - Sends to LLM via `llm_bridge.write()`
   - Logs result

### Client-Side

1. **View Jobs**: Click "🔄 Refresh" in Crontab tab
2. **Run Now**: Select job, click "▶️ Run Now"
3. **Reload**: Click "🔄 Reload File" after editing

## Editing Jobs

### Add New Job

1. Edit `context/CRON.md`
2. Add section:
   ```markdown
   ## My New Job
   
   **Schedule**: 0 */4 * * *
   **Command**: Check disk space and warn if low
   **Enabled**: true
   
   Context for LLM...
   
   ---
   ```
3. Save file - server auto-reloads within 5 seconds

### Disable Job

Change `**Enabled**: true` to `**Enabled**: false`

### Test Schedule

```bash
python -c "
from src.cron_scheduler import CronParser, CronScheduler
from pathlib import Path
from datetime import datetime

jobs = CronParser.parse(Path('context/CRON.md'))
scheduler = CronScheduler('context/CRON.md')

now = datetime.now()
for job in jobs:
    should_run = scheduler._should_run(job, now)
    print(f'{job.name}: {\"RUN\" if should_run else \"skip\"}')
"
```

## Cron Expression Format

```
┌───────────── minute (0-59)
│ ┌───────────── hour (0-23)
│ │ ┌───────────── day of month (1-31)
│ │ │ ┌───────────── month (1-12)
│ │ │ │ ┌───────────── day of week (0-6, Sunday=0)
│ │ │ │ │
* * * * *
```

### Examples

| Expression | Meaning |
|------------|---------|
| `0 * * * *` | Every hour |
| `*/15 * * * *` | Every 15 minutes |
| `0 9 * * *` | Daily at 9:00 AM |
| `0 0 * * 0` | Weekly on Sunday |
| `0 9 * * 1-5` | Weekdays at 9:00 AM |

## Security

- Jobs run with same permissions as server
- LLM has same access as user
- Review commands before enabling
- Disabled by default for sensitive operations

## Logs

Location: `logs/cron/YYYY-MM.log`

Format:
```
[2026-02-24 09:00:00] Daily Summary
Command: Review yesterday's git commits...
Result: [LLM response here]
---
```

## Future Enhancements

- [ ] Job output to chat (notify user)
- [ ] Job dependencies (run B after A)
- [ ] Conditional jobs (only if tests fail)
- [ ] Job results to short-term memory
- [ ] Email notifications for failures
