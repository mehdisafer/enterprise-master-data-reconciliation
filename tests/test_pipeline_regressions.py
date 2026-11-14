"""Publication checkpoints and retries against a real disposable PostgreSQL.

Batch wrappers below call the actual transactional consumer. No database or
consumer outcome is replaced with an in-memory implementation.
"""
from functools import partial

import pytest
from psycopg.types.json import Jsonb

from mdm import pipeline
from mdm.pipeline import SOURCES, PublicationIncomplete, run
from mdm.service import Conflict, now
from mdm.synthetic import demo_records

pytestmark = pytest.mark.integration


def manifest(*, unavailable=False):
    records = [record for record in demo_records()
               if record.source_id in {"ORION-01", "ORION-02", "NS-900"}]
    sources = {source: [record for record in records if record.source_system == source] for source in SOURCES}
    if unavailable:
        sources["ERP_GAMMA"] = None
    return sources


def stored_run(service, key):
    with service.db.connect() as conn:
        record = conn.execute("SELECT * FROM runs WHERE idempotency_key=%s", (key,)).fetchone()
        checkpoints = list(conn.execute(
            "SELECT source_system,status,accepted FROM run_sources WHERE run_id=%s ORDER BY source_system",
            (record["run_id"],),
        ))
    return record, checkpoints


def prohibit_reingestion(monkeypatch, service):
    def unexpected_ingestion(_records):
        pytest.fail("publication retry must reuse all committed source checkpoints")
    monkeypatch.setattr(service, "ingest", unexpected_ingestion)


@pytest.mark.parametrize("unavailable", [False, True])
def test_run_drains_real_single_event_batches_before_persisting_completion(service, monkeypatch, unavailable):
    sources = manifest(unavailable=unavailable)
    original_consume = service.consume
    batches = []

    def consume_one():
        batch = original_consume(limit=1)
        batches.append(batch)
        return batch

    monkeypatch.setattr(service, "consume", consume_one)
    result = run(service, sources, run_key="publication.small-batches")
    expected_events = 2 if unavailable else 3
    assert len(batches) == expected_events
    assert all(not batch["caught_up"] for batch in batches[:-1])
    assert result["consumer"]["caught_up"]
    assert result["consumer"]["remaining"] == 0
    assert result["consumer"]["processed"] == expected_events
    assert result["consumer"]["publication_batches"] == expected_events
    assert result["status"] == ("degraded" if unavailable else "succeeded")
    record, checkpoints = stored_run(service, "publication.small-batches")
    assert record["status"] == result["status"] and record["phase"] == "complete"
    assert record["attempts"] == 1 and record["result"] == result
    assert len(checkpoints) == 3
    assert sum(checkpoint["accepted"] for checkpoint in checkpoints) == expected_events
    assert next(row for row in checkpoints if row["source_system"] == "ERP_GAMMA")["status"] == (
        "unavailable" if unavailable else "succeeded"
    )
    assert run(service, sources, run_key="publication.small-batches") == result
    assert len(batches) == expected_events
    assert stored_run(service, "publication.small-batches")[0]["attempts"] == 1


def test_failure_after_a_committed_consumer_batch_resumes_without_reingestion(service, monkeypatch):
    sources = manifest()
    original_consume = service.consume
    calls = 0

    def crash_after_one_batch():
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected publication failure after one committed batch")
        return original_consume(limit=1)

    monkeypatch.setattr(service, "consume", crash_after_one_batch)
    with pytest.raises(RuntimeError, match="one committed batch"):
        run(service, sources, run_key="publication.crash")
    previous, checkpoints = stored_run(service, "publication.crash")
    before = service.snapshot()
    assert previous["status"] == "failed" and previous["phase"] == "publication"
    assert previous["attempts"] == 1
    assert before["consumer_status"][0]["remaining"] == 2
    monkeypatch.setattr(service, "consume", partial(original_consume, limit=1))
    prohibit_reingestion(monkeypatch, service)
    result = run(service, sources, run_key="publication.crash")
    completed, after_checkpoints = stored_run(service, "publication.crash")
    assert result["run_id"] == str(previous["run_id"])
    assert result["trace"]["origin_correlation_id"] == previous["result"]["trace"]["origin_correlation_id"]
    assert result["consumer"]["caught_up"] and result["consumer"]["processed"] == 2
    assert result["consumer"]["publication_batches"] == 2
    assert completed["attempts"] == 2
    assert after_checkpoints == checkpoints
    assert service.snapshot()["counts"] == before["counts"]


def test_publication_budget_failure_keeps_committed_progress_and_can_resume(service, monkeypatch):
    sources = manifest()
    monkeypatch.setattr(service, "consume", partial(service.consume, limit=1))
    monkeypatch.setattr(pipeline, "MAX_PUBLICATION_BATCHES", 1)
    with pytest.raises(PublicationIncomplete, match="bounded batch limit"):
        run(service, sources, run_key="publication.bounded")
    previous, checkpoints = stored_run(service, "publication.bounded")
    assert previous["status"] == "failed" and previous["phase"] == "publication"
    assert previous["result"]["error_code"] == "publication_batch_limit"
    assert previous["result"]["consumer"]["processed"] == 1
    assert previous["result"]["consumer"]["remaining"] == 2
    assert previous["result"]["consumer"]["publication_batches"] == 1
    monkeypatch.setattr(pipeline, "MAX_PUBLICATION_BATCHES", 2)
    prohibit_reingestion(monkeypatch, service)
    result = run(service, sources, run_key="publication.bounded")
    completed, after_checkpoints = stored_run(service, "publication.bounded")
    assert result["run_id"] == str(previous["run_id"])
    assert result["consumer"]["caught_up"] and result["consumer"]["processed"] == 2
    assert completed["attempts"] == 2 and after_checkpoints == checkpoints


def test_empty_batch_with_inconsistent_projection_fails_without_looping_then_resumes(service, monkeypatch):
    sources = manifest()
    service.ingest([record for records in sources.values() for record in records])
    assert service.consume()["caught_up"]
    source_key = sources["ERP_ALPHA"][0].key
    with service.db.connect(write=True) as conn:
        conn.execute("DELETE FROM consumer_crosswalk WHERE consumer='reporting' AND source_key=%s", (source_key,))
    original_consume = service.consume
    calls = 0

    def count_consumption():
        nonlocal calls
        calls += 1
        return original_consume(limit=1)

    monkeypatch.setattr(service, "consume", count_consumption)
    with pytest.raises(PublicationIncomplete, match="made no progress"):
        run(service, sources, run_key="publication.no-progress")
    assert calls == 1
    previous, checkpoints = stored_run(service, "publication.no-progress")
    failure = previous["result"]
    assert previous["status"] == "failed" and previous["phase"] == "publication"
    assert failure["error_code"] == "publication_no_progress"
    assert failure["consumer"]["remaining"] == 0 and failure["consumer"]["processed"] == 0
    assert failure["consumer"]["missing_sources"] == [source_key]
    # Repair the deliberately corrupted projection at its storage boundary.
    with service.db.connect(write=True) as conn:
        conn.execute("INSERT INTO consumer_crosswalk SELECT 'reporting',source_key,golden_id "
                     "FROM memberships WHERE source_key=%s", (source_key,))
    prohibit_reingestion(monkeypatch, service)
    result = run(service, sources, run_key="publication.no-progress")
    completed, after_checkpoints = stored_run(service, "publication.no-progress")
    assert calls == 2 and result["consumer"]["caught_up"]
    assert result["consumer"]["processed"] == 0 and result["consumer"]["publication_batches"] == 1
    assert completed["attempts"] == 2 and after_checkpoints == checkpoints


@pytest.mark.parametrize("unavailable", [False, True])
def test_old_terminal_result_with_partial_publication_is_repaired_using_existing_run(service, monkeypatch, unavailable):
    sources = manifest(unavailable=unavailable)
    key = "publication.legacy-terminal"
    with pytest.raises(RuntimeError, match="before publication"):
        run(service, sources, run_key=key, failpoint="before_publication")
    previous, checkpoints = stored_run(service, key)
    partial_publication = service.consume(limit=1)
    assert not partial_publication["caught_up"]
    # Reconstruct the historical single-batch completion written by the old code.
    status = "degraded" if unavailable else "succeeded"
    legacy = {"run_id": str(previous["run_id"]), "input_hash": previous["input_hash"], "status": status,
              "sources": {row["source_system"]: {"status": row["status"], "accepted": row["accepted"]}
                          for row in checkpoints},
              "reconciliation": {}, "consumer": partial_publication, "trace": previous["result"]["trace"]}
    with service.db.connect(write=True) as conn:
        conn.execute("UPDATE runs SET status=%s,phase='complete',result=%s,finished_at=%s WHERE run_id=%s",
                     (status, Jsonb(legacy), now(conn), previous["run_id"]))
    before = service.snapshot()["counts"]
    monkeypatch.setattr(service, "consume", partial(service.consume, limit=1))
    prohibit_reingestion(monkeypatch, service)
    result = run(service, sources, run_key=key)
    repaired, after_checkpoints = stored_run(service, key)
    assert result["consumer"]["caught_up"] and result["status"] == status
    assert result["run_id"] == legacy["run_id"]
    assert result["trace"]["origin_correlation_id"] == legacy["trace"]["origin_correlation_id"]
    assert repaired["attempts"] == 2 and repaired["phase"] == "complete"
    assert after_checkpoints == checkpoints and service.snapshot()["counts"] == before
    assert run(service, sources, run_key=key) == result
    assert stored_run(service, key)[0]["attempts"] == 2


def test_publication_retries_remain_within_the_three_attempt_budget(service, monkeypatch):
    sources = manifest()
    monkeypatch.setattr(service, "consume", partial(service.consume, limit=1))
    monkeypatch.setattr(pipeline, "MAX_PUBLICATION_BATCHES", 1)
    original = service.consume

    def fail_after_committed_batch():
        original()
        raise RuntimeError("injected interruption before publication result")

    monkeypatch.setattr(service, "consume", fail_after_committed_batch)
    checkpoints = None
    for attempt in range(1, 4):
        with pytest.raises(RuntimeError, match="interruption"):
            run(service, sources, run_key="publication.exhausted")
        stored, current_checkpoints = stored_run(service, "publication.exhausted")
        assert stored["attempts"] == attempt and stored["status"] == "failed"
        if checkpoints is None:
            checkpoints = current_checkpoints
            prohibit_reingestion(monkeypatch, service)
        assert current_checkpoints == checkpoints
    with pytest.raises(Conflict, match="three attempts"):
        run(service, sources, run_key="publication.exhausted")
    assert stored_run(service, "publication.exhausted")[0]["attempts"] == 3
