# Security Header Scan

Checks HTTP security headers for a web application and scores the results.

## Usage

```bash
python3 scripts/check_headers.py --url <url> [--format json|text]
```

## Headers Checked

| Header | Weight | Severity if Missing | Purpose |
|--------|--------|-------------------|---------|
| Content-Security-Policy | 25% | High | Controls which resources the browser can load. Prevents XSS, data injection |
| Strict-Transport-Security | 20% | High | Forces HTTPS connections. Prevents protocol downgrade attacks |
| X-Frame-Options | 15% | Medium | Prevents clickjacking by controlling iframe embedding |
| X-Content-Type-Options | 15% | Medium | Prevents MIME type sniffing attacks |
| Referrer-Policy | 10% | Medium | Controls what referrer info is sent with requests |
| Permissions-Policy | 15% | Medium | Restricts browser features (camera, microphone, geolocation) |

## Scoring

Score = sum of present header weights, normalized to 0-100.

| Score Range | Grade | Interpretation |
|-------------|-------|---------------|
| 90-100 | A | Excellent: all critical headers present |
| 75-89 | B | Good: most headers present |
| 60-74 | C | Fair: some important headers missing |
| 40-59 | D | Poor: multiple security headers absent |
| 0-39 | F | Critical: minimal security headers |

## Example Output (JSON)

```json
{
  "url": "https://example.com",
  "score": 72,
  "grade": "C",
  "headers": {
    "Content-Security-Policy": {"present": false, "severity": "high"},
    "Strict-Transport-Security": {"present": true, "value": "max-age=31536000", "severity": "ok"},
    "X-Frame-Options": {"present": true, "value": "DENY", "severity": "ok"},
    "X-Content-Type-Options": {"present": true, "value": "nosniff", "severity": "ok"},
    "Referrer-Policy": {"present": false, "severity": "medium"},
    "Permissions-Policy": {"present": false, "severity": "medium"}
  },
  "recommendations": ["Add Content-Security-Policy header", "Add Referrer-Policy header"]
}
```

## Remediation Guidance

| Header | Recommended Value | Implementation |
|--------|-------------------|---------------|
| Content-Security-Policy | `default-src 'self'; script-src 'self'` | Web server config or meta tag |
| Strict-Transport-Security | `max-age=31536000; includeSubDomains` | Web server config |
| X-Frame-Options | `DENY` or `SAMEORIGIN` | Web server config |
| X-Content-Type-Options | `nosniff` | Web server config |
| Referrer-Policy | `strict-origin-when-cross-origin` | Web server config |
| Permissions-Policy | `camera=(), microphone=(), geolocation=()` | Web server config |

## Storing Results as Evidence

After running a scan, save results to the GRC database:

```bash
python3 scripts/db_query.py --action add-evidence \
  --title "Security Header Scan - example.com" \
  --type automated \
  --source check_headers.py \
  --filepath ~/.openclaw/grc/evidence/automated/2026-02-11-headers-example-com.json \
  --valid-from 2026-02-11 \
  --valid-until 2026-05-11 \
  --control-ids 17,18,24
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success: headers checked |
| 1 | Connection error (timeout, DNS, refused) |
| 2 | Invalid URL format |
