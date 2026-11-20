import pytest
from fastapi.testclient import TestClient

from quiet_camps.api.app import create_app
from quiet_camps.api.settings import Settings

ENDPOINTS = [
    "/experiment/blocking-sleep",
    "/experiment/thread-sleep",
    "/experiment/async-sleep",
]


def test_experiments_are_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EXPERIMENTS", raising=False)

    assert Settings().experiments is False


@pytest.mark.parametrize("path", ENDPOINTS)
def test_each_endpoint_sleeps_and_answers(path: str) -> None:
    with TestClient(create_app(Settings(experiments=True))) as client:
        response = client.get(path)

    assert response.status_code == 200
    assert response.json() == {"slept": 0.1}


@pytest.mark.parametrize("path", ENDPOINTS)
def test_endpoints_dont_exist_unless_experiments_are_on(path: str) -> None:
    with TestClient(create_app(Settings(experiments=False))) as client:
        response = client.get(path)

    assert response.status_code == 404
