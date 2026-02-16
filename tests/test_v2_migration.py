"""Tests for V2 schema migration (migrate_v2.py) and fresh V2 init."""

import os
import sqlite3
import tempfile

import pytest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conftest import run_script, get_v2_connection

V2_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(V2_DIR, "scripts")
INIT_DB_V1 = os.path.join(SCRIPTS_DIR, "init_db.py")
MIGRATE_V2 = os.path.join(SCRIPTS_DIR, "migrate_v2.py")
# init_db_v2_patch.py was only needed when init_db.py was V1; removed since init_db.py is V6+

# The 8 new tables introduced in V2
V2_NEW_TABLES = [
    "vulnerabilities",
    "vulnerability_controls",
    "access_review_campaigns",
    "access_review_items",
    "questionnaire_templates",
    "questionnaire_responses",
    "questionnaire_answers",
    "asset_controls",
]

# The 8 new indexes introduced in V2
V2_NEW_INDEXES = [
    "idx_vulnerabilities_status",
    "idx_vulnerabilities_severity",
    "idx_vulnerabilities_cve",
    "idx_access_reviews_status",
    "idx_questionnaire_responses_status",
    "idx_assets_lifecycle",
    "idx_assets_classification",
    "idx_training_assignments_status",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def migrated_db():
    """V1 DB that has been migrated to V2; yields (db_path, migration_result)."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name

    # Init V1
    _, stderr, code = run_script(INIT_DB_V1, db_path=db_path)
    assert code == 0, f"init_db_v1 failed: {stderr}"

    # Migrate
    result, stderr, code = run_script(MIGRATE_V2, db_path=db_path)
    assert code == 0, f"migrate_v2 failed: {stderr}"

    yield db_path, result

    for ext in ["", "-wal", "-shm"]:
        try:
            os.unlink(db_path + ext)
        except OSError:
            pass


@pytest.fixture
def fresh_v2_db():
    """A fresh DB created with init_db.py (which is already V2 on the server).

    If init_db.py is already V2 (has SCHEMA_VERSION = '2.0.0'), use it directly.
    Otherwise, fall back to patching via init_db_v2_patch.py.
    """
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name

    # init_db.py is V6+ and already includes all V2 tables, use it directly
    result, stderr, code = run_script(INIT_DB_V1, db_path=db_path)
    assert code == 0, f"init_db failed: {stderr}"

    yield db_path, result

    for ext in ["", "-wal", "-shm"]:
        try:
            os.unlink(db_path + ext)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_tables(conn):
    """Return a set of user-created table names."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {r[0] for r in rows}


def _get_indexes(conn):
    """Return a set of user-created index names."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {r[0] for r in rows}


def _get_columns(conn, table):
    """Return a list of column names for a table."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [r[1] for r in rows]


# ---------------------------------------------------------------------------
# Tests — Migration from V1 to V2
# ---------------------------------------------------------------------------


class TestMigrationTables:
    """V2-T7.1 – V2-T7.3: Structural changes after migration."""

    def test_migration_creates_new_tables(self, migrated_db):
        """V2-T7.1: All 8 new V2 tables exist after migration."""
        db_path, migration_result = migrated_db
        conn = sqlite3.connect(db_path)
        tables = _get_tables(conn)
        conn.close()

        for tname in V2_NEW_TABLES:
            assert tname in tables, f"Table '{tname}' missing after migration"

    def test_migration_adds_columns(self, migrated_db):
        """V2-T7.2: New columns exist on assets, training_modules, training_assignments."""
        db_path, _ = migrated_db
        conn = sqlite3.connect(db_path)

        assets_cols = _get_columns(conn, "assets")
        assert "ip_address" in assets_cols
        assert "hostname" in assets_cols
        assert "os_type" in assets_cols
        assert "software_version" in assets_cols
        assert "lifecycle_stage" in assets_cols
        assert "data_classification" in assets_cols
        assert "discovery_source" in assets_cols
        assert "encryption_status" in assets_cols
        assert "backup_status" in assets_cols
        assert "patch_status" in assets_cols

        tm_cols = _get_columns(conn, "training_modules")
        assert "content_type" in tm_cols
        assert "content_url" in tm_cols
        assert "difficulty_level" in tm_cols
        assert "requires_recertification" in tm_cols
        assert "recertification_days" in tm_cols

        ta_cols = _get_columns(conn, "training_assignments")
        assert "certificate_path" in ta_cols

        conn.close()

    def test_migration_creates_indexes(self, migrated_db):
        """V2-T7.3: All 8 new V2 indexes exist after migration."""
        db_path, _ = migrated_db
        conn = sqlite3.connect(db_path)
        indexes = _get_indexes(conn)
        conn.close()

        for idx_name in V2_NEW_INDEXES:
            assert idx_name in indexes, f"Index '{idx_name}' missing after migration"


class TestMigrationBehaviour:
    """V2-T7.4 – V2-T7.6: Migration idempotency, data preservation, versioning."""

    def test_migration_idempotent(self, migrated_db):
        """V2-T7.4: Running migrate_v2 a second time returns already_migrated."""
        db_path, _ = migrated_db

        result, stderr, code = run_script(MIGRATE_V2, db_path=db_path)
        assert code == 0
        assert result["status"] == "already_migrated"

    def test_migration_preserves_data(self, v1_db):
        """V2-T7.5: V1 data inserted before migration is intact afterwards."""
        conn = sqlite3.connect(v1_db)
        # Insert V1 data: a framework and a control
        conn.execute(
            "INSERT INTO frameworks (name, slug, version, status) VALUES ('SOC 2', 'soc2', '1.0', 'active')"
        )
        fw_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO controls (framework_id, control_id, title, status) VALUES (?, 'CC1.1', 'Ethics and Integrity', 'complete')",
            (fw_id,),
        )
        conn.execute(
            "INSERT INTO assets (name, type, criticality) VALUES ('Prod Server', 'server', 'high')"
        )
        conn.execute(
            "INSERT INTO training_modules (title, category) VALUES ('Security 101', 'security')"
        )
        conn.commit()
        conn.close()

        # Run migration (may be already_migrated if init_db.py is V2)
        result, stderr, code = run_script(MIGRATE_V2, db_path=v1_db)
        assert code == 0, f"migrate_v2 failed: {stderr}"
        assert result["status"] in ("success", "already_migrated")

        # Verify V1 data is intact
        conn = sqlite3.connect(v1_db)
        fw = conn.execute("SELECT * FROM frameworks WHERE slug = 'soc2'").fetchone()
        assert fw is not None

        ctrl = conn.execute("SELECT * FROM controls WHERE control_id = 'CC1.1'").fetchone()
        assert ctrl is not None
        # Use column index: status is at a known position, but safer to check by name
        cols = [desc[0] for desc in conn.execute("SELECT * FROM controls LIMIT 0").description]
        status_idx = cols.index("status")
        assert ctrl[status_idx] == "complete"

        asset = conn.execute("SELECT * FROM assets WHERE name = 'Prod Server'").fetchone()
        assert asset is not None

        module = conn.execute("SELECT * FROM training_modules WHERE title = 'Security 101'").fetchone()
        assert module is not None
        conn.close()

    def test_migration_updates_version(self, migrated_db):
        """V2-T7.6: Schema version is 2.0.0 after migration."""
        db_path, migration_result = migrated_db

        # Check via migration result
        assert migration_result["target_version"] == "2.0.0"

        # Also verify directly in DB
        conn = sqlite3.connect(db_path)

        # The migration uses a 'metadata' table for schema_version
        # (since the V1 schema_version table has a different structure)
        version = None
        for table in ("metadata", "schema_version"):
            try:
                row = conn.execute(
                    f"SELECT value FROM {table} WHERE key = 'schema_version'"
                ).fetchone()
                if row:
                    version = row[0]
                    break
            except sqlite3.OperationalError:
                pass

        if version is None:
            # Fallback: schema_version table with 'version' column
            try:
                row = conn.execute("SELECT version FROM schema_version ORDER BY rowid DESC LIMIT 1").fetchone()
                if row:
                    version = row[0]
            except sqlite3.OperationalError:
                pass

        conn.close()
        assert version == "2.0.0", f"Expected schema version 2.0.0, got {version}"


# ---------------------------------------------------------------------------
# Tests — Fresh V2 Schema
# ---------------------------------------------------------------------------


class TestFreshV2Schema:
    """V2-T7.7 – V2-T7.8: Fresh database creation with full V2 schema."""

    def test_fresh_v2_schema(self, fresh_v2_db):
        """V2-T7.7: Fresh init creates all V2 tables directly."""
        db_path, init_result = fresh_v2_db
        conn = sqlite3.connect(db_path)
        tables = _get_tables(conn)

        for tname in V2_NEW_TABLES:
            assert tname in tables, f"Table '{tname}' missing from fresh V2 init"

        # Also confirm original V1 tables still present
        for v1_table in ["frameworks", "controls", "evidence", "risks", "assets",
                         "training_modules", "training_assignments"]:
            assert v1_table in tables, f"V1 table '{v1_table}' missing from fresh V2 init"

        # Verify new columns exist on assets (should have them from CREATE TABLE)
        assets_cols = _get_columns(conn, "assets")
        assert "ip_address" in assets_cols
        assert "data_classification" in assets_cols

        conn.close()

    def test_fresh_v2_version(self, fresh_v2_db):
        """V2-T7.8: Fresh init sets schema version >= 2.0.0 (V2 tables included)."""
        db_path, init_result = fresh_v2_db

        # Schema is at least 2.0.0 (currently 6.0.0)
        major = int(init_result["version"].split(".")[0])
        assert major >= 2

        # Also verify in DB
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        conn.close()

        assert row is not None
        db_major = int(row[0].split(".")[0])
        assert db_major >= 2
