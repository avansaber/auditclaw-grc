# Changelog

All notable changes to AuditClaw GRC are documented here.
Versioning follows [Semantic Versioning](https://semver.org/).

## [1.0.1] - 2026-02-16

### Fixed
- Synced init_db.py schema with migration scripts (integrations table missing `name` column, incident_actions table missing `title`/`action_taken_at` columns)
- `add-alert` action now writes `resource_type`, `resource_id`, `drift_details` to actual columns (previously only stored in metadata JSON)
- Added `busy_timeout = 5000ms` to SQLite connections for write contention resilience
- Fixed `check_headers.py` crashing at import time when `requests` library is not installed
- Fixed migration test assertions to match consolidated init_db schema
- All 431 tests passing (previously 27 schema mismatch failures + 5 import failures)

## [1.0.0] - 2026-02-15

Initial public release on [ClawHub](https://clawhub.dev) and [GitHub](https://github.com/avansaber/auditclaw-grc).

### Core Platform
- 97 CLI actions via `db_query.py` (single entry point, JSON output)
- 30 SQLite database tables with WAL mode
- 13 compliance frameworks with 990+ controls:
  - SOC 2, ISO 27001, HIPAA, GDPR, NIST CSF, PCI DSS
  - CIS Controls v8, CMMC 2.0, HITRUST CSF v11, CCPA
  - FedRAMP Moderate, ISO 42001, SOX ITGC
- 431 unit tests, 46 production scenarios validated

### Compliance Management
- Control tracking with status, assignee, due dates, and priority
- Control effectiveness scoring (0-100) with automated rating
- Control maturity levels: initial, developing, defined, managed, optimizing
- Test results tracking linked to controls with pass rates and trends
- Cross-framework control mappings
- Compliance scoring with trend tracking and drift detection
- Gap analysis with priority scoring and effort estimates

### Evidence & Reporting
- Evidence lifecycle management with expiry tracking
- Evidence-to-control linkage (many-to-many)
- Auto-evidence mapping and evidence gap analysis
- CSV evidence export with injection protection
- HTML report generation with XSS prevention
- Interactive HTML dashboard with Canvas integration
- Trust center HTML page generation

### Risk & Incident Management
- Risk register with likelihood/impact scoring and treatment plans
- Incident tracking with timeline actions (containment, investigation, recovery)
- Post-incident reviews with findings, lessons learned, and root cause
- Incident summary with MTTR calculation and severity distribution
- Incident cost tracking and regulatory notification flags

### Policy & Compliance Workflow
- Policy versioning with version chain tracking
- Policy approval workflow: submit, approve, reject, request changes
- Policy acknowledgment tracking per user with due dates
- Compliance alerts with acknowledge/resolve workflow
- Compliance calendar and compliance digest
- Cron-based scheduled alerts

### Asset & Vendor Management
- Asset inventory with criticality, lifecycle, and classification
- Vendor management with risk scoring and contract tracking
- Vendor questionnaire templates with responses, answers, and scoring
- Access review campaigns with approve/revoke/flag decisions
- Vulnerability management with CVE/CVSS tracking and remediation workflow
- Training module management with assignment tracking and completion scoring

### Integrations
- Cloud provider integration framework (AWS, GitHub, Azure, GCP, Okta, Google Workspace)
- Integration health monitoring and sync tracking
- Companion skill detection (`list-companions` action)
- Integration setup guides and credential store
- Browser-based URL scanning (headers, SSL, GDPR) with scheduling
- Drift detection and drift history tracking

### Security
- Secure credential management with path traversal protection and secret masking
- CSV injection protection in evidence exports
- XSS prevention in HTML report generation
- SQLite busy_timeout for write contention resilience

### Packaging
- Published to ClawHub (OpenClaw skill marketplace)
- `.clawhubignore` for clean package builds
- All pip dependencies pinned to exact versions
- SKILL.md with security model documentation
