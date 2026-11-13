"""Real transactional tests. No mocks, fallback database or skipped integration."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import psycopg
import pytest

from mdm.config import Actor
from mdm.demo import demonstrate, execute_request
from mdm.pipeline import SOURCES, run
from mdm.service import Conflict
from mdm.synthetic import demo_records, late_record

pytestmark = pytest.mark.integration
REQ, APP, EXE = Actor("requester", "requester"), Actor("approver", "approver"), Actor("executor", "executor")


def ids_versions(service, keys=None):
    snap = service.snapshot()
    mapping = {r["source_key"]: str(r["golden_id"]) for r in snap["crosswalk"]}
    ids = sorted({mapping[key] for key in (keys or mapping)})
    versions = {str(g["golden_id"]): g["version"] for g in snap["groups"] if str(g["golden_id"]) in ids}
    return ids, versions, mapping


def orion(service):
    records = [r for r in demo_records() if r.source_id in {"ORION-01", "ORION-02"}]
    service.ingest(records)
    return records


def requested(service, key="merge.1"):
    ids, versions, _ = ids_versions(service)
    return service.request_merge(ids, versions, REQ, "Manually reviewed identity evidence", key)


def test_real_end_to_end_demonstration_and_repeat(service):
    report = demonstrate(service)
    assert all(report["assertions"].values())
    assert report["late_ingestion"]["accepted"] == 1
    assert demonstrate(service)["already_executed"]


def test_ingestion_is_idempotent_raw_is_immutable_and_migration_repeats(service):
    records = demo_records()
    service.ingest(records)
    before = service.snapshot()
    assert service.ingest(records)["accepted"] == 0
    assert service.snapshot()["counts"] == before["counts"]
    assert not service.db.migrate()["applied"]
    with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
        with service.db.connect(write=True) as conn:
            conn.execute("DELETE FROM raw_records")
    assert service.check()["passed"]


def test_late_correction_keeps_authority_and_two_time_axes(service):
    records = [r for r in demo_records() if r.source_id in {"NORTHSTAR-01", "NS-44", "NS-900"}]
    service.ingest(records)
    service.reconcile()
    ids, _, _ = ids_versions(service)
    assert len(ids) == 1
    before = service.history(ids[0])
    service.ingest([late_record()])
    history = service.history(ids[0])
    assert len(history) > len(before)
    assert any(h["known_to"] is not None for h in history)
    current = [h for h in history if h["known_to"] is None]
    assert all(h["provenance"]["name"]["source_key"] == "ERP_ALPHA:organization:NORTHSTAR-01" for h in current)
    assert any(h["valid_from"] < h["known_from"] for h in history)
    assert service.check()["passed"]


def test_separation_of_duties_and_optimistic_decision_version(service):
    orion(service)
    decision = requested(service)
    with pytest.raises(PermissionError):
        service.approve(str(decision["decision_id"]), Actor("requester", "approver"), 1)
    approved = service.approve(str(decision["decision_id"]), APP, 1)
    with pytest.raises(PermissionError):
        service.execute(str(decision["decision_id"]), Actor("approver", "executor"), 2)
    with pytest.raises(Conflict):
        service.execute(str(decision["decision_id"]), EXE, 1)
    done = service.execute(str(decision["decision_id"]), EXE, approved["version"])
    assert service.execute(str(decision["decision_id"]), EXE, approved["version"])["result"] == done["result"]


def test_concurrent_decisions_only_one_can_execute(service):
    orion(service)
    one, two = requested(service, "one"), requested(service, "two")
    for decision in (one, two):
        service.approve(str(decision["decision_id"]), APP, 1)
    def execute(decision):
        try:
            return service.execute(str(decision["decision_id"]), EXE, 2)["status"]
        except Conflict:
            return "conflict"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(execute, [one, two]))
    assert sorted(results) == ["conflict", "executed"]
    assert service.check()["passed"]


def test_source_revision_invalidates_approved_plan(service):
    records = orion(service)
    decision = requested(service)
    service.approve(str(decision["decision_id"]), APP, 1)
    changed = records[0].model_copy(update={"address": "New legal address", "source_updated_at": datetime(2026, 10, 2, tzinfo=timezone.utc)})
    service.ingest([changed])
    with pytest.raises(Conflict, match="version"):
        service.execute(str(decision["decision_id"]), EXE, 2)


def test_atomic_crash_before_outbox_rolls_back_then_retries(service):
    orion(service)
    decision = requested(service)
    service.approve(str(decision["decision_id"]), APP, 1)
    before = service.snapshot()
    with pytest.raises(RuntimeError, match="injected"):
        service.execute(str(decision["decision_id"]), EXE, 2, failpoint="before_outbox")
    after = service.snapshot()
    assert before["counts"] == after["counts"]
    assert before["crosswalk"] == after["crosswalk"]
    assert after["decisions"][0]["status"] == "approved"
    service.execute(str(decision["decision_id"]), EXE, 2)
    assert service.check()["passed"]


def test_consumer_crash_duplicate_delivery_and_out_of_order_version(service):
    orion(service)
    with pytest.raises(RuntimeError):
        service.consume(failpoint="before_ack")
    assert not service.snapshot()["consumers"]
    service.consume()
    decision = execute_request(service, requested(service))
    service.consume()
    final = service.snapshot()["consumers"]
    with service.db.connect(write=True) as conn:
        conn.execute("DELETE FROM consumer_inbox")  # replay old events on purpose
    service.consume()
    assert service.snapshot()["consumers"] == final
    assert service.consume()["processed"] == 0
    assert decision["status"] == "executed"


def test_split_and_unmerge_preserve_source_updates_and_negative_decision(service):
    records = orion(service)
    original = ids_versions(service)[2]
    merged = execute_request(service, requested(service))
    updated = records[0].model_copy(update={"address": "Newer address", "source_updated_at": datetime(2026, 10, 3, tzinfo=timezone.utc)})
    service.ingest([updated])
    ids, versions, _ = ids_versions(service)
    request = service.request_unmerge(str(merged["decision_id"]), versions, REQ, "Separate proven legal identities", "undo.1")
    execute_request(service, request)
    assert ids_versions(service)[2] == original
    assert any(r.address == "Newer address" for r in service.records())
    service.reconcile()
    assert ids_versions(service)[2] == original
    assert service.check()["passed"]


def test_explicit_split_partitions_are_total_and_unmerge_after_topology_change_fails(service):
    records = orion(service)
    merged = execute_request(service, requested(service))
    ids, versions, _ = ids_versions(service)
    with pytest.raises(ValueError, match="exactly once"):
        service.request_split(ids[0], [[records[0].key], [records[0].key]], versions[ids[0]], REQ, "Invalid split", "bad")
    split = service.request_split(ids[0], [[r.key] for r in records], versions[ids[0]], REQ, "Two distinct identities", "split.1")
    execute_request(service, split)
    with pytest.raises(Conflict, match="topology"):
        service.request_unmerge(str(merged["decision_id"]), {}, REQ, "Would override later split", "undo.bad")
    assert service.check()["passed"]


def test_bridge_group_cannot_bypass_conflicting_endpoints(service):
    records = [r for r in demo_records() if r.source_id in {"BRIDGE-A", "BRIDGE-B", "BRIDGE-C"}]
    service.ingest(records)
    ids, versions, _ = ids_versions(service)
    with pytest.raises(Conflict, match="registration_id_conflict"):
        service.request_merge(ids, versions, REQ, "Transitive links are insufficient", "bridge")


def test_partial_source_is_degraded_not_deletion_and_retry_uses_checkpoints(service):
    records = demo_records()
    sources = {s: [r for r in records if r.source_system == s] for s in SOURCES}
    sources["ERP_GAMMA"] = None
    with pytest.raises(RuntimeError):
        run(service, sources, run_key="partial", failpoint="before_publication")
    before = service.snapshot()["counts"]
    result = run(service, sources, run_key="partial")
    assert result["status"] == "degraded"
    assert result["consumer"]["caught_up"]
    assert service.snapshot()["counts"] == before
    assert run(service, sources, run_key="partial") == result
    sources["ERP_GAMMA"] = [r for r in records if r.source_system == "ERP_GAMMA"]
    with pytest.raises(Conflict, match="different input"):
        run(service, sources, run_key="partial")
    assert run(service, sources, run_key="restored")["status"] == "succeeded"
    assert len(service.records()) == len(records)


def test_temporal_overlap_is_rejected_at_database_boundary(service):
    orion(service)
    with pytest.raises(psycopg.errors.RaiseException, match="overlapping"):
        with service.db.connect(write=True) as conn:
            conn.execute("INSERT INTO golden_history SELECT gen_random_uuid(),golden_id,group_version+100,attributes,provenance,conflicts,valid_from,valid_to,known_from,known_to FROM golden_history LIMIT 1")


def test_partitioned_ingestion_keeps_candidate_and_identity_invariants(service):
    records = demo_records()
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(service.ingest, [[r for r in records if r.source_system==s] for s in SOURCES]))
    service.reconcile()
    first = ids_versions(service)[2]
    service.reconcile()
    assert ids_versions(service)[2] == first
    assert len(first) == len(records)
    assert service.check()["passed"]
