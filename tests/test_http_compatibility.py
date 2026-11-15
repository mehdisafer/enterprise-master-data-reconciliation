"""HTTP contracts that must survive FastAPI/Pydantic dependency updates.

Transport probes below deliberately stop before a database operation. The two
marked lifecycle tests use the real disposable PostgreSQL fixture instead.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from mdm.api import create_app
from mdm.config import Actor
from mdm.demo import SourceUpdate
from mdm.domain import SourceRecord
from mdm.service import Conflict
from mdm.synthetic import demo_records

TOKENS = {role: f"http-compatibility-{role}-token-000000000000" for role in
          ("reader", "requester", "approver", "executor")}
ACTORS = {token: Actor(f"http.{role}", role) for role, token in TOKENS.items()}
ORION_KEYS = {"ERP_ALPHA:organization:ORION-01", "ERP_BETA:organization:ORION-02"}


def headers(role="reader"):
    return {"Authorization": f"Bearer {TOKENS[role]}"}


def assert_response(response, status):
    assert response.status_code == status, response.text
    identifier = response.headers["x-correlation-id"]
    assert str(UUID(identifier)) == identifier
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    return response.json()


class UnreachableService:
    """A rejected HTTP request must never cross the application boundary."""

    def __getattr__(self, name):
        raise AssertionError(f"Unexpected service access: {name}")


@pytest.fixture
def guarded_client():
    with TestClient(create_app(UnreachableService(), ACTORS)) as client:
        yield client


@pytest.mark.parametrize("path", [
    "/api/me", "/api/overview", "/api/openapi.json",
    "/api/golden/00000000-0000-0000-0000-000000000001/history", "/metrics",
])
@pytest.mark.parametrize("authorization", [None, "Basic not-a-bearer-token", "Bearer unknown-token"])
def test_protected_reads_require_configured_bearer_before_service_access(guarded_client, path, authorization):
    response = guarded_client.get(path, headers={"Authorization": authorization} if authorization else {})
    assert_response(response, 401)
    assert response.headers["www-authenticate"] == "Bearer"


def test_identity_is_server_assigned_and_tokens_do_not_enter_openapi(guarded_client):
    for role in TOKENS:
        response = guarded_client.get("/api/me?role=executor", headers=headers(role))
        assert assert_response(response, 200) == {"name": f"http.{role}", "role": role}
    schema = assert_response(guarded_client.get("/api/openapi.json", headers=headers()), 200)
    assert schema["openapi"].startswith("3.1.")
    schemas = schema["components"]["schemas"]
    for model in ("MergeInput", "SplitInput", "UnmergeInput", "VersionInput", "IngestInput", "SourceRecord"):
        assert schemas[model]["additionalProperties"] is False
    assert schemas["SourceRecord"]["properties"]["valid_from"]["format"] == "date-time"
    assert schemas["SourceRecord"]["properties"]["roles"]["uniqueItems"] is True
    for path in ("/api/ingest", "/api/decisions/merge", "/api/decisions/split", "/api/decisions/unmerge"):
        assert schema["paths"][path]["post"]["security"] == [{"HTTPBearer": []}]
    assert not any(token in str(schema) for token in TOKENS.values())


@pytest.mark.parametrize("changes", [
    {"valid_from": "2026-01-01T00:00:00"},
    {"source_updated_at": "2026-01-01T00:00:00"},
    {"roles": ["customer", "customer"]},
    {"roles": ["administrator"]},
    {"name": "   "},
    {"source_id": "../../outside"},
    {"country": "FRA"},
    {"parent_source_key": "ERP_BETA:product:PARENT"},
    {"entity_type": "product", "roles": ["customer"]},
    {"manufacturer": "Product field on a legal entity"},
    {"actor": {"name": "injected", "role": "executor"}},
])
def test_nested_source_validation_returns_json_422_without_ingestion(guarded_client, changes):
    record = next(record for record in demo_records() if record.key in ORION_KEYS).model_dump(mode="json")
    response = guarded_client.post("/api/ingest", headers=headers("executor"),
                                   json={"records": [{**record, **changes}]})
    errors = assert_response(response, 422)["detail"]
    assert isinstance(errors, list) and errors
    assert all(error["loc"][:3] == ["body", "records", 0] for error in errors)


@pytest.mark.parametrize(("path", "body"), [
    ("/api/decisions/merge", {"group_ids": ["one"], "expected_versions": {}, "reason": "r", "idempotency_key": "k"}),
    ("/api/decisions/merge", {"group_ids": ["one", "two"], "expected_versions": {}, "reason": "", "idempotency_key": "k"}),
    ("/api/decisions/merge", {"group_ids": ["one", "two"], "expected_versions": {"one": "not-an-integer"}, "reason": "r", "idempotency_key": "k"}),
    ("/api/preview-merge", {"group_ids": ["one", "two"], "actor": "requester"}),
    ("/api/decisions/split", {"group_id": "one", "partitions": [["a"]], "expected_version": 1, "reason": "r", "idempotency_key": "k"}),
    ("/api/decisions/unmerge", {"merge_decision_id": "one", "expected_versions": {}, "reason": "r"}),
    ("/api/decisions/one/approve", {"expected_version": 0}),
    ("/api/decisions/one/reject", {"expected_version": 1, "actor": {"role": "approver"}}),
    ("/api/decisions/one/execute", {"expected_version": "not-an-integer"}),
])
def test_invalid_operation_bodies_do_not_reach_the_ledger(guarded_client, path, body):
    response = guarded_client.post(path, json=body, headers=headers("requester"))
    assert isinstance(assert_response(response, 422)["detail"], list)


def test_malformed_json_and_invalid_content_length_keep_error_and_correlation_contracts(guarded_client):
    malformed = guarded_client.post("/api/ingest", content=b'{"records": [',
                                    headers={**headers("executor"), "Content-Type": "application/json"})
    assert assert_response(malformed, 422)["detail"][0]["type"] == "json_invalid"
    invalid_length = guarded_client.post("/api/consume", content=b"{}",
                                         headers={**headers("executor"), "Content-Length": "invalid"})
    assert assert_response(invalid_length, 400)["detail"] == "invalid content length"
    assert malformed.headers["x-correlation-id"] != invalid_length.headers["x-correlation-id"]


@pytest.mark.parametrize(("error", "status", "detail"), [
    (Conflict("source changed; reload"), 409, "source changed; reload"),
    (PermissionError("the requester role is required"), 403, "the requester role is required"),
    (ValueError("invalid identifier"), 422, "invalid identifier"),
    (KeyError("private source key"), 404, "record not found"),
])
def test_domain_failures_remain_http_errors_with_safe_headers(error, status, detail):
    class FailingRead:
        def history(self, identifier):
            raise error

    with TestClient(create_app(FailingRead(), ACTORS)) as client:
        response = client.get(f"/api/golden/{uuid4()}/history", headers=headers())
        assert assert_response(response, status) == {"detail": detail}


def test_nested_source_types_and_database_response_values_survive_http_serialization():
    record = next(record for record in demo_records() if record.key in ORION_KEYS).model_dump(mode="json")
    record.update(name="Étoile Industrie", valid_from="2026-01-01T03:00:00+03:00")
    identity = uuid4()

    class SerializationProbe:
        def ingest(self, records):
            assert len(records) == 1 and isinstance(records[0], SourceRecord)
            assert records[0].valid_from == datetime(2026, 1, 1, tzinfo=timezone.utc)
            assert records[0].roles == ("customer",)
            return {"identity": identity, "record": records[0], "known_at": datetime(2026, 1, 2, tzinfo=timezone.utc)}

    with TestClient(create_app(SerializationProbe(), ACTORS)) as client:
        response = client.post("/api/ingest", json={"records": [record]}, headers=headers("executor"))
        payload = assert_response(response, 200)
        assert payload["identity"] == str(identity)
        assert payload["record"]["name"] == "Étoile Industrie"
        assert payload["record"]["roles"] == ["customer"]
        assert SourceRecord.model_validate(payload["record"]).model_dump(mode="json") == record
        assert datetime.fromisoformat(payload["known_at"]).utcoffset().total_seconds() == 0


def send(client, path, body=None, role="reader", status=200):
    response = client.get(path, headers=headers(role)) if body is None else client.post(path, json=body, headers=headers(role))
    return assert_response(response, status)


def memberships(snapshot):
    return {row["source_key"]: row["golden_id"] for row in snapshot["crosswalk"]}


def merge_body(snapshot, key):
    ids = sorted(set(memberships(snapshot).values()))
    return {"group_ids": ids,
            "expected_versions": {row["golden_id"]: row["version"] for row in snapshot["groups"] if row["golden_id"] in ids},
            "reason": "Synthetic HTTP compatibility decision", "idempotency_key": key}


def execute_http(client, decision):
    prefix = f"/api/decisions/{decision['decision_id']}"
    approved = send(client, prefix + "/approve", {"expected_version": decision["version"]}, "approver")
    return send(client, prefix + "/execute", {"expected_version": approved["version"]}, "executor")


@pytest.mark.integration
def test_real_http_merge_late_update_unmerge_preserves_identity_and_consumer_contract(service):
    records = [record for record in demo_records() if record.key in ORION_KEYS]
    with TestClient(create_app(service, ACTORS)) as client:
        data = {"records": [record.model_dump(mode="json") for record in records]}
        assert send(client, "/api/ingest", data, "executor")["accepted"] == 2
        assert send(client, "/api/ingest", data, "executor")["accepted"] == 0
        send(client, "/api/reconcile", {}, "executor")
        initial = send(client, "/api/overview")["snapshot"]
        original = memberships(initial)
        body = merge_body(initial, "http.compatibility.merge")
        preview = send(client, "/api/preview-merge", {"group_ids": body["group_ids"]})
        assert not preview["hard_conflicts"] and set(preview["source_keys"]) == ORION_KEYS
        assert preview["provenance"]["name"]["source_key"] in ORION_KEYS
        counts = initial["counts"]
        for role in ("reader", "approver", "executor"):
            send(client, "/api/decisions/merge", body, role, 403)
        assert send(client, "/api/overview")["snapshot"]["counts"] == counts
        requested = send(client, "/api/decisions/merge", body, "requester", 201)
        prefix = f"/api/decisions/{requested['decision_id']}"
        send(client, prefix + "/approve", {"expected_version": 1}, "requester", 403)
        send(client, prefix + "/execute", {"expected_version": 1}, "executor", 409)
        merged = execute_http(client, requested)
        assert len(set(merged["result"]["after_memberships"].values())) == 1
        replay = send(client, "/api/decisions/merge", body, "requester", 201)
        assert replay["decision_id"] == merged["decision_id"] and replay["status"] == "executed"
        send(client, "/api/decisions/merge", {**body, "reason": "changed submission"}, "requester", 409)
        update = SourceUpdate(next(record for record in records if record.source_system == "ERP_BETA"))
        send(client, "/api/ingest", {"records": [update.model_dump(mode="json")]}, "executor")
        current = send(client, "/api/overview")["snapshot"]
        active = set(memberships(current).values())
        undo = send(client, "/api/decisions/unmerge", {
            "merge_decision_id": merged["decision_id"], "reason": "Correct the synthetic mistaken merge",
            "idempotency_key": "http.compatibility.unmerge",
            "expected_versions": {row["golden_id"]: row["version"] for row in current["groups"] if row["golden_id"] in active},
        }, "requester", 201)
        execute_http(client, undo)
        assert send(client, "/api/consume", {}, "executor")["caught_up"]
        final = send(client, "/api/overview")
        assert memberships(final["snapshot"]) == original
        assert {row["source_key"]: row["golden_id"] for row in final["snapshot"]["consumer_crosswalk"]} == original
        updated = next(row for row in final["snapshot"]["sources"] if row["source_key"] == update.key)
        assert updated["current_payload"]["address"] == "Updated after the merge"
        history = send(client, f"/api/golden/{original[update.key]}/history")
        assert any(row["known_to"] is not None for row in history)
        assert all(datetime.fromisoformat(row["known_from"]).tzinfo for row in history)
        assert final["quality"]["crosswalk_coverage"] == 1 and service.check()["passed"]


@pytest.mark.integration
def test_real_http_reject_split_and_stale_versions_do_not_corrupt_the_ledger(service):
    service.ingest([record for record in demo_records() if record.key in ORION_KEYS])
    with TestClient(create_app(service, ACTORS)) as client:
        initial = send(client, "/api/overview")["snapshot"]
        body = merge_body(initial, "http.compatibility.rejected")
        decision = send(client, "/api/decisions/merge", body, "requester", 201)
        prefix = f"/api/decisions/{decision['decision_id']}"
        rejected = send(client, prefix + "/reject", {"expected_version": 1}, "approver")
        assert rejected["status"] == "rejected"
        send(client, prefix + "/execute", {"expected_version": 2}, "executor", 409)
        assert memberships(send(client, "/api/overview")["snapshot"]) == memberships(initial)
        decision = send(client, "/api/decisions/merge", {**body, "idempotency_key": "http.compatibility.split-merge"}, "requester", 201)
        merged = execute_http(client, decision)
        current = send(client, "/api/overview")["snapshot"]
        group_id = next(iter(set(merged["result"]["after_memberships"].values())))
        group = next(row for row in current["groups"] if row["golden_id"] == group_id)
        split_body = {"group_id": group_id, "partitions": [[key] for key in sorted(ORION_KEYS)],
                      "expected_version": group["version"], "reason": "Explicit synthetic separation",
                      "idempotency_key": "http.compatibility.split"}
        send(client, "/api/decisions/split", {**split_body, "expected_version": group["version"] - 1}, "requester", 409)
        split = send(client, "/api/decisions/split", split_body, "requester", 201)
        executed = execute_http(client, split)
        assert len(set(executed["result"]["after_memberships"].values())) == 2
        assert send(client, "/api/consume", {}, "executor")["caught_up"]
        send(client, f"/api/decisions/{uuid4()}/approve", {"expected_version": 1}, "approver", 404)
        send(client, "/api/decisions/not-a-uuid/approve", {"expected_version": 1}, "approver", 422)
        final = send(client, "/api/overview")["snapshot"]
        assert set(memberships(final)) == ORION_KEYS
        assert {row["source_key"]: row["golden_id"] for row in final["consumer_crosswalk"]} == memberships(final)
        assert service.check()["passed"]
