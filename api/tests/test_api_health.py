from fastapi.testclient import TestClient

from quiet_camps.api.app import create_app


def test_health_says_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_only_answers_get() -> None:
    client = TestClient(create_app())

    response = client.post("/health")

    assert response.status_code == 405
