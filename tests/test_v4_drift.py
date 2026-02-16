"""Tests for V4 Drift Detection actions (2 actions, 8 tests)."""

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


_evidence_seq = 0

def _seed_evidence(db_path, provider, check_name, passed, failed, total):
    """Insert a mock evidence record with sequential timestamps."""
    global _evidence_seq
    _evidence_seq += 1
    conn = sqlite3.connect(db_path)
    data = json.dumps({"check": check_name, "passed": passed, "failed": failed, "total": total})
    # Use sequential timestamps so ordering is deterministic
    ts = f"2026-01-{_evidence_seq:02d}T00:00:00"
    conn.execute(
        """INSERT INTO evidence (title, type, description, source, metadata, uploaded_at)
           VALUES (?, 'automated', ?, ?, ?, ?)""",
        (f"{check_name} evidence",
         f"{provider.upper()} {check_name} check: {passed}/{total} passed",
         provider, data, ts)
    )
    conn.commit()
    conn.close()


class TestCheckDrift:
    """Test check-drift action."""

    def setup_method(self):
        global _evidence_seq
        _evidence_seq = 0

    def test_check_drift_no_evidence(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("check-drift", db_path,
                ["--provider", "aws"])
            assert code == 0
            assert result["status"] == "ok"
            assert result["total_checks"] == 0
            assert result["drifted"] == 0
        finally:
            os.unlink(db_path)

    def test_check_drift_initial_snapshot(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _seed_evidence(db_path, "aws", "iam", 7, 0, 7)

            result, stderr, code = _run_action("check-drift", db_path,
                ["--provider", "aws"])
            assert code == 0
            assert result["total_checks"] == 1
            assert result["drifts"][0]["type"] == "initial"
        finally:
            os.unlink(db_path)

    def test_check_drift_regression(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            # First snapshot: all pass
            _seed_evidence(db_path, "aws", "iam", 7, 0, 7)
            # Second snapshot: some failures
            _seed_evidence(db_path, "aws", "iam", 5, 2, 7)

            result, stderr, code = _run_action("check-drift", db_path,
                ["--provider", "aws"])
            assert code == 0
            assert result["regressions"] == 1
            assert result["drifted"] == 1
        finally:
            os.unlink(db_path)

    def test_check_drift_improvement(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            # First snapshot: some failures
            _seed_evidence(db_path, "aws", "s3", 2, 3, 5)
            # Second snapshot: fewer failures
            _seed_evidence(db_path, "aws", "s3", 4, 1, 5)

            result, stderr, code = _run_action("check-drift", db_path,
                ["--provider", "aws"])
            assert code == 0
            assert result["improvements"] == 1
        finally:
            os.unlink(db_path)

    def test_check_drift_unchanged(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _seed_evidence(db_path, "aws", "iam", 7, 0, 7)
            _seed_evidence(db_path, "aws", "iam", 7, 0, 7)

            result, stderr, code = _run_action("check-drift", db_path,
                ["--provider", "aws"])
            assert code == 0
            assert result["unchanged"] == 1
            assert result["drifted"] == 0
        finally:
            os.unlink(db_path)

    def test_check_drift_all_providers(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _seed_evidence(db_path, "aws", "iam", 7, 0, 7)
            _seed_evidence(db_path, "github", "branch_protection", 5, 1, 6)

            result, stderr, code = _run_action("check-drift", db_path,
                ["--provider", "all"])
            assert code == 0
            assert result["total_checks"] == 2
        finally:
            os.unlink(db_path)


class TestDriftHistory:
    """Test drift-history action."""

    def test_drift_history_empty(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("drift-history", db_path)
            assert code == 0
            assert result["status"] == "ok"
            assert result["total"] == 0
        finally:
            os.unlink(db_path)

    def test_drift_history_with_alerts(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            # Create drift alerts directly
            _run_action("add-alert", db_path,
                ["--type", "drift_detected", "--title", "Drift: aws/iam — regression",
                 "--severity", "critical", "--resource-type", "aws", "--resource-id", "iam"])
            _run_action("add-alert", db_path,
                ["--type", "drift_detected", "--title", "Drift: aws/s3 — improvement",
                 "--severity", "info", "--resource-type", "aws", "--resource-id", "s3"])

            result, stderr, code = _run_action("drift-history", db_path)
            assert code == 0
            assert result["total"] == 2
            assert result["regressions"] == 1
            assert result["improvements"] == 1
        finally:
            os.unlink(db_path)
