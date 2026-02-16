# SOX IT General Controls Framework Reference

## Overview
The Sarbanes-Oxley Act (SOX) Section 404 requires management to assess and report on the effectiveness of internal controls over financial reporting (ICFR). **IT General Controls (ITGC)** are the foundation of reliable financial IT systems.

## Domains

| Domain | ID | Focus |
|--------|-----|-------|
| Access to Programs and Data | AC | Logical access, user provisioning, privileged access, SoD |
| Program Changes | CM | Change management, testing, approval, deployment |
| Program Development | PD | SDLC, requirements, testing, data conversion |
| Computer Operations | CO | Job scheduling, backup, incident management, monitoring |

## Access to Programs and Data (AC)
Controls ensuring only authorized users can access financial applications and data:
- User access provisioning and deprovisioning
- Periodic access reviews
- Privileged account management
- Segregation of duties enforcement
- Password and authentication policies
- Remote access controls
- Database access controls
- Service account management

## Program Changes (CM)
Controls ensuring changes to financial systems are properly authorized, tested, and deployed:
- Change request and approval workflows
- Development/test/production environment separation
- Code review and testing requirements
- Emergency change procedures
- Version control and rollback procedures
- Change documentation and audit trail
- Post-implementation review

## Program Development (PD)
Controls ensuring new systems are developed with proper controls:
- System development lifecycle (SDLC) methodology
- Requirements documentation and sign-off
- Security requirements integration
- User acceptance testing (UAT)
- Data migration and conversion controls
- Go-live approval process
- Project management oversight

## Computer Operations (CO)
Controls ensuring reliable and continuous operation of financial systems:
- Batch job scheduling and monitoring
- Backup and recovery procedures
- Disaster recovery planning and testing
- System monitoring and alerting
- Incident management processes
- Capacity management
- Data center physical security
- Environmental controls

## Key Requirements for Compliance
1. **Management Assessment**: Annual assessment of ITGC effectiveness
2. **External Audit**: Independent auditor testing of key controls
3. **Deficiency Reporting**: Material weaknesses must be disclosed
4. **Evidence Retention**: Minimum 7 years for SOX-related records
5. **Segregation of Duties**: Strict SoD for financial system access
6. **Change Management**: All changes to financial systems documented and approved

## Typical Evidence
- User access review reports
- Segregation of duties matrix
- Change management tickets and approvals
- Code review documentation
- UAT sign-off records
- Backup and recovery test results
- DR plan and test results
- Job scheduling logs
- Incident tickets for financial systems
- Access provisioning/deprovisioning forms
- Privileged access audit logs
- Password policy documentation

## Cross-Framework Mappings
| SOX ITGC Domain | SOC 2 | ISO 27001 | NIST CSF |
|-----------------|-------|-----------|----------|
| AC (Access) | CC6.1-CC6.8 | A.9 | PR.AC |
| CM (Changes) | CC8.1 | A.12.1, A.14.2 | PR.IP |
| PD (Development) | CC8.1 | A.14.1, A.14.2 | PR.IP |
| CO (Operations) | CC7.1-CC7.4 | A.12.1-A.12.4 | PR.IP, DE.CM |

## Usage
```
/auditclaw-grc activate framework --slug sox-itgc
/auditclaw-grc compliance score --framework sox-itgc
/auditclaw-grc gap analysis --framework sox-itgc
```
