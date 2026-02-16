"""Tests for V4 schema migration (v3.0.0 -> v4.0.0).

Tests cover:
  - Migration creates new tables (integrations, browser_checks)
  - Migration adds new columns to alerts
  - Migration is idempotent (already_migrated)
  - Dry-run mode
  - Fresh install path: init_db + migrate_v2 + migrate_v3 + migrate_v4
  - Schema version updated to 4.0.0
"""

import json
import os
import sqlite3
import tempfile

import pytest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))

from conftest import run_script, get_v2_db_via_migration, get_v2_connection

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
MIGRATE_V3_SCRIPT = os.path.join(SCRIPTS_DIR, "migrate_v3.py")
MIGRATE_V4_SCRIPT = os.path.join(SCRIPTS_DIR, "migrate_v4.py")
INIT_DB_SCRIPT = os.path.join(SCRIPTS_DIR, "init_db.py")

# V4 new tables
V4_NEW_TABLES = [
    "integrations",
    "browser_checks",
]

# V4 new columns (table, column_name)
V4_NEW_COLUMNS = [
    ("alerts", "drift_details"),
    ("alerts", "resource_type"),
    ("alerts", "resource_id"),
    ("alerts", "acknowledged_at"),
    ("alerts", "acknowledged_by"),
]

# V4 new indexes
V4_NEW_INDEXES = [
    "idx_integrations_provider",
    "idx_integrations_status",
    "idx_browser_checks_type",
    "idx_browser_checks_status",
    "idx_alerts_type",
    "idx_alerts_severity",
    "idx_alerts_status",
    "idx_alerts_resource",
]


def _get_v3_db(db_path):
    """Create a V1 DB, migrate to V2, then V3."""
    result, stderr, code = run_script(INIT_DB_SCRIPT, db_path=db_path)
    assert code == 0, f"init_db failed: {stderr}"
    result, stderr, code = run_script(MIGRATE_V3_SCRIPT, db_path=db_path)
    assert code == 0, f"migrate_v3 failed: {stderr}"
    return result


def _get_table_columns(db_path, table_name):
    """Return list of column names for a table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    cols = [row[1] for row in cursor.fetchall()]
    conn.close()
    return cols


def _get_index_names(db_path):
    """Return set of index names in the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
    names = {row[0] for row in cursor.fetchall()}
    conn.close()
    return names


def _get_tables(db_path):
    """Return set of table names in the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    names = {row[0] for row in cursor.fetchall()}
    conn.close()
    return names


class TestV4Migration:
    """V3 -> V4 schema migration tests."""

    def test_migration_creates_tables_and_columns(self):
        """Migration from V3 creates integrations + browser_checks tables and adds alerts columns."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v3_db(db_path)
            result, stderr, code = run_script(MIGRATE_V4_SCRIPT, db_path=db_path)
            assert code == 0, f"migrate_v4 failed: {stderr}"
            assert result["status"] == "ok"
            assert result["from_version"] == "3.0.0"
            assert result["to_version"] == "4.0.0"

            # Check new tables exist
            tables = _get_tables(db_path)
            for table in V4_NEW_TABLES:
                assert table in tables, f"Table {table} not created"

            # Check new columns on alerts
            alert_cols = _get_table_columns(db_path, "alerts")
            for _, col in V4_NEW_COLUMNS:
                assert col in alert_cols, f"Column alerts.{col} not added"

            # Check indexes
            indexes = _get_index_names(db_path)
            for idx in V4_NEW_INDEXES:
                assert idx in indexes, f"Index {idx} not created"

            # Check schema version
            conn = sqlite3.connect(db_path)
            version = conn.execute("SELECT version FROM schema_version ORDER BY rowid DESC LIMIT 1").fetchone()[0]
            conn.close()
            assert version == "4.0.0"
        finally:
            os.unlink(db_path)

    def test_migration_idempotent(self):
        """Running migration twice should not fail."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v3_db(db_path)
            result1, _, code1 = run_script(MIGRATE_V4_SCRIPT, db_path=db_path)
            assert code1 == 0
            assert result1["status"] == "ok"

            result2, _, code2 = run_script(MIGRATE_V4_SCRIPT, db_path=db_path)
            assert code2 == 0
            assert result2["status"] == "ok"
            assert "already at version" in result2["message"]
        finally:
            os.unlink(db_path)

    def test_migration_dry_run(self):
        """Dry-run should not modify the database."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v3_db(db_path)
            result, _, code = run_script(MIGRATE_V4_SCRIPT, args=["--dry-run"], db_path=db_path)
            assert code == 0
            assert result["status"] == "ok"
            assert "DRY RUN" in result["message"]

            # browser_checks should NOT exist yet (V4-only table)
            # integrations already exists from init_db
            tables = _get_tables(db_path)
            assert "browser_checks" not in tables

            # Schema version should still be 3.0.0
            conn = sqlite3.connect(db_path)
            version = conn.execute("SELECT version FROM schema_version ORDER BY rowid DESC LIMIT 1").fetchone()[0]
            conn.close()
            assert version == "3.0.0"
        finally:
            os.unlink(db_path)

    def test_migration_preserves_existing_data(self):
        """Migration preserves existing V3 data (alerts with data)."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v3_db(db_path)

            # Insert test data in V3 tables
            conn = sqlite3.connect(db_path)
            conn.execute("INSERT INTO alerts (type, title, severity) VALUES ('test', 'Test alert', 'warning')")
            conn.execute("INSERT INTO controls (framework_id, control_id, title) VALUES (1, 'TST-1', 'Test Control')")
            conn.commit()
            conn.close()

            # Migrate
            result, _, code = run_script(MIGRATE_V4_SCRIPT, db_path=db_path)
            assert code == 0

            # Verify data preserved
            conn = sqlite3.connect(db_path)
            alert = conn.execute("SELECT type, title, severity FROM alerts WHERE type='test'").fetchone()
            assert alert is not None
            assert alert[0] == "test"
            assert alert[1] == "Test alert"

            control = conn.execute("SELECT control_id, title FROM controls WHERE control_id='TST-1'").fetchone()
            assert control is not None
            assert control[1] == "Test Control"
            conn.close()
        finally:
            os.unlink(db_path)

    def test_fresh_install_full_path(self):
        """Fresh install: init_db + migrate_v2 (via get_v2_db) + migrate_v3 + migrate_v4 produces V4 schema."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            # Full path: V1 -> V2 -> V3 -> V4
            _get_v3_db(db_path)
            result, _, code = run_script(MIGRATE_V4_SCRIPT, db_path=db_path)
            assert code == 0
            assert result["status"] == "ok"

            # Verify all V4 tables
            tables = _get_tables(db_path)
            for table in V4_NEW_TABLES:
                assert table in tables

            # Verify integrations table columns
            int_cols = _get_table_columns(db_path, "integrations")
            expected_int_cols = ["id", "provider", "name", "status", "schedule",
                                "last_sync", "next_sync", "last_error", "error_count",
                                "config", "created_at", "updated_at"]
            for col in expected_int_cols:
                assert col in int_cols, f"integrations.{col} missing"

            # Verify browser_checks table columns
            bc_cols = _get_table_columns(db_path, "browser_checks")
            expected_bc_cols = ["id", "name", "url", "check_type", "schedule",
                               "status", "last_run", "last_result", "last_status",
                               "run_count", "created_at", "updated_at"]
            for col in expected_bc_cols:
                assert col in bc_cols, f"browser_checks.{col} missing"

            # Verify schema version
            conn = sqlite3.connect(db_path)
            version = conn.execute("SELECT version FROM schema_version ORDER BY rowid DESC LIMIT 1").fetchone()[0]
            conn.close()
            assert version == "4.0.0"
        finally:
            os.unlink(db_path)
