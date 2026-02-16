"""T5.x — SSL/TLS certificate check tests (mocked sockets).

Tests check_ssl.py using mocked SSL connections to avoid
network dependencies in automated tests.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import pytest

SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts"
)

sys.path.insert(0, SCRIPTS_DIR)


def make_cert(days_from_now=90, cn="example.com", san=None, issuer_org="Let's Encrypt"):
    """Create a mock certificate dict matching ssl.getpeercert() format."""
    now = datetime.now(timezone.utc)
    not_before = now - timedelta(days=30)
    not_after = now + timedelta(days=days_from_now)

    cert = {
        "subject": ((("commonName", cn),),),
        "issuer": ((("organizationName", issuer_org),), (("commonName", f"{issuer_org} Authority"),)),
        "notBefore": not_before.strftime("%b %d %H:%M:%S %Y GMT"),
        "notAfter": not_after.strftime("%b %d %H:%M:%S %Y GMT"),
        "subjectAltName": tuple(("DNS", name) for name in (san or [cn, f"www.{cn}"])),
        "serialNumber": "ABCDEF1234567890",
        "version": 3
    }
    return cert


def mock_ssl_connection(cert, protocol="TLSv1.3", cipher_name="TLS_AES_256_GCM_SHA384"):
    """Create mock SSL socket context manager chain."""
    mock_ssock = MagicMock()
    mock_ssock.getpeercert.return_value = cert
    mock_ssock.cipher.return_value = (cipher_name, protocol, 256)
    mock_ssock.version.return_value = protocol
    mock_ssock.__enter__ = MagicMock(return_value=mock_ssock)
    mock_ssock.__exit__ = MagicMock(return_value=False)

    mock_sock = MagicMock()
    mock_sock.__enter__ = MagicMock(return_value=mock_sock)
    mock_sock.__exit__ = MagicMock(return_value=False)

    return mock_sock, mock_ssock


class TestValidCert:
    """T5.1 — Valid certificate expiring in 90 days."""

    def test_valid_cert(self):
        """T5.1 — Valid cert → grade A, no warnings about expiry."""
        import check_ssl

        cert = make_cert(days_from_now=90)
        mock_sock, mock_ssock = mock_ssl_connection(cert)

        with patch("check_ssl.socket.create_connection", return_value=mock_sock):
            with patch("check_ssl.ssl.create_default_context") as mock_ctx:
                mock_ctx.return_value.wrap_socket.return_value = mock_ssock
                result, error = check_ssl.check_ssl("example.com")

        assert error is None
        assert result["valid"] is True
        assert result["grade"] == "A"
        assert result["days_until_expiry"] >= 89
        assert result["protocol"] == "TLSv1.3"
        # No expiry warnings for 90 days out
        expiry_warnings = [w for w in result["warnings"] if "expires" in w.lower()]
        assert len(expiry_warnings) == 0


class TestExpiringCert:
    """T5.2 — Certificate expiring in 5 days."""

    def test_expiring_cert(self):
        """T5.2 — Expiring cert → warning about expiry."""
        import check_ssl

        cert = make_cert(days_from_now=5)
        mock_sock, mock_ssock = mock_ssl_connection(cert)

        with patch("check_ssl.socket.create_connection", return_value=mock_sock):
            with patch("check_ssl.ssl.create_default_context") as mock_ctx:
                mock_ctx.return_value.wrap_socket.return_value = mock_ssock
                result, error = check_ssl.check_ssl("example.com")

        assert error is None
        assert result["valid"] is True
        assert result["days_until_expiry"] <= 6
        assert any("URGENT" in w or "expires" in w.lower() for w in result["warnings"])


class TestExpiredCert:
    """T5.3 — Expired certificate."""

    def test_expired_cert(self):
        """T5.3 — Expired cert → valid=false, grade F."""
        import check_ssl

        cert = make_cert(days_from_now=-10)
        mock_sock, mock_ssock = mock_ssl_connection(cert)

        with patch("check_ssl.socket.create_connection", return_value=mock_sock):
            with patch("check_ssl.ssl.create_default_context") as mock_ctx:
                mock_ctx.return_value.wrap_socket.return_value = mock_ssock
                result, error = check_ssl.check_ssl("example.com")

        assert error is None
        assert result["valid"] is False
        assert result["grade"] == "F"
        assert any("expired" in w.lower() for w in result["warnings"])


class TestSelfSigned:
    """T5.4 — Self-signed certificate."""

    def test_self_signed(self):
        """T5.4 — Self-signed cert triggers SSLCertVerificationError."""
        import check_ssl
        import ssl

        # First connection attempt raises SSLCertVerificationError
        # Second attempt (no verify) succeeds with basic info
        mock_sock_fail = MagicMock()
        mock_sock_fail.__enter__ = MagicMock(return_value=mock_sock_fail)
        mock_sock_fail.__exit__ = MagicMock(return_value=False)

        mock_ssock_retry = MagicMock()
        mock_ssock_retry.getpeercert.return_value = b"binary-cert-data"
        mock_ssock_retry.cipher.return_value = ("TLS_AES_256_GCM_SHA384", "TLSv1.3", 256)
        mock_ssock_retry.version.return_value = "TLSv1.3"
        mock_ssock_retry.__enter__ = MagicMock(return_value=mock_ssock_retry)
        mock_ssock_retry.__exit__ = MagicMock(return_value=False)

        mock_sock_retry = MagicMock()
        mock_sock_retry.__enter__ = MagicMock(return_value=mock_sock_retry)
        mock_sock_retry.__exit__ = MagicMock(return_value=False)

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_sock_fail
            return mock_sock_retry

        ssl_error = ssl.SSLCertVerificationError("self-signed certificate")

        with patch("check_ssl.socket.create_connection", side_effect=side_effect):
            with patch("check_ssl.ssl.create_default_context") as mock_ctx:
                # First context (verify) raises on wrap_socket
                ctx1 = MagicMock()
                ctx1.wrap_socket.side_effect = ssl_error

                # Second context (no verify) succeeds
                ctx2 = MagicMock()
                ctx2.wrap_socket.return_value = mock_ssock_retry

                mock_ctx.side_effect = [ctx1, ctx2]

                result, error = check_ssl.check_ssl("self-signed.example.com")

        assert error is None
        assert result["valid"] is False
        assert result["chain_valid"] is False
        assert result["grade"] == "F"


class TestConnectionRefused:
    """T5.5 — Connection refused."""

    def test_connection_refused(self):
        """T5.5 — Port closed → error message."""
        import check_ssl

        with patch("check_ssl.socket.create_connection", side_effect=ConnectionRefusedError):
            result, error = check_ssl.check_ssl("closed.example.com")

        assert result is None
        assert "refused" in error.lower()
