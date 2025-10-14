# Collaborative Session Cleanup

This document explains how to set up automatic cleanup of expired collaborative coding sessions.

## Overview

Collaborative sessions expire after 7 days of inactivity. The `cleanup_sessions` management command marks expired sessions as inactive and updates member records.

## Manual Execution

### Basic Usage
```bash
python manage.py cleanup_sessions
```

### Dry Run (Preview without changes)
```bash
python manage.py cleanup_sessions --dry-run
```

### Verbose Output
```bash
python manage.py cleanup_sessions --verbose
```

### Combined Options
```bash
python manage.py cleanup_sessions --dry-run --verbose
```

## Automated Cleanup with Cron

### Setup Instructions

1. **Open crontab editor:**
   ```bash
   crontab -e
   ```

2. **Add cleanup job (runs daily at 2 AM):**
   ```bash
   0 2 * * * cd /workspaces/CLASS-XII/api && /workspaces/CLASS-XII/.venv/bin/python manage.py cleanup_sessions >> /var/log/cleanup_sessions.log 2>&1
   ```

3. **Save and exit** (Ctrl+X, then Y, then Enter in nano)

### Alternative Schedules

**Every 6 hours:**
```bash
0 */6 * * * cd /workspaces/CLASS-XII/api && /workspaces/CLASS-XII/.venv/bin/python manage.py cleanup_sessions
```

**Once a week (Sunday at 3 AM):**
```bash
0 3 * * 0 cd /workspaces/CLASS-XII/api && /workspaces/CLASS-XII/.venv/bin/python manage.py cleanup_sessions
```

**Every day at midnight:**
```bash
0 0 * * * cd /workspaces/CLASS-XII/api && /workspaces/CLASS-XII/.venv/bin/python manage.py cleanup_sessions
```

### Verify Cron Job

List all cron jobs:
```bash
crontab -l
```

## What Gets Cleaned Up

The command:
1. ✅ Marks expired collaborative sessions as `is_active=False`
2. ✅ Updates all session members to `is_online=False`
3. ✅ Preserves session data for historical purposes
4. ✅ Shows statistics about active vs inactive sessions

## Monitoring

### Check Logs
```bash
tail -f /var/log/cleanup_sessions.log
```

### Manual Check for Expired Sessions
```bash
python manage.py cleanup_sessions --dry-run --verbose
```

## Production Recommendations

### Using systemd Timer (Alternative to Cron)

1. **Create service file:** `/etc/systemd/system/cleanup-sessions.service`
   ```ini
   [Unit]
   Description=Cleanup expired collaborative sessions
   
   [Service]
   Type=oneshot
   User=www-data
   WorkingDirectory=/workspaces/CLASS-XII/api
   ExecStart=/workspaces/CLASS-XII/.venv/bin/python manage.py cleanup_sessions
   StandardOutput=journal
   StandardError=journal
   ```

2. **Create timer file:** `/etc/systemd/system/cleanup-sessions.timer`
   ```ini
   [Unit]
   Description=Run cleanup-sessions daily
   
   [Timer]
   OnCalendar=daily
   Persistent=true
   
   [Install]
   WantedBy=timers.target
   ```

3. **Enable and start:**
   ```bash
   sudo systemctl enable cleanup-sessions.timer
   sudo systemctl start cleanup-sessions.timer
   ```

4. **Check status:**
   ```bash
   sudo systemctl status cleanup-sessions.timer
   sudo systemctl list-timers
   ```

### Database Optimization

For large databases, consider adding database indexes:
```python
# In models.py
class SharedCode(models.Model):
    # ... existing fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['session_type', 'is_active', 'expires_at']),
        ]
```

Then run:
```bash
python manage.py makemigrations
python manage.py migrate
```

## Troubleshooting

### Command Not Found
Make sure you're in the correct directory and using the virtual environment Python:
```bash
cd /workspaces/CLASS-XII/api
/workspaces/CLASS-XII/.venv/bin/python manage.py cleanup_sessions
```

### Permission Denied
Check file permissions:
```bash
chmod +x /workspaces/CLASS-XII/api/manage.py
```

### Cron Not Running
Check cron service:
```bash
sudo systemctl status cron
sudo systemctl start cron
```

Check syslog for cron errors:
```bash
grep CRON /var/log/syslog
```

## Statistics

To see current session statistics:
```bash
python manage.py cleanup_sessions --dry-run --verbose
```

This shows:
- Active sessions
- Total sessions
- Inactive sessions
- Sessions that would be cleaned up

## Notes

- Expired sessions are marked as **inactive**, not deleted
- Session data is preserved for historical analysis
- Members are marked as **offline** when sessions expire
- The command is safe to run multiple times
- Use `--dry-run` to preview changes before applying
