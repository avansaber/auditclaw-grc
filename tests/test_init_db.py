"""Tests for init_db.py — Database initialization."""

import os
import sqlite3
import tempfile

from conftest import run_script


class TestInitDb:
    """T1.x — init_db.py tests."""

    def test_creates_all_tables(self, temp_db):
        """T1.1: All expected tables exist after init."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        expected = [
            "alerts", "assets", "audit_log", "checklist_items", "checklists",
            "compliance_scores", "control_mappings", "controls", "evidence",
            "evidence_controls", "frameworks", "incidents", "policies",
            "policy_controls", "risks", "schema_version", "training_assignments",
            "training_modules", "vendors",
        ]
        for table in expected:
            assert table in tables, f"Missing table: {table}"

    def test_idempotent(self, temp_db):
        """T1.2: Running init twice doesn't error or duplicate."""
        result, stderr, code = run_script("init_db.py", db_path=temp_db)
        assert code == 0
        assert result["status"] == "already_initialized"

    def test_wal_mode(self, temp_db):
        """T1.3: WAL journal mode is set."""
        conn = sqlite3.connect(temp_db)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert mode == "wal"

    def test_schema_version(self, temp_db):
        """T1.4: Version record exists."""
        conn = sqlite3.connect(temp_db)
        version = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()[0]
        conn.close()
        assert version in ("1.0.0", "2.0.0", "6.0.0")

    def test_foreign_keys(self, temp_db):
        """T1.5: Foreign keys enabled."""
        conn = sqlite3.connect(temp_db)
        conn.execute("PRAGMA foreign_keys = ON;")
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        conn.close()
        assert fk == 1

    def test_creates_directory(self):
        """T1.6: Creates parent directory if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "subdir", "test.sqlite")
            result, stderr, code = run_script("init_db.py", db_path=db_path)
            assert code == 0
            assert os.path.exists(db_path)
