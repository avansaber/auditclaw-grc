# FedRAMP Moderate Framework Reference

## Overview
The Federal Risk and Authorization Management Program (FedRAMP) provides a standardized approach to security assessment, authorization, and continuous monitoring for cloud products and services used by U.S. federal agencies.

## Baseline
**FedRAMP Moderate** is based on NIST SP 800-53 Rev 5 and applies to cloud systems where the loss of confidentiality, integrity, or availability would have a **serious adverse effect** on organizational operations, assets, or individuals.

## Control Families

| Family | ID | Focus Area |
|--------|-----|-----------|
| Access Control | AC | User access, least privilege, remote access, separation of duties |
| Awareness and Training | AT | Security awareness, role-based training |
| Audit and Accountability | AU | Audit logging, event analysis, retention, protection |
| Assessment, Authorization and Monitoring | CA | Security assessments, system authorization, continuous monitoring |
| Configuration Management | CM | Baseline configurations, change control, least functionality |
| Contingency Planning | CP | Business continuity, disaster recovery, backup, testing |
| Identification and Authentication | IA | Multi-factor auth, device identification, credential management |
| Incident Response | IR | Incident handling, reporting, monitoring, response plan |
| Maintenance | MA | System maintenance, remote maintenance, maintenance tools |
| Media Protection | MP | Media access, marking, storage, transport, sanitization |
| Physical and Environmental Protection | PE | Physical access, monitoring, environmental controls |
| Planning | PL | Security planning, acceptable use, architecture |
| Program Management | PM | Information security program, risk management strategy |
| Personnel Security | PS | Personnel screening, termination, transfers |
| PII Processing and Transparency | PT | Privacy notices, consent, data minimization |
| Risk Assessment | RA | Risk assessment, vulnerability scanning, monitoring |
| System and Services Acquisition | SA | Allocation, development lifecycle, testing, supply chain |
| System and Communications Protection | SC | Boundary protection, cryptography, denial of service |
| System and Information Integrity | SI | Flaw remediation, malware protection, monitoring, alerts |
| Supply Chain Risk Management | SR | Supply chain controls, provenance, component authenticity |

## Key Requirements for Compliance
1. **3PAO Assessment**: Must use an accredited Third Party Assessment Organization
2. **Continuous Monitoring**: Monthly vulnerability scans, annual penetration testing
3. **POA&M Management**: Plan of Action and Milestones for all findings
4. **Incident Reporting**: Report incidents to US-CERT within specified timeframes
5. **Authorization Package**: SSP, SAR, POA&M, and supporting artifacts

## Typical Evidence
- System Security Plan (SSP)
- Security Assessment Report (SAR)
- Plan of Action and Milestones (POA&M)
- Continuous Monitoring reports
- Vulnerability scan results
- Penetration test reports
- Configuration baseline documentation
- Access control lists and user access reviews
- Incident response plan and test results
- Business continuity / disaster recovery plans

## Cross-Framework Mappings
| FedRAMP Family | SOC 2 | ISO 27001 | NIST CSF |
|----------------|-------|-----------|----------|
| AC (Access Control) | CC6.1-CC6.8 | A.9 | PR.AC |
| AU (Audit) | CC7.1-CC7.4 | A.12.4 | DE.AE, DE.CM |
| CM (Config Mgmt) | CC8.1 | A.12.1, A.14.2 | PR.IP |
| CP (Contingency) | A1.1-A1.3 | A.17 | PR.IP, RC |
| IA (Auth) | CC6.1 | A.9.2-A.9.4 | PR.AC |
| IR (Incident) | CC7.3-CC7.5 | A.16 | RS |
| SC (System/Comms) | CC6.1, CC6.7 | A.10, A.13 | PR.DS |

## Usage
```
/auditclaw-grc activate framework --slug fedramp
/auditclaw-grc compliance score --framework fedramp
/auditclaw-grc gap analysis --framework fedramp
```
