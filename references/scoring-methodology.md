# Compliance Scoring Methodology

This document describes the algorithm used by `scripts/compliance_score.py` to calculate compliance scores for activated frameworks.

## Overview

The scoring engine evaluates each control in a framework, determines its health status, applies priority-based weighting, and produces a weighted percentage score from 0–100.

## Health Determination

Each control is evaluated using a priority-ordered rule set. The **first matching rule wins**; order matters.

| Priority | Condition | Health | Value | Rationale |
|----------|-----------|--------|-------|-----------|
| 1 | Status = `not_started` | CRITICAL | 0.0 | No implementation effort begun |
| 2 | Has evidence with `valid_until` in the past | CRITICAL | 0.0 | Expired evidence = no current proof |
| 3 | Status = `rejected` | AT_RISK | 0.5 | Implementation was attempted but rejected |
| 4 | Status = `in_progress` | AT_RISK | 0.5 | Work underway but not complete |
| 5 | Status = `complete` AND no linked evidence | AT_RISK | 0.5 | Claim of completion without proof |
| 6 | Status = `complete` AND evidence expiring within 30 days | AT_RISK | 0.5 | Evidence about to lapse |
| 7 | Review date is overdue (past `review_date`) | AT_RISK | 0.5 | Review not conducted on schedule |
| 8 | Status = `awaiting_review` | AT_RISK | 0.5 | Pending approval |
| 9 | Status = `complete` AND has current evidence | HEALTHY | 1.0 | Fully implemented with valid proof |

### Health Values

| Health | Numeric Value | Meaning |
|--------|--------------|---------|
| HEALTHY | 1.0 | Control is fully implemented and evidenced |
| AT_RISK | 0.5 | Control needs attention but has partial implementation |
| CRITICAL | 0.0 | Control provides no compliance value currently |

## Priority Weighting

Controls are weighted by their priority level (1–5). Higher priority = higher weight, so critical controls have more impact on the overall score.

| Priority | Label | Weight Multiplier |
|----------|-------|-------------------|
| P5 | Critical | 2.0x |
| P4 | High | 1.5x |
| P3 | Medium | 1.0x |
| P2 | Low | 0.75x |
| P1 | Informational | 0.5x |

## Score Calculation

### Formula

```
For each control i:
  weighted_value[i] = health_value[i] × priority_weight[i]
  max_possible[i]   = 1.0 × priority_weight[i]

score = (sum(weighted_value) / sum(max_possible)) × 100
```

### Worked Example

| Control | Status | Evidence | Health | Value | Priority | Weight | Weighted | Max |
|---------|--------|----------|--------|-------|----------|--------|----------|-----|
| CC6.1 | complete | valid | HEALTHY | 1.0 | P5 | 2.0 | 2.0 | 2.0 |
| CC6.2 | in_progress | - | AT_RISK | 0.5 | P5 | 2.0 | 1.0 | 2.0 |
| CC1.1 | not_started | - | CRITICAL | 0.0 | P4 | 1.5 | 0.0 | 1.5 |
| CC2.1 | complete | valid | HEALTHY | 1.0 | P3 | 1.0 | 1.0 | 1.0 |
| CC9.2 | complete | expiring in 15d | AT_RISK | 0.5 | P3 | 1.0 | 0.5 | 1.0 |

**Totals:** Weighted sum = 4.5, Max possible = 7.5

**Score** = (4.5 / 7.5) × 100 = **60.00**

**Label:** Fair

## Score Labels

| Range | Label | Interpretation |
|-------|-------|---------------|
| ≥ 90 | Excellent | Audit-ready, minimal gaps |
| ≥ 75 | Good | Strong posture, minor improvements needed |
| ≥ 60 | Fair | Gaps exist, remediation plan recommended |
| ≥ 50 | Needs Attention | Significant gaps, immediate action required |
| < 50 | Critical | Major compliance failures, urgent remediation |

## Trend Calculation

When score history exists (via `--store` flag), the engine compares the current score to the most recent stored score:

| Condition | Trend |
|-----------|-------|
| Current > Previous | `improving` |
| Current = Previous | `stable` |
| Current < Previous | `declining` |
| No previous score | `unknown` |

## Drift Detection

Large score changes trigger alerts:

| Change | Alert Level | Meaning |
|--------|-------------|---------|
| Drop > 10 points | `critical_drift` | Major degradation, likely multiple controls affected |
| Drop > 5 points | `warning_drift` | Notable degradation, investigation recommended |
| Drop ≤ 5 points | (none) | Normal fluctuation |

## Health Distribution

The score output includes a breakdown of controls by health status:

```json
{
  "distribution": {
    "healthy": 25,
    "at_risk": 10,
    "critical": 7
  }
}
```

This helps identify not just the score but the **shape** of compliance. A score of 60 with many AT_RISK controls is very different from 60 with a mix of HEALTHY and CRITICAL.

## Score Storage

When called with `--store`, the score is saved to the `compliance_scores` table:

```sql
INSERT INTO compliance_scores (framework_id, score, label, scored_at)
VALUES (?, ?, ?, datetime('now'));
```

This enables:
- Historical trend charts
- Drift detection over time
- Audit trail of compliance posture

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| Framework with 0 controls | Score = 0.0, label = "Critical" |
| All controls `not_applicable` | Excluded from scoring |
| Evidence with no `valid_until` | Treated as non-expiring (always valid) |
| Multiple evidence per control | Uses the most recently valid evidence |
| Score exactly on boundary (e.g., 75.00) | Rounds to label for that boundary (Good) |

## Implementation

The scoring engine is at `scripts/compliance_score.py`. Usage:

```bash
# Calculate and display score
python3 scripts/compliance_score.py --framework soc2

# Calculate, store, and show trend
python3 scripts/compliance_score.py --framework soc2 --store

# Custom database path
python3 scripts/compliance_score.py --framework soc2 --db-path /path/to/db.sqlite
```
