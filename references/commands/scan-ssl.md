# SSL/TLS Certificate Scan

Checks SSL/TLS certificate validity, expiry, protocol version, and cipher strength.

## Usage

```bash
python3 scripts/check_ssl.py --domain <domain> [--port 443] [--format json|text]
```

## What's Checked

| Check | Description |
|-------|-------------|
| Certificate validity | Is the cert currently valid (not expired, not before start date)? |
| Expiry countdown | Days until certificate expires |
| Certificate chain | Is the full chain valid and trusted? |
| Protocol version | TLS 1.0/1.1/1.2/1.3 |
| Cipher suite | Encryption algorithm in use |
| Subject/SAN | Does the cert match the domain? |
| Issuer | Who issued the certificate? |

## Grading Scale

| Grade | Criteria |
|-------|----------|
| A | Valid cert, TLS 1.2+ (1.3 preferred), 60+ days until expiry |
| B | Valid cert, TLS 1.2, 30-60 days until expiry |
| C | Valid cert, older TLS or 14-30 days until expiry |
| D | Valid cert but expiring within 7 days |
| F | Expired certificate or verification failure |

## Warning Thresholds

| Days Until Expiry | Alert Level | Action |
|-------------------|-------------|--------|
| > 30 days | None | Routine monitoring |
| 14-30 days | Warning | Schedule renewal |
| 7-14 days | High | Renew immediately |
| 0-7 days | Critical/URGENT | Emergency renewal |
| Expired | Critical | Certificate has expired |

## Example Output (JSON)

```json
{
  "domain": "example.com",
  "valid": true,
  "issuer": "Let's Encrypt Authority X3",
  "subject": "example.com",
  "san": ["example.com", "www.example.com"],
  "not_before": "2025-12-01",
  "not_after": "2026-03-01",
  "days_until_expiry": 18,
  "protocol": "TLSv1.3",
  "cipher": "TLS_AES_256_GCM_SHA384",
  "chain_valid": true,
  "grade": "A",
  "warnings": ["Certificate expires in 18 days"]
}
```

## Storing Results as Evidence

```bash
python3 scripts/db_query.py --action add-evidence \
  --title "SSL Certificate Scan - example.com" \
  --type automated \
  --source check_ssl.py \
  --filepath ~/.openclaw/grc/evidence/automated/2026-02-11-ssl-example-com.json \
  --valid-from 2026-02-11 \
  --valid-until 2026-05-11 \
  --control-ids 24,25
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success: certificate checked |
| 1 | Connection error (timeout, DNS, refused) |
| 2 | Certificate error (expired, untrusted) |
