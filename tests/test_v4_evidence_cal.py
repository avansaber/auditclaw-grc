"""Tests for V4 Evidence Mapping + Calendar actions (4 actions, 12 tests)."""

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


def _parse_error(stderr):
    try:
        return json.loads(stderr.strip())
    except (json.JSONDecodeError, AttributeError):
        return None


def _seed_evidence_with_control(db_path, title, control_id):
    """Insert evidence and link to a control."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "INSERT INTO evidence (title, type, source, uploaded_at) VALUES (?, 'manual', 'user', datetime('now'))",
        (title,)
    )
    ev_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO evidence_controls (evidence_id, control_id) VALUES (?, ?)",
        (ev_id, control_id)
    )
    conn.commit()
    conn.close()
    return ev_id


class TestAutoMapEvidence:
    """Test auto-map-evidence action."""

    def test_auto_map_no_id(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("auto-map-evidence", db_path)
            assert code == 1
            err = _parse_error(stderr)
            assert err["status"] == "error"
        finally:
            os.unlink(db_path)

    def test_auto_map_not_found(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("auto-map-evidence", db_path, ["--id", "999"])
            assert code == 1
            err = _parse_error(stderr)
            assert err["status"] == "error"
            assert "not found" in err["message"].lower()
        finally:
            os.unlink(db_path)

    def test_auto_map_no_controls_linked(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            # Add evidence without linking controls
            conn = sqlite3.connect(db_path)
            cursor = conn.execute(
                "INSERT INTO evidence (title, type, source) VALUES ('test', 'manual', 'user')"
            )
            ev_id = cursor.lastrowid
            conn.commit()
            conn.close()

            result, stderr, code = _run_action("auto-map-evidence", db_path, ["--id", str(ev_id)])
            assert code == 0
            assert result["mapped_count"] == 0
            assert "link controls first" in result.get("message", "").lower()
        finally:
            os.unlink(db_path)

    def test_auto_map_with_mappings(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            # Activate a framework to get controls
            _run_action("activate-framework", db_path, ["--slug", "soc2"])
            conn = sqlite3.connect(db_path)
            ctrl = conn.execute("SELECT id FROM controls LIMIT 1").fetchone()
            if not ctrl:
                pytest.skip("No controls in database")
            ctrl_id = ctrl[0]
            conn.close()

            ev_id = _seed_evidence_with_control(db_path, "Test evidence", ctrl_id)
            result, stderr, code = _run_action("auto-map-evidence", db_path, ["--id", str(ev_id)])
            assert code == 0
            assert result["status"] == "ok"
            assert result["evidence_id"] == ev_id
            assert isinstance(result["original_controls"], list)
            assert len(result["original_controls"]) == 1
        finally:
            os.unlink(db_path)


class TestListEvidenceGaps:
    """Test list-evidence-gaps action."""

    def test_list_gaps_all_frameworks(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            # Activate a framework first to get controls
            _run_action("activate-framework", db_path, ["--slug", "soc2"])
            result, stderr, code = _run_action("list-evidence-gaps", db_path)
            assert code == 0
            assert result["status"] == "ok"
            assert result["total_controls"] > 0
            # With no evidence linked, all controls should be gaps
            assert result["controls_without_evidence"] == result["total_controls"]
            assert result["framework_coverage_pct"] == 0
        finally:
            os.unlink(db_path)

    def test_list_gaps_by_framework(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _run_action("activate-framework", db_path, ["--slug", "soc2"])
            result, stderr, code = _run_action("list-evidence-gaps", db_path,
                ["--framework", "soc2"])
            assert code == 0
            assert result["status"] == "ok"
            assert result["total_controls"] > 0
            # All gaps should be soc2
            for gap in result["gaps"]:
                assert gap["framework"] == "soc2"
        finally:
            os.unlink(db_path)


class TestComplianceCalendar:
    """Test compliance-calendar action."""

    def test_calendar_empty(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("compliance-calendar", db_path)
            assert code == 0
            assert result["status"] == "ok"
            assert result["total"] >= 0
            assert "overdue" in result
            assert "due_this_week" in result
            assert "due_this_month" in result
        finally:
            os.unlink(db_path)

    def test_calendar_with_days(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("compliance-calendar", db_path,
                ["--days", "90"])
            assert code == 0
            assert result["status"] == "ok"
        finally:
            os.unlink(db_path)

    def test_calendar_filter_by_type(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("compliance-calendar", db_path,
                ["--type", "evidence"])
            assert code == 0
            assert result["status"] == "ok"
        finally:
            os.unlink(db_path)


class TestComplianceDigest:
    """Test compliance-digest action."""

    def test_digest_daily(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("compliance-digest", db_path,
                ["--period", "daily"])
            assert code == 0
            assert result["status"] == "ok"
            assert result["period"] == "daily"
            digest = result["digest"]
            assert "average_score" in digest
            assert "new_alerts" in digest
            assert "unresolved_alerts" in digest
            assert "expiring_evidence" in digest
            assert "total_integrations" in digest
        finally:
            os.unlink(db_path)

    def test_digest_weekly(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("compliance-digest", db_path,
                ["--period", "weekly"])
            assert code == 0
            assert result["period"] == "weekly"
        finally:
            os.unlink(db_path)
