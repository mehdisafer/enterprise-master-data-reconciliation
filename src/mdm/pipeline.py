"""One durable orchestrator: bounded, resumable source/reconcile/consume phases."""
from __future__ import annotations

from uuid import uuid4

from psycopg.types.json import Jsonb

from mdm.domain import SourceRecord
from mdm.service import Conflict, Service, digest, now
from mdm.telemetry import correlated_operation, correlation_scope, emit, metadata

SOURCES = ("ERP_ALPHA", "ERP_BETA", "ERP_GAMMA")


@correlated_operation("pipeline.run")
def run(service: Service, sources: dict[str, list[SourceRecord] | None], *, run_key: str, mode="hybrid", failpoint=None):
    if set(sources) != set(SOURCES):
        raise ValueError("declare all three sources; use null for an explicitly unavailable source")
    if not run_key or len(run_key) > 160:
        raise ValueError("run key must contain 1–160 characters")
    for source, records in sources.items():
        if records is not None and any(r.source_system != source for r in records):
            raise ValueError("source manifest contains a record from another source")
    input_hash = digest({"sources": {s: None if records is None else sorted(
        [r.model_dump(mode="json") for r in records], key=lambda r: (r["source_id"], r["valid_from"]))
        for s, records in sources.items()}, "mode": mode})
    # Keep a session lock across phases, without a long-running SQL transaction.
    # A process crash releases this lease. PostgreSQL commits each source alone.
    with service.db.connect() as lease:
        acquired = lease.execute("SELECT pg_try_advisory_lock(24022003) acquired").fetchone()["acquired"]
        lease.commit()
        if not acquired:
            raise Conflict("another pipeline owns the single orchestrator lease")
        try:
            with service.db.connect(write=True) as conn:
                prior = conn.execute("SELECT * FROM runs WHERE idempotency_key=%s", (run_key,)).fetchone()
                if prior:
                    if prior["input_hash"] != input_hash:
                        raise Conflict("run key already refers to a different input manifest")
                    if prior["status"] in {"succeeded", "degraded"}:
                        emit("pipeline.replayed", run_id=prior["run_id"],
                             origin_correlation_id=prior["result"].get("trace", {}).get("origin_correlation_id"))
                        return prior["result"]
                    if prior["attempts"] >= 3:
                        raise Conflict("run exhausted its three attempts; inspect before creating a new run")
                    run_id = prior["run_id"]
                    run_trace = metadata(prior["result"].get("trace"), run_id=run_id)
                    conn.execute("UPDATE runs SET status='running',attempts=attempts+1,finished_at=NULL,result=%s WHERE run_id=%s",
                                 (Jsonb({**prior["result"], "trace": run_trace}), run_id))
                else:
                    run_id = uuid4()
                    run_trace = metadata(run_id=run_id)
                    conn.execute("INSERT INTO runs(run_id,idempotency_key,input_hash,status,phase,started_at,result) VALUES(%s,%s,%s,'running','ingestion',%s,%s)",
                                 (run_id, run_key, input_hash, now(conn), Jsonb({"trace": run_trace})))
            with correlation_scope(run_id=str(run_id), origin_correlation_id=run_trace["origin_correlation_id"]):
                try:
                    source_status = {}
                    emit("pipeline.phase", phase="ingestion")
                    for source in SOURCES:
                        with service.db.connect() as conn:
                            checkpoint = conn.execute("SELECT * FROM run_sources WHERE run_id=%s AND source_system=%s", (run_id, source)).fetchone()
                        if checkpoint:
                            source_status[source] = {"status": checkpoint["status"], "accepted": checkpoint["accepted"]}
                            continue
                        records = sources[source]
                        if records is None:
                            status = {"status": "unavailable", "accepted": 0}
                        else:
                            status = {"status": "succeeded", **service.ingest(records)}
                        # A crash between ingestion and checkpoint is safe: raw hashes
                        # make the next ingestion a no-op.
                        with service.db.connect(write=True) as conn:
                            conn.execute("INSERT INTO run_sources VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                                         (run_id, source, status["status"], status["accepted"]))
                        source_status[source] = status
                    if failpoint == "after_ingest":
                        raise RuntimeError("injected pipeline crash after ingestion")
                    with service.db.connect(write=True) as conn:
                        conn.execute("UPDATE runs SET phase='reconciliation' WHERE run_id=%s", (run_id,))
                    emit("pipeline.phase", phase="reconciliation")
                    reconciliation = service.reconcile(mode=mode)
                    if failpoint == "before_publication":
                        raise RuntimeError("injected crash after committed decisions and before publication")
                    with service.db.connect(write=True) as conn:
                        conn.execute("UPDATE runs SET phase='publication' WHERE run_id=%s", (run_id,))
                    emit("pipeline.phase", phase="publication")
                    consumer = service.consume()
                    status = "degraded" if any(v["status"] == "unavailable" for v in source_status.values()) else "succeeded"
                    result = {"run_id": str(run_id), "input_hash": input_hash, "status": status,
                              "sources": source_status, "reconciliation": reconciliation, "consumer": consumer,
                              "trace": metadata()}
                    with service.db.connect(write=True) as conn:
                        conn.execute("UPDATE runs SET status=%s,phase='complete',result=%s,finished_at=%s WHERE run_id=%s",
                                     (status, Jsonb(result), now(conn), run_id))
                    emit("pipeline.phase", phase="complete", status=status)
                    return result
                except Exception as exc:
                    with service.db.connect(write=True) as conn:
                        conn.execute("UPDATE runs SET status='failed',result=%s,finished_at=%s WHERE run_id=%s",
                                     (Jsonb({"error_type": type(exc).__name__, "trace": metadata()}), now(conn), run_id))
                    raise
        finally:
            lease.execute("SELECT pg_advisory_unlock(24022003)")
            lease.commit()

