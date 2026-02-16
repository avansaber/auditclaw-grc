"""Tests for V5 Phase 5: Integration Setup UX actions.

Tests: setup-guide, show-policy, test-connection (20 tests)
"""

import json
import os
import sqlite3
import sys

import pytest

# Use conftest helpers
from conftest import run_script, make_args, parse_result

SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
)
sys.path.insert(0, SCRIPTS_DIR)


# ===========================================================================
# setup-guide tests
# ===========================================================================

class TestSetupGuide:
    """Tests for the setup-guide action."""

    def test_missing_provider(self, temp_db):
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "setup-guide"],
            db_path=temp_db,
        )
        parsed = parse_result(result, stderr)
        assert parsed is not None
        assert parsed["status"] == "error"
        assert "--provider" in parsed["message"]

    def test_unknown_provider(self, temp_db):
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "setup-guide", "--provider", "digitalocean"],
            db_path=temp_db,
        )
        parsed = parse_result(result, stderr)
        assert parsed is not None
        assert parsed["status"] == "error"
        assert "Unknown provider" in parsed["message"]

    def test_aws_guide(self, temp_db):
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "setup-guide", "--provider", "aws"],
            db_path=temp_db,
        )
        assert code == 0
        assert result["status"] == "ok"
        assert result["provider"] == "aws"
        assert len(result["steps"]) >= 3
        assert "estimated_time" in result
        assert "permissions_summary" in result
        assert "policy_command" in result
        assert "current_evidence_count" in result
        assert "IAM" in result["steps"][0]["title"]

    def test_github_guide(self, temp_db):
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "setup-guide", "--provider", "github"],
            db_path=temp_db,
        )
        assert code == 0
        assert result["status"] == "ok"
        assert result["provider"] == "github"
        assert len(result["steps"]) >= 3
        assert "GitHub App" in result["steps"][0]["title"]

    def test_azure_guide(self, temp_db):
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "setup-guide", "--provider", "azure"],
            db_path=temp_db,
        )
        assert code == 0
        assert result["status"] == "ok"
        assert result["provider"] == "azure"
        assert len(result["steps"]) >= 3

    def test_gcp_guide(self, temp_db):
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "setup-guide", "--provider", "gcp"],
            db_path=temp_db,
        )
        assert code == 0
        assert result["status"] == "ok"
        assert result["provider"] == "gcp"
        assert len(result["steps"]) >= 3

    def test_idp_guide(self, temp_db):
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "setup-guide", "--provider", "idp"],
            db_path=temp_db,
        )
        assert code == 0
        assert result["status"] == "ok"
        assert result["provider"] == "idp"
        assert len(result["steps"]) >= 3

    def test_all_five_providers_have_guides(self, temp_db):
        for provider in ("aws", "github", "azure", "gcp", "idp"):
            result, stderr, code = run_script(
                "db_query.py",
                ["--action", "setup-guide", "--provider", provider],
                db_path=temp_db,
            )
            assert result["status"] == "ok", f"Failed for {provider}: {result}"
            assert "steps" in result
            assert "checks_unlocked" in result

    def test_evidence_count_zero(self, temp_db):
        result, _, _ = run_script(
            "db_query.py",
            ["--action", "setup-guide", "--provider", "aws"],
            db_path=temp_db,
        )
        assert result["current_evidence_count"] == 0

    def test_evidence_count_after_insert(self, temp_db):
        conn = sqlite3.connect(temp_db)
        conn.execute(
            "INSERT INTO evidence (title, type, description, source, uploaded_at) VALUES (?, ?, ?, ?, datetime('now'))",
            ("AWS IAM check", "automated", "test evidence", "aws"),
        )
        conn.commit()
        conn.close()

        result, _, _ = run_script(
            "db_query.py",
            ["--action", "setup-guide", "--provider", "aws"],
            db_path=temp_db,
        )
        assert result["current_evidence_count"] == 1

    def test_companion_installed_field(self, temp_db):
        result, _, _ = run_script(
            "db_query.py",
            ["--action", "setup-guide", "--provider", "aws"],
            db_path=temp_db,
        )
        assert "companion_installed" in result
        assert isinstance(result["companion_installed"], bool)

    def test_guide_steps_have_required_fields(self, temp_db):
        result, _, _ = run_script(
            "db_query.py",
            ["--action", "setup-guide", "--provider", "aws"],
            db_path=temp_db,
        )
        for step in result["steps"]:
            assert "step" in step
            assert "title" in step
            assert "instructions" in step


# ===========================================================================
# show-policy tests
# ===========================================================================

class TestShowPolicy:
    """Tests for the show-policy action."""

    def test_missing_provider(self, temp_db):
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "show-policy"],
            db_path=temp_db,
        )
        parsed = parse_result(result, stderr)
        assert parsed is not None
        assert parsed["status"] == "error"
        assert "--provider" in parsed["message"]

    def test_show_policy_returns_status(self, temp_db):
        """show-policy returns ok (if companion installed) or error (if not)."""
        for provider in ("aws", "github", "azure", "gcp", "idp"):
            result, stderr, code = run_script(
                "db_query.py",
                ["--action", "show-policy", "--provider", provider],
                db_path=temp_db,
            )
            parsed = parse_result(result, stderr)
            assert parsed is not None, f"No output for {provider}"
            assert parsed["status"] in ("ok", "error"), f"Bad status for {provider}: {parsed}"

    def test_show_policy_ok_has_fields(self, temp_db):
        """If show-policy succeeds, verify it has expected fields."""
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "show-policy", "--provider", "aws"],
            db_path=temp_db,
        )
        parsed = parse_result(result, stderr)
        if parsed and parsed["status"] == "ok":
            assert parsed["provider"] == "aws"
            assert "policy" in parsed
            assert "format" in parsed
            assert parsed["format"] in ("json", "text")
            assert "instructions" in parsed


# ===========================================================================
# test-connection tests
# ===========================================================================

class TestTestConnection:
    """Tests for the test-connection action."""

    def test_missing_provider(self, temp_db):
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "test-connection"],
            db_path=temp_db,
        )
        parsed = parse_result(result, stderr)
        assert parsed is not None
        assert parsed["status"] == "error"
        assert "--provider" in parsed["message"]

    def test_connection_returns_status(self, temp_db):
        """test-connection returns ok or error for all providers."""
        for provider in ("aws", "github", "azure", "gcp", "idp"):
            result, stderr, code = run_script(
                "db_query.py",
                ["--action", "test-connection", "--provider", provider],
                db_path=temp_db,
            )
            parsed = parse_result(result, stderr)
            assert parsed is not None, f"No output for {provider}"
            assert parsed["status"] in ("ok", "error"), f"Bad status for {provider}: {parsed}"

    def test_error_has_message(self, temp_db):
        """When test-connection fails, it should include a message."""
        result, stderr, code = run_script(
            "db_query.py",
            ["--action", "test-connection", "--provider", "aws"],
            db_path=temp_db,
        )
        parsed = parse_result(result, stderr)
        assert parsed is not None
        if parsed["status"] == "error":
            assert "message" in parsed


# ===========================================================================
# ACTIONS dict tests
# ===========================================================================

class TestActionsDictV5:
    """Verify all V5 Phase 5 actions are registered."""

    def test_actions_registered(self):
        from db_query import ACTIONS
        for action_name in ("setup-guide", "show-policy", "test-connection"):
            assert action_name in ACTIONS, f"'{action_name}' missing from ACTIONS"
            assert callable(ACTIONS[action_name])
