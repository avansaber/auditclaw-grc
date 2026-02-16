"""Action functions for Access Reviews and Questionnaires (Batch 2).

These functions follow the same pattern as existing db_query.py actions
and are intended to be integrated into the main action dispatch.
"""

from datetime import datetime
import json


# ---------------------------------------------------------------------------
# ACCESS REVIEW OPERATIONS
# ---------------------------------------------------------------------------

def action_add_access_review(conn, args):
    """Create an access review campaign."""
    title = getattr(args, 'title', None)
    if not title:
        return {"status": "error", "message": "Missing --title argument"}
    description = getattr(args, 'description', None)
    scope_type = getattr(args, 'scope_type', None) or 'all_users'
    scope_config = getattr(args, 'scope_config', None)
    reviewer = getattr(args, 'reviewer', None)
    start_date = getattr(args, 'start_date', None)
    due_date = getattr(args, 'due_date', None)
    now = datetime.utcnow().isoformat()
    cursor = conn.execute(
        """INSERT INTO access_review_campaigns
           (title, description, scope_type, scope_config, reviewer, status,
            start_date, due_date, total_items, reviewed_items, approved_items,
            revoked_items, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, 'draft', ?, ?, 0, 0, 0, 0, ?, ?)""",
        (title, description, scope_type, scope_config, reviewer,
         start_date, due_date, now, now)
    )
    conn.commit()
    return {"status": "created", "id": cursor.lastrowid, "title": title}


def action_list_access_reviews(conn, args):
    """List access review campaigns with optional filters."""
    query = "SELECT * FROM access_review_campaigns WHERE 1=1"
    params = []
    status = getattr(args, 'status', None)
    if status:
        query += " AND status = ?"
        params.append(status)
    reviewer = getattr(args, 'reviewer', None)
    if reviewer:
        query += " AND reviewer = ?"
        params.append(reviewer)
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    campaigns = [dict(r) for r in rows]
    return {"status": "ok", "count": len(campaigns), "campaigns": campaigns}


def action_update_access_review(conn, args):
    """Update an access review campaign."""
    review_id = getattr(args, 'id', None)
    if not review_id:
        return {"status": "error", "message": "Missing --id argument"}
    now = datetime.utcnow().isoformat()
    updates = []
    params = []
    new_status = getattr(args, 'status', None)
    if new_status:
        updates.append("status = ?")
        params.append(new_status)
        if new_status == 'completed':
            updates.append("completed_at = ?")
            params.append(now)
        if new_status == 'active':
            # Auto-set start_date if it is currently null
            row = conn.execute(
                "SELECT start_date FROM access_review_campaigns WHERE id = ?",
                (review_id,)
            ).fetchone()
            if row and not row['start_date']:
                updates.append("start_date = ?")
                params.append(now)
    reviewer = getattr(args, 'reviewer', None)
    if reviewer:
        updates.append("reviewer = ?")
        params.append(reviewer)
    due_date = getattr(args, 'due_date', None)
    if due_date:
        updates.append("due_date = ?")
        params.append(due_date)
    description = getattr(args, 'description', None)
    if description:
        updates.append("description = ?")
        params.append(description)
    if not updates:
        return {"status": "error", "message": "No fields to update"}
    updates.append("updated_at = ?")
    params.append(now)
    params.append(review_id)
    conn.execute(
        f"UPDATE access_review_campaigns SET {', '.join(updates)} WHERE id = ?",
        params
    )
    conn.commit()
    return {"status": "updated", "id": int(review_id)}


def action_add_review_item(conn, args):
    """Add an item to an access review campaign."""
    campaign_id = getattr(args, 'campaign_id', None)
    if not campaign_id:
        return {"status": "error", "message": "Missing --campaign-id argument"}
    user_name = getattr(args, 'user_name', None)
    if not user_name:
        return {"status": "error", "message": "Missing --user-name argument"}
    resource = getattr(args, 'resource', None)
    if not resource:
        return {"status": "error", "message": "Missing --resource argument"}
    current_access = getattr(args, 'current_access', None)
    now = datetime.utcnow().isoformat()
    cursor = conn.execute(
        """INSERT INTO access_review_items
           (campaign_id, user_name, resource, current_access, decision, created_at)
           VALUES (?, ?, ?, ?, 'pending', ?)""",
        (campaign_id, user_name, resource, current_access, now)
    )
    conn.execute(
        "UPDATE access_review_campaigns SET total_items = total_items + 1, updated_at = ? WHERE id = ?",
        (now, campaign_id)
    )
    conn.commit()
    return {"status": "created", "id": cursor.lastrowid, "campaign_id": int(campaign_id)}


def action_list_review_items(conn, args):
    """List items in an access review campaign."""
    campaign_id = getattr(args, 'campaign_id', None)
    if not campaign_id:
        return {"status": "error", "message": "Missing --campaign-id argument"}
    query = "SELECT * FROM access_review_items WHERE campaign_id = ?"
    params = [campaign_id]
    decision = getattr(args, 'decision', None)
    if decision:
        query += " AND decision = ?"
        params.append(decision)
    query += " ORDER BY user_name ASC"
    rows = conn.execute(query, params).fetchall()
    items = [dict(r) for r in rows]
    return {"status": "ok", "count": len(items), "items": items}


def action_update_review_item(conn, args):
    """Record a decision on an access review item."""
    item_id = getattr(args, 'id', None)
    if not item_id:
        return {"status": "error", "message": "Missing --id argument"}
    decision = getattr(args, 'decision', None)
    if not decision:
        return {"status": "error", "message": "Missing --decision argument"}
    if decision not in ('approved', 'revoked', 'modified'):
        return {"status": "error", "message": "Decision must be approved, revoked, or modified"}
    reviewer = getattr(args, 'reviewer', None)
    notes = getattr(args, 'notes', None)
    now = datetime.utcnow().isoformat()
    # Fetch the item to get its campaign_id and current decision
    row = conn.execute(
        "SELECT campaign_id, decision AS old_decision FROM access_review_items WHERE id = ?",
        (item_id,)
    ).fetchone()
    if not row:
        return {"status": "error", "message": f"Review item {item_id} not found"}
    campaign_id = row['campaign_id']
    old_decision = row['old_decision']
    # Update the item
    conn.execute(
        """UPDATE access_review_items
           SET decision = ?, reviewer = ?, notes = ?, reviewed_at = ?
           WHERE id = ?""",
        (decision, reviewer, notes, now, item_id)
    )
    # Update campaign counters
    # Increment reviewed_items only if the old decision was 'pending'
    if old_decision == 'pending':
        conn.execute(
            "UPDATE access_review_campaigns SET reviewed_items = reviewed_items + 1, updated_at = ? WHERE id = ?",
            (now, campaign_id)
        )
    # Decrement old counter if it was not pending (i.e. changing a previous decision)
    if old_decision == 'approved':
        conn.execute(
            "UPDATE access_review_campaigns SET approved_items = approved_items - 1 WHERE id = ?",
            (campaign_id,)
        )
    elif old_decision == 'revoked':
        conn.execute(
            "UPDATE access_review_campaigns SET revoked_items = revoked_items - 1 WHERE id = ?",
            (campaign_id,)
        )
    # Increment new counter
    if decision == 'approved':
        conn.execute(
            "UPDATE access_review_campaigns SET approved_items = approved_items + 1, updated_at = ? WHERE id = ?",
            (now, campaign_id)
        )
    elif decision == 'revoked':
        conn.execute(
            "UPDATE access_review_campaigns SET revoked_items = revoked_items + 1, updated_at = ? WHERE id = ?",
            (now, campaign_id)
        )
    conn.commit()
    return {"status": "updated", "id": int(item_id), "decision": decision}


# ---------------------------------------------------------------------------
# QUESTIONNAIRE OPERATIONS
# ---------------------------------------------------------------------------

def action_add_questionnaire_template(conn, args):
    """Create a questionnaire template."""
    title = getattr(args, 'title', None)
    if not title:
        return {"status": "error", "message": "Missing --title argument"}
    description = getattr(args, 'description', None)
    category = getattr(args, 'category', None) or 'security_review'
    questions_json = getattr(args, 'questions', None)
    question_count = 0
    if questions_json:
        try:
            questions_list = json.loads(questions_json)
            question_count = len(questions_list)
        except (json.JSONDecodeError, TypeError):
            return {"status": "error", "message": "Invalid --questions JSON"}
    now = datetime.utcnow().isoformat()
    cursor = conn.execute(
        """INSERT INTO questionnaire_templates
           (title, description, category, questions, total_questions, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, 'active', ?, ?)""",
        (title, description, category, questions_json, question_count, now, now)
    )
    conn.commit()
    return {"status": "created", "id": cursor.lastrowid, "title": title, "question_count": question_count}


def action_list_questionnaire_templates(conn, args):
    """List questionnaire templates with optional filters."""
    query = "SELECT * FROM questionnaire_templates WHERE 1=1"
    params = []
    category = getattr(args, 'category', None)
    if category:
        query += " AND category = ?"
        params.append(category)
    status = getattr(args, 'status', None)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY title ASC"
    rows = conn.execute(query, params).fetchall()
    templates = [dict(r) for r in rows]
    return {"status": "ok", "count": len(templates), "templates": templates}


def action_add_questionnaire_response(conn, args):
    """Create a new questionnaire response for a template."""
    template_id = getattr(args, 'template_id', None)
    if not template_id:
        return {"status": "error", "message": "Missing --template-id argument"}
    respondent = getattr(args, 'respondent', None)
    if not respondent:
        return {"status": "error", "message": "Missing --respondent argument"}
    vendor_id = getattr(args, 'vendor_id', None)
    # Look up the template to get total_questions
    tmpl = conn.execute(
        "SELECT questions, total_questions FROM questionnaire_templates WHERE id = ?",
        (template_id,)
    ).fetchone()
    if not tmpl:
        return {"status": "error", "message": f"Template {template_id} not found"}
    total_questions = tmpl['total_questions'] or 0
    now = datetime.utcnow().isoformat()
    cursor = conn.execute(
        """INSERT INTO questionnaire_responses
           (template_id, respondent, vendor_id, status, total_questions, answered_questions,
            created_at, updated_at)
           VALUES (?, ?, ?, 'draft', ?, 0, ?, ?)""",
        (template_id, respondent, vendor_id, total_questions, now, now)
    )
    conn.commit()
    return {
        "status": "created",
        "id": cursor.lastrowid,
        "template_id": int(template_id),
        "respondent": respondent,
        "total_questions": total_questions,
    }


def action_list_questionnaire_responses(conn, args):
    """List questionnaire responses with optional filters."""
    query = "SELECT * FROM questionnaire_responses WHERE 1=1"
    params = []
    status = getattr(args, 'status', None)
    if status:
        query += " AND status = ?"
        params.append(status)
    template_id = getattr(args, 'template_id', None)
    if template_id:
        query += " AND template_id = ?"
        params.append(template_id)
    vendor_id = getattr(args, 'vendor_id', None)
    if vendor_id:
        query += " AND vendor_id = ?"
        params.append(vendor_id)
    respondent = getattr(args, 'respondent', None)
    if respondent:
        query += " AND respondent = ?"
        params.append(respondent)
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    responses = [dict(r) for r in rows]
    return {"status": "ok", "count": len(responses), "responses": responses}


def action_add_questionnaire_answer(conn, args):
    """Record an answer to a questionnaire question."""
    response_id = getattr(args, 'response_id', None)
    if not response_id:
        return {"status": "error", "message": "Missing --response-id argument"}
    question_index = getattr(args, 'question_index', None)
    if question_index is None:
        return {"status": "error", "message": "Missing --question-index argument"}
    answer_text = getattr(args, 'answer_text', None)
    if not answer_text:
        return {"status": "error", "message": "Missing --answer-text argument"}
    now = datetime.utcnow().isoformat()
    cursor = conn.execute(
        """INSERT INTO questionnaire_answers
           (response_id, question_index, answer_text, created_at)
           VALUES (?, ?, ?, ?)""",
        (response_id, question_index, answer_text, now)
    )
    # Increment answered_questions on the parent response
    conn.execute(
        "UPDATE questionnaire_responses SET answered_questions = answered_questions + 1, updated_at = ? WHERE id = ?",
        (now, response_id)
    )
    # Check if all questions are now answered
    resp = conn.execute(
        "SELECT answered_questions, total_questions FROM questionnaire_responses WHERE id = ?",
        (response_id,)
    ).fetchone()
    if resp and resp['total_questions'] and resp['answered_questions'] >= resp['total_questions']:
        conn.execute(
            "UPDATE questionnaire_responses SET status = 'completed', submitted_at = ?, updated_at = ? WHERE id = ?",
            (now, now, response_id)
        )
    conn.commit()
    return {
        "status": "created",
        "id": cursor.lastrowid,
        "response_id": int(response_id),
        "question_index": int(question_index),
    }


def action_update_questionnaire_response(conn, args):
    """Update a questionnaire response status."""
    response_id = getattr(args, 'id', None)
    if not response_id:
        return {"status": "error", "message": "Missing --id argument"}
    now = datetime.utcnow().isoformat()
    updates = []
    params = []
    new_status = getattr(args, 'status', None)
    if new_status:
        updates.append("status = ?")
        params.append(new_status)
    reviewed_by = getattr(args, 'reviewed_by', None)
    if reviewed_by:
        updates.append("reviewed_by = ?")
        params.append(reviewed_by)
    if new_status == 'reviewed':
        updates.append("reviewed_at = ?")
        params.append(now)
        if reviewed_by:
            # already added above
            pass
    if not updates:
        return {"status": "error", "message": "No fields to update"}
    updates.append("updated_at = ?")
    params.append(now)
    params.append(response_id)
    conn.execute(
        f"UPDATE questionnaire_responses SET {', '.join(updates)} WHERE id = ?",
        params
    )
    conn.commit()
    return {"status": "updated", "id": int(response_id)}


# ---------------------------------------------------------------------------
# NEW PARSER ARGS NEEDED:
# Access Reviews:
# parser.add_argument("--scope-type", dest="scope_type")
# parser.add_argument("--scope-config", dest="scope_config")
# parser.add_argument("--reviewer")
# parser.add_argument("--campaign-id", dest="campaign_id")
# parser.add_argument("--user-name", dest="user_name")
# parser.add_argument("--resource")
# parser.add_argument("--current-access", dest="current_access")
# parser.add_argument("--decision")
#
# Questionnaires:
# parser.add_argument("--template-id", dest="template_id")
# parser.add_argument("--respondent")
# parser.add_argument("--vendor-id", dest="vendor_id")
# parser.add_argument("--questions")
# parser.add_argument("--response-id", dest="response_id")
# parser.add_argument("--question-index", dest="question_index")
# parser.add_argument("--answer-text", dest="answer_text")
# parser.add_argument("--reviewed-by", dest="reviewed_by")
# parser.add_argument("--module-id", dest="module_id")
# ---------------------------------------------------------------------------
