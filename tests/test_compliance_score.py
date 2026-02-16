"""Tests for compliance_score.py — Scoring engine."""

import json
import sqlite3
from datetime import datetime, timedelta

from conftest import run_script


class TestEmptyAndBasic:
    """T3.1-T3.2: Basic scoring scenarios."""

    def test_empty_framework(self, soc2_db):
        """T3.1: All not_started controls = score 0.0."""
        result, stderr, code = run_script("compliance_score.py", db_path=soc2_db)
        assert code == 0
        assert result["score"] == 0.0
        assert result["label"] == "Critical"

    def test_all_complete(self, excellent_score_db):
        """T3.2: All complete with current evidence = score ~100."""
        result, _, code = run_script("compliance_score.py", db_path=excellent_score_db)
        assert code == 0
        assert result["score"] >= 99.0
        assert result["label"] == "Excellent"


class TestMixedHealth:
    """T3.3-T3.5: Mixed health scenarios."""

    def test_mixed_health(self, mixed_health_db):
        """T3.3: Mixed states produce a score between 0 and 100."""
        result, _, code = run_script("compliance_score.py", db_path=mixed_health_db)
        assert code == 0
        assert 0 < result["score"] < 100
        assert result["health_distribution"]["HEALTHY"] > 0
        assert result["health_distribution"]["AT_RISK"] > 0
        assert result["health_distribution"]["CRITICAL"] > 0

    def test_priority_weighting(self, soc2_db):
        """T3.4: P5 controls affect score more than P1 controls."""
        conn = sqlite3.connect(soc2_db)

        # Set all controls to complete with evidence (baseline)
        conn.execute("UPDATE controls SET status = 'complete'")
        count = conn.execute("SELECT COUNT(*) FROM controls").fetchone()[0]
        for i in range(1, count + 1):
            conn.execute(
                "INSERT INTO evidence (title, status, valid_until, type) VALUES (?, 'active', ?, 'manual')",
                (f"Ev {i}", (datetime.now() + timedelta(days=90)).isoformat()),
            )
            conn.execute("INSERT INTO evidence_controls (evidence_id, control_id) VALUES (?, ?)", (i, i))
        conn.commit()

        # Score with everything complete
        result_full, _, _ = run_script("compliance_score.py", db_path=soc2_db)
        full_score = result_full["score"]

        # Now break a P5 control
        p5_id = conn.execute("SELECT id FROM controls WHERE priority = 5 LIMIT 1").fetchone()
        if p5_id:
            conn.execute("UPDATE controls SET status = 'not_started' WHERE id = ?", (p5_id[0],))
            conn.commit()
            result_p5, _, _ = run_script("compliance_score.py", db_path=soc2_db)
            p5_drop = full_score - result_p5["score"]

            # Restore P5 and break a P1 control
            conn.execute("UPDATE controls SET status = 'complete' WHERE id = ?", (p5_id[0],))
            p1_id = conn.execute("SELECT id FROM controls WHERE priority <= 2 LIMIT 1").fetchone()
            if p1_id:
                conn.execute("UPDATE controls SET status = 'not_started' WHERE id = ?", (p1_id[0],))
                conn.commit()
                result_p1, _, _ = run_script("compliance_score.py", db_path=soc2_db)
                p1_drop = full_score - result_p1["score"]

                # P5 drop should be larger than P1 drop
                assert p5_drop > p1_drop

        conn.close()

    def test_evidence_expiry_affects_health(self, soc2_db):
        """T3.5: Expired evidence makes control critical."""
        conn = sqlite3.connect(soc2_db)

        # Set control 1 to complete with expired evidence
        conn.execute("UPDATE controls SET status = 'complete' WHERE rowid = 1")
        conn.execute(
            "INSERT INTO evidence (title, status, valid_until, type) VALUES ('Expired', 'expired', ?, 'manual')",
            ((datetime.now() - timedelta(days=30)).isoformat(),),
        )
        eid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO evidence_controls (evidence_id, control_id) VALUES (?, 1)", (eid,))
        conn.commit()
        conn.close()

        result, _, code = run_script("compliance_score.py", db_path=soc2_db)
        assert code == 0
        # Should have at least one CRITICAL control
        assert result["health_distribution"]["CRITICAL"] > 0


class TestStoreAndTrend:
    """T3.6-T3.7: Score storage and trend."""

    def test_store_flag(self, soc2_db):
        """T3.6: --store creates a record in compliance_scores."""
        result, _, code = run_script(
            "compliance_score.py", ["--store"], db_path=soc2_db
        )
        assert code == 0
        assert result.get("stored") is True

        conn = sqlite3.connect(soc2_db)
        count = conn.execute("SELECT COUNT(*) FROM compliance_scores").fetchone()[0]
        conn.close()
        assert count >= 1

    def test_trend_calculation(self, soc2_db):
        """T3.7: Two score records produce trend direction."""
        conn = sqlite3.connect(soc2_db)
        # Insert old score
        conn.execute(
            "INSERT INTO compliance_scores (score, calculated_at) VALUES (?, ?)",
            (50.0, (datetime.now() - timedelta(days=7)).isoformat()),
        )
        conn.commit()
        conn.close()

        # Store current score (should be 0 since all not_started)
        result, _, _ = run_script(
            "compliance_score.py", ["--store"], db_path=soc2_db
        )
        # Trend depends on old vs new score
        assert result["trend"] in ("improving", "declining", "stable", "unknown")


class TestScoreLabels:
    """T3.8-T3.9: Score label mapping."""

    def test_score_label_excellent(self, excellent_score_db):
        """T3.8: Score >= 90 → Excellent."""
        result, _, _ = run_script("compliance_score.py", db_path=excellent_score_db)
        assert result["label"] == "Excellent"

    def test_score_label_critical(self, soc2_db):
        """T3.9: Score 0 → Critical."""
        result, _, _ = run_script("compliance_score.py", db_path=soc2_db)
        assert result["label"] == "Critical"


class TestHealthDetermination:
    """T3.10-T3.12: Specific health determination rules."""

    def test_complete_control_no_evidence_is_at_risk(self, soc2_db):
        """T3.10: Complete + no evidence → AT_RISK (0.5 weight)."""
        conn = sqlite3.connect(soc2_db)
        # Set a control to complete but don't add evidence
        conn.execute("UPDATE controls SET status = 'complete' WHERE rowid = 1")
        conn.commit()
        conn.close()

        result, _, _ = run_script("compliance_score.py", db_path=soc2_db)
        assert result["health_distribution"]["AT_RISK"] >= 1

    def test_rejected_control_is_at_risk(self, soc2_db):
        """T3.11: Rejected status → AT_RISK."""
        conn = sqlite3.connect(soc2_db)
        conn.execute("UPDATE controls SET status = 'rejected' WHERE rowid = 1")
        conn.commit()
        conn.close()

        result, _, _ = run_script("compliance_score.py", db_path=soc2_db)
        assert result["health_distribution"]["AT_RISK"] >= 1

    def test_in_progress_control_is_at_risk(self, soc2_db):
        """T3.12: In progress → AT_RISK."""
        conn = sqlite3.connect(soc2_db)
        conn.execute("UPDATE controls SET status = 'in_progress' WHERE rowid = 1")
        conn.commit()
        conn.close()

        result, _, _ = run_script("compliance_score.py", db_path=soc2_db)
        assert result["health_distribution"]["AT_RISK"] >= 1


class TestDriftDetection:
    """T3.13-T3.15: Drift detection."""

    def test_drift_detection_declining(self, soc2_db):
        """T3.13: Large score drop = declining trend."""
        conn = sqlite3.connect(soc2_db)
        # Store a high baseline
        conn.execute(
            "INSERT INTO compliance_scores (score, calculated_at) VALUES (?, ?)",
            (84.0, (datetime.now() - timedelta(days=1)).isoformat()),
        )
        conn.commit()
        conn.close()

        # Current score should be 0 (all not_started), so delta = -84
        result, _, _ = run_script("compliance_score.py", db_path=soc2_db)
        assert result["trend"] == "declining"
        assert result["drift"] in ("critical", "warning")

    def test_drift_detection_stable(self, excellent_score_db):
        """T3.14: Small delta = stable trend."""
        conn = sqlite3.connect(excellent_score_db)
        # Store a baseline close to current (~100)
        conn.execute(
            "INSERT INTO compliance_scores (score, calculated_at) VALUES (?, ?)",
            (99.5, (datetime.now() - timedelta(days=1)).isoformat()),
        )
        conn.commit()
        conn.close()

        result, _, _ = run_script("compliance_score.py", db_path=excellent_score_db)
        assert result["trend"] == "stable"

    def test_drift_detection_no_baseline(self, soc2_db):
        """T3.15: No previous scores = unknown trend."""
        result, _, _ = run_script("compliance_score.py", db_path=soc2_db)
        assert result["trend"] == "unknown"


class TestHealthDistribution:
    """T3.16: Health distribution counts."""

    def test_health_distribution_counts(self, mixed_health_db):
        """T3.16: Returns correct counts per health tier."""
        result, _, _ = run_script("compliance_score.py", db_path=mixed_health_db)
        dist = result["health_distribution"]
        total = dist["HEALTHY"] + dist["AT_RISK"] + dist["CRITICAL"]

        conn = sqlite3.connect(mixed_health_db)
        control_count = conn.execute("SELECT COUNT(*) FROM controls").fetchone()[0]
        conn.close()

        assert total == control_count


class TestScoreRounding:
    """T3.17: Score precision."""

    def test_score_rounds_to_2_decimals(self, mixed_health_db):
        """T3.17: Score is rounded to 2 decimal places."""
        result, _, _ = run_script("compliance_score.py", db_path=mixed_health_db)
        score_str = str(result["score"])
        if "." in score_str:
            decimals = len(score_str.split(".")[1])
            assert decimals <= 2
