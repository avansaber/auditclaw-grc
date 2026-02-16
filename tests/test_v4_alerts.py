"""Tests for V4 Alert CRUD actions (4 actions, 8 tests)."""

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


class TestAlertActions:
    """Test add/list/acknowledge/resolve alert actions."""

    def test_add_alert(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("add-alert", db_path,
                ["--type", "drift_detected", "--title", "S3 encryption disabled",
                 "--severity", "critical"])
            assert code == 0
            assert result["status"] == "created"
            assert result["type"] == "drift_detected"
            assert result["severity"] == "critical"
            assert result["id"] == 1
        finally:
            os.unlink(db_path)

    def test_add_alert_with_resource(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("add-alert", db_path,
                ["--type", "evidence_expired", "--title", "Evidence expired",
                 "--severity", "warning", "--resource-type", "s3_bucket",
                 "--resource-id", "prod-data-bucket"])
            assert code == 0
            assert result["status"] == "created"

            # Verify resource fields stored
            list_result, _, _ = _run_action("list-alerts", db_path)
            alert = list_result["alerts"][0]
            assert alert["resource_type"] == "s3_bucket"
            assert alert["resource_id"] == "prod-data-bucket"
        finally:
            os.unlink(db_path)

    def test_list_alerts(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _run_action("add-alert", db_path,
                ["--type", "drift_detected", "--title", "Alert 1", "--severity", "critical"])
            _run_action("add-alert", db_path,
                ["--type", "evidence_expired", "--title", "Alert 2", "--severity", "warning"])

            result, stderr, code = _run_action("list-alerts", db_path)
            assert code == 0
            assert result["count"] == 2
            assert result["unacknowledged"] == 2
            assert result["unresolved"] == 2
        finally:
            os.unlink(db_path)

    def test_list_alerts_filter_by_type(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _run_action("add-alert", db_path,
                ["--type", "drift_detected", "--title", "Alert 1", "--severity", "critical"])
            _run_action("add-alert", db_path,
                ["--type", "evidence_expired", "--title", "Alert 2", "--severity", "warning"])

            result, stderr, code = _run_action("list-alerts", db_path,
                ["--type", "drift_detected"])
            assert code == 0
            assert result["count"] == 1
            assert result["alerts"][0]["type"] == "drift_detected"
        finally:
            os.unlink(db_path)

    def test_acknowledge_alert(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _run_action("add-alert", db_path,
                ["--type", "drift_detected", "--title", "Alert 1", "--severity", "critical"])

            result, stderr, code = _run_action("acknowledge-alert", db_path, ["--id", "1"])
            assert code == 0
            assert result["status"] == "acknowledged"

            # Verify
            list_result, _, _ = _run_action("list-alerts", db_path)
            assert list_result["unacknowledged"] == 0
            assert list_result["alerts"][0]["acknowledged_at"] is not None
        finally:
            os.unlink(db_path)

    def test_acknowledge_alert_not_found(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("acknowledge-alert", db_path, ["--id", "999"])
            assert code == 1
            err = _parse_error(stderr)
            assert err["status"] == "error"
            assert "not found" in err["message"].lower()
        finally:
            os.unlink(db_path)

    def test_resolve_alert(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _run_action("add-alert", db_path,
                ["--type", "drift_detected", "--title", "Alert 1", "--severity", "critical"])

            result, stderr, code = _run_action("resolve-alert", db_path, ["--id", "1"])
            assert code == 0
            assert result["status"] == "resolved"

            # Verify
            list_result, _, _ = _run_action("list-alerts", db_path)
            assert list_result["unresolved"] == 0
            assert list_result["alerts"][0]["status"] == "resolved"
            assert list_result["alerts"][0]["resolved_at"] is not None
        finally:
            os.unlink(db_path)

    def test_resolve_alert_not_found(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("resolve-alert", db_path, ["--id", "999"])
            assert code == 1
            err = _parse_error(stderr)
            assert err["status"] == "error"
            assert "not found" in err["message"].lower()
        finally:
            os.unlink(db_path)
