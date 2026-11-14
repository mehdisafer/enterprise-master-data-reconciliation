"""Measured bounded profiles; no synthetic score is called production accuracy."""
from __future__ import annotations

import platform
import resource
import time
import tracemalloc
from datetime import timedelta
from itertools import combinations

from mdm.matching import compare, evaluate, generate_candidates
from mdm.synthetic import scale_records


def benchmark(size: int, *, database: bool = False) -> dict:
    if not 30 <= size <= 10000:
        raise ValueError("size must be 30–10,000 source records")
    records, truth = scale_records(max(10, size//3))
    by_key = {r.key: r for r in records}
    tracemalloc.start()
    start = time.perf_counter()
    candidates = generate_candidates(records)
    blocking_s = time.perf_counter()-start
    start = time.perf_counter()
    evidence = [compare(by_key[a], by_key[b]) for a, b in sorted(candidates)]
    comparison_s = time.perf_counter()-start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    control = records[:min(150, len(records))]
    control_map = {r.key: truth[r.key] for r in control}
    start = time.perf_counter()
    exhaustive = [compare(a, b) for a, b in combinations(control, 2)]
    exhaustive_s = time.perf_counter()-start
    control_pairs = generate_candidates(control)
    control_by_key = {r.key: r for r in control}
    start = time.perf_counter()
    blocked = [compare(control_by_key[a], control_by_key[b]) for a, b in sorted(control_pairs)]
    blocked_s = time.perf_counter()-start
    exhaustive_positive = {(e.left_key, e.right_key) for e in exhaustive if e.decision == "auto"}
    blocked_positive = {(e.left_key, e.right_key) for e in blocked if e.decision == "auto"}
    result = {
        "profile": "bounded-synthetic.v1", "requested_records": size, "records": len(records), "seed": 42,
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "predeclared_thresholds": {"false_automatic_merges": 0, "control_candidate_recall": 1.0,
                                   "peak_python_heap_limit_bytes": 256_000_000, "time_budget_seconds": 180},
        "candidate_count": len(candidates), "exhaustive_pair_count": len(records)*(len(records)-1)//2,
        "blocking_seconds": blocking_s, "comparison_seconds": comparison_s,
        "pairs_per_second": len(candidates)/comparison_s if comparison_s else None,
        "peak_python_heap_bytes": peak, "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "automatic_pairs": sum(e.decision == "auto" for e in evidence),
        "control": {"records": len(control), "exhaustive_seconds": exhaustive_s, "blocked_comparison_seconds": blocked_s,
                    "automatic_pair_equivalence": exhaustive_positive == blocked_positive,
                    "metrics": evaluate(control, control_map)},
        "database_executed": database,
        "limits": ["single process", "synthetic distribution", "not a Snowflake performance or cost measurement",
                   "process RSS includes interpreter and imports; Python heap is measured separately"],
    }
    if database:
        from mdm.service import Service
        service = Service()
        service.db.migrate()
        with service.db.connect() as conn:
            if conn.execute("SELECT count(*) n FROM source_records").fetchone()["n"]:
                raise ValueError("database load profile requires an empty dedicated application database")
        start = time.perf_counter()
        ingestion = service.ingest(records)
        ingestion_s = time.perf_counter()-start
        start = time.perf_counter()
        reconciliation = service.reconcile()
        consolidation_s = time.perf_counter()-start
        before = service.snapshot()["counts"]
        changed = [r.model_copy(update={"source_updated_at": r.source_updated_at+timedelta(days=1)}) for r in records[::10]]
        service.ingest(changed)
        after = service.snapshot()["counts"]
        service.consume()
        with service.db.connect() as conn:
            plan = conn.execute("EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) SELECT m.golden_id,count(*) FROM memberships m JOIN source_records s USING(source_key) GROUP BY m.golden_id").fetchone()["QUERY PLAN"]
            server = conn.execute("SELECT version() v").fetchone()["v"]
        result["database"] = {"server": server, "ingestion_seconds": ingestion_s, "consolidation_seconds": consolidation_s,
            "source_records_per_second": len(records)/ingestion_s, "ingestion": ingestion, "reconciliation": reconciliation,
            "history_before": before, "history_after": after, "join_explain_analyze": plan, "invariants": service.check()}
    result["thresholds_met"] = (peak < 256_000_000 and blocking_s+comparison_s < 180
        and result["control"]["automatic_pair_equivalence"]
        and result["control"]["metrics"]["candidate_recall"] == 1
        and result["control"]["metrics"]["auto"]["false_positives"] == 0
        and (not database or result["database"]["invariants"]["passed"]))
    if not result["thresholds_met"]:
        raise AssertionError(result)
    return result
