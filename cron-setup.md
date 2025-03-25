# IPL Betting System Automation Guide

This guide shows how to set up automated betting using the cron scheduler on Linux/Mac systems.

## System Overview

The IPL betting system has two main phases:
1. **Prefetch Phase**: Discovers upcoming matches and caches their data
2. **Betting Phase**: Places bets on active matches

## Cron Job Setup

### Understanding Cron Syntax

```
 ┌───────────── minute (0 - 59)
 │ ┌───────────── hour (0 - 23)
 │ │ ┌───────────── day of the month (1 - 31)
 │ │ │ ┌───────────── month (1 - 12)
 │ │ │ │ ┌───────────── day of the week (0 - 6) (Sunday to Saturday)
 │ │ │ │ │
 │ │ │ │ │
 * * * * * [command to execute]
```

### Key Times for IPL Matches

* **Weekday Matches**: 7:30 PM IST (19:30)
* **Weekend Matches**: 
  * Early match: 3:30 PM IST (15:30)
  * Late match: 7:30 PM IST (19:30)

### Recommended Cron Schedule

#### Prefetch Jobs (Run before matches start)

```
# Weekday prefetch (run at 5:30 PM / 17:30 IST - 2 hours before match)
30 17 * * 1-5 cd /path/to/stake && ./ipl_scheduler.py --prefetch >> /path/to/stake/logs/prefetch.log 2>&1

# Weekend early match prefetch (run at 1:30 PM / 13:30 IST - 2 hours before match)
30 13 * * 6,0 cd /path/to/stake && ./ipl_scheduler.py --prefetch >> /path/to/stake/logs/prefetch.log 2>&1

# Weekend late match prefetch (run at 5:30 PM / 17:30 IST - 2 hours before match)
30 17 * * 6,0 cd /path/to/stake && ./ipl_scheduler.py --prefetch >> /path/to/stake/logs/prefetch.log 2>&1
```

#### Betting Jobs (Run during matches)

```
# Weekday betting (run every 5 minutes from 7:30 PM to 10:30 PM)
*/5 19-22 * * 1-5 cd /path/to/stake && ./ipl_scheduler.py --bet >> /path/to/stake/logs/betting.log 2>&1

# Weekend early match betting (run every 5 minutes from 3:30 PM to 6:30 PM)
*/5 15-18 * * 6,0 cd /path/to/stake && ./ipl_scheduler.py --bet >> /path/to/stake/logs/betting.log 2>&1

# Weekend late match betting (run every 5 minutes from 7:30 PM to 10:30 PM)
*/5 19-22 * * 6,0 cd /path/to/stake && ./ipl_scheduler.py --bet >> /path/to/stake/logs/betting.log 2>&1
```

## Setting Up Cron Jobs

1. Create the logs directory:
```bash
mkdir -p /path/to/stake/logs
```

2. Open your crontab file:
```bash
crontab -e
```

3. Add the cron jobs (modify paths as needed)

4. Save and exit

## Testing Your Setup

To test your setup without waiting for the cron jobs to run:

```bash
# Test prefetch mode
./ipl_scheduler.py --prefetch

# Test betting mode
./ipl_scheduler.py --bet
```

## Checking Logs

Monitor the log files to ensure everything is working:

```bash
# View prefetch logs
tail -f /path/to/stake/logs/prefetch.log

# View betting logs
tail -f /path/to/stake/logs/betting.log
```

## Troubleshooting

- **No match found**: Check if the schedule is correctly configured in `data/cache/schedule.json`
- **Authentication issues**: Run with `--auth` flag manually to refresh authentication
- **No bets placed**: Check if any markets match your sanctioned betting criteria in `sanctioned_bets.json` 