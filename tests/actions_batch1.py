"""
Action functions for Assets, Training, and Vulnerabilities.

These functions follow the established db_query.py pattern:
  - Each takes (conn, args) where conn is a sqlite3 connection and args is argparse.Namespace.
  - Required fields are validated upfront; optional fields use getattr(args, 'field', None).
  - Returns a dict with at least a "status" key.
"""

from datetime import datetime


# ---------------------------------------------------------------------------
# ASSET OPERATIONS
# ---------------------------------------------------------------------------

def action_add_asset(conn, args):
    """Register an asset."""
    name = args.name
    if not name:
        return {"status": "error", "message": "Missing --name argument"}
    criticality = getattr(args, 'criticality', None) or "medium"
    status = getattr(args, 'status', None) or "active"
    lifecycle_stage = getattr(args, 'lifecycle_stage', None) or "in_use"
    data_classification = getattr(args, 'data_classification', None) or "internal"
    discovery_source = getattr(args, 'discovery_source', None) or "manual"
    cursor = conn.execute(
        """INSERT INTO assets (name, type, criticality, owner, description, status,
                               ip_address, hostname, os_type, software_version,
                               lifecycle_stage, data_classification, discovery_source,
                               encryption_status, backup_status, patch_status,
                               created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            name,
            getattr(args, 'type', None),
            criticality,
            getattr(args, 'owner', None),
            getattr(args, 'description', None),
            status,
            getattr(args, 'ip_address', None),
            getattr(args, 'hostname', None),
            getattr(args, 'os_type', None),
            getattr(args, 'software_version', None),
            lifecycle_stage,
            data_classification,
            discovery_source,
            getattr(args, 'encryption_status', None),
            getattr(args, 'backup_status', None),
            getattr(args, 'patch_status', None),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    return {
        "status": "created",
        "id": cursor.lastrowid,
        "name": name,
        "criticality": criticality,
    }


def action_list_assets(conn, args):
    """List assets with optional filters."""
    query = "SELECT * FROM assets WHERE 1=1"
    params = []
    if getattr(args, 'type', None):
        query += " AND type = ?"
        params.append(args.type)
    if getattr(args, 'criticality', None):
        query += " AND criticality = ?"
        params.append(args.criticality)
    if getattr(args, 'status', None):
        query += " AND status = ?"
        params.append(args.status)
    if getattr(args, 'lifecycle_stage', None):
        query += " AND lifecycle_stage = ?"
        params.append(args.lifecycle_stage)
    if getattr(args, 'data_classification', None):
        query += " AND data_classification = ?"
        params.append(args.data_classification)
    if getattr(args, 'discovery_source', None):
        query += " AND discovery_source = ?"
        params.append(args.discovery_source)
    query += " ORDER BY criticality DESC, name ASC"
    rows = conn.execute(query, params).fetchall()
    return {"status": "ok", "count": len(rows), "assets": [dict(r) for r in rows]}


def action_update_asset(conn, args):
    """Update an existing asset."""
    asset_id = getattr(args, 'id', None)
    if not asset_id:
        return {"status": "error", "message": "Missing --id argument"}

    updatable_fields = {
        "name": getattr(args, 'name', None),
        "type": getattr(args, 'type', None),
        "criticality": getattr(args, 'criticality', None),
        "owner": getattr(args, 'owner', None),
        "description": getattr(args, 'description', None),
        "status": getattr(args, 'status', None),
        "ip_address": getattr(args, 'ip_address', None),
        "hostname": getattr(args, 'hostname', None),
        "os_type": getattr(args, 'os_type', None),
        "software_version": getattr(args, 'software_version', None),
        "lifecycle_stage": getattr(args, 'lifecycle_stage', None),
        "data_classification": getattr(args, 'data_classification', None),
        "discovery_source": getattr(args, 'discovery_source', None),
        "encryption_status": getattr(args, 'encryption_status', None),
        "backup_status": getattr(args, 'backup_status', None),
        "patch_status": getattr(args, 'patch_status', None),
    }

    # Build dynamic SET clause for provided fields only
    set_clauses = []
    params = []
    for col, val in updatable_fields.items():
        if val is not None:
            set_clauses.append(f"{col} = ?")
            params.append(val)

    if not set_clauses:
        return {"status": "error", "message": "No fields to update"}

    set_clauses.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(asset_id)

    conn.execute(
        f"UPDATE assets SET {', '.join(set_clauses)} WHERE id = ?",
        params,
    )
    conn.commit()
    return {"status": "updated", "id": asset_id}


# ---------------------------------------------------------------------------
# TRAINING OPERATIONS
# ---------------------------------------------------------------------------

def action_add_training_module(conn, args):
    """Create a training module."""
    title = getattr(args, 'title', None)
    if not title:
        return {"status": "error", "message": "Missing --title argument"}
    difficulty_level = getattr(args, 'difficulty_level', None) or "beginner"
    cursor = conn.execute(
        """INSERT INTO training_modules (title, category, description, duration,
                                          content_type, content_url, difficulty_level,
                                          requires_recertification, recertification_days,
                                          status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
        (
            title,
            getattr(args, 'category', None),
            getattr(args, 'description', None),
            getattr(args, 'duration', None),
            getattr(args, 'content_type', None),
            getattr(args, 'content_url', None),
            difficulty_level,
            getattr(args, 'requires_recertification', None) or 0,
            getattr(args, 'recertification_days', None),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    return {"status": "created", "id": cursor.lastrowid, "title": title}


def action_list_training_modules(conn, args):
    """List training modules with optional filters."""
    query = "SELECT * FROM training_modules WHERE 1=1"
    params = []
    if getattr(args, 'category', None):
        query += " AND category = ?"
        params.append(args.category)
    if getattr(args, 'status', None):
        query += " AND status = ?"
        params.append(args.status)
    if getattr(args, 'difficulty_level', None):
        query += " AND difficulty_level = ?"
        params.append(args.difficulty_level)
    query += " ORDER BY title ASC"
    rows = conn.execute(query, params).fetchall()
    return {"status": "ok", "count": len(rows), "modules": [dict(r) for r in rows]}


def action_add_training_assignment(conn, args):
    """Assign a training module to a user."""
    module_id = getattr(args, 'module_id', None)
    assignee = getattr(args, 'assignee', None)
    if not module_id:
        return {"status": "error", "message": "Missing --module-id argument"}
    if not assignee:
        return {"status": "error", "message": "Missing --assignee argument"}
    status = getattr(args, 'status', None) or "pending"
    cursor = conn.execute(
        """INSERT INTO training_assignments (module_id, assignee, due_date, status,
                                              assigned_at, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            module_id,
            assignee,
            getattr(args, 'due_date', None),
            status,
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    return {
        "status": "created",
        "id": cursor.lastrowid,
        "module_id": module_id,
        "assignee": assignee,
    }


def action_list_training_assignments(conn, args):
    """List training assignments with optional filters."""
    query = "SELECT * FROM training_assignments WHERE 1=1"
    params = []
    if getattr(args, 'assignee', None):
        query += " AND assignee = ?"
        params.append(args.assignee)
    if getattr(args, 'status', None):
        query += " AND status = ?"
        params.append(args.status)
    if getattr(args, 'module_id', None):
        query += " AND module_id = ?"
        params.append(args.module_id)
    if getattr(args, 'overdue', None):
        query += " AND due_date < ? AND status != 'completed'"
        params.append(datetime.now().isoformat())
    query += " ORDER BY due_date ASC"
    rows = conn.execute(query, params).fetchall()
    return {"status": "ok", "count": len(rows), "assignments": [dict(r) for r in rows]}


def action_update_training_assignment(conn, args):
    """Update a training assignment (mark complete, set score, etc.)."""
    assignment_id = getattr(args, 'id', None)
    if not assignment_id:
        return {"status": "error", "message": "Missing --id argument"}

    updatable_fields = {
        "status": getattr(args, 'status', None),
        "score": getattr(args, 'score', None),
        "completed_at": getattr(args, 'completed_at', None),
        "certificate_path": getattr(args, 'certificate_path', None),
    }

    # Auto-set completed_at when status is 'completed' and no explicit value given
    if updatable_fields["status"] == "completed" and not updatable_fields["completed_at"]:
        updatable_fields["completed_at"] = datetime.now().isoformat()

    set_clauses = []
    params = []
    for col, val in updatable_fields.items():
        if val is not None:
            set_clauses.append(f"{col} = ?")
            params.append(val)

    if not set_clauses:
        return {"status": "error", "message": "No fields to update"}

    set_clauses.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(assignment_id)

    conn.execute(
        f"UPDATE training_assignments SET {', '.join(set_clauses)} WHERE id = ?",
        params,
    )
    conn.commit()
    return {"status": "updated", "id": assignment_id}


# ---------------------------------------------------------------------------
# VULNERABILITY OPERATIONS
# ---------------------------------------------------------------------------

def action_add_vulnerability(conn, args):
    """Register a vulnerability finding."""
    title = getattr(args, 'title', None)
    if not title:
        return {"status": "error", "message": "Missing --title argument"}
    severity = getattr(args, 'severity', None) or "medium"
    cvss_score = getattr(args, 'cvss_score', None)
    cursor = conn.execute(
        """INSERT INTO vulnerabilities (title, cve_id, description, source,
                                         cvss_score, cvss_vector, severity,
                                         assignee, affected_assets, affected_packages,
                                         remediation_steps, due_date, status,
                                         created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)""",
        (
            title,
            getattr(args, 'cve_id', None),
            getattr(args, 'description', None),
            getattr(args, 'source', None),
            cvss_score,
            getattr(args, 'cvss_vector', None),
            severity,
            getattr(args, 'assignee', None),
            getattr(args, 'affected_assets', None),
            getattr(args, 'affected_packages', None),
            getattr(args, 'remediation_steps', None),
            getattr(args, 'due_date', None),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
        ),
    )
    vuln_id = cursor.lastrowid

    # Optionally link to controls via vulnerability_controls junction table
    control_ids_raw = getattr(args, 'control_ids', None)
    if control_ids_raw:
        for cid in control_ids_raw.split(","):
            cid = cid.strip()
            if cid:
                conn.execute(
                    """INSERT INTO vulnerability_controls (vulnerability_id, control_id, created_at)
                       VALUES (?, ?, ?)""",
                    (vuln_id, cid, datetime.now().isoformat()),
                )

    conn.commit()
    return {
        "status": "created",
        "id": vuln_id,
        "title": title,
        "severity": severity,
        "cvss_score": cvss_score,
    }


def action_list_vulnerabilities(conn, args):
    """List vulnerabilities with optional filters."""
    query = "SELECT * FROM vulnerabilities WHERE 1=1"
    params = []
    if getattr(args, 'status', None):
        query += " AND status = ?"
        params.append(args.status)
    if getattr(args, 'severity', None):
        query += " AND severity = ?"
        params.append(args.severity)
    if getattr(args, 'source', None):
        query += " AND source = ?"
        params.append(args.source)
    if getattr(args, 'assignee', None):
        query += " AND assignee = ?"
        params.append(args.assignee)
    if getattr(args, 'min_cvss', None) is not None:
        query += " AND cvss_score >= ?"
        params.append(float(args.min_cvss))
    query += " ORDER BY cvss_score DESC NULLS LAST, severity DESC"
    rows = conn.execute(query, params).fetchall()
    return {
        "status": "ok",
        "count": len(rows),
        "vulnerabilities": [dict(r) for r in rows],
    }


def action_update_vulnerability(conn, args):
    """Update a vulnerability record."""
    vuln_id = getattr(args, 'id', None)
    if not vuln_id:
        return {"status": "error", "message": "Missing --id argument"}

    updatable_fields = {
        "status": getattr(args, 'status', None),
        "assignee": getattr(args, 'assignee', None),
        "remediation_steps": getattr(args, 'remediation_steps', None),
        "fix_version": getattr(args, 'fix_version', None),
        "resolved_at": getattr(args, 'resolved_at', None),
        "resolved_by": getattr(args, 'resolved_by', None),
        "risk_accepted": getattr(args, 'risk_accepted', None),
        "risk_acceptance_reason": getattr(args, 'risk_acceptance_reason', None),
    }

    # Auto-set resolved_at when status is 'resolved' and no explicit value given
    if updatable_fields["status"] == "resolved" and not updatable_fields["resolved_at"]:
        updatable_fields["resolved_at"] = datetime.now().isoformat()

    set_clauses = []
    params = []
    for col, val in updatable_fields.items():
        if val is not None:
            set_clauses.append(f"{col} = ?")
            params.append(val)

    if not set_clauses:
        return {"status": "error", "message": "No fields to update"}

    set_clauses.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(vuln_id)

    conn.execute(
        f"UPDATE vulnerabilities SET {', '.join(set_clauses)} WHERE id = ?",
        params,
    )
    conn.commit()
    return {"status": "updated", "id": vuln_id}


# ---------------------------------------------------------------------------
# NEW PARSER ARGS NEEDED (reference for integration into db_query.py)
# ---------------------------------------------------------------------------
#
# Assets:
#   parser.add_argument("--ip-address", dest="ip_address")
#   parser.add_argument("--hostname")
#   parser.add_argument("--os-type", dest="os_type")
#   parser.add_argument("--software-version", dest="software_version")
#   parser.add_argument("--lifecycle-stage", dest="lifecycle_stage")
#   parser.add_argument("--data-classification", dest="data_classification")
#   parser.add_argument("--discovery-source", dest="discovery_source")
#   parser.add_argument("--encryption-status", dest="encryption_status")
#   parser.add_argument("--backup-status", dest="backup_status")
#   parser.add_argument("--patch-status", dest="patch_status")
#
# Training Modules:
#   parser.add_argument("--title")
#   parser.add_argument("--duration", type=int, help="Duration in minutes")
#   parser.add_argument("--content-type", dest="content_type")
#   parser.add_argument("--content-url", dest="content_url")
#   parser.add_argument("--difficulty-level", dest="difficulty_level")
#   parser.add_argument("--requires-recertification", dest="requires_recertification", type=int)
#   parser.add_argument("--recertification-days", dest="recertification_days", type=int)
#
# Training Assignments:
#   parser.add_argument("--module-id", dest="module_id", type=int)
#   parser.add_argument("--assignee")
#   parser.add_argument("--due-date", dest="due_date")
#   parser.add_argument("--score", type=float)
#   parser.add_argument("--completed-at", dest="completed_at")
#   parser.add_argument("--certificate-path", dest="certificate_path")
#   parser.add_argument("--overdue", action="store_true", default=False)
#
# Vulnerabilities:
#   parser.add_argument("--cve-id", dest="cve_id")
#   parser.add_argument("--source", choices=["snyk", "github", "qualys", "dependabot", "manual"])
#   parser.add_argument("--cvss-score", dest="cvss_score", type=float)
#   parser.add_argument("--cvss-vector", dest="cvss_vector")
#   parser.add_argument("--severity", choices=["critical", "high", "medium", "low", "info"])
#   parser.add_argument("--affected-assets", dest="affected_assets", help="JSON string")
#   parser.add_argument("--affected-packages", dest="affected_packages", help="JSON string")
#   parser.add_argument("--remediation-steps", dest="remediation_steps")
#   parser.add_argument("--control-ids", dest="control_ids", help="Comma-separated control IDs")
#   parser.add_argument("--min-cvss", dest="min_cvss", type=float)
#   parser.add_argument("--fix-version", dest="fix_version")
#   parser.add_argument("--resolved-at", dest="resolved_at")
#   parser.add_argument("--resolved-by", dest="resolved_by")
#   parser.add_argument("--risk-accepted", dest="risk_accepted", type=int)
#   parser.add_argument("--risk-acceptance-reason", dest="risk_acceptance_reason")
#
# Action dispatch map additions:
#   "add-asset":                 action_add_asset,
#   "list-assets":               action_list_assets,
#   "update-asset":              action_update_asset,
#   "add-training-module":       action_add_training_module,
#   "list-training-modules":     action_list_training_modules,
#   "add-training-assignment":   action_add_training_assignment,
#   "list-training-assignments": action_list_training_assignments,
#   "update-training-assignment":action_update_training_assignment,
#   "add-vulnerability":         action_add_vulnerability,
#   "list-vulnerabilities":      action_list_vulnerabilities,
#   "update-vulnerability":      action_update_vulnerability,
