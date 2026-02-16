"""Tests for V2 Questionnaire actions (templates, responses, answers).

Test IDs: V2-T5.1 through V2-T5.10
"""

import json
import sqlite3
import sys
import os

# Ensure the V2 directory is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conftest import get_v2_connection, make_args
from actions_batch2 import (
    action_add_questionnaire_template,
    action_list_questionnaire_templates,
    action_add_questionnaire_response,
    action_list_questionnaire_responses,
    action_add_questionnaire_answer,
    action_update_questionnaire_response,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_QUESTIONS = json.dumps([
    {"text": "Do you encrypt data at rest?", "type": "yes_no"},
    {"text": "Describe your incident response process.", "type": "free_text"},
    {"text": "How often do you perform penetration tests?", "type": "multiple_choice"},
])


def _create_template(conn, title="Security Review", category="security_review",
                     questions=SAMPLE_QUESTIONS):
    """Shortcut: create a questionnaire template and return the result dict."""
    args = make_args(title=title, category=category, questions=questions)
    result = action_add_questionnaire_template(conn, args)
    assert result["status"] == "created"
    return result


def _create_vendor(conn, name="Test Vendor"):
    """Insert a vendor directly and return its id."""
    cursor = conn.execute(
        "INSERT INTO vendors (name, criticality, status) VALUES (?, 'medium', 'active')",
        (name,),
    )
    conn.commit()
    return cursor.lastrowid


def _create_response(conn, template_id, respondent="vendor@example.com",
                     vendor_id=None):
    """Shortcut: create a questionnaire response and return the result dict."""
    args = make_args(
        template_id=template_id,
        respondent=respondent,
        vendor_id=vendor_id,
    )
    result = action_add_questionnaire_response(conn, args)
    assert result["status"] == "created"
    return result


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestQuestionnaires:
    """V2-T5.x: Questionnaire template, response, and answer operations."""

    def test_add_questionnaire_template(self, v2_db):
        """V2-T5.1: Create template with title, category, questions-json; verify question_count."""
        conn = get_v2_connection(v2_db)
        result = _create_template(conn, title="Vendor Security Assessment")
        conn.close()

        assert result["id"] > 0
        assert result["title"] == "Vendor Security Assessment"
        assert result["question_count"] == 3

    def test_list_questionnaire_templates(self, v2_db):
        """V2-T5.2: Returns all templates."""
        conn = get_v2_connection(v2_db)
        _create_template(conn, title="Template A")
        _create_template(conn, title="Template B")

        result = action_list_questionnaire_templates(conn, make_args())
        conn.close()

        assert result["status"] == "ok"
        assert result["count"] == 2

    def test_list_questionnaire_templates_by_type(self, v2_db):
        """V2-T5.3: --category filter returns matching templates only."""
        conn = get_v2_connection(v2_db)
        _create_template(conn, title="Security Q", category="security_review")
        _create_template(conn, title="Privacy Q", category="privacy_review")

        result = action_list_questionnaire_templates(
            conn, make_args(category="privacy_review")
        )
        conn.close()

        assert result["count"] == 1
        assert result["templates"][0]["title"] == "Privacy Q"

    def test_add_questionnaire_response(self, v2_db):
        """V2-T5.4: Create response for template + vendor."""
        conn = get_v2_connection(v2_db)
        tmpl = _create_template(conn)
        vendor_id = _create_vendor(conn, "Acme Vendor")

        result = _create_response(
            conn, template_id=tmpl["id"], respondent="vendor@company.example",
            vendor_id=vendor_id,
        )
        conn.close()

        assert result["id"] > 0
        assert result["template_id"] == tmpl["id"]
        assert result["respondent"] == "vendor@company.example"
        assert result["total_questions"] == 3

    def test_list_questionnaire_responses(self, v2_db):
        """V2-T5.5: Returns all responses."""
        conn = get_v2_connection(v2_db)
        tmpl = _create_template(conn)
        _create_response(conn, template_id=tmpl["id"], respondent="a@a.com")
        _create_response(conn, template_id=tmpl["id"], respondent="b@b.com")

        result = action_list_questionnaire_responses(conn, make_args())
        conn.close()

        assert result["status"] == "ok"
        assert result["count"] == 2

    def test_list_questionnaire_responses_by_vendor(self, v2_db):
        """V2-T5.6: --vendor-id filter returns responses for that vendor only."""
        conn = get_v2_connection(v2_db)
        tmpl = _create_template(conn)
        v1 = _create_vendor(conn, "Vendor One")
        v2_id = _create_vendor(conn, "Vendor Two")

        _create_response(conn, tmpl["id"], respondent="v1@v.com", vendor_id=v1)
        _create_response(conn, tmpl["id"], respondent="v2@v.com", vendor_id=v2_id)

        result = action_list_questionnaire_responses(
            conn, make_args(vendor_id=v1)
        )
        conn.close()

        assert result["count"] == 1
        assert result["responses"][0]["respondent"] == "v1@v.com"

    def test_add_questionnaire_answer(self, v2_db):
        """V2-T5.7: Answer recorded, answered_questions incremented."""
        conn = get_v2_connection(v2_db)
        tmpl = _create_template(conn)
        resp = _create_response(conn, template_id=tmpl["id"])

        result = action_add_questionnaire_answer(
            conn, make_args(response_id=resp["id"], question_index=0, answer_text="Yes")
        )

        assert result["status"] == "created"
        assert result["response_id"] == resp["id"]
        assert result["question_index"] == 0

        # Verify answered_questions was incremented
        row = conn.execute(
            "SELECT answered_questions FROM questionnaire_responses WHERE id = ?",
            (resp["id"],),
        ).fetchone()
        conn.close()

        assert row["answered_questions"] == 1

    def test_questionnaire_auto_complete(self, v2_db):
        """V2-T5.8: All questions answered triggers auto-complete (status -> completed)."""
        conn = get_v2_connection(v2_db)
        tmpl = _create_template(conn)  # 3 questions
        resp = _create_response(conn, template_id=tmpl["id"])

        # Answer all 3 questions
        for idx in range(3):
            action_add_questionnaire_answer(
                conn,
                make_args(
                    response_id=resp["id"],
                    question_index=idx,
                    answer_text=f"Answer {idx}",
                ),
            )

        row = conn.execute(
            "SELECT status, submitted_at, answered_questions, total_questions "
            "FROM questionnaire_responses WHERE id = ?",
            (resp["id"],),
        ).fetchone()
        conn.close()

        assert row["status"] == "completed"
        assert row["submitted_at"] is not None
        assert row["answered_questions"] == row["total_questions"]

    def test_update_questionnaire_response_score(self, v2_db):
        """V2-T5.9: Updating status to 'reviewed' stores reviewed_at."""
        conn = get_v2_connection(v2_db)
        tmpl = _create_template(conn)
        resp = _create_response(conn, template_id=tmpl["id"])

        result = action_update_questionnaire_response(
            conn, make_args(id=resp["id"], status="reviewed", reviewed_by="auditor@co.com")
        )

        assert result["status"] == "updated"

        row = conn.execute(
            "SELECT status, reviewed_at, reviewed_by FROM questionnaire_responses WHERE id = ?",
            (resp["id"],),
        ).fetchone()
        conn.close()

        assert row["status"] == "reviewed"
        assert row["reviewed_at"] is not None
        assert row["reviewed_by"] == "auditor@co.com"

    def test_update_questionnaire_response_status(self, v2_db):
        """V2-T5.10: Status transitions (draft -> in_progress -> completed) work."""
        conn = get_v2_connection(v2_db)
        tmpl = _create_template(conn)
        resp = _create_response(conn, template_id=tmpl["id"])

        # draft -> in_progress
        action_update_questionnaire_response(
            conn, make_args(id=resp["id"], status="in_progress")
        )
        row = conn.execute(
            "SELECT status FROM questionnaire_responses WHERE id = ?",
            (resp["id"],),
        ).fetchone()
        assert row["status"] == "in_progress"

        # in_progress -> completed
        action_update_questionnaire_response(
            conn, make_args(id=resp["id"], status="completed")
        )
        row = conn.execute(
            "SELECT status FROM questionnaire_responses WHERE id = ?",
            (resp["id"],),
        ).fetchone()
        conn.close()

        assert row["status"] == "completed"
