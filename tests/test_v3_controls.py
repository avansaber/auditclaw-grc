"""Tests for V3 Step 8.4 + 8.6 Control Effectiveness & Test Results.

Tests for 5 new actions + enhanced list-controls:
  - update-control-effectiveness (V3-T3.1 – V3-T3.4)
  - list-controls-by-maturity (V3-T3.5, V3-T3.7)
  - enhanced list-controls with --min-effectiveness (V3-T3.6)
  - add-test-result (V3-T3.8 – V3-T3.10)
  - list-test-results (V3-T3.11 – V3-T3.12)
  - test-summary (V3-T3.13 – V3-T3.14)
"""

import json
import sqlite3

import pytest

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))

from conftest import run_script, get_v2_connection


def _parse_error(stderr):
    """Parse error JSON from stderr."""
    try:
        return json.loads(stderr.strip())
    except (json.JSONDecodeError, AttributeError):
        return None


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


def _ensure_v3_tables(db_path):
    """Run migrate_v3.py to ensure V3 tables exist."""
    scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
    migrate_script = os.path.join(scripts_dir, "migrate_v3.py")
    run_script(migrate_script, db_path=db_path)


def _get_control_id(db_path):
    """Get the first control ID from the DB (SOC 2 activated)."""
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT id FROM controls LIMIT 1").fetchone()
    conn.close()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Fixture: soc2_db with V3 migration applied
# ---------------------------------------------------------------------------

@pytest.fixture
def v3_db(soc2_db):
    """SOC 2 DB with V3 migration applied."""
    _ensure_v3_tables(soc2_db)
    return soc2_db


# ===========================================================================
# update-control-effectiveness
# ===========================================================================

class TestUpdateControlEffectiveness:
    """V3-T3.1 – V3-T3.4: Control effectiveness scoring."""

    def test_update_control_effectiveness(self, v3_db):
        """V3-T3.1: Set effectiveness score and maturity level."""
        cid = _get_control_id(v3_db)
        result, _, code = _run(
            "update-control-effectiveness", v3_db,
            id=cid, effectiveness_score=85, maturity_level="defined"
        )
        assert code == 0
        assert result["status"] == "updated"

        conn = sqlite3.connect(v3_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM controls WHERE id = ?", (cid,)).fetchone()
        conn.close()
        assert row["effectiveness_score"] == 85
        assert row["maturity_level"] == "defined"
        assert row["effectiveness_rating"] == "effective"  # 85 >= 80

    def test_update_control_effectiveness_rating_auto(self, v3_db):
        """V3-T3.2: Score 90 -> rating 'effective'."""
        cid = _get_control_id(v3_db)
        _run("update-control-effectiveness", v3_db, id=cid, effectiveness_score=90)

        conn = sqlite3.connect(v3_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT effectiveness_rating FROM controls WHERE id = ?", (cid,)).fetchone()
        conn.close()
        assert row["effectiveness_rating"] == "effective"

    def test_update_control_effectiveness_rating_partial(self, v3_db):
        """V3-T3.3: Score 65 -> rating 'partially_effective'."""
        cid = _get_control_id(v3_db)
        _run("update-control-effectiveness", v3_db, id=cid, effectiveness_score=65)

        conn = sqlite3.connect(v3_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT effectiveness_rating FROM controls WHERE id = ?", (cid,)).fetchone()
        conn.close()
        assert row["effectiveness_rating"] == "partially_effective"

    def test_update_control_effectiveness_rating_ineffective(self, v3_db):
        """V3-T3.4: Score 30 -> rating 'ineffective'."""
        cid = _get_control_id(v3_db)
        _run("update-control-effectiveness", v3_db, id=cid, effectiveness_score=30)

        conn = sqlite3.connect(v3_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT effectiveness_rating FROM controls WHERE id = ?", (cid,)).fetchone()
        conn.close()
        assert row["effectiveness_rating"] == "ineffective"


# ===========================================================================
# list-controls-by-maturity
# ===========================================================================

class TestListControlsByMaturity:
    """V3-T3.5, V3-T3.7: Filter and distribution."""

    def test_list_controls_by_maturity(self, v3_db):
        """V3-T3.5: Filter controls by maturity level."""
        conn = sqlite3.connect(v3_db)
        ids = [r[0] for r in conn.execute("SELECT id FROM controls LIMIT 5").fetchall()]
        conn.execute("UPDATE controls SET maturity_level = 'optimizing' WHERE id IN ({})".format(
            ",".join(str(i) for i in ids[:2])
        ))
        conn.execute("UPDATE controls SET maturity_level = 'initial' WHERE id IN ({})".format(
            ",".join(str(i) for i in ids[2:])
        ))
        conn.commit()
        conn.close()

        result, _, code = _run("list-controls-by-maturity", v3_db, maturity_level="optimizing")
        assert code == 0
        assert result["count"] == 2
        for c in result["controls"]:
            assert c["maturity_level"] == "optimizing"

    def test_list_controls_maturity_distribution(self, v3_db):
        """V3-T3.7: Distribution counts per level."""
        conn = sqlite3.connect(v3_db)
        ids = [r[0] for r in conn.execute("SELECT id FROM controls LIMIT 6").fetchall()]
        conn.execute("UPDATE controls SET maturity_level = 'initial' WHERE id = ?", (ids[0],))
        conn.execute("UPDATE controls SET maturity_level = 'developing' WHERE id = ?", (ids[1],))
        conn.execute("UPDATE controls SET maturity_level = 'defined' WHERE id IN (?,?)", (ids[2], ids[3]))
        conn.execute("UPDATE controls SET maturity_level = 'managed' WHERE id = ?", (ids[4],))
        conn.execute("UPDATE controls SET maturity_level = 'optimizing' WHERE id = ?", (ids[5],))
        conn.commit()
        conn.close()

        result, _, code = _run("list-controls-by-maturity", v3_db)
        assert code == 0
        assert result["count"] == 6
        dist = result["maturity_distribution"]
        assert dist["initial"] == 1
        assert dist["developing"] == 1
        assert dist["defined"] == 2
        assert dist["managed"] == 1
        assert dist["optimizing"] == 1


# ===========================================================================
# Enhanced list-controls with --min-effectiveness
# ===========================================================================

class TestListControlsMinEffectiveness:
    """V3-T3.6: Filter controls by minimum effectiveness score."""

    def test_list_controls_by_min_effectiveness(self, v3_db):
        """V3-T3.6: Only controls with score >= threshold."""
        conn = sqlite3.connect(v3_db)
        ids = [r[0] for r in conn.execute("SELECT id FROM controls LIMIT 4").fetchall()]
        conn.execute("UPDATE controls SET effectiveness_score = 90 WHERE id = ?", (ids[0],))
        conn.execute("UPDATE controls SET effectiveness_score = 75 WHERE id = ?", (ids[1],))
        conn.execute("UPDATE controls SET effectiveness_score = 50 WHERE id = ?", (ids[2],))
        conn.execute("UPDATE controls SET effectiveness_score = 30 WHERE id = ?", (ids[3],))
        conn.commit()
        conn.close()

        result, _, code = _run("list-controls", v3_db, min_effectiveness=70)
        assert code == 0
        assert result["count"] == 2
        scores = [c["effectiveness_score"] for c in result["controls"]]
        assert all(s >= 70 for s in scores)


# ===========================================================================
# add-test-result
# ===========================================================================

class TestAddTestResult:
    """V3-T3.8 – V3-T3.10: Record test results."""

    def test_add_test_result(self, v3_db):
        """V3-T3.8: Basic test result."""
        result, _, code = _run(
            "add-test-result", v3_db,
            test_name="S3 Encryption", status="passed",
            items_checked=10, items_passed=10
        )
        assert code == 0
        assert result["status"] == "created"
        assert result["id"] > 0
        assert result["result_status"] == "passed"

    def test_add_test_result_with_control(self, v3_db):
        """V3-T3.9: Linked to control, last_tested_at updated."""
        cid = _get_control_id(v3_db)
        result, _, code = _run(
            "add-test-result", v3_db,
            test_name="Branch Protection", status="failed",
            control_id_ref=cid
        )
        assert code == 0
        assert result["status"] == "created"

        # Verify last_tested_at on control
        conn = sqlite3.connect(v3_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT last_tested_at FROM controls WHERE id = ?", (cid,)).fetchone()
        conn.close()
        assert row["last_tested_at"] is not None

    def test_add_test_result_with_findings(self, v3_db):
        """V3-T3.10: Findings JSON stored."""
        findings = json.dumps([{"message": "Bucket unencrypted", "severity": "high"}])
        result, _, code = _run(
            "add-test-result", v3_db,
            test_name="S3 Encryption", status="failed",
            findings=findings
        )
        assert code == 0

        conn = sqlite3.connect(v3_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT findings FROM test_results WHERE id = ?", (result["id"],)).fetchone()
        conn.close()
        parsed = json.loads(row["findings"])
        assert parsed[0]["severity"] == "high"


# ===========================================================================
# list-test-results
# ===========================================================================

class TestListTestResults:
    """V3-T3.11 – V3-T3.12: List with pass_rate."""

    def test_list_test_results(self, v3_db):
        """V3-T3.11: List results for a control."""
        cid = _get_control_id(v3_db)
        _run("add-test-result", v3_db, test_name="Test A", status="passed", control_id_ref=cid)
        _run("add-test-result", v3_db, test_name="Test B", status="failed", control_id_ref=cid)

        result, _, code = _run("list-test-results", v3_db, control_id_ref=cid)
        assert code == 0
        assert result["count"] == 2

    def test_list_test_results_pass_rate(self, v3_db):
        """V3-T3.12: Correct pass_rate calculation."""
        cid = _get_control_id(v3_db)
        _run("add-test-result", v3_db, test_name="Test", status="passed", control_id_ref=cid)
        _run("add-test-result", v3_db, test_name="Test", status="passed", control_id_ref=cid)
        _run("add-test-result", v3_db, test_name="Test", status="failed", control_id_ref=cid)

        result, _, code = _run("list-test-results", v3_db, control_id_ref=cid)
        assert code == 0
        assert result["count"] == 3
        assert result["pass_rate"] == 66.7  # 2/3


# ===========================================================================
# test-summary
# ===========================================================================

class TestTestSummary:
    """V3-T3.13 – V3-T3.14: Aggregate test statistics."""

    def test_test_summary(self, v3_db):
        """V3-T3.13: Aggregate stats with pass_rate, by_test, trend."""
        _run("add-test-result", v3_db, test_name="S3 Encryption", status="failed")
        _run("add-test-result", v3_db, test_name="S3 Encryption", status="failed")
        _run("add-test-result", v3_db, test_name="S3 Encryption", status="passed")
        _run("add-test-result", v3_db, test_name="S3 Encryption", status="passed")
        _run("add-test-result", v3_db, test_name="Branch Protection", status="passed")
        _run("add-test-result", v3_db, test_name="Branch Protection", status="passed")

        result, _, code = _run("test-summary", v3_db)
        assert code == 0
        assert result["total_runs"] == 6
        assert result["pass_rate"] == 66.7  # 4/6
        assert result["by_status"]["passed"] == 4
        assert result["by_status"]["failed"] == 2
        assert result["by_test"]["S3 Encryption"]["runs"] == 4
        assert result["by_test"]["Branch Protection"]["passed"] == 2
        assert result["trend"] in ("improving", "stable", "declining")

    def test_test_summary_empty(self, v3_db):
        """V3-T3.14: Empty DB returns nulls."""
        result, _, code = _run("test-summary", v3_db)
        assert code == 0
        assert result["total_runs"] == 0
        assert result["pass_rate"] is None
