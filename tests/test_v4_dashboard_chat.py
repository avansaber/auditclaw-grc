"""Tests for V4 generate-dashboard chat action (db_query.py) — 8 tests.

Tests the new generate-dashboard action that provides a text summary
suitable for chat display plus structured data for programmatic use.
"""

import json
import os
import sqlite3
import tempfile

import pytest
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))

from conftest import run_script

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
INIT_DB_SCRIPT = os.path.join(SCRIPTS_DIR, "init_db.py")
MIGRATE_V3_SCRIPT = os.path.join(SCRIPTS_DIR, "migrate_v3.py")
MIGRATE_V4_SCRIPT = os.path.join(SCRIPTS_DIR, "migrate_v4.py")
DB_QUERY_SCRIPT = os.path.join(SCRIPTS_DIR, "db_query.py")


def _get_v4_db(db_path):
    run_script(INIT_DB_SCRIPT, db_path=db_path)
    run_script(MIGRATE_V3_SCRIPT, db_path=db_path)
    run_script(MIGRATE_V4_SCRIPT, db_path=db_path)


def _run_action(action, db_path, extra_args=None):
    args = ["--action", action]
    if extra_args:
        args.extend(extra_args)
    result, stderr, code = run_script(DB_QUERY_SCRIPT, args=args, db_path=db_path)
    return result, stderr, code


def _seed_full_data(db_path):
    """Seed database with comprehensive data for dashboard testing."""
    conn = sqlite3.connect(db_path)

    # Activate SOC2
    conn.close()
    _run_action("activate-framework", db_path, ["--slug", "soc2"])
    conn = sqlite3.connect(db_path)

    # Add compliance scores
    conn.execute(
        "INSERT INTO compliance_scores (framework_slug, score, calculated_at) VALUES (?, ?, datetime('now'))",
        ("soc2", 72.3)
    )

    # Add evidence (mix of fresh, expiring, expired)
    conn.execute(
        "INSERT INTO evidence (title, type, source, status, uploaded_at) VALUES (?, ?, ?, ?, datetime('now'))",
        ("AWS Config Report", "automated", "aws", "active")
    )
    conn.execute(
        "INSERT INTO evidence (title, type, source, status, uploaded_at, valid_until) VALUES (?, ?, ?, ?, datetime('now'), datetime('now', '+15 days'))",
        ("Expiring Cert", "manual", "user", "active")
    )
    conn.execute(
        "INSERT INTO evidence (title, type, source, status, uploaded_at, valid_until) VALUES (?, ?, ?, ?, datetime('now'), datetime('now', '-1 day'))",
        ("Expired Policy", "manual", "user", "active")
    )

    # Add risks (including high-severity ones)
    conn.execute(
        "INSERT INTO risks (title, likelihood, impact, status) VALUES (?, ?, ?, ?)",
        ("Data breach risk", 4, 5, "open")
    )
    conn.execute(
        "INSERT INTO risks (title, likelihood, impact, status) VALUES (?, ?, ?, ?)",
        ("Low risk item", 1, 2, "open")
    )
    conn.execute(
        "INSERT INTO risks (title, likelihood, impact, status) VALUES (?, ?, ?, ?)",
        ("Mitigated risk", 3, 3, "mitigated")
    )

    # Add alerts
    conn.execute(
        "INSERT INTO alerts (title, type, severity, triggered_at) VALUES (?, ?, ?, datetime('now'))",
        ("Score dropped", "score_threshold", "critical")
    )
    conn.execute(
        "INSERT INTO alerts (title, type, severity, triggered_at) VALUES (?, ?, ?, datetime('now'))",
        ("Evidence expiring", "evidence_expiry", "warning")
    )

    # Add integration
    conn.execute(
        "INSERT INTO integrations (provider, name, status) VALUES (?, ?, ?)",
        ("aws", "AWS Prod", "active")
    )

    # Set some control maturity levels
    conn.execute("UPDATE controls SET maturity_level = 'managed' WHERE rowid <= 3")
    conn.execute("UPDATE controls SET maturity_level = 'initial' WHERE rowid BETWEEN 4 AND 6")
    conn.execute("UPDATE controls SET maturity_level = 'defined' WHERE rowid BETWEEN 7 AND 8")

    conn.commit()
    conn.close()


class TestGenerateDashboardAction:
    """Test generate-dashboard db_query action."""

    def test_basic_output_structure(self):
        """Test that generate-dashboard returns expected JSON structure."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _seed_full_data(db_path)

            result, stderr, code = _run_action("generate-dashboard", db_path)
            assert code == 0, f"Action failed: {stderr}"
            assert result["status"] == "ok"

            # Verify all expected keys
            assert "overall_score" in result
            assert "score_indicator" in result
            assert "frameworks_count" in result
            assert "framework_scores" in result
            assert "risks" in result
            assert "evidence" in result
            assert "alerts" in result
            assert "active_incidents" in result
            assert "maturity" in result
            assert "integrations" in result
            assert "dashboard_url" in result
            assert "text_summary" in result
            assert "generated_at" in result
        finally:
            os.unlink(db_path)

    def test_text_summary_present_and_readable(self):
        """Test that text_summary contains meaningful dashboard content."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _seed_full_data(db_path)

            result, stderr, code = _run_action("generate-dashboard", db_path)
            assert code == 0

            summary = result["text_summary"]
            assert isinstance(summary, str)
            assert len(summary) > 100  # Should be substantial

            # Key sections must appear in text summary
            assert "GRC COMPLIANCE DASHBOARD" in summary
            assert "OVERALL SCORE" in summary
            assert "FRAMEWORK SCORES" in summary
            assert "RISK OVERVIEW" in summary
            assert "EVIDENCE" in summary
            assert "ALERTS" in summary
            assert "CONTROL MATURITY" in summary
        finally:
            os.unlink(db_path)

    def test_score_values_match(self):
        """Test that scores in the response match seeded data."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _seed_full_data(db_path)

            result, stderr, code = _run_action("generate-dashboard", db_path)
            assert code == 0

            assert result["overall_score"] == 72.3
            assert result["frameworks_count"] == 1
            assert "soc2" in result["framework_scores"]
            assert result["framework_scores"]["soc2"]["score"] == 72.3
        finally:
            os.unlink(db_path)

    def test_risk_counts(self):
        """Test that risk counts are accurate."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _seed_full_data(db_path)

            result, stderr, code = _run_action("generate-dashboard", db_path)
            assert code == 0

            risks = result["risks"]
            assert risks["total"] == 3
            assert risks["high_critical"] == 1  # Only the 4x5 risk
            assert risks["open"] == 2  # Two open, one mitigated
        finally:
            os.unlink(db_path)

    def test_evidence_freshness_counts(self):
        """Test that evidence freshness breakdown is correct."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _seed_full_data(db_path)

            result, stderr, code = _run_action("generate-dashboard", db_path)
            assert code == 0

            ev = result["evidence"]
            assert ev["total"] == 3
            assert ev["fresh"] >= 1    # At least the no-expiry one
            assert ev["expired"] == 1  # The expired one
        finally:
            os.unlink(db_path)

    def test_alert_breakdown(self):
        """Test that alert counts distinguish critical from others."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _seed_full_data(db_path)

            result, stderr, code = _run_action("generate-dashboard", db_path)
            assert code == 0

            alerts = result["alerts"]
            assert alerts["unresolved"] == 2
            assert alerts["critical"] == 1
        finally:
            os.unlink(db_path)

    def test_score_indicator_colors(self):
        """Test score indicator maps correctly: RED/YELLOW/GREEN."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)

            # Activate framework and set different scores
            _run_action("activate-framework", db_path, ["--slug", "soc2"])

            conn = sqlite3.connect(db_path)

            # Test RED (< 60)
            conn.execute(
                "INSERT INTO compliance_scores (framework_slug, score, calculated_at) VALUES ('soc2', 30.0, datetime('now'))"
            )
            conn.commit()
            conn.close()

            result, _, code = _run_action("generate-dashboard", db_path)
            assert code == 0
            assert result["score_indicator"] == "RED"
            assert "RED" in result["text_summary"]

            # Update to YELLOW (60-79)
            conn = sqlite3.connect(db_path)
            conn.execute("DELETE FROM compliance_scores")
            conn.execute(
                "INSERT INTO compliance_scores (framework_slug, score, calculated_at) VALUES ('soc2', 70.0, datetime('now'))"
            )
            conn.commit()
            conn.close()

            result, _, code = _run_action("generate-dashboard", db_path)
            assert code == 0
            assert result["score_indicator"] == "YELLOW"

            # Update to GREEN (>= 80)
            conn = sqlite3.connect(db_path)
            conn.execute("DELETE FROM compliance_scores")
            conn.execute(
                "INSERT INTO compliance_scores (framework_slug, score, calculated_at) VALUES ('soc2', 92.0, datetime('now'))"
            )
            conn.commit()
            conn.close()

            result, _, code = _run_action("generate-dashboard", db_path)
            assert code == 0
            assert result["score_indicator"] == "GREEN"
        finally:
            os.unlink(db_path)

    def test_empty_db_returns_safe_defaults(self):
        """Test that dashboard works with completely empty database."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)

            result, stderr, code = _run_action("generate-dashboard", db_path)
            assert code == 0
            assert result["status"] == "ok"
            assert result["overall_score"] == 0
            assert result["frameworks_count"] == 0
            assert result["risks"]["total"] == 0
            assert result["evidence"]["total"] == 0
            assert result["alerts"]["unresolved"] == 0
            assert result["active_incidents"] == 0

            # Text summary should still be generated
            summary = result["text_summary"]
            assert "GRC COMPLIANCE DASHBOARD" in summary
            assert "OVERALL SCORE: 0%" in summary
            assert result["dashboard_url"]  # URL should always be present
        finally:
            os.unlink(db_path)
