#!/usr/bin/env bash
# A restore is permitted only into an explicitly named empty, dedicated database.
set -euo pipefail
exec "${MDM_PYTHON:-python3}" - "$@" <<'PY'
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

TABLES = (
    "raw_records", "source_records", "identity_groups", "memberships",
    "golden_history", "decisions", "outbox", "consumer_inbox", "consumer_records",
    "schema_migrations", "standard_records", "membership_history", "candidates",
    "decision_events", "consumer_crosswalk", "runs", "run_sources",
)


class OperationError(Exception):
    """A safe operator-facing error that contains no connection secrets."""


def main():
    parser = argparse.ArgumentParser(description="Restore a verified MDM dump to a new empty database")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--expect-db", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,62}", args.expect_db):
        raise OperationError("Expected database name is invalid")
    if args.expect_db in {"postgres", "template0", "template1"}:
        raise OperationError("A dedicated restore database is required")
    dsn = os.environ.get("MDM_RESTORE_DATABASE_URL", "")
    dsn_file = os.environ.get("MDM_RESTORE_DATABASE_URL_FILE")
    if dsn and dsn_file:
        raise OperationError("Use only one restore secret mechanism")
    if dsn_file:
        dsn = Path(dsn_file).read_text().strip()
    if not dsn:
        raise OperationError("MDM_RESTORE_DATABASE_URL or MDM_RESTORE_DATABASE_URL_FILE is required")
    if args.report.exists() or args.report.is_symlink():
        raise OperationError("Restore report already exists; choose a new path")
    if args.archive.is_symlink() or not args.archive.is_file():
        raise OperationError("Archive must be a regular file")
    manifest_path = Path(str(args.archive) + ".manifest.json")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("format_version") != 1 or set(manifest.get("tables", {})) != set(TABLES):
        raise OperationError("Unsupported backup manifest")
    archive_digest = hashlib.sha256()
    with args.archive.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            archive_digest.update(chunk)
    if archive_digest.hexdigest() != manifest["archive_sha256"]:
        raise OperationError("Archive checksum differs from its recorded manifest")
    client_env = os.environ.copy()
    mapping = {"dbname": "PGDATABASE", "password": "PGPASSWORD", "user": "PGUSER",
               "application_name": "PGAPPNAME", "connect_timeout": "PGCONNECT_TIMEOUT"}
    for key, value in conninfo_to_dict(dsn).items():
        client_env[mapping.get(key, "PG" + key.upper().replace("_", ""))] = str(value)
    client_env["PGCONNECT_TIMEOUT"] = "10"
    client_env["PGOPTIONS"] = "-c lock_timeout=5000 -c statement_timeout=300000"
    pg_restore = os.environ.get("PG_RESTORE", "pg_restore")
    client_version = subprocess.check_output([pg_restore, "--version"], env=client_env, text=True).strip()
    started = time.monotonic()
    with psycopg.connect(dsn, connect_timeout=10, autocommit=True) as conn:
        conn.execute("SET TIME ZONE 'UTC'")
        conn.execute("SET statement_timeout = '300s'")
        conn.execute("SET idle_in_transaction_session_timeout = '600s'")
        database, server_version = conn.execute(
            "SELECT current_database(), current_setting('server_version')"
        ).fetchone()
        if database != args.expect_db:
            raise OperationError("Connected database does not match --expect-db")
        # Serialize this tool. The target must also be fenced from application traffic.
        locked = conn.execute("SELECT pg_try_advisory_lock(1835298098)").fetchone()[0]
        if not locked:
            raise OperationError("Another restore holds the restore lock")
        objects = conn.execute("""
            SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname <> 'information_schema'
        """).fetchone()[0]
        functions = conn.execute("""
            SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname <> 'information_schema'
        """).fetchone()[0]
        other_sessions = conn.execute("""
            SELECT count(*) FROM pg_stat_activity
            WHERE datname = current_database() AND pid <> pg_backend_pid()
        """).fetchone()[0]
        if objects or functions or other_sessions:
            raise OperationError("Restore target is not empty and isolated")
        with args.archive.open("rb") as file:
            subprocess.run(
                [pg_restore, "--dbname", database, "--no-owner", "--no-privileges", "--exit-on-error", "--single-transaction"],
                env=client_env, stdin=file, check=True, timeout=600,
            )
        restored = {}
        for table in TABLES:
            digest = hashlib.sha256()
            count = 0
            query = sql.SQL("SELECT to_jsonb(t)::text FROM {} t ORDER BY to_jsonb(t)::text").format(
                sql.Identifier("public", table)
            )
            with conn.cursor() as cursor:
                cursor.execute(query)
                for (row,) in cursor:
                    digest.update(row.encode() + b"\n")
                    count += 1
            restored[table] = {"rows": count, "sha256": digest.hexdigest()}
        if restored != manifest["tables"]:
            raise OperationError("Restored rows differ from the exported backup snapshot")
        check_env = client_env.copy()
        check_env.pop("MDM_DATABASE_URL_FILE", None)
        check_env["MDM_DATABASE_URL"] = dsn
        check = subprocess.run(["mdm", "check"], env=check_env, capture_output=True, text=True, timeout=120)
        if check.returncode != 0:
            raise OperationError("Business invariant check failed after restoration")
        report = {
            "format_version": 1,
            "restored_at": datetime.now(timezone.utc).isoformat(),
            "target_database": database,
            "server_version": server_version,
            "client_version": client_version,
            "archive_sha256": archive_digest.hexdigest(),
            "tables": restored,
            "snapshot_content_equal": True,
            "business_check_exit_code": check.returncode,
            "business_check": json.loads(check.stdout),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "consumer_delivery_state_restored": True,
            "external_consumer_rollback_performed": False,
        }
        os.umask(0o077)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("x") as file:
            json.dump(report, file, indent=2, sort_keys=True)
            file.write("\n")
        print(json.dumps({"restore_verified": True, "report": str(args.report)}))


try:
    main()
except Exception as exc:
    print(json.dumps({"restore_verified": False, "error_type": type(exc).__name__, "reason": str(exc) if isinstance(exc, OperationError) else "Inspect the failing stage; connection details are suppressed"}), file=sys.stderr)
    sys.exit(1)
PY
