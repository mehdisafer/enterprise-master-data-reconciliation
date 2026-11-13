"""Bound, versioned snapshot publication to Snowflake standard tables.

PostgreSQL remains the decision authority. This module deliberately does not
implement merge decisions in Snowflake or assume its standard-table keys enforce
uniqueness. One publisher holds a PostgreSQL session advisory lock from export
through publication. All reader views switch generations with one DML commit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID


# Reviewed SQL operations only. Input metadata cannot add a table or expression.
# The types here are Snowflake target types; JSONB becomes VARIANT, UUID VARCHAR.
TABLES: dict[str, dict[str, str]] = {
    "source_records": {
        "source_key": "VARCHAR", "source_system": "VARCHAR", "entity_type": "VARCHAR",
        "source_id": "VARCHAR", "current_payload": "VARIANT", "revision": "NUMBER",
        "ingested_at": "TIMESTAMP_TZ",
    },
    "raw_records": {
        "raw_id": "VARCHAR", "source_key": "VARCHAR", "payload": "VARIANT",
        "payload_hash": "VARCHAR", "effective_from": "TIMESTAMP_TZ", "observed_at": "TIMESTAMP_TZ",
    },
    "identity_groups": {
        "golden_id": "VARCHAR", "entity_type": "VARCHAR", "status": "VARCHAR",
        "version": "NUMBER", "created_at": "TIMESTAMP_TZ",
    },
    "memberships": {"source_key": "VARCHAR", "golden_id": "VARCHAR"},
    "golden_history": {
        "history_id": "VARCHAR", "golden_id": "VARCHAR", "group_version": "NUMBER",
        "attributes": "VARIANT", "provenance": "VARIANT", "conflicts": "VARIANT",
        "valid_from": "TIMESTAMP_TZ", "valid_to": "TIMESTAMP_TZ",
        "known_from": "TIMESTAMP_TZ", "known_to": "TIMESTAMP_TZ",
    },
    "decisions": {
        "decision_id": "VARCHAR", "kind": "VARCHAR", "status": "VARCHAR",
        "requested_by": "VARCHAR", "approved_by": "VARCHAR", "executed_by": "VARCHAR",
        "request": "VARIANT", "result": "VARIANT", "created_at": "TIMESTAMP_TZ",
    },
    "outbox": {
        "event_id": "VARCHAR", "aggregate_id": "VARCHAR", "aggregate_version": "NUMBER",
        "event_type": "VARCHAR", "payload": "VARIANT", "occurred_at": "TIMESTAMP_TZ",
    },
    "consumer_inbox": {
        "consumer": "VARCHAR", "event_id": "VARCHAR", "processed_at": "TIMESTAMP_TZ",
    },
    "consumer_records": {
        "consumer": "VARCHAR", "golden_id": "VARCHAR", "group_version": "NUMBER",
        "payload": "VARIANT", "active": "BOOLEAN",
    },
    "standard_records": {
        "source_key": "VARCHAR", "revision": "NUMBER", "normalization_version": "VARCHAR",
        "attributes": "VARIANT",
    },
    "membership_history": {
        "history_id": "VARCHAR", "source_key": "VARCHAR", "golden_id": "VARCHAR",
        "known_from": "TIMESTAMP_TZ", "known_to": "TIMESTAMP_TZ",
    },
    "candidates": {
        "candidate_id": "VARCHAR", "left_key": "VARCHAR", "right_key": "VARCHAR",
        "left_revision": "NUMBER", "right_revision": "NUMBER", "rule_version": "VARCHAR",
        "mode": "VARCHAR", "evidence": "VARIANT", "disposition": "VARCHAR", "created_at": "TIMESTAMP_TZ",
    },
    "decision_events": {
        "event_id": "VARCHAR", "decision_id": "VARCHAR", "actor": "VARCHAR", "transition": "VARCHAR",
        "payload": "VARIANT", "occurred_at": "TIMESTAMP_TZ",
    },
    "consumer_crosswalk": {"consumer": "VARCHAR", "source_key": "VARCHAR", "golden_id": "VARCHAR"},
    "runs": {
        "run_id": "VARCHAR", "idempotency_key": "VARCHAR", "input_hash": "VARCHAR", "status": "VARCHAR",
        "phase": "VARCHAR", "attempts": "NUMBER", "result": "VARIANT", "started_at": "TIMESTAMP_TZ",
        "finished_at": "TIMESTAMP_TZ",
    },
    "run_sources": {
        "run_id": "VARCHAR", "source_system": "VARCHAR", "status": "VARCHAR", "accepted": "NUMBER",
    },
}
KEYS = {
    "source_records": ("source_key",), "raw_records": ("raw_id",),
    "identity_groups": ("golden_id",), "memberships": ("source_key",),
    "golden_history": ("history_id",), "decisions": ("decision_id",),
    "outbox": ("event_id",), "consumer_inbox": ("consumer", "event_id"),
    "consumer_records": ("consumer", "golden_id"),
    "standard_records": ("source_key",), "membership_history": ("history_id",),
    "candidates": ("candidate_id",), "decision_events": ("event_id",),
    "consumer_crosswalk": ("consumer", "source_key"), "runs": ("run_id",),
    "run_sources": ("run_id", "source_system"),
}
PUBLISHER_LOCK = 760207043


def identifier(value: str) -> str:
    """Accept a simple identifier; reject dotted paths, quotes and SQL fragments."""
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", value):
        raise ValueError("SQL names must be simple identifiers of at most 63 characters")
    return value.upper()


def canonical(value: Any) -> str:
    def encode(item: Any) -> Any:
        if isinstance(item, datetime):
            if item.utcoffset() is None:
                raise ValueError("Snapshot timestamps must include a timezone")
            return item.astimezone(timezone.utc).isoformat()
        if isinstance(item, UUID):
            return str(item)
        if isinstance(item, Decimal):
            return int(item) if item == item.to_integral_value() else str(item)
        raise TypeError(f"Unsupported snapshot value type: {type(item).__name__}")

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=encode)


@dataclass(frozen=True)
class SnowflakeConfig:
    account: str
    user: str
    database: str
    schema: str
    warehouse: str
    role: str
    private_key_file: str
    max_rows: int = 100_000
    statement_timeout: int = 120
    run_timeout: int = 600

    def __post_init__(self) -> None:
        for name in ("database", "schema", "warehouse", "role"):
            object.__setattr__(self, name, identifier(getattr(self, name)))
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,255}", self.account):
            raise ValueError("Invalid Snowflake account identifier")
        if not self.user or len(self.user) > 255:
            raise ValueError("Snowflake user is required")
        if not 1 <= self.max_rows <= 1_000_000:
            raise ValueError("max_rows must be between 1 and 1000000")
        if not 10 <= self.statement_timeout <= 300:
            raise ValueError("statement_timeout must be between 10 and 300 seconds")
        if not 30 <= self.run_timeout <= 900:
            raise ValueError("run_timeout must be between 30 and 900 seconds")
        if not self.private_key_file:
            raise ValueError("A key file supplied outside the repository is required")

    @classmethod
    def from_env(cls) -> SnowflakeConfig:
        required = {
            "account": "SNOWFLAKE_ACCOUNT", "user": "SNOWFLAKE_USER",
            "database": "SNOWFLAKE_DATABASE", "schema": "SNOWFLAKE_SCHEMA",
            "warehouse": "SNOWFLAKE_WAREHOUSE", "role": "SNOWFLAKE_ROLE",
            "private_key_file": "SNOWFLAKE_PRIVATE_KEY_PATH",
        }
        missing = [env for env in required.values() if not os.getenv(env)]
        if missing:
            raise ValueError("Missing authorized Snowflake configuration: " + ", ".join(missing))
        return cls(**{key: os.environ[env] for key, env in required.items()})

    def qualified(self, table: str) -> str:
        return f"{self.database}.{self.schema}.{identifier(table)}"


@dataclass(frozen=True)
class Snapshot:
    captured_at: str
    tables: dict[str, list[dict[str, Any]]]
    contract_version: str = "1"

    @property
    def snapshot_id(self) -> str:
        # Capturing an unchanged database again produces the same id.
        return hashlib.sha256(canonical({"contract_version": self.contract_version, "tables": self.tables}).encode()).hexdigest()

    @property
    def counts(self) -> dict[str, int]:
        return {name: len(rows) for name, rows in self.tables.items()}


def validate_snapshot(snapshot: Snapshot) -> None:
    """Check the contract before a cloud connection or write is attempted."""
    if snapshot.contract_version != "1" or set(snapshot.tables) != set(TABLES):
        raise ValueError("Unsupported or incomplete snapshot contract")
    for table, rows in snapshot.tables.items():
        seen: set[str] = set()
        for row in rows:
            if set(row) != set(TABLES[table]):
                raise ValueError(f"Unexpected columns in {table}")
            key = canonical([row[c] for c in KEYS[table]])
            if any(row[c] is None for c in KEYS[table]) or key in seen:
                raise ValueError(f"Missing or duplicate key in {table}")
            seen.add(key)
    sources = {r["source_key"]: r for r in snapshot.tables["source_records"]}
    groups = {str(r["golden_id"]): r for r in snapshot.tables["identity_groups"]}
    mapped: set[str] = set()
    for row in snapshot.tables["memberships"]:
        group = groups.get(str(row["golden_id"]))
        source = sources.get(row["source_key"])
        if source is None or group is None or group["status"] != "active":
            raise ValueError("Orphan or retired crosswalk identity")
        if source["entity_type"] != group["entity_type"]:
            raise ValueError("Crosswalk mixes entity types")
        mapped.add(row["source_key"])
    if mapped != set(sources):
        raise ValueError("Source identities are missing crosswalks")
    for row in snapshot.tables["golden_history"]:
        if str(row["golden_id"]) not in groups:
            raise ValueError("Golden history has an orphan group")
        if not isinstance(row["attributes"], dict) or not isinstance(row["provenance"], dict):
            raise ValueError("Attributes and provenance must be objects")
        if any(row["provenance"].get(key) is None for key in row["attributes"]):
            raise ValueError("Golden attribute has no provenance")
    # Historical provenance may refer to a source moved by split/unmerge. It must
    # still be retained in the source system, not necessarily in the current group.
    canonical(snapshot.tables)


def export_snapshot(pg: Any, *, max_rows: int = 100_000) -> Snapshot:
    """Export explicit columns in one already-open repeatable-read transaction."""
    if not 1 <= max_rows <= 1_000_000:
        raise ValueError("Export row bound must be between 1 and 1000000")
    result: dict[str, list[dict[str, Any]]] = {}
    total = 0
    with pg.cursor() as cursor:
        cursor.execute("SELECT transaction_timestamp()")
        captured = cursor.fetchone()[0].astimezone(timezone.utc).isoformat()
        for table, columns in TABLES.items():
            # Table, columns and ordering are compile-time allowlists above.
            cursor.execute(f"SELECT {', '.join(columns)} FROM public.{table} ORDER BY {', '.join(KEYS[table])} LIMIT %s", (max_rows + 1,))
            rows: list[dict[str, Any]] = []
            while batch := cursor.fetchmany(500):
                total += len(batch)
                if total > max_rows:
                    raise ValueError("Snapshot exceeds configured row bound; use a reviewed bulk-load extension")
                rows.extend(dict(zip(columns, row, strict=True)) for row in batch)
            result[table] = rows
    # Normalize UUIDs and timestamps exactly once before hashing or sending.
    snapshot = Snapshot(captured, json.loads(canonical(result)))
    validate_snapshot(snapshot)
    return snapshot


@dataclass
class SnowflakePublisher:
    connection: Any
    config: SnowflakeConfig
    query_evidence: list[dict[str, Any]] = field(default_factory=list)
    started: float = field(default_factory=time.monotonic)

    def _execute(self, label: str, sql: str, params: tuple[Any, ...] | None = None) -> Any:
        if time.monotonic() - self.started > self.config.run_timeout:
            raise TimeoutError("Snowflake publication exceeded its total wall-clock budget")
        started = time.perf_counter()
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, params)
        except Exception:
            cursor.close()
            raise
        self.query_evidence.append({
            "operation": label, "query_id": cursor.sfqid,
            "client_elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            "rowcount": cursor.rowcount,
        })
        return cursor

    def _run(self, label: str, sql: str, params: tuple[Any, ...] | None = None) -> None:
        self._execute(label, sql, params).close()

    def _scalar(self, label: str, sql: str, params: tuple[Any, ...] | None = None) -> Any:
        cursor = self._execute(label, sql, params)
        try:
            return cursor.fetchone()[0]
        finally:
            cursor.close()

    def bootstrap(self) -> None:
        """Create fixed objects in an existing, explicitly authorized schema.

        Snowflake DDL commits implicitly, so it is kept outside publication.
        No database, warehouse, grants or network resources are created here.
        """
        q = self.config.qualified
        definitions = {
            "_mdm_snapshot_data": "snapshot_id VARCHAR NOT NULL, table_name VARCHAR NOT NULL, row_key VARCHAR NOT NULL, document VARIANT NOT NULL, row_sha256 VARCHAR NOT NULL",
            "_mdm_snapshot_manifest": "snapshot_id VARCHAR NOT NULL, published_at TIMESTAMP_TZ NOT NULL, source_known_at TIMESTAMP_TZ NOT NULL, row_counts VARIANT NOT NULL, contract_version VARCHAR NOT NULL",
            "_mdm_active_snapshot": "singleton NUMBER NOT NULL, snapshot_id VARCHAR",
        }
        for table, definition in definitions.items():
            self._run("bootstrap_table", f"CREATE TABLE IF NOT EXISTS {q(table)} ({definition})")
        for table, columns in TABLES.items():
            projection = ", ".join(
                f"d.document:{column}::{kind} AS {column}" for column, kind in columns.items()
            )
            self._run("bootstrap_view", f"CREATE VIEW IF NOT EXISTS {q(table)} AS SELECT {projection} "
                      f"FROM {q('_mdm_snapshot_data')} d JOIN {q('_mdm_active_snapshot')} a "
                      f"ON d.snapshot_id = a.snapshot_id WHERE a.singleton = 1 AND d.table_name = '{table}'")
        self._run("bootstrap_pointer", f"INSERT INTO {q('_mdm_active_snapshot')} (singleton, snapshot_id) "
                  f"SELECT 1, NULL WHERE NOT EXISTS (SELECT 1 FROM {q('_mdm_active_snapshot')})")
        self.connection.commit()
        if self._scalar("check_single_writer_pointer", f"SELECT count(*) FROM {q('_mdm_active_snapshot')} WHERE singleton = 1") != 1:
            raise ValueError("Corrupt Snowflake active manifest; reconcile before publication")

    def publish(self, snapshot: Snapshot, *, fail_before_commit: bool = False) -> dict[str, Any]:
        """Publish atomically; retry reconciles the content id after uncertain commit."""
        validate_snapshot(snapshot)
        if sum(snapshot.counts.values()) > self.config.max_rows:
            raise ValueError("Snapshot exceeds configured row bound")
        q = self.config.qualified
        sid = snapshot.snapshot_id
        already = self._scalar("reconcile_manifest", f"SELECT count(*) FROM {q('_mdm_snapshot_manifest')} WHERE snapshot_id = %s", (sid,))
        active = self._scalar("reconcile_pointer", f"SELECT snapshot_id FROM {q('_mdm_active_snapshot')} WHERE singleton = 1")
        if already:
            if already != 1 or active != sid:
                raise ValueError("Snapshot is duplicated or historical; refusing to rewind the active generation")
            return {"snapshot_id": sid, "status": "already_published", "counts": snapshot.counts}
        self._run("begin_publication", "BEGIN")
        try:
            for table, rows in snapshot.tables.items():
                for row in rows:
                    document = canonical(row)
                    row_key = canonical([row[c] for c in KEYS[table]])
                    self._run("load_snapshot_row", f"INSERT INTO {q('_mdm_snapshot_data')} "
                              "(snapshot_id, table_name, row_key, document, row_sha256) "
                              "SELECT %s, %s, %s, PARSE_JSON(%s), %s",
                              (sid, table, row_key, document, hashlib.sha256(document.encode()).hexdigest()))
            for table, expected in snapshot.counts.items():
                actual = self._scalar("verify_loaded_count", f"SELECT count(*) FROM {q('_mdm_snapshot_data')} WHERE snapshot_id = %s AND table_name = %s", (sid, table))
                if actual != expected:
                    raise ValueError(f"Loaded row-count mismatch in {table}")
            duplicates = self._scalar("verify_loaded_keys", f"SELECT count(*) FROM (SELECT table_name, row_key FROM {q('_mdm_snapshot_data')} WHERE snapshot_id = %s GROUP BY table_name, row_key HAVING count(*) <> 1)", (sid,))
            if duplicates:
                raise ValueError("Snowflake snapshot contains duplicate keys")
            cursor = self._execute("verify_loaded_documents", f"SELECT table_name, row_key, document FROM {q('_mdm_snapshot_data')} WHERE snapshot_id = %s", (sid,))
            try:
                loaded = {(table, key): canonical(json.loads(document) if isinstance(document, str) else document)
                          for table, key, document in cursor.fetchall()}
            finally:
                cursor.close()
            expected_documents = {(table, canonical([row[c] for c in KEYS[table]])): canonical(row)
                                  for table, rows in snapshot.tables.items() for row in rows}
            if loaded != expected_documents:
                raise ValueError("Loaded Snowflake document content differs from the source snapshot")
            self._run("publish_manifest", f"INSERT INTO {q('_mdm_snapshot_manifest')} "
                      "(snapshot_id, published_at, source_known_at, row_counts, contract_version) "
                      "SELECT %s, CURRENT_TIMESTAMP(), TO_TIMESTAMP_TZ(%s), PARSE_JSON(%s), %s",
                      (sid, snapshot.captured_at, canonical(snapshot.counts), snapshot.contract_version))
            self._run("advance_pointer", f"UPDATE {q('_mdm_active_snapshot')} SET snapshot_id = %s WHERE singleton = 1", (sid,))
            if fail_before_commit:
                raise RuntimeError("Injected failure before snapshot publication commit")
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        return {"snapshot_id": sid, "status": "published", "counts": snapshot.counts}

    def compare(self, snapshot: Snapshot) -> dict[str, Any]:
        """Read back every canonical row, not only counts, through published views."""
        outcomes: dict[str, Any] = {}
        for table, columns in TABLES.items():
            cursor = self._execute("readback_business_contract", f"SELECT {', '.join(columns)} FROM {self.config.qualified(table)} ORDER BY {', '.join(KEYS[table])}")
            try:
                rows = [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
            finally:
                cursor.close()
            for row in rows:
                for column, kind in columns.items():
                    if kind == "VARIANT" and isinstance(row[column], str):
                        row[column] = json.loads(row[column])
            rows = sorted(json.loads(canonical(rows)), key=lambda row: canonical([row[c] for c in KEYS[table]]))
            expected = sorted(snapshot.tables[table], key=lambda row: canonical([row[c] for c in KEYS[table]]))
            if rows != expected:
                raise ValueError(f"Snowflake/PostgreSQL value or type mismatch in {table}")
            outcomes[table] = {"rows": len(rows), "equal": True}
        return outcomes

    def metrics(self) -> dict[str, Any]:
        """Query timings are observed; billing is intentionally not inferred."""
        cursor = self._execute("query_history", "SELECT QUERY_ID, EXECUTION_STATUS, TOTAL_ELAPSED_TIME, BYTES_SCANNED, ROWS_PRODUCED, CREDITS_USED_CLOUD_SERVICES FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION(RESULT_LIMIT => 10000)) WHERE QUERY_TAG = %s", ("enterprise_mdm_snapshot_v1",))
        try:
            rows = cursor.fetchall()
        finally:
            cursor.close()
        return {"session_queries": [dict(zip(("query_id", "status", "total_elapsed_ms", "bytes_scanned", "rows_produced", "credits_used_cloud_services"), row, strict=True)) for row in rows],
                "billing_amount": None,
                "billing_status": "not_observed",
                "cost_note": "Cloud-services query credits are not total warehouse credits or an invoice. Warehouse metering may require additional privileges and delayed account-usage data."}


def connect(config: SnowflakeConfig) -> Any:
    import snowflake.connector  # Optional dependency, only needed for live publication.

    return snowflake.connector.connect(
        account=config.account, user=config.user, role=config.role,
        warehouse=config.warehouse, database=config.database, schema=config.schema,
        authenticator="snowflake_jwt", private_key_file=config.private_key_file,
        private_key_file_pwd=os.getenv("DBT_ENV_SECRET_SNOWFLAKE_KEY_PASSPHRASE") or None,
        login_timeout=10, network_timeout=30, socket_timeout=30,
        autocommit=False, client_session_keep_alive=False,
        # Connector 4.8+ disables OCSP unless a mode is explicitly supplied.
        # Preserve certificate-revocation checking for this controlled publisher.
        ocsp_fail_open=False,
        session_parameters={"TIMEZONE": "UTC", "QUERY_TAG": "enterprise_mdm_snapshot_v1",
                            "STATEMENT_TIMEOUT_IN_SECONDS": config.statement_timeout,
                            "STATEMENT_QUEUED_TIMEOUT_IN_SECONDS": 30},
    )


def replicate(pg: Any, sf: Any, config: SnowflakeConfig, *, exercise_rollback: bool = False) -> dict[str, Any]:
    """One bounded export/publication with crash reconciliation and full readback.

    The passed PostgreSQL connection must be idle and dedicated to publication.
    Use psycopg's default tuple row factory. No in-memory fake qualifies as a
    Snowflake integration: only executing this against the service does.
    """
    publisher = SnowflakePublisher(sf, config)
    with pg.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", (PUBLISHER_LOCK,))
        acquired = cursor.fetchone()[0]
    pg.commit()
    if not acquired:
        raise RuntimeError("Another Snowflake publisher holds the lease")
    try:
        with pg.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            cursor.execute("SET LOCAL statement_timeout = '30000ms'")
        snapshot = export_snapshot(pg, max_rows=config.max_rows)
        pg.commit()
        publisher.bootstrap()
        rollback_exercised = False
        if exercise_rollback:
            try:
                publisher.publish(snapshot, fail_before_commit=True)
            except RuntimeError as exc:
                if str(exc) != "Injected failure before snapshot publication commit":
                    raise
                rollback_exercised = True
        publication = publisher.publish(snapshot)
        comparison = publisher.compare(snapshot)
        retry = publisher.publish(snapshot)
        try:
            metrics = publisher.metrics()
        except Exception as exc:
            # Publication has already committed and been read back. Missing
            # monitoring privileges must not erase evidence or imply rollback.
            sf.rollback()
            metrics = {"status": "unavailable", "error_type": type(exc).__name__,
                       "billing_amount": None, "billing_status": "not_observed"}
        report = {
            "contract_version": "1", "environment": "live_snowflake",
            "captured_at": snapshot.captured_at, "publication": publication,
            "business_equivalence": comparison,
            "rollback_exercised": rollback_exercised,
            "idempotent_retry": retry["status"] == "already_published",
            "queries": publisher.query_evidence, "metrics": metrics,
            "dbt_build": "must_be_executed_separately_and_artifacts_retained",
        }
        return json.loads(canonical(report))
    finally:
        pg.rollback()
        with pg.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", (PUBLISHER_LOCK,))
        pg.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Publish into the dedicated environment specified by SNOWFLAKE_* variables")
    parser.add_argument("--exercise-rollback", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required to start a real Snowflake publication")
    config = SnowflakeConfig.from_env()
    from mdm.config import database_url
    import psycopg

    with psycopg.connect(database_url()) as pg, connect(config) as sf:
        report = replicate(pg, sf, config, exercise_rollback=args.exercise_rollback)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"snapshot_id": report["publication"]["snapshot_id"], "report": str(args.output)}))


if __name__ == "__main__":
    main()
