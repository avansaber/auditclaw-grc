# Database Actions Reference

All database operations go through `scripts/db_query.py`.

## Usage

```bash
python3 scripts/db_query.py --action <action> [options]
```

All output is JSON to stdout. Errors exit with code 1 and print to stderr.

## Global Options

| Flag | Description |
|------|-------------|
| `--action` | **(required)** The action to perform |
| `--db-path` | Custom database path (default: `~/.openclaw/grc/compliance.sqlite`) |

---

## Actions

### status
Returns database overview: framework count, total controls, controls by status, evidence count, risk count, vendor count.

```bash
python3 scripts/db_query.py --action status
```

**Output:** `{ "status": "ok", "frameworks": N, "controls": {...}, "evidence": N, "risks": N, "vendors": N }`

---

### activate-framework
Loads a framework from a JSON file, populates controls and cross-framework mappings.

```bash
python3 scripts/db_query.py --action activate-framework --slug soc2 --framework-file assets/frameworks/soc2.json
```

| Flag | Required | Description |
|------|----------|-------------|
| `--slug` | Yes | Framework identifier (e.g., `soc2`) |
| `--framework-file` | Yes | Path to framework JSON file |

**Output:** `{ "status": "ok", "framework": "soc2", "controls_loaded": 42, "mappings_loaded": N }`

---

### deactivate-framework
Marks a framework as inactive (soft delete).

```bash
python3 scripts/db_query.py --action deactivate-framework --slug soc2 --reason "Switching to ISO 27001"
```

| Flag | Required | Description |
|------|----------|-------------|
| `--slug` | Yes | Framework slug |
| `--reason` | No | Deactivation reason |

---

### list-controls
Lists controls with optional filters. V3 adds effectiveness and maturity filtering.

```bash
python3 scripts/db_query.py --action list-controls
python3 scripts/db_query.py --action list-controls --framework soc2 --status not_started
python3 scripts/db_query.py --action list-controls --overdue
python3 scripts/db_query.py --action list-controls --overdue-reviews
python3 scripts/db_query.py --action list-controls --min-effectiveness 80 --maturity-level managed
```

| Flag | Required | Description |
|------|----------|-------------|
| `--framework` | No | Filter by framework slug |
| `--status` | No | Filter by status (`not_started`, `in_progress`, `complete`, `not_applicable`) |
| `--overdue` | No | Show only controls past due date |
| `--overdue-reviews` | No | Show only controls with overdue reviews |
| `--min-effectiveness` | No | Filter by minimum effectiveness score (int, 0-100) (V3) |
| `--maturity-level` | No | Filter by maturity level (`initial`, `developing`, `defined`, `managed`, `optimizing`) (V3) |

---

### add-control
Creates a new control manually (outside framework activation).

```bash
python3 scripts/db_query.py --action add-control \
  --title "Custom backup verification" \
  --description "Verify backups weekly" \
  --category "Operations" \
  --priority 4 \
  --framework soc2
```

| Flag | Required | Description |
|------|----------|-------------|
| `--title` | Yes | Control title |
| `--description` | No | Control description |
| `--category` | No | Category label |
| `--priority` | No | Priority 1-5 (5=critical) |
| `--framework` | No | Framework to associate with |

---

### update-control
Updates one or more controls. Supports batch updates via comma-separated IDs.

```bash
python3 scripts/db_query.py --action update-control --id 5 --status in_progress --assignee "Alice"
python3 scripts/db_query.py --action update-control --id 1,2,3 --status complete
python3 scripts/db_query.py --action update-control --control-id CC1.1 --status complete --review-date 2026-06-01
```

| Flag | Required | Description |
|------|----------|-------------|
| `--id` | Yes* | Record ID(s), comma-separated for batch |
| `--control-id` | Yes* | Control code (e.g., CC1.1), alternative to --id |
| `--status` | No | New status |
| `--assignee` | No | Assignee name |
| `--due-date` | No | Due date (ISO format) |
| `--review-date` | No | Next review date |
| `--implementation-notes` | No | Notes text |
| `--priority` | No | New priority |

*One of `--id` or `--control-id` required.

---

### add-evidence
Adds an evidence record and optionally links it to controls.

```bash
python3 scripts/db_query.py --action add-evidence \
  --title "AWS MFA screenshot" \
  --filename "mfa-config.png" \
  --filepath "/evidence/2026/mfa-config.png" \
  --type manual \
  --source aws \
  --valid-from 2026-01-01 \
  --valid-until 2026-07-01 \
  --control-ids 5,6,7
```

| Flag | Required | Description |
|------|----------|-------------|
| `--title` | Yes | Evidence title |
| `--filename` | No | Original filename |
| `--filepath` | No | Storage path |
| `--type` | No | `manual`, `automated`, `integration` |
| `--source` | No | `aws`, `github`, `manual`, etc. |
| `--valid-from` | No | Validity start date |
| `--valid-until` | No | Validity end date |
| `--control-ids` | No | Comma-separated control IDs to link |

---

### update-evidence
Updates evidence record fields.

```bash
python3 scripts/db_query.py --action update-evidence --id 3 --status approved --valid-until 2026-12-31
```

| Flag | Required | Description |
|------|----------|-------------|
| `--id` | Yes | Evidence ID |
| `--status` | No | New status (`pending`, `approved`, `rejected`, `expired`) |
| `--valid-from` | No | New validity start |
| `--valid-until` | No | New validity end |

---

### list-evidence
Lists evidence with optional filters.

```bash
python3 scripts/db_query.py --action list-evidence
python3 scripts/db_query.py --action list-evidence --status approved
python3 scripts/db_query.py --action list-evidence --expiring-within 30
```

| Flag | Required | Description |
|------|----------|-------------|
| `--status` | No | Filter by status |
| `--expiring-within` | No | Show evidence expiring within N days |

---

### add-risk
Adds a risk to the register with optional linked controls.

```bash
python3 scripts/db_query.py --action add-risk \
  --title "API key exposure" \
  --description "API keys stored in plaintext" \
  --likelihood 4 \
  --impact 5 \
  --treatment mitigate \
  --treatment-plan "Rotate keys, implement vault" \
  --owner "Security Team" \
  --linked-controls "[5, 6]"
```

| Flag | Required | Description |
|------|----------|-------------|
| `--title` | Yes | Risk title |
| `--description` | No | Risk description |
| `--likelihood` | No | 1-5 scale |
| `--impact` | No | 1-5 scale |
| `--treatment` | No | `avoid`, `mitigate`, `transfer`, `accept` |
| `--treatment-plan` | No | Treatment plan details |
| `--owner` | No | Responsible person/team |
| `--linked-controls` | No | JSON array of control IDs |

---

### list-risks
Lists risks with optional filters.

```bash
python3 scripts/db_query.py --action list-risks
python3 scripts/db_query.py --action list-risks --status open --min-score 15
```

| Flag | Required | Description |
|------|----------|-------------|
| `--status` | No | Filter by status |
| `--min-score` | No | Minimum risk score (likelihood × impact) |

---

### add-vendor
Adds a vendor to the register.

```bash
python3 scripts/db_query.py --action add-vendor \
  --name "AWS" \
  --criticality high \
  --contact-name "Account Manager" \
  --contact-email "vendor-contact@company.example"
```

| Flag | Required | Description |
|------|----------|-------------|
| `--name` | Yes | Vendor name |
| `--criticality` | No | `low`, `medium`, `high`, `critical` |
| `--contact-name` | No | Primary contact |
| `--contact-email` | No | Contact email |

---

### list-vendors
Lists vendors with optional status filter.

```bash
python3 scripts/db_query.py --action list-vendors
python3 scripts/db_query.py --action list-vendors --status active
```

---

### add-incident
Creates a security incident.

```bash
python3 scripts/db_query.py --action add-incident \
  --title "Unauthorized access attempt" \
  --description "Failed login attempts from unknown IP" \
  --severity high
```

| Flag | Required | Description |
|------|----------|-------------|
| `--title` | Yes | Incident title |
| `--description` | No | Details |
| `--severity` | No | `low`, `medium`, `high`, `critical` |

---

### update-incident
Updates incident status, root cause, and cost/notification details (V3 enhancements).

```bash
python3 scripts/db_query.py --action update-incident --id 1 --status resolved --root-cause "Brute force from compromised IP"
python3 scripts/db_query.py --action update-incident --id 1 --estimated-cost 50000 --actual-cost 32000 --regulatory-notification --notification-details "Notified CISA within 72h" --preventive-measures "Implement IP allowlisting"
```

| Flag | Required | Description |
|------|----------|-------------|
| `--id` | Yes | Incident ID |
| `--status` | No | `open`, `investigating`, `resolved`, `closed` |
| `--root-cause` | No | Root cause text |
| `--estimated-cost` | No | Estimated financial cost of the incident (V3) |
| `--actual-cost` | No | Actual financial cost of the incident (V3) |
| `--regulatory-notification` | No | Boolean flag indicating regulatory notification was required (V3) |
| `--notification-details` | No | Details about regulatory/stakeholder notifications sent (V3) |
| `--preventive-measures` | No | Preventive measures to avoid recurrence (V3) |

---

### list-incidents
Lists incidents with optional filters.

```bash
python3 scripts/db_query.py --action list-incidents
python3 scripts/db_query.py --action list-incidents --status open --severity critical
```

---

### add-policy
Creates a compliance policy.

```bash
python3 scripts/db_query.py --action add-policy \
  --title "Access Control Policy" \
  --description "Governs logical access to systems" \
  --content-path "/policies/access-control-v2.md" \
  --control-ids 17,18,19
```

| Flag | Required | Description |
|------|----------|-------------|
| `--title` | Yes | Policy title |
| `--description` | No | Policy description |
| `--content-path` | No | Path to policy content file |
| `--control-ids` | No | Comma-separated control IDs to link |

---

### score-history
Returns compliance score history for a framework.

```bash
python3 scripts/db_query.py --action score-history --framework soc2
python3 scripts/db_query.py --action score-history --framework soc2 --days 30
```

| Flag | Required | Description |
|------|----------|-------------|
| `--framework` | No | Framework slug (omit for all) |
| `--days` | No | Limit to last N days |

---

### list-mappings
Lists cross-framework control mappings.

```bash
python3 scripts/db_query.py --action list-mappings --source-framework soc2 --target-framework iso27001
```

| Flag | Required | Description |
|------|----------|-------------|
| `--source-framework` | No | Source framework slug |
| `--target-framework` | No | Target framework slug |

---

### gap-analysis
Generates a gap analysis with remediation priorities.

```bash
python3 scripts/db_query.py --action gap-analysis --framework soc2
```

| Flag | Required | Description |
|------|----------|-------------|
| `--framework` | No | Framework slug (omit for all) |

**Output includes:** Priority-scored gaps, effort estimates, remediation phases, overall gap percentage.

---

### export-evidence
Exports an evidence package (ZIP) for auditors containing manifest, summary, and control mapping.

```bash
python3 scripts/db_query.py --action export-evidence --framework soc2 --output-dir /tmp/exports
```

| Flag | Required | Description |
|------|----------|-------------|
| `--framework` | Yes | Framework slug |
| `--output-dir` | Yes | Directory to write ZIP file |

**Output includes:** ZIP path, evidence record count, files included, total size.

**ZIP contents:**
- `manifest.json`: Framework metadata and evidence inventory
- `summary.md`: Human-readable compliance summary
- `control-mapping.csv`: Control-to-evidence mapping table
- `evidence/`: Actual evidence files (if stored on disk)

---

### generate-report
Generates an HTML compliance report with scores, controls, evidence, and risks.

```bash
python3 scripts/db_query.py --action generate-report --framework soc2 --output-dir /tmp/reports
```

| Flag | Required | Description |
|------|----------|-------------|
| `--framework` | Yes | Framework slug |
| `--output-dir` | No | Output directory (default: ~/.openclaw/grc/reports/) |

**Output includes:** Report file path, format, score, control count.

**Report sections:**
- Compliance score with visual indicator (Excellent/Good/Fair/Needs Attention/Critical)
- Summary cards (total controls, complete, in progress, not started, evidence, risks)
- Controls table with ID, title, category, priority, status, assignee
- Evidence table with title, type, status, validity
- Risks table with title, score, treatment, status

---

### Asset Management (3 actions)

#### 23. `add-asset`

Registers a new asset in the asset inventory.

```
--action add-asset --name <name> [--type <type>] [--criticality <level>]
         [--owner <name>] [--description <text>] [--status <status>]
         [--ip-address <ip>] [--hostname <host>] [--os-type <os>]
         [--software-version <ver>] [--lifecycle-stage <stage>]
         [--data-classification <class>] [--discovery-source <source>]
         [--encryption-status <text>] [--backup-status <text>]
         [--patch-status <text>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--name` | Yes | Name of the asset |
| `--type` | No | Asset type: `cloud`, `hardware`, `software`, `network`, `data` |
| `--criticality` | No | Criticality level: `low`, `medium`, `high`, `critical` |
| `--owner` | No | Owner or responsible party |
| `--description` | No | Free-text description |
| `--status` | No | Asset status: `active`, `decommissioned`, `retired` |
| `--ip-address` | No | IP address of the asset |
| `--hostname` | No | Hostname of the asset |
| `--os-type` | No | Operating system type |
| `--software-version` | No | Software or firmware version |
| `--lifecycle-stage` | No | Lifecycle stage: `in_use`, `in_development`, `retired`, `decommissioned` |
| `--data-classification` | No | Data classification: `public`, `internal`, `confidential`, `restricted` |
| `--discovery-source` | No | How asset was discovered: `manual`, `scan`, `inventory` |
| `--encryption-status` | No | Encryption status description |
| `--backup-status` | No | Backup status description |
| `--patch-status` | No | Patch status description |

**Output:**
```json
{
  "status": "created",
  "id": 1,
  "name": "Web Server Prod-01",
  "criticality": "high"
}
```

---

#### 24. `list-assets`

Lists assets with optional filters.

```
--action list-assets [--type <type>] [--criticality <level>] [--status <status>]
         [--lifecycle-stage <stage>] [--data-classification <class>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--type` | No | Filter by asset type: `cloud`, `hardware`, `software`, `network`, `data` |
| `--criticality` | No | Filter by criticality: `low`, `medium`, `high`, `critical` |
| `--status` | No | Filter by status: `active`, `decommissioned`, `retired` |
| `--lifecycle-stage` | No | Filter by lifecycle: `in_use`, `in_development`, `retired`, `decommissioned` |
| `--data-classification` | No | Filter by classification: `public`, `internal`, `confidential`, `restricted` |

**Output:**
```json
{
  "status": "ok",
  "assets": [
    {
      "id": 1,
      "name": "Web Server Prod-01",
      "type": "cloud",
      "criticality": "high",
      "owner": "DevOps",
      "status": "active",
      "lifecycle_stage": "in_use",
      "data_classification": "confidential"
    }
  ],
  "count": 1
}
```

---

#### 25. `update-asset`

Updates an existing asset by database ID.

```
--action update-asset --id <db_id> [--name <name>] [--type <type>]
         [--criticality <level>] [--owner <name>] [--status <status>]
         [--ip-address <ip>] [--hostname <host>] [--os-type <os>]
         [--software-version <ver>] [--lifecycle-stage <stage>]
         [--data-classification <class>] [--encryption-status <text>]
         [--backup-status <text>] [--patch-status <text>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--id` | Yes | Database ID of the asset to update |
| `--name` | No | Updated name |
| `--type` | No | Updated type: `cloud`, `hardware`, `software`, `network`, `data` |
| `--criticality` | No | Updated criticality: `low`, `medium`, `high`, `critical` |
| `--owner` | No | Updated owner |
| `--status` | No | Updated status: `active`, `decommissioned`, `retired` |
| `--ip-address` | No | Updated IP address |
| `--hostname` | No | Updated hostname |
| `--os-type` | No | Updated OS type |
| `--software-version` | No | Updated software version |
| `--lifecycle-stage` | No | Updated lifecycle: `in_use`, `in_development`, `retired`, `decommissioned` |
| `--data-classification` | No | Updated classification: `public`, `internal`, `confidential`, `restricted` |
| `--encryption-status` | No | Updated encryption status |
| `--backup-status` | No | Updated backup status |
| `--patch-status` | No | Updated patch status |

**Output:**
```json
{
  "status": "updated",
  "id": 1
}
```

**Note:** Asset-to-control linkage (via the `asset_controls` junction table) is handled either
at creation time through `add-asset` or through direct SQL via the agent.

---

### Training Management (5 actions)

#### 26. `add-training-module`

Creates a new training module definition.

```
--action add-training-module --title <title> [--category <category>]
         [--description <text>] [--duration <minutes>]
         [--content-type <type>] [--content-url <url>]
         [--difficulty-level <level>] [--requires-recertification <0|1>]
         [--recertification-days <days>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--title` | Yes | Title of the training module |
| `--category` | No | Category: `security_awareness`, `privacy`, `compliance`, `technical`, `incident_response` |
| `--description` | No | Description of the module content |
| `--duration` | No | Duration in minutes |
| `--content-type` | No | Content type (e.g., video, document, interactive) |
| `--content-url` | No | URL to the training content |
| `--difficulty-level` | No | Difficulty: `beginner`, `intermediate`, `advanced` |
| `--requires-recertification` | No | Whether recertification is required: `0` or `1` |
| `--recertification-days` | No | Number of days before recertification is needed |

**Output:**
```json
{
  "status": "created",
  "id": 1,
  "title": "Security Awareness Training"
}
```

---

#### 27. `list-training-modules`

Lists training modules with optional filters.

```
--action list-training-modules [--category <category>] [--status <status>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--category` | No | Filter by category: `security_awareness`, `privacy`, `compliance`, `technical`, `incident_response` |
| `--status` | No | Filter by module status |

**Output:**
```json
{
  "status": "ok",
  "modules": [
    {
      "id": 1,
      "title": "Security Awareness Training",
      "category": "security_awareness",
      "duration": 60,
      "difficulty_level": "beginner",
      "requires_recertification": 1,
      "recertification_days": 365
    }
  ],
  "count": 1
}
```

---

#### 28. `add-training-assignment`

Assigns a training module to a person.

```
--action add-training-assignment --module-id <id> --assignee <name>
         [--due-date <YYYY-MM-DD>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--module-id` | Yes | Database ID of the training module |
| `--assignee` | Yes | Name or identifier of the person being assigned |
| `--due-date` | No | Due date in `YYYY-MM-DD` format |

**Output:**
```json
{
  "status": "created",
  "id": 1,
  "module_id": 1,
  "assignee": "John Smith"
}
```

---

#### 29. `list-training-assignments`

Lists training assignments with optional filters.

```
--action list-training-assignments [--assignee <name>] [--module-id <id>]
         [--status <status>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--assignee` | No | Filter by assignee name |
| `--module-id` | No | Filter by training module ID |
| `--status` | No | Filter by status: `assigned`, `in_progress`, `completed`, `overdue` |

**Output:**
```json
{
  "status": "ok",
  "assignments": [
    {
      "id": 1,
      "module_id": 1,
      "module_title": "Security Awareness Training",
      "assignee": "John Smith",
      "status": "assigned",
      "due_date": "2026-06-01",
      "score": null,
      "completed_at": null
    }
  ],
  "count": 1
}
```

---

#### 30. `update-training-assignment`

Updates a training assignment (e.g., mark as completed with a score).

```
--action update-training-assignment --id <db_id> [--status <status>]
         [--score <0-100>] [--completed-at <YYYY-MM-DD>]
         [--certificate-path <path>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--id` | Yes | Database ID of the assignment to update |
| `--status` | No | Updated status: `assigned`, `in_progress`, `completed`, `overdue` |
| `--score` | No | Score achieved (0-100) |
| `--completed-at` | No | Completion date in `YYYY-MM-DD` format |
| `--certificate-path` | No | Path to certificate file |

**Output:**
```json
{
  "status": "updated",
  "id": 1
}
```

---

### Vulnerability Management (3 actions)

#### 31. `add-vulnerability`

Logs a new vulnerability finding.

```
--action add-vulnerability --title <title> [--severity <level>]
         [--cvss-score <score>] [--cvss-vector <vector>] [--cve-id <cve>]
         [--description <text>] [--source <source>]
         [--affected-assets <text>] [--affected-packages <text>]
         [--remediation-steps <text>] [--fix-version <ver>]
         [--due-date <YYYY-MM-DD>] [--assignee <name>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--title` | Yes | Title or summary of the vulnerability |
| `--severity` | No | Severity level: `low`, `medium`, `high`, `critical` |
| `--cvss-score` | No | CVSS numeric score (0.0-10.0) |
| `--cvss-vector` | No | CVSS vector string |
| `--cve-id` | No | CVE identifier (e.g., CVE-2026-12345) |
| `--description` | No | Detailed description of the vulnerability |
| `--source` | No | Discovery source (e.g., scan tool name, manual review) |
| `--affected-assets` | No | Assets affected by this vulnerability |
| `--affected-packages` | No | Software packages affected |
| `--remediation-steps` | No | Steps to remediate the vulnerability |
| `--fix-version` | No | Version that fixes the vulnerability |
| `--due-date` | No | Remediation due date in `YYYY-MM-DD` format |
| `--assignee` | No | Person assigned to remediate |

**Output:**
```json
{
  "status": "created",
  "id": 1,
  "title": "SQL Injection in Login Form",
  "severity": "critical",
  "cvss_score": 9.8
}
```

---

#### 32. `list-vulnerabilities`

Lists vulnerabilities with optional filters.

```
--action list-vulnerabilities [--severity <level>] [--status <status>]
         [--min-cvss <score>] [--assignee <name>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--severity` | No | Filter by severity: `low`, `medium`, `high`, `critical` |
| `--status` | No | Filter by status: `open`, `in_progress`, `resolved`, `risk_accepted` |
| `--min-cvss` | No | Minimum CVSS score filter (e.g., 7.0) |
| `--assignee` | No | Filter by assigned person |

**Output:**
```json
{
  "status": "ok",
  "vulnerabilities": [
    {
      "id": 1,
      "title": "SQL Injection in Login Form",
      "severity": "critical",
      "cvss_score": 9.8,
      "cve_id": "CVE-2026-12345",
      "status": "open",
      "assignee": "Security Team",
      "due_date": "2026-03-01"
    }
  ],
  "count": 1
}
```

---

#### 33. `update-vulnerability`

Updates an existing vulnerability record.

```
--action update-vulnerability --id <db_id> [--status <status>]
         [--assignee <name>] [--severity <level>]
         [--resolved-at <YYYY-MM-DD>] [--resolved-by <name>]
         [--risk-accepted <0|1>] [--risk-acceptance-reason <text>]
         [--fix-version <ver>] [--remediation-steps <text>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--id` | Yes | Database ID of the vulnerability to update |
| `--status` | No | Updated status: `open`, `in_progress`, `resolved`, `risk_accepted` |
| `--assignee` | No | Updated assignee |
| `--severity` | No | Updated severity: `low`, `medium`, `high`, `critical` |
| `--resolved-at` | No | Resolution date in `YYYY-MM-DD` format |
| `--resolved-by` | No | Person who resolved the vulnerability |
| `--risk-accepted` | No | Whether risk is accepted: `0` or `1` |
| `--risk-acceptance-reason` | No | Reason for accepting the risk |
| `--fix-version` | No | Version that contains the fix |
| `--remediation-steps` | No | Updated remediation steps |

**Output:**
```json
{
  "status": "updated",
  "id": 1
}
```

---

### Access Review Campaigns (6 actions)

#### 34. `add-access-review`

Creates a new access review campaign.

```
--action add-access-review --title <title> [--description <text>]
         [--scope-type <type>] [--scope-config <json>]
         [--reviewer <name>] [--due-date <YYYY-MM-DD>]
         [--start-date <YYYY-MM-DD>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--title` | Yes | Title of the access review campaign |
| `--description` | No | Description of the review scope and purpose |
| `--scope-type` | No | Type of scope for the review |
| `--scope-config` | No | JSON configuration for the review scope |
| `--reviewer` | No | Primary reviewer for the campaign |
| `--due-date` | No | Campaign due date in `YYYY-MM-DD` format |
| `--start-date` | No | Campaign start date in `YYYY-MM-DD` format |

**Output:**
```json
{
  "status": "created",
  "id": 1,
  "title": "Q1 2026 Access Review"
}
```

---

#### 35. `list-access-reviews`

Lists access review campaigns with optional filters.

```
--action list-access-reviews [--status <status>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--status` | No | Filter by status: `draft`, `in_progress`, `completed`, `cancelled` |

**Output:**
```json
{
  "status": "ok",
  "campaigns": [
    {
      "id": 1,
      "title": "Q1 2026 Access Review",
      "status": "in_progress",
      "reviewer": "Security Admin",
      "due_date": "2026-03-31",
      "start_date": "2026-01-15",
      "item_count": 25
    }
  ],
  "count": 1
}
```

---

#### 36. `update-access-review`

Updates an access review campaign.

```
--action update-access-review --id <db_id> [--status <status>]
         [--title <title>] [--reviewer <name>] [--due-date <YYYY-MM-DD>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--id` | Yes | Database ID of the campaign to update |
| `--status` | No | Updated status: `draft`, `in_progress`, `completed`, `cancelled` |
| `--title` | No | Updated title |
| `--reviewer` | No | Updated reviewer |
| `--due-date` | No | Updated due date in `YYYY-MM-DD` format |

**Output:**
```json
{
  "status": "updated",
  "id": 1
}
```

---

#### 37. `add-review-item`

Adds an individual access review item to a campaign.

```
--action add-review-item --campaign-id <id> --user-name <name>
         --resource <resource> [--current-access <level>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--campaign-id` | Yes | Database ID of the parent access review campaign |
| `--user-name` | Yes | Name of the user whose access is being reviewed |
| `--resource` | Yes | Resource or system the user has access to |
| `--current-access` | No | Current access level description |

**Output:**
```json
{
  "status": "created",
  "id": 1,
  "campaign_id": 1
}
```

---

#### 38. `list-review-items`

Lists review items for a specific campaign.

```
--action list-review-items --campaign-id <id> [--decision <decision>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--campaign-id` | Yes | Database ID of the access review campaign |
| `--decision` | No | Filter by decision: `pending`, `approved`, `revoked`, `flagged` |

**Output:**
```json
{
  "status": "ok",
  "items": [
    {
      "id": 1,
      "campaign_id": 1,
      "user_name": "jsmith",
      "resource": "Production Database",
      "current_access": "read-write",
      "decision": "pending",
      "reviewer": null,
      "notes": null,
      "reviewed_at": null
    }
  ],
  "count": 1
}
```

---

#### 39. `update-review-item`

Records a review decision on an access review item.

```
--action update-review-item --id <db_id> [--decision <decision>]
         [--reviewer <name>] [--notes <text>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--id` | Yes | Database ID of the review item |
| `--decision` | No | Review decision: `approved`, `revoked`, `flagged` |
| `--reviewer` | No | Name of the person recording the decision |
| `--notes` | No | Notes or justification for the decision |

**Output:**
```json
{
  "status": "updated",
  "id": 1,
  "decision": "approved"
}
```

---

### Questionnaire Management (6 actions)

#### 40. `add-questionnaire-template`

Creates a new questionnaire template with its questions.

```
--action add-questionnaire-template --title <title>
         --questions <json_array> [--description <text>] [--category <cat>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--title` | Yes | Title of the questionnaire template |
| `--questions` | Yes | JSON array of questions: `[{"id":"q1","text":"Do you encrypt data at rest?"},{"id":"q2","text":"..."}]` |
| `--description` | No | Description of the questionnaire purpose |
| `--category` | No | Category for the template |

**Output:**
```json
{
  "status": "created",
  "id": 1,
  "title": "Vendor Security Assessment",
  "question_count": 5
}
```

**Example:**
```bash
python3 scripts/db_query.py --db-path /tmp/grc.db \
  --action add-questionnaire-template \
  --title "Vendor Security Assessment" \
  --category "vendor_assessment" \
  --questions '[{"id":"q1","text":"Do you encrypt data at rest?"},{"id":"q2","text":"Do you have a SOC 2 report?"},{"id":"q3","text":"Describe your incident response process."}]'
```

---

#### 41. `list-questionnaire-templates`

Lists questionnaire templates with optional filters.

```
--action list-questionnaire-templates [--status <status>] [--category <cat>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--status` | No | Filter by template status |
| `--category` | No | Filter by category |

**Output:**
```json
{
  "status": "ok",
  "templates": [
    {
      "id": 1,
      "title": "Vendor Security Assessment",
      "category": "vendor_assessment",
      "question_count": 5,
      "status": "active",
      "created_at": "2026-02-11T10:30:00Z"
    }
  ],
  "count": 1
}
```

---

#### 42. `add-questionnaire-response`

Creates a new response instance for a questionnaire template. This represents one
respondent's in-progress or completed questionnaire.

```
--action add-questionnaire-response --template-id <id> --respondent <name>
         [--vendor-id <id>] [--due-date <YYYY-MM-DD>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--template-id` | Yes | Database ID of the questionnaire template |
| `--respondent` | Yes | Name or email of the respondent |
| `--vendor-id` | No | Database ID of the vendor (if vendor questionnaire) |
| `--due-date` | No | Response due date in `YYYY-MM-DD` format |

**Output:**
```json
{
  "status": "created",
  "id": 1,
  "template_id": 1,
  "total_questions": 5
}
```

---

#### 43. `list-questionnaire-responses`

Lists questionnaire responses with optional filters.

```
--action list-questionnaire-responses [--template-id <id>] [--vendor-id <id>]
         [--status <status>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--template-id` | No | Filter by template ID |
| `--vendor-id` | No | Filter by vendor ID |
| `--status` | No | Filter by response status |

**Output:**
```json
{
  "status": "ok",
  "responses": [
    {
      "id": 1,
      "template_id": 1,
      "template_title": "Vendor Security Assessment",
      "respondent": "vendor@company.example",
      "vendor_id": 3,
      "status": "in_progress",
      "answered_count": 3,
      "total_questions": 5,
      "due_date": "2026-03-15",
      "score": null
    }
  ],
  "count": 1
}
```

---

#### 44. `add-questionnaire-answer`

Records an answer to a specific question within a questionnaire response.
When all questions for a response have been answered, the response status is
automatically updated to `completed`.

```
--action add-questionnaire-answer --response-id <id> --question-index <index>
         --answer-text <text> [--notes <text>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--response-id` | Yes | Database ID of the questionnaire response |
| `--question-index` | Yes | Index of the question being answered (0-based or matching question ID) |
| `--answer-text` | Yes | The answer text |
| `--notes` | No | Additional notes or context for the answer |

**Output:**
```json
{
  "status": "created",
  "id": 1
}
```

**Note:** When the last unanswered question for a response is answered, the response
status is automatically set to `completed`.

---

#### 45. `update-questionnaire-response`

Updates a questionnaire response record (e.g., scoring, status changes, reviewer assignment).

```
--action update-questionnaire-response --id <db_id> [--status <status>]
         [--score <score>] [--reviewed-by <name>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--id` | Yes | Database ID of the questionnaire response to update |
| `--status` | No | Updated status |
| `--score` | No | Numeric score for the completed questionnaire |
| `--reviewed-by` | No | Name of the person who reviewed the response |

**Output:**
```json
{
  "status": "updated",
  "id": 1
}
```

---

### Incident Actions & Reviews (6 actions)

#### 46. `add-incident-action`

Records an action taken during incident response (containment, investigation, recovery, notification, etc.).

```
--action add-incident-action --incident-id <id> --action-type <type>
         --description <text> --performed-by <name>
         [--notes <text>] [--duration-minutes <minutes>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--incident-id` | Yes | Database ID of the parent incident |
| `--action-type` | Yes | Action type: `containment`, `investigation`, `eradication`, `recovery`, `notification`, `other` |
| `--description` | Yes | Description of the action taken |
| `--performed-by` | Yes | Person who performed the action |
| `--notes` | No | Additional notes or context |
| `--duration-minutes` | No | Duration of the action in minutes (integer) |

**Output:**
```json
{
  "status": "created",
  "id": 1,
  "incident_id": 5,
  "action_type": "containment",
  "performed_by": "Security Team"
}
```

---

#### 47. `list-incident-actions`

Lists actions for a specific incident, optionally filtered by type.

```
--action list-incident-actions --incident-id <id> [--action-type <type>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--incident-id` | Yes | Database ID of the incident |
| `--action-type` | No | Filter by action type: `containment`, `investigation`, `eradication`, `recovery`, `notification`, `other` |

**Output:**
```json
{
  "status": "ok",
  "count": 3,
  "actions": [
    {
      "id": 1,
      "incident_id": 5,
      "action_type": "containment",
      "description": "Blocked IP range at firewall",
      "performed_by": "Security Team",
      "notes": null,
      "duration_minutes": 15
    }
  ]
}
```

---

#### 48. `add-incident-review`

Creates a post-incident review record.

```
--action add-incident-review --incident-id <id> --review-type <type>
         --title <title> [--reviewer <name>] [--due-date <YYYY-MM-DD>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--incident-id` | Yes | Database ID of the parent incident |
| `--review-type` | Yes | Review type: `post_mortem`, `lessons_learned`, `root_cause`, `management_review` |
| `--title` | Yes | Title of the review |
| `--reviewer` | No | Person responsible for the review |
| `--due-date` | No | Review due date in `YYYY-MM-DD` format |

**Output:**
```json
{
  "status": "created",
  "id": 1,
  "incident_id": 5,
  "review_type": "post_mortem"
}
```

---

#### 49. `update-incident-review`

Updates a review with findings, status, lessons learned.

```
--action update-incident-review --id <db_id> [--status <status>]
         [--findings <text>] [--lessons-learned <text>]
         [--recommendations <text>] [--reviewer <name>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--id` | Yes | Database ID of the review to update |
| `--status` | No | Review status: `pending`, `in_progress`, `completed` |
| `--findings` | No | Review findings text |
| `--lessons-learned` | No | Lessons learned text |
| `--recommendations` | No | Recommendations text |
| `--reviewer` | No | Updated reviewer name |

**Output:**
```json
{
  "status": "updated",
  "id": 1,
  "review_status": "completed"
}
```

---

#### 50. `list-incident-reviews`

Lists incident reviews with optional filters.

```
--action list-incident-reviews [--incident-id <id>] [--status <status>]
         [--review-type <type>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--incident-id` | No | Filter by incident ID |
| `--status` | No | Filter by status: `pending`, `in_progress`, `completed` |
| `--review-type` | No | Filter by review type: `post_mortem`, `lessons_learned`, `root_cause`, `management_review` |

**Output:**
```json
{
  "status": "ok",
  "count": 2,
  "reviews": [
    {
      "id": 1,
      "incident_id": 5,
      "review_type": "post_mortem",
      "title": "Q1 Breach Post-Mortem",
      "status": "completed",
      "reviewer": "CISO",
      "findings": "...",
      "lessons_learned": "..."
    }
  ]
}
```

---

#### 51. `incident-summary`

Aggregate incident statistics: total, by severity, by status, MTTR, trend.

```
--action incident-summary
```

No flags required.

**Output:**
```json
{
  "status": "ok",
  "total_incidents": 12,
  "by_severity": {
    "critical": 2,
    "high": 4,
    "medium": 3,
    "low": 3
  },
  "by_status": {
    "open": 3,
    "investigating": 2,
    "resolved": 5,
    "closed": 2
  },
  "mttr_hours": 18.5,
  "trend": "improving"
}
```

---

### Policy Lifecycle Management (7 actions)

#### 52. `create-policy-version`

Creates a new version of an existing policy.

```
--action create-policy-version --policy-id <id> [--change-summary <text>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--policy-id` | Yes | Database ID of the parent policy |
| `--change-summary` | No | Summary of changes in this version |

**Output:**
```json
{
  "status": "created",
  "id": 2,
  "title": "Access Control Policy",
  "version": "2.0",
  "parent_version_id": 1,
  "policy_status": "draft"
}
```

---

#### 53. `list-policy-versions`

Lists all versions in a policy chain.

```
--action list-policy-versions --policy-id <id>
```

| Flag | Required | Description |
|------|----------|-------------|
| `--policy-id` | Yes | Database ID of the policy |

**Output:**
```json
{
  "status": "ok",
  "count": 3,
  "versions": [
    {
      "id": 1,
      "title": "Access Control Policy",
      "version": "1.0",
      "policy_status": "superseded"
    },
    {
      "id": 2,
      "title": "Access Control Policy",
      "version": "2.0",
      "policy_status": "active"
    }
  ]
}
```

---

#### 54. `submit-policy-approval`

Submits a policy for approval review.

```
--action submit-policy-approval --policy-id <id> --requested-by <name>
         [--request-notes <text>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--policy-id` | Yes | Database ID of the policy to submit |
| `--requested-by` | Yes | Person requesting approval |
| `--request-notes` | No | Notes for the reviewer |

**Output:**
```json
{
  "status": "created",
  "id": 1,
  "policy_id": 2,
  "requested_by": "Policy Manager",
  "decision": "pending"
}
```

---

#### 55. `review-policy-approval`

Reviews a policy approval request.

```
--action review-policy-approval --id <db_id> --decision <decision>
         --reviewer <name> [--notes <text>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--id` | Yes | Database ID of the approval request |
| `--decision` | Yes | Approval decision: `approved`, `rejected`, `changes_requested` |
| `--reviewer` | Yes | Person reviewing the approval |
| `--notes` | No | Review notes or justification |

**Output:**
```json
{
  "status": "updated",
  "id": 1,
  "policy_id": 2,
  "decision": "approved",
  "reviewed_by": "CISO"
}
```

---

#### 56. `list-policy-approvals`

Lists approval records (audit trail).

```
--action list-policy-approvals [--policy-id <id>] [--decision <decision>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--policy-id` | No | Filter by policy ID |
| `--decision` | No | Filter by decision: `pending`, `approved`, `rejected`, `changes_requested` |

**Output:**
```json
{
  "status": "ok",
  "count": 2,
  "approvals": [
    {
      "id": 1,
      "policy_id": 2,
      "requested_by": "Policy Manager",
      "decision": "approved",
      "reviewed_by": "CISO",
      "notes": "Approved after legal review"
    }
  ]
}
```

---

#### 57. `require-policy-acknowledgment`

Creates acknowledgment requirements for multiple users.

```
--action require-policy-acknowledgment --policy-id <id>
         --users <comma_separated_names> [--due-date <YYYY-MM-DD>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--policy-id` | Yes | Database ID of the policy |
| `--users` | Yes | Comma-separated list of user names |
| `--due-date` | No | Acknowledgment due date in `YYYY-MM-DD` format |

**Output:**
```json
{
  "status": "created",
  "policy_id": 2,
  "created_count": 5,
  "created_for": ["alice", "bob", "carol", "dave", "eve"],
  "skipped": []
}
```

---

#### 58. `acknowledge-policy`

Records a user's acknowledgment of a policy.

```
--action acknowledge-policy --policy-id <id> --user-name <name>
```

| Flag | Required | Description |
|------|----------|-------------|
| `--policy-id` | Yes | Database ID of the policy |
| `--user-name` | Yes | Name of the user acknowledging the policy |

**Output:**
```json
{
  "status": "acknowledged",
  "id": 3,
  "user_name": "alice",
  "policy_id": 2
}
```

---

#### 59. `list-policy-acknowledgments`

Lists acknowledgments with rate calculation.

```
--action list-policy-acknowledgments [--policy-id <id>]
         [--pending] [--overdue]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--policy-id` | No | Filter by policy ID |
| `--pending` | No | Boolean flag to show only pending acknowledgments |
| `--overdue` | No | Boolean flag to show only overdue acknowledgments |

**Output:**
```json
{
  "status": "ok",
  "count": 5,
  "acknowledgment_rate": 60.0,
  "acknowledged_count": 3,
  "pending_count": 2,
  "acknowledgments": [
    {
      "id": 1,
      "policy_id": 2,
      "user_name": "alice",
      "acknowledged_at": "2026-02-10T14:00:00Z",
      "due_date": "2026-02-15",
      "status": "acknowledged"
    }
  ]
}
```

---

### Control Effectiveness & Maturity (2 actions)

#### 60. `update-control-effectiveness`

Updates control effectiveness score and maturity level. Auto-computes `effectiveness_rating`:
>=80 = `effective`, >=50 = `partially_effective`, <50 = `ineffective`.

```
--action update-control-effectiveness --id <db_id>
         [--effectiveness-score <0-100>]
         [--maturity-level <level>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--id` | Yes | Database ID of the control |
| `--effectiveness-score` | No | Effectiveness score (integer, 0-100) |
| `--maturity-level` | No | Maturity level: `initial`, `developing`, `defined`, `managed`, `optimizing` |

**Output:**
```json
{
  "status": "updated",
  "id": 5,
  "effectiveness_score": 85,
  "effectiveness_rating": "effective",
  "maturity_level": "managed"
}
```

---

#### 61. `list-controls-by-maturity`

Lists controls filtered by maturity level with distribution stats.

```
--action list-controls-by-maturity [--maturity-level <level>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--maturity-level` | No | Filter by maturity level: `initial`, `developing`, `defined`, `managed`, `optimizing` |

**Output:**
```json
{
  "status": "ok",
  "count": 42,
  "maturity_distribution": {
    "initial": 5,
    "developing": 10,
    "defined": 15,
    "managed": 8,
    "optimizing": 4
  },
  "controls": [
    {
      "id": 5,
      "title": "Access Control",
      "effectiveness_score": 85,
      "effectiveness_rating": "effective",
      "maturity_level": "managed"
    }
  ]
}
```

---

### Test Result Management (3 actions)

#### 62. `add-test-result`

Records a test result, optionally linked to a control.

```
--action add-test-result --test-name <name> --status <status>
         [--control-id-ref <id>] [--items-checked <int>]
         [--items-passed <int>] [--items-failed <int>]
         [--findings <json>] [--duration-ms <int>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--test-name` | Yes | Name of the test |
| `--status` | Yes | Test result status: `passed`, `failed`, `error`, `skipped` |
| `--control-id-ref` | No | Database ID of the linked control |
| `--items-checked` | No | Number of items checked (integer) |
| `--items-passed` | No | Number of items that passed (integer) |
| `--items-failed` | No | Number of items that failed (integer) |
| `--findings` | No | Findings as a JSON object or array |
| `--duration-ms` | No | Test duration in milliseconds (integer) |

**Output:**
```json
{
  "status": "created",
  "id": 1,
  "result_status": "passed",
  "test_name": "MFA Enforcement Check"
}
```

---

#### 63. `list-test-results`

Lists test results with pass rate.

```
--action list-test-results [--control-id-ref <id>] [--test-name <name>]
         [--status <status>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--control-id-ref` | No | Filter by linked control ID |
| `--test-name` | No | Filter by test name |
| `--status` | No | Filter by status: `passed`, `failed`, `error`, `skipped` |

**Output:**
```json
{
  "status": "ok",
  "count": 3,
  "pass_rate": 66.7,
  "results": [
    {
      "id": 1,
      "test_name": "MFA Enforcement Check",
      "result_status": "passed",
      "control_id_ref": 5,
      "items_checked": 50,
      "items_passed": 50,
      "items_failed": 0,
      "duration_ms": 1200
    }
  ]
}
```

---

#### 64. `test-summary`

Aggregate test statistics with per-test breakdown and trend.

```
--action test-summary
```

No flags required.

**Output:**
```json
{
  "status": "ok",
  "total_runs": 45,
  "pass_rate": 82.2,
  "by_status": {
    "passed": 37,
    "failed": 5,
    "error": 2,
    "skipped": 1
  },
  "by_test": {
    "MFA Enforcement Check": {
      "runs": 10,
      "pass_rate": 90.0
    },
    "Encryption at Rest": {
      "runs": 8,
      "pass_rate": 75.0
    }
  },
  "trend": "improving"
}
```

---

## Action Summary: Incidents, Policies, Controls, Tests

| # | Action | Category | Required Args |
|---|--------|----------|---------------|
| 46 | `add-incident-action` | Incident Actions | `--incident-id`, `--action-type`, `--description`, `--performed-by` |
| 47 | `list-incident-actions` | Incident Actions | `--incident-id` |
| 48 | `add-incident-review` | Incident Reviews | `--incident-id`, `--review-type`, `--title` |
| 49 | `update-incident-review` | Incident Reviews | `--id` |
| 50 | `list-incident-reviews` | Incident Reviews | _(none)_ |
| 51 | `incident-summary` | Incident Summary | _(none)_ |
| 52 | `create-policy-version` | Policy Lifecycle | `--policy-id` |
| 53 | `list-policy-versions` | Policy Lifecycle | `--policy-id` |
| 54 | `submit-policy-approval` | Policy Lifecycle | `--policy-id`, `--requested-by` |
| 55 | `review-policy-approval` | Policy Lifecycle | `--id`, `--decision`, `--reviewer` |
| 56 | `list-policy-approvals` | Policy Lifecycle | _(none)_ |
| 57 | `require-policy-acknowledgment` | Policy Lifecycle | `--policy-id`, `--users` |
| 58 | `acknowledge-policy` | Policy Lifecycle | `--policy-id`, `--user-name` |
| 59 | `list-policy-acknowledgments` | Policy Lifecycle | _(none)_ |
| 60 | `update-control-effectiveness` | Control Effectiveness | `--id` |
| 61 | `list-controls-by-maturity` | Control Maturity | _(none)_ |
| 62 | `add-test-result` | Test Results | `--test-name`, `--status` |
| 63 | `list-test-results` | Test Results | _(none)_ |
| 64 | `test-summary` | Test Results | _(none)_ |

---

## Action Summary: Assets, Training, Vulnerabilities, Reviews, Questionnaires

| # | Action | Category | Required Args |
|---|--------|----------|---------------|
| 23 | `add-asset` | Asset Management | `--name` |
| 24 | `list-assets` | Asset Management | _(none)_ |
| 25 | `update-asset` | Asset Management | `--id` |
| 26 | `add-training-module` | Training Management | `--title` |
| 27 | `list-training-modules` | Training Management | _(none)_ |
| 28 | `add-training-assignment` | Training Management | `--module-id`, `--assignee` |
| 29 | `list-training-assignments` | Training Management | _(none)_ |
| 30 | `update-training-assignment` | Training Management | `--id` |
| 31 | `add-vulnerability` | Vulnerability Management | `--title` |
| 32 | `list-vulnerabilities` | Vulnerability Management | _(none)_ |
| 33 | `update-vulnerability` | Vulnerability Management | `--id` |
| 34 | `add-access-review` | Access Review | `--title` |
| 35 | `list-access-reviews` | Access Review | _(none)_ |
| 36 | `update-access-review` | Access Review | `--id` |
| 37 | `add-review-item` | Access Review | `--campaign-id`, `--user-name`, `--resource` |
| 38 | `list-review-items` | Access Review | `--campaign-id` |
| 39 | `update-review-item` | Access Review | `--id` |
| 40 | `add-questionnaire-template` | Questionnaire | `--title`, `--questions` |
| 41 | `list-questionnaire-templates` | Questionnaire | _(none)_ |
| 42 | `add-questionnaire-response` | Questionnaire | `--template-id`, `--respondent` |
| 43 | `list-questionnaire-responses` | Questionnaire | _(none)_ |
| 44 | `add-questionnaire-answer` | Questionnaire | `--response-id`, `--question-index`, `--answer-text` |
| 45 | `update-questionnaire-response` | Questionnaire | `--id` |

---

### Integration Management (5 actions)

#### 65. `add-integration`

Registers a new cloud provider integration (AWS, GitHub, Google, Okta, etc.).

```
--action add-integration --provider <provider> --name <name>
         [--schedule <cron>] [--config <json>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--provider` | Yes | Provider type: `aws`, `github`, `google`, `okta` |
| `--name` | Yes | Display name for this integration |
| `--schedule` | No | Sync schedule (cron expression) |
| `--config` | No | JSON configuration (credentials reference, scope, etc.) |

**Output:**
```json
{
  "status": "created",
  "id": 1,
  "provider": "aws",
  "name": "Production AWS"
}
```

---

#### 66. `list-integrations`

Lists integrations with optional filters.

```
--action list-integrations [--provider <provider>] [--status <status>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--provider` | No | Filter by provider: `aws`, `github`, `google`, `okta` |
| `--status` | No | Filter by status: `configured`, `active`, `syncing`, `error`, `disabled` |

**Output:**
```json
{
  "status": "ok",
  "count": 2,
  "integrations": [
    {
      "id": 1,
      "provider": "aws",
      "name": "Production AWS",
      "status": "active",
      "schedule": "0 */6 * * *",
      "last_sync": "2026-02-13T06:00:00",
      "error_count": 0
    }
  ]
}
```

---

#### 67. `update-integration`

Updates an integration record.

```
--action update-integration --id <db_id> [--status <status>] [--name <name>]
         [--schedule <cron>] [--last-sync <timestamp>] [--next-sync <timestamp>]
         [--error-message <text>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--id` | Yes | Database ID of the integration |
| `--status` | No | Updated status: `configured`, `active`, `syncing`, `error`, `disabled` |
| `--name` | No | Updated display name |
| `--schedule` | No | Updated sync schedule |
| `--last-sync` | No | Last successful sync timestamp |
| `--next-sync` | No | Next scheduled sync timestamp |
| `--error-message` | No | Error message (auto-increments error_count) |

**Output:**
```json
{
  "status": "updated",
  "id": 1
}
```

---

#### 68. `sync-integration`

Triggers an immediate sync for an integration. Marks the integration as `syncing`.

```
--action sync-integration --id <db_id>
```

| Flag | Required | Description |
|------|----------|-------------|
| `--id` | Yes | Database ID of the integration to sync |

**Output:**
```json
{
  "status": "syncing",
  "id": 1,
  "provider": "aws",
  "name": "Production AWS"
}
```

---

#### 69. `integration-health`

Shows a health dashboard for all integrations with evidence counts and staleness detection.

```
--action integration-health
```

No flags required.

**Output:**
```json
{
  "status": "ok",
  "total": 3,
  "healthy": 2,
  "errored": 0,
  "stale": 1,
  "disabled": 0,
  "integrations": [
    {
      "id": 1,
      "provider": "aws",
      "name": "Production AWS",
      "health": "healthy",
      "sync_age_hours": 6.2,
      "evidence_count": 45,
      "last_evidence_date": "2026-02-13T06:00:00"
    }
  ]
}
```

**Health statuses:** `healthy` (active, no errors), `errored` (error_count > 0), `stale` (last sync > 48h ago), `disabled` (manually disabled)

---

### Alert Management (4 actions)

#### 70. `add-alert`

Creates a new compliance alert.

```
--action add-alert --type <type> --title <title>
         [--severity <level>] [--description <text>]
         [--resource-type <type>] [--resource-id <id>]
         [--drift-details <json>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--type` | Yes | Alert type: `evidence_expiring`, `evidence_expired`, `control_overdue`, `score_decline`, `integration_error`, `vendor_review_due`, `drift_detected` |
| `--title` | Yes | Alert title |
| `--severity` | No | Severity: `critical`, `warning`, `info` (default: `info`) |
| `--description` | No | Alert message body |
| `--resource-type` | No | Resource type (e.g. `s3_bucket`, `iam_user`) |
| `--resource-id` | No | External resource identifier |
| `--drift-details` | No | JSON with drift metadata |

**Output:**
```json
{
  "status": "created",
  "id": 1,
  "type": "evidence_expiring",
  "severity": "warning",
  "title": "SOC 2 evidence expiring in 7 days"
}
```

---

#### 71. `list-alerts`

Lists alerts with optional filters.

```
--action list-alerts [--type <type>] [--severity <level>] [--status <status>]
         [--acknowledged <0|1>] [--resolved <0|1>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--type` | No | Filter by alert type |
| `--severity` | No | Filter by severity: `critical`, `warning`, `info` |
| `--status` | No | Filter by status: `active`, `acknowledged`, `resolved` |
| `--acknowledged` | No | Filter by acknowledgment: `0` (unacknowledged), `1` (acknowledged) |
| `--resolved` | No | Filter by resolution: `0` (unresolved), `1` (resolved) |

**Output:**
```json
{
  "status": "ok",
  "count": 5,
  "unacknowledged": 3,
  "unresolved": 4,
  "alerts": [
    {
      "id": 1,
      "type": "evidence_expiring",
      "severity": "warning",
      "title": "SOC 2 evidence expiring in 7 days",
      "status": "active",
      "triggered_at": "2026-02-13T08:00:00",
      "acknowledged_at": null,
      "resolved_at": null
    }
  ]
}
```

---

#### 72. `acknowledge-alert`

Acknowledges an alert (marks as seen without resolving).

```
--action acknowledge-alert --id <db_id> [--acknowledged-by <name>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--id` | Yes | Database ID of the alert |
| `--acknowledged-by` | No | Person acknowledging (default: `user`) |

**Output:**
```json
{
  "status": "acknowledged",
  "id": 1
}
```

---

#### 73. `resolve-alert`

Resolves an alert (marks as resolved with timestamp).

```
--action resolve-alert --id <db_id>
```

| Flag | Required | Description |
|------|----------|-------------|
| `--id` | Yes | Database ID of the alert to resolve |

**Output:**
```json
{
  "status": "resolved",
  "id": 1
}
```

---

### Browser Check Management (4 actions)

#### 74. `add-browser-check`

Registers a URL for scheduled scanning (headers, SSL, GDPR).

```
--action add-browser-check --name <name> --url <url> --check-type <type>
         [--schedule <cron>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--name` | Yes | Display name for this check |
| `--url` | Yes | URL to check |
| `--check-type` | Yes | Check type: `headers`, `ssl`, `gdpr`, `full` |
| `--schedule` | No | Check schedule (cron expression) |

**Output:**
```json
{
  "status": "created",
  "id": 1,
  "name": "Production Site Headers",
  "url": "https://acme.com",
  "check_type": "headers"
}
```

---

#### 75. `list-browser-checks`

Lists registered browser checks.

```
--action list-browser-checks [--check-type <type>] [--status <status>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--check-type` | No | Filter by check type: `headers`, `ssl`, `gdpr`, `full` |
| `--status` | No | Filter by status: `active`, `paused`, `error` |

**Output:**
```json
{
  "status": "ok",
  "count": 2,
  "checks": [
    {
      "id": 1,
      "name": "Production Site Headers",
      "url": "https://acme.com",
      "check_type": "headers",
      "status": "active",
      "last_run": "2026-02-13T06:00:00",
      "run_count": 12
    }
  ]
}
```

---

#### 76. `update-browser-check`

Updates a browser check record.

```
--action update-browser-check --id <db_id> [--status <status>] [--name <name>]
         [--url <url>] [--schedule <cron>] [--last-run <timestamp>]
         [--last-result <json>] [--last-status <status>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--id` | Yes | Database ID of the browser check |
| `--status` | No | Updated status: `active`, `paused`, `error` |
| `--name` | No | Updated display name |
| `--url` | No | Updated URL |
| `--schedule` | No | Updated schedule |
| `--last-run` | No | Last run timestamp (auto-increments run_count) |
| `--last-result` | No | Last run result (JSON) |
| `--last-status` | No | Last run status |

**Output:**
```json
{
  "status": "updated",
  "id": 1
}
```

---

#### 77. `run-browser-check`

Triggers an immediate browser check run. Marks the check as running and increments run count.

```
--action run-browser-check --id <db_id>
```

| Flag | Required | Description |
|------|----------|-------------|
| `--id` | Yes | Database ID of the browser check to run |

**Output:**
```json
{
  "status": "running",
  "id": 1,
  "name": "Production Site Headers",
  "url": "https://acme.com",
  "check_type": "headers"
}
```

---

### Drift Detection (2 actions)

#### 78. `check-drift`

Compares recent evidence snapshots to detect configuration regressions or improvements.

```
--action check-drift [--provider <provider>] [--check-type <check>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--provider` | No | Filter by provider: `aws`, `github`, or `all` (default: `all`) |
| `--check-type` | No | Filter by specific check name (e.g. `iam`, `s3`) |

**Output:**
```json
{
  "status": "ok",
  "total_checks": 8,
  "drifted": 2,
  "regressions": 1,
  "improvements": 1,
  "unchanged": 6,
  "drifts": [
    {
      "provider": "aws",
      "check": "s3",
      "type": "regression",
      "severity": "warning",
      "current_failed": 3,
      "previous_failed": 1,
      "evidence_id": 42
    }
  ]
}
```

**Drift types:** `regression` (more failures), `improvement` (fewer failures), `unchanged`, `initial` (first snapshot)

---

#### 79. `drift-history`

Retrieves drift detection history from alert records.

```
--action drift-history [--provider <provider>] [--days <30>]
         [--severity <regression|improvement>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--provider` | No | Filter by provider |
| `--days` | No | Look back N days (default: 30) |
| `--severity` | No | Filter: `regression` (critical/warning) or `improvement` (info) |

**Output:**
```json
{
  "status": "ok",
  "total": 5,
  "regressions": 2,
  "improvements": 3,
  "drifts": [...]
}
```

---

### Cross-Framework Evidence Mapping (2 actions)

#### 80. `auto-map-evidence`

Suggests cross-framework control linkages for evidence based on control_mappings.

```
--action auto-map-evidence --id <evidence_id>
```

| Flag | Required | Description |
|------|----------|-------------|
| `--id` | Yes | Database ID of the evidence to map |

**How it works:**
1. Gets currently linked controls for the evidence
2. Looks up cross-framework mappings (confidence >= 0.7)
3. Returns suggested additional controls to link

**Output:**
```json
{
  "status": "ok",
  "evidence_id": 5,
  "original_controls": [12, 15],
  "suggested_controls": [
    {
      "control_id": "A.9.1.1",
      "framework": "iso27001",
      "confidence": 0.9,
      "source_control": 12
    }
  ],
  "mapped_count": 3
}
```

---

#### 81. `list-evidence-gaps`

Lists controls that have no active evidence linked.

```
--action list-evidence-gaps [--framework <slug>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--framework` | No | Filter by framework slug (omit for all frameworks) |

**Output:**
```json
{
  "status": "ok",
  "total_controls": 43,
  "controls_with_evidence": 28,
  "controls_without_evidence": 15,
  "framework_coverage_pct": 65.1,
  "gaps": [
    {
      "control_id": 5,
      "framework": "soc2",
      "title": "Logical Access Controls"
    }
  ]
}
```

---

### Compliance Calendar & Digest (2 actions)

#### 82. `compliance-calendar`

Aggregates upcoming compliance deadlines from all sources.

```
--action compliance-calendar [--days <30>]
         [--type <all|evidence|policy|vendor|training>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--days` | No | Look ahead N days (default: 30) |
| `--type` | No | Filter by type: `all`, `evidence`, `policy`, `vendor`, `training` (default: `all`) |

**Aggregates from:**
- Evidence `valid_until` dates
- Policy `review_date` dates
- Vendor `next_assessment_date`
- Training assignment `due_date`

**Output:**
```json
{
  "status": "ok",
  "total": 8,
  "overdue": 2,
  "due_this_week": 1,
  "due_this_month": 5,
  "upcoming": [
    {
      "type": "evidence_expiry",
      "date": "2026-02-15",
      "title": "Evidence expires: AWS MFA Config",
      "resource_id": 3,
      "resource_type": "evidence",
      "overdue": false
    }
  ]
}
```

---

#### 83. `compliance-digest`

Generates a compliance activity digest for a given period.

```
--action compliance-digest [--period <daily|weekly|monthly>]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--period` | No | Digest period: `daily` (1 day), `weekly` (7 days), `monthly` (30 days). Default: `daily` |

**Output:**
```json
{
  "status": "ok",
  "period": "weekly",
  "digest": {
    "average_score": 73.5,
    "frameworks_tracked": 2,
    "new_alerts": 3,
    "unresolved_alerts": 5,
    "expiring_evidence": 2,
    "overdue_training": 1,
    "overdue_policies": 0,
    "active_incidents": 1,
    "total_integrations": 3,
    "healthy_integrations": 2
  }
}
```

---

## Action Summary: Integrations, Alerts, Browser Checks, Drift, Calendar

| # | Action | Category | Required Args |
|---|--------|----------|---------------|
| 65 | `add-integration` | Integration Management | `--provider`, `--name` |
| 66 | `list-integrations` | Integration Management | _(none)_ |
| 67 | `update-integration` | Integration Management | `--id` |
| 68 | `sync-integration` | Integration Management | `--id` |
| 69 | `integration-health` | Integration Management | _(none)_ |
| 70 | `add-alert` | Alert Management | `--type`, `--title` |
| 71 | `list-alerts` | Alert Management | _(none)_ |
| 72 | `acknowledge-alert` | Alert Management | `--id` |
| 73 | `resolve-alert` | Alert Management | `--id` |
| 74 | `add-browser-check` | Browser Check Management | `--name`, `--url`, `--check-type` |
| 75 | `list-browser-checks` | Browser Check Management | _(none)_ |
| 76 | `update-browser-check` | Browser Check Management | `--id` |
| 77 | `run-browser-check` | Browser Check Management | `--id` |
| 78 | `check-drift` | Drift Detection | _(none)_ |
| 79 | `drift-history` | Drift Detection | _(none)_ |
| 80 | `auto-map-evidence` | Evidence Mapping | `--id` |
| 81 | `list-evidence-gaps` | Evidence Mapping | _(none)_ |
| 82 | `compliance-calendar` | Compliance Calendar | _(none)_ |
| 83 | `compliance-digest` | Compliance Calendar | _(none)_ |
