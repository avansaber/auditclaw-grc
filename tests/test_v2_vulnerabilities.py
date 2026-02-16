"""Tests for V2 vulnerability operations — add, list, update."""

import sqlite3
from datetime import datetime

import pytest

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from actions_batch1 import (
    action_add_vulnerability,
    action_list_vulnerabilities,
    action_update_vulnerability,
)
from conftest import make_args, get_v2_connection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add_vuln(conn, **kwargs):
    return action_add_vulnerability(conn, make_args(**kwargs))


def _list_vulns(conn, **kwargs):
    return action_list_vulnerabilities(conn, make_args(**kwargs))


def _update_vuln(conn, **kwargs):
    return action_update_vulnerability(conn, make_args(**kwargs))


# ---------------------------------------------------------------------------
# Tests — Add Vulnerability
# ---------------------------------------------------------------------------


class TestAddVulnerability:
    """V2-T3.1 – V2-T3.3: Vulnerability creation."""

    def test_add_vulnerability(self, v2_db):
        """V2-T3.1: Basic vulnerability with title, severity, cvss-score."""
        conn = get_v2_connection(v2_db)
        result = _add_vuln(
            conn,
            title="SQL Injection in Login API",
            severity="critical",
            cvss_score=9.8,
        )

        assert result["status"] == "created"
        assert result["id"] > 0
        assert result["title"] == "SQL Injection in Login API"
        assert result["severity"] == "critical"
        assert result["cvss_score"] == 9.8

        row = conn.execute(
            "SELECT * FROM vulnerabilities WHERE id = ?", (result["id"],)
        ).fetchone()
        assert row["title"] == "SQL Injection in Login API"
        assert row["severity"] == "critical"
        assert float(row["cvss_score"]) == 9.8
        assert row["status"] == "open"
        conn.close()

    def test_add_vulnerability_with_cve(self, v2_db):
        """V2-T3.2: Vulnerability with CVE ID and affected-asset stored."""
        conn = get_v2_connection(v2_db)
        result = _add_vuln(
            conn,
            title="Log4Shell",
            severity="critical",
            cvss_score=10.0,
            cve_id="CVE-2021-44228",
            affected_assets='["app-server-01", "app-server-02"]',
        )

        assert result["status"] == "created"
        row = conn.execute(
            "SELECT * FROM vulnerabilities WHERE id = ?", (result["id"],)
        ).fetchone()
        assert row["cve_id"] == "CVE-2021-44228"
        assert "app-server-01" in row["affected_assets"]
        conn.close()

    def test_add_vulnerability_with_controls(self, v2_db):
        """V2-T3.3: --control-ids creates vulnerability_controls junction entries."""
        conn = get_v2_connection(v2_db)

        # Seed framework + controls
        conn.execute(
            "INSERT INTO frameworks (name, slug, version, status) VALUES ('SOC 2', 'soc2', '1.0', 'active')"
        )
        fw_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        for i in range(1, 4):
            conn.execute(
                "INSERT INTO controls (framework_id, control_id, title) VALUES (?, ?, ?)",
                (fw_id, f"CC{i}", f"Control {i}"),
            )
        conn.commit()

        result = _add_vuln(
            conn,
            title="XSS in Dashboard",
            severity="high",
            cvss_score=7.5,
            control_ids="1,2,3",
        )

        assert result["status"] == "created"
        vuln_id = result["id"]

        rows = conn.execute(
            "SELECT control_id FROM vulnerability_controls WHERE vulnerability_id = ? ORDER BY control_id",
            (vuln_id,),
        ).fetchall()
        assert len(rows) == 3
        assert [r["control_id"] for r in rows] == [1, 2, 3]
        conn.close()


# ---------------------------------------------------------------------------
# Tests — List Vulnerabilities
# ---------------------------------------------------------------------------


class TestListVulnerabilities:
    """V2-T3.4 – V2-T3.7: Vulnerability listing with filters."""

    def _seed_vulns(self, conn):
        """Insert a varied set of vulnerabilities for filtering tests."""
        vulns = [
            ("SQLi Auth Bypass", "critical", 9.8, "open"),
            ("SSRF in API", "high", 8.1, "open"),
            ("XSS Reflected", "medium", 5.3, "mitigated"),
            ("Info Leak Header", "low", 3.1, "resolved"),
            ("RCE via Deserialization", "critical", 9.5, "open"),
        ]
        for title, sev, cvss, status in vulns:
            _add_vuln(conn, title=title, severity=sev, cvss_score=cvss)
            # Manually update status for non-open entries
            if status != "open":
                vid = conn.execute(
                    "SELECT id FROM vulnerabilities WHERE title = ?", (title,)
                ).fetchone()["id"]
                conn.execute(
                    "UPDATE vulnerabilities SET status = ? WHERE id = ?", (status, vid)
                )
                conn.commit()

    def test_list_vulnerabilities(self, v2_db):
        """V2-T3.4: List returns all vulnerabilities."""
        conn = get_v2_connection(v2_db)
        self._seed_vulns(conn)

        result = _list_vulns(conn)
        assert result["status"] == "ok"
        assert result["count"] == 5
        assert len(result["vulnerabilities"]) == 5
        conn.close()

    def test_list_vulnerabilities_by_severity(self, v2_db):
        """V2-T3.5: Filter by --severity critical."""
        conn = get_v2_connection(v2_db)
        self._seed_vulns(conn)

        result = _list_vulns(conn, severity="critical")
        assert result["status"] == "ok"
        assert result["count"] == 2
        assert all(v["severity"] == "critical" for v in result["vulnerabilities"])
        conn.close()

    def test_list_vulnerabilities_by_min_cvss(self, v2_db):
        """V2-T3.6: Filter by --min-cvss 7.0."""
        conn = get_v2_connection(v2_db)
        self._seed_vulns(conn)

        result = _list_vulns(conn, min_cvss=7.0)
        assert result["status"] == "ok"
        assert result["count"] == 3  # 9.8, 8.1, 9.5
        for v in result["vulnerabilities"]:
            assert float(v["cvss_score"]) >= 7.0
        conn.close()

    def test_list_vulnerabilities_by_status(self, v2_db):
        """V2-T3.7: Filter by --status open."""
        conn = get_v2_connection(v2_db)
        self._seed_vulns(conn)

        result = _list_vulns(conn, status="open")
        assert result["status"] == "ok"
        assert result["count"] == 3
        assert all(v["status"] == "open" for v in result["vulnerabilities"])
        conn.close()


# ---------------------------------------------------------------------------
# Tests — Update Vulnerability
# ---------------------------------------------------------------------------


class TestUpdateVulnerability:
    """V2-T3.8 – V2-T3.10: Vulnerability updates."""

    def test_update_vulnerability_resolved(self, v2_db):
        """V2-T3.8: Setting status=resolved auto-sets resolved_at."""
        conn = get_v2_connection(v2_db)
        add_result = _add_vuln(
            conn, title="Patch Pending", severity="high", cvss_score=7.2
        )
        vuln_id = add_result["id"]

        result = _update_vuln(conn, id=vuln_id, status="resolved")
        assert result["status"] == "updated"

        row = conn.execute(
            "SELECT * FROM vulnerabilities WHERE id = ?", (vuln_id,)
        ).fetchone()
        assert row["status"] == "resolved"
        assert row["resolved_at"] is not None
        conn.close()

    def test_update_vulnerability_assigned(self, v2_db):
        """V2-T3.9: Update --assigned-to sets assignee field."""
        conn = get_v2_connection(v2_db)
        add_result = _add_vuln(
            conn, title="Needs Owner", severity="medium", cvss_score=5.0
        )
        vuln_id = add_result["id"]

        result = _update_vuln(conn, id=vuln_id, assignee="security-team@example.com")
        assert result["status"] == "updated"

        row = conn.execute(
            "SELECT assignee FROM vulnerabilities WHERE id = ?", (vuln_id,)
        ).fetchone()
        assert row["assignee"] == "security-team@example.com"
        conn.close()

    def test_update_nonexistent_vulnerability(self, v2_db):
        """V2-T3.10: Updating id 99999 runs but affects no rows."""
        conn = get_v2_connection(v2_db)

        result = _update_vuln(conn, id=99999, status="resolved")
        # The action returns "updated" regardless (no existence check)
        assert result["status"] == "updated"

        # Verify nothing was created
        row = conn.execute(
            "SELECT * FROM vulnerabilities WHERE id = 99999"
        ).fetchone()
        assert row is None
        conn.close()
