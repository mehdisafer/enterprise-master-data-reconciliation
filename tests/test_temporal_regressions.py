"""Historical identity constraints must be checked before proposing a merge."""
import pytest

from mdm.config import Actor
from mdm.domain import SourceRecord
from mdm.service import Conflict

pytestmark = pytest.mark.integration


def record(source, identifier, registration, *, start="2026-01-01T00:00:00Z", name="Temporal Industries"):
    return SourceRecord.model_validate({
        "source_system": source, "entity_type": "organization", "source_id": identifier,
        "name": name, "country": "FR", "registration_id": registration,
        "valid_from": start, "source_updated_at": start,
    })


def changing_pair(service, *, second_start="2026-01-01T00:00:00Z"):
    left = record("ERP_ALPHA", "TEMP-A", "HISTORICAL-A")
    right = record("ERP_BETA", "TEMP-B", "HISTORICAL-B", start=second_start)
    service.ingest([left, right])
    service.ingest([record("ERP_ALPHA", "TEMP-A", "HISTORICAL-B", start="2026-02-01T00:00:00Z")])
    return left, right


def groups(service, records):
    snapshot = service.snapshot()
    keys = {record.key for record in records}
    ids = sorted({str(row["golden_id"]) for row in snapshot["crosswalk"] if row["source_key"] in keys})
    versions = {str(group["golden_id"]): group["version"] for group in snapshot["groups"]
                if str(group["golden_id"]) in ids}
    return ids, versions


def test_historical_conflict_retains_evidence_and_does_not_abort_unrelated_merge(service):
    left, right = changing_pair(service)
    stable = [record("ERP_ALPHA", "OTHER-A", "STABLE-ID", name="Unrelated Manufacturing"),
              record("ERP_GAMMA", "OTHER-B", "STABLE-ID", name="Unrelated Manufacturing")]
    service.ingest(stable)
    outcome = service.reconcile()
    assert outcome["automatic_merges"] == 1
    assert outcome["group_conflicts"] == 1
    assert len(groups(service, [left, right])[0]) == 2
    assert len(groups(service, stable)[0]) == 1
    candidate = next(row for row in service.snapshot()["candidates"]
                     if {row["left_key"], row["right_key"]} == {left.key, right.key})
    assert candidate["evidence"]["decision"] == "auto"
    assert candidate["disposition"] == "group_conflict"
    assert any("historical_interval" in conflict for conflict in candidate["group_conflicts"])
    assert service.consume()["caught_up"]
    assert service.check()["passed"]


def test_preview_and_request_explain_historical_conflict_without_mutation(service):
    records = changing_pair(service)
    ids, versions = groups(service, records)
    before = service.snapshot()["counts"]
    preview = service.preview_merge(ids)
    assert preview["attributes"] is None
    assert any("historical_interval" in conflict and "registration_id_conflict" in conflict
               for conflict in preview["hard_conflicts"])
    assert any("2026-01-01" in conflict and "2026-02-01" in conflict for conflict in preview["hard_conflicts"])
    with pytest.raises(Conflict, match="historical_interval"):
        service.request_merge(ids, versions, Actor("temporal.requester", "requester"),
                              "Review all business intervals", "temporal.conflict")
    assert service.snapshot()["counts"] == before


def test_nonoverlapping_historical_identifiers_do_not_create_a_false_conflict(service):
    records = changing_pair(service, second_start="2026-02-01T00:00:00Z")
    assert not service.preview_merge(groups(service, records)[0])["hard_conflicts"]
    assert service.reconcile()["automatic_merges"] == 1
    assert len(groups(service, records)[0]) == 1
    assert service.check()["passed"]


def test_corrected_historical_assertion_can_unblock_merge_without_erasing_prior_knowledge(service):
    left, right = changing_pair(service)
    assert service.reconcile()["group_conflicts"] == 1
    correction = SourceRecord.model_validate({**left.model_dump(mode="json"),
        "registration_id": "HISTORICAL-B", "source_updated_at": "2026-03-01T00:00:00Z"})
    service.ingest([correction])
    ids, _ = groups(service, [left, right])
    assert service.preview_merge(ids)["hard_conflicts"] == []
    assert service.reconcile()["automatic_merges"] == 1
    merged_ids, _ = groups(service, [left, right])
    assert len(merged_ids) == 1
    historical = [row for group_id in ids for row in service.history(group_id)]
    assert any(row["known_to"] is not None and row["attributes"]["registration_id"] == left.registration_id
               for row in historical)
    assert service.consume()["caught_up"]
    assert service.check()["passed"]


def test_snapshot_recomputes_group_conflict_after_a_third_member_changes(service):
    older = record("ERP_ALPHA", "THIRD", "HISTORICAL-A")
    left = record("ERP_BETA", "UNCHANGED-A", "HISTORICAL-B", start="2026-02-01T00:00:00Z")
    right = record("ERP_GAMMA", "UNCHANGED-B", "HISTORICAL-B")
    service.ingest([older, left])
    service.ingest([record("ERP_ALPHA", "THIRD", "HISTORICAL-B", start="2026-02-01T00:00:00Z")])
    assert service.reconcile()["automatic_merges"] == 1
    service.ingest([right])
    assert service.reconcile()["group_conflicts"] == 2

    def unchanged_pair():
        return next(row for row in service.snapshot()["candidates"]
                    if {row["left_key"], row["right_key"]} == {left.key, right.key})

    before = unchanged_pair()
    assert before["disposition"] == "group_conflict"
    service.ingest([SourceRecord.model_validate({**older.model_dump(mode="json"),
        "registration_id": "HISTORICAL-B", "source_updated_at": "2026-03-01T00:00:00Z"})])
    after = unchanged_pair()  # No reconcile: the endpoints and evidence are unchanged.
    assert after["candidate_id"] == before["candidate_id"]
    assert after["left_revision"] == before["left_revision"]
    assert after["right_revision"] == before["right_revision"]
    assert after["evidence"] == before["evidence"]
    assert after["group_conflicts"] == [] and after["disposition"] == "auto"
    assert service.quality()["group_conflicting_candidates"] == 0
    assert len(groups(service, [left, right])[0]) == 2
    assert service.check()["passed"]
