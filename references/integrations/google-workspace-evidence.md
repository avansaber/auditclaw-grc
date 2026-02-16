# Google Workspace Evidence Collection Guide

**Purpose:** Collect compliance evidence from Google Workspace (formerly G Suite) for SOC 2, ISO 27001, HIPAA, GDPR, NIST CSF, and other frameworks.

## Overview

Google Workspace evidence collection uses three approaches:
1. **Admin Console exports**: manual downloads from admin.google.com
2. **Google Admin SDK / Directory API**: programmatic via `gcloud` or API calls
3. **Google Workspace Admin Reports API**: audit logs and activity reports

**Prerequisites:**
- Google Workspace admin account (super admin for full access)
- `gcloud` CLI installed and authenticated: `gcloud auth login`
- Admin SDK API enabled in Google Cloud Console
- OAuth scope: `https://www.googleapis.com/auth/admin.directory.user.readonly`

## Evidence by Control Domain

### 1. Access Control and Identity

**Controls:** SOC 2 CC6.1–CC6.3, ISO 27001 A.9.x, NIST PR.AC-1, HIPAA §164.312(a), CIS 5.x/6.x

| Evidence | Collection Method | Refresh |
|----------|------------------|---------|
| All users list | Admin Console > Directory > Users > Download (CSV) | Monthly |
| Suspended/inactive users | Admin Console > Directory > Users > Filter: Suspended | Monthly |
| 2-Step Verification status | Admin Console > Security > 2-Step Verification > Enrollment | Monthly |
| 2SV enforcement policy | Admin Console > Security > Authentication > 2-Step Verification | Quarterly |
| User account activity | Admin Console > Reports > User Reports > Accounts | Monthly |
| Admin role assignments | Admin Console > Account > Admin roles | Monthly |
| Super admin list | Admin Console > Account > Admin roles > Super Admin | Monthly |
| Password policy | Admin Console > Security > Authentication > Password management | Quarterly |
| Session control settings | Admin Console > Security > Google session control | Quarterly |
| Login challenges | Admin Console > Reports > User Reports > Login audit log | Monthly |

**Key checks:**
- 2-Step Verification enforced for all users (not just recommended)
- Security keys required for super admins
- Super admin accounts limited to 2-3 people
- No suspended accounts with active sessions
- Password minimum length >= 12 characters
- Session duration limited (e.g., 12 hours for web, 30 days for mobile)
- Login challenges enabled for suspicious activity

**API collection:**
```bash
# List all users with 2SV status
# Requires: Admin SDK Directory API enabled
curl -s -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://admin.googleapis.com/admin/directory/v1/users?domain=example.com&maxResults=500&projection=full" \
  | jq '.users[] | {email: .primaryEmail, is2svEnrolled: .isEnrolledIn2Sv, is2svEnforced: .isEnforcedIn2Sv, suspended: .suspended, isAdmin: .isAdmin, lastLoginTime: .lastLoginTime}'
```

### 2. Data Protection and DLP

**Controls:** SOC 2 CC6.7, ISO 27001 A.8.2/A.10.x, NIST PR.DS-1/PR.DS-5, GDPR Art.32, HIPAA §164.312(e)

| Evidence | Collection Method | Refresh |
|----------|------------------|---------|
| DLP rules | Admin Console > Security > Data protection > Manage rules | Quarterly |
| DLP incidents | Admin Console > Security > Data protection > View incidents | Monthly |
| Drive sharing settings | Admin Console > Apps > Google Workspace > Drive > Sharing settings | Quarterly |
| External sharing restrictions | Admin Console > Apps > Google Workspace > Drive > Sharing settings > Sharing options | Quarterly |
| Link sharing defaults | Admin Console > Apps > Google Workspace > Drive > Sharing settings > Link sharing | Quarterly |
| Gmail confidential mode | Admin Console > Apps > Google Workspace > Gmail > Confidential mode | Quarterly |
| Client-side encryption | Admin Console > Security > Access and data control > Client-side encryption | Quarterly |
| Drive labels (classification) | Admin Console > Apps > Google Workspace > Drive > Labels | Quarterly |
| Vault retention rules | Admin Console > Apps > Google Vault > Retention > Custom rules | Quarterly |

**Key checks:**
- External sharing restricted or requires approval for sensitive files
- DLP rules active for PII, PHI, PCI data patterns
- Default link sharing set to "Restricted" (not "Anyone with the link")
- Google Vault retention policies configured for compliance requirements
- Client-side encryption enabled for sensitive data (if available on plan)

### 3. Email Security

**Controls:** SOC 2 CC6.6/CC6.8, ISO 27001 A.13.2.x, NIST PR.DS-2, CIS 9.x

| Evidence | Collection Method | Refresh |
|----------|------------------|---------|
| SPF record | `dig TXT example.com \| grep spf` | Quarterly |
| DKIM configuration | Admin Console > Apps > Google Workspace > Gmail > Authenticate email | Quarterly |
| DMARC record | `dig TXT _dmarc.example.com` | Quarterly |
| Advanced phishing protection | Admin Console > Security > Gmail > Safety > Phishing protection | Quarterly |
| Spoofing protection | Admin Console > Security > Gmail > Safety > Spoofing and authentication | Quarterly |
| Attachment security | Admin Console > Security > Gmail > Safety > Attachments | Quarterly |
| Email routing rules | Admin Console > Apps > Google Workspace > Gmail > Routing | Quarterly |
| Inbound gateway config | Admin Console > Apps > Google Workspace > Gmail > Spam, Phishing and Malware | Quarterly |

**Key checks:**
- SPF record exists and is strict (`-all` not `~all`)
- DKIM signing enabled for all domains
- DMARC policy set to `reject` or `quarantine`
- Enhanced phishing and spoofing protection enabled
- Suspicious attachment blocking enabled
- No overly permissive email routing rules

### 4. Audit Logging

**Controls:** SOC 2 CC7.2, ISO 27001 A.12.4.x, NIST DE.AE-3, HIPAA §164.312(b), CIS 8.x

| Evidence | Collection Method | Refresh |
|----------|------------------|---------|
| Admin audit log | Admin Console > Reports > Audit and investigation > Admin log events | Monthly |
| Login audit log | Admin Console > Reports > Audit and investigation > Login log events | Monthly |
| Drive audit log | Admin Console > Reports > Audit and investigation > Drive log events | Monthly |
| SAML audit log | Admin Console > Reports > Audit and investigation > SAML log events | Monthly |
| Token audit log | Admin Console > Reports > Audit and investigation > Token log events | Monthly |
| Alert Center alerts | Admin Console > Security > Alert center | Weekly |
| BigQuery log export | Admin Console > Reports > BigQuery Export (if configured) | Continuous |

**API collection:**
```bash
# Get admin activity for last 30 days
START=$(date -d '30 days ago' '+%Y-%m-%dT00:00:00.000Z' 2>/dev/null || date -v-30d '+%Y-%m-%dT00:00:00.000Z')
curl -s -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://admin.googleapis.com/admin/reports/v1/activity/users/all/applications/admin?startTime=$START&maxResults=500" \
  | jq '.items[] | {time: .id.time, actor: .actor.email, event: .events[0].name}'
```

**Key checks:**
- Audit logs exported to BigQuery or external SIEM for long-term retention
- Alert Center configured for security-critical events
- Login audit logs show no unauthorized admin access
- Drive audit shows no mass external sharing events

### 5. Third-Party App Access

**Controls:** SOC 2 CC6.1/CC9.2, ISO 27001 A.9.4/A.15.x, NIST PR.AC-4

| Evidence | Collection Method | Refresh |
|----------|------------------|---------|
| Third-party app access | Admin Console > Security > API controls > App access control | Monthly |
| OAuth app allowlist | Admin Console > Security > API controls > App access control > Manage third-party app access | Monthly |
| Connected apps | Admin Console > Security > API controls > App access control > Manage third-party app access > View list | Monthly |
| API scopes granted | Admin Console > Reports > Audit and investigation > Token log events | Monthly |
| Marketplace apps | Admin Console > Apps > Google Workspace Marketplace apps | Quarterly |

**Key checks:**
- Third-party app access is restricted (not "allow all")
- Only approved apps on the allowlist
- No high-risk OAuth scopes granted to untrusted apps
- Regular review of connected third-party applications
- Marketplace apps limited to admin-approved installs

### 6. Mobile Device Management

**Controls:** SOC 2 CC6.4/CC6.7, ISO 27001 A.6.2/A.11.2.x, NIST PR.AC-3, CIS 15.x

| Evidence | Collection Method | Refresh |
|----------|------------------|---------|
| Mobile management policy | Admin Console > Devices > Mobile and endpoints > Settings | Quarterly |
| Enrolled devices | Admin Console > Devices > Mobile and endpoints > Devices | Monthly |
| Device compliance | Admin Console > Devices > Mobile and endpoints > Devices (filter: non-compliant) | Monthly |
| Advanced mobile management | Admin Console > Devices > Mobile and endpoints > Settings > Universal | Quarterly |
| Wipe/lock history | Admin Console > Devices > Mobile and endpoints > Audit log | Monthly |

**Key checks:**
- Mobile management set to "Advanced" (not "Basic")
- Screen lock required on all managed devices
- Device encryption required
- Remote wipe capability enabled
- Compromised device blocking enabled
- Company-owned devices require approval before access

### 7. Endpoint Management (Chrome/Devices)

**Controls:** SOC 2 CC6.8, ISO 27001 A.12.6.x, NIST PR.IP-1, CIS 16.x

| Evidence | Collection Method | Refresh |
|----------|------------------|---------|
| Chrome browser policies | Admin Console > Devices > Chrome > Settings | Quarterly |
| Chrome browser extensions | Admin Console > Devices > Chrome > Apps & extensions | Monthly |
| Managed browsers | Admin Console > Devices > Chrome > Managed browsers | Monthly |
| Chrome OS update policy | Admin Console > Devices > Chrome > Settings > Device > Device update settings | Quarterly |
| Endpoint verification | Admin Console > Devices > Mobile and endpoints > Endpoint verification | Monthly |

### 8. Data Retention and eDiscovery

**Controls:** SOC 2 CC7.2, ISO 27001 A.18.1.3, NIST PR.IP-4, GDPR Art.5(1)(e), HIPAA §164.530(j)

| Evidence | Collection Method | Refresh |
|----------|------------------|---------|
| Vault retention rules | Admin Console > Apps > Google Vault > Retention | Quarterly |
| Vault matters (holds) | Admin Console > Apps > Google Vault > Matters | Monthly |
| Vault export history | Admin Console > Apps > Google Vault > Reports | Monthly |
| Data regions policy | Admin Console > Account > Data regions | Quarterly |
| Takeout settings | Admin Console > Account > Data Sharing > Google Takeout | Quarterly |

**Key checks:**
- Retention rules cover all required data types (email, Drive, Chat)
- Retention periods meet regulatory requirements (e.g., 7 years for financial, 6 years for HIPAA)
- Legal holds active for ongoing matters
- Data region restrictions set for sovereignty compliance
- Google Takeout disabled or restricted for departing employees

## Admin Console Export Guide

For evidence that requires manual export from the Admin Console:

1. **Navigate** to the relevant section (e.g., Security > 2-Step Verification)
2. **Screenshot** the configuration page (use browser's full-page screenshot)
3. **Export data** where CSV/JSON export is available (click the download icon)
4. **Save** to `~/.openclaw/grc/evidence/manual/google-workspace-<topic>-<date>.<ext>`
5. **Record** in the GRC database:
   ```bash
   python3 scripts/db_query.py --action add-evidence \
     --title "Google Workspace 2SV Enforcement" --type manual \
     --source google-admin-console \
     --filepath ~/.openclaw/grc/evidence/manual/google-workspace-2sv-2026-01-15.png \
     --control-ids 8,15,22 \
     --valid-from 2026-01-15 --valid-until 2026-04-15
   ```

## Suggested Refresh Schedule

| Frequency | Evidence Types |
|-----------|---------------|
| Weekly | Alert Center alerts, DLP incidents, suspicious login activity |
| Monthly | User lists, 2SV status, admin roles, device compliance, audit logs, connected apps |
| Quarterly | Security policies (password, sharing, DLP rules), email config (SPF/DKIM/DMARC), mobile mgmt settings, retention rules |

## Evidence Validity

Set `--valid-until` based on evidence type:
- **User/access snapshots** (user lists, admin roles): 30 days
- **Policy configurations** (security settings, DLP rules): 90 days
- **Audit log exports**: 90 days
- **Email authentication records** (SPF, DKIM, DMARC): 90 days
- **Device compliance snapshots**: 30 days
