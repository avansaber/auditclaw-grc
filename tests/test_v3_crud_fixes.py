"""Tests for V3 Step 8.0 CRUD completeness fixes.

Tests for 4 new actions:
  - list-policies (T3.0.1 – T3.0.3)
  - update-policy (T3.0.4 – T3.0.6)
  - update-risk (T3.0.7 – T3.0.9)
  - update-vendor (T3.0.10 – T3.0.12)
"""

import json
import sqlite3
from datetime import datetime, timedelta

import pytest

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))

from conftest import run_script, make_args, get_v2_connection


def _parse_error(stderr):
    """Parse error JSON from stderr (db_query.py prints errors to stderr)."""
    try:
        return json.loads(stderr.strip())
    except (json.JSONDecodeError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _seed_policies(db_path, count=3):
    """Insert sample policies, return list of ids."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    ids = []
    policies = [
        ("Information Security Policy", "information_security", "active",
         (datetime.now() - timedelta(days=10)).isoformat()),
        ("Access Control Policy", "access_control", "active",
         (datetime.now() + timedelta(days=90)).isoformat()),
        ("Incident Response Plan", "incident_response", "draft", None),
    ]
    for title, ptype, status, review_date in policies[:count]:
        conn.execute(
            "INSERT INTO policies (title, type, status, review_date) VALUES (?, ?, ?, ?)",
            (title, ptype, status, review_date),
        )
        ids.append(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    conn.commit()
    conn.close()
    return ids


def _seed_risks(db_path, count=2):
    """Insert sample risks, return list of ids."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    ids = []
    risks = [
        ("Unpatched servers", "security", 3, 4, "open"),
        ("Key employee departure", "operational", 2, 3, "open"),
    ]
    for title, category, likelihood, impact, status in risks[:count]:
        conn.execute(
            "INSERT INTO risks (title, category, likelihood, impact, status) VALUES (?, ?, ?, ?, ?)",
            (title, category, likelihood, impact, status),
        )
        ids.append(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    conn.commit()
    conn.close()
    return ids


def _seed_vendors(db_path, count=2):
    """Insert sample vendors, return list of ids."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    ids = []
    vendors = [
        ("AWS", "cloud", "critical", "active",
         (datetime.now() - timedelta(days=30)).isoformat()),
        ("Acme SaaS", "software", "medium", "active",
         (datetime.now() + timedelta(days=60)).isoformat()),
    ]
    for name, category, criticality, status, next_assessment in vendors[:count]:
        conn.execute(
            "INSERT INTO vendors (name, category, criticality, status, next_assessment_date) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, category, criticality, status, next_assessment),
        )
        ids.append(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    conn.commit()
    conn.close()
    return ids


# ===========================================================================
# list-policies
# ===========================================================================

class TestListPolicies:
    """T3.0.1 – T3.0.3: List policies with filters."""

    def test_list_policies_all(self, soc2_db):
        """T3.0.1: List all policies returns correct count."""
        _seed_policies(soc2_db)
        result, stderr, code = _run("list-policies", soc2_db)
        assert code == 0
        assert result["status"] == "ok"
        assert result["count"] == 3

    def test_list_policies_by_status(self, soc2_db):
        """T3.0.2: Filter policies by status."""
        _seed_policies(soc2_db)
        result, _, code = _run("list-policies", soc2_db, status="active")
        assert code == 0
        assert result["count"] == 2
        assert all(p["status"] == "active" for p in result["policies"])

    def test_list_policies_by_type(self, soc2_db):
        """T3.0.2b: Filter policies by type."""
        _seed_policies(soc2_db)
        result, _, code = _run("list-policies", soc2_db, type="access_control")
        assert code == 0
        assert result["count"] == 1
        assert result["policies"][0]["title"] == "Access Control Policy"

    def test_list_policies_review_due(self, soc2_db):
        """T3.0.3: Filter policies with overdue reviews."""
        _seed_policies(soc2_db)
        result, _, code = _run("list-policies", soc2_db, review_due=True)
        assert code == 0
        # Only "Information Security Policy" has review_date in the past and status=active
        assert result["count"] == 1
        assert result["policies"][0]["title"] == "Information Security Policy"

    def test_list_policies_empty(self, soc2_db):
        """List policies returns zero count on empty table."""
        result, _, code = _run("list-policies", soc2_db)
        assert code == 0
        assert result["count"] == 0


# ===========================================================================
# update-policy
# ===========================================================================

class TestUpdatePolicy:
    """T3.0.4 – T3.0.6: Update policy fields."""

    def test_update_policy_status(self, soc2_db):
        """T3.0.4: Update policy status from draft to active."""
        ids = _seed_policies(soc2_db)
        draft_id = ids[2]  # "Incident Response Plan" is draft

        result, _, code = _run("update-policy", soc2_db, id=draft_id, status="active")
        assert code == 0
        assert result["status"] == "updated"

        conn = sqlite3.connect(soc2_db)
        row = conn.execute("SELECT status, last_updated FROM policies WHERE id = ?", (draft_id,)).fetchone()
        conn.close()
        assert row[0] == "active"
        assert row[1] is not None  # last_updated set

    def test_update_policy_approval(self, soc2_db):
        """T3.0.5: Set approved_by auto-sets approved_at."""
        ids = _seed_policies(soc2_db)
        result, _, code = _run(
            "update-policy", soc2_db, id=ids[0], approved_by="CISO", status="approved"
        )
        assert code == 0

        conn = sqlite3.connect(soc2_db)
        row = conn.execute(
            "SELECT approved_by, approved_at FROM policies WHERE id = ?", (ids[0],)
        ).fetchone()
        conn.close()
        assert row[0] == "CISO"
        assert row[1] is not None  # approved_at auto-set

    def test_update_policy_version(self, soc2_db):
        """T3.0.6: Update policy version and review_date."""
        ids = _seed_policies(soc2_db)
        future = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        result, _, code = _run(
            "update-policy", soc2_db, id=ids[0], version="2.0", review_date=future
        )
        assert code == 0

        conn = sqlite3.connect(soc2_db)
        row = conn.execute(
            "SELECT version, review_date FROM policies WHERE id = ?", (ids[0],)
        ).fetchone()
        conn.close()
        assert row[0] == "2.0"
        assert row[1] == future

    def test_update_policy_not_found(self, soc2_db):
        """Update non-existent policy returns error."""
        result, stderr, code = _run("update-policy", soc2_db, id=9999, status="active")
        assert code != 0
        err = _parse_error(stderr)
        assert err["status"] == "error"
        assert "not found" in err["message"].lower()

    def test_update_policy_no_fields(self, soc2_db):
        """Update with no fields returns error."""
        ids = _seed_policies(soc2_db)
        result, stderr, code = _run("update-policy", soc2_db, id=ids[0])
        assert code != 0
        err = _parse_error(stderr)
        assert err["status"] == "error"
        assert "no fields" in err["message"].lower()


# ===========================================================================
# update-risk
# ===========================================================================

class TestUpdateRisk:
    """T3.0.7 – T3.0.9: Update risk fields."""

    def test_update_risk_status(self, soc2_db):
        """T3.0.7: Update risk status to mitigated."""
        ids = _seed_risks(soc2_db)
        result, _, code = _run("update-risk", soc2_db, id=ids[0], status="mitigated")
        assert code == 0
        assert result["status"] == "updated"
        assert result["risk"]["status"] == "mitigated"

    def test_update_risk_recalculates_score(self, soc2_db):
        """T3.0.8: Changing likelihood/impact auto-recalculates score."""
        ids = _seed_risks(soc2_db)
        # Original: likelihood=3, impact=4, score=12
        result, _, code = _run(
            "update-risk", soc2_db, id=ids[0], likelihood=5, impact=5
        )
        assert code == 0
        assert result["risk"]["score"] == 25  # 5*5
        assert result["risk"]["level"] == "critical"

    def test_update_risk_treatment(self, soc2_db):
        """T3.0.9: Update treatment strategy and plan."""
        ids = _seed_risks(soc2_db)
        result, _, code = _run(
            "update-risk", soc2_db,
            id=ids[0], treatment="mitigate", treatment_plan="Deploy automated patching"
        )
        assert code == 0

        conn = sqlite3.connect(soc2_db)
        row = conn.execute(
            "SELECT treatment, treatment_plan, last_updated FROM risks WHERE id = ?", (ids[0],)
        ).fetchone()
        conn.close()
        assert row[0] == "mitigate"
        assert row[1] == "Deploy automated patching"
        assert row[2] is not None  # last_updated set

    def test_update_risk_not_found(self, soc2_db):
        """Update non-existent risk returns error."""
        result, stderr, code = _run("update-risk", soc2_db, id=9999, status="closed")
        assert code != 0
        err = _parse_error(stderr)
        assert err["status"] == "error"
        assert "not found" in err["message"].lower()

    def test_update_risk_no_fields(self, soc2_db):
        """Update with no fields returns error."""
        ids = _seed_risks(soc2_db)
        result, stderr, code = _run("update-risk", soc2_db, id=ids[0])
        assert code != 0
        err = _parse_error(stderr)
        assert err["status"] == "error"
        assert "no fields" in err["message"].lower()


# ===========================================================================
# update-vendor
# ===========================================================================

class TestUpdateVendor:
    """T3.0.10 – T3.0.12: Update vendor fields."""

    def test_update_vendor_status(self, soc2_db):
        """T3.0.10: Update vendor status to inactive."""
        ids = _seed_vendors(soc2_db)
        result, _, code = _run("update-vendor", soc2_db, id=ids[0], status="inactive")
        assert code == 0
        assert result["status"] == "updated"

        conn = sqlite3.connect(soc2_db)
        row = conn.execute("SELECT status FROM vendors WHERE id = ?", (ids[0],)).fetchone()
        conn.close()
        assert row[0] == "inactive"

    def test_update_vendor_risk_score(self, soc2_db):
        """T3.0.11: Update vendor risk score and next assessment date."""
        ids = _seed_vendors(soc2_db)
        future = (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")
        result, _, code = _run(
            "update-vendor", soc2_db,
            id=ids[0], risk_score=85, next_assessment_date=future
        )
        assert code == 0

        conn = sqlite3.connect(soc2_db)
        row = conn.execute(
            "SELECT risk_score, next_assessment_date FROM vendors WHERE id = ?", (ids[0],)
        ).fetchone()
        conn.close()
        assert row[0] == 85
        assert row[1] == future

    def test_update_vendor_criticality(self, soc2_db):
        """T3.0.12: Update vendor criticality and notes."""
        ids = _seed_vendors(soc2_db)
        result, _, code = _run(
            "update-vendor", soc2_db,
            id=ids[1], criticality="critical", notes="Elevated after data access review"
        )
        assert code == 0

        conn = sqlite3.connect(soc2_db)
        row = conn.execute(
            "SELECT criticality, notes FROM vendors WHERE id = ?", (ids[1],)
        ).fetchone()
        conn.close()
        assert row[0] == "critical"
        assert row[1] == "Elevated after data access review"

    def test_update_vendor_not_found(self, soc2_db):
        """Update non-existent vendor returns error."""
        result, stderr, code = _run("update-vendor", soc2_db, id=9999, status="inactive")
        assert code != 0
        err = _parse_error(stderr)
        assert err["status"] == "error"
        assert "not found" in err["message"].lower()

    def test_update_vendor_no_fields(self, soc2_db):
        """Update with no fields returns error."""
        ids = _seed_vendors(soc2_db)
        result, stderr, code = _run("update-vendor", soc2_db, id=ids[0])
        assert code != 0
        err = _parse_error(stderr)
        assert err["status"] == "error"
        assert "no fields" in err["message"].lower()
