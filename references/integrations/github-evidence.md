# GitHub Evidence Collection Guide

**Purpose:** Collect compliance evidence from GitHub organizations and repositories for SOC 2, ISO 27001, NIST CSF, PCI DSS, and other frameworks.

## Quick Start

```bash
# Check branch protection and save as evidence
gh api repos/myorg/myrepo/branches/main/protection \
  | python3 scripts/db_query.py --action add-evidence \
    --title "Branch Protection - myrepo/main" --type automated \
    --source github-api --control-ids 33,34 \
    --valid-from 2026-01-01 --valid-until 2026-04-01
```

**Prerequisites:** GitHub CLI (`gh`) authenticated with appropriate scopes:
```bash
gh auth login --scopes "admin:org,repo,read:audit_log"
```

## Evidence by Control Domain

### 1. Code Change Management

**Controls:** SOC 2 CC8.1, ISO 27001 A.14.2.x, NIST PR.IP-3, PCI DSS 6.5, CIS 16.x

| Evidence | Command | Refresh |
|----------|---------|---------|
| Branch protection rules | `gh api repos/{owner}/{repo}/branches/main/protection` | Monthly |
| Required reviewers | `gh api repos/{owner}/{repo}/branches/main/protection/required_pull_request_reviews` | Monthly |
| Status checks | `gh api repos/{owner}/{repo}/branches/main/protection/required_status_checks` | Monthly |
| Signed commits enforcement | `gh api repos/{owner}/{repo}/branches/main/protection/required_signatures` | Quarterly |
| Recent merged PRs (audit trail) | `gh pr list --repo {owner}/{repo} --state merged --limit 50 --json number,title,author,mergedAt,reviewDecision` | Monthly |
| PR without review (violations) | `gh pr list --repo {owner}/{repo} --state merged --json number,title,reviewDecision --jq '.[] \| select(.reviewDecision != "APPROVED")'` | Weekly |

**Key checks:**
- Branch protection enabled on main/production branches
- At least 1 required reviewer for PRs
- Status checks required before merge (CI/CD must pass)
- Force push disabled on protected branches
- No direct commits to main (all changes via PRs)
- Dismiss stale reviews on new pushes enabled

**Sample branch protection evidence:**
```json
{
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true
  },
  "required_status_checks": {
    "strict": true,
    "contexts": ["ci/tests", "security/scan"]
  },
  "enforce_admins": { "enabled": true },
  "allow_force_pushes": { "enabled": false },
  "allow_deletions": { "enabled": false }
}
```

### 2. Access Control

**Controls:** SOC 2 CC6.1–CC6.3, ISO 27001 A.9.x, NIST PR.AC-1/PR.AC-4, CIS 5.x/6.x

| Evidence | Command | Refresh |
|----------|---------|---------|
| Org members | `gh api orgs/{org}/members --paginate --jq '.[].login'` | Monthly |
| Org owners (admins) | `gh api orgs/{org}/members?role=admin --jq '.[].login'` | Monthly |
| Outside collaborators | `gh api orgs/{org}/outside_collaborators --paginate --jq '.[].login'` | Monthly |
| 2FA enforcement | `gh api orgs/{org} --jq '.two_factor_requirement_enabled'` | Monthly |
| Members without 2FA | `gh api orgs/{org}/members?filter=2fa_disabled --jq '.[].login'` | Weekly |
| Team membership | `gh api orgs/{org}/teams --paginate --jq '.[].slug' \| xargs -I{} sh -c 'echo "## {}" && gh api orgs/ORG/teams/{}/members --jq ".[].login"'` | Monthly |
| Repository permissions | `gh api repos/{owner}/{repo}/collaborators --jq '.[] \| {login, permissions}'` | Monthly |
| Pending invitations | `gh api orgs/{org}/invitations --jq '.[].login'` | Weekly |
| SSO/SAML status | `gh api orgs/{org} --jq '.plan'` (Enterprise) | Quarterly |
| Deploy keys | `gh api repos/{owner}/{repo}/keys --jq '.[] \| {title, read_only, created_at}'` | Quarterly |

**Key checks:**
- 2FA required for all org members
- No members with 2FA disabled
- Org owners limited to necessary personnel (< 5 recommended)
- Outside collaborators reviewed and justified
- Deploy keys are read-only unless write is specifically needed
- SSO/SAML enforced for Enterprise orgs

### 3. Secrets and Vulnerability Management

**Controls:** SOC 2 CC7.1, ISO 27001 A.12.6, NIST DE.CM-8, PCI DSS 6.x, CIS 7.x/16.x

| Evidence | Command | Refresh |
|----------|---------|---------|
| Dependabot alerts | `gh api repos/{owner}/{repo}/dependabot/alerts?state=open --jq '.[].security_advisory.severity'` | Weekly |
| Dependabot alerts (critical) | `gh api repos/{owner}/{repo}/dependabot/alerts?severity=critical&state=open` | Daily |
| Code scanning alerts | `gh api repos/{owner}/{repo}/code-scanning/alerts?state=open` | Weekly |
| Secret scanning alerts | `gh api repos/{owner}/{repo}/secret-scanning/alerts?state=open` | Weekly |
| Dependabot config exists | `gh api repos/{owner}/{repo}/contents/.github/dependabot.yml --jq '.name'` | Quarterly |
| Security policy exists | `gh api repos/{owner}/{repo}/contents/SECURITY.md --jq '.name'` | Quarterly |

**Key checks:**
- Dependabot enabled on all repositories
- No critical/high Dependabot alerts open > 30 days
- Code scanning (CodeQL or equivalent) enabled
- Secret scanning enabled with push protection
- No active secret scanning alerts
- SECURITY.md present in repositories

### 4. Audit Logging

**Controls:** SOC 2 CC7.2, ISO 27001 A.12.4.x, NIST DE.AE-3, HIPAA §164.312(b), CIS 8.x

| Evidence | Command | Refresh |
|----------|---------|---------|
| Audit log (recent) | `gh api orgs/{org}/audit-log?per_page=100 --jq '.[] \| {action, actor, created_at}'` | Monthly |
| Audit log (specific action) | `gh api "orgs/{org}/audit-log?phrase=action:repo.destroy&per_page=100"` | Monthly |
| Member changes | `gh api "orgs/{org}/audit-log?phrase=action:org.add_member+action:org.remove_member"` | Monthly |
| Permission changes | `gh api "orgs/{org}/audit-log?phrase=action:team.add_member+action:team.remove_member"` | Monthly |
| Webhook deliveries | `gh api repos/{owner}/{repo}/hooks --jq '.[] \| {id, config.url, active, events}'` | Quarterly |

**Note:** Full audit log access requires GitHub Enterprise. Organization-level audit log is available on GitHub Team and Enterprise plans.

### 5. CI/CD Pipeline Security

**Controls:** SOC 2 CC8.1, ISO 27001 A.14.2.x, NIST PR.IP-3, PCI DSS 6.5

| Evidence | Command | Refresh |
|----------|---------|---------|
| Workflow files | `gh api repos/{owner}/{repo}/contents/.github/workflows --jq '.[].name'` | Quarterly |
| Actions permissions | `gh api repos/{owner}/{repo}/actions/permissions` | Quarterly |
| Org-level runner groups | `gh api orgs/{org}/actions/runner-groups` | Quarterly |
| Secrets (names only) | `gh api repos/{owner}/{repo}/actions/secrets --jq '.secrets[].name'` | Quarterly |
| Environment protections | `gh api repos/{owner}/{repo}/environments --jq '.environments[] \| {name, protection_rules}'` | Quarterly |
| Recent workflow runs | `gh run list --repo {owner}/{repo} --limit 20 --json name,status,conclusion,createdAt` | Monthly |

**Key checks:**
- GitHub Actions restricted to allowed actions (not `actions: write` for all)
- Secrets stored in GitHub Secrets (not hardcoded in workflows)
- Production deployments use environment protection rules (required reviewers)
- Self-hosted runners use runner groups with org-level restrictions
- Workflows pin actions to SHA (not tags) for supply chain security

### 6. Repository Configuration

**Controls:** SOC 2 CC6.1, ISO 27001 A.8.x/A.9.x, NIST PR.AC-4

| Evidence | Command | Refresh |
|----------|---------|---------|
| Repository visibility | `gh repo list {org} --json name,visibility --limit 100` | Monthly |
| Private repos with public forks | `gh api repos/{owner}/{repo} --jq '{visibility, allow_forking}'` | Quarterly |
| Default branch | `gh api repos/{owner}/{repo} --jq '.default_branch'` | Quarterly |
| Topics/classification | `gh api repos/{owner}/{repo}/topics --jq '.names'` | Quarterly |
| Archive status (stale repos) | `gh repo list {org} --json name,isArchived,pushedAt --limit 200` | Quarterly |

## Bulk Collection Across All Repos

```bash
#!/bin/bash
# Collect branch protection evidence for all repos in an org
ORG="myorg"
DATE=$(date +%Y-%m-%d)
OUT=~/.openclaw/grc/evidence/automated/github-$DATE
mkdir -p $OUT

gh repo list $ORG --json name,visibility,defaultBranchRef --limit 200 > $OUT/repos.json

# Branch protection for each repo
jq -r '.[].name' $OUT/repos.json | while read repo; do
  gh api "repos/$ORG/$repo/branches/main/protection" 2>/dev/null > "$OUT/branch-protection-$repo.json"
done

# Org-wide settings
gh api "orgs/$ORG" > $OUT/org-settings.json
gh api "orgs/$ORG/members?filter=2fa_disabled" > $OUT/members-no-2fa.json
gh api "orgs/$ORG/outside_collaborators" --paginate > $OUT/outside-collaborators.json

echo "Evidence collected to $OUT"
```

## Suggested Refresh Schedule

| Frequency | Evidence Types |
|-----------|---------------|
| Daily | Critical Dependabot alerts, secret scanning alerts |
| Weekly | Vulnerability alerts (all severities), 2FA compliance, PRs without review |
| Monthly | Access lists (members, collaborators, teams), audit log, branch protection |
| Quarterly | Repository configs, CI/CD settings, deploy keys, webhook inventory |

## Evidence Validity

Set `--valid-until` based on evidence type:
- **Access snapshots** (members, permissions): 30 days
- **Configuration evidence** (branch protection, repo settings): 90 days
- **Vulnerability scans** (Dependabot, CodeQL): 30 days
- **Audit log exports**: 90 days
