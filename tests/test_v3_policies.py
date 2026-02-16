"""Tests for V3 Step 8.3 Policy Workflows.

Tests for 8 new actions:
  - create-policy-version (V3-T2.1 – V3-T2.2)
  - list-policy-versions (V3-T2.3)
  - submit-policy-approval (V3-T2.4)
  - review-policy-approval (V3-T2.5 – V3-T2.7)
  - list-policy-approvals (V3-T2.8 – V3-T2.9)
  - require-policy-acknowledgment (V3-T2.10)
  - acknowledge-policy (V3-T2.11 – V3-T2.12)
  - list-policy-acknowledgments (V3-T2.13 – V3-T2.15)
  - UNIQUE constraint test (V3-T2.16)
"""

import json
import sqlite3
from datetime import datetime, timedelta

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


def _seed_policy(db_path, title="Security Policy", ptype="information_security", status="draft", version="1.0"):
    """Insert a policy and return its id."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute(
        "INSERT INTO policies (title, type, status, version) VALUES (?, ?, ?, ?)",
        (title, ptype, status, version),
    )
    pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return pid


# ---------------------------------------------------------------------------
# Fixture: soc2_db with V3 migration applied
# ---------------------------------------------------------------------------

@pytest.fixture
def v3_db(soc2_db):
    """SOC 2 DB with V3 migration applied."""
    _ensure_v3_tables(soc2_db)
    return soc2_db


# ===========================================================================
# create-policy-version
# ===========================================================================

class TestCreatePolicyVersion:
    """V3-T2.1 – V3-T2.2: Policy versioning."""

    def test_create_policy_version(self, v3_db):
        """V3-T2.1: Create new version with incremented version number."""
        pid = _seed_policy(v3_db, title="Data Retention Policy")
        result, _, code = _run(
            "create-policy-version", v3_db,
            policy_id=pid, change_summary="Updated retention period"
        )
        assert code == 0
        assert result["status"] == "created"
        assert result["version"] == "2.0"
        assert result["parent_version_id"] == pid
        assert result["policy_status"] == "draft"

        # Verify in DB
        conn = sqlite3.connect(v3_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM policies WHERE id = ?", (result["id"],)).fetchone()
        conn.close()
        assert row["parent_version_id"] == pid
        assert row["change_summary"] == "Updated retention period"
        assert row["title"] == "Data Retention Policy"

    def test_create_policy_version_chain(self, v3_db):
        """V3-T2.2: Create v1 -> v2 -> v3 chain."""
        pid1 = _seed_policy(v3_db, title="Access Control Policy")

        r2, _, code2 = _run("create-policy-version", v3_db, policy_id=pid1, change_summary="v2 changes")
        assert code2 == 0
        assert r2["version"] == "2.0"

        r3, _, code3 = _run("create-policy-version", v3_db, policy_id=r2["id"], change_summary="v3 changes")
        assert code3 == 0
        assert r3["version"] == "3.0"
        assert r3["parent_version_id"] == r2["id"]

        # Verify chain in DB
        conn = sqlite3.connect(v3_db)
        conn.row_factory = sqlite3.Row
        v1 = conn.execute("SELECT * FROM policies WHERE id = ?", (pid1,)).fetchone()
        v2 = conn.execute("SELECT * FROM policies WHERE id = ?", (r2["id"],)).fetchone()
        v3 = conn.execute("SELECT * FROM policies WHERE id = ?", (r3["id"],)).fetchone()
        conn.close()
        assert v1["parent_version_id"] is None
        assert v2["parent_version_id"] == pid1
        assert v3["parent_version_id"] == r2["id"]


# ===========================================================================
# list-policy-versions
# ===========================================================================

class TestListPolicyVersions:
    """V3-T2.3: List all versions in a policy chain."""

    def test_list_policy_versions(self, v3_db):
        """V3-T2.3: List versions returns all in chain."""
        pid1 = _seed_policy(v3_db, title="Incident Response Policy")
        r2, _, _ = _run("create-policy-version", v3_db, policy_id=pid1, change_summary="v2")
        r3, _, _ = _run("create-policy-version", v3_db, policy_id=r2["id"], change_summary="v3")

        # List from any node in the chain
        result, _, code = _run("list-policy-versions", v3_db, policy_id=r3["id"])
        assert code == 0
        assert result["count"] == 3
        versions = result["versions"]
        assert versions[0]["id"] == pid1
        assert versions[1]["id"] == r2["id"]
        assert versions[2]["id"] == r3["id"]


# ===========================================================================
# submit-policy-approval
# ===========================================================================

class TestSubmitPolicyApproval:
    """V3-T2.4: Submit policy for approval."""

    def test_submit_policy_approval(self, v3_db):
        """V3-T2.4: Creates approval record, sets policy status to pending_approval."""
        pid = _seed_policy(v3_db)
        result, _, code = _run(
            "submit-policy-approval", v3_db,
            policy_id=pid, requested_by="Alice"
        )
        assert code == 0
        assert result["status"] == "created"
        assert result["decision"] == "pending"
        assert result["requested_by"] == "Alice"

        # Verify policy status changed
        conn = sqlite3.connect(v3_db)
        conn.row_factory = sqlite3.Row
        policy = conn.execute("SELECT status FROM policies WHERE id = ?", (pid,)).fetchone()
        approval = conn.execute("SELECT * FROM policy_approvals WHERE id = ?", (result["id"],)).fetchone()
        conn.close()
        assert policy["status"] == "pending_approval"
        assert approval["decision"] == "pending"
        assert approval["requested_by"] == "Alice"


# ===========================================================================
# review-policy-approval
# ===========================================================================

class TestReviewPolicyApproval:
    """V3-T2.5 – V3-T2.7: Review approval decisions."""

    def test_review_policy_approved(self, v3_db):
        """V3-T2.5: Approve sets decision=approved, policy status=approved."""
        pid = _seed_policy(v3_db)
        sub, _, _ = _run("submit-policy-approval", v3_db, policy_id=pid, requested_by="Alice")

        result, _, code = _run(
            "review-policy-approval", v3_db,
            id=sub["id"], decision="approved", reviewed_by="CTO"
        )
        assert code == 0
        assert result["status"] == "updated"
        assert result["decision"] == "approved"

        # Verify policy approved_by and approved_at
        conn = sqlite3.connect(v3_db)
        conn.row_factory = sqlite3.Row
        policy = conn.execute("SELECT * FROM policies WHERE id = ?", (pid,)).fetchone()
        conn.close()
        assert policy["status"] == "approved"
        assert policy["approved_by"] == "CTO"
        assert policy["approved_at"] is not None

    def test_review_policy_rejected(self, v3_db):
        """V3-T2.6: Reject reverts policy to draft."""
        pid = _seed_policy(v3_db)
        sub, _, _ = _run("submit-policy-approval", v3_db, policy_id=pid, requested_by="Alice")

        result, _, code = _run(
            "review-policy-approval", v3_db,
            id=sub["id"], decision="rejected", reviewed_by="CTO",
            notes="Needs more detail"
        )
        assert code == 0
        assert result["decision"] == "rejected"

        # Verify policy reverted to draft
        conn = sqlite3.connect(v3_db)
        conn.row_factory = sqlite3.Row
        policy = conn.execute("SELECT status FROM policies WHERE id = ?", (pid,)).fetchone()
        approval = conn.execute("SELECT decision_notes FROM policy_approvals WHERE id = ?", (sub["id"],)).fetchone()
        conn.close()
        assert policy["status"] == "draft"
        assert approval["decision_notes"] == "Needs more detail"

    def test_review_policy_changes_requested(self, v3_db):
        """V3-T2.7: changes_requested reverts policy to draft."""
        pid = _seed_policy(v3_db)
        sub, _, _ = _run("submit-policy-approval", v3_db, policy_id=pid, requested_by="Alice")

        result, _, code = _run(
            "review-policy-approval", v3_db,
            id=sub["id"], decision="changes_requested", reviewed_by="CTO"
        )
        assert code == 0
        assert result["decision"] == "changes_requested"

        conn = sqlite3.connect(v3_db)
        policy = conn.execute("SELECT status FROM policies WHERE id = ?", (pid,)).fetchone()
        conn.close()
        assert policy[0] == "draft"


# ===========================================================================
# list-policy-approvals
# ===========================================================================

class TestListPolicyApprovals:
    """V3-T2.8 – V3-T2.9: List approval audit trail."""

    def test_list_policy_approvals(self, v3_db):
        """V3-T2.8: Returns all approval records for a policy."""
        pid = _seed_policy(v3_db)
        _run("submit-policy-approval", v3_db, policy_id=pid, requested_by="Alice")
        _run("submit-policy-approval", v3_db, policy_id=pid, requested_by="Bob")

        result, _, code = _run("list-policy-approvals", v3_db, policy_id=pid)
        assert code == 0
        assert result["count"] == 2

    def test_list_policy_approvals_by_decision(self, v3_db):
        """V3-T2.9: Filter approvals by decision."""
        pid = _seed_policy(v3_db)
        sub1, _, _ = _run("submit-policy-approval", v3_db, policy_id=pid, requested_by="Alice")
        sub2, _, _ = _run("submit-policy-approval", v3_db, policy_id=pid, requested_by="Bob")
        _run("review-policy-approval", v3_db, id=sub1["id"], decision="approved", reviewed_by="CTO")

        result, _, code = _run("list-policy-approvals", v3_db, policy_id=pid, decision="pending")
        assert code == 0
        assert result["count"] == 1
        assert result["approvals"][0]["requested_by"] == "Bob"


# ===========================================================================
# require-policy-acknowledgment
# ===========================================================================

class TestRequirePolicyAcknowledgment:
    """V3-T2.10: Create acknowledgment requirements."""

    def test_require_policy_acknowledgment(self, v3_db):
        """V3-T2.10: Creates rows for each user with status=pending."""
        pid = _seed_policy(v3_db)
        result, _, code = _run(
            "require-policy-acknowledgment", v3_db,
            policy_id=pid, users="Alice,Bob,Charlie", due_date="2026-04-01"
        )
        assert code == 0
        assert result["status"] == "created"
        assert result["created_count"] == 3
        assert set(result["created_for"]) == {"Alice", "Bob", "Charlie"}

        # Verify in DB
        conn = sqlite3.connect(v3_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM policy_acknowledgments WHERE policy_id = ?", (pid,)
        ).fetchall()
        conn.close()
        assert len(rows) == 3
        for row in rows:
            assert row["status"] == "pending"
            assert row["due_date"] == "2026-04-01"


# ===========================================================================
# acknowledge-policy
# ===========================================================================

class TestAcknowledgePolicy:
    """V3-T2.11 – V3-T2.12: Record acknowledgments."""

    def test_acknowledge_policy(self, v3_db):
        """V3-T2.11: Acknowledges and sets timestamp."""
        pid = _seed_policy(v3_db)
        _run("require-policy-acknowledgment", v3_db, policy_id=pid, users="Alice")

        result, _, code = _run(
            "acknowledge-policy", v3_db,
            policy_id=pid, user_name="Alice"
        )
        assert code == 0
        assert result["status"] == "acknowledged"
        assert result["user_name"] == "Alice"

        # Verify in DB
        conn = sqlite3.connect(v3_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM policy_acknowledgments WHERE policy_id = ? AND user_name = 'Alice'", (pid,)
        ).fetchone()
        conn.close()
        assert row["status"] == "acknowledged"
        assert row["acknowledged_at"] is not None

    def test_acknowledge_policy_duplicate(self, v3_db):
        """V3-T2.12: Second acknowledgment returns already_acknowledged."""
        pid = _seed_policy(v3_db)
        _run("require-policy-acknowledgment", v3_db, policy_id=pid, users="Alice")
        _run("acknowledge-policy", v3_db, policy_id=pid, user_name="Alice")

        result, _, code = _run(
            "acknowledge-policy", v3_db,
            policy_id=pid, user_name="Alice"
        )
        assert code == 0
        assert result["status"] == "already_acknowledged"


# ===========================================================================
# list-policy-acknowledgments
# ===========================================================================

class TestListPolicyAcknowledgments:
    """V3-T2.13 – V3-T2.15: List with rate calculation and filters."""

    def test_list_policy_acknowledgments(self, v3_db):
        """V3-T2.13: All acknowledgments with rate calculation."""
        pid = _seed_policy(v3_db)
        _run("require-policy-acknowledgment", v3_db, policy_id=pid, users="Alice,Bob,Charlie")
        _run("acknowledge-policy", v3_db, policy_id=pid, user_name="Alice")

        result, _, code = _run("list-policy-acknowledgments", v3_db, policy_id=pid)
        assert code == 0
        assert result["count"] == 3
        assert result["acknowledged_count"] == 1
        assert result["pending_count"] == 2
        assert result["acknowledgment_rate"] == 33.3

    def test_list_policy_acknowledgments_pending(self, v3_db):
        """V3-T2.14: Only pending acknowledgments."""
        pid = _seed_policy(v3_db)
        _run("require-policy-acknowledgment", v3_db, policy_id=pid, users="Alice,Bob,Charlie")
        _run("acknowledge-policy", v3_db, policy_id=pid, user_name="Alice")

        result, _, code = _run("list-policy-acknowledgments", v3_db, policy_id=pid, pending=True)
        assert code == 0
        assert result["count"] == 2
        names = {a["user_name"] for a in result["acknowledgments"]}
        assert names == {"Bob", "Charlie"}

    def test_list_policy_acknowledgments_overdue(self, v3_db):
        """V3-T2.15: Only overdue (pending + past due_date)."""
        pid = _seed_policy(v3_db)
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        _run("require-policy-acknowledgment", v3_db, policy_id=pid, users="Alice,Bob", due_date=yesterday)
        _run("acknowledge-policy", v3_db, policy_id=pid, user_name="Alice")

        result, _, code = _run("list-policy-acknowledgments", v3_db, policy_id=pid, overdue=True)
        assert code == 0
        assert result["count"] == 1
        assert result["acknowledgments"][0]["user_name"] == "Bob"


# ===========================================================================
# UNIQUE constraint
# ===========================================================================

class TestPolicyAcknowledgmentUnique:
    """V3-T2.16: UNIQUE(policy_id, user_name) constraint."""

    def test_policy_acknowledgment_unique(self, v3_db):
        """V3-T2.16: Duplicate user+policy is skipped."""
        pid = _seed_policy(v3_db)
        r1, _, _ = _run("require-policy-acknowledgment", v3_db, policy_id=pid, users="Alice")
        assert r1["created_count"] == 1

        r2, _, _ = _run("require-policy-acknowledgment", v3_db, policy_id=pid, users="Alice")
        assert r2["created_count"] == 0
        assert r2["skipped"] == ["Alice"]
