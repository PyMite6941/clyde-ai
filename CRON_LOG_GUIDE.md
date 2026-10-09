# Clyde Training Cron Logs — Guide

**Purpose:** All Clyde training cron job output logs are written to `~/Clyde/cron_logs/`.

## Directory Structure

```
~/Clyde/cron_logs/
├── automation_cron.log          # Main automation runner output
├── english_trackA.log           # English pack training (5 AM)
├── python_trackA.log            # Python pack training (7 AM)
├── bugs_trackA.log              # Bugs pack training (9 AM)
├── mixed_trackA.log             # Mixed pack training (11 AM)
├── tool-use-citations_trackA.log # Tool-use-citations pack (1 PM)
├── fact-checking_trackA.log     # Fact-checking pack (3 PM)
├── boundary-aware_trackA.log    # Boundary-aware pack (5 PM)
├── daily_evaluate.log           # Daily benchmark evaluation (7 PM)
└── python_eval_fallback.log   # Python eval fallback (8 PM)
```

## Previous Logs (preserved, not overwritten)

- `previous_cron_output.log` — original `cron_output.log` contents
- `previous_run_log.txt` — original `run_log.txt` contents

## How Hermes Agents Can Access Logs

**Path:** `~/Clyde/cron_logs/`

**Quick access commands:**
```bash
# View latest automation output
tail -f ~/Clyde/cron_logs/automation_cron.log

# View a specific pack's training log
tail -f ~/Clyde/cron_logs/english_trackA.log

# View daily evaluation results
tail -f ~/Clyde/cron_logs/daily_evaluate.log
```

## Cron Job Schedule (from current crontab)

| Time       | Pack/Task              | Log File                      |
|------------|------------------------|-------------------------------|
| 03:00      | Automation manager     | `automation_cron.log`         |
| 05:00      | english pack           | `english_trackA.log`          |
| 07:00      | python pack            | `python_trackA.log`           |
| 09:00      | bugs pack              | `bugs_trackA.log`             |
| 11:00      | mixed pack             | `mixed_trackA.log`            |
| 13:00      | tool-use-citations     | `tool-use-citations_trackA.log` |
| 15:00      | fact-checking          | `fact-checking_trackA.log`    |
| 17:00      | boundary-aware         | `boundary-aware_trackA.log`   |
| 19:00      | Daily evaluation       | `daily_evaluate.log`          |
| 20:00      | Python eval fallback   | `python_eval_fallback.log`    |

## What Changed

- All cron output previously went to `~/Clyde/automation/cron_output.log`
- Now each task writes to its own file under `~/Clyde/cron_logs/`
- Old `cron_output.log` preserved as `previous_cron_output.log`
- Old `run_log.txt` preserved as `previous_run_log.txt`

## Verification

```bash
# Check crontab
crontab -l

# Check logs directory
ls -la ~/Clyde/cron_logs/

# Verify scripts point to new locations
grep OUTPUT_LOG /home/pymite6941/Clyde/automation/*.sh /home/pymite6941/Clyde/automation/*.py
```