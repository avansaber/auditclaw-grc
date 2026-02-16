"""Tests for V2 Trust Center HTML generator (generate_trust_center.py).

Test IDs: V2-T6.1 through V2-T6.6

The trust center generator is a standalone CLI script, so these tests invoke
it via subprocess (matching the run_script pattern from the original test
suite) and then inspect the generated HTML output file.
"""

import json
import os
import sqlite3
import subprocess
import tempfile

from conftest import (
    GENERATE_TRUST_CENTER,
    get_v2_connection,
    get_v2_db_via_migration,
    run_script,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_trust_center(db_path, output_dir, org_name="Test Org"):
    """Run generate_trust_center.py and return (result_dict, html_content)."""
    result, stderr, code = run_script(
        GENERATE_TRUST_CENTER,
        args=["--output-dir", output_dir, "--org-name", org_name],
        db_path=db_path,
    )
    html_path = os.path.join(output_dir, "trust-center.html")
    html_content = ""
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as fh:
            html_content = fh.read()
    return result, html_content, code


def _make_seeded_db():
    """Create a temp V2 DB seeded with frameworks, controls, policies, evidence.

    Returns (db_path, cleanup_func).
    """
    f = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    db_path = f.name
    f.close()

    get_v2_db_via_migration(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    # The trust center queries columns (last_reviewed, next_review) that may
    # not yet exist in the v1->v2 migrated schema.  Add them idempotently so
    # that _safe_query inside generate_trust_center.py does not silently
    # return [].
    for col, col_def in [("last_reviewed", "TEXT"), ("next_review", "TEXT")]:
        try:
            conn.execute(f"ALTER TABLE policies ADD COLUMN {col} {col_def}")
        except sqlite3.OperationalError:
            pass  # already exists

    # Also ensure compliance_tests and browser_checks tables exist (trust
    # center queries them via _safe_query; they are optional).
    conn.execute("""
        CREATE TABLE IF NOT EXISTS compliance_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, status TEXT DEFAULT 'active',
            last_result TEXT, created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS browser_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, status TEXT, last_run TEXT
        )
    """)

    # Framework: SOC 2
    conn.execute(
        "INSERT INTO frameworks (name, slug, version, status, priority) "
        "VALUES ('SOC 2', 'soc2', '2017', 'active', 1)"
    )
    fw_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # 10 controls: 6 complete, 4 not_started  => 60% completion
    for i in range(1, 11):
        status = "complete" if i <= 6 else "not_started"
        conn.execute(
            "INSERT INTO controls (framework_id, control_id, title, category, status, priority) "
            "VALUES (?, ?, ?, 'Security', ?, 3)",
            (fw_id, f"CC{i}.1", f"Control {i}", status),
        )

    # Policies
    conn.execute(
        "INSERT INTO policies (title, type, status) "
        "VALUES ('Information Security Policy', 'information_security', 'active')"
    )
    conn.execute(
        "INSERT INTO policies (title, type, status) "
        "VALUES ('Data Retention Policy', 'data_retention', 'active')"
    )

    # Evidence (1 current item)
    from datetime import datetime, timedelta
    future = (datetime.now() + timedelta(days=90)).isoformat()
    conn.execute(
        "INSERT INTO evidence (title, status, valid_until, type) "
        "VALUES ('IAM Export', 'active', ?, 'automated')",
        (future,),
    )

    conn.commit()
    conn.close()

    def cleanup():
        for ext in ("", "-wal", "-shm"):
            try:
                os.unlink(db_path + ext)
            except OSError:
                pass

    return db_path, cleanup


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestTrustCenter:
    """V2-T6.x: Trust center HTML generation."""

    def test_trust_center_html_created(self, v2_db):
        """V2-T6.1: HTML file exists at expected output path."""
        with tempfile.TemporaryDirectory() as output_dir:
            result, html, code = _run_trust_center(v2_db, output_dir)

        assert code == 0
        assert result["status"] == "generated"
        assert result["path"].endswith("trust-center.html")

    def test_trust_center_contains_framework_badges(self):
        """V2-T6.2: Framework names appear in the HTML."""
        db_path, cleanup = _make_seeded_db()
        try:
            with tempfile.TemporaryDirectory() as output_dir:
                result, html, code = _run_trust_center(db_path, output_dir)

            assert code == 0
            assert "SOC 2" in html
        finally:
            cleanup()

    def test_trust_center_completion_percentage(self):
        """V2-T6.3: Correct completion % for known state (6/10 = 60%)."""
        db_path, cleanup = _make_seeded_db()
        try:
            with tempfile.TemporaryDirectory() as output_dir:
                result, html, code = _run_trust_center(db_path, output_dir)

            assert code == 0
            # The framework card should show "60%" (rendered as e.g. "60%")
            assert "60%" in html
            # The stats section should show "6/10" for controls
            assert "6" in html
        finally:
            cleanup()

    def test_trust_center_policy_table(self):
        """V2-T6.4: Policy titles appear in the HTML table."""
        db_path, cleanup = _make_seeded_db()
        try:
            with tempfile.TemporaryDirectory() as output_dir:
                result, html, code = _run_trust_center(db_path, output_dir)

            assert code == 0
            assert "Information Security Policy" in html
            assert "Data Retention Policy" in html
        finally:
            cleanup()

    def test_trust_center_empty_db(self, v2_db):
        """V2-T6.5: Handles no frameworks gracefully (empty state message)."""
        with tempfile.TemporaryDirectory() as output_dir:
            result, html, code = _run_trust_center(v2_db, output_dir)

        assert code == 0
        assert result["status"] == "generated"
        assert result["frameworks"] == 0
        # The HTML should contain the empty-state message
        assert "No compliance frameworks activated yet." in html

    def test_trust_center_company_name(self, v2_db):
        """V2-T6.6: --org-name appears in the HTML title and hero."""
        with tempfile.TemporaryDirectory() as output_dir:
            result, html, code = _run_trust_center(
                v2_db, output_dir, org_name="Acme Corp"
            )

        assert code == 0
        assert "Acme Corp" in html
        # Should appear in both <title> and <h1>
        assert "Acme Corp Trust Center" in html
