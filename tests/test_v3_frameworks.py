"""Tests for V3 Step 8.5 Framework Activation.

Tests for 4 new framework JSONs:
  - CIS Controls v8 (V3-T4.1, V3-T4.5, V3-T4.7)
  - CMMC 2.0 (V3-T4.2, V3-T4.6)
  - HITRUST CSF (V3-T4.3)
  - CCPA/CPRA (V3-T4.4)
  - All 10 frameworks status check (V3-T4.8)
"""

import json
import sqlite3

import pytest

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))

from conftest import run_script


def _run(action, db_path, **kwargs):
    """Run db_query.py with --action and keyword args as CLI flags."""
    args = ["--action", action]
    for k, v in kwargs.items():
        flag = f"--{k.replace('_', '-')}"
        if isinstance(v, bool) and v:
            args.append(flag)
        else:
            args.extend([flag, str(v)])
    return run_script("db_query.py", args, db_path=db_path)


# ===========================================================================
# CIS Controls
# ===========================================================================

class TestActivateCISControls:
    """V3-T4.1, V3-T4.5, V3-T4.7: CIS Controls v8."""

    def test_activate_cis_controls(self, temp_db):
        """V3-T4.1: Activate CIS Controls, expect ~150 controls."""
        result, stderr, code = _run("activate-framework", temp_db, slug="cis-controls")
        assert code == 0, f"Activation failed: {stderr}"
        assert result["status"] == "activated"
        assert result["controls_loaded"] >= 140  # ~150 safeguards

    def test_activate_cis_categories(self, temp_db):
        """V3-T4.5: Verify 18 control groups present as categories."""
        _run("activate-framework", temp_db, slug="cis-controls")

        conn = sqlite3.connect(temp_db)
        cats = conn.execute(
            "SELECT DISTINCT category FROM controls c JOIN frameworks f ON c.framework_id = f.id WHERE f.slug = 'cis-controls'"
        ).fetchall()
        conn.close()
        cat_names = [r[0] for r in cats]
        assert len(cat_names) >= 18, f"Expected 18+ categories, got {len(cat_names)}: {cat_names}"

    def test_cis_controls_idempotent(self, temp_db):
        """V3-T4.7: Activate twice returns already_active."""
        _run("activate-framework", temp_db, slug="cis-controls")
        result, _, code = _run("activate-framework", temp_db, slug="cis-controls")
        assert code == 0
        assert result["status"] == "already_active"


# ===========================================================================
# CMMC 2.0
# ===========================================================================

class TestActivateCMMC:
    """V3-T4.2, V3-T4.6: CMMC 2.0."""

    def test_activate_cmmc(self, temp_db):
        """V3-T4.2: Activate CMMC 2.0, expect ~110 controls."""
        result, stderr, code = _run("activate-framework", temp_db, slug="cmmc")
        assert code == 0, f"Activation failed: {stderr}"
        assert result["status"] == "activated"
        assert result["controls_loaded"] >= 100  # ~110 practices

    def test_activate_cmmc_levels(self, temp_db):
        """V3-T4.6: Verify CMMC level categories present."""
        _run("activate-framework", temp_db, slug="cmmc")

        conn = sqlite3.connect(temp_db)
        cats = conn.execute(
            "SELECT DISTINCT category FROM controls c JOIN frameworks f ON c.framework_id = f.id WHERE f.slug = 'cmmc'"
        ).fetchall()
        conn.close()
        cat_names = [r[0] for r in cats]
        # Should have categories containing Level 1, Level 2, Level 3
        has_l1 = any("Level 1" in c or "L1" in c for c in cat_names)
        has_l2 = any("Level 2" in c or "L2" in c for c in cat_names)
        has_l3 = any("Level 3" in c or "L3" in c for c in cat_names)
        assert has_l1, f"No Level 1 categories found in {cat_names}"
        assert has_l2, f"No Level 2 categories found in {cat_names}"
        assert has_l3, f"No Level 3 categories found in {cat_names}"


# ===========================================================================
# HITRUST CSF
# ===========================================================================

class TestActivateHITRUST:
    """V3-T4.3: HITRUST CSF."""

    def test_activate_hitrust(self, temp_db):
        """V3-T4.3: Activate HITRUST CSF, expect ~150 controls."""
        result, stderr, code = _run("activate-framework", temp_db, slug="hitrust")
        assert code == 0, f"Activation failed: {stderr}"
        assert result["status"] == "activated"
        assert result["controls_loaded"] >= 140  # ~150 controls


# ===========================================================================
# CCPA/CPRA
# ===========================================================================

class TestActivateCCPA:
    """V3-T4.4: CCPA/CPRA."""

    def test_activate_ccpa(self, temp_db):
        """V3-T4.4: Activate CCPA/CPRA, expect ~20-30 controls."""
        result, stderr, code = _run("activate-framework", temp_db, slug="ccpa")
        assert code == 0, f"Activation failed: {stderr}"
        assert result["status"] == "activated"
        assert result["controls_loaded"] >= 20


# ===========================================================================
# All 10 frameworks status check
# ===========================================================================

class TestAllFrameworksStatus:
    """V3-T4.8: Activate all 10 frameworks, verify status."""

    def test_ten_frameworks_status(self, temp_db):
        """V3-T4.8: Activate all 10, run status, verify all shown."""
        all_slugs = [
            "soc2", "iso27001", "nist-csf", "hipaa", "gdpr", "pci-dss",
            "cis-controls", "cmmc", "hitrust", "ccpa",
        ]
        for slug in all_slugs:
            result, stderr, code = _run("activate-framework", temp_db, slug=slug)
            assert code == 0, f"Activation of {slug} failed: {stderr}"
            assert result["status"] == "activated", f"{slug}: {result}"

        # Run status
        status, _, code = _run("status", temp_db)
        assert code == 0
        assert len(status["frameworks"]) == 10

        # Verify each framework has controls
        conn = sqlite3.connect(temp_db)
        for slug in all_slugs:
            count = conn.execute(
                "SELECT COUNT(*) FROM controls c JOIN frameworks f ON c.framework_id = f.id WHERE f.slug = ?",
                (slug,)
            ).fetchone()[0]
            assert count > 0, f"Framework {slug} has 0 controls"
        conn.close()
