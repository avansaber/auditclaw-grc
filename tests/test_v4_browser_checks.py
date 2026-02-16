"""Tests for V4 Browser Check CRUD actions (4 actions, 8 tests)."""

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


class TestBrowserCheckActions:
    """Test add/list/update/run browser check actions."""

    def test_add_browser_check(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("add-browser-check", db_path,
                ["--name", "Main Site Headers", "--url", "https://example.com",
                 "--check-type", "security_headers"])
            assert code == 0
            assert result["status"] == "created"
            assert result["name"] == "Main Site Headers"
            assert result["url"] == "https://example.com"
            assert result["check_type"] == "security_headers"
        finally:
            os.unlink(db_path)

    def test_add_browser_check_missing_url(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("add-browser-check", db_path,
                ["--name", "Test", "--check-type", "ssl"])
            assert code == 1
            err = _parse_error(stderr)
            assert err["status"] == "error"
            assert "url" in err["message"].lower()
        finally:
            os.unlink(db_path)

    def test_list_browser_checks(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _run_action("add-browser-check", db_path,
                ["--name", "Site Headers", "--url", "https://example.com",
                 "--check-type", "security_headers"])
            _run_action("add-browser-check", db_path,
                ["--name", "Site SSL", "--url", "https://example.com",
                 "--check-type", "ssl"])

            result, stderr, code = _run_action("list-browser-checks", db_path)
            assert code == 0
            assert result["count"] == 2
        finally:
            os.unlink(db_path)

    def test_list_browser_checks_filter_by_type(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _run_action("add-browser-check", db_path,
                ["--name", "Site Headers", "--url", "https://example.com",
                 "--check-type", "security_headers"])
            _run_action("add-browser-check", db_path,
                ["--name", "Site SSL", "--url", "https://example.com",
                 "--check-type", "ssl"])

            result, stderr, code = _run_action("list-browser-checks", db_path,
                ["--check-type", "ssl"])
            assert code == 0
            assert result["count"] == 1
            assert result["checks"][0]["check_type"] == "ssl"
        finally:
            os.unlink(db_path)

    def test_update_browser_check(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _run_action("add-browser-check", db_path,
                ["--name", "Site Headers", "--url", "https://example.com",
                 "--check-type", "security_headers"])

            result, stderr, code = _run_action("update-browser-check", db_path,
                ["--id", "1", "--status", "disabled"])
            assert code == 0
            assert result["status"] == "updated"

            # Verify
            list_result, _, _ = _run_action("list-browser-checks", db_path)
            assert list_result["checks"][0]["status"] == "disabled"
        finally:
            os.unlink(db_path)

    def test_update_browser_check_not_found(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("update-browser-check", db_path,
                ["--id", "999", "--status", "disabled"])
            assert code == 1
            err = _parse_error(stderr)
            assert err["status"] == "error"
            assert "not found" in err["message"].lower()
        finally:
            os.unlink(db_path)

    def test_run_browser_check(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _run_action("add-browser-check", db_path,
                ["--name", "Site Headers", "--url", "https://example.com",
                 "--check-type", "security_headers"])

            result, stderr, code = _run_action("run-browser-check", db_path,
                ["--id", "1"])
            assert code == 0
            assert result["status"] == "running"
            assert result["url"] == "https://example.com"
            assert result["check_type"] == "security_headers"

            # Verify run_count incremented and last_run set
            list_result, _, _ = _run_action("list-browser-checks", db_path)
            assert list_result["checks"][0]["run_count"] == 1
            assert list_result["checks"][0]["last_run"] is not None
        finally:
            os.unlink(db_path)

    def test_run_browser_check_not_found(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("run-browser-check", db_path,
                ["--id", "999"])
            assert code == 1
            err = _parse_error(stderr)
            assert err["status"] == "error"
            assert "not found" in err["message"].lower()
        finally:
            os.unlink(db_path)
