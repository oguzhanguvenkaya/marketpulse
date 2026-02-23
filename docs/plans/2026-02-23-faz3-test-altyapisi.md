# Faz 3: Test Altyapisi ve Guvenlik Regression — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** pytest altyapisini kurup guvenlik fix'lerini dogrulayan regression test paketi yazmak.

**Architecture:** Gercek PostgreSQL (Replit DB) ile test. Her test transaction rollback ile izole. CORS testleri httpx ile explicit Origin header gonderilerek yapilir.

**Tech Stack:** pytest, pytest-asyncio, httpx, ruff, Make

---

## Task 1: Test Bagimliliklari ve Pytest Konfigurasyonu

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/pytest.ini`
- Create: `backend/tests/__init__.py`

**Step 1: Add test dependencies to requirements.txt**

```
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
ruff>=0.3.0
```

**Step 2: Create pytest.ini**

Create `backend/pytest.ini`:

```ini
[pytest]
testpaths = tests
asyncio_mode = auto
```

**Step 3: Create tests package**

Create empty `backend/tests/__init__.py`.

---

## Task 2: conftest.py — DB Fixture ve TestClient

**Files:**
- Create: `backend/tests/conftest.py`

**Step 1: Create conftest.py with transaction rollback isolation**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import get_db, Base
from app.core.config import settings


@pytest.fixture(scope="session")
def db_engine():
    """Create engine connected to real PostgreSQL (from DATABASE_URL)."""
    engine = create_engine(settings.DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Each test runs inside a transaction that rolls back after the test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    # Nested transaction support (SAVEPOINT)
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()

    session.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    """TestClient with DB session override for transaction isolation."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass  # session lifecycle managed by db_session fixture

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def api_key():
    """Return the configured API key for auth tests."""
    return (settings.INTERNAL_API_KEY or "").strip()


@pytest.fixture()
def auth_headers(api_key):
    """Headers with valid API key."""
    return {"X-API-Key": api_key}
```

---

## Task 3: Smoke Testleri

**Files:**
- Create: `backend/tests/test_smoke.py`

**Step 1: Write smoke tests**

```python
"""Smoke tests — verify basic endpoints respond correctly."""


def test_health_endpoint(client):
    """GET /health should return 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_products_endpoint(client):
    """GET /api/products should return 200 with a list."""
    response = client.get("/api/products")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, (list, dict))


def test_nonexistent_api_route(client):
    """GET /api/nonexistent should return 404."""
    response = client.get("/api/nonexistent-route-xyz")
    assert response.status_code == 404


def test_spa_fallback(client):
    """GET /some-frontend-route should return index.html or 404 (not 500)."""
    response = client.get("/dashboard")
    assert response.status_code in (200, 404)
```

---

## Task 4: Guvenlik Regression Testleri

**Files:**
- Create: `backend/tests/test_security.py`

**Step 1: Write security regression tests**

```python
"""Security regression tests — verify Faz 1 & 2 fixes remain in place."""
import httpx
import pytest


class TestPathTraversal:
    """1.1 — Path traversal must be blocked."""

    def test_path_traversal_etc_passwd(self, client):
        response = client.get("/../../etc/passwd")
        assert response.status_code in (400, 404)
        assert "root:" not in response.text

    def test_path_traversal_encoded(self, client):
        response = client.get("/%2e%2e/%2e%2e/%2e%2e/etc/passwd")
        assert response.status_code in (400, 404)
        assert "root:" not in response.text

    def test_path_traversal_double_dot(self, client):
        response = client.get("/../../../etc/shadow")
        assert response.status_code in (400, 404)

    def test_normal_asset_path(self, client):
        """Normal paths should not be blocked."""
        response = client.get("/assets/nonexistent.js")
        # 404 is fine — just shouldn't be 500
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
        # Should not be auth error (might be other error, but not 401/403)
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
        assert "Private" in response.text or "private" in response.text or "local" in response.text

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
        # Whether 404 or 500, should not leak paths
        assert "/Users/" not in response.text
        assert "/home/" not in response.text
        assert "/app/" not in response.text


class TestCORS:
    """2.2 — CORS must not return wildcard unless explicitly configured."""

    def test_cors_with_unknown_origin(self):
        """Request with unknown Origin should not get Access-Control-Allow-Origin: *."""
        with httpx.Client(base_url="http://testserver") as c:
            # Use transport from TestClient for in-process testing
            from app.main import app as fastapi_app
            transport = httpx.ASGITransport(app=fastapi_app)
            with httpx.Client(transport=transport, base_url="http://testserver") as client:
                response = client.options(
                    "/api/products",
                    headers={
                        "Origin": "https://evil.example.com",
                        "Access-Control-Request-Method": "GET",
                    }
                )
                allow_origin = response.headers.get("access-control-allow-origin", "")
                # Should NOT be * (unless explicitly configured)
                # Should either be empty or echo back a whitelisted origin
                assert allow_origin != "*" or allow_origin == ""

    def test_cors_preflight_method(self):
        """OPTIONS preflight should respond properly."""
        from app.main import app as fastapi_app
        transport = httpx.ASGITransport(app=fastapi_app)
        with httpx.Client(transport=transport, base_url="http://testserver") as client:
            response = client.options(
                "/api/products",
                headers={
                    "Origin": "https://evil.example.com",
                    "Access-Control-Request-Method": "POST",
                }
            )
            # Should not crash (200 or 400, not 500)
            assert response.status_code != 500
```

---

## Task 5: Makefile ve Kalite Kapisi

**Files:**
- Create: `Makefile` (project root)
- Create: `backend/.ruff.toml`

**Step 1: Create ruff config**

Create `backend/.ruff.toml`:

```toml
[lint]
select = ["E", "F", "W"]
ignore = ["E501"]  # line length — codebase has many long lines

[lint.per-file-ignores]
"alembic/*" = ["E", "F", "W"]
```

**Step 2: Create Makefile**

Create `Makefile` at project root:

```makefile
.PHONY: test lint check

test:
	cd backend && python -m pytest tests/ -v

lint:
	cd backend && python -m ruff check .

check: lint test
```

---

## Final Verification

```bash
# 1. Run tests
cd /Users/projectx/Desktop/marketpulse && make test

# 2. Run lint
cd /Users/projectx/Desktop/marketpulse && make lint

# 3. Run full check
cd /Users/projectx/Desktop/marketpulse && make check

# Expected: All tests pass, lint clean (or known warnings only)
```
