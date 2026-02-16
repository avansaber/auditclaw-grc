"""Tests for db_query.py — Database CRUD operations."""

import json
import sqlite3
from datetime import datetime, timedelta

from conftest import run_script


class TestActivateFramework:
    """T2.1-T2.2: Framework activation."""

    def test_activate_framework_soc2(self, temp_db):
        """T2.1: Activating SOC 2 loads controls."""
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "activate-framework", "--slug", "soc2"],
            db_path=temp_db,
        )
        assert code == 0
        assert result["status"] == "activated"
        assert result["controls_loaded"] >= 40  # SOC 2 has 42 controls
        assert len(result["domains"]) >= 4

    def test_activate_unknown_framework(self, temp_db):
        """T2.2: Unknown framework returns error."""
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "activate-framework", "--slug", "invalid_framework"],
            db_path=temp_db,
        )
        assert code == 1

    def test_activate_framework_idempotent(self, soc2_db):
        """T2.22: Second activation returns already_active, no duplicate controls."""
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "activate-framework", "--slug", "soc2"],
            db_path=soc2_db,
        )
        assert code == 0
        assert result["status"] == "already_active"

        # Verify no duplicate controls
        conn = sqlite3.connect(soc2_db)
        count = conn.execute("SELECT COUNT(*) FROM controls").fetchone()[0]
        conn.close()
        assert count >= 40 and count <= 50  # Should be exactly the same as initial


class TestStatus:
    """T2.3-T2.5: Status queries."""

    def test_status_empty_db(self, temp_db):
        """T2.3: Status on empty DB returns zero counts."""
        result, stderr, code = run_script(
            "db_query.py", ["--action", "status"], db_path=temp_db
        )
        assert code == 0
        assert result["controls"]["total"] == 0

    def test_status_with_data(self, seeded_db):
        """T2.4: Status on seeded DB returns correct counts."""
        result, stderr, code = run_script(
            "db_query.py", ["--action", "status"], db_path=seeded_db
        )
        assert code == 0
        assert result["controls"]["total"] >= 40
        assert result["controls"]["complete"] == 10
        assert result["controls"]["in_progress"] == 5

    def test_status_specific_framework(self, seeded_db):
        """T2.5: Framework-specific status."""
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "status", "--framework", "soc2"],
            db_path=seeded_db,
        )
        assert code == 0
        assert result["framework"] == "soc2"


class TestAddControl:
    """T2.6-T2.7: Adding controls."""

    def test_add_control(self, soc2_db):
        """T2.6: Adding a custom control."""
        result, stderr, code = run_script(
            "db_query.py",
            [
                "--action", "add-control",
                "--title", "Custom MFA Enforcement",
                "--priority", "5",
                "--category", "Access Control",
            ],
            db_path=soc2_db,
        )
        assert code == 0
        assert result["status"] == "created"
        assert result["id"] > 0

    def test_add_control_duplicate(self, soc2_db):
        """T2.7: Adding same control twice doesn't crash."""
        for _ in range(2):
            result, stderr, code = run_script(
                "db_query.py",
                ["--action", "add-control", "--title", "Duplicate Test", "--control-id", "DUP1"],
                db_path=soc2_db,
            )
        # Second should either succeed with new ID or error gracefully
        assert code == 0 or "error" in (result or {}).get("status", "")


class TestUpdateControl:
    """T2.8-T2.9, T2.23-T2.25: Updating controls."""

    def test_update_control(self, seeded_db):
        """T2.8: Update control status."""
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "update-control", "--id", "1", "--status", "complete"],
            db_path=seeded_db,
        )
        assert code == 0
        assert result["status"] == "updated"

    def test_update_nonexistent(self, seeded_db):
        """T2.9: Update nonexistent control returns error."""
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "update-control", "--id", "99999", "--status", "complete"],
            db_path=seeded_db,
        )
        assert code == 1 or result.get("status") == "error"

    def test_update_control_by_control_id(self, soc2_db):
        """T2.23: Update by control_id code (CC1.1)."""
        result, stderr, code = run_script(
            "db_query.py",
            [
                "--action", "update-control",
                "--control-id", "CC1.1",
                "--status", "complete",
            ],
            db_path=soc2_db,
        )
        assert code == 0
        assert result["status"] == "updated"

        # Verify in DB
        conn = sqlite3.connect(soc2_db)
        row = conn.execute(
            "SELECT status FROM controls WHERE control_id = 'CC1.1'"
        ).fetchone()
        conn.close()
        assert row[0] == "complete"

    def test_update_control_batch(self, soc2_db):
        """T2.24: Batch update --id 1,2,3."""
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "update-control", "--id", "1,2,3", "--status", "complete"],
            db_path=soc2_db,
        )
        assert code == 0
        assert result["updated_count"] == 3

    def test_update_control_nonexistent_control_id(self, soc2_db):
        """T2.25: Invalid control_id returns error."""
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "update-control", "--control-id", "INVALID_CODE", "--status", "complete"],
            db_path=soc2_db,
        )
        assert code == 1 or result.get("status") == "error"


class TestListControls:
    """T2.10-T2.12: Listing controls."""

    def test_list_controls_all(self, seeded_db):
        """T2.10: List all controls."""
        result, stderr, code = run_script(
            "db_query.py", ["--action", "list-controls"], db_path=seeded_db
        )
        assert code == 0
        assert result["count"] >= 40

    def test_list_controls_filtered(self, seeded_db):
        """T2.11: Filter by status."""
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "list-controls", "--status", "complete"],
            db_path=seeded_db,
        )
        assert code == 0
        assert result["count"] == 10
        assert all(c["status"] == "complete" for c in result["controls"])

    def test_list_controls_overdue(self, soc2_db):
        """T2.12: List overdue controls."""
        # Set a control with past due date
        conn = sqlite3.connect(soc2_db)
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        conn.execute("UPDATE controls SET due_date = ?, status = 'in_progress' WHERE rowid = 1", (yesterday,))
        conn.commit()
        conn.close()

        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "list-controls", "--overdue"],
            db_path=soc2_db,
        )
        assert code == 0
        assert result["count"] >= 1


class TestEvidence:
    """T2.13-T2.14, T2.26, T2.34-T2.36: Evidence operations."""

    def test_add_evidence(self, soc2_db):
        """T2.13: Add evidence linked to controls."""
        result, stderr, code = run_script(
            "db_query.py",
            [
                "--action", "add-evidence",
                "--title", "AWS IAM Policy Export",
                "--control-ids", "1,2",
                "--type", "automated",
                "--source", "aws",
                "--valid-until", "2027-01-01",
            ],
            db_path=soc2_db,
        )
        assert code == 0
        assert result["status"] == "created"
        assert len(result["linked_controls"]) == 2

    def test_list_evidence_expiring(self, soc2_db):
        """T2.14: List evidence expiring within 7 days."""
        # Add expiring evidence
        conn = sqlite3.connect(soc2_db)
        expiry = (datetime.now() + timedelta(days=5)).isoformat()
        conn.execute(
            "INSERT INTO evidence (title, status, valid_until, type) VALUES (?, 'active', ?, 'manual')",
            ("Expiring Evidence", expiry),
        )
        conn.commit()
        conn.close()

        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "list-evidence", "--expiring-within", "7"],
            db_path=soc2_db,
        )
        assert code == 0
        assert result["count"] >= 1

    def test_update_evidence_status_transition(self, soc2_db):
        """T2.26: Update evidence status active → expired."""
        # Add evidence first
        conn = sqlite3.connect(soc2_db)
        conn.execute(
            "INSERT INTO evidence (title, status, type) VALUES ('Test Evidence', 'active', 'manual')"
        )
        conn.commit()
        eid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()

        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "update-evidence", "--id", str(eid), "--status", "expired"],
            db_path=soc2_db,
        )
        assert code == 0
        assert result["status"] == "updated"

    def test_evidence_without_expiry(self, soc2_db):
        """T2.34: Evidence without valid_until never appears in expiring list."""
        conn = sqlite3.connect(soc2_db)
        conn.execute(
            "INSERT INTO evidence (title, status, type) VALUES ('No Expiry', 'active', 'manual')"
        )
        conn.commit()
        conn.close()

        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "list-evidence", "--expiring-within", "30"],
            db_path=soc2_db,
        )
        assert code == 0
        titles = [e["title"] for e in result["evidence"]]
        assert "No Expiry" not in titles

    def test_evidence_exactly_30_days(self, soc2_db):
        """T2.35: Evidence expiring in exactly 30 days IS counted as expiring soon."""
        conn = sqlite3.connect(soc2_db)
        expiry = (datetime.now() + timedelta(days=30)).isoformat()
        conn.execute(
            "INSERT INTO evidence (title, status, valid_until, type) VALUES ('30 Day Evidence', 'active', ?, 'manual')",
            (expiry,),
        )
        conn.commit()
        conn.close()

        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "list-evidence", "--expiring-within", "30"],
            db_path=soc2_db,
        )
        assert code == 0
        titles = [e["title"] for e in result["evidence"]]
        assert "30 Day Evidence" in titles


class TestRisks:
    """T2.15-T2.17: Risk operations."""

    def test_add_risk(self, soc2_db):
        """T2.15: Add risk with score calculation."""
        result, stderr, code = run_script(
            "db_query.py",
            [
                "--action", "add-risk",
                "--title", "Unpatched servers",
                "--likelihood", "3",
                "--impact", "4",
                "--category", "security",
            ],
            db_path=soc2_db,
        )
        assert code == 0
        assert result["score"] == 12
        assert result["level"] == "medium"

    def test_add_risk_validation(self, soc2_db):
        """T2.16: Likelihood out of range returns error."""
        result, stderr, code = run_script(
            "db_query.py",
            [
                "--action", "add-risk",
                "--title", "Bad risk",
                "--likelihood", "6",
                "--impact", "4",
            ],
            db_path=soc2_db,
        )
        assert code == 1 or result.get("status") == "error"

    def test_list_risks_by_score(self, soc2_db):
        """T2.17: Filter risks by min score."""
        # Add a high risk
        run_script(
            "db_query.py",
            ["--action", "add-risk", "--title", "High Risk", "--likelihood", "5", "--impact", "4"],
            db_path=soc2_db,
        )
        # Add a low risk
        run_script(
            "db_query.py",
            ["--action", "add-risk", "--title", "Low Risk", "--likelihood", "1", "--impact", "2"],
            db_path=soc2_db,
        )

        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "list-risks", "--min-score", "10"],
            db_path=soc2_db,
        )
        assert code == 0
        assert all(r["score"] >= 10 for r in result["risks"])


class TestVendors:
    """T2.18: Vendor operations."""

    def test_add_vendor(self, soc2_db):
        """T2.18: Add vendor."""
        result, stderr, code = run_script(
            "db_query.py",
            [
                "--action", "add-vendor",
                "--name", "AWS",
                "--criticality", "critical",
            ],
            db_path=soc2_db,
        )
        assert code == 0
        assert result["status"] == "created"
        assert result["criticality"] == "critical"


class TestIncidents:
    """T2.19, T2.27-T2.28: Incident operations."""

    def test_add_incident(self, soc2_db):
        """T2.19: Add incident."""
        result, stderr, code = run_script(
            "db_query.py",
            [
                "--action", "add-incident",
                "--title", "Data breach via API key",
                "--type", "security_breach",
                "--severity", "critical",
            ],
            db_path=soc2_db,
        )
        assert code == 0
        assert result["status"] == "created"
        assert result["severity"] == "critical"

    def test_update_incident_status_workflow(self, soc2_db):
        """T2.27: Incident status workflow detected → investigating → resolved."""
        # Create incident
        result, _, _ = run_script(
            "db_query.py",
            ["--action", "add-incident", "--title", "Test Incident", "--severity", "high"],
            db_path=soc2_db,
        )
        incident_id = str(result["id"])

        # Update to investigating
        result, _, code = run_script(
            "db_query.py",
            ["--action", "update-incident", "--id", incident_id, "--status", "investigating"],
            db_path=soc2_db,
        )
        assert code == 0

        # Update to resolved
        result, _, code = run_script(
            "db_query.py",
            ["--action", "update-incident", "--id", incident_id, "--status", "resolved"],
            db_path=soc2_db,
        )
        assert code == 0

        # Verify resolved_at is set
        conn = sqlite3.connect(soc2_db)
        row = conn.execute("SELECT resolved_at FROM incidents WHERE id = ?", (int(incident_id),)).fetchone()
        conn.close()
        assert row[0] is not None

    def test_list_incidents_by_severity(self, soc2_db):
        """T2.28: Filter incidents by severity."""
        run_script(
            "db_query.py",
            ["--action", "add-incident", "--title", "Critical", "--severity", "critical"],
            db_path=soc2_db,
        )
        run_script(
            "db_query.py",
            ["--action", "add-incident", "--title", "Low", "--severity", "low"],
            db_path=soc2_db,
        )

        result, _, code = run_script(
            "db_query.py",
            ["--action", "list-incidents", "--severity", "critical"],
            db_path=soc2_db,
        )
        assert code == 0
        assert all(i["severity"] == "critical" for i in result["incidents"])


class TestPolicies:
    """T2.21: Policy operations."""

    def test_add_policy(self, soc2_db):
        """T2.21: Add policy with default draft status."""
        result, stderr, code = run_script(
            "db_query.py",
            [
                "--action", "add-policy",
                "--title", "Information Security Policy",
                "--type", "information_security",
            ],
            db_path=soc2_db,
        )
        assert code == 0
        assert result["status"] == "created"
        assert result["policy_status"] == "draft"


class TestGapAnalysis:
    """T2.20, T2.32-T2.33: Gap analysis."""

    def test_gap_analysis(self, seeded_db):
        """T2.20: Gap analysis identifies not_started controls."""
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "gap-analysis", "--framework", "soc2"],
            db_path=seeded_db,
        )
        assert code == 0
        assert result["gap_count"] > 0
        assert result["summary"]["not_started"] > 0
        assert result["readiness_percent"] > 0

    def test_gap_analysis_effort_estimation(self, seeded_db):
        """T2.32: Gaps include effort days and remediation phase."""
        result, _, _ = run_script(
            "db_query.py",
            ["--action", "gap-analysis", "--framework", "soc2"],
            db_path=seeded_db,
        )
        for gap in result["gaps"]:
            assert "effort_days" in gap
            assert "remediation_phase" in gap
            assert gap["remediation_phase"] in ("immediate", "short_term", "medium_term")

    def test_gap_analysis_priority_scoring(self, seeded_db):
        """T2.33: Gaps sorted by priority_score descending."""
        result, _, _ = run_script(
            "db_query.py",
            ["--action", "gap-analysis", "--framework", "soc2"],
            db_path=seeded_db,
        )
        scores = [g["priority_score"] for g in result["gaps"]]
        assert scores == sorted(scores, reverse=True)


class TestScoreHistory:
    """T2.29: Score history."""

    def test_score_history_returns_trend(self, soc2_db):
        """T2.29: Multiple stored scores produce correct trend."""
        conn = sqlite3.connect(soc2_db)
        # Insert two score records
        conn.execute(
            "INSERT INTO compliance_scores (framework_slug, score, total_controls, healthy_controls, at_risk_controls, critical_controls, calculated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("soc2", 60.0, 42, 20, 10, 12, (datetime.now() - timedelta(days=7)).isoformat()),
        )
        conn.execute(
            "INSERT INTO compliance_scores (framework_slug, score, total_controls, healthy_controls, at_risk_controls, critical_controls, calculated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("soc2", 75.0, 42, 30, 8, 4, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

        result, _, code = run_script(
            "db_query.py",
            ["--action", "score-history", "--framework", "soc2"],
            db_path=soc2_db,
        )
        assert code == 0
        assert result["data_points"] == 2
        assert result["trend"] == "improving"


class TestMappings:
    """T2.30: Cross-framework mappings."""

    def test_list_mappings_cross_framework(self, soc2_db):
        """T2.30: SOC 2 → ISO 27001 mappings returned."""
        result, _, code = run_script(
            "db_query.py",
            [
                "--action", "list-mappings",
                "--source-framework", "soc2",
                "--target-framework", "iso27001",
            ],
            db_path=soc2_db,
        )
        assert code == 0
        assert result["count"] > 0
        # Verify mappings reference valid framework slugs
        for m in result["mappings"]:
            assert m["source_framework"] == "soc2"
            assert m["target_framework"] == "iso27001"


class TestDeactivateFramework:
    """T2.31: Framework deactivation."""

    def test_deactivate_framework(self, soc2_db):
        """T2.31: Framework marked inactive, controls preserved."""
        result, _, code = run_script(
            "db_query.py",
            ["--action", "deactivate-framework", "--slug", "soc2", "--reason", "Testing"],
            db_path=soc2_db,
        )
        assert code == 0
        assert result["status"] == "deactivated"

        # Controls should still exist
        conn = sqlite3.connect(soc2_db)
        count = conn.execute("SELECT COUNT(*) FROM controls").fetchone()[0]
        fw_status = conn.execute("SELECT status FROM frameworks WHERE slug = 'soc2'").fetchone()[0]
        conn.close()

        assert count > 0  # Controls preserved
        assert fw_status == "inactive"
