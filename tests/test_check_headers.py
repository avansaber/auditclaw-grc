"""T4.x — Security header check tests (mocked HTTP).

Tests check_headers.py using mocked HTTP responses to avoid
network dependencies in automated tests.
"""

import json
import os
import subprocess
import sys
import pytest
from unittest.mock import patch, MagicMock

SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts"
)

# Add scripts dir to path so we can import check_headers
sys.path.insert(0, SCRIPTS_DIR)


def make_mock_response(headers=None, status_code=200, url="https://example.com"):
    """Create a mock requests.Response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.url = url
    mock_resp.headers = headers or {}
    return mock_resp


class TestAllHeadersPresent:
    """T4.1 — All security headers present → Score 100, Grade A."""

    def test_all_headers_present(self):
        """T4.1 — Perfect score when all headers present."""
        import check_headers

        all_headers = {
            "Content-Security-Policy": "default-src 'self'",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=(), microphone=()"
        }

        with patch("check_headers.requests.get", return_value=make_mock_response(all_headers)):
            result, error = check_headers.check_headers("https://example.com")

        assert error is None
        assert result["score"] == 100
        assert result["grade"] == "A"
        assert len(result["recommendations"]) == 0
        for header_info in result["headers"].values():
            assert header_info["present"] is True
            assert header_info["severity"] == "ok"


class TestNoHeaders:
    """T4.2 — No security headers → Score 0, Grade F."""

    def test_no_headers(self):
        """T4.2 — Zero score when no security headers present."""
        import check_headers

        with patch("check_headers.requests.get", return_value=make_mock_response({})):
            result, error = check_headers.check_headers("https://example.com")

        assert error is None
        assert result["score"] == 0
        assert result["grade"] == "F"
        assert len(result["recommendations"]) == 6
        for header_info in result["headers"].values():
            assert header_info["present"] is False


class TestPartialHeaders:
    """T4.3 — Partial headers → score between 0 and 100."""

    def test_partial_headers(self):
        """T4.3 — Partial score with some headers present."""
        import check_headers

        partial_headers = {
            "Strict-Transport-Security": "max-age=31536000",
            "X-Frame-Options": "SAMEORIGIN",
            "X-Content-Type-Options": "nosniff"
        }

        with patch("check_headers.requests.get", return_value=make_mock_response(partial_headers)):
            result, error = check_headers.check_headers("https://example.com")

        assert error is None
        assert 0 < result["score"] < 100
        assert result["headers"]["Strict-Transport-Security"]["present"] is True
        assert result["headers"]["Content-Security-Policy"]["present"] is False
        assert result["headers"]["Content-Security-Policy"]["severity"] == "high"
        assert len(result["recommendations"]) == 3  # CSP, Referrer, Permissions missing


class TestInvalidUrl:
    """T4.4 — Invalid URL handling."""

    def test_invalid_url(self):
        """T4.4 — Invalid URL returns None with error."""
        import check_headers

        result = check_headers.validate_url("")
        assert result is None


class TestJsonOutputSchema:
    """T4.5 — JSON output has expected schema."""

    def test_json_output_schema(self):
        """T4.5 — Output contains all expected fields."""
        import check_headers

        all_headers = {
            "Content-Security-Policy": "default-src 'self'",
            "Strict-Transport-Security": "max-age=31536000",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=()"
        }

        with patch("check_headers.requests.get", return_value=make_mock_response(all_headers)):
            result, error = check_headers.check_headers("https://example.com")

        assert error is None
        # Check required top-level fields
        required_fields = {"status", "url", "score", "grade", "headers",
                           "recommendations", "checked_at"}
        assert required_fields.issubset(set(result.keys()))

        # Check header sub-fields
        for header_name, header_info in result["headers"].items():
            assert "present" in header_info
            assert "severity" in header_info
