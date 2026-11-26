"""Running behind CloudFront on Lambda: only CloudFront may call the API, /ask counts each
viewer by the address CloudFront saw, and a pooled connection that died while the function
was frozen is replaced, not handed to a request."""

from collections.abc import Iterator

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from starlette.requests import Request

from quiet_camps.api.app import create_app
from quiet_camps.api.origin import ORIGIN_HEADER, client_ip
from quiet_camps.api.settings import Settings
from quiet_camps.db.config import psycopg_conninfo

SECRET = "only-cloudfront-knows"


@pytest.fixture
def guarded(api_settings: Settings, alembic_cfg: Config) -> Iterator[TestClient]:
    command.upgrade(alembic_cfg, "head")
    app = create_app(api_settings.model_copy(update={"origin_secret": SECRET}))
    with TestClient(app) as client:
        yield client


def test_without_the_secret_header_is_403(guarded: TestClient) -> None:
    response = guarded.get("/health")

    assert response.status_code == 403
    assert response.headers["content-type"] == "application/problem+json"


def test_a_wrong_secret_is_403(guarded: TestClient) -> None:
    response = guarded.get("/health", headers={ORIGIN_HEADER: "a guess"})

    assert response.status_code == 403


def test_with_the_secret_header_is_answered(guarded: TestClient) -> None:
    response = guarded.get("/health", headers={ORIGIN_HEADER: SECRET})

    assert response.status_code == 200


def test_no_secret_set_means_no_check(client: TestClient) -> None:
    assert client.get("/health").status_code == 200


def request_with(headers: dict[str, str], peer: str = "127.0.0.1") -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "headers": raw, "client": (peer, 5000)})


def test_client_ip_is_the_peer_without_a_header() -> None:
    assert client_ip(request_with({}), None) == "127.0.0.1"


def test_client_ip_reads_ipv4_and_drops_the_port() -> None:
    request = request_with({"CloudFront-Viewer-Address": "203.0.113.9:46532"})

    assert client_ip(request, "cloudfront-viewer-address") == "203.0.113.9"


def test_client_ip_reads_ipv6_and_drops_the_port() -> None:
    request = request_with({"CloudFront-Viewer-Address": "2001:db8::8a2e:370:7334:46532"})

    assert client_ip(request, "cloudfront-viewer-address") == "2001:db8::8a2e:370:7334"


def test_client_ip_falls_back_to_the_peer_when_the_header_is_missing() -> None:
    assert client_ip(request_with({}), "cloudfront-viewer-address") == "127.0.0.1"


def test_a_connection_that_died_in_the_pool_is_replaced(client: TestClient) -> None:
    assert client.get("/health").status_code == 200  # one connection, now back in the pool
    # As when Neon suspends or the frozen function's connection times out: the server ends it.
    with psycopg.connect(psycopg_conninfo(), autocommit=True) as admin:
        admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity"
            " WHERE datname = current_database() AND pid <> pg_backend_pid()"
        )

    assert client.get("/health").status_code == 200
