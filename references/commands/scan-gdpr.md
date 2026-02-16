# GDPR Compliance Scan

Browser-based GDPR compliance check using OpenClaw's browser automation (CDP).

## Overview

This scan uses headless Chromium to visit a website and check for GDPR compliance indicators. Unlike header and SSL checks (which use Python scripts), GDPR checks require browser automation and are performed by the agent directly using OpenClaw's browser tools.

## What's Checked

| Check | How | Pass Criteria |
|-------|-----|---------------|
| Cookie banner presence | DOM inspection for common banner selectors | Banner appears on first visit |
| Reject/decline option | Check for reject/decline button in banner | Explicit opt-out available |
| Privacy policy link | Search for privacy policy or cookie policy link | Link exists and is accessible |
| Pre-consent tracking | Check cookies before any consent action | No tracking cookies before consent |
| Third-party cookies | Enumerate cookies after page load | Minimal third-party cookies without consent |

## How to Run

The agent uses OpenClaw browser automation tools directly. There is no standalone Python script for GDPR checks.

### Agent Workflow

1. Open browser to target URL in a clean profile (no cookies)
2. Take snapshot of page
3. Check for cookie banner (common selectors: `.cookie-banner`, `#cookie-consent`, `[data-cookiebanner]`, etc.)
4. Check for reject/decline button
5. Check for privacy policy link
6. List all cookies set before any consent action
7. Screenshot the page as evidence
8. Report findings

### Example Telegram Message

"Check GDPR compliance for https://example.com"

### Agent Response Pattern

The agent will:
1. Navigate to the URL in a clean browser profile
2. Analyze the page for GDPR compliance indicators
3. Report findings with pass/fail for each check
4. Offer to save the screenshot as evidence

## Scoring

| Result | Rating |
|--------|--------|
| All checks pass | Compliant |
| Banner present but no reject option | Partially compliant |
| No banner, tracking cookies present | Non-compliant |
| Banner present, no pre-consent tracking | Compliant |

## Capturing Evidence

Screenshots and results can be stored as evidence:

```bash
# Screenshot saved by browser automation
# Then register as evidence:
python3 scripts/db_query.py --action add-evidence \
  --title "GDPR Scan - example.com" \
  --type automated \
  --source "browser-gdpr-check" \
  --filepath ~/.openclaw/grc/evidence/automated/2026-02-11-gdpr-example-com.png \
  --valid-from 2026-02-11 \
  --valid-until 2026-05-11 \
  --control-ids <privacy-related-control-ids>
```

## Limitations

- Cookie banners vary widely; detection is best-effort based on common patterns
- Some sites use JavaScript-heavy banners that may take time to render
- Single-page applications may need additional wait time
- This check is informational, not a legal compliance determination
