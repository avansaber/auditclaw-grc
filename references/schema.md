# GRC Compliance Database Schema

**Engine:** SQLite (WAL mode)
**Location:** `~/.openclaw/grc/compliance.sqlite`
**Schema Version:** 6.0.0
**Tables (36)**

---

## Table List

| # | Table | Purpose |
|---|-------|---------|
| 1 | `schema_version` | Schema version tracking |
| 2 | `metadata` | Key-value metadata store |
| 3 | `frameworks` | Compliance frameworks activated for the organization |
| 4 | `controls` | Controls from activated frameworks |
| 5 | `evidence` | Evidence files linked to controls |
| 6 | `evidence_controls` | Many-to-many: evidence to controls |
| 7 | `risks` | Risk register entries |
| 8 | `vendors` | Third-party vendor records |
| 9 | `assets` | IT and data asset inventory with classification and control linkage |
| 10 | `incidents` | Security and compliance incident log |
| 11 | `policies` | Organizational policies |
| 12 | `policy_controls` | Many-to-many: policies to controls |
| 13 | `training_modules` | Training course definitions with recertification tracking |
| 14 | `training_assignments` | Per-person training assignments with scoring |
| 15 | `checklists` | Personnel onboarding/offboarding checklists |
| 16 | `checklist_items` | Individual items within a checklist |
| 17 | `compliance_scores` | Historical compliance score snapshots |
| 18 | `alerts` | Compliance alerts and notifications |
| 19 | `control_mappings` | Cross-framework control mappings |
| 20 | `audit_log` | Action audit trail |
| 21 | `vulnerabilities` | Vulnerability tracking with CVE, CVSS, severity, remediation |
| 22 | `vulnerability_controls` | Many-to-many: vulnerabilities to controls |
| 23 | `access_review_campaigns` | Periodic access review campaigns |
| 24 | `access_review_items` | Individual items within an access review campaign |
| 25 | `questionnaire_templates` | Vendor assessment questionnaire templates |
| 26 | `questionnaire_responses` | Responses to questionnaire templates |
| 27 | `questionnaire_answers` | Individual answers within a questionnaire response |
| 28 | `asset_controls` | Many-to-many: assets to controls |
| 29 | `incident_actions` | Timeline of actions taken during incident response |
| 30 | `incident_reviews` | Post-incident reviews and lessons learned |
| 31 | `policy_approvals` | Policy approval workflow audit trail |
| 32 | `policy_acknowledgments` | Policy acknowledgment tracking per user |
| 33 | `test_results` | Automated test run results linked to controls |
| 34 | `integrations` | Cloud provider integration configuration and sync tracking |
| 35 | `browser_checks` | Scheduled URL scanning for headers, SSL, GDPR compliance |
| 36 | `integration_credentials` | Secure credential storage for cloud provider integrations |

---

## Table Definitions

### 1. `schema_version`

Schema version tracking. Single row.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| version | TEXT NOT NULL | | Semantic version string (e.g. `2.0.0`) |
| applied_at | TEXT | `datetime('now')` | When this version was applied |

---

### 2. `frameworks`

Compliance frameworks activated for the organization (SOC 2, ISO 27001, HIPAA, etc.).

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| name | TEXT NOT NULL | | Display name: `SOC 2`, `ISO 27001`, etc. |
| slug | TEXT UNIQUE NOT NULL | | URL-safe key: `soc2`, `iso27001` |
| version | TEXT | | Framework version string |
| status | TEXT | `'active'` | `active`, `inactive` |
| priority | INTEGER | `1` | Sort/importance order |
| activated_at | TEXT | `datetime('now')` | When activated |
| notes | TEXT | | Free-text notes |

---

### 3. `controls`

Controls from activated frameworks.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| framework_id | INTEGER FK | | References `frameworks(id)` |
| control_id | TEXT NOT NULL | | Framework control ID: `CC6.1`, `A.9.1.1` |
| title | TEXT NOT NULL | | Control title |
| description | TEXT | | Full description |
| category | TEXT | | Control family/domain |
| status | TEXT | `'not_started'` | `not_started`, `in_progress`, `awaiting_review`, `complete`, `rejected` |
| assignee | TEXT | | Person responsible |
| due_date | TEXT | | ISO 8601 date |
| priority | INTEGER | `3` | 1-5 (5 = highest) |
| review_date | TEXT | | Next review date |
| implementation_notes | TEXT | | Notes on implementation |
| last_updated | TEXT | `datetime('now')` | Last modification timestamp |

**Unique constraint:** `(framework_id, control_id)`

---

### 4. `evidence`

Evidence files linked to controls.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| title | TEXT NOT NULL | | Evidence title |
| filename | TEXT | | Original filename |
| filepath | TEXT | | Path in workspace |
| description | TEXT | | Description of evidence |
| type | TEXT | | `manual`, `automated`, `integration` |
| source | TEXT | | `aws`, `github`, `google`, `manual`, etc. |
| valid_from | TEXT | | Start of validity period |
| valid_until | TEXT | | Expiration date |
| status | TEXT | `'active'` | `active`, `expired`, `archived`, `pending_review` |
| uploaded_at | TEXT | `datetime('now')` | Upload timestamp |
| metadata | TEXT | | JSON for integration-specific data |

---

### 5. `evidence_controls`

Many-to-many linkage between evidence and controls.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| evidence_id | INTEGER FK | | References `evidence(id)` ON DELETE CASCADE |
| control_id | INTEGER FK | | References `controls(id)` ON DELETE CASCADE |

**Primary key:** `(evidence_id, control_id)`

---

### 6. `risks`

Risk register entries.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| title | TEXT NOT NULL | | Risk title |
| description | TEXT | | Full description |
| category | TEXT | | `operational`, `financial`, `strategic`, `compliance`, `security` |
| likelihood | INTEGER | | 1-5 (CHECK constraint) |
| impact | INTEGER | | 1-5 (CHECK constraint) |
| score | INTEGER | | **Generated column:** `likelihood * impact` (STORED) |
| treatment | TEXT | | `mitigate`, `accept`, `transfer`, `avoid` |
| treatment_plan | TEXT | | Description of treatment approach |
| owner | TEXT | | Risk owner |
| review_date | TEXT | | Next review date |
| status | TEXT | `'open'` | `open`, `mitigated`, `accepted`, `closed` |
| linked_controls | TEXT | | JSON array of control IDs |
| created_at | TEXT | `datetime('now')` | Creation timestamp |
| last_updated | TEXT | `datetime('now')` | Last modification timestamp |

---

### 7. `vendors`

Third-party vendor records.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| name | TEXT NOT NULL | | Vendor name |
| category | TEXT | | `saas`, `infrastructure`, `professional_services` |
| criticality | TEXT | `'medium'` | `critical`, `high`, `medium`, `low` |
| data_access | TEXT | | JSON describing what data they access |
| contact_name | TEXT | | Primary contact name |
| contact_email | TEXT | | Primary contact email |
| contract_start | TEXT | | Contract start date |
| contract_end | TEXT | | Contract end date |
| last_assessment_date | TEXT | | Last vendor assessment date |
| next_assessment_date | TEXT | | Next assessment due date |
| risk_score | INTEGER | | Calculated risk score |
| status | TEXT | `'active'` | `active`, `inactive`, `under_review` |
| notes | TEXT | | Free-text notes |
| documents | TEXT | | JSON array of document paths |

---

### 8. `assets` (Enhanced in V2)

IT and data asset inventory. V2 added fields for network details, lifecycle management, security posture, and data classification.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| name | TEXT NOT NULL | | Asset name |
| type | TEXT | | `hardware`, `software`, `cloud`, `network`, `data` |
| criticality | TEXT | `'medium'` | `critical`, `high`, `medium`, `low` |
| owner | TEXT | | Asset owner |
| location | TEXT | | Physical or logical location |
| status | TEXT | `'active'` | `active`, `inactive`, `decommissioned` |
| description | TEXT | | Asset description |
| linked_controls | TEXT | | JSON array (legacy; use `asset_controls` table in V2) |
| metadata | TEXT | | JSON for type-specific data |
| **ip_address** | TEXT | | *V2* IP address |
| **hostname** | TEXT | | *V2* DNS hostname |
| **os_type** | TEXT | | *V2* Operating system type |
| **software_version** | TEXT | | *V2* Software/firmware version |
| **lifecycle_stage** | TEXT | `'in_use'` | *V2* `in_use`, `in_development`, `retired`, `decommissioned` |
| **deployment_date** | TEXT | | *V2* When asset was deployed |
| **encryption_status** | TEXT | | *V2* Encryption state (e.g. `encrypted`, `unencrypted`) |
| **backup_status** | TEXT | | *V2* Backup state |
| **patch_status** | TEXT | | *V2* Patch compliance state |
| **last_patched_date** | TEXT | | *V2* Date of last patch |
| **discovery_source** | TEXT | `'manual'` | *V2* How asset was discovered: `manual`, `scan`, `integration` |
| **data_classification** | TEXT | `'internal'` | *V2* `public`, `internal`, `confidential`, `restricted` |
| **created_at** | TEXT | | *V2* Creation timestamp |
| **updated_at** | TEXT | | *V2* Last modification timestamp |

---

### 9. `incidents`

Security and compliance incident log.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| title | TEXT NOT NULL | | Incident title |
| description | TEXT | | Full description |
| type | TEXT | | `security_breach`, `data_loss`, `system_outage`, `unauthorized_access`, `policy_violation`, `malware`, `physical` |
| severity | TEXT | `'medium'` | `critical`, `high`, `medium`, `low` |
| status | TEXT | `'detected'` | `detected`, `investigating`, `contained`, `resolved`, `closed` |
| reported_by | TEXT | | Who reported the incident |
| reported_at | TEXT | `datetime('now')` | When reported |
| resolved_at | TEXT | | Resolution timestamp |
| root_cause | TEXT | | Root cause analysis |
| corrective_actions | TEXT | | Actions taken |
| affected_systems | TEXT | | JSON array of affected systems |
| impact_assessment | TEXT | | Assessment of business impact |
| timeline | TEXT | | JSON timeline of events |
| lessons_learned | TEXT | | Post-incident lessons |
| metadata | TEXT | | JSON for additional data |

---

### 10. `policies`

Organizational policies.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| title | TEXT NOT NULL | | Policy title |
| type | TEXT | | `information_security`, `acceptable_use`, `access_control`, `data_retention`, `incident_response`, `privacy`, etc. |
| version | TEXT | `'1.0'` | Version string |
| status | TEXT | `'draft'` | `draft`, `active`, `under_review`, `archived` |
| content_path | TEXT | | Path to .md file in workspace |
| approved_by | TEXT | | Approver name |
| approved_at | TEXT | | Approval timestamp |
| review_date | TEXT | | Next review date |
| created_at | TEXT | `datetime('now')` | Creation timestamp |
| last_updated | TEXT | `datetime('now')` | Last modification timestamp |
| notes | TEXT | | Free-text notes |

---

### 11. `policy_controls`

Many-to-many linkage between policies and controls.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| policy_id | INTEGER FK | | References `policies(id)` ON DELETE CASCADE |
| control_id | INTEGER FK | | References `controls(id)` ON DELETE CASCADE |

**Primary key:** `(policy_id, control_id)`

---

### 12. `training_modules` (Enhanced in V2)

Training course definitions. V2 added fields for content delivery, difficulty, and recertification.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| title | TEXT NOT NULL | | Module title |
| category | TEXT | | `security_awareness`, `privacy`, `compliance`, `role_specific` |
| description | TEXT | | Module description |
| duration_minutes | INTEGER | | Duration in minutes |
| duration | INTEGER | | Duration (alternate field) |
| status | TEXT | `'active'` | `active`, `inactive`, `archived` |
| created_at | TEXT | `datetime('now')` | Creation timestamp |
| **content_type** | TEXT | | *V2* `video`, `document`, `interactive`, `quiz` |
| **content_url** | TEXT | | *V2* URL or path to training content |
| **difficulty_level** | TEXT | `'beginner'` | *V2* `beginner`, `intermediate`, `advanced` |
| **requires_recertification** | INTEGER | `0` | *V2* Boolean: 1 = requires periodic recertification |
| **recertification_days** | INTEGER | | *V2* Days between required recertifications |
| **updated_at** | TEXT | | *V2* Last modification timestamp |

---

### 13. `training_assignments` (Enhanced in V2)

Per-person training assignments. V2 added certificate tracking and timestamps.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| module_id | INTEGER FK | | References `training_modules(id)` |
| assignee | TEXT NOT NULL | | Person assigned |
| status | TEXT | `'pending'` | `pending`, `in_progress`, `completed`, `overdue` |
| due_date | TEXT | | Due date |
| completed_at | TEXT | | Completion timestamp |
| score | INTEGER | | Assessment score |
| **assigned_at** | TEXT | | *V2* When the assignment was created |
| **certificate_path** | TEXT | | *V2* Path to completion certificate |
| **created_at** | TEXT | | *V2* Creation timestamp |
| **updated_at** | TEXT | | *V2* Last modification timestamp |

---

### 14. `checklists`

Personnel onboarding/offboarding checklists.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| type | TEXT NOT NULL | | `onboarding`, `offboarding` |
| person_name | TEXT NOT NULL | | Person the checklist is for |
| status | TEXT | `'in_progress'` | `in_progress`, `completed` |
| created_at | TEXT | `datetime('now')` | Creation timestamp |
| completed_at | TEXT | | Completion timestamp |

---

### 15. `checklist_items`

Individual items within a checklist.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| checklist_id | INTEGER FK | | References `checklists(id)` ON DELETE CASCADE |
| title | TEXT NOT NULL | | Item title/description |
| completed | INTEGER | `0` | Boolean: 1 = done |
| completed_at | TEXT | | Completion timestamp |
| notes | TEXT | | Free-text notes |

---

### 16. `compliance_scores`

Historical compliance score snapshots for trend tracking.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| framework_slug | TEXT | | Framework identifier (e.g. `soc2`) |
| score | REAL NOT NULL | | Overall score (0-100) |
| total_controls | INTEGER | | Total controls evaluated |
| healthy_controls | INTEGER | | Controls in good standing |
| at_risk_controls | INTEGER | | Controls at risk |
| critical_controls | INTEGER | | Controls in critical state |
| calculated_at | TEXT | `datetime('now')` | When score was calculated |
| metadata | TEXT | | JSON with detailed scoring breakdown |

---

### 17. `alerts`

Compliance alerts and notifications.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| type | TEXT NOT NULL | | `evidence_expiring`, `evidence_expired`, `control_overdue`, `score_decline`, `integration_error`, `vendor_review_due` |
| severity | TEXT | `'info'` | `critical`, `warning`, `info` |
| title | TEXT NOT NULL | | Alert title |
| message | TEXT | | Alert message body |
| status | TEXT | `'active'` | `active`, `acknowledged`, `resolved` |
| triggered_at | TEXT | `datetime('now')` | When alert was triggered |
| resolved_at | TEXT | | Resolution timestamp |
| cooldown_until | TEXT | | Suppression window end (prevents duplicate alerts) |
| metadata | TEXT | | JSON for additional alert data |

---

### 18. `control_mappings`

Cross-framework control mappings (e.g. SOC 2 CC6.1 maps to ISO 27001 A.9.1.1).

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| source_framework | TEXT NOT NULL | | Source framework slug |
| source_control_id | TEXT NOT NULL | | Source control identifier |
| target_framework | TEXT NOT NULL | | Target framework slug |
| target_control_id | TEXT NOT NULL | | Target control identifier |
| confidence | REAL | `1.0` | Mapping confidence 0.0-1.0 |

**Unique constraint:** `(source_framework, source_control_id, target_framework, target_control_id)`

---

### 19. `audit_log`

Action audit trail for all database operations.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| action | TEXT NOT NULL | | Action performed: `created`, `updated`, `deleted`, `synced`, `generated`, etc. |
| entity_type | TEXT | | Entity type: `control`, `evidence`, `risk`, `vendor`, etc. |
| entity_id | INTEGER | | Entity row ID |
| details | TEXT | | JSON with change details |
| performed_at | TEXT | `datetime('now')` | When action was performed |

---

### 20. `vulnerabilities` (V2)

Vulnerability tracking with CVE identifiers, CVSS scoring, and remediation workflow.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| title | TEXT NOT NULL | | Vulnerability title |
| cve_id | TEXT | | CVE identifier (e.g. `CVE-2024-1234`) |
| description | TEXT | | Full description |
| source | TEXT | | Discovery source: scan tool name, `manual`, etc. |
| cvss_score | REAL | | CVSS score (0.0-10.0) |
| cvss_vector | TEXT | | CVSS vector string |
| severity | TEXT | `'medium'` | `low`, `medium`, `high`, `critical` |
| status | TEXT | `'open'` | `open`, `in_progress`, `resolved`, `risk_accepted` |
| assignee | TEXT | | Person assigned to remediate |
| affected_assets | TEXT | | JSON array or description of affected assets |
| affected_packages | TEXT | | JSON array of affected software packages |
| remediation_steps | TEXT | | Steps to remediate |
| fix_version | TEXT | | Version that contains the fix |
| due_date | TEXT | | Remediation due date |
| resolved_at | TEXT | | Resolution timestamp |
| resolved_by | TEXT | | Who resolved it |
| risk_accepted | INTEGER | `0` | Boolean: 1 = risk has been formally accepted |
| risk_acceptance_reason | TEXT | | Justification for risk acceptance |
| created_at | TEXT | `datetime('now')` | Creation timestamp |
| last_updated | TEXT | `datetime('now')` | Last modification timestamp |
| updated_at | TEXT | | Alternate update timestamp |

---

### 21. `vulnerability_controls` (V2)

Many-to-many linkage between vulnerabilities and controls.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| vulnerability_id | INTEGER FK | | References `vulnerabilities(id)` ON DELETE CASCADE |
| control_id | INTEGER FK | | References `controls(id)` ON DELETE CASCADE |
| created_at | TEXT | | Linkage creation timestamp |

**Primary key:** `(vulnerability_id, control_id)`

---

### 22. `access_review_campaigns` (V2)

Periodic access review campaigns for user access certification.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| title | TEXT NOT NULL | | Campaign title |
| description | TEXT | | Campaign description |
| scope_type | TEXT | | Scope category: `department`, `system`, `role`, etc. |
| scope_config | TEXT | | JSON: departments, systems, roles in scope |
| reviewer | TEXT | | Assigned reviewer |
| status | TEXT | `'draft'` | `draft`, `in_progress`, `completed`, `cancelled` |
| start_date | TEXT | | Campaign start date |
| due_date | TEXT | | Campaign due date |
| completed_at | TEXT | | Completion timestamp |
| total_items | INTEGER | `0` | Total items to review |
| reviewed_items | INTEGER | `0` | Items reviewed so far |
| approved_items | INTEGER | `0` | Items approved |
| revoked_items | INTEGER | `0` | Items revoked |
| created_at | TEXT | `datetime('now')` | Creation timestamp |
| updated_at | TEXT | | Last modification timestamp |

---

### 23. `access_review_items` (V2)

Individual items within an access review campaign.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| campaign_id | INTEGER FK | | References `access_review_campaigns(id)` ON DELETE CASCADE |
| user_name | TEXT NOT NULL | | User whose access is being reviewed |
| resource | TEXT NOT NULL | | Resource/system being accessed |
| current_access | TEXT | | Description of current access level |
| decision | TEXT | `'pending'` | `pending`, `approved`, `revoked`, `flagged` |
| reviewer | TEXT | | Who reviewed this item |
| reviewed_at | TEXT | | Review timestamp |
| notes | TEXT | | Reviewer notes |
| created_at | TEXT | | Creation timestamp |

---

### 24. `questionnaire_templates` (V2)

Vendor assessment questionnaire templates (SIG, CAIQ, HECVAT, custom).

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| title | TEXT NOT NULL | | Template title |
| description | TEXT | | Template description |
| category | TEXT | | `sig`, `caiq`, `hecvat`, `custom`, `vendor_assessment` |
| questions | TEXT | | JSON array of question objects |
| total_questions | INTEGER | `0` | Total number of questions |
| status | TEXT | `'active'` | `active`, `inactive`, `archived` |
| created_at | TEXT | `datetime('now')` | Creation timestamp |
| updated_at | TEXT | | Last modification timestamp |

---

### 25. `questionnaire_responses` (V2)

Responses to questionnaire templates, one per vendor/respondent.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| template_id | INTEGER FK | | References `questionnaire_templates(id)` |
| respondent | TEXT NOT NULL | | Person or entity responding |
| vendor_id | INTEGER FK | | References `vendors(id)` |
| status | TEXT | `'draft'` | `draft`, `in_progress`, `completed`, `reviewed` |
| total_questions | INTEGER | `0` | Total questions in this response |
| answered_questions | INTEGER | `0` | Questions answered so far |
| submitted_at | TEXT | | Submission timestamp |
| reviewed_at | TEXT | | Review timestamp |
| reviewed_by | TEXT | | Who reviewed the response |
| created_at | TEXT | `datetime('now')` | Creation timestamp |
| updated_at | TEXT | | Last modification timestamp |

---

### 26. `questionnaire_answers` (V2)

Individual answers within a questionnaire response.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PK | AUTOINCREMENT | |
| response_id | INTEGER FK | | References `questionnaire_responses(id)` ON DELETE CASCADE |
| question_index | INTEGER NOT NULL | | Zero-based index into template questions array |
| answer_text | TEXT | | The answer text |
| status | TEXT | `'pending'` | `pending`, `answered`, `flagged` |
| notes | TEXT | | Additional notes or context |
| created_at | TEXT | | Creation timestamp |

---

### 27. `asset_controls` (V2)

Many-to-many linkage between assets and controls.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| asset_id | INTEGER FK | | References `assets(id)` ON DELETE CASCADE |
| control_id | INTEGER FK | | References `controls(id)` ON DELETE CASCADE |

**Primary key:** `(asset_id, control_id)`

---

### 28. `incident_actions` (V3)

Timeline of actions taken during incident response.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| incident_id | INTEGER | NOT NULL, FK → incidents(id) | Parent incident |
| action_type | TEXT | NOT NULL | containment, investigation, eradication, recovery, notification, other |
| description | TEXT | NOT NULL | What was done |
| performed_by | TEXT | NOT NULL | Person or team |
| performed_at | TEXT | DEFAULT datetime('now') | When performed |
| notes | TEXT | | Additional details |
| duration_minutes | INTEGER | | Time spent in minutes |

---

### 29. `incident_reviews` (V3)

Post-incident reviews and lessons learned.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| incident_id | INTEGER | NOT NULL, FK → incidents(id) | Reviewed incident |
| review_type | TEXT | NOT NULL | post_mortem, lessons_learned, root_cause, management_review |
| title | TEXT | NOT NULL | Review title |
| status | TEXT | DEFAULT 'pending' | pending, in_progress, completed |
| reviewer | TEXT | | Assigned reviewer |
| findings | TEXT | | Review findings |
| lessons_learned | TEXT | | Key lessons |
| recommendations | TEXT | | Recommended actions |
| due_date | TEXT | | Review due date |
| completed_at | TEXT | | When completed |
| created_at | TEXT | DEFAULT datetime('now') | Creation timestamp |

---

### 30. `policy_approvals` (V3)

Policy approval workflow audit trail.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| policy_id | INTEGER | NOT NULL, FK → policies(id) | Policy under review |
| requested_by | TEXT | NOT NULL | Person requesting approval |
| decision | TEXT | DEFAULT 'pending' | pending, approved, rejected, changes_requested |
| reviewed_by | TEXT | | Reviewer name |
| decision_notes | TEXT | | Approval/rejection notes |
| request_notes | TEXT | | Notes from requester |
| requested_at | TEXT | DEFAULT datetime('now') | Request timestamp |
| reviewed_at | TEXT | | Decision timestamp |
| created_at | TEXT | DEFAULT datetime('now') | Creation timestamp |

---

### 31. `policy_acknowledgments` (V3)

Policy acknowledgment tracking per user.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| policy_id | INTEGER | NOT NULL, FK → policies(id) | Policy to acknowledge |
| user_name | TEXT | NOT NULL | User required to acknowledge |
| status | TEXT | DEFAULT 'pending' | pending, acknowledged |
| due_date | TEXT | | Acknowledgment deadline |
| acknowledged_at | TEXT | | When acknowledged |
| created_at | TEXT | DEFAULT datetime('now') | Creation timestamp |
| UNIQUE | | (policy_id, user_name) | One ack per user per policy |

---

### 32. `test_results` (V3)

Automated test run results linked to controls.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| test_name | TEXT | NOT NULL | Name of the test |
| status | TEXT | NOT NULL | passed, failed, error, skipped |
| control_id | INTEGER | FK → controls(id) | Linked control (optional) |
| items_checked | INTEGER | | Total items examined |
| items_passed | INTEGER | | Items that passed |
| items_failed | INTEGER | | Items that failed |
| findings | TEXT | | JSON array of findings |
| duration_ms | INTEGER | | Test duration in milliseconds |
| run_at | TEXT | DEFAULT datetime('now') | When test was run |
| created_at | TEXT | DEFAULT datetime('now') | Creation timestamp |

---

### 33. `integrations` (V4)

Cloud provider integration configuration and sync status tracking.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| provider | TEXT | NOT NULL | Provider type: `aws`, `github`, `google`, `okta` |
| name | TEXT | NOT NULL | Display name for this integration |
| status | TEXT | DEFAULT 'configured' | `configured`, `active`, `syncing`, `error`, `disabled` |
| schedule | TEXT | | Sync schedule (cron expression) |
| last_sync | TEXT | | Last successful sync timestamp |
| next_sync | TEXT | | Next scheduled sync timestamp |
| last_error | TEXT | | Last error message |
| error_count | INTEGER | DEFAULT 0 | Consecutive error count |
| config | TEXT | | JSON configuration (credentials reference, scope) |
| created_at | TEXT | DEFAULT datetime('now') | Creation timestamp |
| updated_at | TEXT | | Last modification timestamp |

---

### 34. `browser_checks` (V4)

Scheduled URL scanning for security headers, SSL, and GDPR compliance checks.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| name | TEXT | NOT NULL | Display name for this check |
| url | TEXT | NOT NULL | URL to check |
| check_type | TEXT | NOT NULL | `headers`, `ssl`, `gdpr`, `full` |
| schedule | TEXT | | Check schedule (cron expression) |
| status | TEXT | DEFAULT 'active' | `active`, `paused`, `error` |
| last_run | TEXT | | Last run timestamp |
| last_result | TEXT | | Last run result (JSON) |
| last_status | TEXT | | Last run status |
| run_count | INTEGER | DEFAULT 0 | Total number of runs |
| created_at | TEXT | DEFAULT datetime('now') | Creation timestamp |
| updated_at | TEXT | | Last modification timestamp |

---

## Indexes

### V1 Indexes

| Index | Table | Column(s) |
|-------|-------|-----------|
| `idx_controls_framework` | controls | framework_id |
| `idx_controls_status` | controls | status |
| `idx_evidence_status` | evidence | status |
| `idx_evidence_valid_until` | evidence | valid_until |
| `idx_risks_score` | risks | score |
| `idx_risks_status` | risks | status |
| `idx_vendors_criticality` | vendors | criticality |
| `idx_incidents_status` | incidents | status |
| `idx_incidents_severity` | incidents | severity |
| `idx_compliance_scores_framework` | compliance_scores | framework_slug |
| `idx_compliance_scores_date` | compliance_scores | calculated_at |
| `idx_control_mappings_source` | control_mappings | (source_framework, source_control_id) |
| `idx_control_mappings_target` | control_mappings | (target_framework, target_control_id) |
| `idx_alerts_status` | alerts | status |
| `idx_audit_log_entity` | audit_log | (entity_type, entity_id) |

### V2 Indexes

| Index | Table | Column(s) |
|-------|-------|-----------|
| `idx_vulnerabilities_status` | vulnerabilities | status |
| `idx_vulnerabilities_severity` | vulnerabilities | severity |
| `idx_vulnerabilities_cve` | vulnerabilities | cve_id |
| `idx_access_reviews_status` | access_review_campaigns | status |
| `idx_questionnaire_responses_status` | questionnaire_responses | status |
| `idx_assets_lifecycle` | assets | lifecycle_stage |
| `idx_assets_classification` | assets | data_classification |
| `idx_training_assignments_status` | training_assignments | status |

### V3 Indexes

| Index | Table | Columns |
|-------|-------|---------|
| `idx_incident_actions_incident` | incident_actions | incident_id |
| `idx_incident_reviews_incident` | incident_reviews | incident_id |
| `idx_policy_approvals_policy` | policy_approvals | policy_id |
| `idx_policy_acks_policy` | policy_acknowledgments | policy_id |
| `idx_test_results_control` | test_results | control_id |
| `idx_test_results_name` | test_results | test_name |
| `idx_controls_maturity` | controls | maturity_level |
| `idx_controls_effectiveness` | controls | effectiveness_score |

### V4 Indexes

| Index | Table | Columns |
|-------|-------|---------|
| `idx_integrations_provider` | integrations | provider |
| `idx_integrations_status` | integrations | status |
| `idx_browser_checks_type` | browser_checks | check_type |
| `idx_browser_checks_status` | browser_checks | status |

---

## Relationships

### V1 Relationships

```
frameworks 1──∞ controls
controls  ∞──∞ evidence       (via evidence_controls)
controls  ∞──∞ policies       (via policy_controls)
checklists 1──∞ checklist_items
training_modules 1──∞ training_assignments
compliance_scores ∞──1 frameworks  (via framework_slug)
```

### V2 Relationships

```
vulnerabilities ∞──∞ controls            (via vulnerability_controls)
assets          ∞──∞ controls            (via asset_controls)
access_review_campaigns 1──∞ access_review_items
questionnaire_templates 1──∞ questionnaire_responses
questionnaire_responses 1──∞ questionnaire_answers
vendors         1──∞ questionnaire_responses
```

### V3 Relationships

```
incidents       1──∞ incident_actions
incidents       1──∞ incident_reviews
policies        1──∞ policy_approvals
policies        1──∞ policy_acknowledgments
controls        1──∞ test_results
policies        1──∞ policies              (via parent_version_id, version chains)
```

### V4 Relationships

```
integrations (standalone, linked to evidence via provider/source matching)
browser_checks (standalone, results stored as evidence)
alerts ←→ drift_details (JSON drift metadata)
```

---

## Status Workflows

### Control Status

```
not_started -> in_progress -> awaiting_review -> complete
                                              -> rejected
```

### Evidence Status

```
active -> expired
active -> archived
active -> pending_review
```

### Risk Status

```
open -> mitigated -> closed
open -> accepted
```

### Incident Status

```
detected -> investigating -> contained -> resolved -> closed
```

### Policy Status

```
draft -> active -> under_review -> archived
```

### Vulnerability Status (V2)

```
open -> in_progress -> resolved
                    -> risk_accepted
```

### Access Review Decision (V2)

```
pending -> approved
        -> revoked
        -> flagged
```

### Access Review Campaign Status (V2)

```
draft -> in_progress -> completed
                     -> cancelled
```

### Questionnaire Response Status (V2)

```
draft -> in_progress -> completed -> reviewed
```

### Training Assignment Status

```
pending -> in_progress -> completed
                       -> overdue
```

### Incident Review Status (V3)

```
pending -> in_progress -> completed
```

### Policy Approval Decision (V3)

```
pending -> approved
        -> rejected
        -> changes_requested
```

### Policy Acknowledgment Status (V3)

```
pending -> acknowledged
```

### Test Result Status (V3)

```
passed | failed | error | skipped
```

### Integration Status (V4)

```
configured -> active -> syncing -> active
                     -> error
active -> disabled
```

### Browser Check Status (V4)

```
active -> paused
active -> error
```

### Alert Status (V4 enhanced)

```
active -> acknowledged -> resolved
active -> resolved
```

---

## Enum Reference

### Severity Levels (shared)

`critical` | `high` | `medium` | `low`

Vulnerabilities also accept: `informational`

### Asset Types

`hardware` | `software` | `cloud` | `network` | `data`

### Asset Lifecycle Stages (V2)

`in_use` | `in_development` | `retired` | `decommissioned`

### Data Classification (V2)

`public` | `internal` | `confidential` | `restricted`

### Vendor Criticality

`critical` | `high` | `medium` | `low`

### Risk Categories

`operational` | `financial` | `strategic` | `compliance` | `security`

### Risk Treatment Options

`mitigate` | `accept` | `transfer` | `avoid`

### Incident Types

`security_breach` | `data_loss` | `system_outage` | `unauthorized_access` | `policy_violation` | `malware` | `physical`

### Training Categories

`security_awareness` | `privacy` | `compliance` | `role_specific`

### Questionnaire Template Categories (V2)

`sig` | `caiq` | `hecvat` | `custom` | `vendor_assessment`

### Incident Action Types (V3)

`containment` | `investigation` | `eradication` | `recovery` | `notification` | `other`

### Incident Review Types (V3)

`post_mortem` | `lessons_learned` | `root_cause` | `management_review`

### Control Maturity Levels (V3)

`initial` | `developing` | `defined` | `managed` | `optimizing`

### Control Effectiveness Ratings (V3)

`effective` (>=80) | `partially_effective` (>=50) | `ineffective` (<50)

### Policy Approval Decisions (V3)

`pending` | `approved` | `rejected` | `changes_requested`

### Test Result Statuses (V3)

`passed` | `failed` | `error` | `skipped`

### Integration Providers (V4)

`aws` | `github` | `google` | `okta`

### Integration Statuses (V4)

`configured` | `active` | `syncing` | `error` | `disabled`

### Browser Check Types (V4)

`headers` | `ssl` | `gdpr` | `full`

### Alert Types (V4 extended)

`evidence_expiring` | `evidence_expired` | `control_overdue` | `score_decline` | `integration_error` | `vendor_review_due` | `drift_detected`

### Drift Types (V4)

`regression` | `improvement` | `unchanged` | `initial`

---

## Migration Notes

| Scenario | Script | What Happens |
|----------|--------|-------------|
| Fresh install | `init_db.py` | Creates all 34 tables with V4 schema, sets `schema_version = 4.0.0` |
| Existing V1 database | `migrate_v2.py` | ALTER TABLE adds columns to `assets`, `training_modules`, `training_assignments`; CREATE TABLE IF NOT EXISTS adds 8 new tables; creates V2 indexes; updates `schema_version` to `2.0.0` |
| Existing V2 database | `migrate_v3.py` | ALTER TABLE adds columns to `controls`, `incidents`, `policies`; CREATE TABLE IF NOT EXISTS adds 5 new tables; creates V3 indexes; updates `schema_version` to `3.0.0` |
| Existing V3 database | `migrate_v4.py` | CREATE TABLE IF NOT EXISTS adds 2 new tables (`integrations`, `browser_checks`); ALTER TABLE adds 5 columns to `alerts`; creates V4 indexes; updates `schema_version` to `4.0.0` |
| Already V4 | Any script | Returns `already_initialized` / `already_migrated` (idempotent) |

### V2 Columns Added to Existing Tables

**assets** (13 new columns): `ip_address`, `hostname`, `os_type`, `software_version`, `lifecycle_stage`, `deployment_date`, `encryption_status`, `backup_status`, `patch_status`, `last_patched_date`, `discovery_source`, `data_classification`, `created_at`

**training_modules** (5 new columns): `content_type`, `content_url`, `difficulty_level`, `requires_recertification`, `recertification_days`

**training_assignments** (1 new column): `certificate_path`

### V3 Column Additions

#### controls (4 new columns)

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| maturity_level | TEXT | NULL | initial, developing, defined, managed, optimizing |
| effectiveness_score | INTEGER | NULL | 0-100 effectiveness rating |
| effectiveness_rating | TEXT | NULL | Auto-computed: effective (>=80), partially_effective (>=50), ineffective (<50) |
| last_tested_at | TEXT | NULL | Timestamp of last test result linked to this control |

#### incidents (5 new columns)

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| estimated_cost | REAL | NULL | Estimated financial impact |
| actual_cost | REAL | NULL | Actual financial impact |
| regulatory_notification | INTEGER | NULL | 0/1 whether regulatory notification was required |
| notification_details | TEXT | NULL | Details of notifications sent |
| preventive_measures | TEXT | NULL | Preventive measures implemented |

#### policies (2 new columns)

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| parent_version_id | INTEGER | NULL | FK → policies(id) for version chains |
| change_summary | TEXT | NULL | Summary of changes from previous version |

### V4 Column Additions

#### alerts (5 new columns)

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| drift_details | TEXT | NULL | JSON drift metadata (provider, check, details) |
| resource_type | TEXT | NULL | Resource type (e.g. `s3_bucket`, `iam_user`) |
| resource_id | TEXT | NULL | External resource identifier |
| acknowledged_at | TEXT | NULL | When the alert was acknowledged |
| acknowledged_by | TEXT | NULL | Who acknowledged the alert |

---

## Database Configuration

- **Journal mode:** WAL (Write-Ahead Logging) for concurrent read performance
- **Foreign keys:** Enabled (`PRAGMA foreign_keys = ON`)
- **Default path:** `~/.openclaw/grc/compliance.sqlite`
- **Environment override:** `GRC_DB_PATH` environment variable
- **CLI override:** `--db-path` argument on init_db.py / db_query.py / migrate_v2.py / migrate_v3.py / migrate_v4.py
