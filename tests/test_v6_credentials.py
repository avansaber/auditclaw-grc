"""Tests for V6: Credential Store, Auth Provider, Migration, and db_query actions.

Tests: credential_store CRUD, auth_provider fallbacks, migrate_v6, db_query credential actions (50 tests)
"""

import json
import os
import sqlite3
import stat
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from conftest import run_script, make_args, parse_result

SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
)
sys.path.insert(0, SCRIPTS_DIR)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def v6_db(tmp_path):
    """Create a fresh DB with all tables including integration_credentials."""
    db_path = str(tmp_path / "test_v6.sqlite")
    result, stderr, code = run_script("init_db.py", db_path=db_path)
    assert code == 0
    return db_path


@pytest.fixture
def cred_dir(tmp_path):
    """Create a temp credentials directory."""
    cred_dir = str(tmp_path / "credentials")
    os.makedirs(cred_dir, exist_ok=True)
    return cred_dir


@pytest.fixture
def v6_db_with_cred_dir(v6_db, cred_dir):
    """DB + patched CREDENTIALS_DIR."""
    return v6_db, cred_dir


# ===========================================================================
# credential_store.py tests (10 tests)
# ===========================================================================

class TestCredentialStore:
    """Tests for credential_store.py CRUD operations."""

    def test_save_credential_new(self, v6_db, tmp_path):
        """Save a new credential — creates DB row + secret file."""
        from credential_store import save_credential, CREDENTIALS_DIR
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            result = save_credential(
                v6_db, "aws", "iam_role",
                {"role_arn": "arn:aws:iam::123456:role/TestRole", "external_id": "ext-123"},
                secret_data='{"session": "test"}',
                expires_at="2026-12-31T23:59:59"
            )
        assert result["status"] == "created"
        assert result["provider"] == "aws"
        assert result["auth_method"] == "iam_role"
        assert "id" in result

    def test_save_credential_update_existing(self, v6_db, tmp_path):
        """Save again for same provider → updates instead of creating duplicate."""
        from credential_store import save_credential
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            r1 = save_credential(v6_db, "github", "personal_token", {"scope": "repo"}, secret_data="test-token-old-value")
            assert r1["status"] == "created"

            r2 = save_credential(v6_db, "github", "github_app", {"app_id": "12345"}, secret_data="new-key")
            assert r2["status"] == "updated"
            assert r2["id"] == r1["id"]  # Same row

    def test_get_credential_found(self, v6_db, tmp_path):
        """Get credential returns all fields + reads secret from disk."""
        from credential_store import save_credential, get_credential
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            save_credential(v6_db, "azure", "service_principal", {"tenant_id": "t-123", "client_id": "c-456"}, secret_data="cert-data")
            cred = get_credential(v6_db, "azure")

        assert cred is not None
        assert cred["provider"] == "azure"
        assert cred["auth_method"] == "service_principal"
        assert cred["config"]["tenant_id"] == "t-123"
        assert cred["secret_available"] is True
        assert cred["secret_preview"] is not None
        assert cred["status"] == "active"
        assert cred["last_used"] is not None

    def test_get_credential_not_found(self, v6_db):
        """Get credential for non-existent provider returns None."""
        from credential_store import get_credential
        result = get_credential(v6_db, "nonexistent")
        assert result is None

    def test_delete_credential(self, v6_db, tmp_path):
        """Delete removes DB record + secret file."""
        from credential_store import save_credential, delete_credential, get_credential
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            save_credential(v6_db, "gcp", "service_account", {"project_id": "my-project"}, secret_data='{"type":"service_account"}')
            result = delete_credential(v6_db, "gcp")
            assert result["status"] == "deleted"

            # Verify gone
            assert get_credential(v6_db, "gcp") is None

    def test_delete_credential_not_found(self, v6_db):
        """Delete non-existent credential returns not_found."""
        from credential_store import delete_credential
        result = delete_credential(v6_db, "nonexistent")
        assert result["status"] == "not_found"

    def test_rotate_credential(self, v6_db, tmp_path):
        """Rotate replaces secret data while keeping config."""
        from credential_store import save_credential, rotate_credential, get_credential
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            save_credential(v6_db, "github", "personal_token", {"scope": "repo"}, secret_data="old-token")
            result = rotate_credential(v6_db, "github", "new-token")
            assert result["status"] == "rotated"

            cred = get_credential(v6_db, "github")
            assert cred["secret_available"] is True

    def test_rotate_credential_not_found(self, v6_db):
        """Rotate non-existent credential returns not_found."""
        from credential_store import rotate_credential
        result = rotate_credential(v6_db, "nonexistent", "data")
        assert result["status"] == "not_found"

    def test_list_credentials(self, v6_db, tmp_path):
        """List all credentials (without secrets)."""
        from credential_store import save_credential, list_credentials
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            save_credential(v6_db, "aws", "iam_role", {"role_arn": "arn:..."})
            save_credential(v6_db, "github", "personal_token", {"scope": "repo"}, secret_data="test-token-xxx-value")
            save_credential(v6_db, "azure", "client_secret", {"tenant_id": "t-1"})

        creds = list_credentials(v6_db)
        assert len(creds) == 3
        providers = {c["provider"] for c in creds}
        assert providers == {"aws", "azure", "github"}
        # No secret data in list output
        for c in creds:
            assert "secret" not in c

    def test_secret_file_permissions(self, v6_db, tmp_path):
        """Secret files are written with 0o600 permissions."""
        from credential_store import save_credential, get_credential
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            save_credential(v6_db, "aws", "access_key", {"region": "us-east-1"}, secret_data='{"key":"val"}')
            cred = get_credential(v6_db, "aws")
            path = cred["credential_path"]
            assert os.path.exists(path)
            mode = os.stat(path).st_mode
            assert mode & 0o777 == 0o600


# ===========================================================================
# auth_provider.py tests (15 tests)
# ===========================================================================

class TestAuthProvider:
    """Tests for auth_provider.py — each provider's auth cascade + fallback."""

    def test_get_auth_method_from_store(self, v6_db, tmp_path):
        """get_auth_method returns stored credential info."""
        from credential_store import save_credential
        from auth_provider import get_auth_method
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            save_credential(v6_db, "aws", "iam_role", {"role_arn": "arn:..."})
        result = get_auth_method(v6_db, "aws")
        assert result is not None
        assert result["auth_method"] == "iam_role"
        assert result["status"] == "active"
        assert result["provider"] == "aws"

    def test_get_auth_method_env_var_fallback(self, v6_db):
        """get_auth_method detects env var auth when no stored credential."""
        from auth_provider import get_auth_method
        with patch.dict(os.environ, {"AWS_ACCESS_KEY_ID": "TEST_AWS_KEY_PLACEHOLDER"}):
            result = get_auth_method(v6_db, "aws")
        assert result is not None
        assert result["auth_method"] == "env_vars"
        assert result["status"] == "active"

    def test_get_auth_method_none(self, v6_db):
        """get_auth_method returns None when nothing configured."""
        from auth_provider import get_auth_method
        # Ensure no env vars
        env = {k: v for k, v in os.environ.items()
               if k not in ("AWS_ACCESS_KEY_ID", "GITHUB_TOKEN", "AZURE_SUBSCRIPTION_ID", "GCP_PROJECT_ID")}
        with patch.dict(os.environ, env, clear=True):
            result = get_auth_method(v6_db, "aws")
        assert result is None

    def test_get_auth_method_github_env(self, v6_db):
        """get_auth_method detects GITHUB_TOKEN env var."""
        from auth_provider import get_auth_method
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token-placeholder-123"}):
            result = get_auth_method(v6_db, "github")
        assert result is not None
        assert result["auth_method"] == "env_vars"

    def test_get_auth_method_azure_env(self, v6_db):
        """get_auth_method detects AZURE_SUBSCRIPTION_ID env var."""
        from auth_provider import get_auth_method
        with patch.dict(os.environ, {"AZURE_SUBSCRIPTION_ID": "sub-123"}):
            result = get_auth_method(v6_db, "azure")
        assert result is not None
        assert result["auth_method"] == "env_vars"

    def test_get_auth_method_gcp_env(self, v6_db):
        """get_auth_method detects GCP_PROJECT_ID env var."""
        from auth_provider import get_auth_method
        with patch.dict(os.environ, {"GCP_PROJECT_ID": "my-project"}):
            result = get_auth_method(v6_db, "gcp")
        assert result is not None
        assert result["auth_method"] == "env_vars"

    def test_get_auth_method_idp_google_env(self, v6_db):
        """get_auth_method detects Google Workspace env var."""
        from auth_provider import get_auth_method
        with patch.dict(os.environ, {"GOOGLE_WORKSPACE_SA_KEY": "/path/to/key.json"}):
            result = get_auth_method(v6_db, "idp")
        assert result is not None
        assert result["auth_method"] == "env_vars"

    def test_get_auth_method_idp_okta_env(self, v6_db):
        """get_auth_method detects Okta env var."""
        from auth_provider import get_auth_method
        with patch.dict(os.environ, {"OKTA_ORG_URL": "https://my-org.okta.com"}):
            result = get_auth_method(v6_db, "idp")
        assert result is not None
        assert result["auth_method"] == "env_vars"

    def test_get_auth_method_stored_takes_priority(self, v6_db, tmp_path):
        """Stored credential takes priority over env vars."""
        from credential_store import save_credential
        from auth_provider import get_auth_method
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            save_credential(v6_db, "github", "github_app", {"app_id": "99"})
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token-not-real-env"}):
            result = get_auth_method(v6_db, "github")
        assert result["auth_method"] == "github_app"  # Not env_vars

    def test_get_auth_method_with_timestamps(self, v6_db, tmp_path):
        """Stored credential returns timestamp fields."""
        from credential_store import save_credential
        from auth_provider import get_auth_method
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            save_credential(v6_db, "azure", "service_principal", {"tenant_id": "t"}, expires_at="2026-12-31")
        result = get_auth_method(v6_db, "azure")
        assert result["created_at"] is not None
        assert result["expires_at"] == "2026-12-31"

    def test_get_github_client_returns_none_no_config(self, v6_db):
        """get_github_client returns None when nothing configured."""
        from auth_provider import get_github_client
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            result = get_github_client(v6_db)
        assert result is None

    def test_get_github_client_env_fallback(self, v6_db):
        """get_github_client uses GITHUB_TOKEN env var as fallback."""
        from auth_provider import get_github_client
        mock_github_cls = MagicMock()
        mock_instance = MagicMock()
        mock_github_cls.return_value = mock_instance
        mock_module = MagicMock()
        mock_module.Github = mock_github_cls
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token-for-mock-github"}):
            with patch.dict(sys.modules, {"github": mock_module}):
                # Reimport to pick up mocked module
                import importlib
                import auth_provider as ap
                importlib.reload(ap)
                result = ap.get_github_client(v6_db)
        assert result == mock_instance

    def test_get_azure_credential_none_no_config(self, v6_db):
        """get_azure_credential returns (None, None) when nothing configured."""
        from auth_provider import get_azure_credential
        env = {k: v for k, v in os.environ.items() if k != "AZURE_SUBSCRIPTION_ID"}
        with patch.dict(os.environ, env, clear=True):
            cred, sub = get_azure_credential(v6_db)
        assert cred is None
        assert sub is None

    def test_get_gcp_credentials_none_no_config(self, v6_db):
        """get_gcp_credentials returns (None, None) when nothing configured."""
        from auth_provider import get_gcp_credentials
        env = {k: v for k, v in os.environ.items() if k != "GCP_PROJECT_ID"}
        with patch.dict(os.environ, env, clear=True):
            cred, project = get_gcp_credentials(v6_db)
        assert cred is None
        assert project is None

    def test_get_idp_clients_empty_no_config(self, v6_db):
        """get_idp_clients returns empty dict values when nothing configured."""
        from auth_provider import get_idp_clients
        env = {k: v for k, v in os.environ.items()
               if k not in ("GOOGLE_WORKSPACE_SA_KEY", "GOOGLE_WORKSPACE_ADMIN_EMAIL", "OKTA_ORG_URL", "OKTA_API_TOKEN")}
        with patch.dict(os.environ, env, clear=True):
            result = get_idp_clients(v6_db)
        assert result["google_service"] is None
        assert result["okta_config"] is None


# ===========================================================================
# migrate_v6.py tests (5 tests)
# ===========================================================================

class TestMigrateV6:
    """Tests for migrate_v6.py — table creation, directories, idempotency."""

    def test_migrate_creates_table(self, tmp_path):
        """Migration creates integration_credentials table."""
        db_path = str(tmp_path / "test.sqlite")
        # Create a minimal DB first
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.commit()
        conn.close()

        from migrate_v6 import migrate
        with patch("migrate_v6.CREDENTIALS_DIR", str(tmp_path / "creds")):
            result = migrate(db_path)

        assert result["status"] == "migrated"
        assert result["table_created"] == "integration_credentials"

        # Verify table exists
        conn = sqlite3.connect(db_path)
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        assert "integration_credentials" in tables

    def test_migrate_idempotent(self, tmp_path):
        """Running migration twice returns already_migrated."""
        db_path = str(tmp_path / "test.sqlite")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.commit()
        conn.close()

        from migrate_v6 import migrate
        with patch("migrate_v6.CREDENTIALS_DIR", str(tmp_path / "creds")):
            r1 = migrate(db_path)
            assert r1["status"] == "migrated"

            r2 = migrate(db_path)
            assert r2["status"] == "already_migrated"

    def test_migrate_creates_credential_dirs(self, tmp_path):
        """Migration creates credential directory structure."""
        db_path = str(tmp_path / "test.sqlite")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.commit()
        conn.close()

        cred_dir = str(tmp_path / "creds")
        from migrate_v6 import migrate
        with patch("migrate_v6.CREDENTIALS_DIR", cred_dir):
            migrate(db_path)

        assert os.path.isdir(cred_dir)
        for provider in ["aws", "github", "azure", "gcp", "idp"]:
            assert os.path.isdir(os.path.join(cred_dir, provider))

    def test_migrate_db_not_found(self, tmp_path):
        """Migration with non-existent DB returns error."""
        from migrate_v6 import migrate
        result = migrate(str(tmp_path / "nonexistent.sqlite"))
        assert result["status"] == "error"

    def test_migrate_cli(self, tmp_path):
        """CLI invocation of migrate_v6.py works."""
        db_path = str(tmp_path / "test.sqlite")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.commit()
        conn.close()

        result, stderr, code = run_script("migrate_v6.py", db_path=db_path)
        assert code == 0
        assert result["status"] == "migrated"


# ===========================================================================
# db_query.py credential actions tests (9 tests)
# ===========================================================================

class TestDbQueryCredentialActions:
    """Tests for store-credential, get-credential, delete-credential actions (direct call)."""

    def _call_action(self, action_name, db_path, **kwargs):
        """Call a db_query action directly via function import."""
        import db_query
        conn = sqlite3.connect(db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        args = make_args(db_path=db_path, action=action_name, **kwargs)
        action_fn = db_query.ACTIONS[action_name]
        result = action_fn(conn, args)
        conn.close()
        return result

    def test_store_credential(self, v6_db, tmp_path):
        """store-credential action creates a credential."""
        config = json.dumps({"role_arn": "arn:aws:iam::123:role/Test"})
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            result = self._call_action("store-credential", v6_db,
                                       provider="aws", type="iam_role", config=config)
        assert result["status"] == "created"
        assert result["provider"] == "aws"

    def test_store_credential_missing_provider(self, v6_db):
        """store-credential without provider returns error."""
        result = self._call_action("store-credential", v6_db,
                                   provider=None, type="iam_role", config="{}")
        assert result["status"] == "error"
        assert "provider" in result["message"].lower()

    def test_store_credential_missing_type(self, v6_db):
        """store-credential without type returns error."""
        result = self._call_action("store-credential", v6_db,
                                   provider="aws", type=None, config="{}")
        assert result["status"] == "error"
        assert "type" in result["message"].lower()

    def test_store_credential_missing_config(self, v6_db):
        """store-credential without config returns error."""
        result = self._call_action("store-credential", v6_db,
                                   provider="aws", type="iam_role", config=None)
        assert result["status"] == "error"
        assert "config" in result["message"].lower()

    def test_get_credential(self, v6_db, tmp_path):
        """get-credential returns stored credential with secrets masked."""
        config = json.dumps({"app_id": "12345", "installation_id": "67890"})
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            self._call_action("store-credential", v6_db,
                              provider="github", type="github_app",
                              config=config, description="private-key-data")
            result = self._call_action("get-credential", v6_db, provider="github")
        assert result["status"] == "ok"
        assert result["provider"] == "github"
        assert result["auth_method"] == "github_app"
        assert result["has_secret"] is True
        # Secret is masked — not returned directly
        assert "private-key-data" not in json.dumps(result)

    def test_get_credential_not_found(self, v6_db):
        """get-credential for non-existent provider returns not_found."""
        result = self._call_action("get-credential", v6_db, provider="aws")
        assert result["status"] == "not_found"

    def test_get_credential_missing_provider(self, v6_db):
        """get-credential without provider returns error."""
        result = self._call_action("get-credential", v6_db, provider=None)
        assert result["status"] == "error"

    def test_delete_credential(self, v6_db, tmp_path):
        """delete-credential removes stored credential."""
        config = json.dumps({"tenant_id": "t-123"})
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            self._call_action("store-credential", v6_db,
                              provider="azure", type="client_secret",
                              config=config, description="my-secret")
            result = self._call_action("delete-credential", v6_db, provider="azure")
        assert result["status"] == "deleted"

    def test_delete_credential_not_found(self, v6_db):
        """delete-credential for non-existent provider returns not_found."""
        result = self._call_action("delete-credential", v6_db, provider="gcp")
        assert result["status"] == "not_found"


# ===========================================================================
# Integration / end-to-end tests (11 tests)
# ===========================================================================

class TestCredentialIntegration:
    """End-to-end tests: store → retrieve → use → rotate → delete."""

    def test_full_aws_lifecycle(self, v6_db, tmp_path):
        """AWS: store → get → rotate → delete."""
        from credential_store import save_credential, get_credential, rotate_credential, delete_credential
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            # Store
            r = save_credential(v6_db, "aws", "iam_role",
                               {"role_arn": "arn:aws:iam::123:role/AuditClaw", "external_id": "ext-abc"},
                               secret_data='{"session":"test"}')
            assert r["status"] == "created"

            # Get
            cred = get_credential(v6_db, "aws")
            assert cred["auth_method"] == "iam_role"
            assert cred["config"]["role_arn"] == "arn:aws:iam::123:role/AuditClaw"

            # Rotate
            r = rotate_credential(v6_db, "aws", '{"session":"rotated"}')
            assert r["status"] == "rotated"
            cred = get_credential(v6_db, "aws")
            assert cred["secret_available"] is True

            # Delete
            r = delete_credential(v6_db, "aws")
            assert r["status"] == "deleted"
            assert get_credential(v6_db, "aws") is None

    def test_full_github_lifecycle(self, v6_db, tmp_path):
        """GitHub: store app credential → get → delete."""
        from credential_store import save_credential, get_credential, delete_credential
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            save_credential(v6_db, "github", "github_app",
                           {"app_id": "12345", "installation_id": "67890"},
                           secret_data="TEST-PRIVATE-KEY-PLACEHOLDER-NOT-REAL")
            cred = get_credential(v6_db, "github")
            assert cred["auth_method"] == "github_app"
            assert cred["secret_available"] is True

            delete_credential(v6_db, "github")
            assert get_credential(v6_db, "github") is None

    def test_full_azure_lifecycle(self, v6_db, tmp_path):
        """Azure: store certificate-based SP → get → delete."""
        from credential_store import save_credential, get_credential, delete_credential
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            save_credential(v6_db, "azure", "service_principal",
                           {"tenant_id": "t-abc", "client_id": "c-xyz", "subscription_id": "sub-123"},
                           secret_data="TEST-CERTIFICATE-PLACEHOLDER-NOT-REAL")
            cred = get_credential(v6_db, "azure")
            assert cred["config"]["tenant_id"] == "t-abc"
            assert cred["credential_path"].endswith("certificate.pem")

            delete_credential(v6_db, "azure")
            assert get_credential(v6_db, "azure") is None

    def test_full_gcp_lifecycle(self, v6_db, tmp_path):
        """GCP: store SA impersonation → get → delete."""
        from credential_store import save_credential, get_credential, delete_credential
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            save_credential(v6_db, "gcp", "sa_impersonation",
                           {"project_id": "my-project", "target_service_account": "sa@project.iam.gserviceaccount.com"},
                           secret_data='{"config":"impersonation"}')
            cred = get_credential(v6_db, "gcp")
            assert cred["auth_method"] == "sa_impersonation"
            assert cred["config"]["target_service_account"] == "sa@project.iam.gserviceaccount.com"

            delete_credential(v6_db, "gcp")
            assert get_credential(v6_db, "gcp") is None

    def test_full_idp_lifecycle(self, v6_db, tmp_path):
        """IDP: store → get → delete."""
        from credential_store import save_credential, get_credential, delete_credential
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            save_credential(v6_db, "idp", "domain_delegation",
                           {"google": {"admin_email": "test-admin@company.example"}, "okta": {"org_url": "https://test.okta.com", "token": "test-okta-token-placeholder"}},
                           secret_data='{"sa_key":"test"}')
            cred = get_credential(v6_db, "idp")
            assert cred["auth_method"] == "domain_delegation"
            assert cred["config"]["google"]["admin_email"] == "test-admin@company.example"

            delete_credential(v6_db, "idp")
            assert get_credential(v6_db, "idp") is None

    def test_multiple_providers_isolated(self, v6_db, tmp_path):
        """Multiple providers stored simultaneously don't interfere."""
        from credential_store import save_credential, get_credential, list_credentials
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            save_credential(v6_db, "aws", "iam_role", {"role": "test"})
            save_credential(v6_db, "github", "personal_token", {"scope": "repo"}, secret_data="test-token-not-real-value")
            save_credential(v6_db, "azure", "client_secret", {"tenant": "t"}, secret_data="secret")

        creds = list_credentials(v6_db)
        assert len(creds) == 3
        assert {c["provider"] for c in creds} == {"aws", "azure", "github"}

        # Each provider returns correct data
        aws = get_credential(v6_db, "aws")
        assert aws["auth_method"] == "iam_role"
        gh = get_credential(v6_db, "github")
        assert gh["auth_method"] == "personal_token"

    def test_credential_secret_file_naming(self, v6_db, tmp_path):
        """Different auth methods produce correctly named secret files."""
        from credential_store import save_credential, get_credential
        test_cases = [
            ("aws", "iam_role", "session.json"),
            ("github", "github_app", "private-key.pem"),
            ("azure", "service_principal", "certificate.pem"),
            ("gcp", "service_account", "key.json"),
        ]
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            for provider, auth_method, expected_filename in test_cases:
                save_credential(v6_db, provider, auth_method, {"test": True}, secret_data="data")
                cred = get_credential(v6_db, provider)
                assert cred["credential_path"].endswith(expected_filename), \
                    f"{provider}/{auth_method}: expected {expected_filename}, got {cred['credential_path']}"

    def test_credential_config_json_parsing(self, v6_db, tmp_path):
        """Config is stored as JSON string and parsed back correctly."""
        from credential_store import save_credential, get_credential
        complex_config = {
            "role_arn": "arn:aws:iam::123456789012:role/AuditClawReadOnly",
            "external_id": "ext-abc-123",
            "region": "us-west-2",
            "nested": {"key": "value"},
        }
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            save_credential(v6_db, "aws", "iam_role", complex_config)
        cred = get_credential(v6_db, "aws")
        assert cred["config"] == complex_config
        assert cred["config"]["nested"]["key"] == "value"

    def test_store_credential_without_secret(self, v6_db, tmp_path):
        """Storing credential without secret_data works (no file on disk)."""
        from credential_store import save_credential, get_credential
        with patch("credential_store.CREDENTIALS_DIR", str(tmp_path / "creds")):
            save_credential(v6_db, "aws", "iam_role", {"role_arn": "arn:..."})
        cred = get_credential(v6_db, "aws")
        assert cred is not None
        assert cred["credential_path"] is None
        assert "secret" not in cred

    def test_init_db_includes_integration_credentials(self, tmp_path):
        """Fresh init_db.py creates integration_credentials table."""
        db_path = str(tmp_path / "fresh.sqlite")
        result, stderr, code = run_script("init_db.py", db_path=db_path)
        assert code == 0

        conn = sqlite3.connect(db_path)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()]
        conn.close()
        assert "integration_credentials" in tables

    def test_credential_store_error_handling(self, v6_db):
        """get_credential handles missing integration_credentials table gracefully."""
        # Create a DB without the table
        conn = sqlite3.connect(v6_db)
        conn.execute("DROP TABLE IF EXISTS integration_credentials")
        conn.commit()
        conn.close()

        from credential_store import get_credential
        # Should raise or return error, not crash silently
        with pytest.raises(Exception):
            get_credential(v6_db, "aws")
