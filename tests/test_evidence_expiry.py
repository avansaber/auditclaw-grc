"""T9.x — Evidence expiry checker tests.

Tests the standalone evidence_expiry.py script that runs via cron
to detect expired and expiring evidence.
"""

import json
import os
import subprocess
import tempfile
import sqlite3
from datetime import datetime, timedelta
import pytest

SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts"
)


def run_script(script_name, args=None, expect_error=False):
    """Run a Python script and return parsed output."""
    cmd = ["python3", os.path.join(SCRIPTS_DIR, script_name)]
    if args:
        cmd.extend(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if expect_error:
        return result
    # evidence_expiry returns 1 for alerts, 0 for clean, 2 for error
    if result.returncode == 2:
        raise RuntimeError(f"Script error: {result.stderr}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw_output": result.stdout, "returncode": result.returncode}


def create_test_db():
    """Create a temporary database with evidence table."""
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    # Initialize via init_db.py
    subprocess.run(
        ["python3", os.path.join(SCRIPTS_DIR, "init_db.py"), "--db-path", path],
        capture_output=True, check=True
    )
    return path


def seed_evidence(db_path, title, valid_until, status="approved"):
    """Insert an evidence record directly."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO evidence (title, status, valid_until) VALUES (?, ?, ?)",
        (title, status, valid_until)
    )
    conn.commit()
    conn.close()


class TestNoAlerts:
    """T9.1 — No alerts when all evidence is current."""

    def test_empty_db(self):
        """T9.1a — Empty DB returns ok status."""
        db = create_test_db()
        try:
            result = run_script("evidence_expiry.py", ["--db-path", db])
            assert result["status"] == "ok"
            assert result["summary"]["total_alerts"] == 0
        finally:
            os.unlink(db)

    def test_all_current(self):
        """T9.1b — All evidence within validity returns ok."""
        db = create_test_db()
        try:
            future = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
            seed_evidence(db, "Current evidence 1", future)
            seed_evidence(db, "Current evidence 2", future)
            result = run_script("evidence_expiry.py", ["--db-path", db])
            assert result["status"] == "ok"
            assert result["summary"]["expired_count"] == 0
            assert result["summary"]["expiring_count"] == 0
        finally:
            os.unlink(db)

    def test_no_valid_until(self):
        """T9.1c — Evidence without valid_until is ignored (non-expiring)."""
        db = create_test_db()
        try:
            conn = sqlite3.connect(db)
            conn.execute(
                "INSERT INTO evidence (title, status) VALUES (?, ?)",
                ("No expiry evidence", "approved")
            )
            conn.commit()
            conn.close()
            result = run_script("evidence_expiry.py", ["--db-path", db])
            assert result["status"] == "ok"
        finally:
            os.unlink(db)


class TestExpiredEvidence:
    """T9.2 — Detecting already-expired evidence."""

    def test_expired_detected(self):
        """T9.2a — Expired evidence shows in expired list."""
        db = create_test_db()
        try:
            past = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
            seed_evidence(db, "Expired policy doc", past)
            result = run_script("evidence_expiry.py", ["--db-path", db])
            assert result["status"] == "alerts"
            assert result["summary"]["expired_count"] == 1
            assert result["expired"][0]["title"] == "Expired policy doc"
            assert result["expired"][0]["days_overdue"] >= 9
        finally:
            os.unlink(db)

    def test_multiple_expired(self):
        """T9.2b — Multiple expired items all reported."""
        db = create_test_db()
        try:
            past1 = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
            past2 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            seed_evidence(db, "Recently expired", past1)
            seed_evidence(db, "Long expired", past2)
            result = run_script("evidence_expiry.py", ["--db-path", db])
            assert result["summary"]["expired_count"] == 2
            # Sorted by valid_until ascending — oldest first
            assert result["expired"][0]["title"] == "Long expired"
        finally:
            os.unlink(db)

    def test_already_expired_status_excluded(self):
        """T9.2c — Evidence already marked 'expired' is not re-reported."""
        db = create_test_db()
        try:
            past = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
            seed_evidence(db, "Already handled", past, status="expired")
            result = run_script("evidence_expiry.py", ["--db-path", db])
            assert result["status"] == "ok"
            assert result["summary"]["expired_count"] == 0
        finally:
            os.unlink(db)


class TestExpiringEvidence:
    """T9.3 — Detecting evidence expiring within threshold."""

    def test_expiring_within_threshold(self):
        """T9.3a — Evidence expiring within 30 days detected."""
        db = create_test_db()
        try:
            soon = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
            seed_evidence(db, "Expiring soon", soon)
            result = run_script("evidence_expiry.py", ["--db-path", db, "--days", "30"])
            assert result["status"] == "alerts"
            assert result["summary"]["expiring_count"] == 1
            assert result["expiring_soon"][0]["days_remaining"] >= 14
        finally:
            os.unlink(db)

    def test_custom_threshold(self):
        """T9.3b — Custom threshold (7 days) works."""
        db = create_test_db()
        try:
            in_5_days = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
            in_20_days = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")
            seed_evidence(db, "Within 7 days", in_5_days)
            seed_evidence(db, "Outside 7 days", in_20_days)
            result = run_script("evidence_expiry.py", ["--db-path", db, "--days", "7"])
            assert result["summary"]["expiring_count"] == 1
            assert result["expiring_soon"][0]["title"] == "Within 7 days"
        finally:
            os.unlink(db)

    def test_boundary_exactly_on_threshold(self):
        """T9.3c — Evidence expiring exactly on threshold date is included."""
        db = create_test_db()
        try:
            exact = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            seed_evidence(db, "Exactly 30 days", exact)
            result = run_script("evidence_expiry.py", ["--db-path", db, "--days", "30"])
            assert result["summary"]["expiring_count"] == 1
        finally:
            os.unlink(db)

    def test_rejected_excluded(self):
        """T9.3d — Rejected evidence is not reported as expiring."""
        db = create_test_db()
        try:
            soon = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
            seed_evidence(db, "Rejected evidence", soon, status="rejected")
            result = run_script("evidence_expiry.py", ["--db-path", db])
            assert result["status"] == "ok"
        finally:
            os.unlink(db)


class TestMixedScenarios:
    """T9.4 — Mixed expired and expiring evidence."""

    def test_mixed_expired_and_expiring(self):
        """T9.4a — Both expired and expiring are reported."""
        db = create_test_db()
        try:
            past = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
            soon = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
            future = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
            seed_evidence(db, "Expired one", past)
            seed_evidence(db, "Expiring one", soon)
            seed_evidence(db, "Safe one", future)
            result = run_script("evidence_expiry.py", ["--db-path", db])
            assert result["summary"]["expired_count"] == 1
            assert result["summary"]["expiring_count"] == 1
            assert result["summary"]["total_alerts"] == 2
        finally:
            os.unlink(db)


class TestOutputFormats:
    """T9.5 — Output format options."""

    def test_json_format(self):
        """T9.5a — JSON output is valid JSON."""
        db = create_test_db()
        try:
            result = run_script("evidence_expiry.py", ["--db-path", db, "--format", "json"])
            assert "status" in result
            assert "summary" in result
        finally:
            os.unlink(db)

    def test_text_format(self):
        """T9.5b — Text format produces readable output."""
        db = create_test_db()
        try:
            past = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
            seed_evidence(db, "Expired doc", past)
            r = subprocess.run(
                ["python3", os.path.join(SCRIPTS_DIR, "evidence_expiry.py"),
                 "--db-path", db, "--format", "text"],
                capture_output=True, text=True
            )
            assert "Evidence Expiry Alert" in r.stdout
            assert "EXPIRED" in r.stdout
            assert "Expired doc" in r.stdout
        finally:
            os.unlink(db)

    def test_text_format_clean(self):
        """T9.5c — Text format with no alerts shows clean message."""
        db = create_test_db()
        try:
            r = subprocess.run(
                ["python3", os.path.join(SCRIPTS_DIR, "evidence_expiry.py"),
                 "--db-path", db, "--format", "text"],
                capture_output=True, text=True
            )
            assert "All evidence is current" in r.stdout
        finally:
            os.unlink(db)


class TestExitCodes:
    """T9.6 — Exit code behavior."""

    def test_exit_0_no_alerts(self):
        """T9.6a — Exit code 0 when no alerts."""
        db = create_test_db()
        try:
            r = subprocess.run(
                ["python3", os.path.join(SCRIPTS_DIR, "evidence_expiry.py"),
                 "--db-path", db],
                capture_output=True, text=True
            )
            assert r.returncode == 0
        finally:
            os.unlink(db)

    def test_exit_1_with_alerts(self):
        """T9.6b — Exit code 1 when alerts present."""
        db = create_test_db()
        try:
            past = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
            seed_evidence(db, "Expired", past)
            r = subprocess.run(
                ["python3", os.path.join(SCRIPTS_DIR, "evidence_expiry.py"),
                 "--db-path", db],
                capture_output=True, text=True
            )
            assert r.returncode == 1
        finally:
            os.unlink(db)

    def test_exit_2_db_not_found(self):
        """T9.6c — Exit code 2 when database not found."""
        r = subprocess.run(
            ["python3", os.path.join(SCRIPTS_DIR, "evidence_expiry.py"),
             "--db-path", "/tmp/nonexistent_grc_db.sqlite"],
            capture_output=True, text=True
        )
        assert r.returncode == 2
