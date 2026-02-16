"""T7.x — Report generation tests.

Tests generate_report.py with seeded databases.
"""

import json
import os
import subprocess
import tempfile
import sqlite3
import pytest

SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts"
)

ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "frameworks"
)


def create_seeded_db():
    """Create a DB with an activated framework."""
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    subprocess.run(
        ["python3", os.path.join(SCRIPTS_DIR, "init_db.py"), "--db-path", path],
        capture_output=True, check=True
    )
    # Activate SOC 2
    soc2_path = os.path.join(ASSETS_DIR, "soc2.json")
    subprocess.run(
        ["python3", os.path.join(SCRIPTS_DIR, "db_query.py"),
         "--action", "activate-framework", "--slug", "soc2",
         "--framework-file", soc2_path, "--db-path", path],
        capture_output=True, check=True
    )
    return path


class TestHTMLReportGenerated:
    """T7.1 — HTML report file is created."""

    def test_html_report_generated(self):
        """T7.1 — Report file exists and contains framework name."""
        db = create_seeded_db()
        output_dir = tempfile.mkdtemp()
        try:
            r = subprocess.run(
                ["python3", os.path.join(SCRIPTS_DIR, "generate_report.py"),
                 "--framework", "soc2", "--db-path", db, "--output-dir", output_dir],
                capture_output=True, text=True
            )
            result = json.loads(r.stdout)
            assert result["status"] == "generated"
            assert os.path.exists(result["path"])

            with open(result["path"]) as f:
                html = f.read()
            assert "SOC 2" in html
        finally:
            os.unlink(db)
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)


class TestHTMLContainsScore:
    """T7.2 — HTML contains the compliance score."""

    def test_html_contains_score(self):
        """T7.2 — Score value appears in the generated HTML."""
        db = create_seeded_db()
        output_dir = tempfile.mkdtemp()
        try:
            r = subprocess.run(
                ["python3", os.path.join(SCRIPTS_DIR, "generate_report.py"),
                 "--framework", "soc2", "--db-path", db, "--output-dir", output_dir],
                capture_output=True, text=True
            )
            result = json.loads(r.stdout)
            with open(result["path"]) as f:
                html = f.read()
            # Score should be in the HTML (0 for all not_started)
            assert "/100" in html
        finally:
            os.unlink(db)
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)


class TestHTMLContainsControls:
    """T7.3 — HTML contains control table."""

    def test_html_contains_controls(self):
        """T7.3 — Control data appears in the report."""
        db = create_seeded_db()
        output_dir = tempfile.mkdtemp()
        try:
            r = subprocess.run(
                ["python3", os.path.join(SCRIPTS_DIR, "generate_report.py"),
                 "--framework", "soc2", "--db-path", db, "--output-dir", output_dir],
                capture_output=True, text=True
            )
            result = json.loads(r.stdout)
            with open(result["path"]) as f:
                html = f.read()
            # Should contain at least one control ID
            assert "CC1.1" in html
            assert "<table>" in html
        finally:
            os.unlink(db)
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)


class TestUnknownFramework:
    """T7.4 — Unknown framework returns error."""

    def test_unknown_framework(self):
        """T7.4 — Invalid framework slug returns error."""
        db = create_seeded_db()
        output_dir = tempfile.mkdtemp()
        try:
            r = subprocess.run(
                ["python3", os.path.join(SCRIPTS_DIR, "generate_report.py"),
                 "--framework", "nonexistent", "--db-path", db, "--output-dir", output_dir],
                capture_output=True, text=True
            )
            assert r.returncode == 1
            result = json.loads(r.stdout)
            assert result["status"] == "error"
        finally:
            os.unlink(db)
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)
