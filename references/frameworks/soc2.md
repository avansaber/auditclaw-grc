# SOC 2 Type II Framework Reference

**Version:** 2024.1  
**Total Controls:** 43 (42 from JSON + custom additions)  
**Domains:** 4 (Common Criteria, Availability, Confidentiality, Processing Integrity)

## Activation

```bash
python3 scripts/db_query.py --action activate-framework --slug soc2 \
  --framework-file assets/frameworks/soc2.json
```

## Domain Summary

| Domain | ID | Controls | Priority Range |
|--------|-----|----------|---------------|
| Common Criteria | CC | 33 | P3–P5 |
| Availability | A | 3 | P3–P4 |
| Confidentiality | C | 2 | P3–P4 |
| Processing Integrity | PI | 5 | P3 |

## Priority Distribution

| Priority | Count | Description |
|----------|-------|-------------|
| P5 (Critical) | 7 | CC3.2, CC6.1, CC6.2, CC6.3, CC6.6, CC7.2, CC7.4 |
| P4 (High) | 19 | CC1.1, CC3.1, CC3.3, CC4.1, CC4.2, CC5.1, CC5.2, CC6.4, CC6.7, CC6.8, CC7.1, CC7.3, CC7.5, CC8.1, CC9.1, A1.1, A1.3, C1.1 |
| P3 (Medium) | 17 | All remaining controls |

## Controls by Domain

### CC: Common Criteria (33 controls)

#### Control Environment (CC1.x)

| ID | Title | Priority | Typical Evidence |
|----|-------|----------|-----------------|
| CC1.1 | Demonstrates commitment to integrity and ethical values | P4 | Code of Conduct, Ethics training records, Disciplinary action policy |
| CC1.2 | Board exercises oversight responsibility | P3 | Board meeting minutes, Audit committee charter |
| CC1.3 | Management establishes structure, authority, and responsibility | P3 | Org chart, RACI matrix, Job descriptions |
| CC1.4 | Demonstrates commitment to competence | P3 | HR policy, Training records, Performance reviews |
| CC1.5 | Holds individuals accountable | P3 | Performance review process, Accountability framework |

#### Communication and Information (CC2.x)

| ID | Title | Priority | Typical Evidence |
|----|-------|----------|-----------------|
| CC2.1 | Obtains or generates relevant information | P3 | Information classification policy, Data flow diagrams |
| CC2.2 | Communicates internal control information internally | P3 | Internal communications, Policy distribution records |
| CC2.3 | Communicates with external parties | P3 | External communication policy, Vendor notification procedures |

#### Risk Assessment (CC3.x)

| ID | Title | Priority | Typical Evidence |
|----|-------|----------|-----------------|
| CC3.1 | Specifies suitable objectives | P4 | Risk assessment methodology, Risk register |
| CC3.2 | Identifies and analyzes risk | **P5** | Risk assessment report, Threat modeling docs, Vulnerability scans |
| CC3.3 | Considers fraud risk | P4 | Fraud risk assessment, Anti-fraud controls |
| CC3.4 | Identifies and assesses changes | P3 | Change management policy, Change impact assessments |

#### Monitoring Activities (CC4.x)

| ID | Title | Priority | Typical Evidence |
|----|-------|----------|-----------------|
| CC4.1 | Selects and develops monitoring activities | P4 | Monitoring procedures, Internal audit reports, Automated monitoring tools |
| CC4.2 | Evaluates and communicates deficiencies | P4 | Deficiency tracking log, Corrective action plans |

#### Control Activities (CC5.x)

| ID | Title | Priority | Typical Evidence |
|----|-------|----------|-----------------|
| CC5.1 | Selects and develops control activities | P4 | Control catalog, Risk treatment plans |
| CC5.2 | Selects and develops technology controls | P4 | IT general controls, System hardening standards |
| CC5.3 | Deploys through policies and procedures | P3 | Published policies, Procedure documentation, Training records |

#### Logical and Physical Access Controls (CC6.x)

| ID | Title | Priority | Typical Evidence |
|----|-------|----------|-----------------|
| CC6.1 | Implements logical access security | **P5** | Access control policy, SSO/MFA configuration, RBAC documentation |
| CC6.2 | Controls access credentials | **P5** | User provisioning procedures, Access request forms, Onboarding checklist |
| CC6.3 | Manages access removal | **P5** | Access review logs, Offboarding procedures, Deprovisioning evidence |
| CC6.4 | Restricts physical access | P4 | Physical security policy, Visitor logs, Badge access records |
| CC6.5 | Manages access to protected assets | P3 | Asset disposal procedures, Data destruction certificates |
| CC6.6 | Manages security threats and vulnerabilities | **P5** | Endpoint protection config, Vulnerability scan reports, Patch management records |
| CC6.7 | Manages transmission security | P4 | Encryption policy, TLS configuration, VPN documentation |
| CC6.8 | Controls system boundaries | P4 | Firewall rules, Network segmentation docs, WAF configuration |

#### System Operations (CC7.x)

| ID | Title | Priority | Typical Evidence |
|----|-------|----------|-----------------|
| CC7.1 | Manages system changes | P4 | Change management policy, Change tickets, CAB meeting minutes |
| CC7.2 | Monitors system components | **P5** | SIEM configuration, Monitoring dashboards, Alert procedures |
| CC7.3 | Evaluates security events | P4 | Incident response plan, Security event logs, Triage procedures |
| CC7.4 | Responds to security incidents | **P5** | Incident response plan, Incident reports, Post-incident reviews |
| CC7.5 | Recovers from security incidents | P4 | Disaster recovery plan, Business continuity plan, Recovery test results |

#### Change Management (CC8.x)

| ID | Title | Priority | Typical Evidence |
|----|-------|----------|-----------------|
| CC8.1 | Manages changes to infrastructure and software | P4 | SDLC documentation, Code review records, Deployment procedures |

#### Risk Mitigation (CC9.x)

| ID | Title | Priority | Typical Evidence |
|----|-------|----------|-----------------|
| CC9.1 | Identifies and manages risk from vendors | P4 | Vendor risk assessment, Vendor agreements, Vendor monitoring records |
| CC9.2 | Manages risk from business disruptions | P3 | Business impact analysis, Vendor contingency plans |

### A: Availability (3 controls)

| ID | Title | Priority | Typical Evidence |
|----|-------|----------|-----------------|
| A1.1 | Manages system capacity | P4 | Capacity monitoring reports, Auto-scaling configuration, Performance baselines |
| A1.2 | Manages environmental protections | P3 | Environmental controls documentation, UPS/generator records |
| A1.3 | Manages recovery operations | P4 | DR test results, Backup verification logs, RTO/RPO documentation |

### C: Confidentiality (2 controls)

| ID | Title | Priority | Typical Evidence |
|----|-------|----------|-----------------|
| C1.1 | Identifies confidential information | P4 | Data classification policy, Data inventory, Sensitivity labels |
| C1.2 | Disposes of confidential information | P3 | Data disposal procedures, Destruction certificates, Retention schedule |

### PI: Processing Integrity (5 controls)

| ID | Title | Priority | Typical Evidence |
|----|-------|----------|-----------------|
| PI1.1 | Defines processing specifications | P3 | Processing specifications, SLAs, Data quality standards |
| PI1.2 | Monitors processing quality | P3 | Quality assurance procedures, Processing error logs, Reconciliation reports |
| PI1.3 | Maintains processing records | P3 | Audit trail configuration, Log retention policy |
| PI1.4 | Handles processing errors | P3 | Error handling procedures, Exception management process |
| PI1.5 | Controls system inputs and outputs | P3 | Input validation rules, Output verification procedures |

## Cross-Framework Mappings

SOC 2 controls include mappings to:
- **ISO 27001**: Annex A controls (e.g., A.9.1.1, A.12.4.1)
- **NIST CSF**: Functions/Categories (e.g., PR.AC-1, DE.CM-1)

These mappings are loaded automatically during framework activation and stored in the `control_mappings` table.

### Coverage Examples

| SOC 2 | ISO 27001 | NIST CSF |
|-------|-----------|----------|
| CC6.1 (Logical access) | A.9.1.1, A.9.2.1, A.9.4.1 | PR.AC-1, PR.AC-3 |
| CC7.2 (Monitoring) | A.12.4.1 | DE.CM-1, DE.AE-1 |
| CC7.4 (Incident response) | A.16.1.5, A.16.1.6 | RS.RP-1, RS.CO-1 |
| CC3.2 (Risk analysis) | A.6.1.2, A.12.6.1 | ID.RA-1, ID.RA-3 |
