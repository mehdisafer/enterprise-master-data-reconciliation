"""A real database scenario, not a static response or a mocked demonstration."""
from __future__ import annotations

from mdm.config import Actor
from mdm.pipeline import SOURCES, run
from mdm.service import Service
from mdm.synthetic import demo_records, late_record

REQUESTER = Actor("demo.requester", "requester")
APPROVER = Actor("demo.approver", "approver")
EXECUTOR = Actor("demo.executor", "executor")


def execute_request(service: Service, decision):
    if decision["status"] == "pending":
        decision = service.approve(str(decision["decision_id"]), APPROVER, decision["version"])
    if decision["status"] == "approved":
        decision = service.execute(str(decision["decision_id"]), EXECUTOR, decision["version"])
    if decision["status"] != "executed":
        raise ValueError("the demonstration decision was rejected; inspect it before starting another scenario")
    return decision


def demonstrate(service: Service) -> dict:
    records = demo_records()
    with service.db.connect() as conn:
        existing_keys = {r["source_key"] for r in conn.execute("SELECT source_key FROM source_records")}
        prior = conn.execute("SELECT * FROM decisions WHERE idempotency_key='demo:unmerge-orion:v1'").fetchone()
        prior_merge = conn.execute("SELECT * FROM decisions WHERE idempotency_key='demo:merge-orion:v1'").fetchone()
    if existing_keys - {r.key for r in records}:
        raise ValueError("the demonstration requires a dedicated database containing only its synthetic source identities")
    if prior:
        already_executed = prior["status"] == "executed"
        execute_request(service, prior)
        publication = service.consume()
        checks = service.check()
        if not checks["passed"] or not publication["caught_up"]:
            raise AssertionError("resumed demonstration is not reconciled")
        return {"already_executed": already_executed, "resumed": True, "publication": publication,
                "check": checks, "quality": service.quality(), "snapshot": service.snapshot()}
    baseline = run(service, {s: [r for r in records if r.source_system == s] for s in SOURCES}, run_key="demo:initial:v1")
    repeat = service.ingest(records)
    initial = service.snapshot()
    by_source = {r["source_key"]: str(r["golden_id"]) for r in initial["crosswalk"]}
    if prior_merge and prior_merge["status"] == "executed":
        by_source.update(prior_merge["result"]["before_memberships"])
    by_id = {str(r["golden_id"]): r for r in initial["groups"]}
    orion_keys = ["ERP_ALPHA:organization:ORION-01", "ERP_BETA:organization:ORION-02"]
    group_ids = sorted({by_source[k] for k in orion_keys})
    request = prior_merge or service.request_merge(group_ids, {g: by_id[g]["version"] for g in group_ids}, REQUESTER,
        "Demonstration: steward initially mistakes two similar Orion companies for one identity.", "demo:merge-orion:v1")
    merge = execute_request(service, request)
    service.consume()
    merged = service.snapshot()
    late = service.ingest([late_record()])
    # Also update a member of the mistaken group after merging. Unmerge restores
    # its identity, while preserving this later business assertion.
    orion = next(r for r in records if r.key == orion_keys[1])
    update = SourceUpdate(orion)
    service.ingest([update])
    before_unmerge = service.snapshot()
    versions = {str(g["golden_id"]): g["version"] for g in before_unmerge["groups"] if g["status"] == "active"}
    merged_group = merge["result"]["after_memberships"][orion_keys[0]]
    undo = service.request_unmerge(str(merge["decision_id"]), {merged_group: versions[merged_group]}, REQUESTER,
        "Registry evidence confirms two separate companies; preserve both source identities and later updates.", "demo:unmerge-orion:v1")
    undone = execute_request(service, undo)
    # This is the exact crash boundary: the domain transaction has committed,
    # but the reporting consumer still holds the earlier interpretation.
    after_commit_before_publication = service.snapshot()
    publication = service.consume()
    duplicate_delivery = service.consume()
    final = service.snapshot()
    final_map = {r["source_key"]: str(r["golden_id"]) for r in final["crosswalk"]}
    consumer_map = {r["source_key"]: str(r["golden_id"]) for r in final["consumer_crosswalk"] if r["consumer"] == "reporting"}
    assertions = {
        "repeat_ingestion_no_writes": repeat["accepted"] == 0,
        "orion_split_restores_original_ids": all(final_map[k] == by_source[k] for k in orion_keys),
        "consumer_crosswalk_matches_reference": consumer_map == final_map,
        "duplicate_event_poll_no_writes": duplicate_delivery["processed"] == 0,
        "late_assertion_preserved": any(r["current_payload"]["address"] == "Updated after the merge" for r in final["sources"]),
        "invariants": service.check()["passed"],
    }
    if not all(assertions.values()):
        raise AssertionError(assertions)
    return {"contract_version": "demo.v1", "resumed": prior_merge is not None,
            "initial_stage_is_resume_state": prior_merge is not None, "baseline": baseline, "repeated_ingestion": repeat, "late_ingestion": late,
            "merge_decision": str(merge["decision_id"]), "unmerge_decision": str(undone["decision_id"]),
            "publication": publication, "assertions": assertions,
            "stages": {"initial": initial, "merged": merged, "after_commit_before_publication": after_commit_before_publication,
                       "corrected": final}, "quality": service.quality(), "check": service.check()}


def SourceUpdate(record):
    from datetime import datetime, timezone
    from mdm.domain import SourceRecord
    data = record.model_dump()
    data.update(address="Updated after the merge", valid_from=datetime(2026, 10, 2, tzinfo=timezone.utc),
                source_updated_at=datetime(2026, 10, 3, tzinfo=timezone.utc))
    return SourceRecord.model_validate(data)

