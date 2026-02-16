# Generate Compliance Reports

Creates HTML compliance reports from the GRC database.

## Usage

```bash
python3 scripts/generate_report.py --framework <slug> [--format html] [--output-dir <path>] [--db-path <path>]
```

## Report Contents

- **Compliance Score**: Large visual score with label (Excellent/Good/Fair/etc.)
- **Summary Cards**: Total controls, complete, in progress, not started, evidence count, open risks
- **Controls Table**: All controls with ID, title, category, priority, status, assignee
- **Evidence Table**: All evidence with title, type, status, validity
- **Risks Table**: All risks with title, score, treatment, status

## Output

Reports are saved to `~/.openclaw/grc/reports/` by default.

Filename format: `{framework}-report-{date}.html`

Example: `soc2-report-2026-02-11.html`

## Customization

The report uses an inline HTML/CSS template. For custom branding:
1. Modify the `HTML_TEMPLATE` string in `generate_report.py`
2. Or provide a custom Jinja2 template via `--template` (future enhancement)

## Score Calculation

The report uses the most recent stored compliance score if available (from `compliance_score.py --store`). Otherwise, it calculates a simple percentage based on complete controls.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Report generated successfully |
| 1 | Error (framework not found, DB missing, etc.) |
