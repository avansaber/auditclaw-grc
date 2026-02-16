"""T8.x — Evidence export tests.

Tests export_evidence.py with seeded databases.
"""

import json
import os
import subprocess
import tempfile
import zipfile
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


def create_seeded_db(with_evidence=False):
    """Create a DB with an activated framework and optionally evidence."""
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

    if with_evidence:
        # Add evidence linked to first control
        subprocess.run(
            ["python3", os.path.join(SCRIPTS_DIR, "db_query.py"),
             "--action", "add-evidence",
             "--title", "Test MFA Screenshot",
             "--type", "manual",
             "--source", "manual",
             "--valid-from", "2026-01-01",
             "--valid-until", "2026-12-31",
             "--control-ids", "1",
             "--db-path", path],
            capture_output=True, check=True
        )

    return path


class TestZipCreated:
    """T8.1 — ZIP file is created."""

    def test_zip_created(self):
        """T8.1 — ZIP file exists at output path."""
        db = create_seeded_db(with_evidence=True)
        output_dir = tempfile.mkdtemp()
        try:
            r = subprocess.run(
                ["python3", os.path.join(SCRIPTS_DIR, "export_evidence.py"),
                 "--framework", "soc2", "--output-dir", output_dir, "--db-path", db],
                capture_output=True, text=True
            )
            result = json.loads(r.stdout)
            assert result["status"] == "exported"
            assert os.path.exists(result["zip_path"])
            assert result["zip_path"].endswith(".zip")
        finally:
            os.unlink(db)
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)


class TestZipContainsManifest:
    """T8.2 — ZIP contains manifest.json."""

    def test_zip_contains_manifest(self):
        """T8.2 — manifest.json is inside ZIP and is valid JSON."""
        db = create_seeded_db(with_evidence=True)
        output_dir = tempfile.mkdtemp()
        try:
            r = subprocess.run(
                ["python3", os.path.join(SCRIPTS_DIR, "export_evidence.py"),
                 "--framework", "soc2", "--output-dir", output_dir, "--db-path", db],
                capture_output=True, text=True
            )
            result = json.loads(r.stdout)
            with zipfile.ZipFile(result["zip_path"]) as zf:
                assert "manifest.json" in zf.namelist()
                manifest = json.loads(zf.read("manifest.json"))
                assert manifest["framework"] == "soc2"
                assert "evidence_items" in manifest
        finally:
            os.unlink(db)
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)


class TestZipContainsSummary:
    """T8.3 — ZIP contains summary.md."""

    def test_zip_contains_summary(self):
        """T8.3 — summary.md is inside ZIP."""
        db = create_seeded_db(with_evidence=True)
        output_dir = tempfile.mkdtemp()
        try:
            r = subprocess.run(
                ["python3", os.path.join(SCRIPTS_DIR, "export_evidence.py"),
                 "--framework", "soc2", "--output-dir", output_dir, "--db-path", db],
                capture_output=True, text=True
            )
            result = json.loads(r.stdout)
            with zipfile.ZipFile(result["zip_path"]) as zf:
                assert "summary.md" in zf.namelist()
                summary = zf.read("summary.md").decode()
                assert "SOC 2" in summary
                assert "Total Controls" in summary
        finally:
            os.unlink(db)
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)


class TestEmptyEvidence:
    """T8.4 — Export with no evidence still creates valid ZIP."""

    def test_empty_evidence(self):
        """T8.4 — ZIP created with summary noting no evidence."""
        db = create_seeded_db(with_evidence=False)
        output_dir = tempfile.mkdtemp()
        try:
            r = subprocess.run(
                ["python3", os.path.join(SCRIPTS_DIR, "export_evidence.py"),
                 "--framework", "soc2", "--output-dir", output_dir, "--db-path", db],
                capture_output=True, text=True
            )
            result = json.loads(r.stdout)
            assert result["status"] == "exported"
            assert result["evidence_records"] == 0

            with zipfile.ZipFile(result["zip_path"]) as zf:
                summary = zf.read("summary.md").decode()
                assert "No evidence" in summary or "no evidence" in summary.lower()
        finally:
            os.unlink(db)
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)
