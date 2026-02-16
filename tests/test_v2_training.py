"""Tests for V2 training operations — modules and assignments."""

import sqlite3
from datetime import datetime, timedelta

import pytest

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from actions_batch1 import (
    action_add_training_module,
    action_list_training_modules,
    action_add_training_assignment,
    action_list_training_assignments,
    action_update_training_assignment,
)
from conftest import make_args, get_v2_connection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add_module(conn, **kwargs):
    return action_add_training_module(conn, make_args(**kwargs))


def _list_modules(conn, **kwargs):
    return action_list_training_modules(conn, make_args(**kwargs))


def _add_assignment(conn, **kwargs):
    return action_add_training_assignment(conn, make_args(**kwargs))


def _list_assignments(conn, **kwargs):
    return action_list_training_assignments(conn, make_args(**kwargs))


def _update_assignment(conn, **kwargs):
    return action_update_training_assignment(conn, make_args(**kwargs))


# ---------------------------------------------------------------------------
# Tests — Training Modules
# ---------------------------------------------------------------------------


class TestAddTrainingModule:
    """V2-T2.1 – V2-T2.2: Training module creation."""

    def test_add_training_module(self, v2_db):
        """V2-T2.1: Basic module creation."""
        conn = get_v2_connection(v2_db)
        result = _add_module(conn, title="Security Awareness 101", category="security")

        assert result["status"] == "created"
        assert result["id"] > 0
        assert result["title"] == "Security Awareness 101"

        row = conn.execute(
            "SELECT * FROM training_modules WHERE id = ?", (result["id"],)
        ).fetchone()
        assert row["title"] == "Security Awareness 101"
        assert row["category"] == "security"
        assert row["status"] == "active"
        conn.close()

    def test_add_training_module_full(self, v2_db):
        """V2-T2.2: Module creation with all V2 fields including passing-score and recertification-days."""
        conn = get_v2_connection(v2_db)
        result = _add_module(
            conn,
            title="HIPAA Compliance Training",
            category="compliance",
            description="Annual HIPAA awareness course",
            duration=60,
            content_type="video",
            content_url="https://training.example.com/hipaa",
            difficulty_level="intermediate",
            requires_recertification=1,
            recertification_days=365,
        )

        assert result["status"] == "created"
        row = conn.execute(
            "SELECT * FROM training_modules WHERE id = ?", (result["id"],)
        ).fetchone()

        assert row["description"] == "Annual HIPAA awareness course"
        assert row["content_type"] == "video"
        assert row["content_url"] == "https://training.example.com/hipaa"
        assert row["difficulty_level"] == "intermediate"
        assert row["requires_recertification"] == 1
        assert row["recertification_days"] == 365
        conn.close()


class TestListTrainingModules:
    """V2-T2.3 – V2-T2.4: Training module listing."""

    def _seed_modules(self, conn):
        """Insert a set of training modules."""
        modules = [
            ("Security Awareness", "security"),
            ("GDPR Training", "compliance"),
            ("Phishing Simulation", "security"),
            ("SOC 2 Overview", "compliance"),
        ]
        for title, cat in modules:
            _add_module(conn, title=title, category=cat)

    def test_list_training_modules(self, v2_db):
        """V2-T2.3: List all training modules."""
        conn = get_v2_connection(v2_db)
        self._seed_modules(conn)

        result = _list_modules(conn)
        assert result["status"] == "ok"
        assert result["count"] == 4
        assert len(result["modules"]) == 4
        conn.close()

    def test_list_training_modules_by_category(self, v2_db):
        """V2-T2.4: Filter modules by --category."""
        conn = get_v2_connection(v2_db)
        self._seed_modules(conn)

        result = _list_modules(conn, category="security")
        assert result["status"] == "ok"
        assert result["count"] == 2
        assert all(m["category"] == "security" for m in result["modules"])
        conn.close()


# ---------------------------------------------------------------------------
# Tests — Training Assignments
# ---------------------------------------------------------------------------


class TestAddTrainingAssignment:
    """V2-T2.5: Assignment creation."""

    def test_add_training_assignment(self, v2_db):
        """V2-T2.5: Basic assignment with module-id, assignee, due-date."""
        conn = get_v2_connection(v2_db)

        # Create a module first
        mod = _add_module(conn, title="Security Basics", category="security")
        module_id = mod["id"]

        due = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        result = _add_assignment(
            conn,
            module_id=module_id,
            assignee="alice@example.com",
            due_date=due,
        )

        assert result["status"] == "created"
        assert result["id"] > 0
        assert result["module_id"] == module_id
        assert result["assignee"] == "alice@example.com"

        row = conn.execute(
            "SELECT * FROM training_assignments WHERE id = ?", (result["id"],)
        ).fetchone()
        assert row["status"] == "pending"
        assert row["due_date"] == due
        conn.close()


class TestListTrainingAssignments:
    """V2-T2.6 – V2-T2.8: Assignment listing."""

    def _seed_assignments(self, conn):
        """Create modules and assignments for listing tests."""
        mod1 = _add_module(conn, title="Module A", category="security")
        mod2 = _add_module(conn, title="Module B", category="compliance")

        past = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        _add_assignment(conn, module_id=mod1["id"], assignee="alice@example.com", due_date=past)
        _add_assignment(conn, module_id=mod1["id"], assignee="bob@example.com", due_date=future)
        _add_assignment(conn, module_id=mod2["id"], assignee="alice@example.com", due_date=future)

        return mod1["id"], mod2["id"]

    def test_list_training_assignments(self, v2_db):
        """V2-T2.6: List returns all assignments."""
        conn = get_v2_connection(v2_db)
        self._seed_assignments(conn)

        result = _list_assignments(conn)
        assert result["status"] == "ok"
        assert result["count"] == 3
        assert len(result["assignments"]) == 3
        conn.close()

    def test_list_training_assignments_overdue(self, v2_db):
        """V2-T2.7: --overdue flag filters to past due dates with non-completed status."""
        conn = get_v2_connection(v2_db)
        self._seed_assignments(conn)

        result = _list_assignments(conn, overdue=True)
        assert result["status"] == "ok"
        assert result["count"] >= 1

        now_iso = datetime.now().isoformat()
        for a in result["assignments"]:
            assert a["due_date"] < now_iso
            assert a["status"] != "completed"
        conn.close()

    def test_list_training_assignments_by_assignee(self, v2_db):
        """V2-T2.8: Filter assignments by --assignee."""
        conn = get_v2_connection(v2_db)
        self._seed_assignments(conn)

        result = _list_assignments(conn, assignee="alice@example.com")
        assert result["status"] == "ok"
        assert result["count"] == 2
        assert all(
            a["assignee"] == "alice@example.com" for a in result["assignments"]
        )
        conn.close()


class TestUpdateTrainingAssignment:
    """V2-T2.9 – V2-T2.10: Assignment updates."""

    def test_update_training_assignment_complete(self, v2_db):
        """V2-T2.9: Setting status=completed auto-sets completed_at and stores score."""
        conn = get_v2_connection(v2_db)
        mod = _add_module(conn, title="Quiz Module", category="security")
        assign = _add_assignment(
            conn, module_id=mod["id"], assignee="alice@example.com"
        )

        result = _update_assignment(
            conn, id=assign["id"], status="completed", score=92.5
        )
        assert result["status"] == "updated"

        row = conn.execute(
            "SELECT * FROM training_assignments WHERE id = ?", (assign["id"],)
        ).fetchone()
        assert row["status"] == "completed"
        assert row["completed_at"] is not None
        assert float(row["score"]) == 92.5
        conn.close()

    def test_update_training_assignment_no_auto_complete(self, v2_db):
        """V2-T2.10: Setting status=in_progress does NOT set completed_at."""
        conn = get_v2_connection(v2_db)
        mod = _add_module(conn, title="Ongoing Module", category="security")
        assign = _add_assignment(
            conn, module_id=mod["id"], assignee="bob@example.com"
        )

        result = _update_assignment(conn, id=assign["id"], status="in_progress")
        assert result["status"] == "updated"

        row = conn.execute(
            "SELECT * FROM training_assignments WHERE id = ?", (assign["id"],)
        ).fetchone()
        assert row["status"] == "in_progress"
        assert row["completed_at"] is None
        conn.close()
