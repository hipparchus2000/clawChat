# CRON - Scheduled Tasks

This file defines scheduled tasks that run through the LLM.

**Format**: Each job needs:
- `## Job Name` - The heading
- `**Schedule**:` - Cron expression
- `**Command**:` - What to ask the LLM to do
- `**Enabled**:` - true/false
- Context (optional)

---

## Daily Summary

**Schedule**: 0 9 * * *
**Command**: Review yesterday's git commits and provide a summary of changes
**Enabled**: true

Focus on security implications and architectural decisions.

---

## Security Check

**Schedule**: 0 */6 * * *
**Command**: Review recent code for security vulnerabilities
**Enabled**: true

Check for:
- Hardcoded secrets
- Input validation issues
- Insecure crypto usage

---

## Weekly Architecture Review

**Schedule**: 0 10 * * 1
**Command**: Analyze codebase architecture and suggest improvements
**Enabled**: false

Currently disabled - enable when ready for refactoring phase.

---

## Daily Memory Update

**Schedule**: 0 23 * * *
**Command**: Review today's conversation and extract key facts to add to MEMORY.md
**Enabled**: true

Look for:
- New architecture decisions
- Solutions to problems
- Updated preferences
- Important technical details

---

# Cron Format Reference

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday = 0)
│ │ │ │ │
│ │ │ │ │
* * * * *
```

| Schedule | Description |
|----------|-------------|
| `@reboot` | Run when server starts |
| `@hourly` | Same as `0 * * * *` |
| `@daily` | Same as `0 0 * * *` |
| `@weekly` | Same as `0 0 * * 0` |

## Best Practices

- Keep commands specific and focused
- Use `**Enabled**: false` to temporarily disable without deleting
- Add context to help the LLM understand the task
- Don't schedule too frequently (respect API rate limits)
- Review and update cron jobs monthly
