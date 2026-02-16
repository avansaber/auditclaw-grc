"""Tests for V4 Canvas GRC Dashboard generation (5 tests)."""

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
MIGRATE_V3_SCRIPT = os.path.join(SCRIPTS_DIR, "migrate_v3.py")
MIGRATE_V4_SCRIPT = os.path.join(SCRIPTS_DIR, "migrate_v4.py")
INIT_DB_SCRIPT = os.path.join(SCRIPTS_DIR, "init_db.py")
DB_QUERY_SCRIPT = os.path.join(SCRIPTS_DIR, "db_query.py")
DASHBOARD_SCRIPT = os.path.join(SCRIPTS_DIR, "generate_dashboard.py")


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


def _seed_data(db_path):
    """Seed database with sample data for dashboard testing."""
    conn = sqlite3.connect(db_path)

    # Activate SOC2 framework via action
    conn.close()
    _run_action("activate-framework", db_path, ["--slug", "soc2"])
    conn = sqlite3.connect(db_path)

    # Add a compliance score
    conn.execute(
        "INSERT INTO compliance_scores (framework_slug, score, calculated_at) VALUES (?, ?, datetime('now'))",
        ("soc2", 78.5)
    )

    # Add evidence
    conn.execute(
        "INSERT INTO evidence (title, type, source, status, uploaded_at) VALUES (?, ?, ?, ?, datetime('now'))",
        ("AWS Config Report", "automated", "aws", "active")
    )
    conn.execute(
        "INSERT INTO evidence (title, type, source, status, uploaded_at, valid_until) VALUES (?, ?, ?, ?, datetime('now'), datetime('now', '-1 day'))",
        ("Expired Cert", "manual", "user", "active")
    )

    # Add risk
    conn.execute(
        "INSERT INTO risks (title, likelihood, impact, status) VALUES (?, ?, ?, ?)",
        ("Data breach", 3, 4, "open")
    )

    # Add alert
    conn.execute(
        "INSERT INTO alerts (title, type, severity, triggered_at) VALUES (?, ?, ?, datetime('now'))",
        ("Score dropped", "score_threshold", "warning")
    )

    # Add integration
    conn.execute(
        "INSERT INTO integrations (provider, name, status) VALUES (?, ?, ?)",
        ("aws", "AWS Prod", "active")
    )

    conn.commit()
    conn.close()


class TestDashboardGeneration:
    """Test generate_dashboard.py script."""

    def test_dashboard_generates_html(self):
        """Test that dashboard generates valid HTML file."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            output_path = f.name
        try:
            _get_v4_db(db_path)
            _seed_data(db_path)

            result, stderr, code = run_script(
                DASHBOARD_SCRIPT,
                args=["--output", output_path],
                db_path=db_path,
            )
            assert code == 0, f"Dashboard generation failed: {stderr}"
            assert result["status"] == "ok"
            assert result["output"] == output_path

            # Verify HTML file exists and has content
            assert os.path.exists(output_path)
            with open(output_path) as fh:
                html = fh.read()
            assert "<!DOCTYPE html>" in html
            assert "GRC Compliance Dashboard" in html
        finally:
            os.unlink(db_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_dashboard_data_accuracy(self):
        """Test that dashboard JSON output reflects seeded data."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            output_path = f.name
        try:
            _get_v4_db(db_path)
            _seed_data(db_path)

            result, stderr, code = run_script(
                DASHBOARD_SCRIPT,
                args=["--output", output_path],
                db_path=db_path,
            )
            assert code == 0
            # Should reflect 1 framework scored
            assert result["frameworks"] >= 1
            # Should report the score we seeded
            assert result["overall_score"] == 78.5
            # Should report alerts
            assert result["alerts"] == 1
            # Should report evidence items
            assert result["evidence_items"] >= 2
        finally:
            os.unlink(db_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_dashboard_empty_db(self):
        """Test dashboard works with empty database (no data seeded)."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            output_path = f.name
        try:
            _get_v4_db(db_path)

            result, stderr, code = run_script(
                DASHBOARD_SCRIPT,
                args=["--output", output_path],
                db_path=db_path,
            )
            assert code == 0
            assert result["status"] == "ok"
            assert result["overall_score"] == 0
            assert result["frameworks"] == 0
            assert result["alerts"] == 0

            # HTML should still be valid
            with open(output_path) as fh:
                html = fh.read()
            assert "<!DOCTYPE html>" in html
        finally:
            os.unlink(db_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_dashboard_html_sections(self):
        """Test that all dashboard sections are present in HTML."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            output_path = f.name
        try:
            _get_v4_db(db_path)
            _seed_data(db_path)

            result, stderr, code = run_script(
                DASHBOARD_SCRIPT,
                args=["--output", output_path],
                db_path=db_path,
            )
            assert code == 0

            with open(output_path) as fh:
                html = fh.read()

            # Verify all sections present
            assert "Framework Scores" in html
            assert "Risk Heat Map" in html
            assert "Evidence Freshness" in html
            assert "Unresolved Alerts" in html
            assert "Integration Health" in html
            assert "Control Maturity" in html
            assert "Quick Stats" in html
            assert "Quick Actions" in html
            # Auto-reload script
            assert "setTimeout" in html
            assert "300000" in html
        finally:
            os.unlink(db_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_dashboard_creates_output_dir(self):
        """Test that dashboard auto-creates output directory if missing."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        output_dir = tempfile.mkdtemp()
        nested_path = os.path.join(output_dir, "sub", "nested", "dashboard.html")
        try:
            _get_v4_db(db_path)

            result, stderr, code = run_script(
                DASHBOARD_SCRIPT,
                args=["--output", nested_path],
                db_path=db_path,
            )
            assert code == 0
            assert os.path.exists(nested_path)

            with open(nested_path) as fh:
                html = fh.read()
            assert "<!DOCTYPE html>" in html
        finally:
            os.unlink(db_path)
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)

    def test_dashboard_includes_text_summary(self):
        """Test that dashboard JSON output includes text_summary and dashboard_url."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            output_path = f.name
        try:
            _get_v4_db(db_path)
            _seed_data(db_path)

            result, stderr, code = run_script(
                DASHBOARD_SCRIPT,
                args=["--output", output_path],
                db_path=db_path,
            )
            assert code == 0
            assert "text_summary" in result
            assert "dashboard_url" in result
            assert isinstance(result["text_summary"], str)
            assert len(result["text_summary"]) > 50
            assert "GRC COMPLIANCE DASHBOARD" in result["text_summary"]
            assert "OVERALL SCORE" in result["text_summary"]
            assert "http://" in result["dashboard_url"]
        finally:
            os.unlink(db_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

