# Scheduled Compliance Audits

Instructions for registering GRC compliance cron jobs using OpenClaw's scheduling system.

## Overview

The GRC skill uses three scheduled jobs:
1. **Evidence Expiry Check**: daily, catches expiring/expired evidence
2. **Compliance Score Recalculation**: every 6 hours, tracks score drift
3. **Weekly Digest**: Monday mornings, full compliance summary

## Prerequisites

- GRC database initialized (`python3 scripts/init_db.py`)
- At least one framework activated
- OpenClaw cron system available (`openclaw cron list`)

## Cron Registration Commands

### 1. Daily Evidence Expiry Check (7 AM)

```bash
openclaw cron add --name "GRC Evidence Expiry" \
  --cron "0 7 * * *" --tz "America/Los_Angeles" \
  --session isolated \
  --message "Using the auditclaw-grc skill, run evidence expiry check. Run: python3 {baseDir}/scripts/evidence_expiry.py --format text --days 30. Report any expired or expiring evidence to the user." \
  --model "sonnet" \
  --announce --channel telegram
```

### 2. Compliance Score Recalculation (Every 6 Hours)

```bash
openclaw cron add --name "GRC Score Recalc" \
  --cron "0 */6 * * *" --tz "America/Los_Angeles" \
  --session isolated \
  --message "Using the auditclaw-grc skill, recalculate compliance scores. Run: python3 {baseDir}/scripts/compliance_score.py --framework soc2 --store. If score drops more than 5 points, alert the user." \
  --model "sonnet" \
  --announce --channel telegram
```

### 3. Weekly Compliance Digest (Monday 8 AM)

```bash
openclaw cron add --name "GRC Weekly Digest" \
  --cron "0 8 * * 1" --tz "America/Los_Angeles" \
  --session isolated \
  --message "Using the auditclaw-grc skill, generate a weekly compliance digest. Include: current score for each active framework, overdue controls count, expiring evidence count, open risks summary, open incidents. Format as a readable summary." \
  --model "sonnet" \
  --announce --channel telegram
```

## Managing Scheduled Jobs

### List Active Jobs

```bash
openclaw cron list
```

### Remove a Job

```bash
openclaw cron remove --name "GRC Evidence Expiry"
```

### Modify Schedule

Remove and re-add with new cron expression:
```bash
openclaw cron remove --name "GRC Score Recalc"
openclaw cron add --name "GRC Score Recalc" \
  --cron "0 */4 * * *" ...
```

### Trigger Manually

```bash
openclaw cron trigger --name "GRC Evidence Expiry"
```

## Session Configuration

All GRC cron jobs use **isolated sessions** for these reasons:
- No conversation context bleed between checks
- Clean agent state per run
- Parallel execution safe (WAL mode SQLite)
- Consistent skill routing via message prefix

## Message Routing

Every cron message **must** include `"Using the auditclaw-grc skill"` at the beginning. This ensures the OpenClaw agent reliably loads the GRC skill in isolated sessions where there's no prior conversation context.

## Delivery Channels

Configure `--channel` to match your preferred notification channel:

| Channel | Flag | Example |
|---------|------|---------|
| Telegram | `--channel telegram` | Default for @YourBotName |
| Slack | `--channel slack --to "channel:C1234"` | Specific channel |
| Discord | `--channel discord --to "channel:123456"` | Server channel |
| WhatsApp | `--channel whatsapp` | Default number |

## Alert Severity Routing

The evidence expiry script returns exit codes:
- **0**: No alerts; cron runs silently (delivery mode: none)
- **1**: Alerts found; triggers announce delivery
- **2**: Error; triggers error notification

For severity-based routing, configure multiple cron jobs:
- **Critical alerts** (daily): Evidence expired, score < 50
- **Warning alerts** (daily digest): Expiring within 7 days, score drop > 5
- **Info updates** (weekly): Full digest, trend summary

## Timezone Considerations

Always specify `--tz` with an IANA timezone. Common options:
- `America/New_York` (ET)
- `America/Chicago` (CT)
- `America/Los_Angeles` (PT)
- `Europe/London` (GMT/BST)
- `Asia/Kolkata` (IST)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Cron job not firing | Check `openclaw cron list`; verify schedule and timezone |
| No alert received | Verify `--announce` flag and `--channel` setting |
| Wrong skill loaded | Ensure message starts with "Using the auditclaw-grc skill" |
| DB not found | Verify GRC_DB_PATH environment variable or use absolute `--db-path` |
| Duplicate alerts | Check if multiple cron jobs registered for same check |
