"""Tests for V4 Integration CRUD actions (5 actions, 10 tests)."""

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


class TestIntegrationActions:
    """Test add/list/update/sync/health integration actions."""

    def test_add_integration(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("add-integration", db_path,
                ["--provider", "aws", "--name", "AWS Production"])
            assert code == 0
            assert result["status"] == "created"
            assert result["provider"] == "aws"
            assert result["name"] == "AWS Production"
            assert result["id"] == 1
        finally:
            os.unlink(db_path)

    def test_add_integration_missing_provider(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("add-integration", db_path,
                ["--name", "Test"])
            assert code == 1
            err = _parse_error(stderr)
            assert err["status"] == "error"
            assert "provider" in err["message"].lower()
        finally:
            os.unlink(db_path)

    def test_list_integrations(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _run_action("add-integration", db_path,
                ["--provider", "aws", "--name", "AWS Prod"])
            _run_action("add-integration", db_path,
                ["--provider", "github", "--name", "GitHub Org"])

            result, stderr, code = _run_action("list-integrations", db_path)
            assert code == 0
            assert result["count"] == 2
            assert len(result["integrations"]) == 2
        finally:
            os.unlink(db_path)

    def test_list_integrations_filter_by_provider(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _run_action("add-integration", db_path,
                ["--provider", "aws", "--name", "AWS Prod"])
            _run_action("add-integration", db_path,
                ["--provider", "github", "--name", "GitHub Org"])

            result, stderr, code = _run_action("list-integrations", db_path,
                ["--provider", "aws"])
            assert code == 0
            assert result["count"] == 1
            assert result["integrations"][0]["provider"] == "aws"
        finally:
            os.unlink(db_path)

    def test_update_integration(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _run_action("add-integration", db_path,
                ["--provider", "aws", "--name", "AWS Prod"])

            result, stderr, code = _run_action("update-integration", db_path,
                ["--id", "1", "--status", "active"])
            assert code == 0
            assert result["status"] == "updated"

            # Verify
            result, _, _ = _run_action("list-integrations", db_path)
            assert result["integrations"][0]["status"] == "active"
        finally:
            os.unlink(db_path)

    def test_update_integration_not_found(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("update-integration", db_path,
                ["--id", "999", "--status", "active"])
            assert code == 1
            err = _parse_error(stderr)
            assert err["status"] == "error"
            assert "not found" in err["message"].lower()
        finally:
            os.unlink(db_path)

    def test_sync_integration(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _run_action("add-integration", db_path,
                ["--provider", "aws", "--name", "AWS Prod"])

            result, stderr, code = _run_action("sync-integration", db_path,
                ["--id", "1"])
            assert code == 0
            assert result["status"] == "syncing"
            assert result["provider"] == "aws"

            # Verify status changed
            result, _, _ = _run_action("list-integrations", db_path)
            assert result["integrations"][0]["status"] == "syncing"
            assert result["integrations"][0]["last_sync"] is not None
        finally:
            os.unlink(db_path)

    def test_sync_integration_not_found(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("sync-integration", db_path,
                ["--id", "999"])
            assert code == 1
            err = _parse_error(stderr)
            assert err["status"] == "error"
            assert "not found" in err["message"].lower()
        finally:
            os.unlink(db_path)

    def test_integration_health_empty(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("integration-health", db_path)
            assert code == 0
            assert result["total"] == 0
            assert result["healthy"] == 0
        finally:
            os.unlink(db_path)

    def test_integration_health_with_data(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            _run_action("add-integration", db_path,
                ["--provider", "aws", "--name", "AWS Prod"])
            _run_action("add-integration", db_path,
                ["--provider", "github", "--name", "GitHub Org"])

            result, stderr, code = _run_action("integration-health", db_path)
            assert code == 0
            assert result["total"] == 2
            assert result["healthy"] == 2
            for i in result["integrations"]:
                assert "health" in i
                assert "evidence_count" in i
        finally:
            os.unlink(db_path)
