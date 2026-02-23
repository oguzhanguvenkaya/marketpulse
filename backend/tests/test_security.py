"""Security regression tests — verify Faz 1 & 2 fixes remain in place."""
from __future__ import annotations

import pytest


class TestPathTraversal:
    """1.1 — Path traversal must be blocked."""

    def test_path_traversal_etc_passwd(self, client):
        response = client.get("/../../etc/passwd")
        # SPA catch-all may return 200 with index.html; the key security
        # property is that actual /etc/passwd content is never served.
        assert response.status_code != 500
        assert "root:" not in response.text

    def test_path_traversal_encoded(self, client):
        response = client.get("/%2e%2e/%2e%2e/%2e%2e/etc/passwd")
        assert response.status_code != 500
        assert "root:" not in response.text

    def test_path_traversal_double_dot(self, client):
        response = client.get("/../../../etc/shadow")
        assert response.status_code != 500
        assert "root:" not in response.text

    def test_normal_asset_path(self, client):
        """Normal paths should not be blocked."""
        response = client.get("/assets/nonexistent.js")
        assert response.status_code != 500


class TestAuth:
    """1.2 — API key required for mutating endpoints."""

    def test_post_without_api_key_returns_401(self, client):
        response = client.post("/api/search", json={
            "keyword": "test",
            "platform": "hepsiburada"
        })
        assert response.status_code == 401

    def test_post_with_wrong_api_key_returns_403(self, client):
        response = client.post(
            "/api/search",
            json={"keyword": "test", "platform": "hepsiburada"},
            headers={"X-API-Key": "wrong-key-12345"}
        )
        assert response.status_code == 403

    def test_get_without_api_key_allowed(self, client):
        """GET requests should work without API key."""
        response = client.get("/api/products")
        assert response.status_code == 200

    def test_post_with_valid_api_key(self, client, auth_headers):
        """POST with valid key should not return 401/403."""
        if not auth_headers.get("X-API-Key"):
            pytest.skip("INTERNAL_API_KEY not configured")
        response = client.post(
            "/api/search",
            json={"keyword": "test", "platform": "hepsiburada"},
            headers=auth_headers
        )
        assert response.status_code not in (401, 403)


class TestSSRF:
    """2.3 — Private/local IPs must be rejected."""

    def test_ssrf_localhost(self, client, auth_headers):
        if not auth_headers.get("X-API-Key"):
            pytest.skip("INTERNAL_API_KEY not configured")
        response = client.post(
            "/api/url-scraper/scrape",
            json={"url": "http://127.0.0.1:5432/"},
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_ssrf_metadata_endpoint(self, client, auth_headers):
        if not auth_headers.get("X-API-Key"):
            pytest.skip("INTERNAL_API_KEY not configured")
        response = client.post(
            "/api/url-scraper/scrape",
            json={"url": "http://169.254.169.254/latest/meta-data/"},
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_ssrf_private_network(self, client, auth_headers):
        if not auth_headers.get("X-API-Key"):
            pytest.skip("INTERNAL_API_KEY not configured")
        response = client.post(
            "/api/url-scraper/scrape",
            json={"url": "http://10.0.0.1/admin"},
            headers=auth_headers
        )
        assert response.status_code == 400


class TestInputValidation:
    """2.3 — Input fields must be validated."""

    def test_empty_keyword_rejected(self, client, auth_headers):
        if not auth_headers.get("X-API-Key"):
            pytest.skip("INTERNAL_API_KEY not configured")
        response = client.post(
            "/api/search",
            json={"keyword": "", "platform": "hepsiburada"},
            headers=auth_headers
        )
        assert response.status_code == 422

    def test_keyword_too_long(self, client, auth_headers):
        if not auth_headers.get("X-API-Key"):
            pytest.skip("INTERNAL_API_KEY not configured")
        response = client.post(
            "/api/search",
            json={"keyword": "x" * 201, "platform": "hepsiburada"},
            headers=auth_headers
        )
        assert response.status_code == 422

    def test_invalid_platform_rejected(self, client, auth_headers):
        if not auth_headers.get("X-API-Key"):
            pytest.skip("INTERNAL_API_KEY not configured")
        response = client.post(
            "/api/search",
            json={"keyword": "test", "platform": "amazon"},
            headers=auth_headers
        )
        assert response.status_code == 422


class TestErrorLeakage:
    """2.6 — Error responses must not leak internal details."""

    def test_404_no_stack_trace(self, client):
        response = client.get("/api/nonexistent")
        assert "Traceback" not in response.text
        assert "File \"/" not in response.text

    def test_error_no_internal_path(self, client):
        """Force an error and verify no internal paths in response."""
        response = client.get("/api/products/00000000-0000-0000-0000-000000000000")
        assert "/Users/" not in response.text
        assert "/home/" not in response.text


class TestCORS:
    """2.2 — CORS must not return wildcard unless explicitly configured."""

    def test_cors_with_unknown_origin(self):
        """Request with unknown Origin should not get Access-Control-Allow-Origin: *."""
        from fastapi.testclient import TestClient
        from app.main import app as fastapi_app

        with TestClient(fastapi_app) as tc:
            response = tc.options(
                "/api/products",
                headers={
                    "Origin": "https://evil.example.com",
                    "Access-Control-Request-Method": "GET",
                }
            )
            allow_origin = response.headers.get("access-control-allow-origin", "")
            assert allow_origin != "*"

    def test_cors_preflight_no_crash(self):
        """OPTIONS preflight should not crash."""
        from fastapi.testclient import TestClient
        from app.main import app as fastapi_app

        with TestClient(fastapi_app) as tc:
            response = tc.options(
                "/api/products",
                headers={
                    "Origin": "https://evil.example.com",
                    "Access-Control-Request-Method": "POST",
                }
            )
            assert response.status_code != 500
