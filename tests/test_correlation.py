"""Context/HTTP tests are local; durable ledger checks require real PostgreSQL."""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from mdm.api import create_app
from mdm.config import Actor
from mdm.pipeline import SOURCES, run
from mdm.synthetic import demo_records
from mdm.telemetry import (
    correlated_operation, correlation_scope, current_context, emit, logger, metadata,
)

TOKEN = "correlation-unit-test-token-000000"


@pytest.fixture
def events(monkeypatch):
    entries = []

    class Capture(logging.Handler):
        def emit(self, record):
            entries.append(json.loads(record.getMessage()))

    monkeypatch.setattr(logger, "handlers", [Capture()])
    return entries


def test_nested_scopes_restore_context_on_success_and_failure():
    assert current_context() is None
    with correlation_scope(new=True) as outer:
        assert metadata()["correlation_id"] == outer.correlation_id
        run_id = str(uuid4())
        with correlation_scope(run_id=run_id):
            assert metadata()["run_id"] == run_id
            assert metadata()["correlation_id"] == outer.correlation_id
        assert current_context() == outer
        with pytest.raises(RuntimeError):
            with correlation_scope(new=True) as failed:
                assert failed.correlation_id != outer.correlation_id
                raise RuntimeError("test failure")
        assert current_context() == outer
    assert current_context() is None


def test_operation_failure_resets_context_and_never_logs_exception_text(events):
    @correlated_operation("test.failure")
    def fail():
        raise RuntimeError("private.person@example.invalid secret-token SQL statement")

    with pytest.raises(RuntimeError):
        fail()
    assert current_context() is None
    assert events[-1]["event"] == "operation.failed"
    assert events[-1]["error_type"] == "RuntimeError"
    assert "private.person" not in json.dumps(events)
    assert "secret-token" not in json.dumps(events)


@pytest.mark.parametrize("code", [None, 0, 2])
def test_cli_clean_exit_is_not_reported_as_an_operation_failure(events, code):
    @correlated_operation("cli.command")
    def cli_exit():
        raise SystemExit(code)

    with pytest.raises(SystemExit):
        cli_exit()
    expected = "operation.succeeded" if code in (None, 0) else "operation.failed"
    assert events[-1]["event"] == expected
    assert current_context() is None


def test_log_and_trace_allowlists_discard_untrusted_fields(events):
    secret = "private.person@example.invalid"
    with correlation_scope(new=True) as context:
        emit("test.allowlist", actor=secret, token=secret, payload={"name": secret}, reason=secret,
             sql=secret, source_key=secret, status={"secret": secret}, run_id=secret,
             correlation_id=secret, consumer="reporting", accepted=2)
        safe = metadata({"origin_correlation_id": secret, "run_id": secret, "actor": secret})
        assert safe["origin_correlation_id"] == context.correlation_id
    assert secret not in json.dumps(events)
    assert set(events[0]) == {"event", "trace_version", "correlation_id", "origin_correlation_id", "consumer", "accepted"}


def test_diagnostic_sink_failure_does_not_turn_a_completed_operation_into_an_error(monkeypatch):
    def broken_sink(*args, **kwargs):
        raise OSError("diagnostic stream unavailable")

    monkeypatch.setattr(logger, "info", broken_sink)

    @correlated_operation("test.completed")
    def completed():
        return {"accepted": 1}

    assert completed() == {"accepted": 1}
    assert current_context() is None


class ContextProbe:
    """HTTP transport/context double only; it is not a database integration."""

    def __init__(self):
        self.observed = []
        self.fail = False

    def snapshot(self):
        assert current_context() is not None
        value = {"trace": metadata(), "worker_thread": threading.get_ident()}
        self.observed.append(value)
        return value

    def quality(self):
        return {}

    def reconcile(self):
        value = self.snapshot()
        if self.fail:
            raise RuntimeError("private.person@example.invalid secret-query secret-token")
        return value


def test_fastapi_sync_worker_receives_http_context_and_ignores_incoming_trace_headers(events):
    probe = ContextProbe()
    client = TestClient(create_app(probe, {TOKEN: Actor("test", "executor")}))
    response = client.get("/api/overview?ignored=secret-query", headers={
        "Authorization": f"Bearer {TOKEN}", "X-Correlation-ID": "private.person@example.invalid",
    })
    assert response.status_code == 200
    identifier = response.headers["x-correlation-id"]
    assert str(UUID(identifier)) == identifier
    assert response.json()["snapshot"]["trace"]["correlation_id"] == identifier
    assert response.json()["snapshot"]["worker_thread"] != threading.get_ident()
    assert current_context() is None
    assert events[-1]["route"] == "/api/overview"
    assert TOKEN not in json.dumps(events)
    assert "private.person" not in json.dumps(events) and "secret-query" not in json.dumps(events)


def test_failed_request_has_a_correlated_safe_response_and_no_context_leaks(events):
    probe = ContextProbe()
    client = TestClient(create_app(probe, {TOKEN: Actor("test", "executor")}))
    headers = {"Authorization": f"Bearer {TOKEN}"}
    probe.fail = True
    failed = client.post("/api/reconcile", headers=headers)
    assert failed.status_code == 500
    assert failed.headers["x-correlation-id"] == probe.observed[-1]["trace"]["correlation_id"]
    probe.fail = False
    successful = client.post("/api/reconcile", headers=headers)
    assert successful.status_code == 200
    assert successful.headers["x-correlation-id"] != failed.headers["x-correlation-id"]
    assert successful.json()["trace"]["correlation_id"] == successful.headers["x-correlation-id"]
    assert current_context() is None
    assert "private.person" not in failed.text and "secret-token" not in json.dumps(events)
    assert any(event.get("error_type") == "RuntimeError" and event.get("status") == 500 for event in events)


def test_optional_trace_contract_accepts_legacy_payload_and_rejects_arbitrary_metadata():
    schema = json.loads((Path(__file__).resolve().parents[1] / "contracts/golden-event.v1.schema.json").read_text())
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    payload = {"contract_version": "golden-event.v1", "golden_id": str(uuid4()), "group_version": 1,
               "active": False, "source_keys": [], "attributes": {}, "provenance": {}, "conflicts": [],
               "business_slices": [], "correction_for": None}
    validator.validate(payload)
    validator.validate({**payload, "trace": metadata(event_id=uuid4())})
    with pytest.raises(ValidationError):
        validator.validate({**payload, "trace": {**metadata(), "actor_email": "private@example.invalid"}})
    with pytest.raises(ValidationError):
        validator.validate({**payload, "trace": {**metadata(), "correlation_id": "not-a-uuid"}})


@pytest.mark.integration
def test_http_decision_audit_outbox_and_consumer_share_durable_origin(service, events):
    records = [r for r in demo_records() if r.source_id in {"ORION-01", "ORION-02"}]
    service.ingest(records)
    snapshot = service.snapshot()
    ids = sorted({str(row["golden_id"]) for row in snapshot["crosswalk"]})
    versions = {str(row["golden_id"]): row["version"] for row in snapshot["groups"]}
    tokens = {"request-token-0000000000000000000000": Actor("requester", "requester"),
              "approve-token-0000000000000000000000": Actor("approver", "approver"),
              "execute-token-0000000000000000000000": Actor("executor", "executor")}
    client = TestClient(create_app(service, tokens))
    headers = [{"Authorization": f"Bearer {token}"} for token in tokens]
    body = {"group_ids": ids, "expected_versions": versions, "reason": "Reviewed synthetic identity",
            "idempotency_key": "correlation.merge"}
    requested = client.post("/api/decisions/merge", json=body, headers=headers[0])
    assert requested.status_code == 201
    decision = requested.json()
    origin = requested.headers["x-correlation-id"]
    assert decision["request"]["trace"]["correlation_id"] == origin
    approved = client.post(f"/api/decisions/{decision['decision_id']}/approve",
                           json={"expected_version": 1}, headers=headers[1])
    assert approved.status_code == 200
    executed = client.post(f"/api/decisions/{decision['decision_id']}/execute",
                           json={"expected_version": 2}, headers=headers[2])
    assert executed.status_code == 200
    execution_id = executed.headers["x-correlation-id"]
    with service.db.connect() as conn:
        audits = list(conn.execute("SELECT * FROM decision_events WHERE decision_id=%s", (decision["decision_id"],)))
        changes = list(conn.execute("SELECT * FROM outbox WHERE payload->>'correction_for'=%s", (decision["decision_id"],)))
    assert {row["transition"] for row in audits} == {"requested", "approved", "executed"}
    by_transition = {row["transition"]: row["payload"]["trace"] for row in audits}
    assert by_transition["approved"]["correlation_id"] == approved.headers["x-correlation-id"]
    assert by_transition["executed"]["correlation_id"] == execution_id
    assert all(row["payload"]["trace"]["origin_correlation_id"] == origin for row in audits + changes)
    assert all(row["payload"]["trace"]["event_id"] == str(row["event_id"]) for row in audits + changes)
    assert len(changes) == 2
    assert all(row["payload"]["trace"]["correlation_id"] == execution_id for row in changes)
    consumed = client.post("/api/consume", headers=headers[2])
    assert consumed.status_code == 200 and consumed.json()["caught_up"]
    with service.db.connect() as conn:
        receipts = list(conn.execute("SELECT i.event_id,o.payload->'trace' trace FROM consumer_inbox i "
                                     "JOIN outbox o USING(event_id) WHERE o.payload->>'correction_for'=%s",
                                     (decision["decision_id"],)))
        copies = list(conn.execute("SELECT payload FROM consumer_records WHERE consumer='reporting'"))
    assert len(receipts) == 2
    assert all(row["trace"]["origin_correlation_id"] == origin for row in receipts)
    assert all(row["payload"]["trace"]["origin_correlation_id"] == origin for row in copies)
    assert any(event["event"] == "consumer.acknowledged" and event["correlation_id"] == consumed.headers["x-correlation-id"]
               and event.get("origin_correlation_id") == origin for event in events)
    before = service.snapshot()["counts"]
    replayed = client.post("/api/decisions/merge", json=body, headers=headers[0])
    assert replayed.json()["request"]["trace"]["correlation_id"] == origin
    assert replayed.headers["x-correlation-id"] != origin
    assert service.snapshot()["counts"] == before


@pytest.mark.integration
def test_pipeline_retry_retains_run_and_origin_across_committed_automatic_work(service):
    records = [r for r in demo_records() if r.source_id in {"NORTHSTAR-01", "NS-44", "NS-900"}]
    sources = {source: [r for r in records if r.source_system == source] for source in SOURCES}
    with pytest.raises(RuntimeError, match="injected"):
        run(service, sources, run_key="correlation.run", failpoint="before_publication")
    assert current_context() is None
    with service.db.connect() as conn:
        previous = conn.execute("SELECT * FROM runs WHERE idempotency_key='correlation.run'").fetchone()
        changes = list(conn.execute("SELECT payload FROM outbox"))
        decisions = list(conn.execute("SELECT request FROM decisions WHERE kind='automatic_merge'"))
    identifier = str(previous["run_id"])
    origin = previous["result"]["trace"]["origin_correlation_id"]
    assert all(row["payload"]["trace"]["run_id"] == identifier for row in changes)
    assert all(row["request"]["trace"]["run_id"] == identifier for row in decisions)
    outcome = run(service, sources, run_key="correlation.run")
    assert outcome["consumer"]["caught_up"]
    assert outcome["trace"]["run_id"] == identifier
    assert outcome["trace"]["origin_correlation_id"] == origin
    assert outcome["trace"]["correlation_id"] != previous["result"]["trace"]["correlation_id"]
    assert run(service, sources, run_key="correlation.run") == outcome
    assert current_context() is None


@pytest.mark.integration
def test_rolled_back_execution_leaves_no_durable_trace_for_uncommitted_effects(service):
    service.ingest([r for r in demo_records() if r.source_id in {"ORION-01", "ORION-02"}])
    snapshot = service.snapshot()
    versions = {str(row["golden_id"]): row["version"] for row in snapshot["groups"]}
    request = service.request_merge(list(versions), versions, Actor("requester", "requester"),
                                    "Synthetic review", "correlation.rollback")
    service.approve(str(request["decision_id"]), Actor("approver", "approver"), 1)
    with correlation_scope(new=True) as failed:
        with pytest.raises(RuntimeError, match="injected"):
            service.execute(str(request["decision_id"]), Actor("executor", "executor"), 2, failpoint="before_outbox")
    with service.db.connect() as conn:
        for table in ("decision_events", "outbox"):
            # Table names are fixed in this test, never input metadata.
            assert conn.execute(f"SELECT count(*) n FROM {table} WHERE payload->'trace'->>'correlation_id'=%s",
                                (failed.correlation_id,)).fetchone()["n"] == 0
    completed = service.execute(str(request["decision_id"]), Actor("executor", "executor"), 2)
    assert completed["result"]["trace"]["correlation_id"] != failed.correlation_id
    assert current_context() is None
