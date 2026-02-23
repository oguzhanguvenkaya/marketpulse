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
