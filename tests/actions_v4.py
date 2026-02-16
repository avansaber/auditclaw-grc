"""
V4 Action Functions: Integration CRUD, Alert CRUD, Browser Check CRUD

These functions follow the same pattern as existing db_query.py actions:
  - Take (conn, args) parameters
  - Return a dict with status key
  - Use conn.execute() for SQL, conn.commit() for writes
"""

from datetime import datetime


# ---------------------------------------------------------------------------
# Integration Actions (5)
# ---------------------------------------------------------------------------

def action_add_integration(conn, args):
    """Register a new integration provider."""
    provider = getattr(args, 'provider', None)
    if not provider:
        return {"status": "error", "message": "Missing --provider argument"}
    name = args.name
    if not name:
        return {"status": "error", "message": "Missing --name argument"}

    schedule = getattr(args, 'schedule', None)
    config = getattr(args, 'config', None)

    cursor = conn.execute(
        """INSERT INTO integrations (provider, name, status, schedule, config)
           VALUES (?, ?, 'configured', ?, ?)""",
        (provider, name, schedule, config)
    )
    conn.commit()

    return {
        "status": "created",
        "id": cursor.lastrowid,
        "provider": provider,
        "name": name,
    }


def action_list_integrations(conn, args):
    """List integrations with optional filters."""
    query = "SELECT * FROM integrations WHERE 1=1"
    params = []

    provider = getattr(args, 'provider', None)
    if provider:
        query += " AND provider = ?"
        params.append(provider)
    if args.status:
        query += " AND status = ?"
        params.append(args.status)

    query += " ORDER BY provider, name"
    rows = conn.execute(query, params).fetchall()

    return {"status": "ok", "count": len(rows), "integrations": [dict(r) for r in rows]}


def action_update_integration(conn, args):
    """Update an integration record."""
    if not args.id:
        return {"status": "error", "message": "Missing --id argument"}
    row = conn.execute("SELECT id FROM integrations WHERE id = ?", (int(args.id),)).fetchone()
    if not row:
        return {"status": "error", "message": f"Integration not found with id: {args.id}"}

    updates = []
    params = []
    if args.status:
        updates.append("status = ?")
        params.append(args.status)
    if getattr(args, 'last_sync', None):
        updates.append("last_sync = ?")
        params.append(args.last_sync)
    if getattr(args, 'next_sync', None):
        updates.append("next_sync = ?")
        params.append(args.next_sync)
    if getattr(args, 'error_message', None):
        updates.append("last_error = ?")
        params.append(args.error_message)
        updates.append("error_count = error_count + 1")
    if getattr(args, 'schedule', None):
        updates.append("schedule = ?")
        params.append(args.schedule)
    if args.name:
        updates.append("name = ?")
        params.append(args.name)

    if not updates:
        return {"status": "error", "message": "No fields to update"}

    updates.append("updated_at = datetime('now')")
    set_clause = ", ".join(updates)
    conn.execute(f"UPDATE integrations SET {set_clause} WHERE id = ?", params + [int(args.id)])
    conn.commit()
    return {"status": "updated", "id": int(args.id)}


def action_sync_integration(conn, args):
    """Trigger sync for an integration (marks as syncing, returns provider info)."""
    if not args.id:
        return {"status": "error", "message": "Missing --id argument"}
    row = conn.execute("SELECT id, provider, name, status FROM integrations WHERE id = ?",
                       (int(args.id),)).fetchone()
    if not row:
        return {"status": "error", "message": f"Integration not found with id: {args.id}"}

    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "UPDATE integrations SET status = 'syncing', last_sync = ?, updated_at = ? WHERE id = ?",
        (now, now, int(args.id))
    )
    conn.commit()

    return {
        "status": "syncing",
        "id": dict(row)["id"],
        "provider": dict(row)["provider"],
        "name": dict(row)["name"],
    }


def action_integration_health(conn, args):
    """Show health dashboard for all integrations."""
    rows = conn.execute(
        "SELECT * FROM integrations ORDER BY provider, name"
    ).fetchall()

    integrations = []
    healthy = errored = stale = disabled = 0

    for row in rows:
        r = dict(row)
        # Calculate sync age
        sync_age_hours = None
        is_stale = False
        if r["last_sync"]:
            try:
                last = datetime.fromisoformat(r["last_sync"])
                sync_age_hours = round((datetime.now() - last).total_seconds() / 3600, 1)
                is_stale = sync_age_hours > 48  # stale if >48h since last sync
            except (ValueError, TypeError):
                pass

        # Count evidence from this provider
        evidence_count = conn.execute(
            "SELECT COUNT(*) FROM evidence WHERE source = ?", (r["provider"],)
        ).fetchone()[0]

        last_evidence = conn.execute(
            "SELECT MAX(uploaded_at) FROM evidence WHERE source = ?", (r["provider"],)
        ).fetchone()[0]

        health = "disabled" if r["status"] == "disabled" else \
                 "errored" if r["error_count"] and r["error_count"] > 0 else \
                 "stale" if is_stale else "healthy"

        if health == "healthy":
            healthy += 1
        elif health == "errored":
            errored += 1
        elif health == "stale":
            stale += 1
        else:
            disabled += 1

        integrations.append({
            **r,
            "sync_age_hours": sync_age_hours,
            "is_stale": is_stale,
            "evidence_count": evidence_count,
            "last_evidence_date": last_evidence,
            "health": health,
        })

    return {
        "status": "ok",
        "total": len(integrations),
        "healthy": healthy,
        "errored": errored,
        "stale": stale,
        "disabled": disabled,
        "integrations": integrations,
    }


# ---------------------------------------------------------------------------
# Alert Actions (4)
# ---------------------------------------------------------------------------

def action_add_alert(conn, args):
    """Create a new alert."""
    alert_type = args.type
    if not alert_type:
        return {"status": "error", "message": "Missing --type argument"}
    title = args.title
    if not title:
        return {"status": "error", "message": "Missing --title argument"}

    severity = args.severity or "info"
    description = args.description or None
    resource_type = getattr(args, 'resource_type', None)
    resource_id = getattr(args, 'resource_id', None)
    drift_details = getattr(args, 'drift_details', None)

    cursor = conn.execute(
        """INSERT INTO alerts (type, title, severity, message, resource_type, resource_id, drift_details)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (alert_type, title, severity, description, resource_type, resource_id, drift_details)
    )
    conn.commit()

    return {
        "status": "created",
        "id": cursor.lastrowid,
        "type": alert_type,
        "severity": severity,
        "title": title,
    }


def action_list_alerts(conn, args):
    """List alerts with optional filters."""
    query = "SELECT * FROM alerts WHERE 1=1"
    params = []

    if args.type:
        query += " AND type = ?"
        params.append(args.type)
    if args.severity:
        query += " AND severity = ?"
        params.append(args.severity)
    if args.status:
        query += " AND status = ?"
        params.append(args.status)
    acknowledged = getattr(args, 'acknowledged', None)
    if acknowledged is not None and acknowledged != "":
        if acknowledged in ("0", "false", "no"):
            query += " AND acknowledged_at IS NULL"
        elif acknowledged in ("1", "true", "yes"):
            query += " AND acknowledged_at IS NOT NULL"
    resolved = getattr(args, 'resolved', None)
    if resolved is not None and resolved != "":
        if resolved in ("0", "false", "no"):
            query += " AND resolved_at IS NULL"
        elif resolved in ("1", "true", "yes"):
            query += " AND resolved_at IS NOT NULL"

    query += " ORDER BY triggered_at DESC"
    rows = conn.execute(query, params).fetchall()

    unacknowledged = sum(1 for r in rows if not dict(r).get("acknowledged_at"))
    unresolved = sum(1 for r in rows if not dict(r).get("resolved_at"))

    return {
        "status": "ok",
        "count": len(rows),
        "unacknowledged": unacknowledged,
        "unresolved": unresolved,
        "alerts": [dict(r) for r in rows],
    }


def action_acknowledge_alert(conn, args):
    """Acknowledge an alert."""
    if not args.id:
        return {"status": "error", "message": "Missing --id argument"}
    row = conn.execute("SELECT id, status FROM alerts WHERE id = ?", (int(args.id),)).fetchone()
    if not row:
        return {"status": "error", "message": f"Alert not found with id: {args.id}"}

    now = datetime.now().isoformat(timespec="seconds")
    acknowledged_by = getattr(args, 'acknowledged_by', None) or "user"

    conn.execute(
        "UPDATE alerts SET acknowledged_at = ?, acknowledged_by = ? WHERE id = ?",
        (now, acknowledged_by, int(args.id))
    )
    conn.commit()

    return {"status": "acknowledged", "id": int(args.id)}


def action_resolve_alert(conn, args):
    """Resolve an alert."""
    if not args.id:
        return {"status": "error", "message": "Missing --id argument"}
    row = conn.execute("SELECT id, status FROM alerts WHERE id = ?", (int(args.id),)).fetchone()
    if not row:
        return {"status": "error", "message": f"Alert not found with id: {args.id}"}

    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "UPDATE alerts SET status = 'resolved', resolved_at = ? WHERE id = ?",
        (now, int(args.id))
    )
    conn.commit()

    return {"status": "resolved", "id": int(args.id)}


# ---------------------------------------------------------------------------
# Browser Check Actions (4)
# ---------------------------------------------------------------------------

def action_add_browser_check(conn, args):
    """Register a URL for scheduled scanning."""
    name = args.name
    if not name:
        return {"status": "error", "message": "Missing --name argument"}
    url = getattr(args, 'url', None)
    if not url:
        return {"status": "error", "message": "Missing --url argument"}
    check_type = getattr(args, 'check_type', None)
    if not check_type:
        return {"status": "error", "message": "Missing --check-type argument"}

    schedule = getattr(args, 'schedule', None)

    cursor = conn.execute(
        """INSERT INTO browser_checks (name, url, check_type, schedule)
           VALUES (?, ?, ?, ?)""",
        (name, url, check_type, schedule)
    )
    conn.commit()

    return {
        "status": "created",
        "id": cursor.lastrowid,
        "name": name,
        "url": url,
        "check_type": check_type,
    }


def action_list_browser_checks(conn, args):
    """List browser checks with optional filters."""
    query = "SELECT * FROM browser_checks WHERE 1=1"
    params = []

    check_type = getattr(args, 'check_type', None)
    if check_type:
        query += " AND check_type = ?"
        params.append(check_type)
    if args.status:
        query += " AND status = ?"
        params.append(args.status)

    query += " ORDER BY name"
    rows = conn.execute(query, params).fetchall()

    return {"status": "ok", "count": len(rows), "checks": [dict(r) for r in rows]}


def action_update_browser_check(conn, args):
    """Update a browser check record."""
    if not args.id:
        return {"status": "error", "message": "Missing --id argument"}
    row = conn.execute("SELECT id FROM browser_checks WHERE id = ?", (int(args.id),)).fetchone()
    if not row:
        return {"status": "error", "message": f"Browser check not found with id: {args.id}"}

    updates = []
    params = []
    if args.status:
        updates.append("status = ?")
        params.append(args.status)
    if getattr(args, 'last_run', None):
        updates.append("last_run = ?")
        params.append(args.last_run)
    if getattr(args, 'last_result', None):
        updates.append("last_result = ?")
        params.append(args.last_result)
    if getattr(args, 'last_status', None):
        updates.append("last_status = ?")
        params.append(args.last_status)
    if getattr(args, 'schedule', None):
        updates.append("schedule = ?")
        params.append(args.schedule)
    if args.name:
        updates.append("name = ?")
        params.append(args.name)
    if getattr(args, 'url', None):
        updates.append("url = ?")
        params.append(args.url)

    if not updates:
        return {"status": "error", "message": "No fields to update"}

    updates.append("updated_at = datetime('now')")
    if getattr(args, 'last_run', None):
        updates.append("run_count = run_count + 1")

    set_clause = ", ".join(updates)
    conn.execute(f"UPDATE browser_checks SET {set_clause} WHERE id = ?", params + [int(args.id)])
    conn.commit()
    return {"status": "updated", "id": int(args.id)}


def action_run_browser_check(conn, args):
    """Trigger a browser check run (marks as running, returns check info)."""
    if not args.id:
        return {"status": "error", "message": "Missing --id argument"}
    row = conn.execute(
        "SELECT id, name, url, check_type, status FROM browser_checks WHERE id = ?",
        (int(args.id),)
    ).fetchone()
    if not row:
        return {"status": "error", "message": f"Browser check not found with id: {args.id}"}

    r = dict(row)
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "UPDATE browser_checks SET last_run = ?, run_count = run_count + 1, updated_at = ? WHERE id = ?",
        (now, now, int(args.id))
    )
    conn.commit()

    return {
        "status": "running",
        "id": r["id"],
        "name": r["name"],
        "url": r["url"],
        "check_type": r["check_type"],
    }
