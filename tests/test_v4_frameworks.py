"""Tests for V4 New Frameworks: FedRAMP, ISO 42001, SOX ITGC (6 tests)."""

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
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "frameworks")
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


class TestFedRAMP:
    """Test FedRAMP Moderate framework."""

    def test_fedramp_json_valid(self):
        """Test that fedramp.json is valid and has expected structure."""
        json_path = os.path.join(ASSETS_DIR, "fedramp.json")
        with open(json_path) as f:
            data = json.load(f)
        assert data["id"] == "fedramp"
        assert "FedRAMP" in data["name"]
        assert len(data["domains"]) >= 15  # At least 15 control families
        total_controls = sum(len(d["controls"]) for d in data["domains"])
        assert total_controls >= 250, f"Expected >=250 controls, got {total_controls}"

    def test_fedramp_activation(self):
        """Test activating FedRAMP framework and scoring."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("activate-framework", db_path,
                ["--slug", "fedramp"])
            assert code == 0
            assert result["status"] in ("ok", "activated")
            assert result["controls_loaded"] >= 250

            # Score should work
            result, stderr, code = _run_action("status", db_path,
                ["--framework", "fedramp"])
            assert code == 0
        finally:
            os.unlink(db_path)


class TestISO42001:
    """Test ISO/IEC 42001:2023 framework."""

    def test_iso42001_json_valid(self):
        """Test that iso42001.json is valid and has expected structure."""
        json_path = os.path.join(ASSETS_DIR, "iso42001.json")
        with open(json_path) as f:
            data = json.load(f)
        assert data["id"] == "iso42001"
        assert "42001" in data["name"]
        assert len(data["domains"]) >= 5  # At least 5 clauses/sections
        total_controls = sum(len(d["controls"]) for d in data["domains"])
        assert total_controls >= 30, f"Expected >=30 controls, got {total_controls}"

    def test_iso42001_activation(self):
        """Test activating ISO 42001 framework and scoring."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("activate-framework", db_path,
                ["--slug", "iso42001"])
            assert code == 0
            assert result["status"] in ("ok", "activated")
            assert result["controls_loaded"] >= 30

            # Score should work
            result, stderr, code = _run_action("status", db_path,
                ["--framework", "iso42001"])
            assert code == 0
        finally:
            os.unlink(db_path)


class TestSOXITGC:
    """Test SOX IT General Controls framework."""

    def test_sox_itgc_json_valid(self):
        """Test that sox-itgc.json is valid and has expected structure."""
        json_path = os.path.join(ASSETS_DIR, "sox-itgc.json")
        with open(json_path) as f:
            data = json.load(f)
        assert data["id"] == "sox-itgc"
        assert "SOX" in data["name"] or "sox" in data["name"].lower()
        assert len(data["domains"]) >= 4  # 4 ITGC domains
        total_controls = sum(len(d["controls"]) for d in data["domains"])
        assert total_controls >= 40, f"Expected >=40 controls, got {total_controls}"

    def test_sox_itgc_activation(self):
        """Test activating SOX ITGC framework and scoring."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name
        try:
            _get_v4_db(db_path)
            result, stderr, code = _run_action("activate-framework", db_path,
                ["--slug", "sox-itgc"])
            assert code == 0
            assert result["status"] in ("ok", "activated")
            assert result["controls_loaded"] >= 40

            # Score should work
            result, stderr, code = _run_action("status", db_path,
                ["--framework", "sox-itgc"])
            assert code == 0
        finally:
            os.unlink(db_path)
