from fastapi.testclient import TestClient

from apps.athlete_api.main import app

client = TestClient(app)


def test_liveness() -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
    assert response.headers["x-correlation-id"]


def test_readiness() -> None:
    response = client.get("/health/ready", headers={"x-correlation-id": "test-correlation"})
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    assert response.headers["x-correlation-id"] == "test-correlation"
