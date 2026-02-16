"""Shared test fixtures for GRC compliance skill tests."""

import json
import os
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# Shared helper: parse result from run_script
# ---------------------------------------------------------------------------

def parse_result(result, stderr=None):
    """Parse result from run_script -- errors go to stderr, successes to stdout."""
    if result is not None:
        return result
    # db_query.py prints errors to stderr with exit code 1
    if stderr and stderr.strip():
        try:
            return json.loads(stderr.strip())
        except (json.JSONDecodeError, ValueError):
            pass
    return None

# Resolve script paths relative to the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

# Script paths
INIT_DB_SCRIPT = os.path.join(SCRIPTS_DIR, "init_db.py")
MIGRATE_V2_SCRIPT = os.path.join(SCRIPTS_DIR, "migrate_v2.py")
GENERATE_TRUST_CENTER_SCRIPT = os.path.join(SCRIPTS_DIR, "generate_trust_center.py")

# Aliases used by migration test imports
INIT_DB_V1 = INIT_DB_SCRIPT
MIGRATE_V2 = MIGRATE_V2_SCRIPT
GENERATE_TRUST_CENTER = GENERATE_TRUST_CENTER_SCRIPT


# ---------------------------------------------------------------------------
# Helper: run_script by name (relative to scripts/)
# ---------------------------------------------------------------------------

def run_script(script_name_or_path, args=None, db_path=None):
    """Run a Python script and return (stdout_json, stderr, returncode).

    Accepts either:
      - A bare script name: looked up in SCRIPTS_DIR
      - An absolute path: used directly
    """
    if os.path.isabs(script_name_or_path):
        script_path = script_name_or_path
    else:
        script_path = os.path.join(SCRIPTS_DIR, script_name_or_path)

    cmd = ["python3", script_path]
    if db_path:
        cmd.extend(["--db-path", db_path])
    if args:
        cmd.extend(args)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    stdout_json = None
    if result.stdout.strip():
        try:
            stdout_json = json.loads(result.stdout)
        except json.JSONDecodeError:
            stdout_json = result.stdout

    return stdout_json, result.stderr, result.returncode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_args(**kwargs):
    """Create an argparse-like Namespace from keyword arguments."""
    class _Args(SimpleNamespace):
        def __getattr__(self, name):
            return None

    return _Args(**kwargs)


def get_v2_db_via_migration(db_path):
    """Create a base DB then run migrate_v2.py to produce a migrated DB."""
    # Step 1: initialise base schema
    result, stderr, code = run_script(INIT_DB_SCRIPT, db_path=db_path)
    assert code == 0, f"init_db failed: {stderr}"

    # Step 2: run migration
    result, stderr, code = run_script(MIGRATE_V2_SCRIPT, db_path=db_path)
    assert code == 0, f"migrate_v2 failed: {stderr}"

    # Step 3: add columns required by batch2 actions that are not yet in the
    # migration (these will be added in a future migration patch).
    _add_missing_batch2_columns(db_path)

    return result


def _add_missing_batch2_columns(db_path):
    """Add columns that batch2 action code references but the v2 migration
    does not yet create."""
    conn = sqlite3.connect(db_path)
    extras = [
        ("questionnaire_templates", "total_questions", "INTEGER DEFAULT 0"),
        ("questionnaire_templates", "updated_at", "TEXT"),
        ("access_review_campaigns", "updated_at", "TEXT"),
        ("access_review_items", "created_at", "TEXT"),
        ("questionnaire_responses", "updated_at", "TEXT"),
    ]
    for table, col, col_def in extras:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.commit()
    conn.close()


def get_v2_connection(db_path):
    """Return a sqlite3 connection with row_factory and FK enforcement."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_db():
    """Create a temporary SQLite DB, run init, yield path, cleanup."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name

    # Run init_db.py against this temp path
    result, stderr, code = run_script("init_db.py", db_path=db_path)
    assert code == 0, f"init_db.py failed: {stderr}"

    yield db_path

    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass
    for ext in ["-wal", "-shm"]:
        try:
            os.unlink(db_path + ext)
        except OSError:
            pass


@pytest.fixture
def seeded_db(temp_db):
    """DB with SOC 2 activated and sample data loaded."""
    result, stderr, code = run_script(
        "db_query.py",
        ["--action", "activate-framework", "--slug", "soc2"],
        db_path=temp_db,
    )
    assert code == 0, f"activate-framework failed: {stderr}"

    conn = sqlite3.connect(temp_db)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("UPDATE controls SET status='complete' WHERE rowid <= 10")
    conn.execute("UPDATE controls SET status='in_progress' WHERE rowid BETWEEN 11 AND 15")
    conn.commit()
    conn.close()

    yield temp_db


@pytest.fixture
def empty_db(temp_db):
    """DB initialized but with zero frameworks or controls."""
    return temp_db


@pytest.fixture
def soc2_db(temp_db):
    """DB with SOC 2 activated, all controls not_started."""
    result, stderr, code = run_script(
        "db_query.py",
        ["--action", "activate-framework", "--slug", "soc2"],
        db_path=temp_db,
    )
    assert code == 0, f"activate-framework failed: {stderr}"
    return temp_db


@pytest.fixture
def mixed_health_db(soc2_db):
    """DB with controls in varied states for score testing."""
    conn = sqlite3.connect(soc2_db)
    conn.execute("PRAGMA foreign_keys = ON;")

    conn.execute("UPDATE controls SET status='complete' WHERE rowid <= 10")
    for i in range(1, 11):
        conn.execute(
            "INSERT INTO evidence (title, status, valid_until, type) VALUES (?, 'active', ?, 'manual')",
            (f"Evidence {i}", (datetime.now() + timedelta(days=90)).isoformat()),
        )
        conn.execute(
            "INSERT INTO evidence_controls (evidence_id, control_id) VALUES (?, ?)",
            (i, i),
        )

    conn.execute(
        "UPDATE controls SET status='in_progress' WHERE rowid BETWEEN 11 AND 15"
    )

    conn.execute(
        "UPDATE controls SET status='complete' WHERE rowid BETWEEN 16 AND 17"
    )
    for i in range(16, 18):
        conn.execute(
            "INSERT INTO evidence (title, status, valid_until, type) VALUES (?, 'expired', ?, 'manual')",
            (
                f"Expired Evidence {i}",
                (datetime.now() - timedelta(days=30)).isoformat(),
            ),
        )
        conn.execute(
            "INSERT INTO evidence_controls (evidence_id, control_id) VALUES (?, ?)",
            (i - 5, i),
        )

    conn.commit()
    conn.close()
    return soc2_db


@pytest.fixture
def excellent_score_db(soc2_db):
    """All controls complete with current evidence -- should score ~100."""
    conn = sqlite3.connect(soc2_db)
    conn.execute("PRAGMA foreign_keys = ON;")

    conn.execute("UPDATE controls SET status='complete'")
    count = conn.execute("SELECT COUNT(*) FROM controls").fetchone()[0]
    for i in range(1, count + 1):
        conn.execute(
            "INSERT INTO evidence (title, status, valid_until, type) VALUES (?, 'active', ?, 'manual')",
            (f"Evidence {i}", (datetime.now() + timedelta(days=90)).isoformat()),
        )
        conn.execute(
            "INSERT INTO evidence_controls (evidence_id, control_id) VALUES (?, ?)",
            (i, i),
        )

    conn.commit()
    conn.close()
    return soc2_db


# ---------------------------------------------------------------------------
# Migration Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def v2_db():
    """Create a temporary migrated database (via init + migration), yield path, cleanup."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name

    get_v2_db_via_migration(db_path)
    yield db_path

    for ext in ["", "-wal", "-shm"]:
        try:
            os.unlink(db_path + ext)
        except OSError:
            pass


@pytest.fixture
def v1_db():
    """Create a temporary base database (pre-migration), yield path, cleanup."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name

    result, stderr, code = run_script(INIT_DB_SCRIPT, db_path=db_path)
    assert code == 0, f"init_db failed: {stderr}"

    yield db_path

    for ext in ["", "-wal", "-shm"]:
        try:
            os.unlink(db_path + ext)
        except OSError:
            pass


@pytest.fixture
def seeded_v2_db(v2_db):
    """Migrated DB with a framework, controls, policies, and evidence seeded."""
    conn = get_v2_connection(v2_db)

    conn.execute(
        "INSERT INTO frameworks (name, slug, version, status, priority) "
        "VALUES ('SOC 2', 'soc2', '2017', 'active', 1)"
    )
    fw_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    for i in range(1, 11):
        status = "complete" if i <= 6 else ("in_progress" if i <= 8 else "not_started")
        conn.execute(
            "INSERT INTO controls (framework_id, control_id, title, category, status, priority) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (fw_id, f"CC{i}.1", f"Control {i}", "Security", status, 3),
        )

    for title, p_status in [
        ("Information Security Policy", "active"),
        ("Access Control Policy", "active"),
        ("Incident Response Policy", "draft"),
    ]:
        conn.execute(
            "INSERT INTO policies (title, type, status) VALUES (?, 'information_security', ?)",
            (title, p_status),
        )

    future = (datetime.now() + timedelta(days=90)).isoformat()
    conn.execute(
        "INSERT INTO evidence (title, status, valid_until, type) "
        "VALUES ('AWS IAM Export', 'active', ?, 'automated')",
        (future,),
    )

    conn.execute(
        "INSERT INTO vendors (name, criticality, status) VALUES ('Acme Corp', 'high', 'active')"
    )

    conn.commit()
    conn.close()

    return v2_db
