from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_health_status() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["data"]["status"] == "healthy"
    assert body["data"]["service"] == "SWETO API"
