# Auto-Evidence Cron Setup Reference

## Overview
This guide describes how to set up scheduled evidence collection using OpenClaw's cron system. Once configured, evidence is collected automatically and drift detection alerts you to any changes.

## Prerequisites
1. auditclaw-grc skill installed with database initialized
2. auditclaw-aws and/or auditclaw-github companion skills installed
3. AWS credentials configured (`aws configure`) or GitHub token set (`GITHUB_TOKEN`)
4. Integration registered via `add-integration`

## Setting Up AWS Auto-Evidence

### 1. Register the integration
```
/auditclaw-grc add-integration --provider aws --name "AWS Production"
```

### 2. Register cron job
```
cron add --name "aws-evidence-sweep" \
  --schedule "0 6 * * *" \
  --command "python3 ~/clawd/skills/auditclaw-aws/scripts/aws_evidence.py --db-path ~/.openclaw/grc/compliance.sqlite --all"
```
This runs daily at 6:00 AM UTC.

### 3. Optional: Add drift detection after sweep
```
cron add --name "aws-drift-check" \
  --schedule "15 6 * * *" \
  --command "python3 ~/clawd/skills/auditclaw-grc/scripts/drift_detector.py --db-path ~/.openclaw/grc/compliance.sqlite --provider aws"
```
This runs 15 minutes after the evidence sweep to detect any drift.

## Setting Up GitHub Auto-Evidence

### 1. Register the integration
```
/auditclaw-grc add-integration --provider github --name "GitHub Org"
```

### 2. Register cron job
```
cron add --name "github-evidence-sweep" \
  --schedule "0 7 * * *" \
  --command "GITHUB_TOKEN=<token> python3 ~/clawd/skills/auditclaw-github/scripts/github_evidence.py --db-path ~/.openclaw/grc/compliance.sqlite --org <org-name> --all"
```

> **Security note:** Rather than inlining tokens in cron commands (visible via `ps aux`), use the `store-credential` action to save credentials securely.

### 3. Optional: Add drift detection
```
cron add --name "github-drift-check" \
  --schedule "15 7 * * *" \
  --command "python3 ~/clawd/skills/auditclaw-grc/scripts/drift_detector.py --db-path ~/.openclaw/grc/compliance.sqlite --provider github"
```

## Recommended Schedules

| Job | Schedule | Frequency | Why |
|-----|----------|-----------|-----|
| AWS evidence sweep | `0 6 * * *` | Daily 6 AM | Catch overnight changes |
| GitHub evidence sweep | `0 7 * * *` | Daily 7 AM | After AWS sweep |
| Drift detection | `0 8 * * *` | Daily 8 AM | After all sweeps complete |
| Compliance digest | `0 9 * * 1` | Weekly Monday 9 AM | Start-of-week summary |
| Dashboard refresh | `*/30 * * * *` | Every 30 min | Keep dashboard current |

## Managing Cron Jobs

### List all jobs
```
cron list
```

### Remove a job
```
cron remove --name "aws-evidence-sweep"
```

### Modify schedule
```
cron update --name "aws-evidence-sweep" --schedule "0 */6 * * *"
```

## Troubleshooting

### Credential Issues
- **AWS**: Ensure `~/.aws/credentials` exists or IAM instance role is attached
- **GitHub**: Verify `GITHUB_TOKEN` has `repo`, `admin:org`, `security_events` scopes
- **Expired tokens**: GitHub tokens expire; use fine-grained PATs with auto-renewal

### Rate Limits
- **AWS**: boto3 handles retries automatically; add `--region` to limit scope
- **GitHub**: Default rate limit is 5000 req/hour; sweep uses ~50-100 per org

### Error Handling
- Check integration health: `/auditclaw-grc integration-health`
- View error details: `list-integrations --status error`
- Errors increment `error_count` on the integration record
- After 3 consecutive errors, consider disabling the integration

### Log Locations
- Evidence sweep output: Check cron job logs via `cron logs --name <job-name>`
- Drift alerts: `list-alerts --type drift_detected`
- Integration sync status: `list-integrations`
