"""Tests for V3 Step 8.2 Incident Enhancement.

Tests for 6 new actions + enhanced update-incident:
  - add-incident-action (V3-T1.1 – V3-T1.3)
  - list-incident-actions (V3-T1.4 – V3-T1.5)
  - add-incident-review (V3-T1.6 – V3-T1.7)
  - update-incident-review (V3-T1.8)
  - list-incident-reviews (V3-T1.9)
  - incident-summary (V3-T1.10 – V3-T1.11)
  - Enhanced update-incident (V3-T1.12 – V3-T1.14)
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


def _seed_incident(db_path, title="Test Incident", severity="high", status="detected"):
    """Insert an incident and return its id."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute(
        "INSERT INTO incidents (title, type, severity, status) VALUES (?, 'security_breach', ?, ?)",
        (title, severity, status),
    )
    iid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return iid


def _seed_resolved_incident(db_path, title, severity, hours_to_resolve):
    """Insert a resolved incident with known MTTR."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    reported = datetime.now() - timedelta(hours=hours_to_resolve)
    resolved = datetime.now()
    conn.execute(
        "INSERT INTO incidents (title, type, severity, status, reported_at, resolved_at) "
        "VALUES (?, 'security_breach', ?, 'resolved', ?, ?)",
        (title, severity, reported.isoformat(), resolved.isoformat()),
    )
    iid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return iid


# ---------------------------------------------------------------------------
# Fixture: soc2_db with V3 migration applied
# ---------------------------------------------------------------------------

@pytest.fixture
def v3_db(soc2_db):
    """SOC 2 DB with V3 migration applied."""
    _ensure_v3_tables(soc2_db)
    return soc2_db


# ===========================================================================
# add-incident-action
# ===========================================================================

class TestAddIncidentAction:
    """V3-T1.1 – V3-T1.3: Incident timeline actions."""

    def test_add_incident_action(self, v3_db):
        """V3-T1.1: Add basic incident action."""
        iid = _seed_incident(v3_db)
        result, _, code = _run(
            "add-incident-action", v3_db,
            incident_id=iid, action_type="investigation", title="Analyzed logs"
        )
        assert code == 0
        assert result["status"] == "created"
        assert result["id"] > 0
        assert result["action_type"] == "investigation"

    def test_add_incident_action_all_fields(self, v3_db):
        """V3-T1.2: Add action with all fields."""
        iid = _seed_incident(v3_db)
        result, _, code = _run(
            "add-incident-action", v3_db,
            incident_id=iid, action_type="containment",
            title="Isolated server", description="Removed from network",
            outcome="Server isolated within 15 minutes"
        )
        assert code == 0
        assert result["status"] == "created"

        conn = sqlite3.connect(v3_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM incident_actions WHERE id = ?", (result["id"],)).fetchone()
        conn.close()
        assert row["description"] == "Removed from network"
        assert row["outcome"] == "Server isolated within 15 minutes"
        assert row["action_taken_at"] is not None

    def test_add_incident_action_invalid_incident(self, v3_db):
        """V3-T1.3: Invalid incident returns error."""
        result, stderr, code = _run(
            "add-incident-action", v3_db,
            incident_id=99999, action_type="investigation", title="Test"
        )
        assert code != 0
        err = _parse_error(stderr)
        assert err["status"] == "error"
        assert "not found" in err["message"].lower()


# ===========================================================================
# list-incident-actions
# ===========================================================================

class TestListIncidentActions:
    """V3-T1.4 – V3-T1.5: List incident actions."""

    def test_list_incident_actions(self, v3_db):
        """V3-T1.4: List actions ordered by action_taken_at."""
        iid = _seed_incident(v3_db)
        _run("add-incident-action", v3_db, incident_id=iid, action_type="investigation", title="Step 1")
        _run("add-incident-action", v3_db, incident_id=iid, action_type="containment", title="Step 2")
        _run("add-incident-action", v3_db, incident_id=iid, action_type="resolution", title="Step 3")

        result, _, code = _run("list-incident-actions", v3_db, incident_id=iid)
        assert code == 0
        assert result["count"] == 3
        assert result["actions"][0]["title"] == "Step 1"

    def test_list_incident_actions_by_type(self, v3_db):
        """V3-T1.5: Filter actions by type."""
        iid = _seed_incident(v3_db)
        _run("add-incident-action", v3_db, incident_id=iid, action_type="investigation", title="Investigate")
        _run("add-incident-action", v3_db, incident_id=iid, action_type="containment", title="Contain")

        result, _, code = _run("list-incident-actions", v3_db, incident_id=iid, action_type="containment")
        assert code == 0
        assert result["count"] == 1
        assert result["actions"][0]["action_type"] == "containment"


# ===========================================================================
# add-incident-review
# ===========================================================================

class TestAddIncidentReview:
    """V3-T1.6 – V3-T1.7: Post-incident reviews."""

    def test_add_incident_review(self, v3_db):
        """V3-T1.6: Add basic review."""
        iid = _seed_incident(v3_db)
        result, _, code = _run(
            "add-incident-review", v3_db,
            incident_id=iid, conducted_by="Alice"
        )
        assert code == 0
        assert result["status"] == "created"
        assert result["conducted_by"] == "Alice"

    def test_add_incident_review_full(self, v3_db):
        """V3-T1.7: Add review with all fields."""
        iid = _seed_incident(v3_db)
        action_items = json.dumps([{"description": "Deploy MFA", "assignee": "Bob", "due_date": "2026-03-01"}])
        result, _, code = _run(
            "add-incident-review", v3_db,
            incident_id=iid, conducted_by="Alice",
            what_happened="SQL injection via login form",
            what_went_well="Quick detection by monitoring",
            what_went_wrong="No WAF in place",
            lessons_learned="Need WAF and input validation",
            action_items=action_items,
            recommendations="Deploy WAF, add parameterized queries"
        )
        assert code == 0

        conn = sqlite3.connect(v3_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM incident_reviews WHERE id = ?", (result["id"],)).fetchone()
        conn.close()
        assert row["what_happened"] == "SQL injection via login form"
        assert row["what_went_well"] == "Quick detection by monitoring"
        assert row["what_went_wrong"] == "No WAF in place"
        assert row["lessons_learned"] == "Need WAF and input validation"
        assert row["recommendations"] == "Deploy WAF, add parameterized queries"
        items = json.loads(row["action_items"])
        assert items[0]["assignee"] == "Bob"


# ===========================================================================
# update-incident-review
# ===========================================================================

class TestUpdateIncidentReview:
    """V3-T1.8: Update review."""

    def test_update_incident_review_complete(self, v3_db):
        """V3-T1.8: Mark review as completed."""
        iid = _seed_incident(v3_db)
        r, _, _ = _run("add-incident-review", v3_db, incident_id=iid, conducted_by="Alice")
        review_id = r["id"]

        result, _, code = _run("update-incident-review", v3_db, id=review_id, is_completed=1)
        assert code == 0
        assert result["status"] == "updated"

        conn = sqlite3.connect(v3_db)
        row = conn.execute("SELECT is_completed FROM incident_reviews WHERE id = ?", (review_id,)).fetchone()
        conn.close()
        assert row[0] == 1


# ===========================================================================
# list-incident-reviews
# ===========================================================================

class TestListIncidentReviews:
    """V3-T1.9: List reviews."""

    def test_list_incident_reviews(self, v3_db):
        """V3-T1.9: List reviews for an incident."""
        iid = _seed_incident(v3_db)
        _run("add-incident-review", v3_db, incident_id=iid, conducted_by="Alice")
        _run("add-incident-review", v3_db, incident_id=iid, conducted_by="Bob")

        result, _, code = _run("list-incident-reviews", v3_db, incident_id=iid)
        assert code == 0
        assert result["count"] == 2


# ===========================================================================
# incident-summary
# ===========================================================================

class TestIncidentSummary:
    """V3-T1.10 – V3-T1.11: Incident aggregate statistics."""

    def test_incident_summary(self, v3_db):
        """V3-T1.10: Summary with multiple incidents."""
        _seed_incident(v3_db, title="Critical breach", severity="critical")
        _seed_incident(v3_db, title="Minor issue", severity="low")
        _seed_resolved_incident(v3_db, title="Resolved fast", severity="high", hours_to_resolve=4)
        _seed_resolved_incident(v3_db, title="Resolved slow", severity="critical", hours_to_resolve=48)

        result, _, code = _run("incident-summary", v3_db)
        assert code == 0
        assert result["total"] == 4
        assert result["open_count"] == 2
        assert result["resolved_count"] == 2
        assert result["mttr_hours"] is not None
        # MTTR should be approximately (4 + 48) / 2 = 26 hours
        assert 20 < result["mttr_hours"] < 32
        assert result["by_severity"]["critical"] == 2
        assert result["by_severity"]["high"] == 1
        assert result["by_severity"]["low"] == 1

    def test_incident_summary_empty(self, v3_db):
        """V3-T1.11: Summary on empty DB."""
        result, _, code = _run("incident-summary", v3_db)
        assert code == 0
        assert result["total"] == 0
        assert result["mttr_hours"] is None


# ===========================================================================
# Enhanced update-incident (V3 fields)
# ===========================================================================

class TestUpdateIncidentV3:
    """V3-T1.12 – V3-T1.14: Enhanced incident update with costs and regulatory."""

    def test_update_incident_costs(self, v3_db):
        """V3-T1.12: Update estimated and actual costs."""
        iid = _seed_incident(v3_db)
        result, _, code = _run(
            "update-incident", v3_db,
            id=iid, estimated_cost=50000, actual_cost=25000
        )
        assert code == 0

        conn = sqlite3.connect(v3_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT estimated_cost, actual_cost FROM incidents WHERE id = ?", (iid,)).fetchone()
        conn.close()
        assert row["estimated_cost"] == 50000.0
        assert row["actual_cost"] == 25000.0

    def test_update_incident_regulatory(self, v3_db):
        """V3-T1.13: Set regulatory flag and append body to JSON array."""
        iid = _seed_incident(v3_db)
        result, _, code = _run(
            "update-incident", v3_db,
            id=iid, regulatory_required=1, regulatory_body="GDPR DPA"
        )
        assert code == 0

        conn = sqlite3.connect(v3_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT regulatory_notification_required, regulatory_bodies_notified, regulatory_notification_sent_at "
            "FROM incidents WHERE id = ?", (iid,)
        ).fetchone()
        conn.close()
        assert row["regulatory_notification_required"] == 1
        bodies = json.loads(row["regulatory_bodies_notified"])
        assert len(bodies) == 1
        assert bodies[0]["body"] == "GDPR DPA"
        assert row["regulatory_notification_sent_at"] is not None

    def test_update_incident_preventive(self, v3_db):
        """V3-T1.14: Update preventive actions."""
        iid = _seed_incident(v3_db)
        result, _, code = _run(
            "update-incident", v3_db,
            id=iid, preventive_actions="Implement MFA for all admin accounts"
        )
        assert code == 0

        conn = sqlite3.connect(v3_db)
        row = conn.execute("SELECT preventive_actions FROM incidents WHERE id = ?", (iid,)).fetchone()
        conn.close()
        assert row[0] == "Implement MFA for all admin accounts"
