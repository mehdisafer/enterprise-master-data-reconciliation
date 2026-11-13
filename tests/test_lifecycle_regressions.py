"""Real PostgreSQL regressions for retries, human policy and consumer consistency.

These tests require the explicitly supplied disposable *_test database. They are
never substituted with SQLite, a mocked connection or a skipped integration.
"""

from functools import partial
from uuid import uuid4

import pytest

from mdm.config import Actor
from mdm.domain import SourceRecord
from mdm.service import Conflict, now
from mdm.synthetic import demo_records

pytestmark = pytest.mark.integration
REQ = Actor("regression.requester", "requester")
APP = Actor("regression.approver", "approver")
EXE = Actor("regression.executor", "executor")


def selected(*ids):
    return [record for record in demo_records() if record.source_id in ids]


def state(service, keys=None):
    snap = service.snapshot()
    mapping = {row["source_key"]: str(row["golden_id"]) for row in snap["crosswalk"]}
    ids = sorted({mapping[key] for key in (keys or mapping)})
    versions = {str(group["golden_id"]): group["version"] for group in snap["groups"]
                if str(group["golden_id"]) in ids}
    return ids, versions, mapping


def complete(service, decision):
    approved = service.approve(str(decision["decision_id"]), APP, decision["version"])
    return service.execute(str(decision["decision_id"]), EXE, approved["version"])


def merge(service, keys=None, key="regression.merge"):
    ids, versions, _ = state(service, keys)
    return service.request_merge(ids, versions, REQ, "Reviewed identity evidence", key)


@pytest.mark.parametrize("operation", ["merge", "split", "unmerge"])
def test_request_retry_after_execution_returns_same_decision_despite_changed_topology(service, operation):
    records = selected("ORION-01", "ORION-02")
    service.ingest(records)
    ids, versions, _ = state(service)
    initial_args = (ids, versions, REQ, "Reviewed identity evidence", "regression.merge")
    merged = complete(service, service.request_merge(*initial_args))
    if operation == "merge":
        request, replay = merged, partial(service.request_merge, *initial_args)
    else:
        current_ids, current_versions, _ = state(service)
        if operation == "split":
            args = (current_ids[0], [[r.key] for r in records], current_versions[current_ids[0]],
                    REQ, "Separate identities", "regression.split")
            request = complete(service, service.request_split(*args))
            replay = partial(service.request_split, *args)
        else:
            args = (str(merged["decision_id"]), current_versions, REQ, "Undo incorrect merge", "regression.undo")
            request = complete(service, service.request_unmerge(*args))
            replay = partial(service.request_unmerge, *args)
    before = service.snapshot()["counts"]
    repeated = replay()
    assert repeated["decision_id"] == request["decision_id"]
    assert repeated["status"] == "executed"
    assert repeated["result"] == request["result"]
    assert service.snapshot()["counts"] == before
    assert service.check()["passed"]


def test_idempotency_replay_still_rejects_different_actor_reason_or_operation(service):
    service.ingest(selected("ORION-01", "ORION-02"))
    ids, versions, _ = state(service)
    complete(service, merge(service))
    with pytest.raises(Conflict, match="idempotency"):
        service.request_merge(ids, versions, REQ, "Different intended decision", "regression.merge")
    with pytest.raises(Conflict, match="idempotency"):
        service.request_merge(ids, versions, Actor("another", "requester"), "Reviewed identity evidence", "regression.merge")


@pytest.mark.parametrize("same_batch", [False, True])
def test_contradictory_payload_at_same_source_coordinate_rejects_atomically(service, same_batch):
    record = selected("ORION-01")[0]
    other = SourceRecord.model_validate({**record.model_dump(mode="json"), "address": "Contradictory assertion"})
    if not same_batch:
        service.ingest([record])
    before = service.snapshot()
    with pytest.raises(Conflict, match="validity/change coordinate"):
        service.ingest([record, other] if same_batch else [other])
    after = service.snapshot()
    assert after["counts"] == before["counts"]
    assert after["crosswalk"] == before["crosswalk"]
    assert after["sources"] == before["sources"]
    if not same_batch:
        assert service.ingest([record])["accepted"] == 0


def test_three_way_separation_blocks_all_automatic_rejoins_even_after_a_source_revision(service):
    records = selected("NORTHSTAR-01", "NS-44", "NS-900")
    service.ingest(records)
    service.reconcile()
    ids, versions, _ = state(service)
    assert len(ids) == 1
    split = service.request_split(ids[0], [[r.key] for r in records], versions[ids[0]],
                                  REQ, "Verified separate source identities", "regression.split-three")
    complete(service, split)
    separated = state(service)[2]
    assert len(set(separated.values())) == 3
    outcome = service.reconcile()
    assert outcome["automatic_merges"] == 0
    assert outcome["policy_blocked_candidates"] == 3
    assert state(service)[2] == separated
    updated = SourceRecord.model_validate({**records[1].model_dump(mode="json"),
        "source_updated_at": "2026-10-03T00:00:00Z", "address": "A newer address does not undo a human separation"})
    service.ingest([updated])
    assert service.reconcile()["automatic_merges"] == 0
    assert state(service)[2] == separated
    snapshot = service.snapshot()
    assert len(snapshot["policy_blocks"]) == 3
    assert all(row["disposition"] == "review" and row["evidence"]["decision"] == "auto"
               for row in snapshot["candidates"])
    assert service.quality()["suspected_duplicate_pairs"] == 0
    assert service.quality()["policy_blocked_candidates"] == 3
    complete(service, merge(service, key="regression.explicit-override"))
    assert len(state(service)[0]) == 1
    assert service.snapshot()["policy_blocks"] == []


def test_automatic_merge_checks_negative_pairs_across_whole_existing_groups(service):
    records = selected("NORTHSTAR-01", "NS-44", "NS-900")
    by_id = {r.source_id: r for r in records}
    a, b, c = by_id["NORTHSTAR-01"], by_id["NS-44"], by_id["NS-900"]
    service.ingest(records)
    rejection = merge(service, [b.key, c.key], key="regression.reject-bc")
    service.approve(str(rejection["decision_id"]), APP, rejection["version"], reject=True)
    complete(service, merge(service, [a.key, b.key], key="regression.merge-ab"))
    before = state(service)[2]
    assert service.reconcile()["automatic_merges"] == 0
    assert state(service)[2] == before
    ac = next(row for row in service.snapshot()["candidates"] if {row["left_key"], row["right_key"]} == {a.key, c.key})
    assert ac["disposition"] == "review"
    assert {ac["policy_blocks"][0]["left_key"], ac["policy_blocks"][0]["right_key"]} == {b.key, c.key}


def test_policy_precedence_uses_execution_time_not_request_creation_time(service):
    records = selected("ORION-01", "ORION-02")
    service.ingest(records)
    older = merge(service, key="regression.created-first")
    newer = merge(service, key="regression.created-second")
    service.approve(str(newer["decision_id"]), APP, newer["version"], reject=True)
    complete(service, older)  # Older request executes after the newer rejection.
    with service.db.connect() as conn:
        events = service._policy_events(conn)
    assert events[-1]["decision_id"] == str(older["decision_id"])
    assert service._pair_policy(*sorted(r.key for r in records), events) is None


def occupy_old_destination(service, destination):
    """Inject a separately committed topology change at the storage boundary.

    This exercises destination validation independently of request validation.
    All other graph invariants are preserved by the fixture transaction.
    """
    outsider = selected("CELADON-01")[0]
    service.ingest([outsider])
    _, _, mapping = state(service, [outsider.key])
    original = mapping[outsider.key]
    with service.db.connect(write=True) as conn:
        timestamp = now(conn)
        conn.execute("UPDATE memberships SET golden_id=%s WHERE source_key=%s", (destination, outsider.key))
        conn.execute("UPDATE membership_history SET known_to=%s WHERE source_key=%s AND known_to IS NULL",
                     (timestamp, outsider.key))
        conn.execute("INSERT INTO membership_history VALUES(%s,%s,%s,%s,NULL)",
                     (uuid4(), outsider.key, destination, timestamp))
        service._rebuild(conn, original, timestamp)
        service._rebuild(conn, destination, timestamp)
    assert service.check()["passed"]


@pytest.mark.parametrize("after_approval", [False, True])
def test_unmerge_rejects_an_old_destination_that_now_has_unrelated_members(service, after_approval):
    records = selected("ORION-01", "ORION-02")
    service.ingest(records)
    original_ids, _, _ = state(service)
    merged = complete(service, merge(service))
    current_ids, versions, _ = state(service)
    destination = next(group for group in original_ids if group not in current_ids)
    args = (str(merged["decision_id"]), versions, REQ, "Restore original identities", "regression.restore")
    if after_approval:
        requested = service.request_unmerge(*args)
        approved = service.approve(str(requested["decision_id"]), APP, requested["version"])
    occupy_old_destination(service, destination)
    before = service.snapshot()
    with pytest.raises(Conflict, match="destination"):
        if after_approval:
            service.execute(str(approved["decision_id"]), EXE, approved["version"])
        else:
            service.request_unmerge(*args)
    assert service.snapshot()["crosswalk"] == before["crosswalk"]
    assert service.snapshot()["counts"] == before["counts"]


def test_partial_consumer_reports_coverage_and_finishes_whole_correction_with_limit_one(service):
    records = selected("ORION-01", "ORION-02")
    service.ingest(records)
    first = service.consume(limit=1)
    assert first["processed"] == 1 and not first["caught_up"]
    assert first["reference_coverage"] == 0.5
    assert first["consumed_coverage"] == 1.0
    assert len(first["missing_sources"]) == 1
    assert service.consume()["caught_up"]
    complete(service, merge(service))
    corrected = service.consume(limit=1)
    assert corrected["processed"] == 2
    assert corrected["expanded_for_atomic_corrections"] == 1
    assert corrected["caught_up"]
    assert corrected["reference_coverage"] == corrected["consumed_coverage"] == 1.0
    assert corrected["conflicting_sources"] == corrected["unexpected_active_groups"] == []
    assert service.consume(limit=1)["processed"] == 0


def test_caught_up_requires_projection_integrity_not_only_an_empty_outbox(service):
    service.ingest(selected("ORION-01", "ORION-02"))
    assert service.consume()["caught_up"]
    with service.db.connect(write=True) as conn:
        conn.execute("DELETE FROM consumer_crosswalk WHERE consumer='reporting'")
    state = service.consume()
    assert state["remaining"] == 0 and not state["caught_up"]
    assert len(state["missing_sources"]) == 2


def test_quality_counts_only_current_unresolved_pairs_and_snapshot_selects_one_mode(service):
    records = selected("ORION-01", "ORION-02")
    service.ingest(records)
    service.reconcile(mode="deterministic")
    service.reconcile(mode="hybrid")
    assert len(service.snapshot()["candidates"]) == 1
    assert service.snapshot()["candidates"][0]["mode"] == "hybrid"
    assert service.quality()["suspected_duplicate_pairs"] == 1
    updated = SourceRecord.model_validate({**records[0].model_dump(mode="json"),
        "address": "A new address", "source_updated_at": "2026-10-03T00:00:00Z"})
    service.ingest([updated])
    assert service.quality()["suspected_duplicate_pairs"] == 0
    service.reconcile()
    assert service.quality()["suspected_duplicate_pairs"] == 0


def test_merge_preview_exposes_conflicts_without_inventing_a_golden_record(service):
    records = selected("BRIDGE-A", "BRIDGE-B", "BRIDGE-C")
    service.ingest(records)
    ids, versions, _ = state(service)
    preview = service.preview_merge(ids)
    assert preview["attributes"] is None
    assert preview["expected_versions"] == versions
    assert any("registration_id_conflict" in conflict for conflict in preview["hard_conflicts"])
    compatible_ids, _, _ = state(service, [r.key for r in records if r.source_id != "BRIDGE-C"])
    compatible = service.preview_merge(compatible_ids)
    assert compatible["attributes"] is not None
    assert compatible["provenance"]["name"]["source_key"] in compatible["source_keys"]
    with pytest.raises(Conflict):
        service.preview_merge([ids[0], str(uuid4())])

