# GRC Dashboard Command Reference

## Overview
Generate and display an interactive compliance dashboard in the OpenClaw Canvas. The dashboard provides a visual overview of your compliance posture across all active frameworks.

## Commands

### Generate Dashboard
```
/auditclaw-grc generate dashboard
```
Regenerates the dashboard HTML from current database state and deploys it to Canvas.

### View Dashboard
```
/auditclaw-grc show dashboard
```
Opens the dashboard in the Canvas viewer. Equivalent to `canvas navigate ~/clawd/canvas/grc/index.html`.

## Dashboard Sections

| Section | What it Shows |
|---------|---------------|
| Overall Score Gauge | Weighted average across all scored frameworks |
| Framework Cards | Per-framework compliance score with last-scored date |
| Risk Heat Map | 5x5 likelihood-impact grid showing risk distribution |
| Evidence Freshness | Stacked bar: fresh / expiring (30 days) / expired |
| Unresolved Alerts | Latest 8 unresolved alerts with severity badges |
| Integration Health | Provider status, sync time for each integration |
| Control Maturity | Distribution across initial/developing/defined/managed/optimizing |
| Quick Stats | Active incidents, total risks, alerts, evidence count |
| Quick Actions | One-click buttons to invoke common GRC commands |

## Auto-Refresh
The dashboard automatically reloads every 5 minutes. For real-time updates, regenerate manually after making changes.

## CLI Usage
```bash
python3 scripts/generate_dashboard.py --db-path ~/.openclaw/grc/compliance.sqlite
python3 scripts/generate_dashboard.py --db-path ~/.openclaw/grc/compliance.sqlite --output ~/clawd/canvas/grc/index.html
```

### Arguments
| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--db-path` | Yes | - | Path to compliance SQLite database |
| `--output` | No | `~/clawd/canvas/grc/index.html` | Output path for generated HTML |

## Output
The script prints JSON to stdout upon completion:
```json
{
  "status": "ok",
  "output": "~/clawd/canvas/grc/index.html",
  "overall_score": 78.5,
  "frameworks": 3,
  "alerts": 2,
  "evidence_items": 45,
  "generated_at": "2026-02-13T10:30:00"
}
```

## Scheduling
To keep the dashboard current, add a cron job:
```
cron add --name "dashboard-refresh" \
  --schedule "*/30 * * * *" \
  --command "python3 ~/clawd/skills/auditclaw-grc/scripts/generate_dashboard.py --db-path ~/.openclaw/grc/compliance.sqlite"
```
