from fastapi.testclient import TestClient
import pytest

from mdm.api import create_app
from mdm.config import Actor
from mdm.synthetic import demo_records

TOKEN = "unit-test-only-token-0000000000"


def test_console_and_authentication_boundary_without_a_database():
    client = TestClient(create_app(actor_map={TOKEN: Actor("reader", "reader")}))
    page = client.get("/")
    assert page.status_code == 200
    assert "Reconciliation" in page.text
    assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
    assert client.get("/api/overview").status_code == 401
    assert client.get("/api/me", headers={"Authorization": "Bearer invalid"}).status_code == 401
    assert client.get("/api/me", headers={"Authorization": f"Bearer {TOKEN}"}).json()["role"] == "reader"
    assert client.post("/api/reconcile", headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 403


def test_streaming_request_body_is_bounded_without_content_length():
    client = TestClient(create_app(actor_map={TOKEN: Actor("reader", "reader")}, body_limit=128))
    response = client.post("/api/ingest", content=iter([b"a"*80,b"b"*80]),
                           headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    assert response.status_code == 413


@pytest.mark.integration
def test_real_api_does_not_accept_actor_impersonation(service):
    client = TestClient(create_app(service, {TOKEN: Actor("reader", "reader")}))
    headers = {"Authorization": f"Bearer {TOKEN}"}
    service.ingest(demo_records())
    assert client.get("/api/overview", headers=headers).json()["quality"]["crosswalk_coverage"] == 1
    assert client.get("/healthz").status_code == 200
    assert "mdm_sources 34" in client.get("/metrics", headers=headers).text
    response = client.post("/api/decisions/merge", headers=headers, json={
        "group_ids": ["bad", "bad2"], "expected_versions": {}, "reason": "arbitrary", "idempotency_key": "x",
        "actor": {"name": "executor", "role": "executor"}})
    assert response.status_code == 422


@pytest.mark.integration
def test_health_requires_the_migration_record(service):
    client = TestClient(create_app(service, {TOKEN: Actor("reader", "reader")}))
    with service.db.connect(write=True) as conn:
        conn.execute("DELETE FROM schema_migrations")
    assert client.get("/healthz").status_code == 503
