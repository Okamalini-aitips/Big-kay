#!/bin/bash
# Daily pick generation scheduler using cron

# Add this to your crontab to run at 09:30 AM SAST (07:30 UTC)
# Edit crontab: crontab -e
# Add line: 30 7 * * * /app/backend/run_daily_picks.sh

cd /app/backend
python3 scheduler.py >> /var/log/soccer_betting_bot.log 2>&1
